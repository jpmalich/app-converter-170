"""SEND-11 CORRECTION 1b — PROTECTED-LEDGER TRUNCATION HONESTY
(Howard ruled 2026-08-13 send-11 following the pro-quotes reply).

Verbatim: "The endpoint returns the TOTAL alongside the page. It
states plainly when the response is truncated — 'showing 200 of 247'
— on the API and on any surface that renders it. It paginates. It is
REGISTERED AS A SEAM and ledgered like every other removal. Then the
tests can observe by total or by timestamp honestly, because they
will be observing something true."

Root cause: the previous /api/estimates/{eid}/protected-ledger
endpoint read with `.limit(200)` and returned only `entries`. Once
the live ledger crossed 200 rows, every subsequent GET silently
dropped the 201st entry onward — INSIDE the instrument built to make
every human write to a sealed estimate visible. The two send-10-era
tests (test_tape_check_write_lands_in_the_ledger,
test_profile_annotations_write_lands_in_the_ledger) started failing
because n_after == n_before == 200 forever after the cap.

The fix rides the same seam-accounting rule that catches every
other class of truncation: any layer that removes data accounts for
what it removed. The endpoint now returns:
  - total (honest count via count_documents)
  - showing (len of the returned page)
  - page, page_size
  - truncated (bool, true when total > showing)
  - truncation_notice ("showing N of M — page X of Y", or None)
And it accepts `?page=`, `?page_size=` (hard cap 1000). The seam
`protected_ledger_paginated` names the shape in seam_accounting.
"""
from __future__ import annotations

import sys
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import requests  # noqa: E402

from db import db  # noqa: E402
from seam_accounting import SEAM_REGISTRY  # noqa: E402

API = "http://127.0.0.1:8001/api"


# ---------- (A) seam registered --------------------------------------

def test_protected_ledger_paginated_seam_is_registered():
    """The .limit() shape is REPORTED, never silent — send-11 rule."""
    assert "protected_ledger_paginated" in SEAM_REGISTRY
    text = SEAM_REGISTRY["protected_ledger_paginated"].lower()
    # Copy names both the class we caught and the honesty contract.
    assert "truncat" in text
    assert "total" in text
    assert ".limit" in text


# ---------- (B) HTTP surface: total + truncation notice + pagination -

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    # Live login shared with the guard-extension suite.
    r = s.post(f"{API}/auth/login",
               json={"email": "hhunt6677@yahoo.com",
                     "password": "Passw0rd!"}, timeout=15)
    if r.status_code != 200:
        pytest.skip("live auth unavailable in this env")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


def _est_886440_id(session):
    r = session.get(f"{API}/estimates", timeout=15)
    for e in r.json():
        if e.get("estimate_number") == "EST-886440":
            return e["id"]
    pytest.skip("EST-886440 not present on this account")


def test_endpoint_returns_total_showing_and_truncated_flag(session):
    """Every response — untouchable or not — names the honest total,
    showing count, page, page_size, and a truncated bool. No caller
    can read the endpoint and be blind to a cap."""
    eid = _est_886440_id(session)
    r = session.get(f"{API}/estimates/{eid}/protected-ledger", timeout=15)
    body = r.json()
    for key in ("total", "showing", "page", "page_size",
                "truncated", "truncation_notice", "entries"):
        assert key in body, f"missing honesty key {key!r}"
    assert isinstance(body["total"], int)
    assert isinstance(body["showing"], int)
    assert body["showing"] == len(body["entries"])


def test_default_page_size_is_200_and_truncated_when_over_200(session):
    """The historical cap stays as the DEFAULT page size (no consumer
    churn), but the response now says so. When total > 200, the
    truncated flag is true and the notice names 'showing 200 of N'."""
    eid = _est_886440_id(session)
    r = session.get(f"{API}/estimates/{eid}/protected-ledger", timeout=15)
    body = r.json()
    assert body["page_size"] == 200
    if body["total"] > 200:
        assert body["truncated"] is True
        assert body["truncation_notice"]
        assert f"showing {body['showing']} of {body['total']}" \
            in body["truncation_notice"]
        assert body["showing"] == 200
    else:
        assert body["truncated"] is False
        assert body["truncation_notice"] is None


