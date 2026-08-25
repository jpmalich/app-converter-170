"""SEND-127 pins (Howard ruled 2026-08-25) — EVIDENCE-AND-ATTRIBUTION-OR-NULL.

A figure may be DISPLAYED with a flag when it is located but
unattributed. It may NOT feed a quantity until its attribution is
established. Split by CONSUMER, not by value:
  display / read-back → may show the flagged figure
  anything reaching ft², LF or a count → refuses

Dart emitted 1,280.53 ft² of gable and 170 LF of starter on ONE located
56'-0" claimed by two faces (sealed truth: 50'-0" on both) while every
height correctly refused — the gable lane needs no height, so no height
refusal stopped it.
"""
import copy

import measure_staging as staging
from foreign_drafter_scoreboard import (
    CLAIM_FAILS_SAFE, CLAIM_NEITHER, CLAIM_READS,
    FOREIGN_DRAFTER_SCOREBOARD, PRE_SEND127_LEAK, earned_claim,
    read_claim_earned, unattributed_lanes)
from routes.ai_blueprint import (_aggregate_to_hover_shape,
                                 _attribution_gate,
                                 _null_computed_lf_lanes,
                                 _one_source_one_path_guard,
                                 _unattributed_dim_paths,
                                 build_blueprint_readback)


def _two_faces_one_quote():
    """Dart's shape: left and right both fed from ONE located 56'-0",
    and the main plane's rake computed from the same quote."""
    return {
        "walls": [
            {"label": "front", "width_ft": 58.0, "height_ft": None,
             "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": None, "height_ft": None,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 56.0, "height_ft": None,
             "gable_triangle_height_ft": 16.33},
            {"label": "right", "width_ft": 56.0, "height_ft": None,
             "gable_triangle_height_ft": 16.33},
        ],
        "roof_planes": [{"label": "main", "rake_lf": 136.0}],
        "outside_corner_heights_ft": [18.5, 18.5, 18.5, 18.5],
        "starter_lf": 228.0,
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 58.0, "page": 4,
                                     "from": "58'-4\""},
            "walls.left.width_ft": {"v": 56.0, "page": 4,
                                    "from": "56'-0\""},
            "walls.right.width_ft": {"v": 56.0, "page": 4,
                                     "from": "56'-0\""},
            "roof_planes.main.rake_lf": {"v": 136.0, "page": 4,
                                         "from": "56'-0\""},
            # dart's plate quote: two faces' heights AND all four corner
            # heights drew on one 9'-4" — the corner LF lane is a pure
            # quantity input, so it dies where it sits.
            "walls.front.height_ft": {"v": 18.5, "page": 5,
                                      "from": "9'-4\""},
            "walls.left.height_ft": {"v": 18.5, "page": 5,
                                     "from": "9'-4\""},
            "corner_heights.0": {"v": 18.5, "page": 5, "from": "9'-4\""},
            "corner_heights.1": {"v": 18.5, "page": 5, "from": "9'-4\""},
            "corner_heights.2": {"v": 18.5, "page": 5, "from": "9'-4\""},
            "corner_heights.3": {"v": 18.5, "page": 5, "from": "9'-4\""},
        },
    }


def _own_quote_per_face():
    """Boni's shape: every face carries its OWN located quote — no share,
    so nothing may refuse. The gate must not be a blanket kill."""
    return {
        "walls": [
            {"label": "front", "width_ft": 58.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 58.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 39.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 8.0},
            {"label": "right", "width_ft": 39.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 8.0},
        ],
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 58.0, "page": 6, "from": "58'-0\""},
            "walls.back.width_ft": {"v": 58.0, "page": 5, "from": "58'-0\""},
            "walls.left.width_ft": {"v": 39.0, "page": 6, "from": "39'-0\""},
            "walls.right.width_ft": {"v": 39.0, "page": 5, "from": "39'-0\""},
        },
    }


# ----------------------------------------------------------------- detection


