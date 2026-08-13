"""GUARD EXTENSION + HUMAN-WRITE LEDGER (Howard ruled 2026-08-11 send-4 item 3).

"THE GUARD BLOCKS DERIVED WRITES. IT NEVER BLOCKS HUMAN ENTRY.
Tape-check and profile-annotations are MY input. Human entry outranks
every read by sealed ruling, and a protected estimate that will not let
me tape is a protection that fights the ladder it exists to serve.
Those ride above the freeze.

ACCURACY-REPORT FREEZE/REVOKE IS AN ARTIFACT OPERATION AND IS GUARDED.

Every human write to a protected estimate GETS LEDGERED — the chain
should record when I touched it, even though I am allowed to."

These pins cover:
  a) Guard extension: freeze/revoke now 423 on EST-886440.
  b) Human input rides above the freeze: tape-check + profile-
     annotations succeed against the untouchable estimate.
  c) Every human write to the untouchable estimate lands in the
     protected_estimate_ledger with kind + actor + meta + at.
  d) ledger_human_write is a NO-OP for non-untouchable estimates
     (the ledger is scoped to the frozen set).
"""
from __future__ import annotations
from creds_for_tests import TEST_PASSWORD

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import BASE_URL as BASE  # noqa: E402

API = f"{BASE}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PW = TEST_PASSWORD


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=10)
    assert r.status_code == 200
    return s


def _est_886440_id(session) -> str:
    r = session.get(f"{API}/estimates", timeout=15)
    assert r.status_code == 200
    ests = r.json()
    target = next((e for e in ests
                   if e.get("estimate_number") == "EST-886440"), None)
    if not target:
        pytest.skip("EST-886440 not on this session's account")
    return target["id"]


# ---------- (a) guard extension: freeze/revoke now 423 ----------

def test_accuracy_report_freeze_now_guarded(session):
    eid = _est_886440_id(session)
    r = session.post(f"{API}/estimates/{eid}/accuracy-report/freeze",
                     timeout=15)
    assert r.status_code == 423, (
        "freeze is an ARTIFACT operation — must 423 on EST-886440 "
        "per Howard's 2026-08-11 send-4 ruling")
    assert "UNTOUCHABLE" in r.text


def test_accuracy_report_revoke_now_guarded(session):
    eid = _est_886440_id(session)
    r = session.post(f"{API}/estimates/{eid}/accuracy-report/revoke",
                     json={"token": "any"}, timeout=15)
    assert r.status_code == 423
    assert "UNTOUCHABLE" in r.text


# ---------- (b) human input rides above the freeze ----------

def test_tape_check_write_succeeds_on_untouchable(session):
    """Howard's ruling: tape-check is HUMAN INPUT — it rides above the
    freeze. A protected estimate that refuses the ladder-work it
    exists to serve is a protection that fights itself."""
    eid = _est_886440_id(session)
    # First, read current tape state so we can restore.
    r = session.get(f"{API}/estimates/{eid}/tape-check", timeout=15)
    assert r.status_code == 200
    prev = r.json()
    # Put a benign tape value.
    payload = {"walls": {**(prev.get("walls") or {}), "front": 20.02},
               "dormers": prev.get("dormers") or [],
               "held_out": prev.get("held_out") or False}
    r = session.put(f"{API}/estimates/{eid}/tape-check", json=payload,
                    timeout=15)
    assert r.status_code == 200, (
        f"tape-check must ride above the freeze; got {r.status_code} {r.text}"
    )
    # Restore prev.
    session.put(f"{API}/estimates/{eid}/tape-check",
                json={"walls": prev.get("walls") or {},
                      "dormers": prev.get("dormers") or [],
                      "held_out": prev.get("held_out") or False},
                timeout=15)


def test_profile_annotations_ride_above_freeze(session):
    """Same ruling: profile-annotations are human input."""
    eid = _est_886440_id(session)
    # A benign write — snapshot then restore.
    r = session.get(f"{API}/estimates/{eid}", timeout=15)
    assert r.status_code == 200
    prev = (r.json() or {}).get("profile_annotations") or {}
    r = session.put(
        f"{API}/estimates/{eid}/profile-annotations",
        json={"annotations": {**prev, "_test_ride_above_freeze": True}},
        timeout=15)
    assert r.status_code == 200, (
        f"profile-annotations must ride above the freeze; got "
        f"{r.status_code} {r.text}")
    # Restore.
    session.put(f"{API}/estimates/{eid}/profile-annotations",
                json={"annotations": prev}, timeout=15)


