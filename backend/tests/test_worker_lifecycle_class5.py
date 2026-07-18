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
from creds_for_tests import TEST_PASSWORD

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
        await db.ai_measure_runs.insert_one(dict(doc, test_artifact=True))
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
        await db.ai_measure_runs.insert_one(dict(doc, test_artifact=True))
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
        await db.ai_measure_runs.insert_one(dict(doc, test_artifact=True))
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
    """ISOLATED-DB pin (2026-07-17 collateral-kill incident): this test
    runs the GLOBAL sweep — executed against the shared DB it flips any
    LIVE status='running' run to class-5 (it killed a real mid-retry
    reconcile once). It must run against a throwaway database."""
    calls = []

    async def fake_worker(**kw):
        calls.append(kw)

    monkeypatch.setattr(am, "_execute_reconcile_only_worker", fake_worker)

    async def wrapper():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        isolated = client[os.environ["DB_NAME"] + "_c5_sweep_test"]
        monkeypatch.setattr(am, "db", isolated)
        with_pa = _fresh_run_doc()
        without_pa = _fresh_run_doc(raw_per_photo=[])
        await isolated.ai_measure_runs.insert_many([dict(with_pa, test_artifact=True), dict(without_pa, test_artifact=True)])
        try:
            out = await am.sweep_orphaned_runs()
            await asyncio.sleep(0)
            a = await isolated.ai_measure_runs.find_one({"run_id": with_pa["run_id"]})
            b = await isolated.ai_measure_runs.find_one({"run_id": without_pa["run_id"]})
            return out, a, b
        finally:
            await client.drop_database(os.environ["DB_NAME"] + "_c5_sweep_test")
            client.close()

    out, a, b = asyncio.run(wrapper())
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
    db.ai_measure_runs.insert_one(dict(doc, test_artifact=True))
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


