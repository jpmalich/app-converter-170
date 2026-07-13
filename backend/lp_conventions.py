"""Iter 79j.94 — LP SmartSide MATERIAL-USAGE CONVENTIONS layer (Howard's
spec block, 2026-07-11). Authoritative until the original workbook is
uploaded; if the workbook later disagrees on any line, FLAG the
discrepancy — never silently pick.

Core formula (all lap products, standard 1" overlap):
    reveal_in = actual_face_in − 1
    coverage_per_board_sqft = board_length_ft × (reveal_in ÷ 12)
    pieces_per_square = ROUNDUP(100 ÷ coverage_per_board)
All coverage figures WASTE-EXCLUSIVE; waste applied on top (10% default
for lap/soffit), THEN round up to whole pieces. Whole-piece rounding is
per-line, always up, never averaged across lines.

TWO ITEMS PENDING HOWARD'S CONFIRMATION — never filled from other sources:
  1. Shake waste factor (lap default 10% used meanwhile, FLAGGED pending)
  2. LP trim/accessory conventions (starter / J / finish trim carry-over
     from the Alside context) — not encoded as LP rules until confirmed.
"""
from __future__ import annotations
import math

from lp_smartside_formulas import (
    DEFAULT_WASTE,
    LAP_PROFILES,
    SHAKE_REVEAL_MIN_INCHES,
    SOFFIT_PROFILES,
    shake_coverage_sqft_per_pc,
)

# ── Lap table (spec-authoritative; face − 1" = reveal) ──
# KNOWN ESTIMATING TRAP: 8" lap face is 7-7/8", NOT 7-1/4" — reveal 6-7/8".
LAP_FACE_IN = {"6\" Lap": 5.875, "7\" Lap": 6.875, "8\" Lap": 7.875, "12\" Lap": 11.875}
LAP8_WRONG_FACE_IN = 7.25  # any source claiming this is wrong

# pieces-per-square, spec-verified
LAP_PCS_PER_SQUARE_16FT = {"6\" Lap": 16, "7\" Lap": 13, "8\" Lap": 11, "12\" Lap": 7}
LAP_PCS_PER_SQUARE_12FT = {"6\" Lap": 21, "7\" Lap": 18, "8\" Lap": 15, "12\" Lap": 10}

SHAKE_PCS_PER_SQUARE_MIN_REVEAL = 44   # 6-7/8" reveal
SHAKE_PCS_PER_SQUARE_MAX_REVEAL = 31   # 9-7/8" reveal

SOFFIT_BUNDLE_PCS = 9  # 38 Series ships 9 pcs/bundle where bundle rounding applies

# ── Pending confirmations (hold flagged, do NOT default) ──
# Shake waste RULED 2026-07-11: 10%, same as lap, before whole-piece
# round-up. Provisional — revisions ship as conventions updates, never
# silent edits.
SHAKE_WASTE = 0.10

# LP-native line composition RULED 2026-07-11 (supersedes Alside carry-over):
# NO J-channel, NO finish trim, NO aluminum coil lines on LP takeoffs —
# their appearance on any LP-native line is a COMPOSITION BUG.
LP_FORBIDDEN_LINE_MARKERS = ("j-channel", "j channel", "finish trim", "coil")

# LP trim system (rulings on record; full profile spec ALWAYS — never "440 Series" bare):
ISC_TRIM_ITEM = "440 Series Trim 4/4\" x 4\" x 16'"       # per inside-corner location
FASCIA_RAKE_ITEM = "440 Series Trim 4/4\" x 8\" x 16'"    # fascia + rake boards
WRAP_TRIM_ITEM = "540 Series Trim 5/4\" x 4\" x 16'"      # window/door wrap
TRIM_STICK_LEN_FT = 16.0

# Per-system derivation table (Howard amendment, 2026-07-11 — any line
# crossing systems is a composition bug):
#   VINYL: soffit (eaves+rakes) + coil fascia + J + finish trim
#   LP:    soffit (EAVES ONLY, no rake soffit wrap) + 440 4/4"×8"
#          (eaves fascia + rake boards, one product both run types)
#          + 540 trim system + NO J / NO finish trim / NO coil
SYSTEM_DERIVATION = {
    "vinyl": {"soffit_runs": "eaves+rakes", "fascia": "aluminum coil by run length",
              "openings": "J-channel + finish trim"},
    "lp": {"soffit_runs": "eaves only (no rake soffit wrap)",
           "fascia_and_rakes": "440 Series Trim 4/4\" x 8\" x 16'",
           "openings": "540 trim system",
           "forbidden": ("j-channel", "finish trim", "coil")},
}

