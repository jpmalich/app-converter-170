"""SEND-122 pins (Howard ruled 2026-08-24) — Tanis scored-read fallout.

ITEM 1 — THE COMPUTED LF LANE MAY NOT OUTLIVE ITS NULLED INPUTS: starter
308 = 2×97 + 2×57 and eaves 194 = 2×97 rode measurements AFTER the quote
guard nulled the widths they are computed from. starter/eaves/rakes/
corner LF null NAMED when their formula inputs die.
ITEM 2 — A ROW WITH NO COUNT EVIDENCE REFUSES, NEVER CARRIES 1
(supersedes the ungoverned one-row-one-opening convention of
SEND-114/116): the marks-as-1 floor was reached through the ungoverned
lane on Tanis — window_count 7 vs sealed 20.
ITEM 3 — THE REFUSAL BEFORE THE READ: a drawn below-grade level flags
below_grade_unread; the read has no walkout path and says so by name.
"""
import sys

sys.path.insert(0, "/app/backend")

from routes.ai_blueprint import (  # noqa: E402
    _null_computed_lf_lanes,
    _refuse_unevidenced_counts,
    _aggregate_to_hover_shape,
    check_read_consistency,
)


def _wall(label, width=None, height=None, gable=0.0):
    return {"label": label, "width_ft": width, "height_ft": height,
            "gable_triangle_height_ft": gable}


def _tanis_shape_raw():
    # The live bug's exact arithmetic: widths nulled, bare LF totals stand.
    return {
        "walls": [_wall("front"), _wall("back"),
                  _wall("left", gable=14.3), _wall("right", gable=14.3)],
        "starter_lf": 308.0, "eaves_lf": 194.0, "rakes_lf": 122.0,
        "outside_corner_lf": 80.0, "inside_corner_lf": 40.0,
        "outside_corner_heights_ft": [None] * 8,
        "avg_wall_height_ft": 10.0,
        "openings": [], "story_count": 1,
    }


class TestLfLaneGuard:
    def test_tanis_arithmetic_lanes_null_named(self):
        raw = _tanis_shape_raw()
        _null_computed_lf_lanes(raw)
        for k in ("starter_lf", "eaves_lf", "rakes_lf",
                  "outside_corner_lf", "inside_corner_lf"):
            assert raw[k] is None, k
        lanes = {n["lane"]: n for n in raw["_lf_lane_nulled"]}
        assert lanes["starter_lf"]["value"] == 308.0
        assert lanes["eaves_lf"]["value"] == 194.0
        assert lanes["rakes_lf"]["value"] == 122.0
        assert "lf_lanes_nulled_inputs_dead" in (raw.get("_seam_ledger") or {})

    def test_live_inputs_stand_untouched(self):
        raw = {
            "walls": [_wall("front", 30, 10), _wall("back", 30, 10, gable=6),
                      _wall("left", 40, 10, gable=6), _wall("right", 40, 10)],
            "starter_lf": 140.0, "eaves_lf": 70.0, "rakes_lf": 90.0,
            "outside_corner_lf": 40.0, "inside_corner_lf": 20.0,
            "outside_corner_heights_ft": [10.0] * 4,
        }
        _null_computed_lf_lanes(raw)
        assert raw["starter_lf"] == 140.0
        assert raw["eaves_lf"] == 70.0
        assert raw["rakes_lf"] == 90.0
        assert raw["outside_corner_lf"] == 40.0
        assert "_lf_lane_nulled" not in raw

    def test_flag_fires_and_measurements_carry_none(self):
        raw = _tanis_shape_raw()
        _null_computed_lf_lanes(raw)
        flags = {f["code"]: f for f in check_read_consistency(raw)}
        assert "lf_lane_refused" in flags
        assert "starter_lf 308" in flags["lf_lane_refused"]["vars"]["lanes"]
        m = _aggregate_to_hover_shape(raw)
        assert m["starter_lf"] is None
        assert m["eaves_lf"] is None
        assert m["rakes_lf"] is None
        # the 4×avg-height hypothesis fallback may not resurrect a
        # refused lane — a model height never feeds a quantity.
        assert m["outside_corner_lf"] is None
        assert m["inside_corner_lf"] is None
        assert "REFUSED" in m["_starter_basis"]


class TestCountFloorRefusal:
    def test_falsy_qty_refuses_named_never_1(self):
        raw = {"windows": [
                   {"id": "1", "qty": None}, {"id": "2", "qty": 0},
                   {"id": "7", "qty": 1}],
               "doors": [{"id": "E9", "qty": None}]}
        _refuse_unevidenced_counts(raw)
        w = {r["id"]: r for r in raw["windows"]}
        assert w["1"]["_count_unread"] and w["1"]["qty"] is None
        assert w["2"]["_count_unread"] and w["2"]["qty"] is None
        assert not w["7"].get("_count_unread") and w["7"]["qty"] == 1
        assert raw["doors"][0]["_count_unread"]
        marks = {(u["kind"], u["mark"]) for u in raw["_schedule_count_unread"]}
        assert ("windows", "1") in marks and ("windows", "2") in marks
        assert ("doors", "E9") in marks
        assert "counts_refused_no_evidence" in (raw.get("_seam_ledger") or {})

    def test_already_unread_rows_not_double_named(self):
        raw = {"windows": [{"id": "C", "qty": 0, "_count_unread": True}],
               "doors": []}
        _refuse_unevidenced_counts(raw)
        assert not raw.get("_schedule_count_unread")

    def test_aggregation_counts_only_evidence(self):
        # Tanis shape: 6 unevidenced marks refuse; only the located one counts.
        raw = {
            "walls": [_wall("front", 30, 10)],
            "windows": [{"id": "1", "qty": None, "elevation": "front",
                         "type_hint": "double_hung"},
                        {"id": "7", "qty": 1, "elevation": "front",
                         "type_hint": "double_hung"}],
            "doors": [], "openings": [],
            "avg_wall_height_ft": 10.0, "story_count": 1,
        }
        _refuse_unevidenced_counts(raw)
        m = _aggregate_to_hover_shape(raw)
        assert m["window_count"] == 1
        assert any(u["mark"] == "1"
                   for u in raw["_schedule_count_unread"])
        sched_marks = [r["mark"] for r in m["_ai_openings_schedule"]]
        assert "1" not in sched_marks and "7" in sched_marks


class TestBelowGradeRail:
    def test_basement_sheet_flags_below_grade_unread(self):
        raw = {"walls": [], "sheets_identified": [
            {"page": 1, "sheet_title": "BASEMENT FLOOR LEVEL PLAN",
             "useful_for": "floor_plan"}]}
        flags = {f["code"]: f for f in check_read_consistency(raw)}
        assert "below_grade_unread" in flags
        assert "BASEMENT FLOOR LEVEL PLAN" in flags["below_grade_unread"]["vars"]["pages"]

    def test_no_below_grade_sheet_stays_silent(self):
        raw = {"walls": [], "sheets_identified": [
            {"page": 1, "sheet_title": "FIRST FLOOR LEVEL PLAN",
             "useful_for": "floor_plan"},
            {"page": 2, "sheet_title": "FOUNDATION PLAN",
             "useful_for": "floor_plan"}]}
        codes = [f["code"] for f in check_read_consistency(raw)]
        assert "below_grade_unread" not in codes


class TestRailCopy:
    def test_new_flag_copy_exists_en_and_es(self):
        txt = open("/app/frontend/src/lib/dictionaries.js",
                   encoding="utf-8").read()
        for code in ("lf_lane_refused", "below_grade_unread"):
            assert txt.count(f'"bp.rb.consistency.{code}"') == 2, code
