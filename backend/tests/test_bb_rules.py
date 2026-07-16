"""Board & Batten rules — RULED 2026-07-16 (source LPZB0884 sheet).

Pins:
  • field: wall_area ÷ 40 × (1+waste) → whole 4'×10' panels
  • battens: LF = wall_area ÷ spacing(ft) + 1 run × wall height;
    pieces = ceil(LF ÷ 16); NO waste term on battens
  • spacing must divide 48 (12/16/24 o.c.) — seam battens at every
    48" joint land on schedule; anything else raises
  • Nickel Gap reveal LOCKED at 7" — constant coverage, no reveal
    parameter, no frontend input field
  • held items registry (batten SKU / default spacing / starter /
    gable factor / panel waste %) stays flagged until Howard rules
"""
import inspect
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lp_smartside_formulas as lp  # noqa: E402

FRONTEND_SRC = Path("/app/frontend/src")


def test_field_panels_ruled_math():
    assert lp.BB_PANEL_COVERAGE_SQFT == 40.0
    assert lp.board_batten_panel_pieces(400.0, waste=0.0) == 10
    assert lp.board_batten_panel_pieces(400.0, waste=0.10) == 11
    assert lp.board_batten_panel_pieces(401.0, waste=0.0) == 11  # whole panels
    assert lp.board_batten_panel_pieces(0, waste=0.0) == 0


def test_batten_lf_ruled_formula():
    # LF = area ÷ spacing_ft + height (the +1 run per wall)
    assert lp.bb_batten_lf(400.0, 16, 0.0) == 300.0        # 400 ÷ (4/3)
    assert lp.bb_batten_lf(400.0, 16, 10.0) == 310.0
    assert lp.bb_batten_lf(400.0, 12, 8.0) == 408.0        # 400 ÷ 1
    assert lp.bb_batten_lf(400.0, 24, 8.0) == 208.0        # 400 ÷ 2


def test_batten_pieces_no_waste():
    # ceil(LF ÷ 16) with NO waste factor
    assert lp.bb_batten_pieces(310.0) == 20
    assert lp.bb_batten_pieces(320.0) == 20
    assert lp.bb_batten_pieces(320.1) == 21
    # aggregate helper: 400 sqft @16" +0 height → 300 LF → 19 pcs
    assert lp.board_batten_batten_pieces(400.0) == 19
    # old behavior applied 1.10 waste (would have been 21) — ruled out
    assert lp.board_batten_batten_pieces(400.0) != math.ceil(300 * 1.10 / 16)


def test_spacing_must_divide_48():
    assert lp.VALID_BATTEN_SPACINGS_IN == (12, 16, 24)
    for bad in (10, 18, 20, 32, 48, 0, -12):
        try:
            lp.bb_batten_lf(100.0, bad, 0.0)
            assert False, f"spacing {bad} must raise"
        except ValueError:
            pass
    for ok in (12, 16, 24):
        assert 48 % ok == 0
        lp.bb_batten_lf(100.0, ok, 0.0)


def test_nickel_gap_locked_7in():
    assert lp.NICKEL_GAP_COVERAGE_SQFT_PER_PC == 9.33  # 16 × 7 ÷ 12
    # no reveal parameter — the 7" reveal is pinned, not an input
    params = inspect.signature(lp.nickel_gap_pieces).parameters
    assert "reveal" not in " ".join(params.keys()).lower()
    # no frontend input field for a nickel-gap reveal
    for f in FRONTEND_SRC.rglob("*.js*"):
        if "node_modules" in str(f):
            continue
        src = f.read_text(errors="ignore").lower()
        if "nickel" in src:
            assert "nickel_gap_reveal" not in src and "nickelgapreveal" not in src, f


def test_held_items_registry():
    assert set(lp.BB_HELD_PENDING_HOWARD.keys()) == {
        "batten_sku", "default_spacing", "starter_treatment",
        "gable_factor", "panel_waste_pct",
    }
    # gable factor: lap's ×0.7 must not silently apply to panels — the
    # module carries no gable factor constant for B&B
    assert not hasattr(lp, "BB_GABLE_FACTOR")
