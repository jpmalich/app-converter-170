from creds_for_tests import TEST_PASSWORD
"""Chase-relocation verb + audit timeline (ruled 2026-07-15).

Fixture per ruling: the mislocated chase on letrick 7-14-26 7pm (photo run
d6679448 — locators put the chase ISC pair on "right"; truth is back wall).
Tests relocate → assert → revert, leaving the estimate as found.
"""
import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
EST_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"  # letrick 7-14-26 7pm
CHASE_KEY = "corner:isc:chimney-chase-near-side-inside-corner-on-right-wall"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s
    # leave the estimate as found
    s.post(f"{API}/estimates/{EST_ID}/lp-field-verify",
           json={"key": CHASE_KEY, "status": "unverified"}, timeout=15)


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def _preview(session):
    r = session.post(f"{API}/estimates/{EST_ID}/lp-package/preview", json={}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _item(pkg, key):
    return next(it for it in pkg["amber_items"] if it["key"] == key)


# ── Unit: _apply_corner_review overlay ────────────────────────────────

CORNERS = [
    {"type": "inside", "locator": "chimney chase near-side inside corner on right wall",
     "walls": ["right"], "tier": "estimated", "position_frac": 0.7},
    {"type": "outside", "locator": "plain house corner", "walls": ["front"], "tier": "confirmed"},
]


def test_relocated_corner_carries_corrected_wall():
    from routes.lp_package_routes import _apply_corner_review
    state = {CHASE_KEY: {"status": "user_relocated", "to": "back", "position_frac": 0.3}}
    out = _apply_corner_review(CORNERS, state)
    assert len(out) == 2
    assert out[0]["walls"] == ["back"] and out[0]["relocated_to"] == "back"
    assert out[0]["position_frac"] == 0.3
    # scope fence: nothing else invented — locator/tier/type untouched
    assert out[0]["locator"] == CORNERS[0]["locator"] and out[0]["tier"] == "estimated"
    assert CORNERS[0]["walls"] == ["right"]  # source untouched


def test_removed_corner_leaves_assembly_inputs():
    from routes.lp_package_routes import _apply_corner_review
    state = {CHASE_KEY: {"status": "user_removed"}}
    out = _apply_corner_review(CORNERS, state)
    assert len(out) == 1 and out[0]["locator"] == "plain house corner"


def test_relocate_requires_valid_wall(session):
    r = session.post(f"{API}/estimates/{EST_ID}/lp-field-verify",
                     json={"key": CHASE_KEY, "status": "relocated", "to_wall": "roof"}, timeout=15)
    assert r.status_code == 400
    r = session.post(f"{API}/estimates/{EST_ID}/lp-field-verify",
                     json={"key": CHASE_KEY, "status": "relocated", "to_wall": "back",
                           "position_frac": 1.7}, timeout=15)
    assert r.status_code == 400


# ── E2E on the ruled fixture ──────────────────────────────────────────

def test_chase_relocation_e2e(session, mongo_db):
    pkg = _preview(session)
    before = _item(pkg, CHASE_KEY)
    assert before["status"] == "unverified" and before["walls"] == ["right"]

    # relocate right → back (truth per Howard's field check)
    r = session.post(f"{API}/estimates/{EST_ID}/lp-field-verify",
                     json={"key": CHASE_KEY, "status": "relocated", "to_wall": "back",
                           "from_walls": ["right"], "position_frac": 0.8}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "user_relocated" and body["to"] == "back"
    assert body["from"] == ["right"] and body["by"] and body["at"]

    pkg2 = _preview(session)
    it = _item(pkg2, CHASE_KEY)
    assert it["status"] == "user_relocated" and it["relocated_to"] == "back"
    assert it["position_frac"] == 0.8

    # journey-logged
    est = mongo_db.estimates.find_one({"id": EST_ID}, {"tracking": 1})
    evs = [t for t in est["tracking"] if t["type"] == "corner.relocated"]
    assert evs and evs[-1]["meta"]["to"] == "back" and evs[-1]["meta"]["from"] == ["right"]

    # revertible
    r = session.post(f"{API}/estimates/{EST_ID}/lp-field-verify",
                     json={"key": CHASE_KEY, "status": "unverified"}, timeout=15)
    assert r.status_code == 200
    pkg3 = _preview(session)
    assert _item(pkg3, CHASE_KEY)["status"] == "unverified"
    est = mongo_db.estimates.find_one({"id": EST_ID}, {"tracking": 1})
    assert any(t["type"] == "corner.reset" for t in est["tracking"])


def test_removed_corner_redrives_stick_note(session):
    """Amber OSC removal must re-derive the OSC line note (2 amber → 1)."""
    osc_key = "corner:osc:chimney-chase-near-side-outside-corner"
    def osc_note():
        pkg = _preview(session)
        return next(l["note"] for l in pkg["lines"] if "OSC" in l["name"])
    assert "2 unconfirmed (amber)" in osc_note()
    r = session.post(f"{API}/estimates/{EST_ID}/lp-field-verify",
                     json={"key": osc_key, "status": "removed"}, timeout=15)
    assert r.status_code == 200
    try:
        assert "1 unconfirmed (amber)" in osc_note()
    finally:
        session.post(f"{API}/estimates/{EST_ID}/lp-field-verify",
                     json={"key": osc_key, "status": "unverified"}, timeout=15)
    assert "2 unconfirmed (amber)" in osc_note()


# ── Audit timeline: admin boundary ────────────────────────────────────

def test_admin_events_endpoint():
    token = os.environ["SUPPLIER_ADMIN_TOKEN"]
    r = requests.get(f"{API}/admin/estimates/{EST_ID}/events",
                     headers={"X-Admin-Token": token}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["estimate"]["id"] == EST_ID
    types = {e["type"] for e in body["events"]}
    assert "corner.relocated" in types and "corner.reset" in types
    # newest first
    ats = [e["at"] for e in body["events"] if e.get("at")]
    assert ats == sorted(ats, reverse=True)


def test_admin_events_requires_token():
    r = requests.get(f"{API}/admin/estimates/{EST_ID}/events", timeout=15)
    assert r.status_code in (401, 403)
