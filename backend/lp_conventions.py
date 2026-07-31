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

ONE ITEM PENDING HOWARD'S CONFIRMATION — never filled from other sources:
  1. LP trim/accessory conventions (starter / J / finish trim carry-over
     from the Alside context) — not encoded as LP rules until confirmed.
(Shake waste sealed 15% by the 2026-07-24 v3 book-check — see below.)
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

# Shake waste CONTRACTOR-SPEC, sealed 2026-07-24 (v3 book-check): 15%,
# before whole-piece round-up — supersedes the 2026-07-11 provisional 10%.
SHAKE_WASTE = 0.15

# SHAKE REVEAL FIELD (register #4 ruled 2026-07-28): contractor-selectable
# per-estimate field bounded 7"–10", DEFAULT 7" — per LP install
# instructions verbatim: "540 Series Trim is recommended when the shake
# reveal selected ranges between a maximum of 10 inches to a minimum of
# 7 inches". Coverage stays 4' × reveal/12 (clamped to the panel's
# physical 9-7/8" max — a 10" selection prices at 9.875). The sealed
# 44 pcs/sq is the MIN-reveal (6-7/8") instantiation of that same curve;
# at the ruled 7" default it reads ~43 pcs/sq, at 10" (→9.875) ~31. The
# sealed 15% shake waste applies multiplicatively ON TOP regardless of
# the selected reveal. 540-trim pairing consistent with Q12.
SHAKE_REVEAL_FIELD_MIN_IN = 7.0
SHAKE_REVEAL_FIELD_MAX_IN = 10.0
SHAKE_REVEAL_RULE_SOURCE = (
    'LP install instructions: "540 Series Trim is recommended when the '
    'shake reveal selected ranges between a maximum of 10 inches to a '
    'minimum of 7 inches" (register #4 ruled 2026-07-28)')

# LP-native line composition RULED 2026-07-11 (supersedes Alside carry-over):
# NO J-channel, NO finish trim, NO aluminum coil lines on LP takeoffs —
# their appearance on any LP-native line is a COMPOSITION BUG.
LP_FORBIDDEN_LINE_MARKERS = ("j-channel", "j channel", "finish trim", "coil")

# LP trim system (rulings on record; full profile spec ALWAYS — never "440 Series" bare):
# RULED Q12 (2026-07-27, 3 Degree Rd): 540 5/4"×4" is the LP ISC DEFAULT —
# crews run 540 in place of 440; 440 4/4"×4" demoted to substitution option.
ISC_TRIM_ITEM = "540 Series Trim 5/4\" x 4\" x 16'"       # per inside-corner location
FASCIA_RAKE_ITEM = "440 Series Trim 4/4\" x 8\" x 16'"    # fascia + rake boards (8" DEFAULT width)
WRAP_TRIM_ITEM = "540 Series Trim 5/4\" x 4\" x 16'"      # window/door wrap

# FASCIA WIDTH — TRADE SPEC (Howard ruled 2026-07-29): the contractor
# calls it out; no derivation, no heuristic, no inference. Default 8"
# applied silently — no gate, no flag — but the material list PRINTS the
# width on the line (this changes WHICH SKU gets ordered, so it rides the
# money-emitter path, never display).
FASCIA_WIDTHS_IN = (4, 6, 8, 10, 12)
DEFAULT_FASCIA_WIDTH_IN = 8


def fascia_item_for_width(width_in) -> str:
    try:
        w = int(width_in or DEFAULT_FASCIA_WIDTH_IN)
    except (TypeError, ValueError):
        w = DEFAULT_FASCIA_WIDTH_IN
    if w not in FASCIA_WIDTHS_IN:
        w = DEFAULT_FASCIA_WIDTH_IN
    return FASCIA_RAKE_ITEM.replace(' x 8" x', f' x {w}" x')


# WRAP TRIM WIDTH (Howard ruled 2026-07-30): 540 Series widths — changes
# ONLY the SKU name (counts stay ceil LF/16); default 4" per Q12.
WRAP_TRIM_WIDTHS_IN = (4, 6, 8, 10, 12)
DEFAULT_WRAP_TRIM_WIDTH_IN = 4


