"""Iter 78z (P1.4) — End-to-end HTTP tests for new gutter/downspout geometry
auto-fills surfaced via POST /api/measure/map.

Verifies (against the live FastAPI route — no LLM cost):
  * Downspout 6" LF now scales by avg_wall_height / story_count
  * Mitre Each emits for hip roof, suppressed for gable roof
  * Pipe Clips Each scales with downspout drop
  * Gutter Sealant Each derives from joint count
  * All three suppressed when eaves_lf=0
  * No regression: per-profile siding split + new gutter lines coexist
"""
from __future__ import annotations
from creds_for_tests import TEST_PASSWORD

import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = TEST_PASSWORD


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=20,
    )
    if r.status_code != 200:
        pytest.skip(f"Auth failed: {r.status_code} {r.text[:200]}")
    return s


def _post_map(session, measurements):
    r = session.post(
        f"{BASE_URL}/api/measure/map",
        json={"measurements": measurements},
        timeout=30,
    )
    assert r.status_code == 200, f"map failed: {r.status_code} {r.text[:300]}"
    return r.json()


def _gutter(lines, name):
    """Find a Seamless Gutter line by item name on the vinyl tab."""
    for l in lines:
        if l.get("tab") == "vinyl" and l.get("section") == "Seamless Gutter" and l.get("name") == name:
            return l
    return None


# ---------------------------------------------------------------------------
# 1. 2-story hip roof, 100 LF eaves, avg_wall_height=18 → Downspout LF should
#    reflect the new story-aware drop (NOT the old flat 10 LF/downspout).
# ---------------------------------------------------------------------------
def test_two_story_hip_roof_downspout_lf(auth_session):
    data = _post_map(auth_session, {
        "eaves_lf": 100,
        "rake_lf": 0,            # hip roof has no rakes
        "outside_corner_lf": 72, # 4 corners × 18 ft wall = 72 LF
        "inside_corner_lf": 0,
        "_ai_avg_wall_height_ft": 18.0,
        "_ai_story_count": 2,
    })
    lines = data["lines"]
    ds = _gutter(lines, 'Downspout 6"')
    assert ds is not None, "Downspout 6\" line missing"
    # 4 downspouts × (18+3=21) drop = 84 LF (per implementation: max(2, ceil(100/25))=4)
    assert ds["qty"] == 84, f"expected 84 LF, got {ds['qty']}"
    assert ds["unit"] == "LF"
    print("DOWNSPOUT 2-STORY:", ds["qty"], ds.get("note", ""))


def test_two_story_hip_roof_emits_mitre_pipe_clips_sealant(auth_session):
    data = _post_map(auth_session, {
        "eaves_lf": 100,
        "outside_corner_lf": 72,
        "inside_corner_lf": 0,
        "_ai_avg_wall_height_ft": 18.0,
        "_ai_story_count": 2,
    })
    lines = data["lines"]

    mitre = _gutter(lines, "Mitre")
    assert mitre is not None, "Mitre line missing on hip roof"
    assert mitre["qty"] == 4, f"hip roof rectangular: 4 outside corners → 4 mitres, got {mitre['qty']}"
    assert mitre["unit"] == "Each"

    clips = _gutter(lines, "Pipe Clips")
    assert clips is not None, "Pipe Clips line missing"
    # 4 downspouts × max(2, ceil(21/6)=4) clips = 16
    assert clips["qty"] == 16, f"expected 16 clips, got {clips['qty']}"
    assert clips["unit"] == "Each"

    sealant = _gutter(lines, "Gutter Sealant")
    assert sealant is not None, "Gutter Sealant line missing"
    # mitres=4, runs=ceil(100/30)=4 → end_caps=8, outlets=4 → 16 joints / 4 = 4 tubes
    assert sealant["qty"] == 4, f"expected 4 tubes, got {sealant['qty']}"
    assert sealant["unit"] == "Each"
    print("HIP ROOF GUTTER ACCESSORIES:", mitre["qty"], clips["qty"], sealant["qty"])


# ---------------------------------------------------------------------------
# 2. Gable roof — mitres should be 0 (gutter doesn't wrap), but Pipe Clips
#    and Gutter Sealant should still emit.
# ---------------------------------------------------------------------------
def test_gable_roof_zero_mitres_but_clips_and_sealant_emit(auth_session):
    data = _post_map(auth_session, {
        "eaves_lf": 100,
        "rake_lf": 60,
        "outside_corner_lf": 72,
        "inside_corner_lf": 0,
        "_ai_avg_wall_height_ft": 18.0,
        "_per_elevation_breakdown": [
            {"label": "front", "gable_sqft": 50, "wall_body_sqft": 800},
        ],
    })
    lines = data["lines"]

    mitre = _gutter(lines, "Mitre")
    assert mitre is None or mitre["qty"] == 0, \
        f"gable roof should have 0 mitres, got {mitre and mitre['qty']}"

    clips = _gutter(lines, "Pipe Clips")
    assert clips is not None and clips["qty"] > 0, "Pipe Clips must still emit on gable roof"

    sealant = _gutter(lines, "Gutter Sealant")
    assert sealant is not None and sealant["qty"] > 0, "Gutter Sealant must still emit on gable roof"
    print("GABLE ROOF:", "mitre=", (mitre and mitre['qty']) or 0,
          "clips=", clips["qty"], "sealant=", sealant["qty"])


