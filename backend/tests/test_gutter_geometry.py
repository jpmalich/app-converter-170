"""Iter 78z (P1.4) — Gutter/downspout geometry accuracy.

PINS UPDATED (SEND-105, named per SEND-99 condition 1): this file
previously pinned the story-default height ladder — `_ai_avg_wall_height_ft`
as a quantity base, `_ai_story_count` × 9 ft fallback, and a hardcoded
9/12 ft floor. RULING V's conversion (carried PENDING_CONVERSION in the
census since send 19) made every one of those assertions wrong: the
downspout drop and gutter-mitre count now derive from VERIFIED wall
heights only (`_verified_wall_heights_ft` — taped human dimensions or
the face's own DP-1 DERIVED chain, max never averaged) and REFUSE (None,
named) where none exists. Model heights are hypothesis only. The old
formulas' geometry (÷25 downspouts, +3 kick/slack, clips/6, joints/4)
is unchanged — only the height BASE moved.
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
    _verified_drop_height_ft,
)


def _vh(ft, src="taped_human", face="front"):
    return {face: {"ft": ft, "src": src}}


def _gutter_line(lines: list, item: str) -> dict | None:
    for l in lines:
        if l["tab"] == "vinyl" and l["section"] == "Seamless Gutter" and l["name"] == item:
            return l
    return None


# ---------------------- Downspout drop (Ruling V) ------------------------

def test_downspout_drop_uses_verified_height_only():
    """Verified 18 ft (taped or DP-1 chain) → drop = 21 LF."""
    m = {"_verified_wall_heights_ft": _vh(18.0)}
    assert _downspout_drop_ft(m) == 21.0
    h, basis = _verified_drop_height_ft(m)
    assert h == 18.0 and "never averaged" in basis


def test_downspout_drop_refuses_model_height_and_story_count():
    """The retired ladder: a model height, a story count, or nothing at
    all now REFUSE — no story defaults, no `_ai_story_count or 1`, no
    hardcoded 9'."""
    assert _downspout_drop_ft({"_ai_avg_wall_height_ft": 18.0}) is None
    assert _downspout_drop_ft({"_ai_story_count": 2}) is None
    assert _downspout_drop_ft({}) is None
    _, why = _verified_drop_height_ft({})
    assert "Ruling V" in why and "hypothesis only" in why


def test_downspout_drop_max_of_verified_never_averaged():
    m = {"_verified_wall_heights_ft": {
        "front": {"ft": 9.0, "src": "dp1_derived_chain"},
        "back": {"ft": 18.0, "src": "taped_human"}}}
    assert _downspout_drop_ft(m) == 21.0   # max(9, 18) + 3


def test_downspout_lf_two_story_doubles_one_story():
    """Same Howard-bug pin, verified bases: 100 LF eaves, 4 downspouts:
    verified 9 ft → 4 × 12 = 48 LF; verified 18 ft → 4 × 21 = 84 LF."""
    m1 = {"eaves_lf": 100, "_verified_wall_heights_ft": _vh(9.0)}
    m2 = {"eaves_lf": 100, "_verified_wall_heights_ft": _vh(18.0)}
    assert _downspout_lf(m1) == 48
    assert _downspout_lf(m2) == 84


def test_downspout_lf_refuses_without_verified_height():
    """Downspouts exist (count stands) but the LF REFUSES — never a
    silent zero, never a 9 ft guess."""
    assert _downspout_lf({"eaves_lf": 100, "_ai_story_count": 1}) is None
    assert _downspout_count({"eaves_lf": 100}) == 4   # count is LF-free


def test_downspout_zero_when_no_eaves():
    assert _downspout_lf({"eaves_lf": 0}) == 0
    assert _downspout_count({"eaves_lf": 0}) == 0


# ---------------------- Mitres (Ruling V base) ---------------------------

def test_mitre_count_gable_roof_zero_outside():
    m = {
        "eaves_lf": 110,
        "outside_corner_lf": 36,
        "inside_corner_lf": 0,
        "_verified_wall_heights_ft": _vh(9.0),
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 800},
        ],
    }
    assert _mitre_count(m) == 0  # gable wall present → 0 outside mitres


def test_mitre_count_hip_roof_wraps():
    m = {
        "eaves_lf": 160,
        "outside_corner_lf": 36,
        "inside_corner_lf": 0,
        "_verified_wall_heights_ft": _vh(9.0),
        "_ai_gable_sqft": 0,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 0, "wall_body_sqft": 800},
        ],
    }
    assert _mitre_count(m) == 4


def test_mitre_count_l_shaped_house_with_inside_corner():
    m = {
        "eaves_lf": 140,
        "outside_corner_lf": 54,
        "inside_corner_lf": 9,
        "_verified_wall_heights_ft": _vh(9.0),
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 800},
        ],
    }
    assert _mitre_count(m) == 1


def test_mitre_count_refuses_without_verified_height():
    m = {"eaves_lf": 140, "outside_corner_lf": 54,
         "_ai_avg_wall_height_ft": 9}
    assert _mitre_count(m) is None
    assert _gutter_corner_count(m) is None


