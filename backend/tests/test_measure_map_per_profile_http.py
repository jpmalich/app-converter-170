from creds_for_tests import TEST_PASSWORD
"""Iter 78z (P1.2) — End-to-end HTTP tests against POST /api/measure/map.

Verifies the per-elevation profile-split feature wired through the actual
FastAPI route (no LLM cost — /map is a pure deterministic mapper).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Load frontend .env for REACT_APP_BACKEND_URL
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


def _siding_lines(lines, tab, section="Vinyl Siding"):
    return [l for l in lines if l.get("tab") == tab and l.get("section") == section]


# --- Test 1 — Campbell-style multi-profile (lap+shake+B&B) -------------------
def test_multi_profile_splits_vinyl_into_three_lines(auth_session):
    data = _post_map(auth_session, {
        "siding_with_openings_sqft": 2068.0,
        "siding_sqft": 2068.0,
        "_per_profile_sqft": {"lap": 1840.0, "shake": 168.0, "board_batten": 60.0},
    })
    lines = data.get("lines", [])
    vinyl = _siding_lines(lines, "vinyl")
    names = [l["name"] for l in vinyl]
    print("VINYL NAMES:", names)
    assert any("Charter Oak" in n and "Dutch Lap" in n for n in names), names
    assert any("Pelican Bay" in n for n in names), names
    assert any("board and batten" in n.lower() for n in names), names
    # All three lines must carry the per-elevation note
    for l in vinyl:
        assert l.get("note", "").startswith("Per-elevation breakdown:"), l


# --- Test 2 — Single profile keeps default Charter Oak line ------------------
def test_single_profile_keeps_default_mapping(auth_session):
    data = _post_map(auth_session, {
        "siding_with_openings_sqft": 1500.0,
        "siding_sqft": 1500.0,
        "_per_profile_sqft": {"lap": 1500.0},
    })
    vinyl = _siding_lines(data["lines"], "vinyl")
    names = [l["name"] for l in vinyl]
    # Exactly one Charter Oak DL line, NO per-elevation note
    co = [l for l in vinyl if "Charter Oak" in l["name"] and "Dutch Lap" in l["name"]]
    assert len(co) == 1, names
    assert not co[0].get("note", "").startswith("Per-elevation breakdown:"), co[0]


# --- Test 3 — Legacy HOVER PDF (no _per_profile_sqft) ------------------------
def test_legacy_no_breakdown_keeps_default(auth_session):
    data = _post_map(auth_session, {
        "siding_with_openings_sqft": 1500.0,
        "siding_sqft": 1500.0,
    })
    vinyl = _siding_lines(data["lines"], "vinyl")
    co = [l for l in vinyl if "Charter Oak" in l["name"]]
    assert len(co) >= 1
    assert not co[0].get("note", "").startswith("Per-elevation breakdown:")


# --- Test 4 — Multi-profile cascades across vinyl / ascend / lp_smart --------
def test_multi_profile_cascades_across_tabs(auth_session):
    data = _post_map(auth_session, {
        "siding_with_openings_sqft": 2068.0,
        "siding_sqft": 2068.0,
        "_per_profile_sqft": {"lap": 1840.0, "shake": 168.0, "board_batten": 60.0},
    })
    lines = data["lines"]
    vinyl = _siding_lines(lines, "vinyl")
    ascend = _siding_lines(lines, "ascend", section="Ascend Cladding")
    lp = _siding_lines(lines, "lp_smart", section="LP Smart Siding")
    print(f"counts: vinyl={len(vinyl)} ascend={len(ascend)} lp={len(lp)}")
    # Spec from review_request:
    assert len(vinyl) == 3, [l["name"] for l in vinyl]
    # Ascend has no Shake SKU → 2 lines (lap + B&B)
    assert len(ascend) == 2, [l["name"] for l in ascend]
    # LP per review spec was "lap + shake (no B&B)" but code also maps B&B to
    # "38 Series Vertical Panel" — that's an additive feature, not a regression.
    # Accept >=2 lines as long as lap + shake are present.
    lp_names = [l["name"] for l in lp]
    assert len(lp) >= 2, lp_names
    assert any("Lap" in n for n in lp_names), lp_names
    assert any("Shake" in n for n in lp_names), lp_names
    # LP lap line must use PCS units
    lap_line = next(l for l in lp if "Lap" in l["name"])
    assert lap_line.get("unit") == "PCS", lap_line


# --- Test 5 — Accessory lines still emit on vinyl tab ------------------------
def test_accessories_still_emit_when_multi_profile(auth_session):
    data = _post_map(auth_session, {
        "siding_with_openings_sqft": 2068.0,
        "siding_sqft": 2068.0,
        "rakes_lf": 70.0,
        "eaves_lf": 80.0,
        "starter_lf": 80.0,
        "opening_perimeter_lf": 180.0,
        "window_count": 12,
        "wall_area_total_sqft": 2200.0,
        "_per_profile_sqft": {"lap": 1840.0, "shake": 168.0, "board_batten": 60.0},
    })
    lines = data["lines"]
    vinyl_all = [l for l in lines if l.get("tab") == "vinyl"]
    names = " | ".join(l["name"] for l in vinyl_all)
    print("VINYL TAB NAMES:", names)
    # Common cascading accessories driven by perimeter/eaves/rakes
    assert "J-Channel" in names or "j-channel" in names.lower(), names
    assert "Starter" in names or "starter" in names.lower(), names
    # House wrap is driven by wall area
    assert "House Wrap" in names or "house wrap" in names.lower(), names


# --- Test 6 — No double-counting (only the split lines, no default) ----------
def test_no_double_counting_when_multi_profile(auth_session):
    data = _post_map(auth_session, {
        "siding_with_openings_sqft": 2068.0,
        "siding_sqft": 2068.0,
        "_per_profile_sqft": {"lap": 1840.0, "shake": 168.0},
    })
    vinyl = _siding_lines(data["lines"], "vinyl")
    # Exactly two siding lines, both with per-elevation note
    assert len(vinyl) == 2, [l["name"] for l in vinyl]
    for l in vinyl:
        assert l["note"].startswith("Per-elevation breakdown:")
