"""Iter 78z (P1.4) — Gutter/downspout geometry accuracy.

Verifies:
  - Downspout LF scales by story / avg_wall_height (no more 2x undercount)
  - Mitre auto-fill differentiates gable vs hip roof
  - Pipe Clips scale per downspout drop (more clips on 2-story)
  - Gutter Sealant tubes derive from joint count
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from routes.hover import (  # noqa: E402
    _build_lines,
    _downspout_drop_ft,
    _downspout_lf,
    _downspout_count,
    _mitre_count,
    _pipe_clips_count,
    _sealant_count,
    _gutter_corner_count,
)


def _gutter_line(lines: list, item: str) -> dict | None:
    for l in lines:
        if l["tab"] == "vinyl" and l["section"] == "Seamless Gutter" and l["name"] == item:
            return l
    return None


# ---------------------- Downspout drop ----------------------------------

def test_downspout_drop_uses_avg_wall_height():
    """With AI-measured wall height = 18 ft (2-story), drop = 21 LF."""
    m = {"_ai_avg_wall_height_ft": 18.0}
    assert _downspout_drop_ft(m) == 21.0


def test_downspout_drop_falls_back_to_story_count():
    """No avg_wall_height → use story_count × 9 ft baseline."""
    assert _downspout_drop_ft({"_ai_story_count": 2}) == 21.0  # 2*9 + 3
    assert _downspout_drop_ft({"_ai_story_count": 1}) == 12.0
    assert _downspout_drop_ft({"_ai_story_count": 3}) == 30.0


def test_downspout_drop_final_fallback():
    """No height data at all → 12 LF (single-story baseline)."""
    assert _downspout_drop_ft({}) == 12.0


def test_downspout_lf_two_story_doubles_one_story():
    """The Howard bug: 2-story home was undercounted by ~2x. With the new
    formula, a 100 LF eaves house with 4 downspouts gets:
      1-story: 4 × 12 = 48 LF
      2-story: 4 × 21 = 84 LF
    (Not exactly 2x but ~1.75x — the fixed +3 ft kick/slack tax is
    constant.)"""
    m1 = {"eaves_lf": 100, "_ai_story_count": 1}
    m2 = {"eaves_lf": 100, "_ai_story_count": 2}
    lf1 = _downspout_lf(m1)
    lf2 = _downspout_lf(m2)
    assert lf1 == 48
    assert lf2 == 84
    assert lf2 / lf1 > 1.5  # confirms the multiplier scaled


def test_downspout_zero_when_no_eaves():
    assert _downspout_lf({"eaves_lf": 0}) == 0
    assert _downspout_count({"eaves_lf": 0}) == 0


# ---------------------- Mitres ------------------------------------------

def test_mitre_count_gable_roof_zero_outside():
    """Gable roof — gutter doesn't wrap. Outside corners ignored."""
    m = {
        "eaves_lf": 110,
        "outside_corner_lf": 36,  # 4 corners × 9 ft
        "inside_corner_lf": 0,
        "_ai_avg_wall_height_ft": 9,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 800},
        ],
    }
    assert _mitre_count(m) == 0  # gable wall present → 0 outside mitres


def test_mitre_count_hip_roof_wraps():
    """Hip roof (no gables) — gutter wraps the full perimeter."""
    m = {
        "eaves_lf": 160,
        "outside_corner_lf": 36,
        "inside_corner_lf": 0,
        "_ai_avg_wall_height_ft": 9,
        "_ai_gable_sqft": 0,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 0, "wall_body_sqft": 800},
        ],
    }
    assert _mitre_count(m) == 4  # 4 outside corners on a basic rectangular hip


def test_mitre_count_l_shaped_house_with_inside_corner():
    """L-shaped footprint: gable roof + 1 inside corner → 1 mitre."""
    m = {
        "eaves_lf": 140,
        "outside_corner_lf": 54,  # 6 outside corners × 9 ft
        "inside_corner_lf": 9,    # 1 inside corner × 9 ft
        "_ai_avg_wall_height_ft": 9,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 800},
        ],
    }
    assert _mitre_count(m) == 1  # gable hides outsides; 1 inside


def test_gutter_corner_count_basic():
    m = {"outside_corner_lf": 36, "inside_corner_lf": 9, "_ai_avg_wall_height_ft": 9}
    out_n, in_n = _gutter_corner_count(m)
    assert out_n == 4
    assert in_n == 1


# ---------------------- Pipe clips --------------------------------------