def test_gutter_corner_count_basic():
    m = {"outside_corner_lf": 36, "inside_corner_lf": 9,
         "_verified_wall_heights_ft": _vh(9.0)}
    out_n, in_n = _gutter_corner_count(m)
    assert out_n == 4
    assert in_n == 1


# ---------------------- Pipe clips --------------------------------------

def test_pipe_clips_two_story_more_than_one_story():
    m1 = {"eaves_lf": 100, "_verified_wall_heights_ft": _vh(9.0)}
    m2 = {"eaves_lf": 100, "_verified_wall_heights_ft": _vh(18.0)}
    assert _pipe_clips_count(m1) == 8
    assert _pipe_clips_count(m2) == 16


def test_pipe_clips_refuse_without_verified_height():
    assert _pipe_clips_count({"eaves_lf": 100}) is None


def test_pipe_clips_zero_when_no_downspouts():
    assert _pipe_clips_count({"eaves_lf": 0}) == 0


# ---------------------- Sealant -----------------------------------------

def test_sealant_count_gable_house():
    m = {
        "eaves_lf": 100,
        "outside_corner_lf": 36,
        "_verified_wall_heights_ft": _vh(9.0),
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 800},
        ],
    }
    # 0 mitres (gable) + 8 end caps + 4 outlets = 12 joints → 3 tubes
    assert _sealant_count(m) == 3


def test_sealant_refuses_when_mitre_base_refuses():
    m = {"eaves_lf": 100, "outside_corner_lf": 36}
    assert _sealant_count(m) is None


def test_sealant_zero_when_no_eaves():
    assert _sealant_count({"eaves_lf": 0}) == 0


# ---------------------- Integration via _build_lines --------------------

def test_build_lines_emits_new_gutter_accessories():
    m = {
        "siding_sqft": 2000,
        "siding_with_openings_sqft": 2000,
        "eaves_lf": 160,
        "rakes_lf": 0,
        "outside_corner_lf": 72,
        "inside_corner_lf": 0,
        "_verified_wall_heights_ft": _vh(18.0),
        "_ai_gable_sqft": 0,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 0, "wall_body_sqft": 500},
        ],
    }
    lines = _build_lines(m)
    assert _gutter_line(lines, 'Gutter 6"') is not None
    downspout = _gutter_line(lines, 'Downspout 6"')
    assert downspout is not None
    # 160/25 = 7 downspouts × 21 LF = 147 LF → 15 × 10' sticks
    assert downspout["qty"] == 15
    assert "verified: taped_human 18.0 ft" in downspout["note"]
    assert _gutter_line(lines, "elbow") is not None
    assert _gutter_line(lines, "End Cap") is not None
    assert _gutter_line(lines, "Hangars with Screws") is not None
    mitre = _gutter_line(lines, "Mitre")
    assert mitre is not None
    assert mitre["qty"] == 4
    clips = _gutter_line(lines, "Pipe Clips")
    assert clips is not None
    assert clips["qty"] == 28
    assert _gutter_line(lines, "Gutter Sealant") is not None


def test_build_lines_refused_reads_emit_named_rows_never_silent_zero():
    """SEND-105 Ruling V — with gutter present but NO verified height,
    the height-based rows land as NAMED refusals (qty None,
    not_derivable), never skipped and never zero. Height-free rows
    (gutter LF, end caps) still derive."""
    m = {
        "siding_sqft": 2000,
        "siding_with_openings_sqft": 2000,
        "eaves_lf": 160,
        "outside_corner_lf": 72,
        "_ai_avg_wall_height_ft": 18,   # model — hypothesis only
        "_ai_story_count": 2,           # retired ladder
        "_ai_gable_sqft": 0,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 0, "wall_body_sqft": 500},
        ],
    }
    lines = _build_lines(m)
    assert _gutter_line(lines, 'Gutter 6"') is not None   # height-free
    for item in ('Downspout 6"', "Mitre", "Pipe Clips", "Gutter Sealant"):
        row = _gutter_line(lines, item)
        assert row is not None, item
        assert row["qty"] is None and row["not_derivable"], item
        assert "REFUSED" in row["not_derivable_reason"], item
        assert "Ruling V" in row["not_derivable_reason"], item


def test_build_lines_skips_gutter_accessories_when_no_eaves():
    m = {"siding_sqft": 100, "siding_with_openings_sqft": 100, "eaves_lf": 0}
    lines = _build_lines(m)
    assert _gutter_line(lines, "Mitre") is None
    assert _gutter_line(lines, "Pipe Clips") is None
    assert _gutter_line(lines, "Gutter Sealant") is None


def test_build_lines_gable_house_emits_no_mitres_but_does_emit_clips():
    m = {
        "siding_sqft": 1500,
        "siding_with_openings_sqft": 1500,
        "eaves_lf": 80,
        "outside_corner_lf": 36,
        "_verified_wall_heights_ft": _vh(9.0),
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 600},
        ],
    }
    lines = _build_lines(m)
    assert _gutter_line(lines, "Mitre") is None  # zero qty → suppressed
    clips = _gutter_line(lines, "Pipe Clips")
    assert clips is not None
    assert clips["qty"] == 8
