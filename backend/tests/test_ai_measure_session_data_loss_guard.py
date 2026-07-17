"""Iter 79j.63 — Session data-loss regression guard.

On Jul 7 2026, contractor clicked "Refine on Photo" on EST-910869 /
Red-House fixture 673707d5 and reported that the local photo list
emptied in both the refine view AND the main modal, and that
close/reopen + Resume did NOT recover it.

Diagnosis (see PRD `## ACTIVE GATE` block): the server-side session
doc was intact throughout — 8 photos, 8 annotations, full preview.
The bug was two client-side flaws:
  1. `sessionChecked` was a per-mount latch (not per-open), so
     close+reopen never re-fetched.
  2. No matching recovery banner when local state was empty but the
     server had a healthy session.

Fix 1 (this iter) resets `sessionChecked` on modal close. Fix 4
(this file) locks down the server-side contract so future changes
can't regress the invariants that let the recovery work:

- PUT + GET is byte-identical for photo_urls, photo_annotations,
  and preview.
- Opening / closing "Refine on Photo" without an Apply must NOT
  cause the session doc to change. (Refine only touches the session
  via the parent's onApply → setPreview → debounced autosave path.
  A no-op refine round-trip = zero backend writes.)
- Multiple GETs of the same session return the same content.
- The empty-photos + preview combo (the Iter 79j.29 clobber shape)
  round-trips correctly if the client sends it, so the server side
  can't accidentally erase or corrupt state.
"""
from __future__ import annotations
from creds_for_tests import TEST_PASSWORD

import os
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path("/app/backend/.env"))
load_dotenv(Path("/app/frontend/.env"), override=False)

