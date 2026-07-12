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

# ── Pending confirmations (do NOT fill from other sources) ──
PENDING_CONFIRMATIONS = {
    "shake_waste_factor": (
        "Shake waste factor pending Howard's confirmation — lap default 10% "
        "used meanwhile, flagged on every shake line."
    ),
    "lp_trim_accessory_conventions": (
        "LP trim/accessory conventions (starter / J-channel / finish trim / "
        "soffit F-channel / fascia coil rules) were logged in the Alside "
        "context — carry-over to LP lines unconfirmed, not encoded."
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
    more pieces) with the flag visible. Shake waste factor is PENDING —
    lap default 10% used, flagged."""
    flags = []
    if reveal_in is None:
        reveal_in = SHAKE_REVEAL_MIN_INCHES
        flags.append(
            "reveal: unconfirmed — priced at minimum reveal 6-7/8\" (worst case, more pieces)"
        )
    if waste is None:
        waste = DEFAULT_WASTE
        flags.append("shake waste factor PENDING confirmation — lap default 10% applied")
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