PENDING_CONFIRMATIONS = {
    "starter_rule_divisor": (
        "Starter rule discrepancy — BOTH derivations stated: code rule "
        "ceil(start-course LF ÷ 12.5) [Letrick: ceil(168/12.5) = 14] vs file "
        "comment ÷ 10 [ceil(168/10) = 17]; delivered 20. Howard to rule."
    ),
    "expertfinish_availability_matrix": (
        "LOOKUP (not a ruling): ingest LP's published color-by-product-line "
        "ExpertFinish matrix; flag combinations our lines use that the matrix "
        "doesn't support; BlueLinx sheet = stocking-reality overlay when it lands."
    ),
    "bluelinx_sku_upload": "Howard's BlueLinx SKU sheet upload pending — BlueLinx names only until then.",
}

# ─────────────────────── Milestones (ruled log) ───────────────────────
MILESTONES = {
    "phase4_flag_flip": (
        "2026-07-13 — C4 RULED PASS; PHASE 4 FLAG-FLIP AUTHORIZED: "
        "LP_AI_FORMULAS_V1 live — the LP-native package is the production "
        "composition path. September numbers (ruled framing, NEVER blended): "
        "conventions-on-verified-geometry = 9/9 within ±3% vs Howard's sealed "
        "Letrick hand-takeoff (the engine's claim); end-to-end photos-to-order "
        "= 6/8 within ±3% with ambers flagging the extraction residual "
        "(the pipeline's claim, honestly labeled). "
        "Ground truth: letrick_hand_takeoff_key.py; runs 4a009e93 (C4 e2e), "
        "5005d6eb (pre-C4); reports in /app/memory/."
    ),
}


def reveal_from_face(face_in: float) -> float:
    return float(face_in) - 1.0


def coverage_per_board_sqft(reveal_in: float, board_length_ft: float) -> float:
    return round(float(board_length_ft) * (float(reveal_in) / 12.0), 2)


def pieces_per_square(reveal_in: float, board_length_ft: float) -> int:
    cov = float(board_length_ft) * (float(reveal_in) / 12.0)
    return int(math.ceil(100.0 / cov - 1e-9))


def line_math(area_sqft: float, coverage_sqft_per_pc: float, waste: float = DEFAULT_WASTE) -> dict:
    """Transparency triple (waste BEFORE whole-piece round-up): the
    contractor sees the math, consistent with the honesty architecture."""
    if area_sqft <= 0 or coverage_sqft_per_pc <= 0:
        return {"base_qty": 0.0, "waste_qty": 0.0, "ordered_pcs": 0, "waste_pct": round(waste * 100)}
    base = float(area_sqft) / float(coverage_sqft_per_pc)
    adj = base * (1.0 + float(waste))
    return {
        "base_qty": round(base, 2),
        "waste_qty": round(adj, 2),
        "ordered_pcs": int(math.ceil(adj - 1e-9)),
        "waste_pct": round(waste * 100),
    }


def shake_takeoff(area_sqft: float, reveal_in=None, waste=None) -> dict:
    """Reveal is JOB-SPECIFIC — never defaulted silently. Unspecified →
    flag `reveal: unconfirmed` and price at MINIMUM reveal (worst case,
    more pieces) with the flag visible. Shake waste RULED 10% (same as
    lap, provisional — revisions ship as conventions updates)."""
    flags = []
    if reveal_in is None:
        reveal_in = SHAKE_REVEAL_MIN_INCHES
        flags.append(
            "reveal: unconfirmed — priced at minimum reveal 6-7/8\" (worst case, more pieces)"
        )
    if waste is None:
        waste = SHAKE_WASTE
    m = line_math(area_sqft, shake_coverage_sqft_per_pc(reveal_in), waste)
    m["reveal_in"] = float(reveal_in)
    m["flags"] = flags
    return m


def batten_takeoff_flags(spacing=None) -> list:
    """Batten spacing is job-specific — flag if unspecified (PDF-standard
    16\" o.c. applied meanwhile, visibly)."""
    if spacing is None:
        return ["batten spacing: unconfirmed — PDF-standard 16\" o.c. applied, job-specific"]
    return []


def soffit_panel_for_overhang(overhang_in: float) -> dict:
    """Panel width matched to overhang depth; non-standard depths take
    the NEXT width up with rip waste logged as a line note."""
    widths = [("12\" Soffit", 12.0), ("16\" Soffit", 16.0), ("24\" Soffit", 24.0)]
    for name, w in widths:
        if overhang_in <= w:
            note = None
            if overhang_in not in (12.0, 16.0, 24.0):
                note = f"non-standard {overhang_in:g}\" overhang — next width up ({name}), rip waste logged"
            return {"panel": name, "rip_waste_note": note}
    return {"panel": "24\" Soffit",
            "rip_waste_note": f"overhang {overhang_in:g}\" exceeds 24\" panel — multi-rip, field plan"}


