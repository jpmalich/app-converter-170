"""FIXTURE DELETE-PROTECTION pins (Howard's consolidated ruling 2026-07-23, item 4).

  • backend-enforced: DELETE on a protected doc fails 423 with the doc
    INTACT — regardless of caller (the route refuses, not the UI)
  • un-protect is its own deliberate action (PUT /protected), then delete
    proceeds normally — never a bypass on the delete path
  • delete-preflight surfaces the protection
  • the 7 fixture keeps carry the flag; demo reset births it protected
  • UI: lock indicator replaces the delete control ("protected fixture")
Protection-survives-seed-round-trip pin lands with the 3b export/seed
tooling (the exports carry the flag).
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
REDHOUSE_EST = "673707d5-9b7e-4d8f-8eaf-63c86820f611"
PROTECTED_FIXTURES = [
    "673707d5-9b7e-4d8f-8eaf-63c86820f611",  # red house
    "e452a988-83b8-4e6e-9537-1223d0ecbf6f",  # LP pair
    "8f95c9c2-add9-416a-92f3-786a4ea2ce83",  # Letrick
    "db82ec7a-3177-406d-a602-927255e9e10e",  # doug jones
    "48231310-3872-4d4e-b657-35ade10c1cb8",  # haugh
    "d78cd3b4-a65c-4238-8d16-7827b131a85c",  # round-two (banked)
]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def test_delete_refused_on_protected_doc_intact(session):
    r = session.delete(f"{API}/estimates/{REDHOUSE_EST}", timeout=20)
    assert r.status_code == 423
    assert "Protected fixture" in r.text
    r2 = session.get(f"{API}/estimates/{REDHOUSE_EST}", timeout=20)
    assert r2.status_code == 200 and r2.json()["id"] == REDHOUSE_EST


def test_unprotect_is_separate_action_then_delete_works(session):
    est = session.post(f"{API}/estimates", json={"customer_name": "ZZ protect-pin TEMP"},
                       timeout=20).json()
    eid = est["id"]
    try:
        assert session.put(f"{API}/estimates/{eid}/protected",
                           json={"protected": True}, timeout=20).status_code == 200
        assert session.delete(f"{API}/estimates/{eid}", timeout=20).status_code == 423
        pf = session.get(f"{API}/estimates/{eid}/delete-preflight", timeout=20).json()
        assert pf["protected"] is True
        assert any("PROTECTED FIXTURE" in w for w in pf["warnings"])
        # deliberate flip FIRST, as its own action — then delete proceeds
        assert session.put(f"{API}/estimates/{eid}/protected",
                           json={"protected": False}, timeout=20).status_code == 200
        assert session.delete(f"{API}/estimates/{eid}", timeout=20).status_code == 200
        assert session.get(f"{API}/estimates/{eid}", timeout=20).status_code == 404
    finally:
        session.delete(f"{API}/estimates/{eid}", timeout=20)


def test_all_fixture_keeps_carry_the_flag(session):
    rows = session.get(f"{API}/estimates?kind=", timeout=20).json()
    by_id = {e["id"]: e for e in rows}
    for eid in PROTECTED_FIXTURES:
        if eid in by_id:
            assert by_id[eid].get("protected") is True, f"{eid[:8]} unprotected"
        else:
            r = session.get(f"{API}/estimates/{eid}", timeout=20)
            assert r.status_code == 200 and r.json().get("protected") is True, f"{eid[:8]}"
    demo = [e for e in rows if e.get("demo_key")]
    for d in demo:
        assert d.get("protected") is True, "demo estimate unprotected"


def test_demo_reset_births_protected():
    src = Path("/app/backend/routes/demo.py").read_text()
    assert '"protected": True' in src


def test_dashboard_lock_replaces_delete_control():
    jsx = Path("/app/frontend/src/pages/Dashboard.jsx").read_text()
    assert "e.protected ?" in jsx
    assert 'data-testid={`protected-${e.id}`}' in jsx
    assert "Protected fixture" in jsx
    assert "Lock" in jsx