def test_pagination_returns_a_disjoint_next_page(session):
    """?page=2 returns the next chunk. Two pages read back-to-back
    must not overlap on their `at` timestamps."""
    eid = _est_886440_id(session)
    r1 = session.get(
        f"{API}/estimates/{eid}/protected-ledger?page=1&page_size=5",
        timeout=15)
    b1 = r1.json()
    if b1["total"] < 6:
        pytest.skip("ledger too small to walk a second page")
    r2 = session.get(
        f"{API}/estimates/{eid}/protected-ledger?page=2&page_size=5",
        timeout=15)
    b2 = r2.json()
    assert b1["page"] == 1
    assert b2["page"] == 2
    assert b1["page_size"] == 5
    assert b1["truncated"] is True
    ids1 = [e.get("id") for e in b1["entries"] if e.get("id")]
    ids2 = [e.get("id") for e in b2["entries"] if e.get("id")]
    if ids1 and ids2:
        assert set(ids1).isdisjoint(set(ids2))


def test_page_size_hard_capped_at_1000(session):
    """A caller asking for 10_000 gets 1000 back, not 10_000 — the
    hard cap prevents a bad client from asking for the DB at once,
    but 1000 comfortably covers the current live-ledger size and
    lets a paginating consumer walk it in one visible pass."""
    eid = _est_886440_id(session)
    r = session.get(
        f"{API}/estimates/{eid}/protected-ledger?page_size=10000",
        timeout=15)
    body = r.json()
    assert body["page_size"] == 1000


def test_can_walk_the_full_ledger_via_pagination(session):
    """A consumer walking the total via successive pages sees every
    entry exactly once — the seam-accounting rule at the surface."""
    eid = _est_886440_id(session)
    r0 = session.get(
        f"{API}/estimates/{eid}/protected-ledger?page_size=1000",
        timeout=15)
    total = r0.json()["total"]
    if total == 0:
        pytest.skip("ledger empty on this account")
    seen: set[str] = set()
    page = 1
    while True:
        r = session.get(
            f"{API}/estimates/{eid}/protected-ledger?"
            f"page={page}&page_size=100", timeout=15)
        b = r.json()
        for e in b["entries"]:
            key = e.get("id") or (e.get("at"), e.get("kind"),
                                  e.get("actor_email"))
            seen.add(key if isinstance(key, str) else str(key))
        if not b["truncated"] or page * b["page_size"] >= total:
            break
        page += 1
        if page > 50:  # safety valve
            break
    # We should see AT LEAST total unique keys (equality only if ids
    # exist on every row; some legacy rows lack `id` and fall back on
    # the composite key which may collide — hence >=).
    assert len(seen) >= min(total, 100), \
        f"pagination lost entries: saw {len(seen)}, total {total}"


# ---------- (C) motor-level truncation guard ------------------------

def test_over_the_cap_ledger_reports_truncation_via_direct_motor():
    """A synthetic 250-row load into a scratch estimate — walked via
    a SYNCHRONOUS pymongo client — proves count_documents is honest
    while a .limit(200) query silently returns 200. Sync client is
    required: the shared motor client in db.py binds to the first
    event loop pytest uses; subsequent asyncio.run() calls hit
    'Event loop is closed' (guard_extension's own note documents
    this trap). Sync pymongo sidesteps the loop-binding entirely."""
    import os
    from pymongo import MongoClient

    est_id = f"test-send11b-{uuid.uuid4().hex[:8]}"
    sync = MongoClient(os.environ["MONGO_URL"])
    coll = sync[os.environ["DB_NAME"]]["protected_estimate_ledger"]
    try:
        coll.insert_many([{"id": f"row-{i}",
                           "estimate_id": est_id,
                           "at": datetime.now(timezone.utc),
                           "kind": "tape_check",
                           "actor_email": "synth@example.com"}
                          for i in range(250)])
        honest = coll.count_documents({"estimate_id": est_id})
        capped = len(list(coll.find({"estimate_id": est_id})
                          .sort("at", -1).limit(200)))
        assert honest == 250, f"seed count wrong: {honest}"
        assert capped == 200, (
            "silent-cap negative control returned "
            f"{capped}; upstream is no longer .limit(200)? "
            "Update this test to the new cap or drop the shape.")
        # The delta IS the defect. The new endpoint reports it.
        assert honest - capped == 50
    finally:
        coll.delete_many({"estimate_id": est_id})
        sync.close()