def wrap_item_for_width(width_in) -> str:
    try:
        w = int(width_in or DEFAULT_WRAP_TRIM_WIDTH_IN)
    except (TypeError, ValueError):
        w = DEFAULT_WRAP_TRIM_WIDTH_IN
    if w not in WRAP_TRIM_WIDTHS_IN:
        w = DEFAULT_WRAP_TRIM_WIDTH_IN
    return WRAP_TRIM_ITEM.replace(' x 4" x', f' x {w}" x')
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
# ─────────────── LP product SKU tables (single source) ───────────────
# Fork-boundary fix (2026-07-13): these lived as literals in the shared
# catalog seed while lp_package imported the seed to read them — a core
# boundary violation caught by the CI drift check. The tables now live
# HERE; catalog_seed imports them (legal app → LP direction).
LP_TRIM_SKUS = (
    '190 Series Trim 19/32" x 3" x 16\'',
    '440 Series Trim 4/4" x 4" x 16\'',
    '440 Series Trim 4/4" x 6" x 16\'',
    '440 Series Trim 4/4" x 8" x 16\'',
    '440 Series Trim 4/4" x 10" x 16\'',
    '440 Series Trim 4/4" x 12" x 16\'',
    '540 Series Trim 5/4" x 4" x 16\'',
    '540 Series Trim 5/4" x 6" x 16\'',
    '540 Series Trim 5/4" x 8" x 16\'',
    '540 Series Trim 5/4" x 10" x 16\'',
    '540 Series Trim 5/4" x 12" x 16\'',
)
LP_OSC_SKUS = (
    '540 Series OSC 5/4" x 4" x 16\'',
    '540 Series OSC 5/4" x 6" x 16\'',
)

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
    """Reveal is the CONTRACTOR'S FIELD (register #4 ruled 2026-07-28):
    bounded 7"–10", DEFAULT 7" — per LP install instructions (see
    SHAKE_REVEAL_RULE_SOURCE). Unspecified → the ruled 7" default with
    the flag visible. Shake waste sealed 15% (CONTRACTOR-SPEC,
    2026-07-24 v3 book-check) applies on top regardless of reveal."""
    flags = []
    if reveal_in is None:
        reveal_in = SHAKE_REVEAL_FIELD_MIN_IN
        flags.append(
            "reveal: unconfirmed — priced at the ruled 7\" default "
            "(register #4 2026-07-28; was min 6-7/8\" worst-case before the ruling)"
        )
    if waste is None:
        waste = SHAKE_WASTE
    m = line_math(area_sqft, shake_coverage_sqft_per_pc(reveal_in), waste)
    m["reveal_in"] = float(reveal_in)
    m["flags"] = flags
    return m


def batten_takeoff_flags(spacing=None) -> list:
    """RETIRED AS A FLAG (Howard 2026-07-29): batten spacing is a TRADE
    SPEC — the contractor calls it out in the trade-spec group (12/16/24,
    default 12" applied silently, no gate, no flag; the batten line note
    names the spacing and the delta when it moves off default)."""
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


