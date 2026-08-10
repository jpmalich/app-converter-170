"""SEND 8-2 RULINGS (Howard, 2026-08-10):
1. WING FLAG GUARD — opposing walls that disagree FLAG LOUD with both
   widths, and the box-model rect takes the SHORTER of the pair (a max()
   could inflate the rect and silently SUPPRESS the wing detector —
   a missing body costs the job).
2. PORCH WALL-SIDE FROM GEOMETRY — the porch plane's eave names the
   wall-abutting run; undeterminable → FLAG + disclosed minimum, never
   the longer-side assumption (right on Boni 16'6"×6' by luck only).
3. FIELD NAMING — vent_unit_count / shutter_panel_count: a field name
   that can be read two ways is a defect; pairs = ceil(panels ÷ 2).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _aggregate_to_hover_shape, _opposing_pairs, build_blueprint_readback,
    check_read_consistency,
)
from routes.hover import _porch_geom  # noqa: E402


class TestWingFlagGuard:
    def test_disagreeing_pair_flags_loud_with_both_numbers(self):
        raw = {"walls": [
            {"label": "front", "width_ft": 58, "height_ft": 9},
            {"label": "back", "width_ft": 39, "height_ft": 9},
            {"label": "left", "width_ft": 39, "height_ft": 9},
            {"label": "right", "width_ft": 39, "height_ft": 9},
        ]}
        flags = check_read_consistency(raw)
        hit = [f for f in flags if f["code"] == "opposing_walls_disagree"]
        assert len(hit) == 1
        v = hit[0]["vars"]
        assert v["pair"] == "front/back"
        assert {v["a"], v["b"]} == {"58", "39"}
        assert hit[0]["level"] == "loud"

    def test_rect_takes_the_shorter_side_so_the_wing_can_fire(self):
        # The Boni shape: projecting garage makes the read's front longer
        # than the back. max() would build a 58-wide rect and swallow the
        # wing; the guard keeps the rect at the shorter 39.
        fb, lr, disags = _opposing_pairs(
            {"front": 58, "back": 39, "left": 39, "right": 39})
        assert fb == 39 and lr == 39
        assert disags == [("front/back", 58.0, 39.0)]

    def test_agreeing_pairs_stay_silent_and_unchanged(self):
        fb, lr, disags = _opposing_pairs(
            {"front": 58, "back": 58, "left": 39, "right": 39})
        assert fb == 58 and lr == 39 and disags == []

    def test_wing_flag_can_now_fire_where_max_suppressed_it(self):
        # footprint 58×39 = 2262; max-rect 58×39 would swallow it, the
        # min-rect 39×39 = 1521 lets the wing check see the excess.
        raw = {"walls": [
            {"label": "front", "width_ft": 58, "height_ft": 9},
            {"label": "back", "width_ft": 39, "height_ft": 9},
            {"label": "left", "width_ft": 39, "height_ft": 9},
            {"label": "right", "width_ft": 39, "height_ft": 9},
        ], "footprint_area_sqft": 2262, "roof_planes": []}
        rb = build_blueprint_readback(raw)
        assert rb["wing_check"]["flag"] is True


class TestPorchWallSideFromGeometry:
    def test_eave_names_the_wall_side(self):
        m = {"porch_ceiling_sqft": 99,
             "_porch_dims": [{"width_ft": 6.0, "length_ft": 16.5}],
             "_roof_planes": [{"is_porch": True, "eave_lf": 16.5}]}
        g = _porch_geom(m)
        assert g["wall_lf"] == 16.5
        assert g["basis"] == "real_dims"

    def test_eave_can_name_the_shorter_side_as_the_wall(self):
        # deeper-than-wide porch: the OLD longer-side assumption breaks;
        # geometry (eave = 6') puts the wall on the short run.
        m = {"porch_ceiling_sqft": 99,
             "_porch_dims": [{"width_ft": 6.0, "length_ft": 16.5}],
             "_roof_planes": [{"is_porch": True, "eave_lf": 6.0}]}
        g = _porch_geom(m)
        assert g["wall_lf"] == 6.0
        assert g["basis"] == "real_dims"

    def test_undeterminable_flags_and_takes_the_disclosed_minimum(self):
        m = {"porch_ceiling_sqft": 99,
             "_porch_dims": [{"width_ft": 6.0, "length_ft": 16.5}],
             "_roof_planes": []}
        g = _porch_geom(m)
        assert g["basis"] == "real_dims_wall_undetermined"
        assert g["wall_lf"] == 6.0
        assert "UNDETERMINED" in g["text"]
        # perimeter (the ceiling-receiving channel) is orientation-proof
        assert g["perimeter_lf"] == 45.0

    def test_square_porch_needs_no_geometry(self):
        m = {"porch_ceiling_sqft": 64,
             "_porch_dims": [{"width_ft": 8.0, "length_ft": 8.0}],
             "_roof_planes": []}
        g = _porch_geom(m)
        assert g["basis"] == "real_dims" and g["wall_lf"] == 8.0


class TestFieldNaming:
    def test_renamed_fields_reach_their_measurements(self):
        raw = {"walls": [], "windows": [], "doors": [],
               "roof_planes": [],
               "vent_unit_count": 3, "shutter_panel_count": 10}
        m = _aggregate_to_hover_shape(raw)
        assert m["vent_count"] == 3
        assert m["shutter_count"] == 10

    def test_downstream_arithmetic_matches_the_chosen_units(self):
        # vents = unit count as qty; shutters = ceil(panels / 2) PAIRS.
        from routes.hover import HOVER_MAPPING_SPEC
        vents = next(d for d in HOVER_MAPPING_SPEC
                     if "Gable vents" in str(d.get("item", "")))
        shutters = next(d for d in HOVER_MAPPING_SPEC
                        if "Shutters" in str(d.get("item", "")))
        assert vents["unit"] == "Each"
        assert vents["extract"]({"vent_count": 3}) == 3
        assert shutters["unit"] == "PR"
        assert shutters["extract"]({"shutter_count": 10}) == 5
        assert shutters["extract"]({"shutter_count": 9}) == 5
