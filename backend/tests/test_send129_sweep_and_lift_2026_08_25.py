"""SEND-129 pins (Howard ruled 2026-08-25).

Two halves:

A. THE OVERWRITE SWEEP — "a refusal that does not survive to the end of
   the pipeline is not a refusal." Every class from the SEND-128
   inventory that was a live site is pinned here.

B. THE LIFT — corroboration as the only way an unattributed WIDTH feeds a
   quantity: structural conditions PLUS Δ inside the ALREADY-REGISTERED
   3.8% elevation noise floor (derived, not chosen). The PRINTED figure
   feeds. Width instrument only — a height can never be corroborated,
   because the height is the read's own ruler.
"""
import attribution_lift as lift
import seam_accounting
from ocr_geometry import RULINGS_REGISTER
from routes.ai_blueprint import (_aggregate_to_hover_shape,
                                 _attribution_gate,
                                 _null_computed_lf_lanes,
                                 _one_source_one_path_guard,
                                 _unattributed_dim_paths,
                                 build_blueprint_readback)
from routes.hover import (REFUSAL_SENSITIVE_LANES, _key_refused,
                          refused_measurement_lanes)


def _shared_raw():
    return {
        "walls": [
            {"label": "front", "width_ft": 54.0, "height_ft": None,
             "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 54.0, "height_ft": None,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 30.0, "height_ft": None,
             "gable_triangle_height_ft": 8.75},
            {"label": "right", "width_ft": 30.0, "height_ft": None,
             "gable_triangle_height_ft": 8.75},
        ],
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 54.0, "page": 7, "from": "54'-0\""},
            "walls.back.width_ft": {"v": 54.0, "page": 7, "from": "54'-0\""},
            "walls.left.width_ft": {"v": 30.0, "page": 7, "from": "30'-0\""},
            "walls.right.width_ft": {"v": 30.0, "page": 7, "from": "30'-0\""},
        },
    }


def _resolved(wall_only, **kw):
    read = {"status": "RESOLVED", "wall_only_ft": wall_only,
            "fence_margin_warning": None, "scale_contested": False,
            "scale_quote_unattributed": False, "scale_quote": "9'-1 1/8\""}
    read.update(kw)
    return read


# ============================== A — THE SWEEP ==============================


def test_seam_ledger_is_idempotent_a_rerun_cannot_inflate_the_disclosure():
    raw = {}
    seam_accounting.account(raw, "dims_nulled_no_evidence", ["walls.left.width_ft"])
    seam_accounting.account(raw, "dims_nulled_no_evidence", ["walls.left.width_ft"])
    entry = raw["_seam_ledger"]["dims_nulled_no_evidence"]
    assert entry["removed"] == 1
    seam_accounting.account(raw, "dims_nulled_no_evidence", ["walls.back.width_ft"])
    assert raw["_seam_ledger"]["dims_nulled_no_evidence"]["removed"] == 2


def test_dim_evidence_merges_and_shared_source_cannot_duplicate():
    raw = _shared_raw()
    _one_source_one_path_guard(raw)
    n_shared = len(raw["_dim_shared_source"])
    raw["_dim_evidence"]["walls.front.height_ft"] = {
        "v": 9.9, "page": 1, "from": "9'-11 1/8\""}
    _one_source_one_path_guard(raw)
    assert len(raw["_dim_shared_source"]) >= n_shared
    quotes = [(r["quote"], r["page"], tuple(r["consumers"]))
              for r in raw["_dim_shared_source"]]
    assert len(quotes) == len(set(quotes)), "a re-run duplicated a record"
    # the merge keeps provenance an earlier pass recorded
    assert "walls.front.width_ft" in raw["_dim_evidence"]


def test_a_refused_starter_never_re_sources_itself_from_the_eaves():
    raw = _shared_raw()
    raw["starter_lf"] = 228.0
    raw["eaves_lf"] = 108.0
    for w in raw["walls"]:
        w["width_ft"] = None
    _null_computed_lf_lanes(raw)
    m = _aggregate_to_hover_shape(raw)
    assert m["starter_lf"] is None
    assert "16" not in str(m.get("_starter_basis") or "")
    assert "printed read 108" not in str(m.get("_starter_basis") or "")


def test_stale_plane_summed_flags_are_cleared_on_a_later_pass():
    raw = {"walls": [{"label": "left", "width_ft": None,
                      "gable_triangle_height_ft": 8.0}],
           "roof_planes": [{"label": "main", "eave_lf": None,
                            "rake_lf": None}],
           "rakes_lf": None, "eaves_lf": None,
           "_eaves_plane_summed": True, "_rakes_plane_summed": True}
    m = _aggregate_to_hover_shape(raw)
    assert not raw.get("_eaves_plane_summed")
    assert not raw.get("_rakes_plane_summed")
    assert m["rakes_lf"] is None


def test_carry_refusals_names_an_overwritten_refusal():
    prev = {"starter_lf": None, "siding_sqft": 0.0}
    new = {"starter_lf": 170.0, "siding_sqft": 1280.53}
    seam_accounting.carry_refusals(prev, new, "photo door")
    over = new["_refused_overwritten"]
    assert [o["key"] for o in over] == ["starter_lf"]
    assert over[0]["overwritten_by"] == "photo door"
    # idempotent — a second carry does not double the record
    seam_accounting.carry_refusals(prev, new, "photo door")
    assert len(new["_refused_overwritten"]) == 1


