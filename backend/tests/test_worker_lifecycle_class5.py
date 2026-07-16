from creds_for_tests import TEST_PASSWORD
"""Failure class 5 — WORKER LIFECYCLE pins (Iter 111, standing rule).

Live failure (EST-657226): a hot-reload killed the reconcile task after
8/8 photos finished Phase A. These pins lock the defenses:
  • watchdog threshold formula unchanged (max(60, 2×wave-budget))
  • auto-resume reconcile-only from persisted Phase A (capped at 1)
  • flip-to-error stamps failure_class 5 + honest recovery guidance
  • startup sweep recovers orphans without anyone polling
  • operator preflight endpoint (restart_safe)
  • anchor integrity: non-admin model choices clamp to the validated set
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))

import routes.ai_measure as am  # noqa: E402

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = TEST_PASSWORD

SRC = Path("/app/backend/routes/ai_measure.py").read_text()


def _fresh_run_doc(**over):
    doc = {
        "run_id": "test-c5-" + uuid.uuid4().hex[:12],
        "user_id": "test-user",
        "estimate_id": "test-est",
        "status": "running",
        "stage": "reconciling",
        "model_choice": "claude-fable-5",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "updated_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "phase_a_progress": {"done": 8, "total": 8, "per_wave_budget_s": 250},
        "raw_per_photo": [{"walls_visible": ["front"]}] * 8,
    }
    doc.update(over)
    return doc


def _run_scenario(monkeypatch, coro_factory):
    """Run an async scenario against a FRESH motor client bound to this
    test's event loop (module-level motor client can't hop loops)."""
    async def wrapper():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        monkeypatch.setattr(am, "db", client[os.environ["DB_NAME"]])
        try:
            return await coro_factory(client[os.environ["DB_NAME"]])
        finally:
            client.close()
    return asyncio.run(wrapper())


# ── watchdog threshold pin ───────────────────────────────────────────
def test_watchdog_threshold_formula_pinned():
    assert "stale_threshold_s = max(60, 2 * wave_budget_s)" in SRC


def test_class5_constants_pinned():
    assert am.FAILURE_CLASS_WORKER_LIFECYCLE == 5
    assert am._AUTO_RESUME_CAP == 1


# ── auto-resume from persisted Phase A ───────────────────────────────
def test_auto_resume_with_persisted_phase_a(monkeypatch):
    calls = []

    async def fake_worker(**kw):
        calls.append(kw)

    monkeypatch.setattr(am, "_execute_reconcile_only_worker", fake_worker)

    async def scenario(db):
        doc = _fresh_run_doc()
        await db.ai_measure_runs.insert_one(dict(doc))
        try:
            out = await am._handle_dead_worker(doc, idle_s=999, source="test")
            after = await db.ai_measure_runs.find_one({"run_id": doc["run_id"]})
            # let the dispatched fake worker task run
            await asyncio.sleep(0)
            return out, after
        finally:
            await db.ai_measure_runs.delete_one({"run_id": doc["run_id"]})

    out, after = _run_scenario(monkeypatch, scenario)
    assert out == "resumed"
    assert after["status"] == "running"
    assert after["stage"] == "reconciling"
    assert after["lifecycle_resume_attempts"] == 1
    assert after["failure_class"] == 5
    assert after["lifecycle_last_death"]["source"] == "test"
    assert len(calls) == 1
    assert len(calls[0]["extractions"]) == 8


def test_flip_to_class5_error_without_phase_a(monkeypatch):
    async def scenario(db):
        doc = _fresh_run_doc(raw_per_photo=[])
        await db.ai_measure_runs.insert_one(dict(doc))
        try:
            out = await am._handle_dead_worker(doc, idle_s=700, source="status_poll")
            return out, await db.ai_measure_runs.find_one({"run_id": doc["run_id"]})
        finally:
            await db.ai_measure_runs.delete_one({"run_id": doc["run_id"]})

    out, after = _run_scenario(monkeypatch, scenario)
    assert out == "failed"
    assert after["status"] == "error"
    assert after["error_kind"] == "WorkerDied"
    assert after["failure_class"] == 5
    assert "class 5" in after["error"]
    assert "Retry Run" in after["error"]


def test_auto_resume_capped_at_one(monkeypatch):
    async def scenario(db):
        doc = _fresh_run_doc(lifecycle_resume_attempts=1)
        await db.ai_measure_runs.insert_one(dict(doc))
        try:
            out = await am._handle_dead_worker(doc, idle_s=999, source="test")
            return out, await db.ai_measure_runs.find_one({"run_id": doc["run_id"]})
        finally:
            await db.ai_measure_runs.delete_one({"run_id": doc["run_id"]})

    out, after = _run_scenario(monkeypatch, scenario)
    assert out == "failed"
    assert after["status"] == "error"
    assert after["failure_class"] == 5
    # honest guidance: Phase A IS saved, manual reconcile retry is cheap
    assert "Retry reconciliation" in after["error"]


# ── startup sweep ────────────────────────────────────────────────────
def test_startup_sweep_recovers_orphans(monkeypatch):
    calls = []

    async def fake_worker(**kw):
        calls.append(kw)

    monkeypatch.setattr(am, "_execute_reconcile_only_worker", fake_worker)

    async def scenario(db):
        with_pa = _fresh_run_doc()
        without_pa = _fresh_run_doc(raw_per_photo=[])
        await db.ai_measure_runs.insert_many([dict(with_pa), dict(without_pa)])
        try:
            out = await am.sweep_orphaned_runs()
            await asyncio.sleep(0)
            a = await db.ai_measure_runs.find_one({"run_id": with_pa["run_id"]})
            b = await db.ai_measure_runs.find_one({"run_id": without_pa["run_id"]})
            return out, a, b
        finally:
            await db.ai_measure_runs.delete_many(
                {"run_id": {"$in": [with_pa["run_id"], without_pa["run_id"]]}})

    out, a, b = _run_scenario(monkeypatch, scenario)
    assert out["resumed"] >= 1 and out["failed"] >= 1
    assert a["status"] == "running" and a["lifecycle_resume_attempts"] == 1
    assert b["status"] == "error" and b["failure_class"] == 5
    assert "process start" in b["error"]


# ── operator preflight (standing rule) ───────────────────────────────
def test_in_flight_preflight_endpoint():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    client = MongoClient(os.environ["MONGO_URL"]) 
    db = client[os.environ["DB_NAME"]]
    doc = _fresh_run_doc(updated_at=datetime.now(timezone.utc))
    db.ai_measure_runs.insert_one(dict(doc))
    try:
        body = s.get(f"{API}/measure/ai-measure/in-flight", timeout=15).json()
        assert body["restart_safe"] is False
        assert any(x["run_id"] == doc["run_id"] for x in body["runs"])
    finally:
        db.ai_measure_runs.delete_one({"run_id": doc["run_id"]})
        client.close()
    body2 = s.get(f"{API}/measure/ai-measure/in-flight", timeout=15).json()
    assert all(x["run_id"] != doc["run_id"] for x in body2["runs"])


# ── anchor integrity: model clamp ────────────────────────────────────
def test_validated_default_and_clamp():
    assert am._DEFAULT_MODEL_KEY == "claude-fable-5"
    assert am._VALIDATED_MODEL_KEYS == frozenset({"claude-fable-5"})
    # non-admin choices clamp, recorded not silent
    key, clamped_from = am._clamp_model_choice("gpt-5.5", {"role": "estimator"})
    assert key == "claude-fable-5" and clamped_from == "gpt-5.5"
    key, clamped_from = am._clamp_model_choice("claude-fable-5", {"role": "estimator"})
    assert key == "claude-fable-5" and clamped_from is None
    # admins keep the full bake-off registry
    for role in ("owner", "supplier_admin", "admin"):
        key, clamped_from = am._clamp_model_choice("gpt-5.5", {"role": role})
        assert key == "gpt-5.5" and clamped_from is None
