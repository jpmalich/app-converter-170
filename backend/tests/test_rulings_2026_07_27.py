"""CONSOLIDATED RULINGS Q1–Q17 (2026-07-27) — sealed against 3 Degree Rd
ground truth (EST-562488, run hover-dfd4847fcd71-board_batten). Pins the
money-layer sitting: every ruling that landed as code, plus the
DERIVATION-PURITY invariant. All CONTRACTOR-SPEC; changes require
re-ratification."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routes.hover import (_build_lines, _soffit_total_split, _apply_color_tier,
                          _isc_540_pcs, _osc_lp_pcs, _frieze_540_pcs)
from lp_package import assemble_lp_package
from lp_conventions import MISC_LABOR_ROWS


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("LP_AI_FORMULAS_V1", "true")
    yield


# 3 Degree Rd measured inputs (Hover door, forced board_batten, waste 30%)
DEGREE3 = {
    "_hover_source": True,
    "siding_sqft": 4504, "eaves_lf": 308.25, "rakes_lf": 319.42,
    "outside_corner_count": 26, "outside_corner_lf": 175.42,
    "inside_corner_count": 24, "inside_corner_lf": 173.08,
    "opening_perimeter_lf": 535.08, "window_count": 30,
    "entry_door_count": 3, "patio_door_count": 1, "garage_door_count": 1,
    "overhang_in": 12, "soffit_sqft": 2620,
    "level_frieze_lf": 406.83, "sloped_frieze_lf": 276.5,
    "_per_profile_sqft": {"board_batten": 4504}, "_waste_pct": 0.30,
}


def _find(lines, name, tab=None):
    for l in lines:
        if l["name"] == name and (tab is None or l.get("tab") == tab):
            return l
    return None


def test_q1_tearoff_dumpster_presence_rows():
    lines = _build_lines({"siding_sqft": 1000})
    for tab in ("vinyl", "ascend", "lp_smart"):
        for nm in ("Tear-Off", "Dumpster"):
            l = _find(lines, nm, tab)
            assert l is not None, f"{nm} missing on {tab}"
            assert l["qty"] == 0 and l.get("qty_pending") is True
            assert "CONTRACTOR-ENTERED" in l["note"]
    assert "tear-off" in MISC_LABOR_ROWS and "dumpster" in MISC_LABOR_ROWS


def test_q2_porch_ceiling_implied_flag_only():
    from routes.lp_package_routes import _hover_mapping_contract
    m, flags = _hover_mapping_contract(dict(DEGREE3), "board_batten")
    codes = [f.get("code") for f in flags]
    assert "porch_ceiling_implied" in codes  # 2620/627.67 = 4.2' avg vs 1'
    assert not m.get("porch_ceiling_sqft")  # flag-only, never invents area
    m2, flags2 = _hover_mapping_contract(
        {"siding_sqft": 1000, "soffit_sqft": 200, "eaves_lf": 100,
         "rakes_lf": 100, "overhang_in": 12}, "lap")
    assert "porch_ceiling_implied" not in [f.get("code") for f in flags2]


def test_q3_fascia_coil_width_conditional():
    m = {"siding_sqft": 1000, "eaves_lf": 100, "rakes_lf": 100}
    l = _find(_build_lines(m), ".019 Coil (1 per 50' fascia)", "vinyl")
    assert l["qty"] == 2.0  # ≤10" fascia → 24" coil ripped in half = 100 LF/roll
    assert "100 LF/roll" in l["note"]
    l2 = _find(_build_lines({**m, "fascia_width_in": 12}),
               ".019 Coil (1 per 50' fascia)", "vinyl")
    assert l2["qty"] == 4.0  # >10" → 50 LF/roll
    assert "50 LF/roll" in l2["note"]


def test_q4_dormer_pooling_no_separate_skus():
    meas = {"siding_sqft": 2000, "eaves_lf": 108, "rakes_lf": 73.4,
            "_ai_dormers": [{"width_ft": 15, "knee_wall_height_ft": 5},
                            {"width_ft": 15, "knee_wall_height_ft": 5}]}
    pkg = assemble_lp_package(meas)
    names = [l["name"] for l in pkg["lines"]]
    assert not any("Dormer" in n for n in names)
    fas = _find(pkg["lines"], '440 Series Trim 4/4" x 8" x 16\'')
    assert "dormer fascia 30" in fas["note"]
    assert fas["qty"] == 14  # 7 + 5 + ceil(30/16)=2 per-segment (Q16)
    osc = _find(pkg["lines"], '540 Series OSC 5/4" x 6" x 16\'')
    assert osc is not None and "dormer corners pooled into OSC" in osc["note"]
    assert osc["qty"] == 4  # 2 dormers × 2 posts × max(1, ceil(5/16))


def test_q6_q7_photo_door_stories_and_vents():
    from routes.ai_measure import _aggregate_to_hover_shape
    raw = {"openings_schedule": [
        {"type": "vent", "count": 2},
        {"type": "window", "count": 1, "width_in": 36, "height_in": 48},
    ]}
    m = _aggregate_to_hover_shape(raw)
    assert m["vent_count"] == 2
    assert m["shutter_count"] == 0
    assert m["window_count"] == 1


def test_q8_color_tier_relands_standard_rows():
    lines = [
        {"tab": "vinyl", "name": "Outside corners Standard color", "note": "x"},
        {"tab": "vinyl", "name": "Soffit & fascia Charter Oak Standard Color", "note": "y"},
        {"tab": "lp_smart", "name": "Touch up kits", "note": "z"},
    ]
    out = _apply_color_tier(copy.deepcopy(lines), "architectural")
    assert out[0]["name"] == "Outside corners Architectural color"
    assert out[1]["name"] == "Soffit & fascia Charter Oak Architectural color"
    assert "Q8 ruled 2026-07-27" in out[0]["note"]
    assert out[2]["name"] == "Touch up kits"  # LP tab untouched
    same = _apply_color_tier(copy.deepcopy(lines), "standard")
    assert same[0]["name"] == "Outside corners Standard color"


def test_q11_lp_bb_base_is_nothing():
    from routes.lp_package_routes import _force_profile_measurements
    m = _force_profile_measurements(
        {"starter_lf": 654.67, "siding_sqft": 4504}, "board_batten")
    assert m["starter_lf"] == 0  # B&B: no starter — and NOTHING replaces it
    pkg = assemble_lp_package({**DEGREE3, "starter_lf": 0})
    names = [l["name"] for l in pkg["lines"]]
    assert not any("Starter" in n for n in names)
    assert not any("J-Channel" in n or "J Channel" in n for n in names)


def test_q13_per_corner_stick_math():
    # 3 Degree Rd: OSC 26 corners @ 6.75' avg → 26 (was pooled 11)
    assert _osc_lp_pcs({"outside_corner_count": 26, "outside_corner_lf": 175.42}) == 26
    # ISC 24 corners @ 7.21' avg → 24 (was pooled 11)
    assert _isc_540_pcs({"inside_corner_count": 24, "inside_corner_lf": 173.08}) == 24
    # tall corners: 2 × 18' → 2 sticks each
    assert _isc_540_pcs({"inside_corner_count": 2, "inside_corner_lf": 36}) == 4
    # pooled ONLY when the count is unavailable (Q16 fallback)
    assert _osc_lp_pcs({"outside_corner_lf": 175.42}) == 11


def test_q14_measured_soffit_total_governs():
    v, c = _soffit_total_split(DEGREE3)
    assert v == 1286.7 and c == 1333.3  # eave/rake proportional split
    lines = _build_lines(dict(DEGREE3))
    vented = _find(lines, "38 Series Soffit 16 x 16 Vented", "lp_smart")
    closed = _find(lines, "38 Series Soffit 16 x 16 Closed", "lp_smart")
    assert vented["qty"] == 67 and "MEASURED soffit TOTAL governs" in vented["note"]
    assert closed["qty"] == 69
    # Q14a: the measured total also KEEPS the Closed row on the assembled
    # LP-native package (eaves-only removal is fallback-basis only)
    pkg = assemble_lp_package(dict(DEGREE3))
    pkg_closed = _find(pkg["lines"], "38 Series Soffit 16 x 16 Closed")
    assert pkg_closed is not None and pkg_closed["qty"] == 69
    # Q14b: vinyl is the SUBSTITUTION target — its row pulls the measured
    # total too: 2620 ÷ 10 = 262 (3 Degree Rd real: 260 pcs installed)
    vinyl = _find(lines, "Soffit & fascia Charter Oak Standard Color", "vinyl")
    assert vinyl["qty"] == 262
    # explicit per-surface breakdown still governs FIRST
    l2 = _find(_build_lines({**DEGREE3, "_soffit_vented_sqft": 216}),
               "38 Series Soffit 16 x 16 Vented", "lp_smart")
    assert "report per-surface basis" in l2["note"]


def test_q15_caulk_and_touchup_scaling(flag_on):
    lines = _build_lines(dict(DEGREE3))
    caulk = _find(lines, "OSI Quad Max Caulking", "lp_smart")
    # B&B @8" o.c.: 4504 ÷ (2/3) = 6756 LF → 423 sticks; ÷23 → 19 tubes
    assert caulk["qty"] == 19
    assert "1 tube per 23 batten sticks" in caulk["note"]
    touch = _find(lines, "Touch up kits", "lp_smart")
    assert touch["qty"] == 4  # 45.04 SQ ÷ 11 per color → 4 (real: 4)
    assert "1 kit per 11 SQ per color" in touch["note"]
    # non-B&B: register #5 (ruled 2026-07-28) retired the flat 2/job —
    # LP non-B&B = 1 tube per SQUARE: 1000 sqft = 10 SQ → 10 tubes
    caulk2 = _find(_build_lines({"siding_sqft": 1000}), "OSI Quad Max Caulking", "lp_smart")
    assert caulk2["qty"] == 10


def test_q10_frieze_consumed():
    assert _frieze_540_pcs(DEGREE3) == 26 + 18  # per-segment (Q16)
    wrap = _find(_build_lines(dict(DEGREE3)),
                 '540 Series Trim 5/4" x 4" x 16\'', "lp_smart")
    assert "frieze" in wrap["note"] and "Q10 ruled 2026-07-27" in wrap["note"]
    # wrap 32 + frieze 44 + ISC 24 = 100 (3 Degree Rd re-derive; real 142 —
    # residual logged as evidence, no invented scope)
    assert wrap["qty"] == 100


def test_derivation_purity_pinned():
    """DERIVATION PURITY (confirmed + PINNED 2026-07-27): every derivation
    is a pure function of THIS estimate's own measurements + coded
    conventions — no derivation reads another estimate, quote, or
    historical job at derivation time. Real-job lists (3 Degree Rd) enter
    ONLY as evidence for rulings that land as code."""
    import inspect
    import lp_package as lpk
    import routes.hover as hv
    # static: the derivation modules never import the DB layer
    src_pkg = inspect.getsource(lpk)
    assert "import db" not in src_pkg and "from db" not in src_pkg
    src_bl = inspect.getsource(hv._build_lines)
    assert "db." not in src_bl and "await" not in src_bl
    # runtime: same inputs → byte-identical outputs, inputs never mutated
    meas = dict(DEGREE3)
    snap = copy.deepcopy(meas)
    a = assemble_lp_package(dict(meas))
    b = assemble_lp_package(dict(meas))
    assert a == b
    la = _build_lines(dict(meas))
    lb = _build_lines(dict(meas))
    assert la == lb
    assert meas == snap