# ---------- (c) every human write lands in the ledger ----------
# Verified via the /protected-ledger endpoint so the test uses HTTP
# only (no direct motor calls — those bind db.py's shared client to
# a per-test event loop and break subsequent asyncio.run()s elsewhere).

def test_tape_check_write_lands_in_the_ledger(session):
    """A tape-check PUT on EST-886440 must add an entry to
    protected_estimate_ledger. Ledgered kind: 'tape_check'.

    SEND-11 AMEND (2026-08-13): observes `total` (honest count),
    not `len(entries)` — the endpoint's response is now paginated
    with a truncation notice, so a saturated 200-cap must not hide
    the write behind a silent .limit()."""
    eid = _est_886440_id(session)
    # Snapshot ledger before.
    r = session.get(f"{API}/estimates/{eid}/protected-ledger", timeout=15)
    assert r.status_code == 200
    before = r.json()
    assert before["scope"] == "untouchable"
    assert "total" in before, "response must name the honest total"
    n_before = before["total"]
    # Do a benign tape-check PUT.
    prev_r = session.get(f"{API}/estimates/{eid}/tape-check", timeout=15)
    prev = prev_r.json()
    session.put(f"{API}/estimates/{eid}/tape-check", json={
        "walls": {**(prev.get("walls") or {}), "front": 20.03},
        "dormers": prev.get("dormers") or [],
        "held_out": prev.get("held_out") or False,
    }, timeout=15)
    # Read ledger after.
    r2 = session.get(f"{API}/estimates/{eid}/protected-ledger", timeout=15)
    after = r2.json()
    assert after["total"] == n_before + 1
    latest = after["entries"][0]
    assert latest["kind"] == "tape_check"
    assert latest["actor_email"]  # not empty
    # Restore.
    session.put(f"{API}/estimates/{eid}/tape-check", json={
        "walls": prev.get("walls") or {},
        "dormers": prev.get("dormers") or [],
        "held_out": prev.get("held_out") or False,
    }, timeout=15)


def test_profile_annotations_write_lands_in_the_ledger(session):
    """A profile-annotations PUT on EST-886440 must add an entry with
    kind 'profile_annotations'.

    SEND-11 AMEND (2026-08-13): observes `total`, same reasoning."""
    eid = _est_886440_id(session)
    r = session.get(f"{API}/estimates/{eid}/protected-ledger", timeout=15)
    n_before = r.json()["total"]
    # Snapshot then write.
    est_r = session.get(f"{API}/estimates/{eid}", timeout=15)
    prev = (est_r.json() or {}).get("profile_annotations") or {}
    session.put(
        f"{API}/estimates/{eid}/profile-annotations",
        json={"annotations": {**prev,
                              "_test_ledger_pin": True}}, timeout=15)
    r2 = session.get(f"{API}/estimates/{eid}/protected-ledger", timeout=15)
    body = r2.json()
    assert body["total"] == n_before + 1
    assert body["entries"][0]["kind"] == "profile_annotations"
    # Restore.
    session.put(f"{API}/estimates/{eid}/profile-annotations",
                json={"annotations": prev}, timeout=15)


def test_ledger_scoped_to_untouchable_only(session):
    """Non-untouchable estimates return scope: not_untouchable, entries:
    [] — the ledger is FROZEN-SET-ONLY (a general audit log lives
    elsewhere)."""
    r = session.get(f"{API}/estimates", timeout=15)
    ests = r.json()
    other = next((e for e in ests
                  if e.get("estimate_number") != "EST-886440"), None)
    if not other:
        pytest.skip("no non-untouchable estimate on this account")
    r = session.get(
        f"{API}/estimates/{other['id']}/protected-ledger", timeout=15)
    assert r.status_code == 200
    assert r.json()["scope"] == "not_untouchable"
    assert r.json()["entries"] == []


def test_untouchable_module_carries_the_ruling():
    """The docstring names the send-4 ruling — so future readers see
    the extension, not just the original 2026-08-09 write-guard."""
    src = Path("/app/backend/untouchable.py").read_text()
    assert "GUARD EXTENSION" in src
    assert "2026-08-11" in src
    assert "ledger_human_write" in src
    assert "HUMAN ENTRY" in src
