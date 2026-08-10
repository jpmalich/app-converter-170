"""TAKEOFF ELEVATIONS PHASE 1 (Howard ordered 2026-08-10; scope filed
2026-08-09, approach (A) synthetic render — never the architectural
sheet painted over).

The blueprint sheet contract mirrors the photo door's, so SheetSvg
renders it UNCHANGED. Honesty pins:
- quoted printed dims tag AI-READ ✓ with the verbatim quote;
- an unreadable height hatches NEEDS YOUR TAPE (never a guessed frame);
- opening positions are SCHEMATIC and say so;
- mark-merge-suspected openings carry the suspicion onto the sheet.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.blueprint_elevation import build_blueprint_sheet  # noqa: E402


def _run(raw):
    return {"run_id": "abcdef1234567890", "result": {"raw_ai": raw},
            "model_name": "claude-test", "completed_at": "2026-08-10"}


EST = {"estimate_number": "EST-TEST", "customer_name": "t", "address": "a"}


def _raw(**over):
    raw = {
        "walls": [
            {"label": "front", "width_ft": 58.0, "height_ft": 9.0,
             "gable_triangle_height_ft": 0,
             "siding_pct_this_wall": 100,
             "wall_body_profile_callout": "LAP"},
            {"label": "back", "width_ft": 58.0, "height_ft": None,
             "gable_triangle_height_ft": 0},
        ],
        "windows": [
            {"id": "A", "elevation": "front", "width_in": 36.0,
             "height_in": 60.0, "qty": 2, "product_code": "SH3050",
             "type_hint": "SH"},
        ],
        "doors": [
            {"id": "D1", "elevation": "front", "width_in": 36.0,
             "height_in": 80.0, "qty": 1, "type_hint": "entry"},
            {"id": "G1", "elevation": "front", "width_in": 192.0,
             "height_in": 84.0, "qty": 1, "type_hint": "garage"},
        ],
        "avg_wall_height_ft": 9.0,
        "roof_pitch": "7/12",
        "story_count": 1,
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 58.0, "page": 3,
                                     "from": "58'-0\""},
        },
    }
    raw.update(over)
    return raw


class TestBlueprintSheetContract:
    def test_quoted_width_tags_and_prints_the_quote(self):
        s = build_blueprint_sheet(EST, _run(_raw()), "front")
        assert s["wall"]["width_ft"] == 58.0
        assert s["wall"]["width_tag"] == "AI-READ ✓"
        assert "58'-0\"" in s["wall"]["width_source"]
        assert s["source_door"] == "blueprint"
        assert s["sheet_code"] == "EL-1"
        assert s["hatch_needs_tape"] is None

    def test_unquoted_height_tags_ai_warn(self):
        s = build_blueprint_sheet(EST, _run(_raw()), "front")
        assert s["wall"]["height_tag"] == "AI-READ ⚠"

    def test_unread_height_hatches_needs_your_tape(self):
        # The Boni back-garage-wing acceptance case: null height draws at
        # the average, HATCHED — never presented as a read.
        s = build_blueprint_sheet(EST, _run(_raw()), "back")
        assert s["wall"]["height_ft"] == 9.0  # avg fallback, disclosed
        assert s["wall"]["height_tag"] == "ESTIMATED"
        assert s["hatch_needs_tape"] and "NEEDS YOUR TAPE" in s["hatch_needs_tape"]

    def test_missing_wall_is_named_not_guessed(self):
        s = build_blueprint_sheet(EST, _run(_raw()), "left")
        assert s["wall"]["width_ft"] is None
        assert "no left wall" in s["hatch_needs_tape"]

    def test_openings_are_schematic_and_say_so(self):
        s = build_blueprint_sheet(EST, _run(_raw()), "front")
        assert s["opening_counts"] == {"windows": 2, "doors": 1,
                                       "patio_doors": 0, "vents": 0,
                                       "garage_doors": 1}
        for o in s["openings"]:
            assert "SCHEMATIC" in o["position_tag"]
        w = next(o for o in s["openings"] if o["type"] == "Window")
        assert w["sill_in"] == 20.0  # 6'8" header − 60" window
        d = next(o for o in s["openings"] if o["type"] == "Entry door")
        assert d["sill_in"] == 0.0
        # even spacing spans the wall, never stacked at zero
        centers = [o["center_ft"] for o in s["openings"]]
        assert len(set(centers)) == len(centers)
        assert all(0 < c < 58 for c in centers)

    def test_merge_suspect_rides_onto_the_sheet(self):
        raw = _raw(_mark_merge_suspected=[
            {"code": "SH3050", "marks": ["A"], "likely_unread": []}])
        s = build_blueprint_sheet(EST, _run(raw), "front")
        w = next(o for o in s["openings"] if o["opening_id"] == "A")
        assert "MERGE-SUSPECT" in w["position_tag"]
        assert w["confirmed"] is False
        assert "MARK-MERGE SUSPECTED" in s["schedule_note"]

    def test_stepped_wall_names_its_segments(self):
        raw = _raw()
        raw["walls"][0]["height_segments"] = [
            {"name": "main", "width_ft": 40, "height_ft": 9},
            {"name": "wing", "width_ft": 18, "height_ft": None},
        ]
        s = build_blueprint_sheet(EST, _run(raw), "front")
        assert "STEPPED WALL" in s["wall"]["step_note"]
        assert "UNREAD" in s["wall"]["step_note"]
        assert s["wall"]["area_sqft"] is None

    def test_roofline_binds_from_the_blueprint_raw(self):
        raw = _raw()
        raw["walls"][0]["gable_triangle_height_ft"] = 8.0
        s = build_blueprint_sheet(EST, _run(raw), "front")
        assert s["roofline"] is not None
        assert s["wall"]["gable_triangle_ft"] == 8.0
