"""HOVER measurement report importer.

Flow:
1. Contractor uploads a HOVER PDF (multi-page measurement report).
2. We extract the plain text with pdfplumber — the PDFs are
   text-based, not scans, so this is fast and accurate.
3. The extracted text is sent to Claude Sonnet 4.5 with a strict JSON-output
   prompt that pulls every measurement we need (areas, counts, lengths).
4. Backend maps those measurements to catalog line items using
   industry-standard waste/coverage ratios and returns a draft `lines[]`
   payload the frontend can preview + commit.

Why text extraction first instead of sending the PDF binary to the LLM:
- `FileContentWithMimeType` in emergentintegrations only works with Gemini.
- HOVER PDFs are pure text (no scanned images we need to OCR).
- Sending ~40KB of text is ~10x cheaper + faster than the binary.

Constants live in this file so Howard can tune them without me touching code.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Optional

import pdfplumber
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from deps import get_current_user
import lp_smartside_formulas as lp_formulas
from vinyl_color_tiers import apply_row_color_tiers as _apply_row_color_tiers
from measure_staging import (guess_vero_product_type as _staging_guess_vero,
                             VERO_TO_MEZZO as _VERO_TO_MEZZO,
                             build_paired_openings as _staging_build_paired_openings,
                             fold_photo_fillins as _staging_fold_photo_fillins,
                             is_fillin as _staging_is_fillin)

# Iter 78q — Phase 3 Deep Verify uses MongoDB to cache rendered elevation
# page PNGs. The TTL index purges entries 1 hour after creation so we
# never accumulate stale render data.
try:
    from services import db
except Exception:  # pragma: no cover — defensive at import time
    db = None


# -----------------------------------------------------------------------------
# Window-style guessing — HOVER reports DON'T tell us if a window is DH vs
# slider vs casement. They only give the rough opening (W × H). These rules
# pick the most likely Vero product type from those two numbers. Contractors
# can override per opening in the preview modal before applying.
#
# Rules apply in order — first match wins. Tuned to Howard's real-world bias:
# 99% of replacement openings end up as Double Hung; we only switch when
# dimensions strongly indicate otherwise.
# -----------------------------------------------------------------------------
def _guess_vero_product_type(width_in: float, height_in: float) -> str:
    """ONE COPY (ruled 2026-08-01): lives in measure_staging."""
    return _staging_guess_vero(width_in, height_in)


def _vero_to_mezzo_product_type(vero_type: str) -> str:
    return _VERO_TO_MEZZO.get(vero_type, "Mezzo Double Hung")

load_dotenv()

router = APIRouter()
logger = logging.getLogger("estimator.hover")

DEFAULT_WASTE_PCT = 10.0  # Howard's preferred default per setup

# -----------------------------------------------------------------------------
# Catalog mapping
# -----------------------------------------------------------------------------
# Map HOVER measurements → catalog line items. Each entry now declares which
# *tab(s)* it targets (vinyl / ascend / lp_smart) so a single HOVER upload
# auto-populates all three parallel option sets — the contractor lands with
# three complete quotes ready to compare.
#
# Industry-standard ratios are documented inline so Howard can tune them.

# Typical opening perimeters used to back out window+patio-door perimeter
# from HOVER's lumped `opening_perimeter_lf` (HOVER doesn't break it out).
ENTRY_DOOR_PERIM_LF = 19.0    # 6'8" × 3'0" → 2 × (6.67 + 3.0) ≈ 19.3
GARAGE_DOOR_PERIM_LF = 32.0   # 9'0" × 7'0" → 2 × (9 + 7) = 32
PATIO_DOOR_PERIM_LF = 22.0    # 6'0" × 6'8" → 2 × (6 + 6.67) ≈ 25.3 (use 22, panels share jambs)
WINDOW_PERIM_LF_FALLBACK = 14.0  # 3'0" × 4'0" typical replacement window → 14 perim
FINISH_TRIM_SILL_LF_FALLBACK = 3.0  # ruled 2026-08-01 (10e): typical 3' sill width


def _window_perim_total_lf(m: dict) -> float:
    """Total window perimeter (all 4 sides) across every window on the job.

    Prefers per-window dims from `windows[]` (most accurate); falls back to
    `window_count × WINDOW_PERIM_LF_FALLBACK` when HOVER didn't break out
    individual dimensions. Used by Finish Trim (Iter 78f — full window
    perimeter, not just sills).
    """
    windows = m.get("windows") or []
    if windows:
        perim_in = sum(
            2 * (float(w.get("width_in") or 0) + float(w.get("height_in") or 0))
            for w in windows
        )
        return perim_in / 12.0
    return float(m.get("window_count") or 0) * WINDOW_PERIM_LF_FALLBACK


# R1 ruled 2026-07-30 (Howard): exactly 2 J passes per rake — ONE wall pass
# carried by the wall J-Channel line (vinyl accessories), ONE rake pass
# carried by Soffit J (soffit category). The old soffit-J 2×rakes term made
# 3 total and is retired. ONE DOCTRINE STRING — the finish-trim exclusion,
# the wall-J rake term and the soffit-J derivation all pin to this marker
# (test_rake_j_passes_2026_07_30).
RAKE_J_DOCTRINE = ("R1 ruled 2026-07-30: exactly 2 J passes per rake — "
                   "wall pass on the wall J-Channel line, ONE rake pass on Soffit J")


def _finish_trim_sill_lf(m: dict) -> float:
    """RULED 2026-08-01 (10e closing): finish trim's window term is the
    SILL WIDTHS — undersill trim catches the cut panel edge under the sill;
    the window sides/tops are the J-channel's work, billed separately.
    Primary input = measured window_bottom_width_total_lf; else compute it
    from per-window dims; else window_count × 3' (the old ×14 full-opening
    constant is retired for this term)."""
    wbw = float(m.get("window_bottom_width_total_lf") or 0)
    if wbw > 0:
        return wbw
    windows = m.get("windows") or []
    if windows:
        computed = sum(float(w.get("width_in") or 0) for w in windows) / 12.0
        if computed > 0:
            return computed
    return float(m.get("window_count") or 0) * FINISH_TRIM_SILL_LF_FALLBACK


def _finish_trim_viz(m: dict) -> dict | None:
    """BARS = CHIPS (Howard ruled 2026-08-07): the coverage bar renders
    ONLY what the emitted line carries — one source, zero client-side
    formula copies to go stale. 637-vs-279 died here."""
    eaves = float(m.get("eaves_lf") or 0)
    sills = _finish_trim_sill_lf(m)
    if eaves <= 0 and sills <= 0:
        return None
    return {
        "segments": [
            {"label": "Eave top course", "lf": round(eaves, 1)},
            {"label": "Window sills", "lf": round(sills, 1)},
        ],
        "divisor": 12.5,
        "formula": ("ceil((Eave top course + Window sills) ÷ 12.5) — "
                    "sills + top course (ruled 2026-08-01); rakes excluded "
                    f"({RAKE_J_DOCTRINE})"),
    }


def _soffit_j_viz(m: dict) -> dict | None:
    """Soffit-J bar segments — same terms the extract divides."""
    eaves = float(m.get("eaves_lf") or 0)
    rakes = float(m.get("rakes_lf") or 0)
    porch, _ = _porch_soffit_j_lf(m)
    if eaves <= 0 and rakes <= 0 and porch <= 0:
        return None
    return {
        "segments": [
            {"label": "Eaves run", "lf": round(eaves, 1)},
            {"label": "Rakes × 1 pass", "lf": round(rakes, 1)},
            {"label": "Porch ceiling channel", "lf": round(porch, 1)},
        ],
        "divisor": 12.5,
        "formula": ("ceil((Eaves + Rakes + porch ceiling channel) ÷ 12.5) — "
                    "ONE rake pass (R1 2026-07-30); porch FULL PERIMETER "
                    "on this line (split ruled 2026-08-07)"),
    }


def _gutter_viz(m: dict) -> dict | None:
    """Gutter-assumption chips read the SAME derivation the lines used —
    run inventory when a door read it, never a client-side eaves/30 copy."""
    glf = _gutter_lf(m)
    if glf <= 0:
        return None
    runs = _gutter_run_list(m)
    return {
        "gutter_lf": round(glf, 1),
        "runs": _gutter_run_count(m),
        "run_labels": [r["label"] for r in runs] if runs else None,
        "basis": "run_inventory" if runs else "eaves_estimate",
        "downspouts": _downspout_count(m),
        "hangers_spaced": math.ceil(glf / 2 - 1e-9),
    }


def _finish_trim_pcs(m: dict) -> int:
    """Finish Trim qty = ceil((Eaves top course + window SILL widths) ÷ 12.5)
    — Howard ruled 2026-08-01 (10e): sills + top course; the Iter 78f full
    window perimeter retired (it double-served edges the J already covers).
    Rakes are deliberately excluded: the rake's two passes are already
    carried by wall J-Channel (1) + Soffit J (1) — R1 ruled 2026-07-30
    (see RAKE_J_DOCTRINE); adding rake here would push it to 3."""
    eaves = float(m.get("eaves_lf") or 0)
    sills = _finish_trim_sill_lf(m)
    return max(0, math.ceil((eaves + sills) / 12.5 - 1e-9))


def _finish_trim_note(m: dict) -> str:
    eaves = float(m.get("eaves_lf") or 0)
    sills = _finish_trim_sill_lf(m)
    if float(m.get("window_bottom_width_total_lf") or 0) > 0:
        src = "measured sill widths"
    elif m.get("windows"):
        src = f"{len(m.get('windows') or [])} windows summed sill widths"
    else:
        src = (f"{int(m.get('window_count') or 0)} wins × "
               f"{int(FINISH_TRIM_SILL_LF_FALLBACK)}' sill (fallback)")
    total = eaves + sills
    pcs = max(0, math.ceil(total / 12.5 - 1e-9))
    return (f"{eaves:.0f} eaves + {sills:.0f} LF window sills "
            f"({src}) = {total:.0f} LF ÷ 12.5 = {pcs} pcs")


# Iter 79b — .019 Coil (Siding Accessories) auto-fill — Howard switched
# from "1 roll per 5 squares of siding" to a perimeter-based rule that
# matches how the coil is actually installed (wrapped around openings
# for clean flashing transitions). Perimeter = windows + entry doors
# + sliding glass / patio doors + garage doors. 1 ROLL covers 100 LF.
def _coil_019_rolls(m: dict) -> float:
    win = 0.0 if m.get("_windows_integral_j") else _window_perim_total_lf(m)
    entry = float(m.get("entry_door_count") or 0) * ENTRY_DOOR_PERIM_LF
    patio = float(m.get("patio_door_count") or 0) * PATIO_DOOR_PERIM_LF
    garage = float(m.get("garage_door_count") or 0) * GARAGE_DOOR_PERIM_LF
    total = win + entry + patio + garage
    if total <= 0:
        return 0
    return round(total / 100, 2)


def _coil_019_breakdown(m: dict) -> str:
    integral_j = bool(m.get("_windows_integral_j"))
    win = 0.0 if integral_j else _window_perim_total_lf(m)
    entry_n = float(m.get("entry_door_count") or 0)
    patio_n = float(m.get("patio_door_count") or 0)
    garage_n = float(m.get("garage_door_count") or 0)
    entry_lf = entry_n * ENTRY_DOOR_PERIM_LF
    patio_lf = patio_n * PATIO_DOOR_PERIM_LF
    garage_lf = garage_n * GARAGE_DOOR_PERIM_LF
    parts = ["0 LF windows (integral-J — ruled 2026-08-05, not wrapped)"
             if integral_j else f"{win:.0f} LF windows"]
    if entry_n:
        parts.append(f"{int(entry_n)} entry × {int(ENTRY_DOOR_PERIM_LF)}")
    if patio_n:
        parts.append(f"{int(patio_n)} sliding × {int(PATIO_DOOR_PERIM_LF)}")
    if garage_n:
        parts.append(f"{int(garage_n)} garage × {int(GARAGE_DOOR_PERIM_LF)}")
    total = win + entry_lf + patio_lf + garage_lf
    return f"{' + '.join(parts)} = {total:.0f} LF ÷ 100 = {round(total/100, 2)} rolls"


# Iter 78h — per-job breakdown strings for the 3 downspout-derived gutter
# rows so the Takeoff Recon Card can surface the math (1/25 LF rule, min 2,
# 10 LF/downspout, 2 elbows/downspout). Mirrors the J-channel pattern.
def _downspout_count(m: dict) -> int:
    # GUTTER ACCESSORIES CONSUME THE RUN INVENTORY (Howard ruled
    # 2026-08-07): every accessory divides the GUTTER figure (run sum
    # when a door read runs), never the discarded eave plane-sum.
    glf = _gutter_lf(m)
    if glf <= 0:
        return 0
    return max(2, math.ceil(glf / 25 - 1e-9))


# SEND-105 — RULING V CONVERSION (was PENDING_CONVERSION in every
# census line since send 19). The drop height comes from a VERIFIED
# base or the read REFUSES: no story defaults, no `_ai_story_count
# or 1`, no hardcoded 9'. Model heights stay hypothesis-only.
# SEND-107: refused rows carry a MACHINE REASON CODE so companions
# assert the code, never the prose sentence (a reworded message must
# not break a pin when no behaviour changed).
RULING_V_REFUSAL_CODE = "RULING_V_NO_VERIFIED_HEIGHT"


# SEND-129 (Howard ruled 2026-08-25) — A REFUSAL THAT DOES NOT SURVIVE TO
# THE END OF THE PIPELINE IS NOT A REFUSAL. The measurement keys below are
# read by priced lanes; a REFUSED key (present and None) used to arrive as
# `or 0`, i.e. a silent zero indistinguishable from a real zero. Now the
# refusal is (a) carried to the takeoff as its own disclosure and (b)
# refuses the lanes whose whole basis it is.
REFUSAL_SENSITIVE_LANES = {
    "starter_lf": ["starter course", "starter door deduction"],
    "footprint_perimeter_ft": ["batten stackup", "start course"],
    "outside_corner_lf": ["outside corner posts", "roofline mitres"],
    "inside_corner_lf": ["inside corner posts", "mitres"],
    "eaves_lf": ["gutter", "fascia", "level frieze"],
    "rakes_lf": ["rake trim", "sloped frieze"],
    "siding_sqft": ["field siding"],
    "soffit_sqft": ["soffit"],
    "level_frieze_lf": ["level frieze"],
    "sloped_frieze_lf": ["sloped frieze"],
    "drip_edge_lf": ["drip edge"],
}


def _key_refused(m: dict, key: str) -> bool:
    """REFUSED = the key is present and None. Absent is 'never read'."""
    return isinstance(m, dict) and key in m and m.get(key) is None


def refused_measurement_lanes(m: dict) -> list:
    """Every refused measurement key with the priced lanes that read it —
    the disclosure that rides the takeoff so a refusal is never a zero."""
    out = []
    for key, lanes in REFUSAL_SENSITIVE_LANES.items():
        if _key_refused(m, key):
            out.append({"key": key, "lanes": lanes,
                        "note": (f"{key} REFUSED upstream — the lane(s) "
                                 f"{', '.join(lanes)} have no owned input; "
                                 "a zero here would be a real zero, and "
                                 "this is not one")})
    return out


def _verified_drop_height_ft(m: dict):
    """(height_ft, basis) from the estimate's own VERIFIED heights —
    taped human dimensions or the face's own DP-1 DERIVED chain —
    worst-case MAX, never averaged (Ruling T precedent). (None, why)
    when nothing verified exists."""
    vh = m.get("_verified_wall_heights_ft") or {}
    ents = [(f, d) for f, d in vh.items()
            if isinstance(d, dict) and d.get("ft")]
    if not ents:
        return None, ("no verified wall height on this estimate — "
                      "nothing taped and no DP-1 DERIVED chain; a model "
                      "height is hypothesis only and never a quantity "
                      "base (Ruling V)")
    f, d = max(ents, key=lambda e: float(e[1]["ft"]))
    return float(d["ft"]), (f"{d.get('src')} {d['ft']} ft ({f} face — "
                            f"max of {len(ents)} verified, never "
                            "averaged)")


def _downspout_drop_ft(m: dict):
    """Verified eave height + 2 ft kick-out + 1 ft slack, or None
    (REFUSED — Ruling V). The story-count ladder (1→9/2→18/3→27) and
    the 9 ft floor are RETIRED."""
    h, _ = _verified_drop_height_ft(m)
    if h is None:
        return None
    return h + 3.0  # +2 ft kick + 1 ft slack


def _downspout_lf(m: dict):
    """Total downspout coil LF for the job (count × per-drop), or None
    when the drop height REFUSES (Ruling V)."""
    n = _downspout_count(m)
    if n <= 0:
        return 0
    drop = _downspout_drop_ft(m)
    if drop is None:
        return None
    return int(round(n * drop))


def _gutter_basis(m: dict) -> str:
    """Names the LF basis every gutter accessory divides (ruled 2026-08-07)."""
    return "LF gutter (run inventory)" if _gutter_run_list(m) else "LF eaves"


def _downspout_breakdown(m: dict) -> str:
    glf = _gutter_lf(m)
    if glf <= 0:
        return "No gutter → 0 downspouts"
    raw = glf / 25
    n = _downspout_count(m)
    drop = _downspout_drop_ft(m)
    if drop is None:
        _, why = _verified_drop_height_ft(m)
        return (f"REFUSED — drop height not derivable: {why}; "
                f"{n} downspouts stand, LF and sticks refuse")
    total_lf = _downspout_lf(m)
    _, basis = _verified_drop_height_ft(m)
    min_hit = " (min 2)" if n == 2 and raw < 2 else ""
    sticks = math.ceil(total_lf / 10 - 1e-9) if total_lf > 0 else 0
    return (f"{glf:.0f} {_gutter_basis(m)} ÷ 25 = {raw:.1f} → ceil = "
            f"{n} downspouts{min_hit} × {drop:.0f} LF drop "
            f"(verified: {basis} + 3 ft kick/slack) = {total_lf} LF "
            f"→ {sticks} sticks (10' each, whole sticks — ruled 2026-07-31)")


def _gutter_run_list(m: dict) -> list:
    runs = m.get("_gutter_runs")
    if not isinstance(runs, list):
        return []
    out = []
    for r in runs:
        if isinstance(r, dict):
            try:
                lf = float(r.get("lf") or 0)
            except (TypeError, ValueError):
                lf = 0.0
            if lf > 0:
                out.append({"label": str(r.get("label") or "run"), "lf": lf})
    return out


def _gutter_lf(m: dict) -> float:
    """GUTTER CONSUMES THE RUN INVENTORY (Howard ruled 2026-08-06 — the
    gutter over-count trace): plane-summed eaves stay the SOFFIT figure
    (soffit exists under every eave), but gutter is per-FACADE-RUN — a
    plane census can list a bump-out's eave beside the run it already
    sits inside. When the door read gutter runs, their sum IS the gutter
    figure; otherwise eaves LF (unchanged fallback)."""
    runs = _gutter_run_list(m)
    if runs:
        return float(sum(r["lf"] for r in runs))
    return float(m.get("eaves_lf") or 0)


def _gutter_note(m: dict) -> str:
    runs = _gutter_run_list(m)
    if not runs:
        return "Eaves LF × 1 run (gutters run along eaves, not rakes)"
    lst = " + ".join(f"{r['label']} {r['lf']:g}'" for r in runs)
    return (f"Run inventory: {lst} = {_gutter_lf(m):g} LF — checkable against "
            "the house by eye; the eave plane-sum stays the soffit figure")


def _elbow_breakdown(m: dict) -> str:
    glf = _gutter_lf(m)
    if glf <= 0:
        return "No gutter → 0 elbows"
    raw = glf / 25
    n = _downspout_count(m)
    min_hit = " (min 2)" if n == 2 and raw < 2 else ""
    return (f"{glf:.0f} {_gutter_basis(m)} ÷ 25 = {raw:.1f} → {n} downspouts{min_hit} "
            f"× 2 elbows (top turn + kick-out) = {n * 2} elbows")


# Iter 78i — Hangers with screws. Howard's install rule: 1 hanger per 2 ft
# of gutter + 1 per gutter run.
# RUN COUNT (Howard ruled 2026-08-07): when a door read the run
# inventory, its COUNT is the run count — the app never again invents 7
# runs off a plane-sum the card correctly printed as 3. The ~1 run per
# 30 LF estimate survives only as the no-inventory fallback.
def _gutter_run_count(m: dict) -> int:
    runs = _gutter_run_list(m)
    if runs:
        return len(runs)
    eaves = float(m.get("eaves_lf") or 0)
    if eaves <= 0:
        return 0
    return max(2, math.ceil(eaves / 30 - 1e-9))


def _hangers_count(m: dict) -> int:
    glf = _gutter_lf(m)
    if glf <= 0:
        return 0
    spaced = math.ceil(glf / 2 - 1e-9)
    runs = _gutter_run_count(m)
    return spaced + runs


def _hangers_breakdown(m: dict) -> str:
    glf = _gutter_lf(m)
    if glf <= 0:
        return "No gutter → 0 hangers"
    spaced = math.ceil(glf / 2 - 1e-9)
    runs = _gutter_run_count(m)
    run_src = "door-read run inventory" if _gutter_run_list(m) else "~1 run per 30 LF est."
    return (f"{glf:.0f} {_gutter_basis(m)} ÷ 2 ft spacing = {spaced} + {runs} runs "
            f"({run_src}, 1 per run) = {spaced + runs} hangers")


# Iter 78z (P1.4) — Gutter geometry: mitres, pipe clips, sealant.
#
# Mitre count = number of outside (or inside) corners the gutter run
# wraps. We infer roof type from AI walls: any gable wall present
# means the gutter doesn't wrap (typical 2-run front+back layout, 0
# mitres). On a pure hip roof every elevation flows water into the
# gutter so the gutter wraps the full perimeter — 4 mitres for a basic
# rectangular footprint, +1 per additional outside corner. We pull
# corner count from `outside_corner_lf / avg_wall_height` (rounded).
# Inside corners (re-entrant L-shaped footprints) add inside mitres
# 1:1 with `inside_corner_lf / avg_wall_height`.
def _has_gable_wall(m: dict) -> bool:
    """True when at least one wall in the per-elevation breakdown was
    flagged as a gable (gable_sqft > 0). Falls back to `_ai_gable_sqft`
    aggregate when the per-elevation grid isn't available."""
    per_elev = m.get("_per_elevation_breakdown") or []
    if isinstance(per_elev, list):
        for e in per_elev:
            if float(e.get("gable_sqft") or 0) > 0:
                return True
    return float(m.get("_ai_gable_sqft") or 0) > 0


def _gutter_corner_count(m: dict):
    """Returns (outside_corners, inside_corners) of the gutter run, or
    None when no verified height exists to divide the corner LF by
    (SEND-105 Ruling V — the hardcoded 9 ft floor is RETIRED).

    Outside corners drive ROOFLINE mitres. Inside corners (re-entrant
    L-shaped footprints) also drive mitres 1:1.
    """
    h, _ = _verified_drop_height_ft(m)
    if h is None or h <= 0:
        return None
    # SEND-129: a refused corner LF refuses the mitre count — the caller
    # already emits a NAMED refusal row for None (Ruling V machinery).
    if _key_refused(m, "outside_corner_lf") or _key_refused(m, "inside_corner_lf"):
        return None
    out_lf = float(m.get("outside_corner_lf") or 0)
    in_lf = float(m.get("inside_corner_lf") or 0)
    out_n = round(out_lf / h)
    in_n = round(in_lf / h)
    return max(0, out_n), max(0, in_n)


def _mitre_count(m: dict):
    if _gutter_lf(m) <= 0:
        return 0
    cc = _gutter_corner_count(m)
    if cc is None:
        return None
    out_n, in_n = cc
    # Gable house: gutter doesn't wrap → 0 outside mitres. Inside
    # corners (porches / L-shapes) still get a mitre because the gutter
    # has to follow the re-entrant fascia.
    if _has_gable_wall(m):
        return in_n
    # Pure hip roof: gutter wraps → mitres at every outside + inside corner.
    return out_n + in_n


def _mitre_breakdown(m: dict) -> str:
    if _gutter_lf(m) <= 0:
        return "No gutter → 0 mitres"
    cc = _gutter_corner_count(m)
    if cc is None:
        _, why = _verified_drop_height_ft(m)
        return f"REFUSED — corner count not derivable: {why}"
    out_n, in_n = cc
    gable = _has_gable_wall(m)
    n = _mitre_count(m)
    if gable:
        return (f"Gable roof — gutter doesn't wrap. "
                f"Outside corners ({out_n}) skipped; inside corners {in_n} → {n} mitres")
    return (f"Hip roof — gutter wraps. "
            f"Outside {out_n} + inside {in_n} = {n} mitres")


