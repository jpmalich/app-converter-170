"""SEGMENT-LEVEL PARTIAL DERIVABILITY — SEND-13 (2026-08-14).

Howard ruled this earlier and it was never built (the third ruled item to
go missing between sends): a wall with ONE segment killed REPORTS THE
KNOWN SEGMENT'S AREA, NAMES THE OTHER AS NOT DERIVABLE, and the wall total
says it is a SUBSET. `wall_body_gross_sqft` stops being all-or-nothing and
STOPS FALLING BACK TO THE TOP-LEVEL RECTANGLE — that fallback is the
silent inflation ruled against (it would credit a dead segment's area at
the full wall width).

Purity: numbers here are fixture inputs unlike Boni's, used to pin the
RELATIONSHIP (partial sum, named killed piece, subset flag), never as
assertion targets copied from the house.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from measure_staging import wall_body_gross_sqft, walk_walls  # noqa: E402
from profile_callouts import breakdown_walls_by_profile  # noqa: E402


def _wall_one_dead_segment():
    # main body derives (20×10=200); garage wing width killed.
    return {
        "label": "front", "width_ft": None, "height_ft": None,
        "wall_body_profile_callout": "lap",
        "height_segments": [
            {"label": "main body 2-story", "width_ft": 20.0, "height_ft": 10.0},
            {"label": "garage wing 1-story", "width_ft": None, "height_ft": 10.0},
        ],
    }


def test_partial_gross_sums_only_the_derivable_segment():
    gross, used, deriv = wall_body_gross_sqft(_wall_one_dead_segment())
    assert gross == 200.0                 # 20×10, garage absent
    assert len(used) == 1
    assert deriv["has_segments"] is True
    assert deriv["derivable"] is True
    assert deriv["subset"] is True
    assert [nd["label"] for nd in deriv["not_derivable"]] == \
        ["garage wing 1-story"]


def test_no_fallback_to_top_level_rectangle():
    """The killed segment is ABSENT, never covered by width×height. Even
    if a top-level width/height were present, a dead segment does not get
    credited at the full wall rectangle."""
    w = _wall_one_dead_segment()
    w["width_ft"] = 44.0          # a top-level width exists…
    w["height_ft"] = 10.0
    gross, used, deriv = wall_body_gross_sqft(w)
    assert gross == 200.0         # …but the dead garage seg is NOT 44×10
    assert deriv["subset"] is True


def test_breakdown_reports_known_segment_and_names_the_other():
    bd = breakdown_walls_by_profile([_wall_one_dead_segment()])
    face = bd["per_elevation"][0]
    assert face["wall_body_sqft"] == 200.0        # known segment reported
    assert face["wall_body_derivable"] is True
    assert face["wall_body_subset"] is True       # total says it's a subset
    named = [f for f in bd["faces_not_derivable"]
             if f.get("segment") == "garage wing 1-story"]
    assert named and named[0].get("partial") is True
    assert "not read" in named[0]["reason"]


def test_money_walk_sums_subset_and_names_missing():
    res = walk_walls([_wall_one_dead_segment()])
    assert round(res["siding_sqft"], 1) == 200.0
    fnd = [f for f in res["faces_not_derivable"]
           if f.get("segment") == "garage wing 1-story"]
    assert fnd and fnd[0].get("partial") is True


def test_all_segments_dead_refusal_companion_names_each():
    # SEND-107 PAIRING: this is the walk's REFUSAL COMPANION — all
    # segments dead → not derivable, each named. Renamed (assertions
    # untouched) so the money-walk pairing pin can discover it.
    w = {
        "label": "back", "width_ft": None, "height_ft": None,
        "wall_body_profile_callout": "lap",
        "height_segments": [
            {"label": "main body", "width_ft": None, "height_ft": None},
            {"label": "wing", "width_ft": None, "height_ft": None},
        ],
    }
    gross, used, deriv = wall_body_gross_sqft(w)
    assert gross == 0.0 and used == []
    assert deriv["derivable"] is False
    bd = breakdown_walls_by_profile([w])
    assert bd["per_elevation"][0]["wall_body_sqft"] is None
    segs_named = {f.get("segment") for f in bd["faces_not_derivable"]}
    assert {"main body", "wing"} <= segs_named


def test_unsegmented_wall_uses_its_rectangle_unchanged():
    w = {"label": "left", "width_ft": 30.0, "height_ft": 10.0,
         "wall_body_profile_callout": "lap"}
    gross, used, deriv = wall_body_gross_sqft(w)
    assert gross == 300.0
    assert deriv["has_segments"] is False
    assert deriv["derivable"] is True
    assert deriv["subset"] is False


def test_unsegmented_killed_width_still_names_the_whole_wall():
    w = {"label": "left", "width_ft": None, "height_ft": 10.0,
         "wall_body_profile_callout": "lap"}
    gross, used, deriv = wall_body_gross_sqft(w)
    assert gross == 0.0
    assert deriv["derivable"] is False
    assert deriv["not_derivable"][0]["label"] == "left"