def soffit_takeoff_eave_length(eave_lf: float, overhang_in: float, waste: float = DEFAULT_WASTE) -> dict:
    """Eave-length ordering method: panels = eave length ÷ panel length
    (16' boards run along the fascia at one panel-width of depth)."""
    sel = soffit_panel_for_overhang(overhang_in)
    length_ft = float(SOFFIT_PROFILES[sel["panel"]]["length_ft"])
    base = float(eave_lf) / length_ft if eave_lf > 0 else 0.0
    adj = base * (1.0 + float(waste))
    return {
        "panel": sel["panel"],
        "rip_waste_note": sel["rip_waste_note"],
        "base_qty": round(base, 2),
        "waste_qty": round(adj, 2),
        "ordered_pcs": int(math.ceil(adj - 1e-9)) if adj > 0 else 0,
        "waste_pct": round(waste * 100),
        "bundle_note": f"38 Series ships {SOFFIT_BUNDLE_PCS} pcs/bundle where bundle rounding applies",
    }


def soffit_takeoff_area(area_sqft: float, overhang_in: float, waste: float = DEFAULT_WASTE) -> dict:
    """Area ordering method: area ÷ coverage per panel + waste."""
    sel = soffit_panel_for_overhang(overhang_in)
    cov = float(SOFFIT_PROFILES[sel["panel"]]["coverage_sqft_per_pc"])
    m = line_math(area_sqft, cov, waste)
    m.update({"panel": sel["panel"], "rip_waste_note": sel["rip_waste_note"],
              "bundle_note": f"38 Series ships {SOFFIT_BUNDLE_PCS} pcs/bundle where bundle rounding applies"})
    return m


def near_boundary(raw_squares: float) -> bool:
    """Whole-square amendment (Howard, 2026-07-11): annotate when the
    pre-round quantity falls within 0.5 square of the LOWER whole square —
    the boundary square is the crew's trim-or-keep call. Tool defaults
    safe (round up); human owns the judgment."""
    return 0 < (raw_squares - math.floor(raw_squares)) <= 0.5


def rake_slope_length_ft(pitch_rise_per_12: float, half_span_ft: float) -> float:
    """Rake slope from pitch + half-span — NEVER plan-view length."""
    return round(float(half_span_ft) * math.sqrt(1.0 + (float(pitch_rise_per_12) / 12.0) ** 2), 2)


def soffit_run_area_sqft(eaves_lf: float, rakes_lf: float, overhang_in: float,
                         include_rakes: bool = True) -> float:
    """Conventions fix (package-wide, vinyl AND LP): soffit derivation
    must panel eaves AND rakes wherever overhangs carry soffit."""
    runs = float(eaves_lf or 0) + (float(rakes_lf or 0) if include_rakes else 0.0)
    return round(runs * float(overhang_in or 0) / 12.0, 1)


def fascia_rake_takeoff(eaves_lf: float, rakes_lf: float) -> dict:
    """LP fascia + rake boards: 440 Series Trim 4/4"×8"×16' — one product
    across both run types (RULED, amendment 2026-07-11). LF = eave runs +
    rake SLOPE lengths (never plan-view). C4 (ruled 2026-07-13): stick-
    count lines get whole-stick rounding as their ENTIRE allowance — no
    percentage waste. Splice-and-round-up TOTAL sticks."""
    total_lf = float(eaves_lf or 0) + float(rakes_lf or 0)
    if total_lf <= 0:
        return {"total_lf": 0.0, "ordered_pcs": 0, "flags": []}
    return {
        "total_lf": round(total_lf, 1),
        "ordered_pcs": int(math.ceil(total_lf / TRIM_STICK_LEN_FT - 1e-9)),
        "flags": [],
    }


def lp_composition_bugs(lines: list) -> list:
    """Composition guard: J-channel / finish trim / coil on an LP-native
    takeoff is a composition bug. Returns offending line names."""
    out = []
    for l in lines:
        name = str(l.get("name") or "").lower()
        if any(m in name for m in LP_FORBIDDEN_LINE_MARKERS):
            out.append(l.get("name"))
    return out


def spec_discrepancies() -> list:
    """Internal consistency audit: module data vs the spec block's core
    formula. Any mismatch is FLAGGED, never silently picked."""
    out = []
    for name, face in LAP_FACE_IN.items():
        want_reveal = reveal_from_face(face)
        have_reveal = float(LAP_PROFILES[name]["reveal_in"])
        if abs(want_reveal - have_reveal) > 1e-6:
            out.append(f"{name}: reveal {have_reveal} != face−1 = {want_reveal}")
        want_cov = coverage_per_board_sqft(want_reveal, 16)
        have_cov = float(LAP_PROFILES[name]["coverage_sqft_per_pc"])
        if abs(want_cov - have_cov) > 0.01:
            out.append(f"{name}: coverage {have_cov} != {want_cov}")
        if pieces_per_square(want_reveal, 16) != LAP_PCS_PER_SQUARE_16FT[name]:
            out.append(f"{name}: 16' pcs/square mismatch")
        if pieces_per_square(want_reveal, 12) != LAP_PCS_PER_SQUARE_12FT[name]:
            out.append(f"{name}: 12' pcs/square mismatch")
    return out
