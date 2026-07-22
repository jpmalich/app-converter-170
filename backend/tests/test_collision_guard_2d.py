"""COLLISION GUARD — 2D AMENDMENT pins (Howard's ruling 2026-07-23).

A collision requires overlap in BOTH axes: the along-wall horizontal span
AND the vertical extent (sill/base → head). Elements clear in either axis
never flag. FOUNDING FALSE POSITIVE: red house front W1 (48×34, sill
11'-5⅛") × G2 (100×73 garage door at grade) — 17⅝" horizontal overlap,
64" of vertical clearance — flagged BEFORE this amendment, clean AFTER.

Uncertainty rule preserved: an element with NO sill read (v bounds
absent/None) cannot prove clearance, so horizontal overlap alone still
flags. Flag-always/suppress-never semantics unchanged.

Count pins (verbatim, before → after):
  • red house FRONT collisions: 1 (W1 × G2, 17⅝") → 0
  • haugh EST-067615 FRONT collisions: 21 → 8 (13 vertically-clear
    artifact pairs retired; the flooding-fixture pin >3 still holds)
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from routes.elevation_sheets import detect_collisions  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
REDHOUSE_EST = "673707d5-9b7e-4d8f-8eaf-63c86820f611"  # EST-910869
HAUGH_EST = "48231310-3872-4d4e-b657-35ade10c1cb8"     # EST-067615


def _redhouse_front_pair():
    """The founding pair, at the run's own numbers (W1 center 13.5',
    48×34 sill 137.1"; G2 center 18.2', 100×73 at grade)."""
    return [
        {"name": "W1", "kind": "opening", "base": "b1",
         "lo_ft": 13.5 - 2.0, "hi_ft": 13.5 + 2.0,
         "v_lo_ft": 137.1 / 12.0, "v_hi_ft": (137.1 + 34.0) / 12.0},
        {"name": "G2", "kind": "opening", "base": "b2",
         "lo_ft": 18.2 - 100.0 / 24.0, "hi_ft": 18.2 + 100.0 / 24.0,
         "v_lo_ft": 0.0, "v_hi_ft": 73.0 / 12.0},
    ]


def test_founding_false_positive_vertically_clear_no_flag():
    """Horizontal overlap 17.6" but 64" of vertical clearance → clean."""
    assert detect_collisions(_redhouse_front_pair()) == []


def test_both_axes_overlap_still_flags_with_v_overlap_reported():
    els = _redhouse_front_pair()
    els[0]["v_lo_ft"], els[0]["v_hi_ft"] = 4.0, 7.0  # drop W1 into G2's band
    cols = detect_collisions(els)
    assert len(cols) == 1 and set(cols[0]["elements"]) == {"W1", "G2"}
    assert cols[0]["overlap_in"] == 17.6
    assert cols[0]["v_overlap_in"] == pytest.approx(25.0, abs=0.1)  # 73" head − 48" sill
    assert cols[0]["suppressed"] is None  # flag-always semantics unchanged


def test_unknown_vertical_extent_cannot_prove_clearance():
    """No sill read on either element → horizontal overlap alone flags
    (uncertainty flags, never silently clears). Also pins backward
    compatibility: 1D guard elements keep their pre-amendment behavior."""
    els = _redhouse_front_pair()
    for e in els:
        e.pop("v_lo_ft"), e.pop("v_hi_ft")
    cols = detect_collisions(els)
    assert len(cols) == 1
    assert cols[0]["v_overlap_in"] is None
    assert cols[0]["v_overlap_label"] == "unknown (no sill read)"
    # one side known, other unknown → still cannot prove clearance
    els[0]["v_lo_ft"], els[0]["v_hi_ft"] = 137.1 / 12.0, 171.1 / 12.0
    assert len(detect_collisions(els)) == 1


def test_vertical_abutment_within_tolerance_is_clear():
    """Head exactly at the other's sill (0" vertical overlap ≤ tol) →
    clear, same tolerance rule as the horizontal axis."""
    els = _redhouse_front_pair()
    els[0]["v_lo_ft"], els[0]["v_hi_ft"] = 73.0 / 12.0, 107.0 / 12.0
    assert detect_collisions(els) == []


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def test_redhouse_front_live_no_w1_g2_false_positive(session):
    """ACCEPTANCE SHEET — the founding example on the live route.
    BEFORE: 1 collision (W1 × G2, 17⅝" horizontal). AFTER: 0 — W1's sill
    (11'-5⅛") clears G2's head (6'-1") by 64"."""
    r = session.get(f"{API}/estimates/{REDHOUSE_EST}/elevation-sheet/front", timeout=30)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["collisions"] == []
    for o in s["openings"]:
        assert o["collision"] is False, f"{o['tag']} wrongly flagged"
    # schedule itself untouched: G1 W1 G2 D1 all still render
    assert [o["tag"] for o in s["openings"]] == ["G1", "W1", "G2", "D1"]


def test_haugh_front_true_collisions_survive(session):
    """The flooding fixture keeps its TRUE collisions: 21 → 8 (pinned).
    Every retired pair was vertically clear; every survivor overlaps in
    both axes (or cannot prove vertical clearance)."""
    r = session.get(f"{API}/estimates/{HAUGH_EST}/elevation-sheet/front", timeout=30)
    assert r.status_code == 200, r.text
    s = r.json()
    assert len(s["collisions"]) == 8
    pairs = {frozenset(c["elements"]) for c in s["collisions"]}
    assert frozenset({"W1", "W2"}) in pairs      # both-axes overlap survives
    assert frozenset({"W1", "W4"}) not in pairs  # vertically clear — retired