# Pipe Clips: 1 clip per 6 ft of downspout drop (industry standard).
# Most installs use 2 clips per single-story drop (~12 LF / 6 = 2),
# 4 clips per 2-story drop. Each clip secures the downspout to the
# wall against wind load.
def _pipe_clips_count(m: dict):
    n_down = _downspout_count(m)
    if n_down <= 0:
        return 0
    drop = _downspout_drop_ft(m)
    if drop is None:
        return None
    per_down = max(2, math.ceil(drop / 6 - 1e-9))
    return n_down * per_down


def _pipe_clips_breakdown(m: dict) -> str:
    n_down = _downspout_count(m)
    if n_down <= 0:
        return "No downspouts → 0 pipe clips"
    drop = _downspout_drop_ft(m)
    if drop is None:
        _, why = _verified_drop_height_ft(m)
        return f"REFUSED — clip count not derivable: {why}"
    per_down = max(2, math.ceil(drop / 6 - 1e-9))
    total = n_down * per_down
    return (f"{n_down} downspouts × {per_down} clips ({drop:.0f} LF drop ÷ 6) "
            f"= {total} clips")


# Gutter Sealant: 1 tube per 4 connection points. Connection points =
# every mitre + every end cap + every outlet (1 outlet per downspout).
# A standard 10 oz tube covers ~16-20 ft of joint, and each connection
# uses ~4-5 ft. Howard's job-cost rule of thumb: 1 tube per 4 joints.
def _sealant_count(m: dict):
    if _gutter_lf(m) <= 0:
        return 0
    mitres = _mitre_count(m)
    if mitres is None:
        return None
    runs = _gutter_run_count(m)
    end_caps = runs * 2
    outlets = _downspout_count(m)
    joints = mitres + end_caps + outlets
    return max(1, math.ceil(joints / 4 - 1e-9)) if joints > 0 else 0


def _sealant_breakdown(m: dict) -> str:
    if _gutter_lf(m) <= 0:
        return "No gutter → 0 sealant tubes"
    mitres = _mitre_count(m)
    if mitres is None:
        _, why = _verified_drop_height_ft(m)
        return f"REFUSED — joint count not derivable: {why}"
    runs = _gutter_run_count(m)
    end_caps = runs * 2
    outlets = _downspout_count(m)
    joints = mitres + end_caps + outlets
    n = _sealant_count(m)
    return (f"{mitres} mitres + {end_caps} end caps + {outlets} outlets "
            f"= {joints} joints ÷ 4 = {n} tubes")


def _j_channel_pcs(m: dict) -> int:
    """See `_j_channel_breakdown` for the full math + which source path
    was used. This wrapper just returns the integer piece count."""
    pcs, _ = _j_channel_compute(m)
    return pcs


def _j_channel_breakdown(m: dict) -> str:
    """Iter 57ee — Human-readable breakdown of the J-channel calc shown
    in the HOVER/blueprint preview. Example output:
        "5 wins × 14 + 1 patio × 22 + 2 garage × 32 + 100 eaves + 140 rakes = 326 LF ÷ 12.5 = 27 pcs"
    or when HOVER provided real per-window dims:
        "windows = 77 LF (5 individual dims) + 1 patio × 22 + 2 garage × 32 + 100 eaves + 140 rakes = 333 LF ÷ 12.5 = 27 pcs"
    """
    _, br = _j_channel_compute(m)
    return br


# =========================================================================
# VINYL-CONVENTIONS BATCH (3+4+5), RULED 2026-07-18 — region/context split.
# (3) J-channel derives as separate lines per application context
#     (window/door · rake/gable · soffit) and per product region where
#     accents exist, each carrying its region's product color; same split
#     for finish trim where context differs. Line naming states context +
#     region for the puller. PIN: no pooled J on multi-region jobs.
# (4) Starter is profile-specific: clap keeps 12'6"; shake regions derive
#     Pelican Bay Shake Starter #65516000 (own product + price line);
#     B&B/vertical gets NO starter — base treatment is J-channel, its own
#     context line in the B&B region's color. PINS: no starter on B&B
#     ever; shake starter never prices as clap.
# Split lines keep `base_item` = the catalog SKU so the estimate merge
# can inherit tier pricing for the new context-named rows.
# =========================================================================
_SHAKE_STARTER_SKU = "Pelican Bay Shake Starter"
_J_SKU = "3/4\" J-Channel Standard color"
_FT_SKU = "Finish Trim Standard color"
_NO_STARTER_FAMILIES = {"shake", "board_batten"}


def _region_split_active(m: dict) -> bool:
    per = m.get("_per_profile_sqft") or {}
    fams = {f for f, s in per.items() if isinstance(s, (int, float)) and s > 0}
    return len(fams) >= 2


def _region_context_lines(m: dict) -> list[dict]:
    per = {f: s for f, s in (m.get("_per_profile_sqft") or {}).items()
           if isinstance(s, (int, float)) and s > 0}
    base_lf = {f: float(v) for f, v in (m.get("_per_profile_base_lf") or {}).items()
               if isinstance(v, (int, float)) and v > 0}
    gable_lf = {f: float(v) for f, v in (m.get("_per_profile_gable_break_lf") or {}).items()
                if isinstance(v, (int, float)) and v > 0}
    out: list[dict] = []

    def line(name, base_item, qty, note):
        # LENGTH-CUT context rows (ruled 2026-07-29): ÷12.5 whole-stick
        # counts are the entire allowance — never take the waste field.
        out.append({"tab": "vinyl", "section": "Siding Accessories",
                    "name": name, "base_item": base_item,
                    "unit": "PCS", "qty": qty, "note": note,
                    "_waste_included": True})

    clap_fams = sorted(f for f in per if f not in _NO_STARTER_FAMILIES)
    clap_label = "/".join(clap_fams) if clap_fams else "lap"
    total_base = sum(base_lf.values())
    # SEND-129 (class C): a REFUSED starter must not read as 0 LF and
    # silently become the whole door deduction. The rows say REFUSED.
    if _key_refused(m, "starter_lf"):
        line(f"Starter — {clap_label} body", "Starter", 0,
             "REFUSED — starter_lf has no owned input upstream (perimeter "
             "refused or unattributed); this is not a zero, it is a "
             "refusal (SEND-129)")
        return out
    starter_lf = float(m.get("starter_lf") or 0)
    door_ded = max(0.0, total_base - starter_lf) if total_base > 0 else 0.0

    # ---- STARTER (profile-specific) ----
    if clap_fams:
        clap_base = sum(base_lf.get(f, 0.0) for f in clap_fams)
        if base_lf:
            net = max(0.0, clap_base - door_ded)
            qty = max(0, math.ceil(net / 12.5 - 1e-9)) if net > 0 else 0
            line(f"Starter — {clap_label} body", "Starter", qty,
                 f"clap starter 12'6\" (ruled): {clap_base:.0f} LF {clap_label} base − {door_ded:.0f} door deduction = {net:.0f} ÷ 12.5 = {qty} (door deduction assigned to the clap body)")
        else:
            qty = max(0, math.ceil(starter_lf / 12.5 - 1e-9))
            line(f"Starter — {clap_label} body", "Starter", qty,
                 f"older run without per-region base LF — clap starter from whole-house {starter_lf:.0f} LF; re-run measurement for the region split")
    if "shake" in per:
        s_lf = base_lf.get("shake", 0.0) + gable_lf.get("shake", 0.0)
        if s_lf > 0:
            qty = math.ceil(s_lf / 12.5 - 1e-9)
            line("Pelican Bay Shake Starter — shake region", _SHAKE_STARTER_SKU, qty,
                 f"#65516000, own product (never priced as clap starter): {s_lf:.0f} LF shake base/gable-break ÷ 12.5 = {qty} (12'6\" stick assumed — flag for ruling)")
        else:
            line("Pelican Bay Shake Starter — shake region", _SHAKE_STARTER_SKU, 0,
                 "⚠ shake region base LF unavailable on this run — verify by hand (#65516000; never priced as clap starter)")
    if "board_batten" in per:
        bb_lf = base_lf.get("board_batten", 0.0)
        if bb_lf > 0:
            qty = math.ceil(bb_lf / 12.5 - 1e-9)
            line("3/4\" J-Channel Standard color — B&B base", _J_SKU, qty,
                 f"B&B base treatment = J-channel, NO starter (ruled): {bb_lf:.0f} LF B&B base ÷ 12.5 = {qty} — carries the B&B region's product color")
        else:
            line("3/4\" J-Channel Standard color — B&B base", _J_SKU, 0,
                 "⚠ B&B base treatment = J-channel, NO starter (ruled) — B&B base LF unavailable on this run, verify by hand; carries the B&B region's product color")

    # ---- J-CHANNEL context split (no pooled J on multi-region — pinned) ----
    pcs_open, br_open = _j_channel_compute(m, include_rakes=False,
                                           include_eave_porch=False)
    if pcs_open > 0:
        line("3/4\" J-Channel Standard color — window/door", _J_SKU, pcs_open,
             f"{br_open} — {clap_label} body region color")
    rakes = float(m.get("rakes_lf") or 0)
    if rakes > 0:
        qty = math.ceil(rakes / 12.5 - 1e-9)
        gable_note = (f" — borders {'/'.join(sorted(gable_lf))} gable region color"
                      if gable_lf else f" — {clap_label} body region color")
        line("3/4\" J-Channel Standard color — rake/gable", _J_SKU, qty,
             f"{rakes:.0f} LF rakes ÷ 12.5 = {qty}{gable_note}")
    ep_lf, ep_br = _eave_porch_j_lf(m)
    if ep_lf > 0:
        qty = math.ceil(ep_lf / 12.5 - 1e-9)
        line("3/4\" J-Channel Standard color — eave/porch soffit channel",
             _J_SKU, qty,
             f"{ep_br} = {ep_lf:.0f} LF ÷ 12.5 = {qty} — {clap_label} body region color")

    # ---- FINISH TRIM context split ----
    eaves = float(m.get("eaves_lf") or 0)
    if eaves > 0:
        qty = math.ceil(eaves / 12.5 - 1e-9)
        line("Finish Trim Standard color — eave run", _FT_SKU, qty,
             f"{eaves:.0f} LF eaves ÷ 12.5 = {qty}")
    win_sills = _finish_trim_sill_lf(m)
    if win_sills > 0:
        qty = math.ceil(win_sills / 12.5 - 1e-9)
        line("Finish Trim Standard color — window sills", _FT_SKU, qty,
             f"{win_sills:.0f} LF window sills ÷ 12.5 = {qty}")
    return out


def _porch_geom(m: dict) -> dict:
    """PORCH SHAPE DISCIPLINE (Howard ruled 2026-08-07): AN AREA DOES NOT
    DETERMINE A SHAPE. Never back dimensions out of an area. Real dims
    govern when a door holds them; otherwise FLAG and use the DISCLOSED
    MINIMUM (square-assumed) — never fabricate a rectangle.
    Sources, best first:
      1. contractor-entered porch dims (Job-Info entries, width×length)
      2. porch-flagged roof plane with eave+rake reads (eave = fascia
         side, rakes = the two sides)
      3. area only → square MINIMUM, flagged
    Returns {sqft, perimeter_lf, wall_lf, basis, text}: perimeter is the
    ceiling-receiving channel (Soffit-J line, full perimeter); wall_lf is
    the wall-abutting length (wall-J line only)."""
    sqft = float(m.get("porch_ceiling_sqft") or 0)
    real = [(float(p.get("width_ft") or 0), float(p.get("length_ft") or 0))
            for p in (m.get("_porch_dims") or []) if isinstance(p, dict)
            and float(p.get("width_ft") or 0) > 0
            and float(p.get("length_ft") or 0) > 0]
    if real:
        perim = sum(2.0 * (w + l) for w, l in real)
        # WALL SIDE FROM GEOMETRY (Howard ruled 2026-08-10 send 2): never
        # assume the longer dim abuts the house — right on Boni
        # (16'6"×6'0") BY LUCK, wrong on any deeper-than-wide porch. The
        # porch roof plane's eave (the fascia side) names the wall run; a
        # dim matching it (±1') is the wall side. UNDETERMINABLE → FLAG
        # and take the DISCLOSED MINIMUM (shorter side), never a guess.
        eave = 0.0
        for p in (m.get("_roof_planes") or []):
            if isinstance(p, dict) and p.get("is_porch"):
                try:
                    eave = float(p.get("eave_lf") or 0)
                except (TypeError, ValueError):
                    eave = 0.0
                break
        wall = 0.0
        undetermined = False
        parts_txt = []
        for w, l in real:
            if abs(w - l) <= 0.5:
                side = w  # square-ish — either side is the wall side
            elif eave > 0 and abs(w - eave) <= 1.0 and abs(l - eave) > 1.0:
                side = w
            elif eave > 0 and abs(l - eave) <= 1.0 and abs(w - eave) > 1.0:
                side = l
            else:
                side = min(w, l)
                undetermined = True
            wall += side
            parts_txt.append(f"{side:g}' wall × {w + l - side:g}' deep")
        basis = "real_dims_wall_undetermined" if undetermined else "real_dims"
        txt = " + ".join(parts_txt)
        if undetermined:
            txt += (" — WALL SIDE UNDETERMINED (no porch roof plane names "
                    "the fascia run): shorter side taken as the disclosed "
                    "minimum; mark the actual house-abutting side")
        return {"sqft": sqft, "perimeter_lf": perim, "wall_lf": wall,
                "basis": basis, "text": txt}
    for p in (m.get("_roof_planes") or []):
        if isinstance(p, dict) and p.get("is_porch"):
            try:
                pw = float(p.get("porch_width_ft") or 0)
                pd = float(p.get("porch_depth_ft") or 0)
            except (TypeError, ValueError):
                pw = pd = 0.0
            if pw > 0 and pd > 0:
                # printed floor-plan dims — width runs along the house wall
                return {"sqft": sqft, "perimeter_lf": 2.0 * (pw + pd),
                        "wall_lf": pw, "basis": "porch_plane",
                        "text": f"{pw:g}' along the wall × {pd:g}' deep (printed porch dims)"}
            e = float(p.get("eave_lf") or 0)
            r = float(p.get("rake_lf") or 0)
            if e > 0 and r > 0:
                d = r / 2.0
                return {"sqft": sqft, "perimeter_lf": 2.0 * (e + d),
                        "wall_lf": e, "basis": "porch_plane",
                        "text": f"{e:g}' eave × {d:g}' side (porch roof plane)"}
            break
    if sqft > 0:
        side = math.sqrt(sqft)
        return {"sqft": sqft, "perimeter_lf": 4.0 * side, "wall_lf": side,
                "basis": "square_minimum", "text": f"√{sqft:g}"}
    return {"sqft": 0.0, "perimeter_lf": 0.0, "wall_lf": 0.0,
            "basis": "none", "text": ""}


def _porch_soffit_j_lf(m: dict) -> tuple[float, str]:
    """PORCH-J ASSEMBLY SPLIT (Howard ruled 2026-08-07): the CEILING-
    receiving channel prints on the SOFFIT-J line at FULL PERIMETER; the
    wall J beneath prints on the WALL-J line at wall-abutting length only
    (see _eave_porch_j_lf). Vinyl/Ascend only — LP carries neither."""
    g = _porch_geom(m)
    if g["perimeter_lf"] <= 0:
        return 0.0, ""
    if g["basis"] == "real_dims":
        br = (f"{g['perimeter_lf']:.0f} porch ceiling channel — FULL "
              f"PERIMETER 2×(w+d), real dims {g['text']}")
    elif g["basis"] == "porch_plane":
        br = (f"{g['perimeter_lf']:.0f} porch ceiling channel — FULL "
              f"PERIMETER 2×(w+d), {g['text']}")
    else:
        br = (f"{g['perimeter_lf']:.0f} porch ceiling channel — FULL "
              f"PERIMETER MINIMUM, square-assumed 4×{g['text']} — real "
              "dims not held, FLAG: an area does not determine a shape "
              "(ruled 2026-08-07)")
    return g["perimeter_lf"], br + " (split ruled 2026-08-07: ceiling channel on the Soffit-J line)"


def _eave_porch_j_lf(m: dict) -> tuple[float, str]:
    """EAVE/PORCH-J, WALL-J SIDE (Howard ruled 2026-08-05; ASSEMBLY SPLIT
    ruled 2026-08-07): eave soffit panels tuck into a wall-side receiving
    channel, and the porch carries a wall J beneath its ceiling channel —
    WALL-ABUTTING LENGTH ONLY on this line. The ceiling-receiving channel
    itself moved to the SOFFIT-J line at full perimeter (see
    _porch_soffit_j_lf). NEVER LP SmartSide (different soffit/trim
    system; no eave-J). PORCH IDENTIFICATION is per-door and NEVER
    silent: real dims when held; a square-assumed MINIMUM is flagged —
    an area does not determine a shape (ruled 2026-08-07)."""
    eaves = float(m.get("eaves_lf") or 0)
    g = _porch_geom(m)
    parts: list[str] = []
    total = 0.0
    if eaves > 0:
        total += eaves
        parts.append(f"{eaves:.0f} eave wall-channel")
    if g["wall_lf"] > 0:
        total += g["wall_lf"]
        if g["basis"] == "real_dims":
            parts.append(
                f"{g['wall_lf']:.0f} porch wall-J — wall-abutting side only "
                f"(real dims {g['text']}, longer side taken as the wall "
                "side — verify); ceiling channel moved to the Soffit-J "
                "line (split ruled 2026-08-07)")
        elif g["basis"] == "porch_plane":
            parts.append(
                f"{g['wall_lf']:.0f} porch wall-J — wall-abutting side only "
                f"({g['text']}); ceiling channel moved to the Soffit-J "
                "line (split ruled 2026-08-07)")
        else:
            parts.append(
                f"{g['wall_lf']:.0f} porch wall-J MINIMUM — square-assumed "
                f"{g['text']}; real dims not held, FLAG: verify the "
                "wall-side length (an area does not determine a shape — "
                "ruled 2026-08-07); ceiling channel moved to the Soffit-J line")
    else:
        parts.append(
            "no porch ceiling identified on this read — if the house "
            "has one, its wall-J is NOT in this count (flag, "
            "never silent)")
    return total, " + ".join(parts) + \
        " (eave/porch-J — ruled 2026-08-05, vinyl/Ascend only)"


def _j_channel_compute(m: dict, include_rakes: bool = True,
                       include_eave_porch: bool = True) -> tuple[int, str]:
    """Howard's J-channel formula (Iter 78 — eaves moved to Finish Trim):

        pcs = ceil( (window + patio + garage perimeter + rakes) / 12.5 )

    Eaves used to be added here, but that double-counted the eave run
    against Finish Trim (which already includes eaves). Eaves now belong
    exclusively to Finish Trim; J-channel covers openings + rake
    terminations only.

    Garage doors are now INCLUDED in the J-channel count (most
    contractors wrap vinyl J around the garage opening even with a
    brickmould surround, since the head + jambs still receive panels).

    Window+patio perimeter is computed best-signal-first:
      1) Sum actual perimeters from `windows[]` (individual dims) if
         HOVER extracted them. Most reliable.
      2) Else: use HOVER's lumped `opening_perimeter_lf` minus the
         entry-door + garage-door allowances (garage gets added back).
      3) Else: count-based estimate (window_count × 14 + patio × 22).
         Safety net for HOVER reports that don't print the opening
         perimeter at all.

    Returns (pcs, breakdown_string).
    """
    entry_n = float(m.get("entry_door_count") or 0)
    garage_n = float(m.get("garage_door_count") or 0)
    patio_n = float(m.get("patio_door_count") or 0)
    win_count = float(m.get("window_count") or 0)
    opening_perim = float(m.get("opening_perimeter_lf") or 0)
    windows = m.get("windows") or []
    rakes = (float(m.get("rakes_lf") or 0)) if include_rakes else 0.0
    # INTEGRAL-J WINDOWS (Howard ruled 2026-08-05, Boni ruling 3): the
    # windows carry their own J — their perimeter comes OUT of the wall-J
    # math. Patio/garage openings still receive J.
    integral_j = bool(m.get("_windows_integral_j"))

    parts: list[str] = []  # human-readable breakdown segments
    if integral_j:
        win_patio_perim = patio_n * PATIO_DOOR_PERIM_LF
        parts.append("windows = 0 LF (integral-J windows — ruled 2026-08-05, window perimeter excluded)")
        if patio_n:
            parts.append(f"{int(patio_n)} patio × {int(PATIO_DOOR_PERIM_LF)}")
    elif windows:
        win_perim_in = sum(
            2 * (float(w.get("width_in") or 0) + float(w.get("height_in") or 0))
            for w in windows
        )
        win_lf = win_perim_in / 12.0
        win_patio_perim = win_lf + (patio_n * PATIO_DOOR_PERIM_LF)
        parts.append(f"windows = {win_lf:.1f} LF ({len(windows)} individual dims)")
        if patio_n:
            parts.append(f"{int(patio_n)} patio × {int(PATIO_DOOR_PERIM_LF)}")
    elif opening_perim > 0:
        win_patio_perim = max(
            0.0,
            opening_perim
            - entry_n * ENTRY_DOOR_PERIM_LF
            - garage_n * GARAGE_DOOR_PERIM_LF,
        )
        sub_str = f"{opening_perim:.0f} HOVER perim"
        if entry_n:
            sub_str += f" − {int(entry_n)} entry × {int(ENTRY_DOOR_PERIM_LF)}"
        if garage_n:
            sub_str += f" − {int(garage_n)} garage × {int(GARAGE_DOOR_PERIM_LF)}"
        parts.append(f"({sub_str}) = {win_patio_perim:.0f} LF window+patio")
    else:
        win_patio_perim = (
            win_count * WINDOW_PERIM_LF_FALLBACK
            + patio_n * PATIO_DOOR_PERIM_LF
        )
        parts.append(f"{int(win_count)} wins × {int(WINDOW_PERIM_LF_FALLBACK)}")
        if patio_n:
            parts.append(f"{int(patio_n)} patio × {int(PATIO_DOOR_PERIM_LF)}")
    if garage_n:
        parts.append(f"{int(garage_n)} garage × {int(GARAGE_DOOR_PERIM_LF)}")
    if rakes:
        parts.append(f"{rakes:.0f} rakes")
    ep_lf, ep_br = _eave_porch_j_lf(m) if include_eave_porch else (0.0, "")
    if ep_br:
        parts.append(ep_br)

    total_lf = (
        win_patio_perim
        + garage_n * GARAGE_DOOR_PERIM_LF
        + rakes
        + ep_lf
    )
    if total_lf <= 0:
        return 0, "no openings + no rakes → 0 pcs"
    pcs = int(math.ceil(total_lf / 12.5 - 1e-9))
    breakdown = f"{' + '.join(parts)} = {total_lf:.0f} LF ÷ 12.5 = {pcs} pcs"
    return pcs, breakdown


def _frieze_540_pcs(m: dict) -> int:
    """Q10 (ruled 2026-07-27): frieze LF consumed — per-segment ÷16 (Q16)."""
    lvl = float(m.get("level_frieze_lf") or 0)
    slp = float(m.get("sloped_frieze_lf") or 0)
    return (math.ceil(lvl / 16.0 - 1e-9) if lvl > 0 else 0) + \
           (math.ceil(slp / 16.0 - 1e-9) if slp > 0 else 0)


def _isc_540_pcs(m: dict) -> int:
    """Q12/Q13 (ruled 2026-07-27): ISC default = 540-4"; PER-CORNER
    whole-stick round-up, min 1 pc per corner (pooling retired)."""
    ic = int(m.get("inside_corner_count") or 0)
    ilf = float(m.get("inside_corner_lf") or 0)
    if ic <= 0 and _key_refused(m, "inside_corner_lf"):
        return 0      # refused, and the takeoff carries the refusal
    if ic > 0:
        per_h = (ilf / ic) if ilf > 0 else 9.5
        return ic * max(1, math.ceil(per_h / 16.0 - 1e-9))
    if ilf > 0:
        return math.ceil(ilf / 16.0 - 1e-9)
    return 0


def _osc_corner_heights(m: dict):
    """Per-corner trim heights when a door read them. None entries are
    undimensioned corners that KEEP THEIR FLAG (ruled 2026-08-06) —
    never averaged, never silently defaulted."""
    hs = m.get("_osc_corner_heights_ft")
    if not isinstance(hs, list) or not hs:
        return None
    out = []
    for h in hs:
        try:
            v = float(h) if h is not None else 0.0
        except (TypeError, ValueError):
            v = 0.0
        out.append(v if v > 0 else None)
    return out if any(v for v in out if v) else None


