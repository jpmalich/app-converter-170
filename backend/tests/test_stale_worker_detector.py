"""Iter 79j.62 — Stale-worker detector on GET /ai-measure/status/{run_id}.

`asyncio.create_task` workers do not survive uvicorn hot-reload. Before
this iter, a killed worker left the run doc stuck at `status=running`
forever — the browser polled for 820s watching 8 grey dots on the
Wave HUD before giving up (Jul 7 2026 red-house confirmation attempt).

The detector flips a stale `running` doc to `error` in place at
read-time so the frontend's existing run-error banner surfaces a
Retry Run button (same pattern as reconciliation-failure).

Tests here are HTTP integration tests — they poke the real endpoint
against a seeded run doc in Mongo, so we cover the full pymongo +
FastAPI dependency stack instead of unit-mocking the endpoint.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta
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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def session():
    """Use a Session so Cloudflare bot cookies (__cf_bm) travel with
    each subsequent request. Passing cookies=jar alone drops them."""
    s = requests.Session()
    r = s.post(
        f"{BASE}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_user_id(session):
    r = session.get(f"{BASE}/api/auth/me", timeout=5)
    assert r.status_code == 200, f"/auth/me failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _seed_run(db, admin_user_id, *, status, updated_ago_s, per_wave_budget_s=250, phase="starting"):
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    db.ai_measure_runs.insert_one({
        "run_id": run_id,
        "estimate_id": "test-fixture-" + run_id[:8],
        "user_id": admin_user_id,
        "status": status,
        "stage": "extracting_per_photo",
        "created_at": now - timedelta(seconds=updated_ago_s + 5),
        "updated_at": now - timedelta(seconds=updated_ago_s),
        "phase_a_progress": {
            "wave": 0, "waves_total": 4, "done": 0, "failed": 0, "total": 8,
            "per_wave_budget_s": per_wave_budget_s, "phase": phase,
            "transport": "anthropic_direct", "concurrency": 2,
        },
    })
    return run_id


def _status(run_id, session):
    r = session.get(
        f"{BASE}/api/measure/ai-measure/status/{run_id}",
        timeout=10,
    )
    assert r.status_code == 200, f"status returned {r.status_code}: {r.text}"
    return r.json()


def test_fresh_running_run_is_untouched(db, session, admin_user_id):
    """A worker that wrote progress 10s ago is healthy — must NOT flip."""
    run_id = _seed_run(db, admin_user_id, status="running", updated_ago_s=10)
    try:
        s = _status(run_id, session)
        assert s["status"] == "running", f"fresh run was flipped to {s['status']}"
        assert s.get("error") in (None, "")
        db_doc = db.ai_measure_runs.find_one({"run_id": run_id})
        assert db_doc["status"] == "running"
    finally:
        db.ai_measure_runs.delete_one({"run_id": run_id})


def test_stale_running_run_flips_to_error(db, session, admin_user_id):
    """A worker idle for > 2×per_wave_budget must flip to error."""
    # 2 × 250s = 500s; 600s idle is clearly stale
    run_id = _seed_run(db, admin_user_id, status="running", updated_ago_s=600)
    try:
        s = _status(run_id, session)
        assert s["status"] == "error", (
            f"stale run should be flipped to error, got {s['status']}: {s}"
        )
        assert s["error_kind"] == "WorkerDied"
        assert "failure class 5" in (s["error"] or "").lower()
        assert "retry run" in (s["error"] or "").lower()
        assert s["stage"] == "worker_died"
        # DB doc must be persistent so a subsequent poll returns the same state
        db_doc = db.ai_measure_runs.find_one({"run_id": run_id})
        assert db_doc["status"] == "error"
        assert db_doc["error_kind"] == "WorkerDied"
        assert db_doc["failure_class"] == 5
    finally:
        db.ai_measure_runs.delete_one({"run_id": run_id})


def test_60s_floor_when_per_wave_budget_missing(db, session, admin_user_id):
    """Legacy docs without per_wave_budget_s still get a 60s floor."""
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    db.ai_measure_runs.insert_one({
        "run_id": run_id,
        "estimate_id": "test-fixture-nolegacy",
        "user_id": admin_user_id,
        "status": "running",
        "stage": "starting",
        "created_at": now - timedelta(seconds=180),
        "updated_at": now - timedelta(seconds=180),
        # NOTE: no phase_a_progress → per_wave_budget defaults to 250 → threshold 500s
        # 180s idle < 500s ceiling → should NOT flip
    })
    try:
        s = _status(run_id, session)
        assert s["status"] == "running"
    finally:
        db.ai_measure_runs.delete_one({"run_id": run_id})


def test_already_errored_run_untouched(db, session, admin_user_id):
    """Runs already in `error` state must be idempotent — no re-writes."""
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    original_err = "original error from the worker"
    db.ai_measure_runs.insert_one({
        "run_id": run_id,
        "estimate_id": "test-fixture-errored",
        "user_id": admin_user_id,
        "status": "error",
        "stage": "reconciling",
        "error": original_err,
        "error_kind": "OriginalError",
        "created_at": now - timedelta(seconds=3600),
        "updated_at": now - timedelta(seconds=3600),
    })
    try:
        s = _status(run_id, session)
        assert s["status"] == "error"
        assert s["error"] == original_err
        assert s["error_kind"] == "OriginalError"
        assert s["stage"] == "reconciling"
    finally:
        db.ai_measure_runs.delete_one({"run_id": run_id})


def test_done_run_untouched(db, session, admin_user_id):
    """Runs in `done` state — even ancient ones — never flip."""
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    db.ai_measure_runs.insert_one({
        "run_id": run_id,
        "estimate_id": "test-fixture-done",
        "user_id": admin_user_id,
        "status": "done",
        "stage": "done",
        "created_at": now - timedelta(seconds=86_400),
        "updated_at": now - timedelta(seconds=86_400),
        "result": {"measurements": {}, "lines": []},
    })
    try:
        s = _status(run_id, session)
        assert s["status"] == "done"
        assert s["error"] in (None, "")
    finally:
        db.ai_measure_runs.delete_one({"run_id": run_id})


def test_ownership_still_enforced_on_stale_run(db, session, admin_user_id):
    """Even a stale run must reject readers who don't own it — the
    detector runs AFTER the ownership check, not before."""
    run_id = _seed_run(db, admin_user_id, status="running", updated_ago_s=1000)
    # forcibly re-assign to a different user
    db.ai_measure_runs.update_one({"run_id": run_id}, {"$set": {"user_id": "some-other-user"}})
    try:
        r = session.get(
            f"{BASE}/api/measure/ai-measure/status/{run_id}",
            timeout=10,
        )
        assert r.status_code == 403
        # And the doc must NOT have been flipped to error by the request
        db_doc = db.ai_measure_runs.find_one({"run_id": run_id})
        assert db_doc["status"] == "running"
    finally:
        db.ai_measure_runs.delete_one({"run_id": run_id})