def test_pipe_clips_two_story_more_than_one_story():
    """2-story drop (21 LF) needs more clips than 1-story (12 LF)."""
    m1 = {"eaves_lf": 100, "_ai_story_count": 1}  # 4 downspouts × 2 clips
    m2 = {"eaves_lf": 100, "_ai_story_count": 2}  # 4 downspouts × 4 clips
    assert _pipe_clips_count(m1) == 8
    assert _pipe_clips_count(m2) == 16


def test_pipe_clips_zero_when_no_downspouts():
    assert _pipe_clips_count({"eaves_lf": 0}) == 0


# ---------------------- Sealant -----------------------------------------

def test_sealant_count_gable_house():
    """Gable house: 4 end caps (2 runs × 2) + 4 outlets + 0 mitres = 8
    joints → ceil(8 / 4) = 2 tubes."""
    m = {
        "eaves_lf": 100,
        "outside_corner_lf": 36,
        "_ai_avg_wall_height_ft": 9,
        "_ai_story_count": 1,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 800},
        ],
    }
    # gutter_runs = max(2, ceil(100/30)) = 4 runs → 8 end caps
    # downspouts = max(2, ceil(100/25)) = 4 outlets
    # mitres = 0 (gable)
    # joints = 0 + 8 + 4 = 12 → ceil(12/4) = 3 tubes
    assert _sealant_count(m) == 3


def test_sealant_zero_when_no_eaves():
    assert _sealant_count({"eaves_lf": 0}) == 0


# ---------------------- Integration via _build_lines --------------------

def test_build_lines_emits_new_gutter_accessories():
    """Hip-roof 2-story home should now generate ALL of: Mitre, Pipe
    Clips, Gutter Sealant (in addition to existing Gutter / Downspout /
    elbow / End Cap / Hangars)."""
    m = {
        "siding_sqft": 2000,
        "siding_with_openings_sqft": 2000,
        "eaves_lf": 160,
        "rakes_lf": 0,
        "outside_corner_lf": 72,  # 4 corners × 18 ft (2-story)
        "inside_corner_lf": 0,
        "_ai_avg_wall_height_ft": 18,
        "_ai_story_count": 2,
        "_ai_gable_sqft": 0,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 0, "wall_body_sqft": 500},
        ],
    }
    lines = _build_lines(m)
    # All 7 gutter rows should be present
    assert _gutter_line(lines, 'Gutter 6"') is not None
    downspout = _gutter_line(lines, 'Downspout 6"')
    assert downspout is not None
    # 160/25 = 7 downspouts × 21 LF = 147 LF → 15 × 10' sticks
    # (SALES UNIT ruled 2026-07-31)
    assert downspout["qty"] == 15
    assert _gutter_line(lines, "elbow") is not None
    assert _gutter_line(lines, "End Cap") is not None
    assert _gutter_line(lines, "Hangars with Screws") is not None
    # NEW lines
    mitre = _gutter_line(lines, "Mitre")
    assert mitre is not None
    assert mitre["qty"] == 4  # hip roof, 4 outside corners
    clips = _gutter_line(lines, "Pipe Clips")
    assert clips is not None
    assert clips["qty"] == 28  # 7 downspouts × 4 clips (21 LF drop / 6)
    sealant = _gutter_line(lines, "Gutter Sealant")
    assert sealant is not None


def test_build_lines_skips_gutter_accessories_when_no_eaves():
    """0 eaves → no gutter section accessories emitted."""
    m = {"siding_sqft": 100, "siding_with_openings_sqft": 100, "eaves_lf": 0}
    lines = _build_lines(m)
    assert _gutter_line(lines, "Mitre") is None
    assert _gutter_line(lines, "Pipe Clips") is None
    assert _gutter_line(lines, "Gutter Sealant") is None


def test_build_lines_gable_house_emits_no_mitres_but_does_emit_clips():
    """Standard gable house: 0 mitres, 8 clips (4 downspouts × 2 clips)."""
    m = {
        "siding_sqft": 1500,
        "siding_with_openings_sqft": 1500,
        "eaves_lf": 80,
        "outside_corner_lf": 36,
        "_ai_avg_wall_height_ft": 9,
        "_ai_story_count": 1,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 600},
        ],
    }
    lines = _build_lines(m)
    assert _gutter_line(lines, "Mitre") is None  # zero qty → suppressed
    clips = _gutter_line(lines, "Pipe Clips")
    assert clips is not None
    # 4 downspouts × max(2, ceil(12/6)=2) = 8
    assert clips["qty"] == 8