def test_two_faces_one_quote_is_unattributed_and_taints_its_consumers():
    raw = _two_faces_one_quote()
    _one_source_one_path_guard(raw)
    ua = _unattributed_dim_paths(raw)
    assert "walls.left.width_ft" in ua
    assert "walls.right.width_ft" in ua
    # the rake computed from the SAME ambiguous quote is tainted too —
    # otherwise the plane sum rebuilds what the face refusal stopped
    assert "roof_planes.main.rake_lf" in ua
    # the front width has its own quote — never unattributed
    assert "walls.front.width_ft" not in ua


def test_own_quote_per_face_is_never_unattributed():
    raw = _own_quote_per_face()
    _one_source_one_path_guard(raw)
    assert _unattributed_dim_paths(raw) == {}


def test_one_feature_sharing_with_its_own_consumer_is_not_ambiguous():
    """A wall width and the rake derived from it share the quote — one
    attribution flowing downstream, not two owners."""
    raw = {
        "walls": [{"label": "left", "width_ft": 30.0}],
        "roof_planes": [{"label": "main", "rake_lf": 64.0}],
        "_dim_evidence": {
            "walls.left.width_ft": {"v": 30.0, "page": 7, "from": "30'-0\""},
            "roof_planes.main.rake_lf": {"v": 64.0, "page": 7,
                                         "from": "30'-0\""},
        },
    }
    _one_source_one_path_guard(raw)
    assert _unattributed_dim_paths(raw) == {}


# ---------------------------------------------------------------------- gate


def test_gate_marks_the_face_keeps_the_value_and_kills_quantity_inputs():
    raw = _two_faces_one_quote()
    _one_source_one_path_guard(raw)
    _attribution_gate(raw)
    walls = {w["label"]: w for w in raw["walls"]}
    # DISPLAY: the figure stays on the record, flagged
    assert walls["left"]["width_ft"] == 56.0
    assert "UNATTRIBUTED" in walls["left"]["_width_unattributed"]
    assert "56'-0" in walls["left"]["_width_unattributed"]
    assert not walls["front"].get("_width_unattributed")
    # QUANTITY-ONLY INPUTS: nulled where they sit
    assert raw["roof_planes"][0]["rake_lf"] is None
    assert raw["outside_corner_heights_ft"] == [None, None, None, None]
    assert raw["_dim_unattributed"]
    seams = raw.get("_seam_ledger") or {}
    assert "dims_unattributed_quantity_refused" in seams


def test_gate_is_idempotent():
    raw = _two_faces_one_quote()
    _one_source_one_path_guard(raw)
    _attribution_gate(raw)
    first = copy.deepcopy(raw["_dim_unattributed"])
    _attribution_gate(raw)
    assert raw["_dim_unattributed"] == first


# ---------------------------------------------------------------- the walk


def test_walk_refuses_body_and_gable_on_an_unattributed_face():
    walls = [
        {"label": "left", "width_ft": 56.0, "height_ft": 10.0,
         "gable_triangle_height_ft": 16.33},
        {"label": "front", "width_ft": 58.0, "height_ft": 10.0,
         "gable_triangle_height_ft": 0},
    ]
    walk = staging.walk_walls(
        walls, unattributed_faces={"left": "width located but UNATTRIBUTED"})
    # the gable needs no height — it must still refuse
    assert walk["gable_sqft"] == 0.0
    # the front face is untouched
    assert walk["siding_sqft"] == 58.0 * 10.0
    nd = [r for r in walk["faces_not_derivable"]
          if r.get("surface") == "width_attribution"]
    assert len(nd) == 1 and nd[0]["label"] == "left"
    # the read width still rides the detail for display
    d = next(x for x in walk["detail"] if x["label"] == "left")
    assert d["refused"] is True and d["width_ft"] == 56.0


# ------------------------------------------------------------- aggregation