def _osc_per_corner_pcs(m: dict, stick_ft: float):
    """STOP AVERAGING CORNER HEIGHTS (Howard ruled 2026-08-06): when a
    door read per-corner dimensions, each corner takes ceil(its OWN trim
    height / stick), min 1 — the stick length is the threshold at which
    a corner needs a second piece. An undimensioned corner holds min 1
    stick and keeps its flag in the note. Returns None when no
    per-corner heights exist (pooled/count fallbacks apply unchanged)."""
    hs = _osc_corner_heights(m)
    if hs is None:
        return None
    return sum(max(1, math.ceil(h / stick_ft - 1e-9)) if h else 1 for h in hs)


def _osc_heights_note(m: dict, stick_ft: float) -> str:
    hs = _osc_corner_heights(m) or []
    dim = [h for h in hs if h]
    und = len(hs) - len(dim)
    two_plus = sum(1 for h in dim if h > stick_ft + 1e-9)
    src = {
        "blueprint_dimensioned": "the dimensioned elevations (blueprint door)",
        "hover_callout": "the drawn corner callouts (Hover door)",
        "photo_ai": "photo AI ESTIMATE — VERIFY before ordering, never taped",
    }.get(str(m.get("_osc_heights_source") or ""), "the door's per-corner read")
    hs_txt = ", ".join((f"{h:g}'" if h else "?") for h in hs)
    txt = (f"{len(hs)} corner(s), per-corner sticks off {src} [{hs_txt}] — "
           f"each corner takes its TALLER wall, ceil(height ÷ {stick_ft:g}') "
           f"min 1; {stick_ft:g}' stick is the threshold for a second piece"
           + (f" — {two_plus} corner(s) take 2+" if two_plus else ""))
    if und:
        txt += (f" — {und} corner(s) UNDIMENSIONED: held at 1 stick, flag "
                "stands (never averaged, never silently defaulted)")
    return txt


def _osc_lp_pcs(m: dict) -> int:
    """Q13 (ruled 2026-07-27): OSC per-corner whole-stick round-up, min 1
    pc per corner; pooled ÷16 only when the corner count is unavailable.
    TALL CORNERS (never-average rule sealed 2026-07-28): taped heights
    over one 16' stick take ceil(h/16) each — a material-governing
    dimension is NEVER averaged (261 Haugh: 18'5" corner = 2 sticks that
    the 10' average hid). Identical math to the package emitter, pinned."""
    oc = int(m.get("outside_corner_count") or 0)
    olf = float(m.get("outside_corner_lf") or 0)
    # SEND-129 (class C): a refused corner LF with no count is a refusal,
    # and the takeoff carries it — never a quiet 0 pieces.
    if oc <= 0 and _key_refused(m, "outside_corner_lf"):
        return 0
    tall = [float(h) for h in (m.get("_osc_tall_corners_ft") or []) if h]
    # PER-CORNER HEIGHTS (Howard ruled 2026-08-06): a door that read each
    # corner's own dimension governs — taped heights (human) still win.
    if not tall:
        per = _osc_per_corner_pcs(m, 16.0)
        if per is not None:
            return per
    if oc > 0 and olf > 0:
        k = min(len(tall), oc)
        rest_cnt = oc - k
        rest_lf = max(olf - sum(tall[:k]), 0.0)
        q_rest = rest_cnt * max(1, math.ceil((rest_lf / rest_cnt) / 16.0 - 1e-9)) if rest_cnt else 0
        q_tall = sum(max(1, math.ceil(h / 16.0 - 1e-9)) for h in tall[:k])
        return q_rest + q_tall
    if olf > 0:
        return math.ceil(olf / 16.0 - 1e-9)
    return 0


def _soffit_total_split(m: dict) -> tuple[float, float]:
    """Q14a (ruled 2026-07-27): a measured Hover soffit TOTAL governs over
    the overhang fallback. Split proportionally to eave vs rake run LF
    (eaves vent, rakes close — standing convention). Returns
    (vented_sqft, closed_sqft); (0, 0) when no measured total."""
    total = float(m.get("soffit_sqft") or 0)
    if total <= 0:
        return 0.0, 0.0
    e = float(m.get("eaves_lf") or 0)
    r = float(m.get("rakes_lf") or 0)
    if e + r <= 0:
        return total, 0.0
    return round(total * e / (e + r), 1), round(total * r / (e + r), 1)


def _batten_spacing_in(m: dict) -> int:
    try:
        s = int(m.get("_batten_spacing_in") or 0)
    except (TypeError, ValueError):
        s = 0
    return s if s in lp_formulas.VALID_BATTEN_SPACINGS_IN \
        else lp_formulas.DEFAULT_BATTEN_SPACING_IN


def _bb_batten_sticks(m: dict) -> int:
    bb = float((m.get("_per_profile_sqft") or {}).get("board_batten") or 0) \
        + float((m.get("_per_profile_sqft") or {}).get("vertical") or 0)
    if bb <= 0 or not lp_formulas.is_enabled():
        return 0
    return lp_formulas.board_batten_batten_pieces(
        bb, spacing_in=_batten_spacing_in(m),
        wall_height_ft=float(m.get("_bb_wall_height_ft") or 0))


def _openings_ded_note(m: dict) -> str:
    """SEND-115 RULING 1 (2026-08-23): the deduction prints on the
    takeoff — what was deducted AND what refused. Aggregate only until
    a placement read exists."""
    d = m.get("_openings_deduction")
    if not d:
        return ""
    if d.get("deduction_refused"):
        # SEND-116 ITEM 1: a refused deduction NAMES both the openings
        # and why — never a partial gross minus a whole-house deduction.
        if d.get("refusal_class") == "openings_exceed_gross":
            out = (f" · OPENINGS DEDUCTION REFUSED — openings "
                   f"{round(d['openings_sqft_read'], 1):g} ft² meet or "
                   f"exceed the derived gross "
                   f"{round(d['gross_sqft'], 1):g} ft² — reads disagree; "
                   f"nothing deducted")
        else:
            faces = ", ".join(d.get("faces_refused") or []) or "?"
            out = (f" · OPENINGS DEDUCTION REFUSED — "
                   f"{round(d['openings_sqft_read'], 1):g} ft² of openings "
                   f"read, but face(s) {faces} refused and an opening may "
                   f"only deduct from a gross that includes its face; no "
                   f"placement exists to scope the deduction (openings "
                   f"unplaced); nothing deducted")
    else:
        out = (f" · OPENINGS DEDUCTED {round(d['deducted_sqft'], 1):g} ft² "
               f"— full area, no threshold (gross "
               f"{round(d['gross_sqft'], 1):g} − openings = "
               f"{round(d['net_sqft'], 1):g} ft²)")
    groups: dict = {}
    for r in d.get("refused") or []:
        k = ("window" if r.get("kind") == "windows" else "door",
             r.get("why") or "refused")
        groups.setdefault(k, []).append(str(r.get("mark") or "?"))
    for (kind, why), marks in groups.items():
        out += (f". {len(marks)} {kind} mark{'s' if len(marks) != 1 else ''}"
                f" refused ({', '.join(marks)}) — {why}")
    if d.get("deduction_refused"):
        return out
    if groups:
        out += ". DEDUCTION INCOMPLETE"
    else:
        out += ". Deduction complete — every schedule count read"
    out += ". Aggregate only — not attributed per face (openings unplaced)"
    return out


def _batten_note(m: dict) -> str:
    """Batten statement — names the spacing, and NAMES THE DELTA
    explicitly when the trade-spec spacing moves off the 12\" default
    (Howard ruled 2026-07-29)."""
    s = _batten_spacing_in(m)
    base = (f"Batten strips — wall area ÷ ({s}\"/12) + 1 run × wall height "
            f"when taped, {s}\" on-center (trade spec, default 12\"), "
            "16' stock, no waste")
    if s == lp_formulas.DEFAULT_BATTEN_SPACING_IN:
        return base
    bb = float((m.get("_per_profile_sqft") or {}).get("board_batten") or 0) \
        + float((m.get("_per_profile_sqft") or {}).get("vertical") or 0)
    h = float(m.get("_bb_wall_height_ft") or 0)
    at_default = lp_formulas.board_batten_batten_pieces(
        bb, spacing_in=lp_formulas.DEFAULT_BATTEN_SPACING_IN, wall_height_ft=h)
    at_spec = lp_formulas.board_batten_batten_pieces(
        bb, spacing_in=s, wall_height_ft=h)
    return (f"{base} — DELTA vs 12\" default: {at_spec - at_default:+d} pcs "
            f"({at_spec} @ {s}\" vs {at_default} @ 12\")")


# Q8 (ruled 2026-07-27): per-estimate COLOR-TIER selector re-lands
# derivations — Standard-color rows swap to their Architectural twins.
# RETIRED 2026-08-02: the single-tier `_apply_color_tier(lines, tier)`
# swapped EVERY row to one estimate-wide tier. Howard ruled PER-ROW —
# each row follows its own color picker (vinyl_color_tiers.
# apply_row_color_tiers, ONE copy). The dropdown control is gone.


# SALES UNIT (Howard ruled 2026-07-31, landed after his price pages):
# wrap underlayment sells by the ROLL. TWO constants — RainDrop and House
# Wrap cover different squares per roll; never a shared "wrap roll" number.
HOUSE_WRAP_SQ_PER_ROLL = 9.00
RAINDROP_SQ_PER_ROLL = 11.25

