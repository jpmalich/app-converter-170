"""SEND-32 (Howard sealed 2026-08-16) — Rulings JJ + KK pins.

RULING JJ — A RAIL CANDIDATE CARRIES EXACTLY ONE DIMENSION TOKEN. A
size pair (2-11½ × 3-11½) is an annotation, not a chain dimension.
Same shape as II: one structural property generalizing to every note
form without naming any glyph. A page moving ESTABLISHED →
INDETERMINATE under JJ is a real result, not a regression.

RULING KK — THE 2" IS A REFERENCE PLANE, NOT A DISAGREEMENT. Foundation
plans dimension the foundation wall; floor plans dimension framing.
Siding wraps the framing → first-floor governs siding; the foundation
figure stays visible alongside. THE DISTINGUISHER (the whole ruling):
same-plane disagreement = GENUINE CONTRADICTION, still reported as one;
cross-plane difference = two planes, both correct; unknown plane =
INDETERMINATE, the cases cannot be told apart — no default, no
magnitude threshold, never "prefer the later sheet".
"""
import sys

sys.path.insert(0, "/app/backend")

import ocr_geometry as og


def _run(raw, x, y, w, h, axis, src="upright"):
    return {"norm": raw, "raw": raw,
            "loc": {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h},
            "src": src, "axis": axis}


# ---------------------------------------------------------------------------
# RULING JJ — single dimension token
# ---------------------------------------------------------------------------

def test_jj_size_pair_is_never_a_rail():
    # The live polluter from p6 — two dimension tokens joined by the
    # '×' glyph, which is NOT alphabetic and slipped Ruling II.
    assert og.dimension_token_count("2-11%° × 3-119°") == 2
    assert og.is_rail_candidate("2-11%° × 3-119°") is False
    # Single-token chain dimensions stay rails.
    assert og.is_rail_candidate("58-0°") is True
    assert og.is_rail_candidate("33'-0'") is True
    assert og.is_rail_candidate("5'10°") is True


def test_jj_recovers_the_true_bottom_rail_on_a_p6_shape():
    runs = [
        _run("58-0°", 55.0, 18.0, 1.3, 0.9, og.HORIZONTAL),   # top rail
        _run("58-0°", 55.0, 70.0, 1.4, 1.2, og.HORIZONTAL),   # true bottom rail
        _run("2-11%° × 3-119°", 50.0, 73.3, 3.0, 0.9, og.HORIZONTAL),  # size pair below it
        _run("30-0*", 28.9, 41.3, 0.55, 1.5, og.VERTICAL),
        _run("33'-0\"", 81.8, 39.7, 0.55, 1.5, og.VERTICAL),
    ]
    env = og.rail_envelope(runs)
    assert env["status"] == "ESTABLISHED"
    assert env["rails"]["bottom"] == "58-0°"
    assert env["y_hi"] == 70.0


def test_jj_established_to_indeterminate_is_a_real_result():
    # When the ONLY horizontal candidates are size pairs, the envelope
    # honestly cannot be established — not a regression.
    runs = [
        _run("2-11%° × 3-119°", 50.0, 20.0, 3.0, 0.9, og.HORIZONTAL),
        _run("3-0° × 5-0°", 50.0, 70.0, 3.0, 0.9, og.HORIZONTAL),
        _run("30-0*", 28.9, 41.3, 0.55, 1.5, og.VERTICAL),
        _run("33'-0\"", 81.8, 39.7, 0.55, 1.5, og.VERTICAL),
    ]
    env = og.rail_envelope(runs)
    assert env["status"] == og.INDETERMINATE
    assert "horizontal" in env["reason"]


# ---------------------------------------------------------------------------
# RULING KK — reference plane vs genuine contradiction
# ---------------------------------------------------------------------------

def test_kk_cross_plane_difference_is_two_planes_framing_governs_siding():
    v = og.reference_plane_verdict([
        {"value": "30-2", "page": 4, "plane": "foundation"},
        {"value": "30-0*", "page": 6, "plane": "framing"},
    ], material="siding")
    assert v["status"] == "REFERENCE_PLANES"
    assert v["governs"]["plane"] == "framing"
    assert v["governs"]["value"] == "30-0*"
    # The foundation figure is VISIBLE ALONGSIDE — not hidden, not a conflict.
    assert v["alongside"][0]["plane"] == "foundation"
    assert v["alongside"][0]["value"] == "30-2"


def test_kk_same_plane_disagreement_stays_a_genuine_contradiction():
    # THE DISTINGUISHER: two framing sheets disagreeing is a conflict
    # KK must NOT swallow — this is what separates the ruling from
    # "prefer the later sheet".
    v = og.reference_plane_verdict([
        {"value": "30-0", "page": 6, "plane": "framing"},
        {"value": "31-0", "page": 7, "plane": "framing"},
    ])
    assert v["status"] == "CONTRADICTION"
    assert "SAME reference plane" in v["why"]


def test_kk_unknown_plane_cannot_distinguish_and_says_so():
    v = og.reference_plane_verdict([
        {"value": "30-2", "page": 4, "plane": None},
        {"value": "30-0", "page": 6, "plane": "framing"},
    ])
    assert v["status"] == og.INDETERMINATE
    assert "cannot be told apart" in v["why"]


def test_kk_governing_plane_missing_never_substitutes_the_other():
    v = og.reference_plane_verdict([
        {"value": "30-2", "page": 4, "plane": "foundation"},
    ], material="siding")
    assert v["status"] == og.INDETERMINATE
    assert "never substitutes" in v["why"]


def test_kk_unruled_material_has_no_default_plane():
    v = og.reference_plane_verdict([
        {"value": "30-2", "page": 4, "plane": "foundation"},
        {"value": "30-0", "page": 6, "plane": "framing"},
    ], material="roofing")
    assert v["status"] == og.INDETERMINATE
    assert "no default" in v["why"]


def test_kk_agreeing_planes_report_agree():
    v = og.reference_plane_verdict([
        {"value": "33-0", "page": 4, "plane": "foundation"},
        {"value": "33'-0\"", "page": 6, "plane": "framing"},
    ])
    assert v["status"] == "AGREE"
    assert v["governs"]["plane"] == "framing"


def test_kk_plane_attribution_from_sheet_title_never_guessed():
    assert og.plane_for_sheet_title("FOUNDATION PLAN") == "foundation"
    assert og.plane_for_sheet_title("FIRST FLOOR PLAN") == "framing"
    assert og.plane_for_sheet_title("SECOND FLOOR PLAN") == "framing"
    assert og.plane_for_sheet_title("FRONT & REAR ELEVATIONS") is None
    assert og.plane_for_sheet_title(None) is None
