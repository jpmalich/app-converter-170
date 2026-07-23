"""Slice 2 + field-verify-from-flags (approved 2026-07-17).

Pins:
  • default-profile changes carry provenance (from→to, by, at) and are
    revertible via the same mechanism (another logged set)
  • flag checklist entries ride user-measured machinery: by/at recorded,
    reopen reverts (prev retained), journey-logged
  • per-item retirement: closed flags report status=closed with closer
    named; open ones stay amber — an OFFER, never a gate (preview always
    derives regardless of open flags)
  • closing batten_wall_heights re-derives batten LF LIVE:
    LF = area÷spacing + Σ(wall heights); reopen reverts the qty
  • validation: batten close demands positive taped heights; bad
    codes/actions are 422
"""
from creds_for_tests import TEST_PASSWORD
import math
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
EST_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"  # letrick
HOVER_RUN = "7c6194d46b91444990b6910a175b12ff"  # re-ingested 2026-07-18 (TTL 2nd-instance re-arm; archived from birth)
BATTEN = '190 Series Trim 19/32" x 3" x 16\''


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s
    s.post(f"{API}/estimates/{EST_ID}/default-profile", json={"profile": None}, timeout=15)


@pytest.fixture(scope="module")
def hover_est(session):
    r = session.post(f"{API}/estimates", json={"kind": "lp_smart", "customer_name": "ZZ flags-pin TEMP"}, timeout=15)
    temp = r.json()["id"]
    rr = session.post(f"{API}/estimates/{temp}/hover-lp-run",
                      json={"hover_run_id": HOVER_RUN, "profile": "board_batten"}, timeout=30)
    assert rr.status_code == 200, rr.text
    yield temp
    session.delete(f"{API}/estimates/{temp}", timeout=15)


def _batten_qty(session, est_id):
    pkg = session.post(f"{API}/estimates/{est_id}/lp-package/preview", json={}, timeout=60).json()
    line = next(l for l in pkg["lines"] if l["name"] == BATTEN)
    return line["qty"], pkg


class TestProvenanceAndRevert:
    def test_change_carries_provenance(self, session):
        r = session.post(f"{API}/estimates/{EST_ID}/default-profile",
                         json={"profile": "board_batten"}, timeout=15).json()
        ch = r["change"]
        assert ch["from"] is None and ch["to"] == "board_batten"
        assert ch["by"] == "hhunt6677@yahoo.com" and ch["at"]

    def test_revert_is_a_logged_set(self, session):
        r = session.post(f"{API}/estimates/{EST_ID}/default-profile",
                         json={"profile": None}, timeout=15).json()
        ch = r["change"]
        assert ch["from"] == "board_batten" and ch["to"] is None


class TestFlagChecklist:
    def test_bad_code_and_action_422(self, session, hover_est):
        assert session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                            json={"code": "nope", "action": "close"}, timeout=15).status_code == 422
        assert session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                            json={"code": "corner_locators", "action": "destroy"}, timeout=15).status_code == 422

    def test_batten_close_demands_taped_heights(self, session, hover_est):
        for bad in ({}, {"wall_heights_ft": []}, {"wall_heights_ft": [9, -2]}, {"wall_heights_ft": "9,9"}):
            r = session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                             json={"code": "batten_wall_heights", "action": "close", "values": bad}, timeout=15)
            assert r.status_code == 422, bad

    def test_close_rederives_batten_lf_live_and_reopen_reverts(self, session, hover_est):
        base_qty, base_pkg = _batten_qty(session, hover_est)
        assert all(f["status"] == "open" for f in base_pkg["hover_mapping_flags"])
        heights = [9, 9, 18.5, 9]
        r = session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                         json={"code": "batten_wall_heights", "action": "close",
                               "values": {"wall_heights_ft": heights}}, timeout=15)
        assert r.status_code == 200
        entry = r.json()["entry"]
        assert entry["status"] == "closed" and entry["by"] and entry["at"]
        new_qty, new_pkg = _batten_qty(session, hover_est)
        # LIVE re-derive: LF gained Σ(heights)=45.5 → qty strictly increases
        assert new_qty > base_qty
        flag = next(f for f in new_pkg["hover_mapping_flags"] if f["code"] == "batten_wall_heights")
        assert flag["status"] == "closed" and flag["closed_by"] == "hhunt6677@yahoo.com"
        # others still open — per-item retirement, never a gate
        assert next(f for f in new_pkg["hover_mapping_flags"] if f["code"] == "corner_locators")["status"] == "open"
        # reopen reverts qty and status; prev retained (revertible machinery)
        rr = session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                          json={"code": "batten_wall_heights", "action": "reopen"}, timeout=15)
        assert rr.status_code == 200
        assert rr.json()["entry"]["prev"]["status"] == "closed"
        back_qty, back_pkg = _batten_qty(session, hover_est)
        assert back_qty == base_qty
        flag2 = next(f for f in back_pkg["hover_mapping_flags"] if f["code"] == "batten_wall_heights")
        assert flag2["status"] == "open"

    def test_simple_confirm_close(self, session, hover_est):
        r = session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                         json={"code": "opening_schedule", "action": "close",
                               "values": {"confirmed": True}}, timeout=15)
        assert r.status_code == 200
        _, pkg = _batten_qty(session, hover_est)
        assert next(f for f in pkg["hover_mapping_flags"] if f["code"] == "opening_schedule")["status"] == "closed"
