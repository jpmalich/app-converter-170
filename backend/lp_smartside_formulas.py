"""LP SmartSide AI auto-population formulas (Iter 78ab — 2026-02-28).

Source: LP_SmartSide_Reference.pdf (Howard, 2026-02-28). Material
quantity formulas for the 5 LP product families plus default profile
selections agreed with Howard:

    - 8" Lap   (default lap profile)
    - 16" Soffit  (default soffit panel)
    - 7" Shake reveal  (default cedar shake reveal)
    - Nickel Gap is fixed 7" reveal (no user choice)
    - Board & Batten field panel is 4×10 = 40 sqft; batten LF from PDF.

This module is the single source of truth for LP material math. It is
imported by `routes/hover.py` (which feeds HOVER PDF, AI Photo Measure,
AI Blueprint, and manual estimate creation through `_build_lines`), so
flipping the feature flag here updates all four ingest paths at once.

Staging
-------
Behavior is gated by env `LP_AI_FORMULAS_V1` (default OFF). When OFF the
legacy ~9.09 sqft/PCS conversion in `_PROFILE_SKU_MAP` continues to fire
and contractors see the same quotes as before. When ON, AI auto-
population uses the PDF-accurate per-profile coverage rates + adds the
190 Series batten line when board-and-batten is detected.

Per Howard (2026-02-28):
  * Q1=D — apply to HOVER + AI Measure + Blueprint + manual entry
    (all four paths consume `_build_lines`, so this single module
    covers them).
  * Q2=8" Lap / 16" Soffit / 7" Shake reveal as defaults.
  * Q3=stage behind a flag, do not enable yet.
  * Q4=A — auto-populate MATERIAL qty only; do not touch labor lines.
  * Q5=keep existing trim/accessory formulas as-is; bump 540 Series
    when shakes are detected; do NOT auto-add J-channel for Nickel Gap
    (kept as a constant for a future iteration); battens get a new
    auto-fill row mapped to the existing catalog SKU
    `190 Series Trim 19/32" x 3" x 16'`.

Coverage data verified against LP coverage chart LPZB0884.
"""
from __future__ import annotations
import math
import os

# ────────────────────── Feature flag ──────────────────────