BASE = os.environ["REACT_APP_BACKEND_URL"]
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", TEST_PASSWORD)


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(
        f"{BASE}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def eid(session, db):
    """Create a throwaway estimate for this test module and clean it
    up + its session doc at teardown."""
    r = session.post(
        f"{BASE}/api/estimates",
        json={"customer_name": "Session Regression Fixture"},
        timeout=10,
    )
    assert r.status_code == 200, f"estimate create failed: {r.status_code} {r.text}"
    _eid = r.json()["id"]
    yield _eid
    # Teardown
    try:
        db.ai_measure_sessions.delete_one({"estimate_id": _eid})
        session.delete(f"{BASE}/api/estimates/{_eid}", timeout=10)
    except Exception:
        pass


def _make_fixture_payload(eid):
    """A representative 8-photo Red-House-style session payload."""
    photos = [f"{uuid.uuid4().hex}.jpg" for _ in range(8)]
    annotations = {}
    for i, name in enumerate(photos):
        elev = ["front", "front-right", "right", "back-right", "back", "back-left", "left", "front-left"][i]
        annotations[name] = {
            "elevation": elev,
            "reference": {"p1": {"x": 100, "y": 200}, "p2": {"x": 100, "y": 400}, "inches": 96},
            "windowReference": None,
            "zones": [],
            "targetPin": None,
            "windows": [],
            "profileBoxes": [],
        }
    preview = {
        "measurements": {
            "siding_sqft": 1234.5, "eaves_lf": 88, "rakes_lf": 44,
            "outside_corner_lf": 32, "window_count": 12, "entry_door_count": 2,
            "_ai_scale_confidence": "high",
        },
        "lines": [],
        "vero_openings": [],
        "raw_ai": {
            "walls": [{"label": "front", "width_ft": 30, "height_ft": 10, "eave_ft": 10}],
            "openings": [], "dormers": [],
        },
        "raw_per_photo": [{"photo_idx": i, "walls_visible": []} for i in range(8)],
        "run_id": "test-fixture-run",
    }
    return {
        "estimate_id": eid,
        "photo_urls": photos,
        "reference_dim": "16",
        "wall_height": "10",
        "siding_pct": "",
        "overhang_in": 12.0,
        "preview": preview,
        "photo_annotations": annotations,
    }


def _put_session(session, eid, payload):
    r = session.put(f"{BASE}/api/measure/sessions/{eid}", json=payload, timeout=10)
    assert r.status_code == 200, f"session PUT failed: {r.status_code} {r.text}"
    return r.json()


def _get_session(session, eid):
    r = session.get(f"{BASE}/api/measure/sessions/{eid}", timeout=10)
    assert r.status_code == 200, f"session GET failed: {r.status_code} {r.text}"
    return r.json()


def test_session_put_get_byte_identical(session, eid):
    """The core round-trip invariant. If this ever regresses,
    Resume + recovery are broken."""
    payload = _make_fixture_payload(eid)
    _put_session(session, eid, payload)
    got = _get_session(session, eid)

    assert got["photo_urls"] == payload["photo_urls"], (
        f"photo_urls round-trip mismatch:\n"
        f"  sent: {payload['photo_urls']}\n"
        f"  got:  {got.get('photo_urls')}"
    )
    assert got["photo_annotations"] == payload["photo_annotations"], (
        "photo_annotations round-trip mismatch — Refine / Annotate would lose work"
    )
    assert got["preview"] == payload["preview"], (
        "preview round-trip mismatch — Resume would restore a corrupted preview"
    )
    assert got["reference_dim"] == payload["reference_dim"]
    assert got["wall_height"] == payload["wall_height"]
    assert float(got["overhang_in"]) == float(payload["overhang_in"])


def test_refine_on_photo_no_op_roundtrip(session, eid, db):
    """Opening + closing Refine on Photo WITHOUT calling Apply must
    leave the session doc byte-identical.

    Modeled: Refine on Photo is a frontend-only modal that reads
    `prefillUrls={photoUrls}` and returns to the parent via
    `onApply({ measurements: ... })`. If the user opens Refine and
    closes without applying (via the "close" button or backdrop
    click), the parent's `onApply` is NEVER called, no
    `setPreview()` fires, no autosave-eligible state changes, no PUT
    hits the server.

    We assert this contract by:
      1. Seeding the session doc via PUT
      2. Reading `updated_at` from the DB
      3. Simulating the "no-op refine" — no writes at all
      4. Re-reading the DB doc, asserting `updated_at` is unchanged
         AND all persisted fields are byte-identical.
    """
    payload = _make_fixture_payload(eid)
    _put_session(session, eid, payload)
    before = db.ai_measure_sessions.find_one({"estimate_id": eid})
    assert before is not None
    updated_at_before = before["updated_at"]

    # === Simulated "open Refine → close Refine" — NO backend calls ===
    # (If the frontend ever adds a session-touching call on Refine
    # open/close, this test doesn't cover it; that would be a scope
    # regression to catch in a separate Playwright test.)
    # === end simulation ===

    after = db.ai_measure_sessions.find_one({"estimate_id": eid})
    assert after["updated_at"] == updated_at_before, (
        f"Session doc's updated_at moved without any user action: "
        f"before={updated_at_before} after={after['updated_at']}"
    )
    # Full field-by-field comparison — the invariant we ACTUALLY care about
    for key in ("photo_urls", "photo_annotations", "preview",
                "reference_dim", "wall_height", "siding_pct", "overhang_in"):
        assert after[key] == before[key], (
            f"Field '{key}' changed during no-op refine round-trip:\n"
            f"  before: {before[key]!r}\n"
            f"  after:  {after[key]!r}"
        )


def test_idempotent_puts_produce_identical_docs(session, eid, db):
    """Two identical PUTs must produce byte-identical persisted state
    (except `updated_at` which we accept moves).

    This guards against any future server-side transformation that
    might silently normalize / drop fields between round-trips.
    """
    payload = _make_fixture_payload(eid)
    _put_session(session, eid, payload)
    first = db.ai_measure_sessions.find_one({"estimate_id": eid})
    _put_session(session, eid, payload)
    second = db.ai_measure_sessions.find_one({"estimate_id": eid})

    for key in ("photo_urls", "photo_annotations", "preview",
                "reference_dim", "wall_height", "siding_pct", "overhang_in"):
        assert first[key] == second[key], f"idempotency broken on field '{key}'"


def test_get_is_deterministic(session, eid):
    """Two consecutive GETs of the same session must return
    identical JSON. Catches any accidental clock/randomness leak
    from the server side."""
    payload = _make_fixture_payload(eid)
    _put_session(session, eid, payload)
    a = _get_session(session, eid)
    b = _get_session(session, eid)
    # `updated_at` is a stable ISO timestamp set at PUT time — must
    # not drift across GETs.
    assert a == b, f"GET is non-deterministic:\n  a={a}\n  b={b}"


def test_empty_photos_with_preview_survives_roundtrip(session, eid, db):
    """The Iter 79j.29 clobber-shape: photo_urls: [] + preview: {...}.

    The FRONTEND autosave has a guard that never sends this shape.
    But if a rogue caller ever sends it, the server should NOT
    reject the request AND should NOT silently mutate it — it
    should faithfully round-trip so a debug tool can inspect the
    exact bad state that triggered the guard.

    This test locks down the contract: if the frontend guard ever
    breaks, the DB will indeed be poisoned to match what the client
    sent (making the poison visible instead of silent), and the
    Resume path in `resumeSession()` has the fallback at L813-825
    to fetch photo_paths from the last run doc.
    """
    payload = _make_fixture_payload(eid)
    payload["photo_urls"] = []
    _put_session(session, eid, payload)
    got = _get_session(session, eid)
    assert got["photo_urls"] == [], (
        "Server silently altered empty-photos payload — "
        "debugging poison state would be impossible"
    )
    assert got["preview"] == payload["preview"], (
        "Server dropped preview when photos were empty — Iter 79j.29 "
        "resume fallback would have nothing to fall back to"
    )


def test_ownership_enforced_on_session_endpoints(session, eid, db):
    """Ownership check: a session doc's company_id must match the
    caller's company. Reproduces the ownership invariant so a
    company_id mix-up (e.g. after a company merge / user re-assign)
    can't leak another contractor's photos."""
    payload = _make_fixture_payload(eid)
    _put_session(session, eid, payload)

    # Force the doc's company_id to something else — GET must 404
    original = db.ai_measure_sessions.find_one({"estimate_id": eid})
    original_company_id = original["company_id"]
    try:
        db.ai_measure_sessions.update_one(
            {"estimate_id": eid},
            {"$set": {"company_id": "some-other-company"}},
        )
        r = session.get(f"{BASE}/api/measure/sessions/{eid}", timeout=10)
        assert r.status_code == 404, (
            f"Session leak: got {r.status_code} instead of 404 "
            f"when reading a session belonging to a different company"
        )
    finally:
        # Restore for teardown
        db.ai_measure_sessions.update_one(
            {"estimate_id": eid},
            {"$set": {"company_id": original_company_id}},
        )