def fascia_rake_takeoff(eaves_lf: float, rakes_lf: float,
                        dormer_fascia_lf: float = 0.0) -> dict:
    """LP fascia + rake boards: 440 Series Trim 4/4"×8"×16' — one product
    across both run types (RULED, amendment 2026-07-11). LF = eave runs +
    rake SLOPE lengths (never plan-view). C4 (ruled 2026-07-13): whole-
    stick rounding is the ENTIRE allowance — no percentage waste.
    Q16 (ruled 2026-07-27): rounding applies PER-SEGMENT where segment
    data exists (eaves / rakes / dormer fascia are the known segments);
    within each segment the LF is an aggregate → pooled, flagged.
    Q4 (ruled 2026-07-27): dormer fascia LF POOLS into this line — the
    separate non-priced dormer-fascia SKU retires."""
    e = float(eaves_lf or 0)
    r = float(rakes_lf or 0)
    d = float(dormer_fascia_lf or 0)
    total_lf = e + r + d
    if total_lf <= 0:
        return {"total_lf": 0.0, "ordered_pcs": 0, "flags": []}
    segs = [lf for lf in (e, r, d) if lf > 0]
    pcs = sum(int(math.ceil(lf / TRIM_STICK_LEN_FT - 1e-9)) for lf in segs)
    return {
        "total_lf": round(total_lf, 1),
        "ordered_pcs": pcs,
        "dormer_fascia_lf": round(d, 1),
        "flags": (["per-segment rounding (Q16): eaves/rakes/dormer segments; "
                   "aggregate LF within each segment — pooled, flagged"]
                  if len(segs) > 1 else []),
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


# ── LABOR / MISC CONVENTIONS (Howard's standing defaults, ruled
# 2026-07-23 with the Casile handback): these are NOT master-sheet SKUs —
# they are the contractor's standing labor conventions, applied wherever
# the named row would otherwise be $0. Contractor-editable per estimate
# on the money surface (an edited tab-line price inherits and wins),
# same class as the waste pre-fill. Keys are sheet_norm()-normalized. ──
# WASTE IS FAMILY-DEFAULTED (CONTRACTOR-SPEC, sealed 2026-07-24): siding
# waste DEFAULTS by product family — vertical panel cutting reality makes
# board & batten 30% vs lap 10%. The estimate field stays the ONE visible,
# contractor-editable number; only its DEFAULT derives from the selected
# family (profile selection + Hover materialize pre-fill it). No silent
# waste anywhere. Shake 15 · Nickel Gap 12: CONTRACTOR-SPEC, sealed
# 2026-07-24 (v3 book-check) — same one-visible-field mechanics.
# Soffit baked-10: RECOGNIZED as the SEALED soffit convention (register
# #6 ruled 2026-07-28) — the 1.10 cut factor inside soffit_pieces is the
# LP PDF convention (single-bake pinned), predates the family-waste seal,
# now cited; NO change.
FAMILY_WASTE_DEFAULTS = {
    "lap": 10.0,
    "board_batten": 30.0,
    "shake": 15.0,
    "nickel_gap": 12.0,
}


def family_waste_default_pct(profile: str | None) -> float:
    return float(FAMILY_WASTE_DEFAULTS.get(profile or "", 10.0))


# SEALED (Howard, 2026-07-28 — P3 gable precedent; 261 Haugh corner
# evidence): MATERIAL-GOVERNING DIMENSIONS ARE NEVER AVERAGED — per-unit
# or FLAGGED, no third option. An average on a material-governing
# dimension hides the unit that takes extra material (Haugh: one 18'5"
# corner takes 2 sticks; the 10' per-corner average hid it).
NEVER_AVERAGE_RULE = ("material-governing dimensions are NEVER averaged — "
                      "per-unit or FLAGGED, no third option (sealed 2026-07-28)")


# SEALED DEFAULT — FACADE COMPOSITION AT IMPORT (Howard, 2026-07-28,
# production restore): every measured facade ft² is attributed AT IMPORT
# with NO user action. WALL classes SIDE; MASONRY classes (brick / block /
# stone — plus stucco per the sealed stucco/brick rule and metal per
# Class C) AUTO-EXCLUDE with the reason named. A label that cannot be
# attributed SIDES and flags loudly — FLAGGED MEANS WE MADE A CALL AND
# TOLD THE USER; NO ZERO IS EVER PRODUCED BY AN UNMADE DECISION. The
# lumped facades total never composes (Class A conservation stands); the
# flag is INFORMATIONAL, never a gate. ONE EMITTER: both Hover doors
# (worker draft lines + LP mapping contract) compose through here.
FACADE_EXCLUDED_CLASSES = {
    "brick": "masonry (stone/brick rule sealed)",
    "block": "masonry (stone/brick rule sealed)",
    "stone": "masonry (stone/brick rule sealed)",
    "stucco": "stucco (stucco/brick exclusion ruled 2026-07-17)",
    "metal": "non-sided cladding (Class C sealed 2026-07-28)",
}


def compose_default_facade_scope(facade_breakdown: dict | None) -> dict | None:
    """One emitter of the sealed facade default (Howard, 2026-07-28)."""
    rows = {k[:-5]: float(v) for k, v in (facade_breakdown or {}).items()
            if k.endswith("_sqft") and isinstance(v, (int, float)) and v > 0}
    if not rows:
        return None
    sided = {k: v for k, v in rows.items() if k not in FACADE_EXCLUDED_CLASSES}
    excluded = {k: v for k, v in rows.items() if k in FACADE_EXCLUDED_CLASSES}
    unrecognized = sorted(k for k in sided if k not in ("siding", "other"))
    beyond_siding_row = any(k != "siding" for k in sided)
    return {
        "mode": "composed_default" if beyond_siding_row else "wrap_only",
        "wrap_sqft": round(sum(sided.values()), 1),
        "sided": sided,
        "excluded": excluded,
        "excluded_reasons": {k: FACADE_EXCLUDED_CLASSES[k] for k in excluded},
        "unrecognized_sided": unrecognized,
        "measured_total": round(sum(rows.values()), 1),
    }


def facade_scope_flag_label(scope: dict) -> str:
    """Informational flag text — 'sided X · excluded Y as masonry · tap to
    change'. Never a gate."""
    sided_txt = ", ".join(f"{k} {v:g} ft²" for k, v in sorted(scope["sided"].items()))
    parts = [(f"FACADE SCOPE COMPOSED AT IMPORT (sealed 2026-07-28): "
              f"sided {scope['wrap_sqft']:g} ft²"
              + (f" ({sided_txt})" if sided_txt else ""))]
    if scope["excluded"]:
        excl_txt = ", ".join(f"{k} {v:g} ft² — {scope['excluded_reasons'][k]}"
                             for k, v in sorted(scope["excluded"].items()))
        parts.append(f"excluded {round(sum(scope['excluded'].values()), 1):g} ft² ({excl_txt})")
    if scope["unrecognized_sided"]:
        parts.append("UNRECOGNIZED label(s) " + ", ".join(scope["unrecognized_sided"])
                     + " SIDED by rule — no zero from an unmade decision; verify on the walk")
    parts.append("tap to change in the facade picker — informational, never a gate")
    return " · ".join(parts)

# CATALOG-ONLY ROWS — MANUAL BY DESIGN (register #8 ruled 2026-07-28):
# these rows carry NO formula on purpose; no silent derivation is ever
# added. The coils are manual by the iter97 composition ruling; the rest
# by Howard's standing order (manual by omission, named).
CATALOG_ONLY_MANUAL_BY_DESIGN = (
    # "38 Series 4' x 8' Panel" LEFT the registry 2026-07-30: panel_size
    # trade spec grew it a ruled, spec-gated derivation (Howard #6).
    "38 Series Vertical Panel",
    '540 Series OSC 5/4" x 4" x 16\'',
    '440 Series Trim 4/4" x 6" x 16\'',
    '440 Series Trim 4/4" x 10" x 16\'',
    '440 Series Trim 4/4" x 12" x 16\'',
    '540 Series Trim 5/4" x 6" x 16\'',
    '540 Series Trim 5/4" x 8" x 16\'',
    '540 Series Trim 5/4" x 10" x 16\'',
    '540 Series Trim 5/4" x 12" x 16\'',
    # Ghost names fixed per Howard #6 (2026-07-30): a guard must watch the
    # EXACT catalog string — pinned by test_registry_names_resolve_to_
    # live_catalog_rows.
    'Flash tape 3 3/4" x 90\'',
    '24 inch CTW soffit',
    '24 inch VSSFT',
)


# LABOR IS THE CONTRACTOR'S — v3 ZEROING (sealed 2026-07-24): ALL labor
# defaults are $0 until the contractor fills them — NO exceptions. The
# five provisional guesses RETIRED ENTIRELY (they were never the
# contractor's numbers) and joined the retired machine set below. The
# Price Catalog's per-item LABOR $ column is the standing labor home
# ("Labor is yours to set — overrides save to your company only"): a
# filled catalog rate or a companies.labor_rates entry binds on rebuild
# (lab_src "company"); a per-estimate edit wins forever (lab_src
# "human"); everything else shows $0 in the visible "contractor sets
# labor" state (lab_src "pending" on the named misc-labor rows).
MISC_LABOR_ROWS = (
    "cap window",
    "cap entry door",
    "cap patio door",
    "cap single garage door",
    "clean up/ haul away job debris",
    # RULED Q1 (2026-07-27): tear-off + dumpster EXIST on every door,
    # quantity AND labor contractor-entered — pending until set.
    "tear-off",
    "dumpster",
)

# Superseded machine defaults, BOTH retired generations (the 2026-07-23
# provisional set 25/75/75/100/150 AND the 2026-07-24 close-out guesses
# 98/107/100/138/334, retired by the v3 zeroing ruling). A row still
# carrying one of these is a MACHINE binding, never a contractor edit —
# it rebinds to the current default ($0 / company rate) on rebuild.
RETIRED_LABOR_DEFAULTS = {
    "cap window": {25.0, 98.0},
    "cap entry door": {75.0, 107.0},
    "cap patio door": {75.0, 100.0},
    "cap single garage door": {100.0, 138.0},
    "clean up/ haul away job debris": {150.0, 334.0},
}


# ═══════════════════════════════════════════════════════════════════════
# TRADE-SPEC FAMILY REGISTER (Howard ruled 2026-07-31 — parity audit).
# ONE MECHANIC, THREE FAMILIES: every trade spec names the families it
# governs. A family-specific spec is a DEFECT unless registered here as
# DIFFERENT-BY-NATURE with the reason recorded. Pinned by
# test_e2e_spec_journey_2026_07_31.py — an entry without families or a
# nature-reason fails the suite.
# ═══════════════════════════════════════════════════════════════════════
TRADE_SPEC_FAMILY_REGISTER = {
    "overhang_in": {
        "families": ("vinyl", "ascend", "lp_smart"), "ruled": "2026-07-31",
        "reason": "soffit depth term on every family's soffit derivation"},
    "porch_ceilings": {
        "families": ("vinyl", "ascend", "lp_smart"), "ruled": "2026-07-31",
        "reason": "porch sqft folds into every family's soffit derivation"},
    "fascia_width_in": {
        "families": ("vinyl", "ascend", "lp_smart"), "ruled": "2026-07-31",
        "reason": ("R1 — governs the .019 coil divisor on vinyl/Ascend "
                   "(≤10\" → 24\" roll ripped = 100 LF/roll; >10\" → 50) and "
                   "the 440-Series board width on LP")},
    "batten_spacing_in": {
        "families": ("lp_smart",), "ruled": "2026-07-31",
        "different_by_nature": (
            "Ascend Composite B&B is a panel with the batten look "
            "integrated — no separate batten strip exists on an Ascend "
            "(or vinyl) job, ever; the 190-Series strip is LP-only")},
    "shake_reveal_in": {
        "families": ("lp_smart",), "ruled": "2026-07-31",
        "different_by_nature": (
            "vinyl shake (Pelican Bay 9\") has ONE fixed exposure — no "
            "reveal choice; it derives at 13 pcs per 1/2 SQ and orders by "
            "the half square (R3)")},
    "panel_size": {
        "families": ("lp_smart",), "ruled": "2026-07-31",
        "different_by_nature": (
            "picks between 38-Series 4×10 / 4×8 sheet SKUs; vinyl and "
            "Ascend siding is SQ-coverage, not sheet-picked (R4)")},
    "wrap_trim_width_in": {
        "families": ("lp_smart",), "ruled": "2026-07-31",
        "different_by_nature": (
            "picks the 540-Series board width; vinyl wraps openings with "
            "coil, not boards (R4)")},
    "lp_soffit_type": {
        "families": ("lp_smart",), "ruled": "2026-07-31",
        "different_by_nature": (
            "steers the two-SKU LP soffit split (Vented/Closed); vinyl "
            "soffit is a single Charter Oak row (R4)")},
    "color_tier": {
        "families": ("vinyl",), "ruled": "2026-07-28",
        "different_by_nature": (
            "price tiers exist for vinyl only (Howard ruled 2026-07-28); "
            "Ascend and LP SmartSide have none")},
}