def test_priced_lanes_carry_the_refusal_instead_of_a_silent_zero():
    m = {"starter_lf": None, "outside_corner_lf": None,
         "footprint_perimeter_ft": None}
    keys = {r["key"] for r in refused_measurement_lanes(m)}
    assert {"starter_lf", "outside_corner_lf",
            "footprint_perimeter_ft"} <= keys
    assert _key_refused(m, "starter_lf")
    assert not _key_refused({"starter_lf": 194.0}, "starter_lf")
    assert not _key_refused({}, "starter_lf"), "absent is not refused"
    for key in ("starter_lf", "footprint_perimeter_ft",
                "outside_corner_lf", "inside_corner_lf"):
        assert key in REFUSAL_SENSITIVE_LANES


def test_readback_shows_a_refused_plane_figure_as_refused_not_zero():
    raw = {"walls": [{"label": "left", "width_ft": 30.0}],
           "roof_planes": [{"label": "main", "eave_lf": None,
                            "rake_lf": None}],
           "outside_corner_lf": None, "inside_corner_lf": None}
    rb = build_blueprint_readback(raw)
    row = (rb.get("planes") or [])[0]
    assert row["eave_refused"] is True and row["rake_refused"] is True
    assert rb["corners"]["basis"] == "refused"
    assert "outside_corner_lf" in rb["corners"]["refused_keys"]


# ============================== B — THE LIFT ==============================


def test_the_floor_is_the_registered_one_not_a_chosen_number():
    assert lift.NOISE_FLOOR_PCT == 3.8
    floor_text = [f for f in RULINGS_REGISTER["findings"]
                  if "ELEVATION NOISE FLOOR" in f]
    assert floor_text and "3.8%" in floor_text[0]


def test_inside_the_floor_lifts_and_the_printed_figure_feeds():
    v = lift.evaluate(30.0, _resolved(29.41))
    assert v["lifted"] is True
    assert v["delta_ft"] == 0.59 and v["delta_pct"] == 1.97
    assert v["figure_that_feeds"] == 30.0          # decision 2
    assert "PRINTED figure feeds" in v["statement"]


def test_outside_the_floor_refuses_but_still_prints_the_delta():
    v = lift.evaluate(50.0, _resolved(56.0))
    assert v["lifted"] is False
    assert v["delta_ft"] == 6.0 and v["delta_pct"] == 12.0
    assert "OUTSIDE the registered" in v["statement"]


def test_structural_conditions_each_refuse_on_their_own():
    assert not lift.evaluate(30.0, {"status": "NOT_ATTEMPTED",
                                    "reason": "no elevation located"})["lifted"]
    silhouette_only = _resolved(None, silhouette_ft=31.96)
    assert not lift.evaluate(30.0, silhouette_only)["lifted"]
    fenced = _resolved(29.41, fence_margin_warning="left reaches inside")
    assert not lift.evaluate(30.0, fenced)["lifted"]
    contested = _resolved(53.9, scale_contested=True)
    assert not lift.evaluate(54.0, contested)["lifted"]
    inherited = _resolved(53.9, scale_quote_unattributed=True)
    v = lift.evaluate(54.0, inherited)
    assert not v["lifted"] and "inherits the ambiguity" in v["statement"]


def test_the_gate_lifts_the_sides_and_keeps_the_shared_pair_refused():
    raw = _shared_raw()
    _one_source_one_path_guard(raw)
    raw["_linework_corroboration"] = {
        "left": _resolved(29.41), "right": _resolved(29.67),
        # the back's only ruler is contested — circular, refused
        "back": _resolved(53.9, scale_contested=True),
        # the front resolved geometry but no wall-only figure
        "front": _resolved(None, silhouette_ft=54.73),
    }
    _attribution_gate(raw)
    walls = {w["label"]: w for w in raw["walls"]}
    assert not walls["left"].get("_width_unattributed")
    assert not walls["right"].get("_width_unattributed")
    assert walls["front"].get("_width_unattributed")
    assert walls["back"].get("_width_unattributed")
    lifted = {c["path"] for c in raw["_attribution_corroboration"]
              if c.get("delta_ft") is not None and c.get("lifted") is not False}
    assert lifted == {"walls.left.width_ft", "walls.right.width_ft"}
    m = _aggregate_to_hover_shape(raw)
    # the sides' gables return; the perimeter still needs all four widths
    assert m["siding_sqft"] > 0
    assert m["starter_lf"] is None
    assert m.get("footprint_perimeter_ft") is None


def test_corroboration_is_a_width_instrument_only():
    raw = {
        "walls": [
            {"label": "front", "width_ft": 54.0, "height_ft": 9.9},
            {"label": "back", "width_ft": 54.0, "height_ft": 9.9},
        ],
        "_dim_evidence": {
            "walls.front.height_ft": {"v": 9.9, "page": 1,
                                      "from": "9'-11 1/8\""},
            "walls.back.height_ft": {"v": 9.9, "page": 1,
                                     "from": "9'-11 1/8\""},
        },
    }
    _one_source_one_path_guard(raw)
    # a "corroborating" read offered for the heights changes nothing
    raw["_linework_corroboration"] = {"front": _resolved(9.9),
                                      "back": _resolved(9.9)}
    _attribution_gate(raw)
    walls = {w["label"]: w for w in raw["walls"]}
    assert walls["front"]["_height_unattributed"]
    assert walls["back"]["_height_unattributed"]
    assert "circular" in lift.WIDTH_INSTRUMENT_ONLY