HOVER_MAPPING_SPEC = [
    # =====================================================================
    # HEADLINE SIDING — one per tab. We use HOVER's "+ Openings < 20ft²
    # +10%" row (from SIDING WASTE TOTALS) so the small-opening adder is
    # already baked in. Raw facades area is the fallback.
    #
    # Iter 78z (P1.2) — When measurements carry a multi-profile breakdown
    # (`_per_profile_sqft` has >1 family — Lap + Shake + B&B etc.), the
    # default single-SKU siding rows below are SKIPPED in `_build_lines`
    # and replaced with per-profile lines via `_profile_siding_lines()`.
    # The `_is_default_siding: True` marker tags these rows for that
    # skip logic. Single-profile (or no breakdown) houses still hit the
    # default mapping with the small-opening adder baked in.
    # =====================================================================
    {
        "tabs": ["vinyl"],
        "section": "Vinyl Siding",
        "item": "Charter Oak Standard color Dutch Lap 4.5\" .046",
        "unit": "SQ",
        "extract": lambda m: round(
            ((m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0)) / 100.0,
            1,
        ),
        # BASIS NAMED ON EVERY NOTE (ruled): the +10% claim prints ONLY
        # when the HOVER waste-totals row actually fed the number. A
        # blueprint read carries no such row — its note says what the
        # number is: gross area, openings kept, no waste inside.
        "note": lambda m: (
            (("Wall area ÷ 100 = SQ" + _openings_ded_note(m)
              + "; no waste inside this number, the Waste % field is the only waste")
             if m.get("_openings_deduction")
             else ("From HOVER 'SIDING WASTE TOTALS → + Openings < 20ft² +10%'"
                   if (m.get("siding_with_openings_sqft") or 0) > 0
                   else "Gross wall area ÷ 100 = SQ — no openings read to deduct (deduction ruled 2026-08-23); no waste inside this number, the Waste % field is the only waste"))
            # A DEFAULTED PROFILE PRINTS AS DEFAULTED (Howard ruled
            # 2026-08-09): this row is the spec default, not a choice.
            + " · PROFILE DEFAULTED — not a choice; pick the profile on the estimate"
        ),
        "_is_default_siding": True,
    },
    {
        "tabs": ["ascend"],
        "section": "Ascend Cladding",
        "item": "Ascend Composite Lap Siding 7\"",
        "unit": "SQ",
        "extract": lambda m: round(
            ((m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0)) / 100.0,
            1,
        ),
        "note": lambda m: ("Siding sqft ÷ 100 = SQ — default Ascend profile "
                           "(change via edit)") + _openings_ded_note(m),
        "_is_default_siding": True,
    },
    {
        "tabs": ["lp_smart"],
        "section": "LP Smart Siding",
        "item": '38 Series Lap 3/8" x 8" x 16\'',
        "unit": "PCS",
        # AREA GOOD, SINGLE APPLICATION (Howard ruled 2026-07-29 — the
        # pre-pick default-lap DOUBLE-BAKE fix): when the rebuild carries
        # a positive _waste_pct the book bakes it INSIDE, so the flag opts
        # this row OUT of the tab bake; import drafts (_waste_pct 0) leave
        # the field to the ONE bake. Callable — evaluated per build.
        "waste_included": lambda m: (
            float(m["_waste_pct"]) if m.get("_waste_pct") is not None else 0.0
        ) > 0,
        "extract": lambda m: (
            # SEALED (Howard, ruled 2026-07-19): book counter convention —
            # 11 pcs/square. PDF 9.17 divisor RETIRED for 38 Series lap
            # (kept as reference pedigree in LAP_PROFILES). NO baked
            # waste: the waste applied is the surfaced _waste_pct only
            # (contractor's estimate field, or the Hover ruled default) —
            # no silent constant.
            lp_formulas.lap_pieces_book(
                (m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0),
                waste=(float(m["_waste_pct"]) if m.get("_waste_pct") is not None else 0.0),
            )
            if lp_formulas.is_enabled()
            else max(
                1,
                round(((m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0)) * 0.11),
            )
        ),
        "note": lambda m: (
            "38 Lap: ceil(sqft ÷ 100 × 11 × (1+waste)) — 11 pcs per square; waste = contractor's % field, not baked into the formula"
            if lp_formulas.is_enabled()
            else "11 PCS per Sq (LP 8\" lap exposure); sqft × 0.11 rounded"
        ) + _openings_ded_note(m),
        "_is_default_siding": True,
    },
    # Iter 68 (2026-06-22) — LP starter-pack auto-fill so HOVER imports
    # don't leave the LP tab empty. Note: 6" Lap is intentionally NOT
    # auto-filled — it's an ALTERNATIVE to 8" Lap, not additive. If the
    # contractor wants 6" instead, they zero out 8" and type the 6" qty
    # (or we can build a one-tap "swap to 6"" button later).
    # Iter 68a: 6" Lap auto-fill removed after Howard caught the double-
    # count in preview. Row stays in the catalog at $26.45 PCS (whole-sale)
    # but qty starts at 0.
    # 440 Series Trim — SEALED CONVENTIONS GOVERN THE TAB (ruled 2026-07-24,
    # Casile close-out): the pre-sealed (eaves+rakes)÷16 × %waste formula
    # RETIRED. 4/4"×4" = inside-corner pooling; 4/4"×8" = fascia + rake
    # runs (Letrick width precedent, CONTRACTOR-SPEC confirmed). Whole-stick
    # rounding is the entire allowance — no % waste on stick counts.
    # Q12 (ruled 2026-07-27): the 440 4/4"×4" ISC tab row RETIRED — 540
    # 5/4"×4" is the LP ISC default; ISC sticks land on the 540 row below.
    {
        "tabs": ["lp_smart"],
        "section": "LP SmartSide Trim",
        "item": '440 Series Trim 4/4" x 8" x 16\'',
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: math.ceil(
            ((m.get("eaves_lf") or 0) + (m.get("rakes_lf") or 0)) / 16
         - 1e-9),
        "note": lambda m: (
            f"Fascia {float(m.get('eaves_lf') or 0):g} LF + rake {float(m.get('rakes_lf') or 0):g} LF ÷ 16, "
            "whole-stick count is the entire allowance; 8\" width is contractor-spec"
        ),
    },
    # 540 Series Trim 5/4" x 4" — window / entry door / patio / garage trim
    # wrap. Per-opening trim LF mirrors the J-channel formula divisors
    # Howard set in Iter 57ee: 14 ft per window, 21 ft per entry, 25 ft
    # per patio (sliding glass), 32 ft per garage door. Sum ÷ 16 (board).
    # Iter 78ab — when LP_AI_FORMULAS_V1 is enabled AND shakes appear in
    # the per-profile breakdown, add Howard's 540 belly-band bump per
    # LP PDF guidance ("recommends 540 Series for shake reveals 7"–10"").
    {
        "tabs": ["lp_smart"],
        "section": "LP SmartSide Trim",
        "item": '540 Series Trim 5/4" x 4" x 16\'',
        "unit": "PCS",
        # Whole-stick rounding is the entire allowance (ruled 2026-07-24).
        "waste_included": True,
        # RULED 2026-07-17 (261 Haugh shakedown): measured opening
        # perimeter governs when the report supplies it — doors trim
        # 3 sides (deduct bottoms: garage 16', entry 3', SGD 8' each).
        # Per-opening constants remain the fallback (no schedule).
        "extract": lambda m: max(
            1,
            (
                math.ceil(max(0.0,
                    float(m.get("opening_perimeter_lf") or 0)
                    - 16.0 * (m.get("garage_door_count") or 0)
                    - 3.0 * (m.get("entry_door_count") or 0)
                    - 8.0 * (m.get("patio_door_count") or 0)
                ) / 16 - 1e-9)
                if (m.get("opening_perimeter_lf") or 0) > 0
                else math.ceil((
                    (m.get("window_count") or 0) * 14
                    + (m.get("entry_door_count") or 0) * 21
                    + (m.get("patio_door_count") or 0) * 25
                    + (m.get("garage_door_count") or 0) * 32
                ) / 16 - 1e-9)
            )
            # Q10 (ruled 2026-07-27): frieze CONSUMED — per-segment ÷16 (Q16)
            + _frieze_540_pcs(m)
            # Q12/Q13 (ruled 2026-07-27): ISC default = 540-4"; per-corner
            # whole-stick round-up, min 1 pc per corner
            + _isc_540_pcs(m)
            + (
                lp_formulas.shake_540_series_bump(
                    float((m.get("_per_profile_sqft") or {}).get("shake") or 0)
                )
                if lp_formulas.is_enabled()
                else 0
            ),
        ),
        "note": lambda m: (
            (
                (
                    f"Measured opening perimeter {float(m.get('opening_perimeter_lf') or 0):g} LF "
                    f"− door bottoms (garage {(m.get('garage_door_count') or 0)}×16' + entry {(m.get('entry_door_count') or 0)}×3' "
                    f"+ SGD {(m.get('patio_door_count') or 0)}×8') ÷ 16 — doors trim 3 sides"
                )
                if (m.get("opening_perimeter_lf") or 0) > 0
                else "Window/entry/patio/garage perimeter wrap ÷ 16"
            )
            + (f" + frieze {float(m.get('level_frieze_lf') or 0):g}+{float(m.get('sloped_frieze_lf') or 0):g} LF per-segment = {_frieze_540_pcs(m)}"
               + (" (TYPED toggle — frieze LF from measured eave/rake runs, photo door)"
                  if _staging_is_fillin(m, "frieze") else "")
               if _frieze_540_pcs(m) else "")
            + (f" + ISC {int(m.get('inside_corner_count') or 0)} corner(s) per-corner round-up = {_isc_540_pcs(m)}"
               if _isc_540_pcs(m) else "")
            + (
                f" + {lp_formulas.shake_540_series_bump(float((m.get('_per_profile_sqft') or {}).get('shake') or 0))} shake belly-band pcs (LP PDF)"
                if lp_formulas.is_enabled()
                   and float((m.get("_per_profile_sqft") or {}).get("shake") or 0) > 0
                else ""
            )
        ),
    },
    # RULED (2026-07-16, LPZB0884): batten LF = wall_area ÷ spacing(ft)
    # + 1 run × wall height per wall; pcs = ceil(LF ÷ 16), no waste on
    # battens; spacing must divide 48. Ingest path lacks per-wall heights
    # so the +height term is 0 here. Spacing became a TRADE SPEC 2026-07-29
    # (see the row comment below).
    # RULED (2026-07-29): spacing is a TRADE SPEC — 12/16/24 o.c., 12"
    # default (8" retired; the 3 Degree 465 is a second opinion, not a
    # target). batten LF = wall_area ÷ spacing(ft) + 1 run × wall height
    # per wall; pcs = ceil(LF ÷ 16), no waste on battens; spacing must
    # divide 48. HOVER-SCHEDULE numbers feed this — never drawn reads.
    {
        "tabs": ["lp_smart"],
        "section": "LP SmartSide Trim",
        "item": '190 Series Trim 19/32" x 3" x 16\'',
        "unit": "PCS",
        # "no waste on battens" is the sealed rule — the tab bake violated
        # the row's own note until 2026-07-24.
        "waste_included": True,
        "extract": lambda m: (_bb_batten_sticks(m) if lp_formulas.is_enabled() else 0),
        "note": _batten_note,
    },
    # .019 Coil LP AUTO-ADD RETIRED (iter97 composition ruling, 2026-07-12):
    # an auto-add is DERIVED composition — coil on an LP-native derived
    # takeoff is a cross-domain composition bug. The row remains in the
    # LP Siding Accessories catalog as a flagged cross_domain_manual_add
    # exception; contractors add it by hand when a job needs flashing.
    # (Iter 68/79b mapping superseded on the lp_smart tab only.)
    # Q15 (SEALED 2026-07-27, 3 Degree Rd): touch-up = 1 kit per 11 SQ per
    # color (flat per-job constant retired). Colors unknown at import → 1.
    {
        "tabs": ["lp_smart"],
        "section": "LP Siding Accessories",
        "item": 'Touch up kits',
        "unit": "PCS",
        "extract": lambda m: max(1, round(
            ((m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0)) / 100.0 / 11.0)) \
            * max(1, int(m.get("_lp_color_count") or 1)),
        "note": lambda m: (
            f"1 kit per 11 SQ per color: "
            f"{((m.get('siding_with_openings_sqft') or m.get('siding_sqft') or 0)) / 100.0:g} SQ ÷ 11 — "
            "color count reads the estimate's Job Info selections; unknown at import → 1"
            + (f" · × {int(m.get('_lp_color_count'))} selected colors"
               if int(m.get("_lp_color_count") or 1) > 1 else "")),
    },
    # CAULK FAMILY-SHAPED (register #5 ruled 2026-07-28) — flat 2/job
    # RETIRED everywhere. B&B keeps the sealed 1 tube per 23 batten sticks
    # (Q15 2026-07-27); LP non-B&B = 1 tube per SQUARE (SmartSide butt
    # joints take sealant).
    {
        "tabs": ["lp_smart"],
        "section": "LP Siding Accessories",
        "item": 'OSI Quad Max Caulking',
        "unit": "Tube",
        "extract": lambda m: (
            max(1, math.ceil(_bb_batten_sticks(m) / 23.0 - 1e-9))
            if _bb_batten_sticks(m) > 0
            else max(1, math.ceil(
                ((m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0)) / 100.0 - 1e-9))
        ),
        "note": lambda m: (
            f"B&B: 1 tube per 23 batten sticks — "
            f"{_bb_batten_sticks(m)} sticks ÷ 23"
            if _bb_batten_sticks(m) > 0
            else (
                f"LP non-B&B: 1 tube per SQUARE — SmartSide butt joints take sealant "
                f""
                f"{((m.get('siding_with_openings_sqft') or m.get('siding_sqft') or 0)) / 100.0:g} SQ")
        ),
    },
    # J blocks — small penetration cover plates (lights, outlets, hose
    # bibs, dryer vents). Scaled by openings as a rough house-size proxy
    # since HOVER doesn't list utility penetrations.
    {
        "tabs": ["lp_smart"],
        "section": "LP Siding Accessories",
        "item": 'J blocks',
        "unit": "Each",
        "extract": lambda m: max(
            4,
            round((m.get("window_count") or 0) / 6 + (m.get("door_count") or 0) / 2),
        ),
        "note": ("Min 4 — lights, outlets, hose bibs scaled by openings "
                 "(SEALED AS-IS register #1 ruled 2026-07-28: per-job variance makes "
                 "photo-counting unreliable — contractor owns the final qty)"),
    },
    # Mini Splits — large penetration covers (AC linesets, dryer vents,
    # range hoods). Most homes have 1-3.
    {
        "tabs": ["lp_smart"],
        "section": "LP Siding Accessories",
        "item": 'Mini Splits',
        "unit": "Each",
        "extract": lambda m: max(
            1,
            round((m.get("entry_door_count") or 0) / 2),
        ),
        "note": ("Min 1 — AC linesets, dryer vents, range hoods "
                 "(SEALED AS-IS register #2 ruled 2026-07-28: contractor owns the final qty)"),
    },
    # =====================================================================
    # OUTSIDE CORNERS — count is HOVER outside-corner LF ÷ piece length.
    # Vinyl/Ascend = 10' pieces, LP = 16' pieces.
    # =====================================================================
    {
        "tabs": ["vinyl"],
        "section": "Siding Accessories",
        "item": "Outside corners Standard color",
        "unit": "PCS",
        # LENGTH-CUT (Howard ruled 2026-07-29): whole-stick count IS the
        # allowance — the waste field multiplies AREA GOODS only.
        "waste_included": True,
        # PER-CORNER HEIGHTS govern when a door read them (ruled
        # 2026-08-06 — stop averaging corner heights); pooled ÷12.5
        # stays the unchanged fallback.
        "extract": lambda m: (
            _osc_per_corner_pcs(m, 12.5)
            if _osc_per_corner_pcs(m, 12.5) is not None
            else (0 if _key_refused(m, "outside_corner_lf")
                  else max(1, math.ceil((m.get("outside_corner_lf") or 0) / 12.5 - 1e-9)))),
        "note": lambda m: (
            _osc_heights_note(m, 12.5)
            if _osc_per_corner_pcs(m, 12.5) is not None
            else "Vinyl 12.5' outside-corner pieces (HOVER LF ÷ 12.5, round up)"),
    },
    {
        "tabs": ["ascend"],
        "section": "Ascend Cladding/Accessories",
        "item": "Ascend 5.5\" Outside Corner  - MATTE",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: (
            _osc_per_corner_pcs(m, 12.5)
            if _osc_per_corner_pcs(m, 12.5) is not None
            else (0 if _key_refused(m, "outside_corner_lf")
                  else max(1, math.ceil((m.get("outside_corner_lf") or 0) / 12.5 - 1e-9)))),
        "note": lambda m: (
            _osc_heights_note(m, 12.5)
            if _osc_per_corner_pcs(m, 12.5) is not None
            else "Ascend 12.5' outside-corner pieces / corner LF"),
    },
    {
        "tabs": ["lp_smart"],
        "section": "LP Siding Accessories",
        # SEALED (ruled 2026-07-24): OSC product width is 5/4"×6"
        # (Howard's default, CONTRACTOR-SPEC confirmed) — the 4" tab row
        # retired. Whole-stick pooling = entire allowance.
        "item": "540 Series OSC 5/4\" x 6\" x 16'",
        "unit": "PCS",
        "waste_included": True,
        # Q13 (ruled 2026-07-27): per-corner whole-stick round-up, min 1
        # pc per corner — flat ÷16 pooling retired.
        "extract": lambda m: _osc_lp_pcs(m),
        "note": lambda m: (
            _osc_heights_note(m, 16.0)
            if (not m.get("_osc_tall_corners_ft")
                and _osc_per_corner_pcs(m, 16.0) is not None)
            else (
            (
                f"OSC {int(m.get('outside_corner_count') or 0)} corner(s) × per-corner "
                f"whole-stick round-up ({float(m.get('outside_corner_lf') or 0):g} LF total, "
                "min 1 pc/corner)"
                + ((" — " + str(len(m.get('_osc_tall_corners_ft') or [])) + " taped TALL corner(s) ["
                    + ", ".join(f"{float(h):g}'" for h in (m.get('_osc_tall_corners_ft') or []))
                    + "] take ceil(h/16) sticks each — taped height counts, never the average")
                   if m.get("_osc_tall_corners_ft") else "")
                + ((f" — HUMAN count {int(m.get('outside_corner_count') or 0)} (report read "
                    f"{m.get('_osc_count_hover')}, shown for comparison)")
                   if m.get("_corner_count_human") and m.get("_osc_count_hover") else "")
            )
            if int(m.get("outside_corner_count") or 0) > 0
            else (f"Outside-corner {float(m.get('outside_corner_lf') or 0):g} LF ÷ 16 — "
                  "POOLED (corner count unavailable; Q16 flag)")
            )
        ),
    },
    # =====================================================================
    # INSIDE CORNERS — vinyl + ascend. LP doesn't ship a dedicated inside-
    # corner item (LP installers use trim/butt joints), so we skip LP here.
    # =====================================================================
    {
        "tabs": ["vinyl"],
        "section": "Siding Accessories",
        "item": "Inside Corners (Siding) Standard color",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: max(0, math.ceil((m.get("inside_corner_lf") or 0) / 12.5 - 1e-9)),
        "note": "12.5' pieces per HOVER inside-corner LF, round up — defaults to Standard color",
    },
    # R4 (Howard ruled 2026-07-30): the Ascend "Inside Corners" emitter is
    # RETIRED — the item does not exist (supplier-dropped Feb 2026); an
    # emitter feeding a retired catalog name puts an unbuyable line on a
    # real quote. Detector: test_every_static_emitter_item_resolves_to_a_
    # live_catalog_row.
    # =====================================================================
    # STARTER — both vinyl and Ascend now per-PCS in the catalog. HOVER
    # qty = LF ÷ 12.5 (RULED 2026-07-18, vinyl-conventions batch: "clap
    # keeps 12'6\"" — closes the old ÷10-vs-÷12.5 question). LP has no
    # dedicated starter. On multi-region jobs the pooled row is SUPPRESSED
    # and replaced by profile-specific region lines (_region_context_lines).
    # =====================================================================
    {
        "tabs": ["vinyl"],
        "section": "Siding Accessories",
        "item": "Starter",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: 0 if _region_split_active(m) else max(0, math.ceil((m.get("starter_lf") or 0) / 12.5 - 1e-9)),
        "note": "Vinyl Starter pcs = ceil(HOVER starter LF ÷ 12.5)",
    },
    {
        "tabs": ["ascend"],
        "section": "Ascend Cladding/Accessories",
        "item": "Ascend - Starter",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: max(0, math.ceil((m.get("starter_lf") or 0) / 12.5 - 1e-9)),
        "note": "Ascend Starter pcs = ceil(HOVER starter LF ÷ 12.5)",
    },
    # =====================================================================
    # FINISH TRIM — qty = (eaves LF + FULL window perimeter) ÷ 12.5
    # Iter 78f (2026-02-25): Howard's clarification — finish trim wraps the
    # full window perimeter (top + sides + bottom), not just the sill width.
    # Rakes ARE included here as the rake's WALL pass (R1 ruled 2026-07-30,
    # RAKE_J_DOCTRINE): wall pass on this line, ONE rake pass on Soffit J —
    # exactly 2 per rake.
    # =====================================================================
    {
        "tabs": ["vinyl"],
        "section": "Siding Accessories",
        "item": "Finish Trim Standard color",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: 0 if _region_split_active(m) else _finish_trim_pcs(m),
        "note": lambda m: _finish_trim_note(m),
        "viz": lambda m: _finish_trim_viz(m),
    },
    {
        "tabs": ["ascend"],
        "section": "Ascend Cladding/Accessories",
        "item": "ASCEND Finish Trim",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: _finish_trim_pcs(m),
        "note": lambda m: _finish_trim_note(m),
        "viz": lambda m: _finish_trim_viz(m),
    },
    # =====================================================================
    # J-CHANNEL — wraps window + patio + GARAGE door perimeters PLUS soffit
    # eaves + rakes. HOVER lumps every opening together in
    # `opening_perimeter_lf`; we prefer the per-window dims from
    # `windows[]` when present, otherwise back out entry doors and fall
    # back to count-based estimates. LP doesn't use J-channel.
    # Pieces are 12.5 ft each, always round UP.
    # =====================================================================
    {
        "tabs": ["vinyl"],
        "section": "Siding Accessories",
        "item": "3/4\" J-Channel Standard color",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: 0 if _region_split_active(m) else _j_channel_pcs(m),
        "note": lambda m: _j_channel_breakdown(m),
    },
    {
        "tabs": ["ascend"],
        "section": "Ascend Cladding/Accessories",
        "item": "Ascend - J - Channel",
        "unit": "PCS",
        "waste_included": True,
        "extract": lambda m: _j_channel_pcs(m),
        "note": lambda m: _j_channel_breakdown(m),
    },
    # =====================================================================
    # .019 TRIM COIL (Siding Accessories) — Iter 79b: switched from a
    # "1 roll per 5 squares of siding" rule to a perimeter-based rule per
    # Howard. The coil wraps the LF perimeter of every opening (windows,
    # entry doors, sliding glass / patio doors, garage doors); 1 roll
    # covers 100 LF of perimeter wrap. The "Siding Accessories" section
    # is shared across the Vinyl and Ascend tabs, so one mapping with
    # both tabs listed lands the qty on each.
    # =====================================================================
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Siding Accessories",
        "item": ".019 Coil",
        "unit": "ROLL",
        "extract": lambda m: _coil_019_rolls(m),
        "note": lambda m: (_coil_019_breakdown(m)
                           + _coil_color_note(m, "_window_wrap_color",
                                              "wraps openings — window-wrap colour")),
    },
    # =====================================================================
    # WALL UNDERLAYMENT — vinyl gets House Wrap; Ascend gets RainDrop House
    # Wrap (the rainscreen underlayment Ascend installers prefer). LP has
    # no underlayment line in the catalog.
    # =====================================================================
    {
        "tabs": ["vinyl"],
        "section": "Siding Accessories",
        "item": "House Wrap",
        "unit": "ROLL",
        # Fractional rolls here; the ONE waste emitter (_bake_tab_waste /
        # applyWasteQty) bakes the field waste then ceils — whole-unit
        # rounding happens ONLY on the sales unit (the roll).
        "extract": lambda m: round(
            ((m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0))
            / 100.0 / HOUSE_WRAP_SQ_PER_ROLL,
            2,
        ),
        "note": "Sold by the roll — 9.00 SQ/roll (ruled 2026-07-31); "
                "SQ from HOVER 'SIDING WASTE TOTALS → + Openings < 20ft² +10%'",
    },
    {
        "tabs": ["ascend"],
        "section": "Siding Accessories",
        "item": "RainDrop",
        "unit": "ROLL",
        "extract": lambda m: round(
            ((m.get("siding_with_openings_sqft") or m.get("siding_sqft") or 0))
            / 100.0 / RAINDROP_SQ_PER_ROLL,
            2,
        ),
        "note": "Ascend rainscreen underlayment — sold by the roll, "
                "11.25 SQ/roll (ruled 2026-07-31)",
    },
    # =====================================================================
    # NAILS — vinyl + ascend; LP uses different fasteners (manual entry).
    # =====================================================================
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Siding Accessories",
        "item": "2\" Nails 30 lbs",
        # SALES UNIT (Howard ruled 2026-07-31): sold by the 30-lb BOX,
        # 1 box per 15 SQ — the JOB label was the lie; the count was
        # already boxes. round → ceil per the whole-units doctrine.
        "unit": "BOX",
        "extract": lambda m: max(1, math.ceil((m.get("siding_sqft") or 0) / 100.0 / 15 - 1e-9)),
        "note": "1 box per 15 SQ of siding — ordered by the 30-lb box (ruled 2026-07-31)",
    },
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Siding Accessories",
        "item": "1 1/4\" Trim Nails",
        "unit": "Box",
        "extract": lambda m: 1,
        "note": "1 box per job (standard)",
    },
    # =====================================================================
    # SOFFIT — vinyl + ascend share the soffit line; LP has its own
    # panel-based soffit. Iter 45: switched LF → PCS using Howard's
    # formula: Pieces = (Overhang × Length) ÷ ((Exposure/12) × Panel length)
    # Charter Oak default uses 10"-exposure × 12' panel = 10 sqft/pc;
    # overhang is read from the estimate (defaults to 12" if absent).
    # Length = eaves + rakes since soffit wraps both the level eave and
    # the gable rake undersides. Waste% is left for the Waste Factor
    # card downstream so we don't double-apply.
    # =====================================================================
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Vinyl Soffit with Siding",
        "item": "Soffit & fascia Charter Oak Standard Color",
        "unit": "PCS",
        # Q14a (ruled 2026-07-27): measured soffit TOTAL governs on the
        # vinyl list too (the substitution target pulls real quantities).
        "extract": lambda m: (
            math.ceil(float(m.get("soffit_sqft") or 0) / 10.0 - 1e-9)
            if (m.get("soffit_sqft") or 0) > 0
            else max(
                0,
                math.ceil(
                    (
                        (float(m.get("overhang_in") or 12) / 12.0)
                        * ((m.get("eaves_lf") or 0) + (m.get("rakes_lf") or 0))
                        + (m.get("porch_ceiling_sqft") or 0)
                    )
                    / 10.0
                 - 1e-9),
            )
        ),
        "note": lambda m: (
            # Provenance print (ruled 2026-08-02): TYPED vs MEASURED —
            # the document must not hide how a number got there.
            ((f"TYPED soffit total {float(m.get('soffit_sqft') or 0):g} sqft — CONTRACTOR "
              "FILL-IN, photo door (not a measurement) ÷ 10 sqft/pc; Standard color default")
             if _staging_is_fillin(m, "soffit_sqft") else
             (f"MEASURED soffit total {float(m.get('soffit_sqft') or 0):g} sqft ÷ 10 sqft/pc "
              "(Q14a ruled 2026-07-27 — measured total governs); Standard color default"))
            if (m.get("soffit_sqft") or 0) > 0
            else (
                f"Pieces = ((Overhang {float(m.get('overhang_in') or 12):g}\" ÷ 12) × (Eaves+Rakes) "
                f"+ porch_ceiling {float(m.get('porch_ceiling_sqft') or 0):g} sqft) ÷ 10 sqft/pc; Standard color default"
            )
        ),
    },
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Vinyl Soffit with Siding",
        "item": "3/4\" Soffit J-Channel (Charter Oak) Standard color",
        "unit": "PCS",
        "waste_included": True,
        # R1 ruled 2026-07-30: rakes counted ONCE (was 2× before the ruling —
        # 3 passes total with the wall-J rake term; see RAKE_J_DOCTRINE).
        # ASSEMBLY SPLIT (ruled 2026-08-07): the porch CEILING-receiving
        # channel prints HERE at full perimeter (the wall J beneath stays
        # on the wall-J line, wall-abutting only).
        "extract": lambda m: max(
            0,
            math.ceil(((m.get("eaves_lf") or 0) + (m.get("rakes_lf") or 0)
                       + _porch_soffit_j_lf(m)[0]) / 12.5 - 1e-9),
        ),
        "viz": lambda m: _soffit_j_viz(m),
        "note": lambda m: (
            f"(Eaves + Rakes"
            + (f" + {_porch_soffit_j_lf(m)[1]}" if _porch_soffit_j_lf(m)[0] > 0 else "")
            + f") ÷ 12.5 LF/stick — {RAKE_J_DOCTRINE}"
            + " — eave counts ONE run: the fascia side carries NO J, the "
              "fascia wrap is the receiver (SEALED 2026-08-07 — was "
              "accidental-right, now ruled)"
            + ((" — pre-ruling 2×rakes rule gave "
                f"{max(0, math.ceil(((m.get('eaves_lf') or 0) + 2.0 * (m.get('rakes_lf') or 0)) / 12.5 - 1e-9))} pcs, "
                f"now {max(0, math.ceil(((m.get('eaves_lf') or 0) + (m.get('rakes_lf') or 0)) / 12.5 - 1e-9))}")
               if (m.get("rakes_lf") or 0) > 0 else "")
        ),
    },
    # =====================================================================
    # FASCIA / RAKE / FRIEZE COVERAGE — driven off eaves LF (per Howard).
    # Lives in the shared "Vinyl Soffit with Siding" section so one mapping
    # lands the qty on both Vinyl and Ascend tabs.
    # =====================================================================
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Vinyl Soffit with Siding",
        "item": 'Fascia/rake or frieze',
        "unit": "LF",
        "extract": lambda m: round((m.get("eaves_lf") or 0) + (m.get("rakes_lf") or 0)),
        "note": "Eaves LF + Rakes LF × 1 wrap (fascia wraps both eave runs and gable rakes)",
    },
    # =====================================================================
    # .019 FASCIA COIL — 1 roll per 100 LF of soffit/fascia (per Howard).
    # Soffit/fascia LF = eaves LF + rakes LF.
    # =====================================================================
    # Q3 (ruled 2026-07-27): fascia coil is WIDTH-CONDITIONAL — fascia
    # ≤10" → 100 LF/roll (24" coil ripped in half); >10" → 50 LF/roll.
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Vinyl Soffit with Siding",
        "item": ".019 Coil",
        "unit": "ROLL",
        "extract": lambda m: round(
            ((m.get("eaves_lf") or 0) + (m.get("rakes_lf") or 0))
            / (100.0 if float(m.get("_fascia_width_in") or 8) <= 10 else 50.0), 2
        ),
        "note": lambda m: (
            f"Width-conditional: fascia "
            f"{float(m.get('_fascia_width_in') or 8):g}\" "
            + ("≤10\" → 24\" coil ripped in half = 100 LF/roll"
               if float(m.get("_fascia_width_in") or 8) <= 10
               else ">10\" → 50 LF/roll")
            + " — soffit & fascia LF ÷ divisor"
            + _coil_color_note(m, "_soffit_fascia_color", "fascia wrap — soffit/fascia colour")
        ),
    },
    # =====================================================================
    # CAULKING — family-shaped (register #5 ruled 2026-07-28): flat 2/job
    # RETIRED. Vinyl/Ascend interlock — caulk at OPENINGS only: 1 tube per
    # opening (windows + doors).
    # =====================================================================
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Siding Accessories",
        "item": "Caulking (per color)",
        "unit": "EA",
        "extract": lambda m: max(1, (0 if m.get("_windows_integral_j")
                                     else int(m.get("window_count") or 0))
                                 + int(m.get("door_count") or 0)),
        "note": lambda m: (
            f"1 tube per opening — interlocking siding, caulk at openings only "
            f""
            + ("0 windows (integral-J — ruled 2026-08-05, the J is the seal)"
               if m.get("_windows_integral_j")
               else f"{int(m.get('window_count') or 0)} windows")
            + f" + {int(m.get('door_count') or 0)} doors"),
    },
    # Iter 70 (2026-06-22): wire HOVER fields previously left on the floor.
    # Gable Vents — auto-populate from HOVER's Accessories → Vents Qty.
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Siding Accessories",
        "item": "Gable vents (round,octagon)",
        "unit": "Each",
        "extract": lambda m: int(m.get("vent_count") or 0),
        "note": "HOVER Accessories → Vents Qty",
    },
    # Shutters — HOVER reports total individual shutters; catalog row is
    # priced per PAIR, so divide by 2 (round up so a stray single still
    # gets a pair quoted).
    {
        "tabs": ["vinyl", "ascend"],
        "section": "Siding Accessories",
        "item": "Shutters (louvered, raised panel) standard sizes",
        "unit": "PR",
        "extract": lambda m: math.ceil((m.get("shutter_count") or 0) / 2 - 1e-9),
        "note": "HOVER shutter qty ÷ 2 (catalog priced per pair)",
    },
    # Second/Third/Clear Story Fee — flat $1,846 labor adder on Windows
    # tab when HOVER reports the home is >1 story. Stories field is a
    # string ("1", "2", ">1"); we treat anything not equal to "1" and
    # not blank as multi-story.
    {
        "tabs": ["windows"],
        "section": "Window Misc.",
        "item": "Second/Third/Clear Story Fee",
        "unit": "each",
        "extract": lambda m: 1 if (
            str(m.get("stories") or "1").strip() not in ("1", "", "None", "null")
        ) else 0,
        "note": "HOVER stories > 1 → 1 fee applies",
    },
    # Iter 68 (2026-06-22): split soffit Vented vs Closed by eaves/rakes.
    # Convention: VENTED soffit goes on EAVES (allows attic ventilation),
    # CLOSED/SOLID soffit goes on RAKES (no venting needed at gables).
    # Howard's request — splits the previous (eaves+rakes)/16 lump into
    # the two right material rows so the contractor doesn't have to move
    # qty between them by hand.
    #
    # Iter 78ah — when LP_AI_FORMULAS_V1 is on, LP soffit qty scales
    # with the estimate's overhang (mirroring how Vinyl/Ascend
    # Charter Oak soffit is computed). Coverage from PDF default 16"
    # Soffit panel = 21.3 sqft/PCS. Formula:
    #   pcs = ceil( (overhang_in/12) × LF / 21.3 × 1.10 waste )
    # When the flag is off, fall back to the legacy LF ÷ 16 row so
    # historical quotes don't shift.
    # Iter 78aj — porch ceilings contribute sqft to the SAME soffit
    # qty. Vented porches go on eaves (most common — front porch
    # ceiling under the main eave) so we route the porch_ceiling_sqft
    # total to the Vented row. Closed (rake) row stays rake-only.
    {
        "tabs": ["lp_smart"],
        "section": "LP SmartSide Soffit",
        "item": "38 Series Soffit 16 x 16 Vented",
        "unit": "PCS",
        # soffit_pieces carries ×1.10 inside — the tab bake was doubling
        # waste (10% on 10%) until 2026-07-24.
        "waste_included": True,
        # Q14a (ruled 2026-07-27): explicit per-surface breakdown governs
        # first; else a MEASURED Hover soffit TOTAL governs (proportional
        # eave/rake split); overhang-depth estimate is the LAST fallback.
        "extract": lambda m: (
            lp_formulas.soffit_pieces(float(m.get("_soffit_vented_sqft") or 0))
            if (m.get("_soffit_vented_sqft") or 0) > 0
            else (
                lp_formulas.soffit_pieces(_soffit_total_split(m)[0])
                if _soffit_total_split(m)[0] > 0
                else (
                    lp_formulas.soffit_pieces(
                        (float(m.get("overhang_in") or 12) / 12.0) * (m.get("eaves_lf") or 0)
                        + (m.get("porch_ceiling_sqft") or 0)
                    )
                    if lp_formulas.is_enabled()
                    else max(
                        1,
                        math.ceil(((m.get("eaves_lf") or 0) + (m.get("porch_ceiling_sqft") or 0) / max(float(m.get("overhang_in") or 12) / 12.0, 0.1)) / 16 - 1e-9),
                    )
                )
            )
        ),
        "note": lambda m: (
            f"Vented — MEASURED eave soffit {float(m.get('_soffit_vented_sqft') or 0):g} sqft ÷ 21.3 × 1.10 (report per-surface basis)"
            if (m.get("_soffit_vented_sqft") or 0) > 0
            else (
                ((f"Vented — TYPED soffit total governs (CONTRACTOR FILL-IN, photo door — not a measurement): "
                  f"eave share {_soffit_total_split(m)[0]:g} of {float(m.get('soffit_sqft') or 0):g} sqft ÷ 21.3 × 1.10 — verify venting split")
                 if _staging_is_fillin(m, "soffit_sqft") else
                 (f"Vented — measured soffit total governs: "
                  f"eave share {_soffit_total_split(m)[0]:g} of {float(m.get('soffit_sqft') or 0):g} sqft ÷ 21.3 × 1.10 — verify venting split"))
                if _soffit_total_split(m)[0] > 0
                else (
                    (
                        f"Vented (eaves + porches) — ceil( ((overhang {float(m.get('overhang_in') or 12):g}\" ÷ 12) × eaves_LF "
                        f"+ porch_ceiling {float(m.get('porch_ceiling_sqft') or 0):g} sqft) ÷ 21.3 × 1.10 ) — PDF 16\" Soffit"
                    )
                    if lp_formulas.is_enabled()
                    else "Vented goes on eaves (attic vent path) — eaves LF ÷ 16"
                )
            )
        ),
    },
    {
        "tabs": ["lp_smart"],
        "section": "LP SmartSide Soffit",
        "item": "38 Series Soffit 16 x 16 Closed",
        "unit": "PCS",
        # soffit_pieces carries ×1.10 inside — see Vented row.
        "waste_included": True,
        "extract": lambda m: (
            lp_formulas.soffit_pieces(float(m.get("_soffit_closed_sqft") or 0))
            if (m.get("_soffit_closed_sqft") or 0) > 0
            else (
                lp_formulas.soffit_pieces(_soffit_total_split(m)[1])
                if _soffit_total_split(m)[1] > 0
                else (
                    lp_formulas.soffit_pieces(
                        (float(m.get("overhang_in") or 12) / 12.0) * (m.get("rakes_lf") or 0)
                    )
                    if lp_formulas.is_enabled()
                    else (
                        max(1, math.ceil((m.get("rakes_lf") or 0) / 16 - 1e-9))
                        if (m.get("rakes_lf") or 0) > 0
                        else 0
                    )
                )
            )
        ),
        "note": lambda m: (
            (
                f"Closed — MEASURED rake + ceiling soffit {float(m.get('_soffit_closed_sqft') or 0):g} sqft "
                f"(incl. ceiling {float(m.get('_soffit_ceiling_sqft') or 0):g} sqft — porch-ceiling mechanism, no venting) ÷ 21.3 × 1.10"
            )
            if (m.get("_soffit_closed_sqft") or 0) > 0
            else (
                ((f"Closed — TYPED soffit total governs (CONTRACTOR FILL-IN, photo door — not a measurement): "
                  f"rake share {_soffit_total_split(m)[1]:g} of {float(m.get('soffit_sqft') or 0):g} sqft ÷ 21.3 × 1.10 — verify venting split")
                 if _staging_is_fillin(m, "soffit_sqft") else
                 (f"Closed — measured soffit total governs: "
                  f"rake share {_soffit_total_split(m)[1]:g} of {float(m.get('soffit_sqft') or 0):g} sqft ÷ 21.3 × 1.10 — verify venting split"))
                if _soffit_total_split(m)[1] > 0
                else (
                    f"Closed (rakes) — ceil( (overhang {float(m.get('overhang_in') or 12):g}\" ÷ 12) × rakes_LF ÷ 21.3 × 1.10 ) — PDF 16\" Soffit"
                    if lp_formulas.is_enabled()
                    else "Closed goes on rakes (gable ends, no venting) — rakes LF ÷ 16"
                )
            )
        ),
    },
    # =====================================================================
    # GUTTER — all 3 tabs share the Seamless Gutter section.
    # Iter 78 (2026-02-23): tightened downspout + end-cap formulas per
    # Howard's LETRICK reconciliation. Downspouts: 1 per 25 LF (was 30).
    # End caps: 1 run per 30 LF eaves (was 40).
    #   - 2 elbows per downspout (1 top to turn off the gutter, 1 kick-out
    #     at the bottom to throw water away from the foundation)
    #   - Minimum 2 downspouts when ANY gutter is present (code-typical:
    #     a house needs at least one on each end). When eaves_lf is 0
    #     (e.g. a side-elevation-only quote), all three rows extract to 0
    #     and the line items get suppressed by the zero-qty filter.
    # =====================================================================
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "Gutter 6\"",
        "unit": "LF",
        # RUN INVENTORY governs when a door read it (ruled 2026-08-06);
        # eaves LF stays the unchanged fallback.
        "extract": lambda m: round(_gutter_lf(m)),
        "note": lambda m: _gutter_note(m),
    },
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "Downspout 6\"",
        # SALES UNIT (Howard ruled 2026-07-31): downspout comes in 10'
        # STICKS — qty is whole sticks, ceil(LF ÷ 10). LF math unchanged
        # underneath (story-aware drops, Iter 78z).
        "unit": "Stick",
        "extract": lambda m: (None if _downspout_lf(m) is None
                              else math.ceil(_downspout_lf(m) / 10 - 1e-9)
                              if _downspout_lf(m) > 0 else 0),
        "note": lambda m: _downspout_breakdown(m),
        "viz": lambda m: _gutter_viz(m),
    },
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "elbow",
        "unit": "Each",
        # 2 elbows per downspout (top turn + bottom kick-out). Downspout
        # count consumes the run-inventory gutter LF (ruled 2026-08-07).
        "extract": lambda m: _downspout_count(m) * 2,
        "note": lambda m: _elbow_breakdown(m),
    },
    # Iter 65 — End Caps. Industry standard: 2 caps per continuous gutter
    # run (one on each end). HOVER doesn't expose a gutter-run count so
    # we estimate runs from eaves LF: a typical rectangular home has
    # ~2 runs (front + back), larger/wrapping homes get +1 run per ~30
    # LF (tightened from 40 in Iter 78 per LETRICK reconciliation).
    # Min 2 runs whenever any gutter is present.
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "End Cap",
        "unit": "Each",
        # RUN INVENTORY governs the run count when a door read it
        # (ruled 2026-08-07); ~1 run per 30 LF stays the fallback.
        "extract": lambda m: (
            _gutter_run_count(m) * 2 if _gutter_lf(m) > 0 else 0
        ),
        "note": lambda m: (
            f"2 end caps × {_gutter_run_count(m)} runs "
            + ("(door-read run inventory: "
               + " + ".join(r["label"] for r in _gutter_run_list(m)) + ")"
               if _gutter_run_list(m)
               else "(~1 run per 30 LF eaves, min 2 runs)")
        ),
        "viz": lambda m: _gutter_viz(m),
    },
    # Iter 78i — Hangars with Screws. Howard's install rule: 1 hanger every
    # 2 ft of gutter PLUS 1 extra per gutter run (for the end termination).
    # Run count reuses the End-Cap estimate (max(2, ceil(eaves/30))) so the
    # two formulas stay in sync. Shared across vinyl/ascend/LP siding tabs;
    # available on AI Measure + HOVER + Blueprint via the shared
    # `_build_lines` mapper.
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "Hangars with Screws",
        "unit": "Each",
        "extract": lambda m: _hangers_count(m),
        "note": lambda m: _hangers_breakdown(m),
        "viz": lambda m: _gutter_viz(m),
    },
    # Iter 78z (P1.4) — Mitre auto-fill. Inferred from roof type
    # (gable vs hip) + corner counts. Gable houses get 0 outside mitres
    # because the gutter doesn't wrap; hip roofs get a mitre at every
    # outside + inside corner. Inside corners (L-shaped footprints) get
    # a mitre regardless of roof type. See `_mitre_count` for the full
    # math + `_mitre_breakdown` for the human-readable formula chip.
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "Mitre",
        "unit": "Each",
        "extract": lambda m: _mitre_count(m),
        "note": lambda m: _mitre_breakdown(m),
    },
    # Iter 78z (P1.4) — Pipe Clips auto-fill. Industry standard: 1 clip
    # per 6 ft of downspout drop, minimum 2 per downspout. Scales
    # correctly with story count via `_downspout_drop_ft`.
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "Pipe Clips",
        "unit": "Each",
        "extract": lambda m: _pipe_clips_count(m),
        "note": lambda m: _pipe_clips_breakdown(m),
    },
    # Iter 78z (P1.4) — Gutter Sealant auto-fill. 1 tube per 4 joint
    # points (mitre + end cap + outlet). Howard's job-cost rule of thumb.
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Seamless Gutter",
        "item": "Gutter Sealant",
        "unit": "Each",
        "extract": lambda m: _sealant_count(m),
        "note": lambda m: _sealant_breakdown(m),
    },
    # Iter 57w — Mirror Gutter + Downspout into the ISS catalog. ISS uses
    # the "Seamless Gutter with Siding" section with plainer item names
    # ("Gutter" / "Downspout"), so they need their own spec entries. ISS
    # has no separate "elbow" line in the catalog so we don't emit it
    # there. (Re-siding jobs are the typical ISS use case — "with
    # Siding" matches the "without Siding" exception is non-default.)
    {
        "tabs": ["iss"],
        "section": "Seamless Gutter with Siding",
        "item": "Gutter",
        "unit": "LF",
        # Same physical gutter as the vinyl line — the run inventory
        # governs when a door read it (ruled 2026-08-06).
        "extract": lambda m: round(_gutter_lf(m)),
        "note": lambda m: _gutter_note(m),
    },
    {
        "tabs": ["iss"],
        "section": "Seamless Gutter with Siding",
        "item": "Downspout",
        "unit": "LF",
        # Iter 78z (P1.4): story-aware drop, same formula as the vinyl
        # side. See `_downspout_drop_ft` for the height heuristic.
        "extract": lambda m: _downspout_lf(m),
        "note": lambda m: _downspout_breakdown(m),
    },
    # =====================================================================
    # CAPS — Misc. Labor & Material section is on all 3 tabs.
    # =====================================================================
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Misc. Labor and Material",
        "item": "Cap window",
        "unit": "Each",
        "always_emit": True,
        "extract": lambda m: (0 if m.get("_windows_integral_j")
                              else int(m.get("window_count") or 0)),
        "note": lambda m: ("0 — integral-J windows (ruled 2026-08-05): "
                           "factory-trimmed, no capping"
                           if m.get("_windows_integral_j")
                           else "1 per window from HOVER"),
    },
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Misc. Labor and Material",
        "item": "Cap entry door",
        "unit": "Each",
        "extract": lambda m: int(m.get("entry_door_count") or 0),
        "note": "1 per entry door (D-N prefix, < 72in wide)",
    },
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Misc. Labor and Material",
        "item": "Cap patio door",
        "unit": "Each",
        "extract": lambda m: int(m.get("patio_door_count") or 0),
        "note": "1 per sliding glass / patio door",
    },
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Misc. Labor and Material",
        "item": "Cap single garage door",
        "unit": "Each",
        "extract": lambda m: int(m.get("garage_door_count") or 0),
        "note": "1 per garage door (OHD-N or ≥72×84in)",
    },
    # =====================================================================
    # WINDOWS TAB — per-opening Vero entries are built separately from the
    # extracted windows[] list (see _build_vero_openings below). These two
    # catalog-line mappings cover the labor rows that still live in the
    # standard "Window Installation" section.
    # =====================================================================
    {
        "tabs": ["windows"],
        "section": "Window Installation",
        "item": "Window DH/Slider - Pocket Install",
        "unit": "Each",
        "extract": lambda m: int(m.get("window_count") or 0),
        "note": "1 install per window — default method (swap to Full Fin per job)",
    },
    {
        "tabs": ["windows"],
        "section": "Sliding Glass Door Install",
        "item": "Vinyl Sliding Glass Door (5' & 6' width)",
        "unit": "Each",
        "extract": lambda m: int(m.get("patio_door_count") or 0),
        "note": "1 install per HOVER patio door",
    },
    {
        "tabs": ["windows"],
        "section": "Window Installation",
        "item": "Cap window (Windows)",
        "unit": "Each",
        "extract": lambda m: int(m.get("window_count") or 0),
        "note": "1 cap per HOVER window (default exterior wrap)",
    },
    # Iter 42e: standard fee + disposal fee — always 1 per HOVER upload on
    # any windows estimate (paired or standalone). Howard wanted these to
    # land automatically since every job carries them.
    {
        "tabs": ["windows"],
        "section": "Window Installation",
        "item": "Job Measure Standard Fee 4 days+",
        "unit": "JOB",
        "extract": lambda m: 1 if (int(m.get("window_count") or 0) > 0 or int(m.get("patio_door_count") or 0) > 0) else 0,
        "note": "1 per job when any window/patio door derives — standard measure fee",
    },
    {
        "tabs": ["windows"],
        "section": "Window Installation",
        "item": "Disposal Fee (Windows)",
        "unit": "JOB",
        "extract": lambda m: 1 if (int(m.get("window_count") or 0) > 0 or int(m.get("patio_door_count") or 0) > 0) else 0,
        "note": "1 per job when any window/patio door derives — disposal fee",
    },
    # Iter 47: auto-fill .019 Coil qty from total window perimeter.
    # Math per Howard: total perimeter LF ÷ 100 LF per roll = qty rolls
    # (each W-N opening contributes 2 × (width + height) inches → ÷12 LF).
    # Lines populate on BOTH Vero (`windows`) and Mezzo (`mezzo`) tabs so
    # the snapshot reflects the trim on whichever brand the contractor
    # presents.
    {
        "tabs": ["windows", "mezzo"],
        "section": "Window Material List",
        "item": "Windows - .019 Coil",
        "unit": "ROLL",
        "extract": lambda m: round(
            sum(
                2 * ((float(w.get("width_in") or 0) + float(w.get("height_in") or 0)) / 12.0)
                for w in (m.get("windows") or [])
            ) / 100.0,
            2,
        ),
        "note": "Auto-calc: sum of window perimeters ÷ 100 LF/roll",
    },
    # Iter 42f: siding-side disposal — fires on vinyl + ascend + lp_smart
    # tabs when HOVER reports any siding to install. The "Tear-Off / Clean
    # Up" section is shared across all 3 siding lines so one line covers
    # whichever option the contractor quotes.
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Tear-Off / Clean Up",
        "item": "clean up/ haul away job debris",
        "unit": "JOB",
        "extract": lambda m: 1 if (m.get("siding_sqft") or 0) > 0 else 0,
        "note": "Disposal — one per job when siding work is present",
    },
    # Q1 (ruled 2026-07-27): Tear-Off + Dumpster EXIST on every door —
    # quantity AND labor CONTRACTOR-ENTERED (pending until set; readiness
    # panel surfaces them). No auto-derive.
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Tear-Off / Clean Up",
        "item": "Tear-Off",
        "unit": "SQ",
        "always_emit": True,
        "extract": lambda m: 0,
        "note": "0 until the contractor enters it — human-owned count, no auto-derive",
    },
    {
        "tabs": ["vinyl", "ascend", "lp_smart"],
        "section": "Tear-Off / Clean Up",
        "item": "Dumpster",
        "unit": "Each",
        "always_emit": True,
        "extract": lambda m: 0,
        "note": "0 until the contractor enters it — human-owned count, no auto-derive",
    },
]


