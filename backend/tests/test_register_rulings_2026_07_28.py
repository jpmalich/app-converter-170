"""UNRULED-MATH REGISTER — ALL 8 RULED (2026-07-28, post Walk-v2 clearance).
Pins every register ruling as code. CONTRACTOR-SPEC where numeric;
changes require re-ratification.

 #1/#2 J-blocks & Mini-splits — SEALED AS-IS (contractor owns final qty)
 #3   LAP UNIFY — split path conforms to sealed 11 pcs/sq; 9.17 retires
 #4   SHAKE REVEAL — contractor field bounded 7"–10", default 7"
 #5   CAULK family-shaped — flat 2/job retired everywhere
 #6   SOFFIT 1.10 — recognized as the sealed baked-10 convention
 #7   TOUCH-UP color count — reads the estimate's Job Info selections
 #8   CATALOG-ONLY manual rows — manual BY DESIGN, cited
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lp_smartside_formulas as lp_formulas
from lp_smartside_formulas import lap_pieces_book, pieces_needed, LAP_PCS_PER_SQUARE
from routes.hover import _build_lines, _lp_profile_sku_entry
from lp_package import assemble_lp_package
from lp_conventions import (CATALOG_ONLY_MANUAL_BY_DESIGN,
                            SHAKE_REVEAL_FIELD_MIN_IN,
                            SHAKE_REVEAL_FIELD_MAX_IN,
                            SHAKE_REVEAL_RULE_SOURCE, shake_takeoff,
                            soffit_takeoff_area)


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("LP_AI_FORMULAS_V1", "true")
    yield


def _find(lines, name, tab=None):
    for l in lines:
        if l["name"] == name and (tab is None or l.get("tab") == tab):
            return l
    return None


# ── #1 / #2 — J-blocks & Mini-splits SEALED AS-IS ─────────────────────────
def test_r1_r2_jblocks_minisplits_sealed_as_is():
    lines = _build_lines({"siding_sqft": 2000, "window_count": 18,
                          "door_count": 4, "entry_door_count": 2})
    jb = _find(lines, "J blocks", "lp_smart")
    ms = _find(lines, "Mini Splits", "lp_smart")
    assert jb["qty"] == max(4, round(18 / 6 + 4 / 2))  # = 5
    assert ms["qty"] == max(1, round(2 / 2))           # = 1
    assert "SEALED AS-IS register #1" in jb["note"]
    assert "SEALED AS-IS register #2" in ms["note"]
    # minimums hold on tiny jobs — contractor owns the final qty
    small = _build_lines({"siding_sqft": 400})
    assert _find(small, "J blocks", "lp_smart")["qty"] == 4
    assert _find(small, "Mini Splits", "lp_smart")["qty"] == 1


# ── #3 — LAP UNIFY: split path ≡ sealed book 11 pcs/sq, forever ──────────
def test_r3_split_path_coverage_is_book_rate(flag_on):
    item, unit, cov = _lp_profile_sku_entry("lap")
    assert cov == pytest.approx(100.0 / LAP_PCS_PER_SQUARE)
    assert cov != pytest.approx(9.17)  # PDF divisor retired from ordering


@pytest.mark.parametrize("sqft", [500, 1000, 1780, 2064, 3333.5, 4504])
@pytest.mark.parametrize("waste", [0.0, 0.10, 0.30])
def test_r3_equivalence_pinned_both_paths_identical_sticks(flag_on, sqft, waste):
    _, _, cov = _lp_profile_sku_entry("lap")
    assert pieces_needed(sqft, cov, waste) == lap_pieces_book(sqft, waste=waste)


def test_r3_split_path_line_cites_lap_unify(flag_on):
    lines = _build_lines({
        "siding_sqft": 2000,
        "_per_profile_sqft": {"lap": 1500, "shake": 500},
        "_waste_pct": 0.10, "_default_family": "lap",
    })
    lap = _find(lines, '38 Series Lap 3/8" x 8" x 16\'', "lp_smart")
    assert lap is not None
    assert "LAP UNIFY register #3" in lap["note"]
    assert lap["qty"] == lap_pieces_book(1500, waste=0.10)


# ── #4 — SHAKE REVEAL: contractor field 7"–10", default 7" ────────────────
def test_r4_bounds_and_default():
    assert SHAKE_REVEAL_FIELD_MIN_IN == 7.0
    assert SHAKE_REVEAL_FIELD_MAX_IN == 10.0
    assert "maximum of 10 inches to a minimum of 7 inches" in SHAKE_REVEAL_RULE_SOURCE
    assert lp_formulas.DEFAULT_SHAKE_REVEAL_INCHES == 7.0


def test_r4_model_validator_422_shape():
    from models import EstimateIn
    from pydantic import ValidationError
    assert EstimateIn(shake_reveal_in=8.5).shake_reveal_in == 8.5
    assert EstimateIn().shake_reveal_in is None
    for bad in (6.5, 10.5, 0, -1):
        with pytest.raises(ValidationError):
            EstimateIn(shake_reveal_in=bad)


def test_r4_reveal_field_drives_split_path_coverage(flag_on):
    # default 7" → coverage 2.33; selected 8" → 2.67; 10" clamps to panel 9.875 → 3.29
    _, _, cov7 = _lp_profile_sku_entry("shake")
    assert cov7 == pytest.approx(2.33)
    _, _, cov8 = _lp_profile_sku_entry("shake", {"_shake_reveal_in": 8.0})
    assert cov8 == pytest.approx(2.67)
    _, _, cov10 = _lp_profile_sku_entry("shake", {"_shake_reveal_in": 10.0})
    assert cov10 == pytest.approx(3.29)  # panel physical max 9-7/8"


def test_r4_shake_line_names_the_reveal(flag_on):
    m = {"siding_sqft": 2000,
         "_per_profile_sqft": {"lap": 1500, "shake": 500},
         "_shake_reveal_in": 8.0}
    shake = _find(_build_lines(m), "Shake", "lp_smart")
    assert 'reveal 8"' in shake["note"] and "register #4" in shake["note"]
    # fewer pieces at deeper reveal than the 7" default, 15% waste on top
    assert shake["qty"] == pieces_needed(500, 2.67, 0.15)


def test_r4_shake_takeoff_default_is_ruled_seven():
    m = shake_takeoff(500.0)
    assert m["reveal_in"] == 7.0
    assert any("register #4" in f for f in m["flags"])
    # 500 ÷ 2.33 × 1.15 = 246.78 → 247 (was 252 at the pre-ruling 6-7/8" worst case)
    assert m["ordered_pcs"] == 247


def test_r4_interaction_with_sealed_44_per_sq_and_15pct():
    """The sealed 44 pcs/sq is the MIN-reveal (6-7/8") instantiation of
    coverage = 4' × reveal/12; the ruled field (7–10) walks the same curve
    and the sealed 15% waste applies on top regardless of reveal."""
    assert math.ceil(100.0 / lp_formulas.shake_coverage_sqft_per_pc(6.875)) == 44
    assert math.ceil(100.0 / lp_formulas.shake_coverage_sqft_per_pc(7.0)) == 43
    assert math.ceil(100.0 / lp_formulas.shake_coverage_sqft_per_pc(10.0)) == 31
    assert shake_takeoff(100.0, reveal_in=7.0)["waste_pct"] == 15


# ── #5 — CAULK family-shaped: flat 2/job retired everywhere ───────────────
def test_r5_lp_non_bb_one_tube_per_square():
    lines = _build_lines({"siding_sqft": 2000})
    c = _find(lines, "OSI Quad Max Caulking", "lp_smart")
    assert c["qty"] == 20  # 20 SQ → 20 tubes (not the retired flat 2)
    assert "1 tube per SQUARE" in c["note"]  # register tag out of UI wording 2026-07-29
    # small job: ceil, min 1 — the flat-2 floor is gone
    small = _find(_build_lines({"siding_sqft": 90}), "OSI Quad Max Caulking", "lp_smart")
    assert small["qty"] == 1


def test_r5_bb_keeps_sealed_1_per_23_sticks(flag_on):
    m = {"siding_sqft": 4504, "_per_profile_sqft": {"board_batten": 4504},
         "_force_profile_lines": True}
    lines = _build_lines(m)
    battens = _find(lines, '190 Series Trim 19/32" x 3" x 16\'', "lp_smart")["qty"]
    c = _find(lines, "OSI Quad Max Caulking", "lp_smart")
    assert c["qty"] == math.ceil(battens / 23.0 - 1e-9)
    assert "1 tube per 23 batten sticks" in c["note"]


def test_r5_vinyl_ascend_one_tube_per_opening():
    lines = _build_lines({"siding_sqft": 2000, "window_count": 12, "door_count": 3})
    for tab in ("vinyl", "ascend"):
        c = _find(lines, "Caulking (per color)", tab)
        assert c["qty"] == 15  # 12 windows + 3 doors
        assert "1 tube per opening" in c["note"]  # register tag out of UI wording 2026-07-29
    # no openings listed → min 1, never the retired flat 2
    c = _find(_build_lines({"siding_sqft": 900}), "Caulking (per color)", "vinyl")
    assert c["qty"] == 1


# ── #6 — SOFFIT 1.10 recognized as the sealed baked-10 convention ─────────
def test_r6_soffit_baked_10_unchanged():
    t = soffit_takeoff_area(213.0, overhang_in=12)
    assert t["waste_pct"] == 10  # single-bake pinned — citation lands, no change
    assert t["ordered_pcs"] == math.ceil(213.0 / 15.9 * 1.10)  # 12" panel at 12" overhang


# ── #7 — TOUCH-UP color count reads the estimate's Job Info selections ────
def _bb_meas():
    return {"_hover_source": True, "siding_sqft": 2064,
            "siding_with_openings_sqft": 2064,
            "outside_corner_count": 14, "outside_corner_lf": 140.3,
            "_per_profile_sqft": {"board_batten": 2064},
            "_force_profile_lines": True, "_waste_pct": 0.30}


def test_r7_touch_up_multiplies_by_distinct_selected_colors():
    pkg = assemble_lp_package(_bb_meas(), colors={
        "all": "Snowscape White", "opening_trim": "Abyss Black"})
    tk = _find(pkg["lines"], "Touch up kits")
    # base 2064 sqft → 20.64 SQ ÷ 11 → 2 kits per color × 2 distinct colors
    assert tk["qty"] == 4
    assert "register #7" in tk["note"]
    assert "Snowscape White" in tk["note"] and "Abyss Black" in tk["note"]


def test_r7_single_color_cited_not_multiplied():
    pkg = assemble_lp_package(_bb_meas(), colors={"all": "Quarry Gray"})
    tk = _find(pkg["lines"], "Touch up kits")
    assert tk["qty"] == 2
    assert "1 selected color" in tk["note"] and "register #7" in tk["note"]


def test_r7_no_colors_selected_base_stays():
    pkg = assemble_lp_package(_bb_meas())
    tk = _find(pkg["lines"], "Touch up kits")
    assert tk["qty"] == 2
    assert "selected color" not in (tk["note"] or "")  # nothing invented


def test_r7_tab_line_path_multiplies_too():
    """Tab/package parity: the tab-line spec multiplies by the same
    Job-Info color count the package path reads (never divergent)."""
    m = dict(_bb_meas())
    m["_lp_color_count"] = 2
    tk = _find(_build_lines(m), "Touch up kits", "lp_smart")
    assert tk["qty"] == 4
    assert "× 2 selected colors" in tk["note"]


# ── #8 — CATALOG-ONLY rows stay manual BY DESIGN ──────────────────────────
def test_r8_catalog_only_rows_never_grow_a_derivation(flag_on):
    lines = _build_lines({
        "siding_sqft": 4504, "eaves_lf": 308, "rakes_lf": 319,
        "outside_corner_count": 26, "outside_corner_lf": 175,
        "window_count": 30, "entry_door_count": 3,
        "_per_profile_sqft": {"board_batten": 4504},
        "_force_profile_lines": True,
    })
    emitted = {l["name"] for l in lines}
    for manual in CATALOG_ONLY_MANUAL_BY_DESIGN:
        assert manual not in emitted, (
            f"{manual}: catalog-only manual row grew a silent derivation "
            "(register #8 ruled 2026-07-28 — manual BY DESIGN)")
