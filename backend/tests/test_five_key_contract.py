"""FIVE-KEY schedule contract pins (ruled 2026-07-20, Spec v2 C-6/C-7).

Contract: opening categories are CLOSED at exactly
{windows, doors, patio_doors, vents, garage_doors}. Every category gets
full provenance, ratify verbs, collision-guard registration, and basis
treatment. Future types still arrive by proposal.

DEFECT REGRESSION (audit 2026-07-20, logged in the integrity register):
garage_door / patio_door openings previously folded into 'Entry door'
via the `"door" in type` check — dormant misclassification. These pins
make that fold impossible to reintroduce silently.
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from routes.elevation_sheets import _bind_openings, detect_collisions  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"

FIVE_KEYS = {"windows", "doors", "patio_doors", "vents", "garage_doors"}


def _raw_five():
    return {"openings": [
        {"type": "window", "wall": "front", "width_in": 36, "height_in": 60,
         "along_wall_ft": 6.0, "bbox": {"x": 0.1, "y": 0.4, "w": 0.05, "h": 0.35}},
        {"type": "entry_door", "wall": "front", "width_in": 36, "height_in": 80,
         "along_wall_ft": 16.0, "bbox": {"x": 0.3, "y": 0.5, "w": 0.05, "h": 0.4}},
        {"type": "patio_door", "wall": "front", "width_in": 72, "height_in": 80,
         "along_wall_ft": 26.0, "bbox": {"x": 0.45, "y": 0.5, "w": 0.1, "h": 0.4}},
        {"type": "garage_door", "wall": "front", "width_in": 192, "height_in": 84,
         "along_wall_ft": 42.0, "bbox": {"x": 0.6, "y": 0.48, "w": 0.25, "h": 0.42}},
        {"type": "vent", "wall": "front", "width_in": 12, "height_in": 8,
         "along_wall_ft": 55.0, "bbox": {"x": 0.9, "y": 0.55, "w": 0.02, "h": 0.05}},
    ]}


def test_five_categories_tag_and_type():
    out = _bind_openings(_raw_five(), "front", [])
    assert [o["tag"] for o in out] == ["W1", "D1", "P1", "G1", "V1"]
    assert [o["type"] for o in out] == [
        "Window", "Entry door", "Patio door", "Garage door", "Vent"]


def test_defect_regression_no_door_fold():
    """AUDIT DEFECT RETIRED: garage/patio doors must NEVER type as
    'Entry door' — the pre-amendment `"door" in type` fold."""
    out = _bind_openings(_raw_five(), "front", [])
    entry = [o for o in out if o["type"] == "Entry door"]
    assert len(entry) == 1 and entry[0]["tag"] == "D1"
    assert next(o for o in out if o["tag"] == "P1")["type"] == "Patio door"
    assert next(o for o in out if o["tag"] == "G1")["type"] == "Garage door"


def test_all_door_categories_sit_at_grade():
    out = _bind_openings(_raw_five(), "front", [])
    for tag in ("D1", "P1", "G1"):
        o = next(x for x in out if x["tag"] == tag)
        assert o["sill_in"] == 0.0 and o["sill_tag"] == "AI-READ ✓", tag
    # window sill still door-anchored from bbox — basis treatment intact
    w1 = next(x for x in out if x["tag"] == "W1")
    assert w1["sill_in"] is not None and w1["sill_tag"] == "ESTIMATED"


def test_verb_machinery_corrected_type_to_garage():
    """Ratify verbs cover every category: a corrected_type=garage_door
    matcher re-types a window row to Garage door (G-tagged)."""
    raw = {"openings": [
        {"type": "window", "wall": "front", "width_in": 36, "height_in": 60,
         "along_wall_ft": 6.0, "style": ""}]}
    matchers = [{"wall": "front", "type": "window", "style": "", "dims": [36.0, 60.0],
                 "removed": False, "corrected_type": "garage_door"}]
    out = _bind_openings(raw, "front", matchers)
    assert [o["tag"] for o in out] == ["G1"]
    assert out[0]["type"] == "Garage door" and out[0]["sill_in"] == 0.0


def test_collision_guard_registers_garage_door():
    """Collision-guard registration is category-complete: a garage door
    overlapping a window flags BOTH (opening × opening — no suppression)."""
    elements = [
        {"name": "G1", "kind": "opening", "base": "position AI-READ ✓ · center 10'-0\"",
         "lo_ft": 2.0, "hi_ft": 18.0},
        {"name": "W1", "kind": "opening", "base": "position AI-READ ✓ · center 17'-0\"",
         "lo_ft": 15.5, "hi_ft": 18.5},
    ]
    cols = detect_collisions(elements)
    assert len(cols) == 1 and set(cols[0]["elements"]) == {"G1", "W1"}
    assert cols[0]["suppressed"] is None  # openings never suppress each other


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def test_live_contract_closed_at_five_keys(session):
    """HTTP: every sheet emits EXACTLY the five keys — closed contract."""
    for which in ("front", "left", "back", "right"):
        r = session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/{which}", timeout=30)
        assert r.status_code == 200, r.text
        counts = r.json()["opening_counts"]
        assert set(counts.keys()) == FIVE_KEYS, which
        assert all(isinstance(v, int) for v in counts.values()), which
