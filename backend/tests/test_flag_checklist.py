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


class TestWallHeightOneTap:
    """WALL-HEIGHT ONE-TAP (authorized 2026-07-27): the estimate-page tape
    field closes batten_wall_heights — and the taped total now feeds the
    TAB-LINE rebuild too (rebuild_lp_tab_lines folds the closed checklist,
    same as the package paths)."""

    def test_taped_heights_feed_tab_line_rebuild(self, session, hover_est):
        r = session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                         json={"code": "batten_wall_heights", "action": "close",
                               "values": {"wall_heights_ft": [9, 9, 18.5]}}, timeout=15)
        assert r.status_code == 200, r.text
        rr = session.post(f"{API}/estimates/{hover_est}/hover-lp-run",
                          json={"hover_run_id": HOVER_RUN, "profile": "board_batten"}, timeout=30)
        assert rr.status_code == 200, rr.text
        est = session.get(f"{API}/estimates/{hover_est}", timeout=30).json()
        batten = next(l for l in est["lines"]
                      if l.get("tab") == "lp_smart" and l["name"] == BATTEN)
        # WALKED (Class A sealed 2026-07-28): this fixture is the 261 Haugh
        # anatomy (Siding row 0; wrap 2064 + stucco 312 + brick 234) — the
        # lumped 2610 NEVER composes now; wrap-suggested 2064 governs.
        # 2064 ft² @ 12" o.c. (trade-spec default, ruled 2026-07-29) =
        # 2064 LF + Σ taped 36.5 = 2100.5 → ÷16 = 132.
        assert batten["qty"] == 132
        # reopen reverts the term on the next rebuild
        session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                     json={"code": "batten_wall_heights", "action": "reopen"}, timeout=15)
        session.post(f"{API}/estimates/{hover_est}/hover-lp-run",
                     json={"hover_run_id": HOVER_RUN, "profile": "board_batten"}, timeout=30)
        est2 = session.get(f"{API}/estimates/{hover_est}", timeout=30).json()
        batten2 = next(l for l in est2["lines"]
                       if l.get("tab") == "lp_smart" and l["name"] == BATTEN)
        assert batten2["qty"] == 129  # 2064 ÷ 16 — height term back to 0 (12" o.c. default)


class TestCornerCountCorrection:
    """CORNER-COUNT CORRECTION (ruled 2026-07-28, Casile re-book-check):
    closing corner_locators with a walked HUMAN count re-derives OSC
    per-corner (Q13) from the corrected count; the report's count stays
    on the line as the flagged comparison. Reopen restores the report."""

    def test_human_corner_count_governs(self, session, hover_est):
        r = session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                         json={"code": "corner_locators", "action": "close",
                               "values": {"outside_corner_count": 14}}, timeout=15)
        assert r.status_code == 200, r.text
        session.post(f"{API}/estimates/{hover_est}/hover-lp-run",
                     json={"hover_run_id": HOVER_RUN, "profile": "board_batten"}, timeout=30)
        est = session.get(f"{API}/estimates/{hover_est}", timeout=30).json()
        osc = next(l for l in est["lines"]
                   if l.get("tab") == "lp_smart" and l["name"].startswith("540 Series OSC"))
        assert osc["qty"] == 14  # 14 × max(1, ceil((140.33/14)/16)) — Q13
        assert "HUMAN count 14" in osc["note"] and "report read 20" in osc["note"]
        # reopen → report count governs again
        session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                     json={"code": "corner_locators", "action": "reopen"}, timeout=15)
        session.post(f"{API}/estimates/{hover_est}/hover-lp-run",
                     json={"hover_run_id": HOVER_RUN, "profile": "board_batten"}, timeout=30)
        est2 = session.get(f"{API}/estimates/{hover_est}", timeout=30).json()
        osc2 = next(l for l in est2["lines"]
                    if l.get("tab") == "lp_smart" and l["name"].startswith("540 Series OSC"))
        assert osc2["qty"] == 20
        assert "HUMAN count" not in osc2["note"]

    def test_bad_count_rejected(self, session, hover_est):
        r = session.post(f"{API}/estimates/{hover_est}/flag-checklist",
                         json={"code": "corner_locators", "action": "close",
                               "values": {"outside_corner_count": -3}}, timeout=15)
        assert r.status_code == 422