# -----------------------------------------------------------------------------
# Pydantic
# -----------------------------------------------------------------------------
class HoverLine(BaseModel):
    section: str
    name: str
    unit: str
    qty: float
    note: str = ""
    # Which tab the line belongs to: "vinyl" | "ascend" | "lp_smart". The
    # importer emits one HoverLine per (mapping × tab) so a single upload
    # populates all three parallel option sets in the estimator.
    tab: str = "vinyl"


class HoverVeroOpening(BaseModel):
    """One Vero W×H per-opening row produced from a HOVER window. Mirrors the
    `vero_openings[]` shape the estimator stores on the Estimate doc. Iter 46:
    aligned with the Mezzo-style adders model — no more glass_package /
    tempered_upcharge / premium_options legacy fields."""
    id: str
    product_type: str
    label: str = ""
    width: float
    height: float
    qty: int = 1
    sister_color: str = "White Interior/White Exterior"
    sizing: str = "ui_bucket"
    # Catalog-resolved snapshots are recomputed by VeroPanel after merge.
    bucket_label: str = ""
    base_mat: float = 0
    adders: list = []
    # The original HOVER ID (W-101 etc.) — surfaced in the preview so the
    # contractor can match it back to the elevations.
    hover_id: str = ""


class HoverMezzoOpening(BaseModel):
    """One Mezzo W×H per-opening row produced from a HOVER window. Mirrors
    the `mezzo_openings[]` shape the estimator stores on the Estimate doc.
    Mezzo doesn't have a Casement product type — Vero Casement guesses map
    to Mezzo Double Hung in `_vero_to_mezzo_product_type`."""
    id: str
    product_type: str
    label: str = ""
    width: float
    height: float
    qty: int = 1
    bucket_label: str = ""
    base_mat: float = 0
    adders: list = []
    hover_id: str = ""


class HoverImportResult(BaseModel):
    measurements: dict
    lines: list[HoverLine]
    vero_openings: list[HoverVeroOpening] = []
    mezzo_openings: list[HoverMezzoOpening] = []
    raw_extract_chars: int
    # Iter 78o — sanity-check warnings from `hover_sanity.run_checks`. List
    # of {code, level, message, detail?} dicts. Empty = report looks
    # consistent. Frontend renders these as a yellow banner inside the
    # preview modal so contractors see discrepancies BEFORE they apply.
    warnings: list[dict] = []
    # Straight-on S2 elevation read result (checking tool — Deep Verify
    # retired 2026-07-29). None when the read errored before returning.
    elevation_read: Optional[dict] = None


# -----------------------------------------------------------------------------
# Parsing
# -----------------------------------------------------------------------------
PROMPT_SYSTEM = (
    "You are a precise data-extraction assistant. You are given the full text "
    "of a HOVER exterior-measurement PDF report. Your job is to pull every "
    "measurement listed and return ONLY a JSON object (no commentary, no "
    "markdown). Use the exact keys defined below. If a value isn't present, "
    "set it to null. All lengths are in feet (decimal — convert 144' 7\" to "
    "144.58 etc.). All areas are square feet."
)

PROMPT_TEMPLATE = """Extract from this HOVER report:

{{
  "siding_sqft": <total Facades Siding area, ft² — the BASE area before any waste>,
  "siding_with_openings_sqft": <value from the "SIDING WASTE TOTALS" section, specifically the line labeled "+ Openings < 20ft² +10%" (or "Openings <20ft² +10%"). This is the siding area AFTER the 10% small-openings adder. ft². If that exact line is not present, return null.>,
  "opening_facade_assignments": <ONLY if the report explicitly assigns openings to facades/materials (e.g., an opening listed under a Stucco or Brick facade section): a list of {{"id": "<opening id like W-101 or D-2>", "facade": "<siding|stucco|brick|stone|metal|other>"}}. NEVER infer placement from opening type, elevation, or height — if the report does not state it, return []. (Class C sealed 2026-07-28)>,
  "soffit_sqft": <total Soffit Area, ft²>,
  "eaves_lf": <total Eaves length, feet (decimal)>,
  "rakes_lf": <total Rakes length, feet (decimal)>,
  "starter_lf": <Level Starter Length, feet (decimal)>,
  "outside_corner_count": <Corners Outside Qty>,
  "outside_corner_lf": <Corners Outside Length, feet (decimal)>,
  "inside_corner_count": <Corners Inside Qty>,
  "inside_corner_lf": <Corners Inside Length, feet (decimal)>,
  "opening_count": <Openings Quantity total — windows + doors>,
  "opening_perimeter_lf": <sum of all opening perimeters if shown, else null>,
  "window_count": <number of windows>,
  "window_bottom_width_total_lf": <sum of the bottom-edge (sill) width of EVERY window listed in the Doors & Windows table, in feet (decimal). For each window, take its WIDTH dimension (the shorter horizontal measurement, NOT the height) and add them all together. Example: three windows at 36in (3.0ft), 48in (4.0ft) and 60in (5.0ft) → 12.0. If individual window dimensions aren't shown, set to null.>,
  "door_count": <total number of doors of all types>,
  "entry_door_count": <number of single/double entry doors — `D-N` IDs that are NOT garage-sized (<72in wide OR <84in tall)>,
  "patio_door_count": <number of sliding/patio doors — typically `SGD-N` IDs (Sliding Glass Door), or `FD-N` (French Door)>,
  "garage_door_count": <number of garage/overhead doors — `OHD-N` prefix, or any door with width >= 96in (8ft, the smallest standard garage door). Most garage doors are 96-216in wide.>,
  "stories": <"1" | ">1" | "2" etc as printed>,
  "footprint_perimeter_ft": <FOOTPRINT section — Footprint Perimeter, feet (decimal). If not present, null.>,
  "footprint_area_sqft": <FOOTPRINT section — Footprint Area, ft² (decimal). If not present, null.>,
  "address": <property address if shown, else null>,
  "level_frieze_lf": <Level Frieze Board Length under Roofline section, feet (decimal). If not present, null.>,
  "sloped_frieze_lf": <Sloped Frieze Board Length under Roofline section, feet (decimal). If not present, null.>,
  "drip_edge_lf": <Drip Edge / Perimeter Length under Roof Measurements, feet (decimal). If not present, null.>,
  "total_trim_sqft": <Total Trim Area from the Areas table (Trims row), ft². If not present, null.>,
  "shutter_count": <Accessories → Shutter Qty (total individual shutters, NOT pairs). If not present, null.>,
  "vent_count": <Accessories → Vents Qty (gable/roof vents). If not present, null.>,
  "united_inches": <Total United Inches across all window openings (sum of width_in + height_in for each window). If not present, null.>,
  "per_elevation_siding": {{
    "front": <Front elevation siding sqft, or null>,
    "back": <Back elevation siding sqft, or null>,
    "left": <Left elevation siding sqft, or null>,
    "right": <Right elevation siding sqft, or null>
  }},
  "roof_area_sqft": <Total Roof Area, ft². If not present, null.>,
  "facade_breakdown": {{
    "siding_sqft": <Facades table — Siding row area only, ft². If not present, null.>,
    "stucco_sqft": <Facades table — Stucco row area, ft². If not present, null.>,
    "brick_sqft": <Facades table — Brick / Masonry row area, ft². If not present, null.>,
    "stone_sqft": <Facades table — Stone row area, ft². If not present, null.>,
    "metal_sqft": <Facades table — Metal row area, ft². If not present, null.>,
    "other_sqft": <sum of any other facade material rows, ft². If not present, null.>
  }},
  "windows": [
    {{ "id": "W-101", "width_in": 29.0, "height_in": 51.0 }},
    ... one object per individual window opening listed in the Doors & Windows table ...
  ]
}}

Window extraction rules:
  - Pull EVERY individual window listed (W-101, W-202, etc.). Window-group rows
    (WG-1, WG-2) are usually composites of the underlying W-N openings — skip
    the WG rows and only emit the individual W-N entries.
  - width_in is the SHORTER horizontal dimension (always the first number).
  - height_in is the VERTICAL dimension (second number).
  - Always emit inches as decimals. `29"` → 29.0.
  - Skip rows that are clearly doors (D-, SGD-, FD-, OHD- prefix).
  - If no individual window dimensions are available, emit an empty list [].

Door classification rules (apply in this order):
  1. Any door with prefix `SGD-` or `FD-` → patio_door_count
  2. Any door with prefix `OHD-` → garage_door_count
  3. Any door with width >= 96in (8ft) → garage_door_count (standard garage door size starts at 96in; 72in is too narrow to be a garage)
  4. All other doors (single front doors at 36in wide, double doors at 72in wide × 80in tall, etc.) → entry_door_count

The three counts (entry + patio + garage) must sum to door_count.

Facade-breakdown rule (PINNED 2026-07-18): emit each facade material row
SEPARATELY in facade_breakdown — NEVER sum different materials together.
siding_sqft (top-level) stays the Siding row only.

Convert all `7' 5"` style values to decimal feet. Example: `7' 5"` → 7.42.

PDF text follows:
---
{text}
---
Return ONLY the JSON object."""


