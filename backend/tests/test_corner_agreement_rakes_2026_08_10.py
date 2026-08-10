"""SEND 8 RULINGS (Howard, 2026-08-10):
1. CORNER AGREEMENT-OR-FLAG — disagreement keeps the primary, fires a
   loud corner_walk_conflict PRINTING BOTH NUMBERS. Max-wins dies.
2. RAKES — the plane sum GOVERNS whenever planes carry rake figures
   (exact mirror of the eaves rule). Larger-wins dies.
3. EAVE/RAKE ORIENTATION CHECK — on a simple gable roof, eaves and
   rakes sit on opposite wall pairs, always (the EST-040221 instrument).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    check_read_consistency, build_blueprint_readback,
)


def _walls(flip=False):
    g = 8.0
    return [
        {"label": "front", "width_ft": 58, "gable_triangle_height_ft": g if flip else 0},
        {"label": "back", "width_ft": 58, "gable_triangle_height_ft": g if flip else 0},
        {"label": "left", "width_ft": 39, "gable_triangle_height_ft": 0 if flip else g},
        {"label": "right", "width_ft": 39, "gable_triangle_height_ft": 0 if flip else g},
    ]


class TestEaveRakeOrientation:
    def test_flipped_house_flags_with_both_pair_sums(self):
        # EST-040221 shape: eaves landing on the 39' pair instead of the
        # 58's — the eave figure matches the GABLE pair. Wrong house.
        raw = {"walls": _walls(), "eaves_lf": 78, "roof_planes": []}
        flags = check_read_consistency(raw)
        hit = [f for f in flags if f["code"] == "eave_rake_orientation"]
        assert len(hit) == 1
        v = hit[0]["vars"]
        assert v["eaves"] == "78" and v["gsum"] == "78" and v["esum"] == "116"
        assert hit[0]["level"] == "loud"

    def test_correct_orientation_stays_silent(self):
        raw = {"walls": _walls(), "eaves_lf": 116, "roof_planes": []}
        codes = {f["code"] for f in check_read_consistency(raw)}
        assert "eave_rake_orientation" not in codes

    def test_plane_sum_feeds_the_check(self):
        raw = {"walls": _walls(),
               "eaves_lf": 0,
               "roof_planes": [{"label": "main", "eave_lf": 78,
                                "rake_lf": 60, "gable_ends": 2}]}
        codes = {f["code"] for f in check_read_consistency(raw)}
        assert "eave_rake_orientation" in codes

    def test_square_house_never_flags(self):
        # pairs within 15% of each other — orientation is unreadable,
        # the check abstains rather than guessing.
        walls = [
            {"label": "front", "width_ft": 40, "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 40, "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 38, "gable_triangle_height_ft": 8},
            {"label": "right", "width_ft": 38, "gable_triangle_height_ft": 8},
        ]
        raw = {"walls": walls, "eaves_lf": 76, "roof_planes": []}
        codes = {f["code"] for f in check_read_consistency(raw)}
        assert "eave_rake_orientation" not in codes


class TestCornerConflictOnTheCard:
    def test_conflict_prints_both_numbers(self):
        raw = {"walls": [],
               "_corner_walk_conflict": {
                   "primary": {"out": 6, "in": 2, "lf": 92.0},
                   "roof_pass": {"out": 10, "in": 6, "lf": 130.0}}}
        flags = check_read_consistency(raw)
        hit = [f for f in flags if f["code"] == "corner_walk_conflict"]
        assert len(hit) == 1
        v = hit[0]["vars"]
        assert v["p_out"] == 6 and v["p_in"] == 2
        assert v["r_out"] == 10 and v["r_in"] == 6
        assert hit[0]["level"] == "loud"

    def test_conflict_reaches_the_readback_consistency_list(self):
        raw = {"walls": [{"label": "front", "width_ft": 40,
                          "height_ft": 9}],
               "roof_planes": [],
               "_corner_walk_conflict": {
                   "primary": {"out": 6, "in": 2, "lf": 92.0},
                   "roof_pass": {"out": 10, "in": 6, "lf": 130.0}}}
        rb = build_blueprint_readback(raw)
        codes = {f["code"] for f in rb["consistency"]}
        assert "corner_walk_conflict" in codes


class TestRakesPlaneSumGoverns:
    def _agg(self, raw):
        from routes.ai_blueprint import _aggregate_to_hover_shape
        return _aggregate_to_hover_shape(raw)

    def test_plane_sum_beats_a_larger_bare_top_level(self):
        # THE RULING'S POINT: the model's bare 120 must LOSE to the
        # evidenced plane sum 84 — larger-wins is dead.
        raw = {"walls": [], "windows": [], "doors": [],
               "rakes_lf": 120,
               "roof_planes": [
                   {"label": "main", "eave_lf": 116, "rake_lf": 84,
                    "gable_ends": 2}]}
        m = self._agg(raw)
        assert m["rakes_lf"] == 84
        assert raw["_rakes_plane_summed"] is True

    def test_rakes_govern_even_when_planes_carry_no_eaves(self):
        raw = {"walls": [], "windows": [], "doors": [],
               "rakes_lf": 120,
               "roof_planes": [
                   {"label": "main", "eave_lf": 0, "rake_lf": 84,
                    "gable_ends": 2}]}
        m = self._agg(raw)
        assert m["rakes_lf"] == 84

    def test_bare_top_level_rides_only_without_plane_rakes(self):
        raw = {"walls": [], "windows": [], "doors": [],
               "rakes_lf": 120, "roof_planes": []}
        m = self._agg(raw)
        assert m["rakes_lf"] == 120
        assert "_rakes_plane_summed" not in raw
