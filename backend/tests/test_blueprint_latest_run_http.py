"""BLUEPRINT LATEST-RUN endpoint (Howard ruled 2026-08-11 send-3).

Powers the persistent entry-link surface (BlueprintElevationEntry). The
sheet renders from ANY COMPLETED READ, applied or not — this endpoint
lets the estimate page know which state the entry chip should be in
(available/no-run/running/error) without opening the run dialog.
"""
from __future__ import annotations
from creds_for_tests import TEST_PASSWORD

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import requests

from api_base import BASE_URL as BASE

API = f"{BASE}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PW = TEST_PASSWORD


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=10)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return s


def test_latest_run_endpoint_registered(session):
    """The route exists — not 404-because-missing but 404-because-estimate."""
    r = session.get(
        f"{API}/estimates/{uuid.uuid4().hex}/blueprint-latest-run", timeout=10)
    assert r.status_code == 404
    # 404 from the handler ("Estimate not found"), not from a missing route.
    assert "estimate" in r.text.lower()


def test_est_886440_latest_run_returns_available(session):
    """EST-886440 has run 80c10620 archived — the entry surface must be
    'available' so the persistent link mount can render EL-1..EL-4."""
    # Look up EST-886440 by number.
    r = session.get(f"{API}/estimates", timeout=15)
    assert r.status_code == 200
    ests = r.json()
    target = next((e for e in ests
                   if e.get("estimate_number") == "EST-886440"), None)
    if not target:
        pytest.skip("EST-886440 not on this session's account — fixture-only test")
    eid = target["id"]
    r = session.get(
        f"{API}/estimates/{eid}/blueprint-latest-run", timeout=10)
    assert r.status_code == 200
    d = r.json()
    # The 8-11 grading chain run is done; the entry surface must speak
    # "available" so the persistent card renders links (not a chip).
    assert d["available"] is True
    assert d["state"] == "ready"
    assert d.get("run_id")
    # Walls carried — at least front (the acceptance sheet) is present.
    assert "front" in (d.get("walls") or [])


def test_entry_surface_speaks_state_and_way_out_when_no_run(session):
    """A brand-new estimate has no run. The endpoint must return
    available=False + a way-out message so the entry chip speaks
    STATE + WAY OUT (never invisible)."""
    # Create a throw-away test estimate.
    r = session.post(f"{API}/estimates",
                     json={"customer_name": "TEST_entry_link_no_run",
                           "address": "n/a"}, timeout=10)
    assert r.status_code == 200
    eid = r.json()["id"]
    try:
        r = session.get(
            f"{API}/estimates/{eid}/blueprint-latest-run", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["available"] is False
        assert d["state"] == "no_run"
        # The way-out sentence — chip contract.
        msg = str(d.get("message") or "").lower()
        assert "blueprint" in msg
        assert "tile" in msg or "start" in msg
    finally:
        # Cleanup.
        try:
            session.delete(f"{API}/estimates/{eid}", timeout=10)
        except Exception:
            pass


def test_apply_takeoff_guard_still_refuses_est_886440(session):
    """Guard report (§3): PUT /estimates/{id} is covered by
    refuse_untouchable — apply-takeoff writes through this path and 423s
    on EST-886440. This pin is the standing regression: any future write
    path added to Apply that bypasses PUT would need to carry its own
    guard, and this test names the ruling as of today."""
    r = session.get(f"{API}/estimates", timeout=15)
    assert r.status_code == 200
    ests = r.json()
    target = next((e for e in ests
                   if e.get("estimate_number") == "EST-886440"), None)
    if not target:
        pytest.skip("EST-886440 not on this session's account")
    eid = target["id"]
    # Attempt a benign PUT.
    r = session.put(f"{API}/estimates/{eid}",
                    json={"customer_name": "guard-check"}, timeout=10)
    assert r.status_code == 423, (
        "the guard must return 423 on EST-886440 — if this pin fires "
        "green, the apply-takeoff path is no longer refused"
    )
    assert "UNTOUCHABLE" in r.text