def _extract_pdf_text(raw: bytes) -> str:
    """Pull plain text from a HOVER PDF. We collect each page separately and
    join with double-newlines so the LLM can still see section boundaries."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(raw)
        path = f.name
    try:
        with pdfplumber.open(path) as pdf:
            parts = []
            for p in pdf.pages:
                t = p.extract_text() or ""
                if t.strip():
                    parts.append(t)
            return "\n\n".join(parts)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _strip_json_fence(s: str) -> str:
    """Claude usually returns clean JSON, but occasionally wraps in ```json fences.
    Strip both common variants before parsing."""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


async def _ask_claude(text: str, session_id: str) -> dict:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY missing on server")
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=PROMPT_SYSTEM,
    ).with_model("anthropic", "claude-opus-4-5-20251101")  # Iter 58: upgraded from Sonnet 4.5 to Opus 4.5 — matches AI Measure for max accuracy on edge HOVER PDFs
    msg = UserMessage(text=PROMPT_TEMPLATE.format(text=text[:60000]))  # safety cap
    try:
        reply = await chat.send_message(msg)
    except Exception as e:
        # Surface the most common, actionable failure modes as friendly 4xx
        # errors instead of generic 500s. Budget exhaustion is by far the
        # most likely cause once a contractor runs a few large HOVER PDFs.
        msg = str(e).lower()
        if "budget" in msg and "exceed" in msg:
            raise HTTPException(
                status_code=402,
                detail=(
                    "Universal LLM key budget exceeded. Add balance in your "
                    "Emergent profile (Profile → Universal Key → Add Balance) "
                    "and retry the HOVER import."
                ),
            ) from e
        if "rate" in msg and "limit" in msg:
            raise HTTPException(
                status_code=429,
                detail="LLM rate limit hit — wait a few seconds and retry.",
            ) from e
        # Unknown LLM error — bubble up with detail so it's not a blind 500
        logger.exception("HOVER LLM call failed")
        raise HTTPException(
            status_code=502,
            detail=f"HOVER parser failed talking to the LLM ({e})",
        ) from e
    try:
        return json.loads(_strip_json_fence(reply))
    except json.JSONDecodeError as e:
        logger.warning("Claude returned non-JSON: %s", reply[:400])
        raise HTTPException(
            status_code=502,
            detail=f"Could not parse measurements from HOVER report (LLM JSON parse failed: {e})",
        ) from e


# Iter 78z (P1.2) — Per-profile siding SKU lookup. Maps a canonical
# profile family (from profile_callouts.classify_profile) to the right
# catalog SKU on each siding tab. Tuple shape: (item_name, unit,
# sqft_per_unit). qty = ceil(sqft / sqft_per_unit) rounded to 1 decimal.
# When a profile has no SKU on a given tab (e.g. Ascend has no Shake),
# the row is silently skipped — the contractor can manually add a
# substitute. The vinyl + ascend SQ rates use 100 sqft/SQ; LP uses 11
# PCS/SQ for lap/shake/nickel-gap (consistent with Iter 67 conversion),
# and 32 sqft/PCS for 4'×8' panels.
_PROFILE_SKU_MAP: dict[tuple[str, str], tuple[str, str, float]] = {
    # ---- Vinyl tab — Charter Oak family ------------------------------
    ("lap",          "vinyl"):    ('Charter Oak Standard color Dutch Lap 4.5" .046', "SQ", 100.0),
    ("dutch_lap",    "vinyl"):    ('Charter Oak Standard color Dutch Lap 4.5" .046', "SQ", 100.0),
    # R3 (Howard ruled 2026-07-31): Pelican Bay sells by the HALF SQUARE —
    # 13 pcs per 1/2 SQ, one fixed exposure, no reveal choice. qty derives
    # in half squares; whole-unit rounding lands on whole half squares.
    ("shake",        "vinyl"):    ('Pelican Bay Shakes 9"',                          "1/2 SQ", 50.0),
    ("board_batten", "vinyl"):    ('vertical board and batten Standard color 7"',   "SQ", 100.0),
    ("vertical",     "vinyl"):    ('vertical board and batten Standard color 7"',   "SQ", 100.0),
    # ---- Ascend tab --------------------------------------------------
    ("lap",          "ascend"):   ('Ascend Composite Lap Siding 7"',                       "SQ", 100.0),
    ("dutch_lap",    "ascend"):   ('Ascend Composite Lap Siding 7"',                       "SQ", 100.0),
    ("board_batten", "ascend"):   ('Ascend Composite B&B 12"',             "SQ", 100.0),    ("vertical",     "ascend"):   ('Ascend Composite B&B 12"',             "SQ", 100.0),
    # Shake has no Ascend SKU — skipped.
    # ---- LP tab — 38 Series + Shake + Nickel Gap ---------------------
    # Legacy uniform 9.09 sqft/PCS conversion. When LP_AI_FORMULAS_V1 is
    # enabled, `_lp_profile_sku_entry()` below overrides these with the
    # PDF-accurate per-profile coverage (8" Lap = 9.17, Shake @ 7" = 2.33,
    # etc.) per Howard's master LP reference (2026-02-28).
    ("lap",          "lp_smart"): ('38 Series Lap 3/8" x 8" x 16\'', "PCS", 100.0 / 11),  # ≈9.09 sqft/pc
    ("dutch_lap",    "lp_smart"): ('38 Series Lap 3/8" x 8" x 16\'', "PCS", 100.0 / 11),
    ("shake",        "lp_smart"): ('Shake',                          "PCS", 100.0 / 11),
    ("nickel_gap",   "lp_smart"): ('Nickel Gap',                     "PCS", 100.0 / 11),
    # F7 (Howard ruled 2026-07-30): the gated-legacy 4×8 Vertical Panel
    # rows (÷32 while the live path is 4×10 ÷40) are DELETED — flag-off
    # emits no BB line rather than a divergent one.
}


def _lp_profile_sku_entry(family: str, measurements: dict | None = None) -> tuple[str, str, float] | None:
    """Iter 78ab — When `LP_AI_FORMULAS_V1` is enabled, return the LP
    SKU + accurate per-profile coverage rate from the PDF formulas
    (8" Lap / 16" Soffit / 7" shake reveal defaults). Else None so
    the caller falls back to the legacy `_PROFILE_SKU_MAP` row.

    Coverage rates are sqft per PCS — keep the unit aligned with the
    legacy map so the qty math (`sqft / sqft_per_unit`) is unchanged.
    """
    if not lp_formulas.is_enabled():
        return None
    if family in ("lap", "dutch_lap"):
        # LAP UNIFY (register #3 ruled 2026-07-28): the split path CONFORMS
        # to the sealed book 11 pcs/sq (2026-07-19) — the PDF 9.17 coverage
        # retires from ORDERING (stays on record as reference pedigree).
        # 100/11 ≈ 9.0909 sqft/pc ⇒ pieces_needed ≡ lap_pieces_book, pinned.
        return (
            '38 Series Lap 3/8" x 8" x 16\'',
            "PCS",
            100.0 / lp_formulas.LAP_PCS_PER_SQUARE,
        )
    if family == "shake":
        # SHAKE REVEAL (register #4 ruled 2026-07-28): contractor-selectable
        # estimate field bounded 7"–10", default 7" — per LP install
        # instructions ("540 Series Trim is recommended when the shake
        # reveal selected ranges between a maximum of 10 inches to a
        # minimum of 7 inches"). Coverage = 4' × reveal/12, clamped to the
        # panel's physical max 9-7/8" (a 10" selection prices at 9.875).
        _reveal = float((measurements or {}).get("_shake_reveal_in")
                        or lp_formulas.DEFAULT_SHAKE_REVEAL_INCHES)
        return (
            'Shake',
            "PCS",
            lp_formulas.shake_coverage_sqft_per_pc(_reveal),
        )
    if family == "nickel_gap":
        return (
            'Nickel Gap',
            "PCS",
            lp_formulas.NICKEL_GAP_COVERAGE_SQFT_PER_PC,
        )
    if family in ("board_batten", "vertical"):
        # PANEL SIZE trade spec (Howard ruled 2026-07-30): contractor picks
        # 4×10 (default, 40 ft²) or 4×8 (32 ft²) — changes COUNT and SKU.
        if str((measurements or {}).get("_panel_size") or "4x10") == "4x8":
            return (
                "38 Series 4' x 8' Panel",
                "PCS",
                lp_formulas.BB_PANEL_SIZES_SQFT["4x8"],
            )
        return (
            "38 Series 4' x 10' Panel",
            "PCS",
            lp_formulas.BB_PANEL_COVERAGE_SQFT,
        )
    return None

# Section per tab for the per-profile siding lines (keyed by tab).
_PROFILE_SECTION_BY_TAB = {
    "vinyl":    "Vinyl Siding",
    "ascend":   "Ascend Cladding",
    "lp_smart": "LP Smart Siding",
}


def _profile_siding_lines(measurements: dict) -> list[dict]:
    """Emit one siding line per profile family per tab when the AI/
    Blueprint pipeline returned a multi-profile breakdown.

    Returns [] when:
      - `_per_profile_sqft` is absent (HOVER PDF imports — keep
        default mapping)
      - only 1 profile family is present (single-profile house —
        default mapping still wins because it uses HOVER's small-
        opening 10% adder)
      - no profiles have positive sqft

    Notes the contractor will see on each emitted line:
      "Per-elevation breakdown: SHAKE 168 ft²"
    """
    per_profile = measurements.get("_per_profile_sqft") or {}
    if not isinstance(per_profile, dict):
        return []
    positive = {f: s for f, s in per_profile.items() if isinstance(s, (int, float)) and s > 0}
    # Compare-profiles (ruled 2026-07-16): a forced single-family derivation
    # sets `_force_profile_lines` so the per-profile path emits even for one
    # family (the default-mapping shortcut would otherwise win).
    if len(positive) <= 1 and not measurements.get("_force_profile_lines"):
        return []
    # Iter 79j.71 — composition tripwire. Families flagged with a
    # composition conflict get an amber line (qty 0 + warning note)
    # instead of a number: a silently wrong quantity is worse than a
    # blank the contractor must fill.
    conflicts_raw = measurements.get("_profile_composition_conflicts") or []
    conflict_reasons: dict[str, str] = {}
    for c in conflicts_raw:
        if isinstance(c, dict) and c.get("family"):
            fam = str(c["family"])
            conflict_reasons.setdefault(fam, str(c.get("reason") or "composition conflict"))
    composition = measurements.get("_per_profile_composition") or {}

    def _composition_note(family: str, sqft: float) -> str:
        base = f"Per-elevation breakdown: {family.upper().replace('_', ' ')} {sqft:.0f} ft²"
        surfaces = composition.get(family) if isinstance(composition, dict) else None
        if not isinstance(surfaces, list) or not surfaces:
            return base
        parts = [
            f"{s.get('elevation')} {s.get('surface')} {s.get('sqft')}"
            for s in surfaces[:6] if isinstance(s, dict)
        ]
        if len(surfaces) > 6:
            parts.append(f"+{len(surfaces) - 6} more")
        return base + " = " + " + ".join(parts)

    out: list[dict] = []
    for tab in ("vinyl", "ascend", "lp_smart"):
        section = _PROFILE_SECTION_BY_TAB[tab]
        for family, sqft in positive.items():
            # UNKNOWN family (ruled 2026-07-26 A): never priced by guess —
            # hard amber flag on the LP tab, qty 0.
            if family == "unknown":
                if tab != "lp_smart":
                    continue
                out.append({
                    "tab": tab,
                    "section": section,
                    "name": "UNCLASSIFIED SIDING PROFILE",
                    "unit": "SQFT",
                    "qty": 0,
                    "note": (f"⚠ {sqft:.0f} ft² carries an unclassifiable profile "
                             "callout — classify by hand before quoting; never "
                             "priced by guess (ruled 2026-07-26 A)"),
                })
                continue
            # Iter 78ab — flag-aware LP override. When
            # LP_AI_FORMULAS_V1 is ON, swap the legacy 9.09 sqft/PCS
            # row for the PDF-accurate per-profile coverage rate.
            sku = None
            if tab == "lp_smart":
                sku = _lp_profile_sku_entry(family, measurements)
            if sku is None:
                sku = _PROFILE_SKU_MAP.get((family, tab))
            if not sku:
                continue
            item, unit, sqft_per_unit = sku
            if sqft_per_unit <= 0:
                continue
            # Iter 79j.71 — amber-flag conflicted families: qty 0 + loud
            # note, never a number.
            if family in conflict_reasons:
                out.append({
                    "tab": tab,
                    "section": section,
                    "name": item,
                    "unit": unit,
                    "qty": 0,
                    "note": (
                        f"⚠ {family.upper().replace('_', ' ')} quantity composition "
                        f"conflict — verify by hand ({conflict_reasons[family]})"
                    ),
                })
                continue
            # Iter 78ab — LP tab applies waste + round-up per PDF.
            # WASTE IS FAMILY-DEFAULTED (sealed 2026-07-24): the surfaced
            # _waste_pct (estimate field / family default) governs when
            # present — 0.0 means BASE qty (import draft; the field bakes).
            # Vinyl + Ascend keep the legacy 1-decimal quantity to
            # preserve existing quote behaviour.
            if tab == "lp_smart" and lp_formulas.is_enabled():
                # WASTE IS FAMILY-DEFAULTED, split path corrected by
                # ruling C (2026-07-26): each family line defaults to ITS
                # family waste (lap 10 · B&B/vertical 30 · shake 15 ·
                # nickel gap 12 — sealed 2026-07-24). The ONE visible
                # estimate field governs its own (selected) family and
                # single-family jobs — never another family's line.
                from lp_conventions import family_waste_default_pct
                _w = measurements.get("_waste_pct")
                _sel = measurements.get("_default_family")
                _fam_key = "board_batten" if family == "vertical" else family
                if _w is not None and (len(positive) <= 1 or family == _sel):
                    _waste = float(_w)
                    _waste_src = "estimate field"
                else:
                    _waste = family_waste_default_pct(_fam_key) / 100.0
                    _waste_src = "family default"
                qty = lp_formulas.pieces_needed(sqft, sqft_per_unit, _waste)
                waste_included = True
            else:
                qty = round(sqft / sqft_per_unit, 1)
                waste_included = False
                _waste = None
                _waste_src = None
            if qty <= 0:
                continue
            _note = _composition_note(family, sqft)
            if family == "shake" and tab == "vinyl":
                _note += (" · 13 pcs per 1/2 SQ — ordered by the half square, "
                          "whole half squares (R3 ruled 2026-07-31)")
            if _waste_src == "family default":
                _note += f" · waste {_waste * 100:g}% (family default)"
            if tab == "lp_smart" and lp_formulas.is_enabled():
                if family in ("lap", "dutch_lap"):
                    _note += " · book 11 pcs/sq (LAP UNIFY register #3 ruled 2026-07-28 — PDF 9.17 retired to reference)"
                elif family == "shake":
                    _rv = float(measurements.get("_shake_reveal_in")
                                or lp_formulas.DEFAULT_SHAKE_REVEAL_INCHES)
                    _note += (f" · reveal {_rv:g}\" (contractor field, bounded 7\"–10\", default 7\" — "
                              "register #4 ruled 2026-07-28 per LP install instructions)")
            out.append({
                "tab": tab,
                "section": section,
                "name": item,
                "unit": unit,
                "qty": qty,
                "_waste_included": waste_included,
                "note": _note,
            })
    return out




def _compose_facade_default_into(measurements: dict) -> dict | None:
    """PRODUCTION RESTORE (Howard, sealed 2026-07-28): compose the sealed
    facade default AT IMPORT on the SHARED Hover door — every measured ft²
    attributed with NO user action. WALL classes side; MASONRY classes
    exclude (reason named); an unrecognized label SIDES and flags loudly.
    The lumped facades total never composes (Class A). FLAGGED means WE
    MADE A CALL AND TOLD THE USER — no zero from an unmade decision.
    Informational, never a gate. Mutates `measurements`; returns scope."""
    from lp_conventions import compose_default_facade_scope
    scope = compose_default_facade_scope(measurements.get("facade_breakdown"))
    if not scope:
        return None
    top = float(measurements.get("siding_sqft") or 0)
    if round(top, 1) != scope["wrap_sqft"]:
        measurements["_siding_sqft_report"] = top
        measurements["siding_sqft"] = scope["wrap_sqft"]
        swo = float(measurements.get("siding_with_openings_sqft") or 0)
        if swo > 0:
            # the +10% small-openings figure keys to the report's Siding
            # basis — no valid anchor once the composed scope differs;
            # preserved (named), never composes
            measurements["_siding_with_openings_report"] = swo
            measurements["siding_with_openings_sqft"] = None
    measurements["_facade_scope"] = {
        "mode": scope["mode"], "wrap_sqft": scope["wrap_sqft"],
        "measured_total": scope["measured_total"], "sided": scope["sided"],
        "excluded": scope["excluded"],
        "excluded_reasons": scope["excluded_reasons"],
    }
    measurements["_area_conservation"] = {
        "measured_total_sqft": scope["measured_total"],
        "sided_sqft": scope["wrap_sqft"],
        "excluded_sqft": round(sum(scope["excluded"].values()), 1),
        "flagged_sqft": 0.0,
    }
    return scope


def _build_lines(measurements: dict) -> list[dict]:
    out = []
    # Iter 78z (P1.2) — Multi-profile siding split. When the AI Measure /
    # Blueprint pipeline returns a per-profile breakdown (Campbell-style
    # houses with Lap on the body + Shake on the gables + B&B on the
    # porch), emit ONE siding line per profile family and skip the
    # default single-SKU rows below. Single-profile houses (or HOVER PDF
    # imports that don't carry the breakdown) keep the existing default
    # mapping.
    profile_lines = _profile_siding_lines(measurements)
    skip_default_siding = len(profile_lines) > 0
    if profile_lines:
        out.extend(profile_lines)
    # Vinyl-conventions batch (3+4+5), ruled 2026-07-18: multi-region jobs
    # get context/region-split starter, J-channel and finish-trim lines
    # (pooled vinyl rows suppress themselves via _region_split_active).
    if _region_split_active(measurements):
        out.extend(_region_context_lines(measurements))
    for spec in HOVER_MAPPING_SPEC:
        if skip_default_siding and spec.get("_is_default_siding"):
            continue
        try:
            _raw_q = spec["extract"](measurements)
        except (TypeError, ValueError):
            _raw_q = 0
        if _raw_q is None:
            # SEND-105 RULING V — a refused base emits a NAMED refusal
            # row, never a silent zero and never a skipped row.
            _note = spec["note"]
            if callable(_note):
                try:
                    _note = _note(measurements)
                except Exception:
                    _note = ""
            if not (_note or "").startswith("REFUSED"):
                _note = ("REFUSED — no verified wall height on this "
                         "estimate (Ruling V)")
            for tab in spec["tabs"]:
                out.append({"tab": tab, "section": spec["section"],
                            "name": spec["item"], "unit": spec["unit"],
                            "qty": None, "not_derivable": True,
                            "not_derivable_code": RULING_V_REFUSAL_CODE,
                            "not_derivable_reason": _note,
                            "note": _note})
            continue
        qty = float(_raw_q)
        # Q1 (ruled 2026-07-27): presence rows (Tear-Off / Dumpster) emit
        # at qty 0 — contractor-entered, flagged pending until set.
        if qty <= 0 and not spec.get("always_emit"):
            continue
        # Emit one line per tab the spec targets. The contractor's estimator
        # already creates parallel entries for every (tab, section, item)
        # tuple, so we never need to fabricate mat/lab here — the frontend
        # merge keys by (tab, section, item) and finds the right row.
        # `note` may be a static string or a callable taking `measurements`
        # → per-job string (used by the J-channel rule for its formula
        # breakdown, Iter 57ee).
        note_val = spec["note"]
        if callable(note_val):
            try:
                note_val = note_val(measurements)
            except Exception:
                note_val = ""
        # BARS = CHIPS (ruled 2026-08-07): optional structured breakdown
        # rides the line so UI coverage bars render the SAME source the
        # formula divided — never a client-side formula copy.
        viz_val = spec.get("viz")
        if callable(viz_val):
            try:
                viz_val = viz_val(measurements)
            except Exception:
                viz_val = None
        for tab in spec["tabs"]:
            out.append({
                "tab": tab,
                "section": spec["section"],
                "name": spec["item"],
                "unit": spec["unit"],
                "qty": qty,
                # Sealed-convention stick rows (whole-stick rounding IS the
                # entire allowance) and formulas with ×1.10 inside opt out
                # of the tab waste bake (ruled 2026-07-24 — the old
                # ÷16 × %waste tab formulas retired). Callable flags
                # evaluate per build (default-lap single-application,
                # ruled 2026-07-29).
                "_waste_included": (bool(spec["waste_included"](measurements))
                                    if callable(spec.get("waste_included"))
                                    else bool(spec.get("waste_included"))),
                "note": note_val,
                **({"viz": viz_val} if isinstance(viz_val, dict) else {}),
                **({"qty_pending": True} if spec.get("always_emit") and qty <= 0 else {}),
            })
    # Q8 superseded 2026-08-02: tier DERIVES from the color, PER ROW —
    # each row follows its own picker (siding / outside corner /
    # accessories / soffit-fascia). Runs before ID stamping so the
    # renamed row binds the Architectural item id and price.
    out = _apply_row_color_tiers(out, measurements.get("_row_colors") or {})
    # FASCIA WIDTH TRADE SPEC (Howard ruled 2026-07-29): the contractor's
    # width call-out renames the 440 fascia SKU — the material list prints
    # the width on the line (wrong lumber on the truck is the risk; the
    # printed width is the protection). Default 8" applies silently.
    # SEND-74 — the MONEY LINE says the gable basis. SEND-137: the walk's
    # gables are MEASURED TRIANGLES (½ × width × rise); the retired 0.70
    # field factor no longer appears on any line. A traced/drawn gable zone
    # names its own basis through the overlay note instead.
    from measure_staging import (GABLE_BASIS_MEASURED_TRIANGLE,
                                 gable_basis_label)
    _walk_rows = measurements.get("_wall_walk_detail") or []
    if any((d.get("gable_sqft") or 0) > 0 for d in _walk_rows
           if isinstance(d, dict)):
        _basis_note = gable_basis_label(GABLE_BASIS_MEASURED_TRIANGLE)
        for l in out:
            if (l.get("unit") == "SQ"
                    and l.get("section") in ("Vinyl Siding",
                                             "Ascend Cladding",
                                             "LP Smart Siding")):
                l["note"] = ((str(l.get("note")) + " · ")
                             if l.get("note") else "") + _basis_note
    return _stamp_item_ids(_order_whole_units(_apply_trade_spec_widths(
        _steer_lp_soffit(out, measurements), measurements)))


_LP_VENTED_SOFFIT = "38 Series Soffit 16 x 16 Vented"
_LP_CLOSED_SOFFIT = "38 Series Soffit 16 x 16 Closed"


def _steer_lp_soffit(lines: list, m: dict) -> list:
    """SOFFIT STEER LIVES BACKEND (Howard ruled 2026-08-07): the
    contractor's vented/closed choice must survive every rebuild — a
    steer living only in the frontend apply path dies on the next
    rederive, the silent no-op class R1 exists to kill. "mix" = the
    measured split, untouched. Mirrors wasteLogic.steerLpSoffit."""
    stype = str(m.get("_lp_soffit_type") or "mix")
    if stype not in ("vented", "closed"):
        return lines
    vented = closed = None
    out = []
    for l in lines:
        if l.get("tab") == "lp_smart" and l.get("name") == _LP_VENTED_SOFFIT:
            vented = l
            continue
        if l.get("tab") == "lp_smart" and l.get("name") == _LP_CLOSED_SOFFIT:
            closed = l
            continue
        out.append(l)
    if not (vented or closed):
        return out
    base = (vented if stype == "vented" else closed) or vented or closed
    merged = dict(base)
    merged["name"] = _LP_VENTED_SOFFIT if stype == "vented" else _LP_CLOSED_SOFFIT
    merged["qty"] = ((float(vented.get("qty") or 0) if vented else 0.0)
                     + (float(closed.get("qty") or 0) if closed else 0.0))
    merged["note"] = (str(base.get("note") or "")
                      + f" · steered ALL-{stype.upper()} by the contractor's "
                        "soffit type (spec — survives rebuilds, ruled 2026-08-07)")
    out.append(merged)
    return out


def _stamp_item_ids(lines: list) -> list:
    """ID BINDING (Howard ruled 2026-07-31): every derived line carries
    its app-minted identity FROM BIRTH — resolved through the literal
    register (catalog_ids.py), never guessed. Split/variant rows whose
    display name is not a catalog row stay un-ID'd (their base_item
    carries the lineage) and keep binding by the name fallback."""
    from catalog_ids import ITEM_IDS, NAME_INDEX
    for l in lines:
        if not l.get("item_id"):
            iid = ITEM_IDS.get((l.get("section"), l.get("name"))) \
                or NAME_INDEX.get(l.get("name"))
            if iid:
                l["item_id"] = iid
    return lines


def _coil_color_note(m: dict, key: str, label: str) -> str:
    """R2 follow-on (Howard GO 2026-07-30): the coil line NAMES the colour
    of the component it wraps, from Job Info MATERIAL COLORS — never
    silence when unset."""
    c = str(m.get(key) or "").strip()
    return f" — {label}: {c}" if c else f" — {label}: colour not set — set in Job Info"


def _order_whole_units(lines: list) -> list:
    """R3 (Howard ruled 2026-07-30): WHOLE UNITS on every ordered line,
    every unit, EACH LINE ON ITS OWN — 0.5 retires (ceil, −1e-9 guard).
    Cut-prone (area) rows keep raw qty HERE because the waste bake (both
    mirrors) is their order layer and must see raw; everything else
    fractional rounds up at the source emitter so no door can print a
    quantity a contractor cannot buy."""
    for l in lines:
        q = l.get("qty")
        if isinstance(q, (int, float)) and q > 0 and q != int(q) \
                and not _cut_prone_line(l):
            l["raw_qty"] = float(q)
            l["qty"] = float(math.ceil(q - 1e-9))
    return lines


def _apply_trade_spec_widths(lines: list, m: dict) -> list:
    """Trade-spec width renames on the LP tab lines: fascia width (440)
    and wrap-trim width (540, Howard ruled 2026-07-30 — changes ONLY the
    name; the whole Q12 540 scope wrap+ISC+frieze carries the width)."""
    from lp_conventions import (DEFAULT_FASCIA_WIDTH_IN, DEFAULT_WRAP_TRIM_WIDTH_IN,
                                FASCIA_RAKE_ITEM, WRAP_TRIM_ITEM,
                                fascia_item_for_width, wrap_item_for_width)
    try:
        w = int(m.get("_fascia_width_in") or DEFAULT_FASCIA_WIDTH_IN)
    except (TypeError, ValueError):
        w = DEFAULT_FASCIA_WIDTH_IN
    try:
        ww = int(m.get("_wrap_trim_width_in") or DEFAULT_WRAP_TRIM_WIDTH_IN)
    except (TypeError, ValueError):
        ww = DEFAULT_WRAP_TRIM_WIDTH_IN
    for l in lines:
        if l.get("tab") != "lp_smart":
            continue
        if w != DEFAULT_FASCIA_WIDTH_IN and l.get("name") == FASCIA_RAKE_ITEM:
            l["name"] = fascia_item_for_width(w)
            l["note"] = ((l.get("note") or "") +
                         f' — fascia width {w}" (trade spec, contractor call-out; default 8")').strip(" —")
        elif ww != DEFAULT_WRAP_TRIM_WIDTH_IN and l.get("name") == WRAP_TRIM_ITEM:
            l["name"] = wrap_item_for_width(ww)
            l["note"] = ((l.get("note") or "") +
                         f' — wrap-trim width {ww}" (trade spec; name-only, counts unchanged; default 4")').strip(" —")
    return lines


def _build_window_openings(measurements: dict) -> tuple[list[dict], list[dict]]:
    """Turn the extracted `windows[]` list into paired Vero + Mezzo opening
    rows. ONE BUILDER (Howard ruled 2026-08-01, finding 10b): the math lives
    in measure_staging.build_paired_openings — this is the dims-mode door."""
    raw = measurements.get("windows") or []
    if not isinstance(raw, list):
        return [], []
    return _staging_build_paired_openings(windows=raw)


# -----------------------------------------------------------------------------
# (Phase 3 Deep Verify RETIRED 2026-07-29 — Howard's ruling. The straight-on
# S2 elevation read below is the single verification pass. See
# verification_integrity_register.md · SILENT-ZERO-VERIFICATION.)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Endpoint
# -----------------------------------------------------------------------------
@router.post("/estimates/hover-import")
async def hover_import(
    file: UploadFile = File(...),
    overhang_in: float = Form(12.0),
    user: dict = Depends(get_current_user),
):
    """Async launcher: upload a HOVER PDF, persist a `running` run doc,
    spawn a background worker that does the PDF→Claude→mapping→vision
    pipeline, and return a `run_id` the frontend polls via
    `/estimates/hover-import/status/{run_id}`.

    Iter 79d (Feb 2026) — Howard hit Cloudflare 524s on production when
    Claude Opus took >100 s to map large multi-page HOVERs. Async
    launcher pattern (already shipped for AI Blueprint + AI Measure)
    removes the long-running synchronous HTTP request, so the edge
    timeout never trips. The heavy work runs background; the client
    polls every 2 s for status (cheap, fast).

    `overhang_in` (inches) flows into the soffit piece-count formula —
    frontend sends the estimate's current overhang so the imported qty
    matches what the contractor will see in Job Info.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file")
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF too large (>20MB)")
    # Fast text extract — happens in the request scope so we can reject
    # scanned/image PDFs synchronously (sub-second). The slow part is
    # the Claude call which moves to the worker.
    text = _extract_pdf_text(raw)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from PDF — is this a scanned/image PDF?",
        )

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY missing on server")
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    user_id = user.get("id", "anon")
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    # S1 — SUBSTRATE PERSISTENCE (authorized 2026-07-29): keep the PDF on
    # disk past the 1h page-cache TTL so the elevation-geometry read
    # (S2) can re-render Hover's drawn pages any time. Keyed by run_id.
    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "uploads", "hover_pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.abspath(os.path.join(pdf_dir, f"{run_id}.pdf"))
    with open(pdf_path, "wb") as fh:
        fh.write(raw)
    await db.hover_import_runs.insert_one({
        "run_id": run_id,
        "user_id": user_id,
        "status": "running",
        "stage": "claude-mapping",
        "overhang_in": overhang_in,
        "raw_extract_chars": len(text),
        "pdf_size_bytes": len(raw),
        "pdf_name": file.filename,
        "pdf_path": pdf_path,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "result": None,
        "error": None,
    })
    asyncio.create_task(_execute_hover_import_worker(
        run_id=run_id,
        raw=raw,
        text=text,
        overhang_in=overhang_in,
        user_id=user_id,
        api_key=api_key,
    ))
    return {
        "run_id": run_id,
        "status": "running",
        "stage": "claude-mapping",
        "raw_extract_chars": len(text),
    }


# Iter 79d — index for hover_import_runs lives in startup.py
# (run_id unique + created_at TTL 24h).


@router.post("/estimates/hover-elevation-read/{run_id}")
async def hover_elevation_read(run_id: str, user: dict = Depends(get_current_user)):
    """S2 — read Hover's OWN drawn elevation pages (report only, no S3:
    nothing feeds flags or counts; Howard reviews the acceptance runs
    first). Requires the persisted PDF from S1 — older runs need a
    re-upload."""
    doc = await db.hover_import_runs.find_one({"run_id": run_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Hover run not found (runs expire after 24h — re-upload the PDF)")
    pdf_path = doc.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=409, detail=(
            "This run predates PDF persistence (S1) — re-upload the Hover "
            "PDF and run the read on the fresh import."))
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY missing on server")
    with open(pdf_path, "rb") as fh:
        raw = fh.read()
    from routes.hover_elevation_read import read_elevation_geometry
    schedule_text = _extract_pdf_text(raw)
    report = await read_elevation_geometry(
        raw, api_key, session_id=f"elevread-{run_id}", schedule_text=schedule_text)
    await db.hover_import_runs.update_one(
        {"run_id": run_id},
        {"$set": {"elevation_read": report,
                  "elevation_read_at": datetime.now(timezone.utc).isoformat()}})
    return {"run_id": run_id, **report}


@router.get("/estimates/hover-import/status/{run_id}")
async def hover_import_status(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """Poll the status of an async HOVER-import run. Returns the same
    shape as the legacy sync `/estimates/hover-import` response inside
    `result` once `status == "done"`.

    Stages (in order):
      claude-mapping  — Claude Opus is parsing the PDF text → measurements
      building-lines  — Backend maps measurements → catalog lines
      vision-verify   — Phase 2 vision pass on elevation drawings (optional)
      done            — Final result is in `result`
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    doc = await db.hover_import_runs.find_one({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    # Strict ownership check — only the user who launched the run can read it.
    if doc.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your run")
    # ARCHIVE-ON-VIEW (ruled 2026-08-11, TTL incident #3): hover runs
    # carry the SHORTEST fuse in the DB (24h, audit A3) — a viewed run
    # must not be reapable.
    from run_archive import archive_run_on_view, reap_time_for
    _archived = bool(await archive_run_on_view(
        doc, reason="view:hover-status"))
    created = doc.get("created_at")
    completed = doc.get("completed_at") or doc.get("updated_at")
    elapsed_ms = None
    if isinstance(created, datetime):
        if completed and isinstance(completed, datetime):
            # Mongo returns naive datetimes; coerce to aware UTC for safe subtraction.
            if completed.tzinfo is None:
                completed = completed.replace(tzinfo=timezone.utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            elapsed_ms = int((completed - created).total_seconds() * 1000)
        else:
            now = datetime.now(timezone.utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            elapsed_ms = int((now - created).total_seconds() * 1000)
    return {
        "run_id": run_id,
        "status": doc.get("status"),
        "stage": doc.get("stage"),
        "result": doc.get("result"),
        "error": doc.get("error"),
        "elapsed_ms": elapsed_ms,
        "archived": _archived,
        # Exact reap time (ruled 2026-08-11) — None once archived.
        "reaped_at": reap_time_for("hover_import_runs", doc.get("created_at"),
                                   archived=_archived),
    }


_CUT_PRONE_ASCEND = {'Ascend Composite Lap Siding 7"',
                     'Ascend Composite B&B 12"'}


def _cut_prone_line(line: dict) -> bool:
    """Python mirror of frontend lib/wasteLogic.js isCutProneItem — AREA
    GOODS ONLY (Howard sealed 2026-07-29): the waste field multiplies
    area-counted goods (panels, lap, soffit, wrap). LENGTH-CUT goods
    (whole-stick-per-run / -per-corner / -per-segment: corners, starter,
    finish trim, J-channel, LP trim sticks) are waste-included BY
    CONSTRUCTION — the whole-stick count already contains the scrap; a
    percentage on top buys sticks nobody cuts. Keep in lockstep."""
    section = str(line.get("section") or "").lower()
    name = str(line.get("name") or "").lower()
    if section == "vinyl siding":
        return True
    if (line.get("section") in ("Ascend Cladding", "Ascend Cladding/Accessories")
            and line.get("name") in _CUT_PRONE_ASCEND):
        return True
    if section in ("lp smart siding", "lp smartside soffit"):
        return True
    # D8 (found by the e2e spec journey, 2026-07-31): the real row is
    # "Soffit & fascia Charter Oak Standard Color" — the old
    # "charter oak soffit" substring matched NOTHING and the sealed
    # area-goods rule (soffit panels take field waste) never fired.
    if section == "vinyl soffit with siding" and "soffit & fascia charter oak" in name:
        return True
    # D2 (parity audit 2026-07-31): the Ascend catalog row is named
    # "RainDrop" — the fuller name never shipped. Keep all three.
    if name in ("house wrap", "raindrop house wrap", "raindrop"):
        return True
    if name == '3/8" fan fold' or "fan fold" in name:
        return True
    return False


def _bake_tab_waste(lines: list, waste_pct) -> list:
    """bakeWasteIntoLines mirror (equality pinned): cut-prone rows bake the
    field's waste then round UP to WHOLE units — 0.5 RETIRED (whole units
    at the order layer, Howard sealed 2026-07-28: 540 trim 110.5 was raw
    100 × 1.1 IEEE754 noise kept by round-up-half). Fractional qtys on
    other ordered rows round up at the same layer; sealed derivation rows
    (_waste_included) are already order-ready."""
    factor = 1 + max(0.0, float(waste_pct or 0)) / 100.0
    out = []
    for l in lines:
        l = dict(l)
        raw = float(l.get("qty") or 0)
        if raw <= 0 or l.get("_waste_included"):
            out.append(l)
            continue
        if _cut_prone_line(l):
            l["raw_qty"] = raw
            l["qty"] = float(math.ceil(raw * factor - 1e-9))
            # BAR (d) — THE WASTE STEP PRINTS (Howard's grade 2026-08-07:
            # soffit printed 48 while its chip derived 40; a quantity that
            # doesn't explain its last step is a bar-(d) failure).
            if l["qty"] != raw:
                l["note"] = _with_waste_chip(l.get("note"), raw, l["qty"], waste_pct)
        elif raw != int(raw):
            l["qty"] = float(math.ceil(raw - 1e-9))
        out.append(l)
    return out


_WASTE_CHIP_RE = re.compile(r" · ×[\d.]+ waste \([\d.]+%\): [\d.]+ → [\d.]+$")


def _with_waste_chip(note, raw, qty, waste_pct) -> str:
    """Idempotent waste chip — strip any prior chip, append the current
    step. Mirrored in wasteLogic.js withWasteChip (format pinned)."""
    base = _WASTE_CHIP_RE.sub("", str(note or ""))
    factor = 1 + max(0.0, float(waste_pct or 0)) / 100.0
    return (f"{base} · ×{factor:.2f} waste ({float(waste_pct or 0):g}%): "
            f"{raw:g} → {qty:g}")


async def rebuild_lp_tab_lines(*, est_id: str, company_id: str,
                               base_measurements: dict, est: dict,
                               profile, waste_field) -> tuple:
    """ONE FAMILY EVERYWHERE tab-line rebuild (extracted verbatim from
    hover-lp-run's rebuild_tab_lines block, rulings 2026-07-23/24; shared
    with the photo/blueprint LP APPLY GATE — lp-package/materialize, ruled
    2026-07-25). profile=None composes at the extraction's own profile
    split (default-profile inheritance already applied upstream).
    Returns (tab_lines, scoped_measurements)."""
    from routes.lp_package_routes import _DEFAULT_PROFILES, _force_profile_measurements
    scoped = dict(base_measurements)
    # SEND-129: the refusal rides all the way to the persisted takeoff.
    _ref_lanes = refused_measurement_lanes(scoped)
    if _ref_lanes:
        scoped["_refused_measurement_lanes"] = _ref_lanes
    # PORCH CEILINGS ROLL INTO SOFFIT SERVER-SIDE (ruled 2026-07-24,
    # Casile set-back entry): Job-Info porch entries feed the Vented
    # soffit derivation on every rebuild — same math as the editor's
    # recalc hook (porchCeilingTotalSqft mirror).
    porches = est.get("porch_ceilings") or []
    porch_sqft = sum(
        (float(p.get("width_ft") or 0) * float(p.get("length_ft") or 0))
        for p in porches if isinstance(p, dict))
    if porch_sqft > 0:
        scoped["porch_ceiling_sqft"] = porch_sqft
        scoped["_porch_src"] = "human"
        # REAL PORCH DIMS ride with the area (ruled 2026-08-07: an area
        # does not determine a shape) — J math uses the real perimeter.
        scoped["_porch_dims"] = [
            {"width_ft": float(p.get("width_ft") or 0),
             "length_ft": float(p.get("length_ft") or 0)}
            for p in porches if isinstance(p, dict)
            and float(p.get("width_ft") or 0) > 0
            and float(p.get("length_ft") or 0) > 0]
    if est.get("overhang_in") is not None:
        scoped["overhang_in"] = est["overhang_in"]
    # SOFFIT STEER LIVES BACKEND (Howard ruled 2026-08-07): the vented/
    # closed choice rides the rebuild so it survives every rederive.
    if est.get("lp_soffit_type"):
        scoped["_lp_soffit_type"] = est["lp_soffit_type"]
    # COLOR TIER DERIVES FROM THE COLOR (Howard ruled 2026-08-02):
    # per-row, each row follows its own Material Colors picker — the
    # standalone dropdown is retired (one decision, one control).
    _rc = {"siding": est.get("siding_color") or "",
           "outside_corner": est.get("outside_corner_color") or "",
           "accessories": est.get("accessories_color") or "",
           "soffit_fascia": est.get("soffit_fascia_color") or "",
           "board_batten": est.get("board_batten_color") or ""}
    if any(_rc.values()):
        scoped["_row_colors"] = _rc
    # INTEGRAL-J WINDOWS (Boni ruling 3, 2026-08-05): the per-job toggle
    # rides the shared rebuild — every family, every trigger.
    if est.get("windows_integral_j"):
        scoped["_windows_integral_j"] = True
    # SHAKE REVEAL (register #4 ruled 2026-07-28): the estimate field
    # rides the tab-line rebuild too — same fold as the package paths.
    if est.get("shake_reveal_in") is not None:
        scoped["_shake_reveal_in"] = float(est["shake_reveal_in"])
    # TRADE SPECS (Howard ruled 2026-07-29): batten spacing + fascia width
    # ride the tab-line rebuild too — tab/package parity, never divergent.
    if est.get("batten_spacing_in") is not None:
        scoped["_batten_spacing_in"] = int(est["batten_spacing_in"])
    if est.get("fascia_width_in") is not None:
        scoped["_fascia_width_in"] = int(est["fascia_width_in"])
    # PANEL SIZE + WRAP TRIM WIDTH (Howard ruled 2026-07-30) — same spec
    # plumbing, exact-key discipline (F2 class).
    if est.get("panel_size") is not None:
        scoped["_panel_size"] = str(est["panel_size"])
    if est.get("wrap_trim_width_in") is not None:
        scoped["_wrap_trim_width_in"] = int(est["wrap_trim_width_in"])
    # PHOTO FILL-IN BOXES (Howard ruled 2026-08-01, Three Doors step 6):
    # photo-door-only fold — inert unless scoped._source == "photo" and
    # only ever fills a hole (ONE copy in measure_staging).
    scoped = dict(_staging_fold_photo_fillins(scoped, est))
    # R2 follow-on (GO 2026-07-30): coil lines carry the wrapped
    # component's colour from Job Info MATERIAL COLORS.
    if est.get("window_wrap_color"):
        scoped["_window_wrap_color"] = str(est["window_wrap_color"])
    if est.get("soffit_fascia_color"):
        scoped["_soffit_fascia_color"] = str(est["soffit_fascia_color"])
    # TOUCH-UP COLOR COUNT (register #7 ruled 2026-07-28): Job-Info color
    # selections multiply the kit count on the tab lines too — the same
    # count the package path reads (tab/package parity, never divergent).
    if est.get("lp_colors"):
        from lp_colors import resolve_group_colors
        _resolved, _ = resolve_group_colors(est["lp_colors"])
        _n = len({v for v in _resolved.values() if v})
        if _n > 0:
            scoped["_lp_color_count"] = _n
    # WALL-HEIGHT ONE-TAP (authorized 2026-07-27): a closed
    # batten_wall_heights checklist entry (taped heights) feeds the batten
    # +height term on the TAB-LINE rebuild too — same fold as the package
    # paths (_apply_flag_checklist); TAPED provenance rides the entry.
    _bbf = (est.get("lp_flag_checklist") or {}).get("batten_wall_heights") or {}
    if _bbf.get("status") == "closed":
        try:
            _bbh = float(sum(float(h) for h in
                             ((_bbf.get("values") or {}).get("wall_heights_ft") or [])))
        except (TypeError, ValueError):
            _bbh = 0.0
        if _bbh > 0:
            scoped["_bb_wall_height_ft"] = _bbh
    # CORNER-COUNT CORRECTION (ruled 2026-07-28): human walked count
    # governs the tab-line rebuild too; report count kept for comparison.
    # SEND-105 — RULING V fold: this estimate's own VERIFIED wall
    # heights (taped human dimensions + DP-1 DERIVED chain faces) ride
    # the rebuild; the downspout-drop and gutter-mitre reads refuse
    # without one. Model heights stay hypothesis-only, never a base.
    _vh = {}
    try:
        async for _t in db.human_dimensions.find(
                {"estimate_id": est_id, "kind": "taped_wall_height_ft"},
                {"_id": 0, "face_id": 1, "value_ft": 1}):
            if _t.get("value_ft"):
                _vh[_t["face_id"]] = {"ft": float(_t["value_ft"]),
                                      "src": "taped_human"}
    except Exception:
        pass
    try:
        from routes.pdf_overlay import _latest_ocr
        _ot, _run105 = await _latest_ocr(est_id)
        if _ot:
            from height_read import derive_face_heights
            _fid = {"front": "front", "rear": "back",
                    "left": "left", "right": "right"}
            for _f, _rr in (derive_face_heights(_ot) or {}).items():
                if (_rr.get("status") == "DERIVED" and _rr.get("ft")
                        and _fid[_f] not in _vh):
                    _vh[_fid[_f]] = {"ft": float(_rr["ft"]),
                                     "src": "dp1_derived_chain"}
    except Exception:
        pass
    if _vh:
        scoped["_verified_wall_heights_ft"] = _vh
    _ccf = (est.get("lp_flag_checklist") or {}).get("corner_locators") or {}
    if _ccf.get("status") == "closed" and not scoped.get("_corner_count_human"):
        _cvals = _ccf.get("values") or {}
        for _k, _mk in (("outside_corner_count", "_osc_count_hover"),
                        ("inside_corner_count", "_isc_count_hover")):
            _v = _cvals.get(_k)
            if isinstance(_v, (int, float)) and _v > 0:
                scoped[_mk] = scoped.get(_k)
                scoped[_k] = int(_v)
                scoped["_corner_count_human"] = True
        # TALL CORNERS (never-average sealed 2026-07-28): taped heights
        # ride the rebuild too — same fold as _apply_flag_checklist.
        _tall = _cvals.get("tall_corners_ft")
        if isinstance(_tall, list) and _tall:
            scoped["_osc_tall_corners_ft"] = [float(h) for h in _tall]
    # CEILING DEDUP (class sealed 2026-07-28): TAPED ceiling governs —
    # the Hover-measured duplicate deducts on the rebuild too.
    _cdf = (est.get("lp_flag_checklist") or {}).get("ceiling_dedup") or {}
    if _cdf.get("status") == "closed":
        _dup = float((_cdf.get("values") or {}).get("duplicate_sqft") or 0)
        if _dup > 0 and float(scoped.get("soffit_sqft") or 0) > 0:
            # IDEMPOTENT FOLD (Howard's frozen-waste audit 2026-08-03):
            # /rederive persists scoped back into hover_measurements, so
            # deducting from the live value compounded −duplicate_sqft on
            # EVERY call (261 Haugh: 423→383→343→…). Deduct from the
            # PRE-DEDUP base — same result no matter how often it runs.
            _base_sof = float(scoped.get("_soffit_sqft_hover")
                              or scoped["soffit_sqft"])
            scoped["_soffit_sqft_hover"] = _base_sof
            scoped["soffit_sqft"] = max(_base_sof - _dup, 0.0)
            scoped["_soffit_dedup_sqft"] = _dup
    # Family-defaulted waste flows INTO the derivation (sealed
    # 2026-07-24): profile siding rows derive with the resolved field.
    scoped["_waste_pct"] = float(waste_field or 0) / 100.0
    tab_lines = _bake_tab_waste(
        _build_lines(_force_profile_measurements(scoped, profile)
                     if profile else dict(scoped)),
        waste_field)
    prev = await db.estimates.find_one(
        {"id": est_id}, {"_id": 0, "lines": 1, "lp_pricing_tier": 1})
    prev_lines = (prev or {}).get("lines") or []
    prev_idx = {(l.get("tab"), l.get("section"), l.get("name")): l
                for l in prev_lines}
    # ID BINDING (Howard ruled 2026-07-31): the rebuild inherits by the
    # app-minted identity FIRST — a renamed row keeps its human qty,
    # price and note. (tab, item_id) must be unique to bind; ambiguous
    # ids (splits) fall back to the name key. Names are labels now.
    id_idx = {}
    for l in prev_lines:
        if l.get("item_id"):
            k = (l.get("tab"), l.get("item_id"))
            id_idx[k] = None if k in id_idx else l

    def _prev_for(l):
        if l.get("item_id"):
            hit = id_idx.get((l.get("tab"), l.get("item_id")))
            if hit is not None:
                return hit
        return prev_idx.get((l.get("tab"), l.get("section"), l.get("name")))

    consumed = set()
    for l in tab_lines:
        old = _prev_for(l)
        if old:
            consumed.add(id(old))
            for k in ("mat", "lab", "adders", "ami_part", "contractor_note", "item_id"):
                if old.get(k) is not None:
                    l[k] = old[k]
            # Human-typed quantities survive the rebuild verbatim —
            # mixed-material jobs are human choices, never residue.
            # "yours: X · derived: Y" (ruled 2026-07-31): the fresh derived
            # value is stamped so the UI names both numbers.
            if (old.get("qty_src") or "") == "human":
                l["derived_qty"] = l.get("qty")
                l["qty"] = old.get("qty")
                l["raw_qty"] = old.get("raw_qty")
                l["qty_src"] = "human"
    # Rows with NO previous line to inherit from bind to the company's
    # resolved catalog (tier + overrides + LP engine) — the same source
    # the frontend import-apply merge reads. Never a silent None price.
    if any(l.get("mat") is None for l in tab_lines):
        from routes.catalog import _resolve_catalog_for_company
        comp_doc = await db.companies.find_one({"id": company_id}, {"_id": 0})
        cat = await _resolve_catalog_for_company(
            comp_doc, (prev or {}).get("lp_pricing_tier"))
        cat_idx = {(s["title"], it["name"]): it
                   for s in cat.get("sections") or [] for it in s.get("items") or []}
        # ID BINDING: price binds by identity first — a renamed catalog
        # row still prices its line.
        cat_id_idx = {it["item_id"]: it
                      for s in cat.get("sections") or []
                      for it in s.get("items") or [] if it.get("item_id")}
        for l in tab_lines:
            if l.get("mat") is not None:
                continue
            it = (cat_id_idx.get(l.get("item_id")) if l.get("item_id") else None) \
                or cat_idx.get((l.get("section"), l.get("name")))
            if it and not it.get("pricing_pending"):
                l["mat"] = it["mat"]
                l["lab"] = it["lab"]
                if it.get("ami_part") is not None:
                    l["ami_part"] = it["ami_part"]
            else:
                # No catalog row either — the frontend import-apply
                # convention is an explicit $0.00, never a None hole.
                l["mat"] = 0.0
                l["lab"] = 0.0
    # PROFILE OWNS ITS FAMILY (P0 regression, ruled 2026-07-24 —
    # Casile lap-251 double-quote): a profile-mapped rebuild writes the
    # selected family's derived quantities and ZEROES every other
    # siding family's DERIVED rows (visible qty-0, price kept).
    # Human-typed rows (qty_src == "human") always survive verbatim —
    # mixed-material jobs are human choices, never derivation residue.
    current_keys = {(l.get("tab"), l.get("section"), l.get("name")) for l in tab_lines}
    other_family_keys = set()
    for fam in _DEFAULT_PROFILES:
        if fam == profile:
            continue
        try:
            for fl in _build_lines(_force_profile_measurements(dict(scoped), fam)):
                k = (fl.get("tab"), fl.get("section"), fl.get("name"))
                if k not in current_keys:
                    other_family_keys.add(k)
        except Exception:
            continue
    for k, old in prev_idx.items():
        if k in current_keys or id(old) in consumed:
            continue
        if (old.get("qty_src") or "") == "human":
            tab_lines.append(dict(old))
        elif k in other_family_keys:
            zeroed = dict(old)
            zeroed["qty"] = 0
            zeroed["raw_qty"] = None
            tab_lines.append(zeroed)
    # LABOR IS THE CONTRACTOR'S — v3 ZEROING (sealed 2026-07-24): ALL
    # labor on the LP walk surface (vinyl/ascend/lp_smart tabs) is $0
    # until the contractor fills it — the provisional guesses RETIRED
    # ENTIRELY. Binding order per row:
    #   1. contractor edit (lab_src "human") — wins, untouched;
    #   2. contractor standing rate — companies.labor_rates or the
    #      Price Catalog LABOR $ override (the catalog is the labor
    #      home, ruled: no new card) — lab_src "company";
    #   3. $0 — named misc-labor rows stamp lab_src "pending" (the
    #      visible "contractor sets labor" state). No unflagged labor
    #      anywhere. Windows-tab labor is Excel-authored ISS pricing —
    #      out of scope.
    from lp_conventions import MISC_LABOR_ROWS
    from lp_costs import sheet_norm as _sheet_norm
    from routes.lp_package_routes import _load_tier_sheet_for
    comp_doc_rates = await db.companies.find_one(
        {"id": company_id}, {"_id": 0, "labor_rates": 1})
    company_rates = (comp_doc_rates or {}).get("labor_rates") or {}
    catalog_sheet = await _load_tier_sheet_for({"company_id": company_id})
    for l in tab_lines:
        if (l.get("tab") or "vinyl") not in ("vinyl", "ascend", "lp_smart"):
            continue
        if (l.get("lab_src") or "") == "human":
            continue  # contractor edit wins, forever
        key = _sheet_norm(l.get("name") or "")
        rate = company_rates.get(key)
        cat_lab = float((catalog_sheet.get(key) or {}).get("lab") or 0)
        if rate is not None and float(rate) > 0:
            l["lab"] = float(rate)
            l["lab_src"] = "company"
        elif cat_lab > 0:
            l["lab"] = cat_lab
            l["lab_src"] = "company"
        else:
            l["lab"] = 0.0
            l["lab_src"] = "pending" if key in MISC_LABOR_ROWS else None
    return tab_lines, scoped


def scope_to_lp_family(tab_lines: list, prev_lines: list) -> list:
    """ONE COPY of the lp_smart-kind family scoping (Howard ruled
    2026-08-04: "an LP door restores LP lines ONLY" — every door, the
    LINE surface). The rebuild emits every tab; an lp_smart estimate
    keeps ONLY the LP family plus: non-family service tabs verbatim,
    human-typed rows regardless of tab, and Howard-flagged survivors.
    Shared by /rederive, hover-lp-run, and lp-package/materialize —
    the wholesale writes at the two materialize doors were the
    re-contamination path the /rederive fix alone could not close.

    SPEC-RENAME BINDING (same class as the tier-binding sweep,
    2026-08-04): a MACHINE lp_smart row whose name differs from an
    emitted row only by its size digits (4' x 10' Panel → 4' x 8'
    Panel, wrap trim widths, fascia widths) was CONSUMED by the
    respec — carrying it doubles the panel surface. Human-typed and
    flagged rows are untouchable, rename or not."""
    import re
    derived_lp = [l for l in tab_lines
                  if (l.get("tab") or "vinyl") == "lp_smart"]
    keys = {(l.get("tab"), l.get("section"), l.get("name")) for l in derived_lp}
    id_keys = {(l.get("tab"), l.get("item_id")) for l in derived_lp if l.get("item_id")}

    def _size_base(n):
        return re.sub(r"\d+(?:\.\d+)?", "§", n or "")

    size_keys = {(l.get("tab"), l.get("section"), _size_base(l.get("name")))
                 for l in derived_lp}

    def _size_consumed(l):
        return ((l.get("tab") or "vinyl") == "lp_smart"
                and (l.get("qty_src") or "") != "human"
                and not l.get("manual")
                and not l.get("cross_family_flag")
                and (l.get("tab"), l.get("section"), _size_base(l.get("name"))) in size_keys)

    carry = [l for l in prev_lines
             if (l.get("tab"), l.get("section"), l.get("name")) not in keys
             and not (l.get("item_id") and (l.get("tab"), l.get("item_id")) in id_keys)
             and not _size_consumed(l)
             and ((l.get("tab") or "vinyl") not in ("vinyl", "ascend", "windows")
                  or (l.get("qty_src") or "") == "human"
                  or l.get("cross_family_flag"))]
    return derived_lp + carry


@router.post("/estimates/{est_id}/rederive")
async def rederive_estimate(
    est_id: str, payload: dict | None = None,
    user: dict = Depends(get_current_user),
):
    from untouchable import refuse_untouchable
    await refuse_untouchable(est_id)
    """ONE SHARED REBUILD, EVERY FAMILY (Howard ruled 2026-07-31 — parity
    audit). The SAME rebuild_lp_tab_lines that serves hover-lp-run and
    lp-package/materialize now serves siding-kind (Vinyl + Ascend) off the
    estimate's stored measurements. This is BOTH triggers: the automatic
    one (spec saves) and the MANUAL one — a rule change landing after
    import reaches stored estimates only through this door.
    Coverage: Vinyl · Ascend · LP (LP path unchanged — same function).
    Human-typed quantities survive absolutely; overridden lines carry
    derived_qty for the "yours: X · derived: Y" surface."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "kind": 1, "porch_ceilings": 1, "overhang_in": 1,
         "siding_color": 1, "outside_corner_color": 1,
         "accessories_color": 1, "shake_reveal_in": 1, "lp_colors": 1,
         "batten_spacing_in": 1, "fascia_width_in": 1,
         "panel_size": 1, "wrap_trim_width_in": 1,
         "window_wrap_color": 1, "soffit_fascia_color": 1,
         "lp_flag_checklist": 1, "hover_measurements": 1,
         "photo_soffit_sqft": 1, "photo_drip_edge_lf": 1,
         "photo_total_trim_sqft": 1, "photo_frieze_present": 1,
         "waste_pct": 1, "default_siding_profile": 1, "lines": 1,
         "lp_soffit_type": 1,
         "windows_integral_j": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Estimate not found")
    kind = est.get("kind") or "siding"
    if kind not in ("siding", "lp_smart"):
        raise HTTPException(status_code=400,
                            detail="Re-derive covers siding-kind (Vinyl/Ascend) and lp_smart-kind estimates")
    base = est.get("hover_measurements") or {}
    if not base:
        raise HTTPException(status_code=409,
                            detail="No stored measurements — import a HOVER/Blueprint first; re-derive replays the rules over the saved measurements")
    # Live-value overrides (race guard): the client may pass the spec it
    # just changed so the rebuild never reads a stale autosave.
    for k in ("overhang_in", "porch_ceilings", "fascia_width_in",
              "batten_spacing_in", "panel_size", "wrap_trim_width_in",
              "shake_reveal_in", "waste_pct", "windows_integral_j",
              "lp_soffit_type",
              "siding_color", "outside_corner_color",
              "accessories_color", "soffit_fascia_color",
              "photo_soffit_sqft", "photo_drip_edge_lf",
              "photo_total_trim_sqft", "photo_frieze_present"):
        if payload is not None and payload.get(k) is not None:
            est[k] = payload[k]
    profile = est.get("default_siding_profile") if kind == "lp_smart" else None
    if kind == "lp_smart" and payload is not None and payload.get("profile"):
        from routes.lp_package_routes import _DEFAULT_PROFILES
        if payload["profile"] not in _DEFAULT_PROFILES:
            raise HTTPException(status_code=422,
                                detail=f"profile must be one of {_DEFAULT_PROFILES}")
        profile = payload["profile"]
    waste_field = float(est.get("waste_pct") or 0)
    prev_lines = est.get("lines") or []
    tab_lines, scoped = await rebuild_lp_tab_lines(
        est_id=est_id, company_id=user["company_id"],
        base_measurements=dict(base), est=est,
        profile=profile, waste_field=waste_field)
    if kind == "siding":
        # Siding-kind door writes ONLY its own tabs; every other tab's rows
        # carry verbatim. Hand-filled rows (blind rows, legacy pre-qty_src)
        # with quantity survive verbatim — nothing hand-typed is ever lost.
        derived_va = [l for l in tab_lines
                      if (l.get("tab") or "vinyl") in ("vinyl", "ascend")]
        keys = {(l.get("tab"), l.get("section"), l.get("name")) for l in derived_va}
        # ID BINDING (ruled 2026-07-31): a saved row whose IDENTITY was
        # consumed by the rebuild (renamed label, same item_id) must not
        # ride along as a duplicate.
        id_keys = {(l.get("tab"), l.get("item_id")) for l in derived_va if l.get("item_id")}
        # TIER BINDING (stale-row sweep, 2026-08-04): Standard/Architectural
        # variants are the SAME physical row — the color picks the tier at
        # derive time. A MACHINE row whose name differs from an emitted row
        # only by the tier token was consumed by the rebuild; carrying it
        # doubles the siding count (found live: 3 Degree Dutch Lap 47+47).
        # Human-typed rows are untouchable, tier collision or not.
        def _tier_base(n):
            return ((n or "").replace("Architectural color", "§tier§")
                    .replace("Standard color", "§tier§"))
        tier_keys = {(l.get("tab"), l.get("section"), _tier_base(l.get("name")))
                     for l in derived_va if "color" in (l.get("name") or "")}
        def _tier_consumed(l):
            return ("color" in (l.get("name") or "")
                    and (l.get("qty_src") or "") != "human"
                    and not l.get("manual")
                    and (l.get("tab"), l.get("section"), _tier_base(l.get("name"))) in tier_keys)
        carry = [l for l in prev_lines
                 if (l.get("tab"), l.get("section"), l.get("name")) not in keys
                 and not (l.get("item_id") and (l.get("tab"), l.get("item_id")) in id_keys)
                 and not _tier_consumed(l)
                 and ((l.get("tab") or "vinyl") not in ("vinyl", "ascend")
                      or (l.get("qty") or 0) > 0)]
        tab_lines = derived_va + carry
    else:
        # lp_smart-kind door writes ONLY the LP family (Howard ruled
        # 2026-08-04: "an LP door restores LP lines ONLY" — the LINE
        # surface, every door, both directions; this server-side rebuild
        # is the door the Hover-modal fix alone could not close: a
        # re-derive was re-landing vinyl/ascend rows on LP estimates).
        # Non-family service tabs (iss gutter, etc.) carry verbatim;
        # human-typed rows survive regardless of tab — flagged in the
        # response, never silently dropped.
        tab_lines = scope_to_lp_family(tab_lines, prev_lines)
    # SEND-79 Item 1 — the overlay law RE-RUNS over the rebuilt lines
    # (never copied across the merge): what a human value superseded
    # survives every rebuild by construction.
    from routes.pdf_overlay import reapply_overlay_law
    tab_lines = await reapply_overlay_law(est_id, tab_lines)
    import seam_accounting
    scoped = seam_accounting.carry_refusals(
        est.get("hover_measurements"), scoped, f"{kind} rederive")
    await db.estimates.update_one(
        {"id": est_id},
        {"$set": {"lines": tab_lines, "hover_measurements": scoped}})
    from estimate_events import log_estimate_event
    await log_estimate_event(est_id, "estimate.rederived", {
        "kind": kind, "profile": profile, "waste_pct": waste_field,
        "by": user.get("email"), "trigger": (payload or {}).get("trigger") or "manual",
    })
    preserved = [l.get("name") for l in tab_lines
                 if (l.get("qty_src") or "") == "human" and l.get("derived_qty") is not None]
    return {"ok": True, "kind": kind, "lines": tab_lines,
            "human_preserved": preserved}


@router.post("/estimates/{est_id}/hover-lp-run")
async def hover_lp_run(
    est_id: str, payload: dict, user: dict = Depends(get_current_user),
):
    from untouchable import refuse_untouchable
    await refuse_untouchable(est_id)
    """Slice 1 — Hover→LP engine bridge. Materializes a Hover import as an
    LP-native derivation run so the LP Material List panel, Compare toggle,
    freeze/QR, and geometry-basis machinery all work UNCHANGED off Hover
    measurements. The Hover→engine mapping contract governs the translation
    (unmappable fields flag pending, never approximate). Geometry basis is
    named "Hover import — report <run_id>". LP SmartSide only."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")
    hover_run_id = (payload or {}).get("hover_run_id")
    profile = (payload or {}).get("profile")
    from routes.lp_package_routes import _DEFAULT_PROFILES, _hover_mapping_contract
    if profile not in _DEFAULT_PROFILES:
        raise HTTPException(status_code=422, detail=f"profile must be one of {_DEFAULT_PROFILES}")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "kind": 1, "porch_ceilings": 1, "overhang_in": 1,
         "siding_color": 1, "outside_corner_color": 1,
         "accessories_color": 1, "shake_reveal_in": 1, "lp_colors": 1,
         "batten_spacing_in": 1, "fascia_width_in": 1,
         "panel_size": 1, "wrap_trim_width_in": 1,
         "window_wrap_color": 1, "soffit_fascia_color": 1,
         "lp_flag_checklist": 1, "lines": 1, "windows_integral_j": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Estimate not found")
    if est.get("kind") != "lp_smart":
        raise HTTPException(status_code=400, detail="Hover→LP run is LP SmartSide only (slice 1)")
    hrun = await db.hover_import_runs.find_one({"run_id": hover_run_id})
    if not hrun:
        # TTL pin, 2nd instance (2026-07-18): hover_import_runs carries a
        # 24h TTL — artifact-referenced hover runs live on in fixture_runs.
        from run_archive import find_archived_run
        hrun = await find_archived_run({"run_id": hover_run_id})
    if not hrun or hrun.get("status") != "done":
        raise HTTPException(status_code=404, detail="Completed Hover import run not found")
    if hrun.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your run")
    hover_meas = ((hrun.get("result") or {}).get("measurements")) or {}
    engine_meas, mapping_flags = _hover_mapping_contract(
        hover_meas, profile,
        facade_scope=(payload or {}).get("facade_scope"),
        soffit_breakdown=(payload or {}).get("soffit_breakdown"),
        waste_pct=(payload or {}).get("waste_pct"),
    )
    # SEND-107: the derived run id is PER-ESTIMATE. It was keyed by hover
    # run + profile alone, so a duplicate rebuilding from the same hover
    # run HIJACKED the source estimate's run doc (upsert re-pointed
    # estimate_id) — "no estimate influences another" applies to run
    # identity too. Existing stamped docs keep their old ids; only new
    # rebuilds mint the scoped form.
    lp_run_id = f"hover-{hover_run_id[:12]}-{profile}-{est_id[:8]}"
    now = datetime.now(timezone.utc)
    await db.ai_measure_runs.update_one(
        {"run_id": lp_run_id},
        {"$set": {
            "run_id": lp_run_id,
            "estimate_id": est_id,
            "status": "done",
            "source": "hover",
            "hover_report_id": hover_run_id[:8],
            "hover_mapping_flags": mapping_flags,
            "page_paths": None,
            "result": {"measurements": engine_meas, "raw_ai": {}},
            "created_at": now,
            "updated_at": now,
        }},
        upsert=True,
    )
    # Pin the LP composition source to this Hover run + record the profile.
    # Hover waste unification (ruled 2026-07-20): the ruled 10% default is
    # written INTO the estimate's visible waste_pct field on import —
    # contractor-editable; downstream math reads the field via
    # _apply_contractor_waste (never a silent engine default). An explicit
    # payload waste_pct (fraction) wins over the family default.
    # WASTE IS FAMILY-DEFAULTED (sealed 2026-07-24): lap 10 · B&B 30 —
    # the visible field pre-fills from the selected family.
    from lp_conventions import family_waste_default_pct
    payload_waste = (payload or {}).get("waste_pct")
    waste_field = (round(float(payload_waste) * 100, 1)
                   if payload_waste is not None
                   else family_waste_default_pct(profile))
    est_set = {"lp_source_run_id": lp_run_id,
               "default_siding_profile": profile,
               "waste_pct": waste_field}
    # ONE FAMILY EVERYWHERE (Jon Casile founding example, ruled 2026-07-23):
    # materialize also RE-DERIVES the classic tab lines at the chosen
    # profile + facade scope — lap clears via re-derivation (never
    # hand-zeroed), no surface on the estimate speaks a different family.
    # mat/lab inherited by (tab, section, name); waste baked per the same
    # contractor-waste rule the import apply bakes.
    rebuilt_lines = None
    if bool((payload or {}).get("rebuild_tab_lines", True)):
        # Extracted to rebuild_lp_tab_lines (shared with the photo/blueprint
        # LP APPLY GATE — lp-package/materialize, ruled 2026-07-25).
        # Behavior identical: porch/overhang injection, waste bake, price
        # inheritance, family zeroing, v3 labor binding.
        scoped_base = dict(hover_meas)
        if engine_meas.get("siding_sqft") is not None:
            scoped_base["siding_sqft"] = engine_meas["siding_sqft"]  # scope governs
        rebuilt_lines, scoped = await rebuild_lp_tab_lines(
            est_id=est_id, company_id=user["company_id"],
            base_measurements=scoped_base, est=est,
            profile=profile, waste_field=waste_field)
        # LP DOOR WRITES LP ONLY (Howard ruled 2026-08-04): the rebuild
        # emits every tab — the wholesale write here was re-landing
        # vinyl/ascend rows on LP estimates after the /rederive fix.
        rebuilt_lines = scope_to_lp_family(rebuilt_lines, est.get("lines") or [])
        # SEND-79 Item 1 — re-run the overlay law, never copy markers.
        from routes.pdf_overlay import reapply_overlay_law
        rebuilt_lines = await reapply_overlay_law(est_id, rebuilt_lines)
        est_set["lines"] = rebuilt_lines
        # Porch-ceiling recompute basis (Casile set-back doorway item):
        # the classic import apply persists est.hover_measurements; the
        # server-side rebuild must too, or a Job-Info porch-ceiling entry
        # recomputes soffit off an EMPTY basis (eaves/rakes = 0) and
        # clobbers the import-derived qtys.
        import seam_accounting
        est_set["hover_measurements"] = seam_accounting.carry_refusals(
            est.get("hover_measurements"), scoped, "lp materialize")
    await db.estimates.update_one({"id": est_id}, {"$set": est_set})
    # TTL pin, 2nd instance (2026-07-18): the stamp above is a persistent
    # artifact — archive BOTH the materialized LP run and its SOURCE hover
    # run the moment the reference is minted (un-expirable from birth).
    from run_archive import archive_run_for_artifact
    await archive_run_for_artifact(run_id=lp_run_id, reason="hover-lp-materialize")
    await archive_run_for_artifact(run_id=hover_run_id, reason="hover-lp-materialize:source")
    from estimate_events import log_estimate_event
    await log_estimate_event(est_id, "lp.hover_run.materialized", {
        "hover_run_id": hover_run_id, "lp_run_id": lp_run_id,
        "profile": profile, "mapping_flags": mapping_flags, "by": user.get("email"),
        "waste_pct_written": waste_field,
    })
    return {"ok": True, "lp_run_id": lp_run_id, "profile": profile,
            "mapping_flags": mapping_flags,
            "tab_lines": rebuilt_lines}



async def _execute_hover_import_worker(
    *,
    run_id: str,
    raw: bytes,
    text: str,
    overhang_in: float,
    user_id: str,
    api_key: str,
):
    """Background worker — runs the heavy HOVER mapping pipeline + writes
    the result back to `hover_import_runs.{run_id}`."""
    async def _set_stage(stage: str):
        if db is None:
            return
        await db.hover_import_runs.update_one(
            {"run_id": run_id},
            {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc)}},
        )

    try:
        # Stage 1 — Claude mapping (the slow step that caused the 524).
        # Wrap in asyncio.wait_for so a stuck Claude call can't leave
        # the run doc parked at status='running' indefinitely. 4 min is
        # well above the realistic p99 (~90 s for a 12-page HOVER) and
        # comfortably under the frontend's 5-min polling cap, so the
        # client sees a clean 'error' state if Claude is unresponsive.
        await _set_stage("claude-mapping")
        measurements = await asyncio.wait_for(
            _ask_claude(text, session_id=f"hover-{user_id}"),
            timeout=240,
        )
        windows_payload = measurements.pop("windows", None) or []
        vero_openings, mezzo_openings = _build_window_openings(
            {"windows": windows_payload}
        )
        measurements["overhang_in"] = overhang_in
        # PRODUCTION RESTORE (Howard, sealed 2026-07-28): the sealed
        # facade default composes AT IMPORT — the vinyl/ascend/LP draft
        # lines below derive from the ATTRIBUTED siding area, never a
        # zero from an unmade decision.
        _fb_scope = _compose_facade_default_into(measurements)
        # Hover waste unification (ruled 2026-07-20): the ruled 10%
        # default is no longer applied inside formulas — it is WRITTEN
        # into the estimate's visible waste_pct field at apply/
        # materialize time (hover-lp-run + frontend apply), where the
        # contractor sees and edits it. Draft lines carry BASE
        # quantities; the field mechanism (raw_qty × 1+waste%) governs.
        # NEW imports only — pre-existing estimates untouched.
        measurements["_waste_pct"] = 0.0
        measurements["_waste_field_prefill_pct"] = DEFAULT_WASTE_PCT

        # Stage 2 — Map measurements to catalog lines (cheap, in-process).
        await _set_stage("building-lines")
        lines = _build_lines(measurements)
        from routes.hover_sanity import run_checks
        warnings = run_checks(measurements)
        if _fb_scope and (_fb_scope["excluded"] or _fb_scope["unrecognized_sided"]):
            from lp_conventions import facade_scope_flag_label
            warnings.append({
                "code": "facade_scope_composed", "level": "info",
                "message": facade_scope_flag_label(_fb_scope), "detail": None,
            })

        # Stage 3 — Drawing verification. The straight-on S2 elevation read
        # is the SINGLE verification pass (Deep Verify retired by Howard
        # 2026-07-29; scale-bar re-derivation deliberately NOT carried over
        # — pixel-derived numbers arguing with printed callouts reopen the
        # sealed provenance door). CHECKING TOOL ONLY: results live on the
        # run doc + warnings banner; nothing feeds a flag, count, or line
        # (S3 unwired by test).
        await _set_stage("vision-verify")
        elevation_read: Optional[dict] = None
        try:
            from routes.hover_elevation_read import read_elevation_geometry
            elevation_read = await read_elevation_geometry(
                raw, api_key,
                session_id=f"elevread-{run_id}",
                schedule_text=text,
            )
            if elevation_read.get("pages_read"):
                for i, wtext in enumerate(elevation_read.get("warnings") or []):
                    # every ⚠ individually — never a summary
                    warnings.append({
                        "code": f"elevation_read_{i + 1}",
                        "message": wtext,
                        "detail": ("straight-on elevation read (checking tool "
                                   "— printed text tables outrank vision reads)"),
                    })
            else:
                # SILENT-ZERO-VERIFICATION class (Howard 2026-07-29,
                # 92/92 audit): a verification step that finds nothing
                # must NOT render as a pass — loud, on the import, every
                # time. Detector: test_verification_silent_zero.py
                warnings.append({
                    "code": "vision_zero_pages",
                    "message": ("DRAWING VERIFICATION DID NOT RUN — 0 "
                                "elevation pages recognized in this PDF's "
                                "format. Nothing was cross-checked against "
                                "the drawings."),
                    "detail": elevation_read.get("error") or "no straight-on view pages located",
                })
        except Exception as e:
            logger.warning("elevation read failed: %s", e)
            warnings.append({
                "code": "vision_zero_pages",
                "message": ("DRAWING VERIFICATION DID NOT RUN — the "
                            "elevation read errored. Nothing was "
                            "cross-checked against the drawings."),
                "detail": str(e)[:200],
            })

        result_payload = {
            "measurements": measurements,
            # Convert pydantic models to dicts so MongoDB can store them.
            "lines": [HoverLine(**ln).model_dump() for ln in lines],
            "vero_openings": [HoverVeroOpening(**op).model_dump() for op in vero_openings],
            "mezzo_openings": [HoverMezzoOpening(**op).model_dump() for op in mezzo_openings],
            "raw_extract_chars": len(text),
            "warnings": warnings,
            "elevation_read": elevation_read,
        }
        await db.hover_import_runs.update_one(
            {"run_id": run_id},
            {"$set": {
                "status": "done",
                "stage": "done",
                "result": result_payload,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        # AUTO-ARCHIVE ON PROTECTED ESTIMATES (ruled 2026-08-11) — no-op
        # when the run carries no estimate_id yet.
        from run_archive import maybe_archive_protected
        await maybe_archive_protected(run_id)
    except Exception as e:
        logger.exception("Iter 79d: hover_import worker failed: %s", e)
        if db is not None:
            await db.hover_import_runs.update_one(
                {"run_id": run_id},
                {"$set": {
                    "status": "error",
                    "stage": "error",
                    "error": str(e) or "Unknown error",
                    "completed_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