def is_enabled() -> bool:
    """LP AI formula module is gated by env. Default OFF so existing
    behavior is preserved until Howard greenlights production.

    A per-request override (set via `override_flag` context manager
    below) takes precedence over the env value so the admin preview
    can compute both legacy + PDF qtys back-to-back inside one
    request without env mutation.
    """
    if _OVERRIDE_FLAG is not None:
        return _OVERRIDE_FLAG
    return os.environ.get("LP_AI_FORMULAS_V1", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


# Thread-unsafe but request-local override. Only used by the admin
# preview endpoint (which is synchronous within a single async task)
# and by tests.
_OVERRIDE_FLAG: bool | None = None


class override_flag:  # noqa: N801 — context-manager style camel name
    """Temporarily force `is_enabled()` to a fixed value for the
    duration of the `with` block. Restores the prior state on exit."""

    def __init__(self, value: bool):
        self.value = bool(value)
        self._prev: bool | None = None

    def __enter__(self):
        global _OVERRIDE_FLAG
        self._prev = _OVERRIDE_FLAG
        _OVERRIDE_FLAG = self.value
        return self

    def __exit__(self, *exc):
        global _OVERRIDE_FLAG
        _OVERRIDE_FLAG = self._prev
        return False


# ────────────────────── Defaults (Howard, 2026-02-28) ──────────────────────

DEFAULT_LAP_PROFILE = "8\" Lap"
DEFAULT_SOFFIT_WIDTH = "16\" Soffit"
DEFAULT_SHAKE_REVEAL_INCHES = 7.0

# Standard PDF waste factor for every LP family. Contractor can still
# bump it manually on the estimate.
DEFAULT_WASTE = 0.10  # 10%

# ────────────────────── Lap Siding (38 Series, 16' boards) ──────────────────────
# Per PDF: face width − 1" overlap = reveal. coverage = 16ft × reveal/12.
# 6" Lap is DISCONTINUED per catalog Iter 78x, so we don't carry it.
LAP_PROFILES: dict[str, dict] = {
    "6\" Lap":  {"reveal_in": 4.875, "coverage_sqft_per_pc": 6.50},
    "7\" Lap":  {"reveal_in": 5.875, "coverage_sqft_per_pc": 7.83},
    "8\" Lap":  {"reveal_in": 6.875, "coverage_sqft_per_pc": 9.17},
    "12\" Lap": {"reveal_in": 10.875, "coverage_sqft_per_pc": 14.50},
}

# ────────────────────── Cedar Texture Shakes (4' panels) ──────────────────────
# Variable reveal 6-7/8" to 9-7/8". coverage = 4ft × reveal/12.
# PDF data table values verified.
SHAKE_REVEAL_COVERAGE: dict[float, float] = {
    6.875: 2.29,
    7.000: 2.33,
    8.000: 2.67,
    9.875: 3.29,
}
SHAKE_REVEAL_MIN_INCHES = 6.875
SHAKE_REVEAL_MAX_INCHES = 9.875


def shake_coverage_sqft_per_pc(reveal_inches: float) -> float:
    """Coverage = 4ft × reveal/12. Clamps to PDF min/max."""
    r = max(SHAKE_REVEAL_MIN_INCHES, min(SHAKE_REVEAL_MAX_INCHES, float(reveal_inches)))
    return round(4.0 * r / 12.0, 2)


# ────────────────────── Nickel Gap (8" nom., fixed 7" reveal, 16' boards) ──────────────────────
NICKEL_GAP_COVERAGE_SQFT_PER_PC = 9.33  # = 16 × 7 ÷ 12

# Future iteration (per Howard 2026-02-28 Q3=C "keep in memory"):
# Nickel Gap concealed-fastening installations may need J-channel
# takeoff. Holding the rule here until Howard turns it on.
NICKEL_GAP_J_CHANNEL_NEEDS_REVIEW = True  # noqa: F841 — placeholder

# ────────────────────── Soffit (38 Series, 16' boards) ──────────────────────
SOFFIT_PROFILES: dict[str, dict] = {
    "12\" Soffit": {"actual_width_in": 11.94, "length_ft": 16, "coverage_sqft_per_pc": 15.9},
    "16\" Soffit": {"actual_width_in": 15.94, "length_ft": 16, "coverage_sqft_per_pc": 21.3},
    "24\" Soffit": {"actual_width_in": 23.94, "length_ft": 16, "coverage_sqft_per_pc": 31.9},
    "4'x8' Soffit Panel": {"actual_width_in": 47.88, "length_ft": 8, "coverage_sqft_per_pc": 31.9},
}

# ────────────────────── Board & Batten (4×10 panels + batten strips) ──────────────────────
# RULED (Howard 2026-07-16, source LPZB0884 sheet):
#   field   = 4'×10' panels @ 40 sq ft nominal; wall_area ÷ 40 × (1+waste) → whole panels
#   battens = separate line, 16' stock;
#             LF per wall = wall_area ÷ spacing(ft) + 1 run × wall height
#             seam battens mandatory at every 48" panel joint — spacing MUST
#             divide 48 (12/16/24 o.c. valid) so every seam lands on a
#             scheduled batten; pieces = ceil(LF ÷ 16), NO waste term on battens.
BB_PANEL_COVERAGE_SQFT = 40.0  # 4ft × 10ft nominal
VALID_BATTEN_SPACINGS_IN = (12, 16, 24)  # every 48" seam must land on a batten
DEFAULT_BATTEN_SPACING_IN = 16  # sheet's "standard look" — default NOT ratified (see BB_HELD)

# 190 Series Trim is the EXISTING catalog mapping for the batten strip —
# product/width + SKU not ratified (see BB_HELD).
BATTEN_CATALOG_SKU = '190 Series Trim 19/32" x 3" x 16\''
BATTEN_STOCK_LENGTH_FT = 16.0

# Items HELD pending Howard's ruling — derivations must FLAG lines that
# depend on these, never silently assume:
BB_HELD_PENDING_HOWARD = {
    "batten_sku": "batten product/width + SKU — 190 Series 3\"×16' is the existing mapping, NOT ratified",
    "default_spacing": "default o.c. spacing — 16\" is the sheet's 'standard look', NOT ratified",
    "starter_treatment": "B&B starter treatment — unruled",
    "gable_factor": "panel gable factor — lap's ×0.7 does NOT auto-carry to panels, B&B gable rule unruled",
    "panel_waste_pct": "panel waste % — unruled; derivations compute at 0% and flag",
}


# ────────────────────── Shake → 540 Series bump (Q2 = A) ──────────────────────
# PDF: "LP recommends 540 Series Trim when reveal is between 7" and 10""
# for shakes. Adds belly-band + termination trim allowance. Per Howard
# we bump the 540 Series qty by this amount whenever shake sqft > 0.
SHAKE_540_BUMP_PCS_PER_100_SQFT = 2  # 2 pieces of 16' × 5/4"×4" per 100 sqft of shake field


# ────────────────────── Public API ──────────────────────


def lap_coverage_sqft_per_pc(profile: str | None = None) -> float:
    """Lookup coverage by profile name. Falls back to the 8" default."""
    key = profile or DEFAULT_LAP_PROFILE
    if key not in LAP_PROFILES:
        key = DEFAULT_LAP_PROFILE
    return float(LAP_PROFILES[key]["coverage_sqft_per_pc"])


def soffit_coverage_sqft_per_pc(panel_name: str | None = None) -> float:
    key = panel_name or DEFAULT_SOFFIT_WIDTH
    if key not in SOFFIT_PROFILES:
        key = DEFAULT_SOFFIT_WIDTH
    return float(SOFFIT_PROFILES[key]["coverage_sqft_per_pc"])


def pieces_needed(
    wall_area_sqft: float,
    coverage_sqft_per_pc: float,
    waste: float = DEFAULT_WASTE,
) -> int:
    """Generic LP material qty: ceil(area / coverage × (1 + waste))."""
    if wall_area_sqft <= 0 or coverage_sqft_per_pc <= 0:
        return 0
    return int(math.ceil(float(wall_area_sqft) / float(coverage_sqft_per_pc) * (1.0 + float(waste))))


def lap_pieces(wall_area_sqft: float, profile: str | None = None,
               waste: float = DEFAULT_WASTE) -> int:
    return pieces_needed(wall_area_sqft, lap_coverage_sqft_per_pc(profile), waste)


def shake_pieces(wall_area_sqft: float,
                 reveal_inches: float = DEFAULT_SHAKE_REVEAL_INCHES,
                 waste: float = DEFAULT_WASTE) -> int:
    return pieces_needed(
        wall_area_sqft, shake_coverage_sqft_per_pc(reveal_inches), waste,
    )


def nickel_gap_pieces(wall_area_sqft: float,
                      waste: float = DEFAULT_WASTE) -> int:
    return pieces_needed(wall_area_sqft, NICKEL_GAP_COVERAGE_SQFT_PER_PC, waste)


def soffit_pieces(soffit_area_sqft: float, panel_name: str | None = None,
                  waste: float = DEFAULT_WASTE) -> int:
    return pieces_needed(
        soffit_area_sqft, soffit_coverage_sqft_per_pc(panel_name), waste,
    )


def board_batten_panel_pieces(wall_area_sqft: float,
                              waste: float = DEFAULT_WASTE) -> int:
    """RULED: wall_area ÷ 40 × (1+waste) → whole panels. NOTE: the waste
    VALUE for panels is held pending Howard (BB_HELD panel_waste_pct)."""
    return pieces_needed(wall_area_sqft, BB_PANEL_COVERAGE_SQFT, waste)


def bb_batten_lf(wall_area_sqft: float, spacing_in: int = DEFAULT_BATTEN_SPACING_IN,
                 wall_height_ft: float = 0.0) -> float:
    """RULED batten linear feet for ONE wall:
    LF = wall_area ÷ spacing(ft) + 1 run × wall_height.
    Spacing must divide 48 so every 48" panel seam lands on a scheduled
    batten (12/16/24 o.c. valid)."""
    spacing_in = int(spacing_in)
    if spacing_in not in VALID_BATTEN_SPACINGS_IN or 48 % spacing_in != 0:
        raise ValueError(
            f"batten spacing {spacing_in}\" o.c. invalid — must divide 48 "
            f"(valid: {VALID_BATTEN_SPACINGS_IN}) so seam battens land on schedule")
    if wall_area_sqft <= 0:
        return 0.0
    return float(wall_area_sqft) / (spacing_in / 12.0) + float(wall_height_ft or 0.0)


def bb_batten_pieces(total_lf: float) -> int:
    """RULED: pieces = ceil(LF ÷ 16). NO waste term on battens."""
    if total_lf <= 0:
        return 0
    return int(math.ceil(float(total_lf) / BATTEN_STOCK_LENGTH_FT))


def board_batten_batten_pieces(
    wall_area_sqft: float,
    spacing_in: int = DEFAULT_BATTEN_SPACING_IN,
    wall_height_ft: float = 0.0,
) -> int:
    """Aggregate helper (hover ingest path): ruled LF → 16' pieces."""
    return bb_batten_pieces(bb_batten_lf(wall_area_sqft, spacing_in, wall_height_ft))


def shake_540_series_bump(shake_sqft: float) -> int:
    """Belly-band + termination 540 Series Trim bump per Howard (Q2=A).
    Returns extra pieces of 540 Series 5/4"×4"×16' to add when shakes
    are present."""
    if shake_sqft <= 0:
        return 0
    return int(math.ceil(shake_sqft / 100.0 * SHAKE_540_BUMP_PCS_PER_100_SQFT))
