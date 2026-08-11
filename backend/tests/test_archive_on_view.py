"""ARCHIVE-ON-VIEW + PROTECTED AUTO-ARCHIVE + DEAD-WORKER SWEEP + EXPIRY
ON THE CARD (ruled 2026-08-11, TTL incident #3).

"Runs you acted on survive, runs you are evaluating die" is the
anti-pattern that reaped the EST-886440 grading chain. Pins:
  1. Viewing a terminal run (status endpoint) archives it — blueprint,
     measure AND hover (the 24h shortest fuse).
  2. A RUNNING run is NOT archived on view (still being written).
  3. Responses print the exact reap time; archived runs print None.
  4. A run on a PROTECTED estimate archives at completion-hook time.
  5. The blueprint dead-worker boot sweep flips a corpse to a class-5
     error AND archives it (the crash evidence must outlive the TTL).
  6. The card JSX prints the reap time / archived chip (EN+ES).
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from creds_for_tests import TEST_PASSWORD  # noqa: E402
from api_base import BASE_URL  # noqa: E402

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    s._user_id = s.get(f"{API}/auth/me", timeout=10).json()["id"]
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def _seed_run(mongo_db, coll, user_id, *, status="done", estimate_id=None):
    rid = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    mongo_db[coll].insert_one({
        "run_id": rid, "user_id": user_id, "estimate_id": estimate_id,
        "status": status, "stage": status,
        "result": {"raw_ai": {}, "measurements": {}} if status == "done" else None,
        "error": None, "test_artifact": True,
        "created_at": now, "updated_at": now,
        "completed_at": now if status == "done" else None,
    })
    return rid


def _cleanup(mongo_db, coll, rid):
    mongo_db[coll].delete_one({"run_id": rid})
    mongo_db.fixture_runs.delete_one({"run_id": rid})


def test_pin1_blueprint_status_view_archives(admin_session, mongo_db):
    rid = _seed_run(mongo_db, "ai_blueprint_runs", admin_session._user_id)
    try:
        r = admin_session.get(f"{API}/measure/ai-blueprint/status/{rid}", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["archived"] is True
        assert body["reaped_at"] is None  # archived runs never print a reap time
        arch = mongo_db.fixture_runs.find_one({"run_id": rid})
        assert arch is not None, "human view must archive — TTL incident #3"
        assert "view:blueprint-status" in (arch.get("artifact_reasons") or [])
        assert arch.get("substrate") == "ai_blueprint_runs"
    finally:
        _cleanup(mongo_db, "ai_blueprint_runs", rid)


def test_pin1b_measure_status_view_archives(admin_session, mongo_db):
    rid = _seed_run(mongo_db, "ai_measure_runs", admin_session._user_id)
    try:
        r = admin_session.get(f"{API}/measure/ai-measure/status/{rid}", timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["archived"] is True
        arch = mongo_db.fixture_runs.find_one({"run_id": rid})
        assert arch is not None
        assert "view:measure-status" in (arch.get("artifact_reasons") or [])
    finally:
        _cleanup(mongo_db, "ai_measure_runs", rid)


def test_pin1c_hover_status_view_archives(admin_session, mongo_db):
    """hover carries the SHORTEST fuse in the DB (24h, audit A3) — the
    same anti-pattern that ate the grading chain dies here too."""
    rid = _seed_run(mongo_db, "hover_import_runs", admin_session._user_id)
    try:
        r = admin_session.get(f"{API}/estimates/hover-import/status/{rid}", timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["archived"] is True
        arch = mongo_db.fixture_runs.find_one({"run_id": rid})
        assert arch is not None
        assert "view:hover-status" in (arch.get("artifact_reasons") or [])
    finally:
        _cleanup(mongo_db, "hover_import_runs", rid)


def test_pin2_running_run_not_archived_and_prints_reap_time(admin_session, mongo_db):
    rid = _seed_run(mongo_db, "ai_blueprint_runs", admin_session._user_id,
                    status="running")
    try:
        r = admin_session.get(f"{API}/measure/ai-blueprint/status/{rid}", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["archived"] is False
        assert mongo_db.fixture_runs.find_one({"run_id": rid}) is None, (
            "a running doc is still being written — its terminal poll archives it")
        # Exact reap time printed: created_at + 30 days
        assert body["reaped_at"] is not None
        reap = datetime.fromisoformat(body["reaped_at"])
        created = mongo_db.ai_blueprint_runs.find_one({"run_id": rid})["created_at"]
        expected = created.replace(tzinfo=timezone.utc) + timedelta(days=30)
        assert abs((reap - expected).total_seconds()) < 2
    finally:
        _cleanup(mongo_db, "ai_blueprint_runs", rid)


def test_pin3_error_run_view_archives(admin_session, mongo_db):
    """A failed run is worth more than a successful one — error runs
    archive on view too."""
    rid = _seed_run(mongo_db, "ai_measure_runs", admin_session._user_id,
                    status="error")
    mongo_db.ai_measure_runs.update_one(
        {"run_id": rid}, {"$set": {"error": "boom"}})
    try:
        r = admin_session.get(f"{API}/measure/ai-measure/status/{rid}", timeout=15)
        assert r.status_code == 200
        assert r.json()["archived"] is True
        assert mongo_db.fixture_runs.find_one({"run_id": rid}) is not None
    finally:
        _cleanup(mongo_db, "ai_measure_runs", rid)


def _run_with_fresh_db(coro_factory):
    """Drive backend coroutines with a fresh Motor client — the shared
    `db` client binds to the first asyncio.run loop and breaks on the
    second (established suite pattern)."""
    from motor.motor_asyncio import AsyncIOMotorClient

    async def go():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        fresh = client[os.environ["DB_NAME"]]
        import run_archive
        old = run_archive.db
        run_archive.db = fresh
        try:
            return await coro_factory(fresh)
        finally:
            run_archive.db = old
            client.close()
    return asyncio.run(go())


def test_pin4_protected_estimate_completion_archives(admin_session, mongo_db):
    eid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    mongo_db.estimates.insert_one({
        "id": eid, "customer_name": "TEST_protected_archive",
        "company_id": "test", "protected": True, "test_artifact": True,
        "created_at": now.isoformat(),
    })
    rid = _seed_run(mongo_db, "ai_measure_runs", admin_session._user_id,
                    estimate_id=eid)
    try:
        async def _go(fresh):
            from run_archive import maybe_archive_protected
            return await maybe_archive_protected(rid)
        archived_rid = _run_with_fresh_db(_go)
        assert archived_rid == rid
        arch = mongo_db.fixture_runs.find_one({"run_id": rid})
        assert arch is not None, "protection means unreapable, applied or not"
        assert "protected-estimate:completion" in (arch.get("artifact_reasons") or [])
        # Unprotected estimate → no-op
        mongo_db.estimates.update_one({"id": eid}, {"$set": {"protected": False}})
        rid2 = _seed_run(mongo_db, "ai_measure_runs", admin_session._user_id,
                         estimate_id=eid)
        try:
            async def _go2(fresh):
                from run_archive import maybe_archive_protected
                return await maybe_archive_protected(rid2)
            assert _run_with_fresh_db(_go2) is None
            assert mongo_db.fixture_runs.find_one({"run_id": rid2}) is None
        finally:
            _cleanup(mongo_db, "ai_measure_runs", rid2)
    finally:
        _cleanup(mongo_db, "ai_measure_runs", rid)
        mongo_db.estimates.delete_one({"id": eid})


def test_pin5_dead_worker_sweep_flips_and_archives(admin_session, mongo_db):
    rid = _seed_run(mongo_db, "ai_blueprint_runs", admin_session._user_id,
                    status="running")
    try:
        async def _go(fresh):
            import routes.ai_blueprint as bp
            old = bp.db
            bp.db = fresh
            try:
                return await bp.sweep_orphaned_blueprint_runs()
            finally:
                bp.db = old
        out = _run_with_fresh_db(_go)
        assert out["archived_dead"] >= 1
        doc = mongo_db.ai_blueprint_runs.find_one({"run_id": rid})
        assert doc["status"] == "error"
        assert doc["error_kind"] == "dead_worker_boot_sweep"
        arch = mongo_db.fixture_runs.find_one({"run_id": rid})
        assert arch is not None, (
            "the sweep must ARCHIVE the corpse — the crash evidence must "
            "outlive the TTL (compound failure B1)")
        assert arch["status"] == "error", "archived copy carries the crash state"
        assert "dead-worker:boot-sweep" in (arch.get("artifact_reasons") or [])
    finally:
        _cleanup(mongo_db, "ai_blueprint_runs", rid)


JSX = Path("/app/frontend/src/components/estimate/BlueprintReadBackCard.jsx").read_text()
DICTS = Path("/app/frontend/src/lib/dictionaries.js").read_text()


def test_pin6_expiry_on_the_card():
    assert 'data-testid="bp-rb-run-reap"' in JSX
    assert 'data-testid="bp-rb-run-archived"' in JSX
    assert "run?.reaped_at" in JSX and "run?.archived" in JSX
    # EN + ES card text — the boundary is stated, both languages
    assert '"bp.rb.reap": "reaped at {when} unless applied/archived"' in DICTS
    assert '"bp.rb.archived": "archived — never reaped"' in DICTS
    assert '"bp.rb.reap": "se purga el {when} salvo que se aplique/archive"' in DICTS
    assert '"bp.rb.archived": "archivada — nunca se purga"' in DICTS