def test_aggregation_refuses_every_width_lane_on_the_dart_shape():
    raw = _two_faces_one_quote()
    _one_source_one_path_guard(raw)
    m = _aggregate_to_hover_shape(raw)
    assert m["siding_sqft"] == 0.0                    # the 1,280.53 ft² lane
    assert m["starter_lf"] is None                    # the 170 LF lane
    assert m.get("footprint_perimeter_ft") is None
    assert m["_perimeter_lf"] is None
    assert m["rakes_lf"] is None
    assert m["outside_corner_lf"] is None
    assert "UNATTRIBUTED" in m["_starter_basis"]
    assert "left" in m["_starter_basis"] and "right" in m["_starter_basis"]


def test_aggregation_leaves_an_own_quote_house_alone():
    raw = _own_quote_per_face()
    _one_source_one_path_guard(raw)
    m = _aggregate_to_hover_shape(raw)
    assert m["siding_sqft"] > 0
    assert m["starter_lf"] == 58.0 + 58.0 + 39.0 + 39.0
    assert m["footprint_perimeter_ft"] == 194.0
    assert not raw.get("_dim_unattributed")


def test_readback_shows_the_flagged_figure_display_lane():
    raw = _two_faces_one_quote()
    _one_source_one_path_guard(raw)
    _aggregate_to_hover_shape(raw)
    rb = build_blueprint_readback(raw)
    assert rb.get("dim_unattributed")
    assert rb.get("dim_shared_source")
    codes = {f.get("code") for f in (rb.get("rail") or [])}
    assert "dims_unattributed_quantity_refused" in codes


def test_lf_ledger_merges_and_a_refused_lane_never_resurrects():
    """The LF sweep now runs twice (again after the gate). Overwriting its
    ledger erased the earlier kills and let a refused starter come back
    from a printed fallback — it MERGES."""
    raw = {"walls": [{"label": "front", "width_ft": None},
                     {"label": "back", "width_ft": None}],
           "starter_lf": 308.0, "eaves_lf": 194.0}
    _null_computed_lf_lanes(raw)
    lanes = {n["lane"] for n in raw["_lf_lane_nulled"]}
    assert {"starter_lf", "eaves_lf"} <= lanes
    raw["eaves_lf"] = 16.0          # a stale printed figure arrives late
    _null_computed_lf_lanes(raw)
    lanes2 = {n["lane"] for n in raw["_lf_lane_nulled"]}
    assert "starter_lf" in lanes2 and "eaves_lf" in lanes2


# ---------------------------------------------------------- the scoreboard


def test_metric_is_quantity_emitted_not_faces_derived():
    for d, e in FOREIGN_DRAFTER_SCOREBOARD.items():
        assert set(e) == {"sealed", "unattributed_quantity_emitted",
                          "attributed_quantity_emitted"}, d
        assert e["sealed"] is True, d
    assert unattributed_lanes() == {}
    assert earned_claim() == CLAIM_FAILS_SAFE
    assert not read_claim_earned()


def test_any_unattributed_quantity_costs_the_fails_safe_claim():
    leaking = {
        "tanis": {"sealed": True, "unattributed_quantity_emitted": {},
                  "attributed_quantity_emitted": {}},
        "dart": {"sealed": True,
                 "unattributed_quantity_emitted": {"gable_sqft": 1280.53},
                 "attributed_quantity_emitted": {}},
    }
    assert earned_claim(leaking) == CLAIM_NEITHER
    # the pre-split leak is on the record and is exactly what the metric
    # was blind to when it counted faces
    assert PRE_SEND127_LEAK["dart"]["gable_sqft"] == 1280.53
    assert PRE_SEND127_LEAK["dart"]["starter_lf"] == 170.0


def test_read_claim_needs_more_than_one_drafter_emitting():
    one = {
        "tanis": {"sealed": True, "unattributed_quantity_emitted": {},
                  "attributed_quantity_emitted": {"siding_sqft": 900.0}},
        "dart": {"sealed": True, "unattributed_quantity_emitted": {},
                 "attributed_quantity_emitted": {}},
    }
    assert earned_claim(one) == CLAIM_FAILS_SAFE
    two = copy.deepcopy(one)
    two["dart"]["attributed_quantity_emitted"] = {"siding_sqft": 1200.0}
    assert earned_claim(two) == CLAIM_READS