# ── class-5 pins (2026-07-17 vanished-run incident) ──────────────────
def test_in_flight_counts_awaiting_retry_runs():
    """A failed-reconcile run with persisted Phase A + a live retry path
    is IN-FLIGHT for restart purposes — preflight must surface it."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    doc = _fresh_run_doc(
        status="error", stage="worker_died", error_kind="WorkerDied",
        updated_at=datetime.now(timezone.utc))
    db.ai_measure_runs.insert_one(dict(doc, test_artifact=True))
    try:
        body = s.get(f"{API}/measure/ai-measure/in-flight", timeout=15).json()
        assert body["restart_safe"] is False
        mine = next(x for x in body["runs"] if x["run_id"] == doc["run_id"])
        assert mine["kind"] == "awaiting_retry"
    finally:
        db.ai_measure_runs.delete_one({"run_id": doc["run_id"]})
        client.close()


def test_in_flight_ignores_stale_error_runs():
    """Error runs older than 24 h don't flag restart_safe forever."""
    s = requests.Session()
    s.post(f"{API}/auth/login",
           json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    doc = _fresh_run_doc(
        status="error", stage="worker_died", error_kind="WorkerDied",
        updated_at=datetime.now(timezone.utc) - timedelta(hours=48))
    db.ai_measure_runs.insert_one(dict(doc, test_artifact=True))
    try:
        body = s.get(f"{API}/measure/ai-measure/in-flight", timeout=15).json()
        assert all(x["run_id"] != doc["run_id"] for x in body["runs"])
    finally:
        db.ai_measure_runs.delete_one({"run_id": doc["run_id"]})
        client.close()


def test_class5_resume_and_retry_use_phase_b_key_routing():
    assert 'api_key, _src = _pick_llm_api_key("anthropic", phase="B")' in SRC
    assert 'api_key, _source = _pick_llm_api_key("anthropic", phase="B")' in SRC


def test_proxy_llm_calls_are_nonblocking():
    """Iter 79j.95 freeze pin: LlmChat.send_message bottoms out in a SYNC
    litellm.completion() — every proxy call must route through the
    worker-thread wrapper so a proxy hang can never freeze the loop."""
    assert "def _send_message_nonblocking" in SRC
    # the ONLY chat.send_message reference left is inside the wrapper
    assert SRC.count("chat.send_message") == 1


def test_reconcile_only_hollow_result_never_passes_as_done(monkeypatch):
    """2026-07-17 pin: the proxy returned prose ('no JSON object found')
    and the reconcile-only worker marked the run DONE with 0 walls /
    0 sqft. A parse-broken reconcile must flip to error, Phase A intact."""
    async def fake_reconcile(**kw):
        return {"_parse_error": "no JSON object found", "_transport": "emergent_proxy"}
    monkeypatch.setattr(am, "_reconcile_extractions", fake_reconcile)

    async def scenario(db):
        doc = _fresh_run_doc()
        await db.ai_measure_runs.insert_one(dict(doc, test_artifact=True))
        try:
            await am._execute_reconcile_only_worker(
                run_id=doc["run_id"], api_key="k", user_id="test-user",
                extractions=doc["raw_per_photo"], model_provider="anthropic",
                model_name="claude-fable-5", address=None,
                reference_dim=None, annotation_hint="")
            return await db.ai_measure_runs.find_one({"run_id": doc["run_id"]})
        finally:
            await db.ai_measure_runs.delete_one({"run_id": doc["run_id"]})

    after = _run_scenario(monkeypatch, scenario)
    assert after["status"] == "error"
    assert after["error_kind"] == "ReconciliationRetryError"
    assert "honesty guard" in after["error"]
    assert after["raw_per_photo"], "Phase A must survive the flip"


def test_direct_phase_b_streams():
    """2026-07-17 pin: non-streaming messages.create + extended thinking
    sat SILENT past the 300s httpx read timeout (two APITimeoutError
    deaths on the 261 Haugh retry; the successful direct run took 327s).
    Direct Phase B must stream so bytes flow through the quiet phase."""
    assert "client.messages.stream(" in SRC
    assert "get_final_message" in SRC


# ── deterministic-timeout register #3 (ruled 2026-07-17) ─────────────
_EMPIRICAL_COMPLEX_RECONCILE_S = 327  # canonical b7a26956, 32k ceiling


def test_phase_b_single_ceiling_policy():
    """ONE ceiling constant, every reconcile path through it, sized above
    the empirically observed complex-house duration (327s at 32k output;
    the 48k ceiling runs longer). Variant 3 killed three re-runs at a
    360s ceiling mislabeled '180s'."""
    assert am.PHASE_B_CEILING_S >= 2 * _EMPIRICAL_COMPLEX_RECONCILE_S
    # the constant governs BOTH transports (direct outer wait_for via
    # total_timeout_s + emergency proxy call)
    assert "total_timeout_s = PHASE_B_CEILING_S" in SRC
    assert "timeout=PHASE_B_CEILING_S" in SRC
    # no resurrected read+60 formula, no stale mislabeled error text
    assert "read_timeout_s + 60" not in SRC
    assert "local 180s wait_for ceiling hit" not in SRC


def test_lf_panel_never_renders_zeros_for_pending():
    """2026-07-17 pin: a failed/incomplete reconcile must render the
    linear-measurements panel as EMPTY/pending — never editable 0 LF."""
    jsx = (Path(__file__).resolve().parents[2] / "frontend" / "src" /
           "components" / "estimate" / "AIMeasureButton.jsx").read_text()
    assert 'data-testid="ai-measure-lf-pending"' in jsx
    assert "_reconciliation_error" in jsx
    assert 'value={preview.measurements[key] ?? ""}' in jsx
    assert "Number(preview.measurements[key] || 0)" not in jsx


# ── status parity (ruled 2026-07-17) ─────────────────────────────────
def test_done_never_coexists_with_unresolved_reconcile_error():
    """ONE canonical awaiting-retry state. DB invariant: no run doc may
    be status=done while its stored result carries an unresolved
    _reconciliation_error / _parse_error (hollow-done). Guarded at both
    workers; existing docs migrated 2026-07-17."""
    client = MongoClient(os.environ["MONGO_URL"])
    try:
        db = client[os.environ["DB_NAME"]]
        offenders = list(db.ai_measure_runs.find(
            {"status": "done",
             "$or": [
                 {"result.raw_ai._reconciliation_error": {"$nin": [None, ""]}},
                 {"result.raw_ai._parse_error": {"$nin": [None, ""]}},
             ]},
            {"run_id": 1}))
        assert not offenders, f"hollow-done docs present: {[d['run_id'] for d in offenders]}"
    finally:
        client.close()


def test_status_parity_guard_in_both_workers():
    assert SRC.count('"error_kind": "ReconciliationRetryError"') >= 2
    assert "STATUS PARITY (ruled 2026-07-17)" in SRC


def test_client_retry_poll_budget_matches_ceiling():
    """Ceiling policy applies to EVERY consumer — the old 240s client
    poll expired before 327s+ reconciles finished."""
    jsx = (Path(__file__).resolve().parents[2] / "frontend" / "src" /
           "components" / "estimate" / "AIMeasureButton.jsx").read_text()
    assert "i < 320" in jsx and "i < 80;" not in jsx


# ── proxy retirement (ruled 2026-07-17) ──────────────────────────────
def test_proxy_emergency_default_off():
    assert am._PROXY_EMERGENCY is False
    assert 'os.environ.get("AI_MEASURE_PROXY_EMERGENCY", "0")' in SRC


def test_no_production_run_touches_litellm(monkeypatch):
    """RULED 2026-07-17: proxy fallback removed from production photo/
    blueprint paths. Direct errors surface honestly; the emergency
    switch is the ONLY road to litellm and stamps proxy_degraded."""
    async def fake_direct(**kw):
        return {"_reconciliation_error": "boom", "_transport": "anthropic_direct"}
    calls = {"proxy": 0}
    async def counting_proxy(**kw):
        calls["proxy"] += 1
        return {"walls": [], "_transport": "emergent_proxy"}
    monkeypatch.setattr(am, "_reconcile_extractions_direct", fake_direct)
    monkeypatch.setattr(am, "_reconcile_extractions_via_proxy", counting_proxy)
    monkeypatch.setattr(am, "_pick_llm_api_key", lambda p, phase=None: ("k", "anthropic_direct"))
    kw = dict(api_key="pk", user_id="t", model_provider="anthropic",
              model_name="claude-fable-5", extractions=[], address=None,
              reference_dim=None, annotation_hint="")

    monkeypatch.setattr(am, "_PROXY_EMERGENCY", False)
    out = asyncio.run(am._reconcile_extractions(**kw))
    assert out["_reconciliation_error"] == "boom"
    assert calls["proxy"] == 0, "production run touched litellm"

    monkeypatch.setattr(am, "_PROXY_EMERGENCY", True)
    out = asyncio.run(am._reconcile_extractions(**kw))
    assert calls["proxy"] == 1
    assert out["_transport"] == "proxy_degraded" and out["_proxy_degraded"] is True


def test_anthropic_without_direct_key_errors_instead_of_proxy(monkeypatch):
    calls = {"proxy": 0}
    async def counting_proxy(**kw):
        calls["proxy"] += 1
        return {}
    monkeypatch.setattr(am, "_reconcile_extractions_via_proxy", counting_proxy)
    monkeypatch.setattr(am, "_pick_llm_api_key", lambda p, phase=None: ("k", "emergent_proxy"))
    monkeypatch.setattr(am, "_PROXY_EMERGENCY", False)
    out = asyncio.run(am._reconcile_extractions(
        api_key="pk", user_id="t", model_provider="anthropic",
        model_name="claude-fable-5", extractions=[], address=None,
        reference_dim=None, annotation_hint=""))
    assert "RETIRED" in out["_reconciliation_error"]
    assert calls["proxy"] == 0


# ── shared-DB test isolation (pattern pin, ruled 2026-07-17) ─────────
_GLOBAL_MUTATORS = ("sweep_orphaned_runs",)


def test_global_mutators_only_run_against_isolated_dbs():
    """Pattern pin: any test invoking a GLOBAL DB mutator must run it
    against an isolated throwaway database (a pytest sweep once
    collateral-killed a live mid-retry run on the shared DB)."""
    import glob as _glob
    for path in _glob.glob(os.path.join(os.path.dirname(__file__), "test_*.py")):
        src = open(path).read()
        for fn in _GLOBAL_MUTATORS:
            if f".{fn}(" in src:
                assert "drop_database" in src, (
                    f"{os.path.basename(path)} calls global mutator {fn} "
                    "without an isolated throwaway DB")