def test_gable_roof_via_ai_aggregate(auth_session):
    """Falls back to `_ai_gable_sqft` when no per-elevation breakdown supplied."""
    data = _post_map(auth_session, {
        "eaves_lf": 100,
        "outside_corner_lf": 72,
        "_ai_avg_wall_height_ft": 18.0,
        "_ai_gable_sqft": 120,
    })
    lines = data["lines"]
    mitre = _gutter(lines, "Mitre")
    assert mitre is None or mitre["qty"] == 0, "gable aggregate should suppress mitres"


# ---------------------------------------------------------------------------
# 3. eaves_lf=0 → all 3 new gutter accessories must be suppressed
# ---------------------------------------------------------------------------
def test_zero_eaves_suppresses_all_gutter_accessories(auth_session):
    data = _post_map(auth_session, {
        "eaves_lf": 0,
        "outside_corner_lf": 50,
        "_ai_avg_wall_height_ft": 18.0,
    })
    lines = data["lines"]
    assert _gutter(lines, "Mitre") is None, "Mitre must be suppressed when eaves=0"
    assert _gutter(lines, "Pipe Clips") is None, "Pipe Clips must be suppressed"
    assert _gutter(lines, "Gutter Sealant") is None, "Gutter Sealant must be suppressed"
    # Other downspout-derived lines too:
    assert _gutter(lines, 'Downspout 6"') is None or _gutter(lines, 'Downspout 6"')["qty"] == 0


# ---------------------------------------------------------------------------
# 4. Story-count fallback path (no avg_wall_height_ft provided)
# ---------------------------------------------------------------------------
def test_one_story_fallback_downspout_drop(auth_session):
    """1-story (no avg_wall_height): drop = 9+3 = 12 LF/down."""
    data = _post_map(auth_session, {"eaves_lf": 100, "_ai_story_count": 1})
    ds = _gutter(data["lines"], 'Downspout 6"')
    assert ds is not None
    # 4 downspouts × 12 = 48
    assert ds["qty"] == 48, f"expected 48 LF, got {ds['qty']}"


def test_two_story_fallback_downspout_drop(auth_session):
    """2-story (no avg_wall_height): drop = 18+3 = 21 LF/down."""
    data = _post_map(auth_session, {"eaves_lf": 100, "_ai_story_count": 2})
    ds = _gutter(data["lines"], 'Downspout 6"')
    assert ds is not None
    assert ds["qty"] == 84, f"expected 84 LF, got {ds['qty']}"


def test_no_height_data_falls_back_to_12(auth_session):
    """Neither avg_wall_height nor story_count → 12 LF baseline."""
    data = _post_map(auth_session, {"eaves_lf": 100})
    ds = _gutter(data["lines"], 'Downspout 6"')
    assert ds is not None
    assert ds["qty"] == 48, f"expected 48 LF (4×12), got {ds['qty']}"


# ---------------------------------------------------------------------------
# 5. No regression: multi-profile siding still splits AND gutter accessories
#    still emit on the same response (orthogonal features).
# ---------------------------------------------------------------------------
def test_multi_profile_siding_and_gutter_accessories_coexist(auth_session):
    data = _post_map(auth_session, {
        "siding_with_openings_sqft": 2068.0,
        "siding_sqft": 2068.0,
        "_per_profile_sqft": {"lap": 1840.0, "shake": 168.0, "board_batten": 60.0},
        "eaves_lf": 100,
        "outside_corner_lf": 72,
        "_ai_avg_wall_height_ft": 18.0,
    })
    lines = data["lines"]
    vinyl_siding = [l for l in lines if l.get("tab") == "vinyl" and l.get("section") == "Vinyl Siding"]
    assert len(vinyl_siding) == 3, \
        f"expected 3 distinct vinyl siding lines (lap/shake/B&B), got {len(vinyl_siding)}: " \
        f"{[l['name'] for l in vinyl_siding]}"

    # And the new gutter accessories still emit:
    assert _gutter(lines, "Mitre") is not None
    assert _gutter(lines, "Pipe Clips") is not None
    assert _gutter(lines, "Gutter Sealant") is not None
    assert _gutter(lines, 'Downspout 6"') is not None


# ---------------------------------------------------------------------------
# 6. L-shaped house with inside corner: hip roof should add inside mitre too
# ---------------------------------------------------------------------------
def test_l_shaped_house_inside_corner_adds_mitre(auth_session):
    """4 outside corners + 1 inside corner = 5 mitres on hip roof."""
    data = _post_map(auth_session, {
        "eaves_lf": 120,
        "outside_corner_lf": 72,  # 4 corners
        "inside_corner_lf": 18,   # 1 inside corner
        "_ai_avg_wall_height_ft": 18.0,
    })
    mitre = _gutter(data["lines"], "Mitre")
    assert mitre is not None and mitre["qty"] == 5, \
        f"L-shape hip: expected 5 mitres (4 out + 1 in), got {mitre and mitre['qty']}"
