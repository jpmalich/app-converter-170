from creds_for_tests import TEST_PASSWORD
"""Ruled 2026-07-14 — no persistent artifact may reference a reapable run.

Pins:
  • /m/ freeze archives the EXACT backing run into fixture_runs (no TTL)
  • /r/ freeze archives the estimate's backing run
  • quote-send trigger is wired (source pin — sending real email in tests
    is off-limits)
  • _load_run falls back to fixture_runs after the ai_measure_runs doc is
    reaped (November-callback path)
  • backfill archives runs referenced by sent quotes / live QR freezes
  • unreferenced runs stay under the 30-day TTL (no blanket archival)
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = TEST_PASSWORD
SOURCE_RUN_ID = "4a009e93eb5348c08cc26bfb935675ce"  # frozen Letrick archive


def _run_fresh(module, fn_name, *args, **kwargs):
    """Run an async helper on a FRESH loop + FRESH motor client — the
    process-global db client may be bound to another test module's closed
    loop (order-independence)."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    old_db = module.db
    module.db = client[os.environ["DB_NAME"]]
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(getattr(module, fn_name)(*args, **kwargs))
    finally:
        module.db = old_db
        loop.close()
        client.close()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    s._user_id = s.get(f"{API}/auth/me", timeout=10).json()["id"]
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def _clone_letrick_run(mongo_db, est_id, user_id):
    """A run realistic enough for full package assembly: clone the frozen
    Letrick archive's result onto a fresh run doc."""
    src = mongo_db.fixture_runs.find_one({"run_id": SOURCE_RUN_ID}, {"_id": 0})
    assert src, "frozen Letrick archive missing from fixture_runs"
    run_id = "test-archive-" + uuid.uuid4().hex[:10]
    mongo_db.ai_measure_runs.insert_one({
        **src, "run_id": run_id, "estimate_id": est_id, "user_id": user_id,
        "created_at": src.get("created_at"),
    })
    return run_id


def _cleanup(mongo_db, s, est_id, run_ids):
    s.delete(f"{API}/estimates/{est_id}", timeout=15)
    mongo_db.estimates_trash.delete_one({"id": est_id})
    mongo_db.ai_measure_runs.delete_many({"run_id": {"$in": run_ids}})
    mongo_db.fixture_runs.delete_many({"run_id": {"$in": run_ids}})
    mongo_db.lp_material_list_snapshots.delete_many({"estimate_id": est_id})
    mongo_db.accuracy_report_snapshots.delete_many({"estimate_id": est_id})


def test_m_freeze_archives_exact_run_and_survives_reaping(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Archive M"}, timeout=15).json()["id"]
    run_id = _clone_letrick_run(mongo_db, est_id, s._user_id)
    try:
        r = s.post(f"{API}/estimates/{est_id}/lp-material-list/freeze", json={}, timeout=30)
        assert r.status_code == 200, r.text
        arch = mongo_db.fixture_runs.find_one({"run_id": run_id})
        assert arch, "freeze did not archive the backing run"
        assert "m-freeze" in (arch.get("artifact_reasons") or [])
        # November-callback path: reap the live doc, panel still serves
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        r2 = s.post(f"{API}/estimates/{est_id}/lp-package/preview", json={}, timeout=30)
        assert r2.status_code == 200, f"fixture fallback failed: {r2.text[:200]}"
        assert r2.json().get("run_id") == run_id
    finally:
        _cleanup(mongo_db, s, est_id, [run_id])


def test_r_freeze_archives_backing_run(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Archive R"}, timeout=15).json()["id"]
    run_id = _clone_letrick_run(mongo_db, est_id, s._user_id)
    try:
        # accuracy report needs tape + a scored run (tape wall value = eave ft)
        rt = s.put(f"{API}/estimates/{est_id}/tape-check", json={"walls": {"front": 8.5, "back": 8.9}}, timeout=15)
        assert rt.status_code == 200, rt.text
        rs = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=30)
        assert rs.status_code == 200, rs.text
        r = s.post(f"{API}/estimates/{est_id}/accuracy-report/freeze", json={}, timeout=30)
        assert r.status_code == 200, r.text
        arch = mongo_db.fixture_runs.find_one({"run_id": run_id})
        assert arch, "r-freeze did not archive the backing run"
        assert "r-freeze" in (arch.get("artifact_reasons") or [])
    finally:
        _cleanup(mongo_db, s, est_id, [run_id])


def test_quote_send_trigger_wired_source_pin():
    src = (Path(__file__).resolve().parent.parent / "routes" / "email.py").read_text()
    send_idx = src.index("resend.Emails.send")
    ret_idx = src.index("return {", send_idx)
    assert "archive_run_for_artifact" in src[send_idx:ret_idx], (
        "quote-send must archive the backing run between send and return")


def test_backfill_archives_referenced_and_skips_unreferenced(admin_session, mongo_db):
    s = admin_session
    est_sent = s.post(f"{API}/estimates", json={"customer_name": "Backfill Sent"}, timeout=15).json()["id"]
    est_plain = s.post(f"{API}/estimates", json={"customer_name": "Backfill Plain"}, timeout=15).json()["id"]
    run_sent = _clone_letrick_run(mongo_db, est_sent, s._user_id)
    run_plain = _clone_letrick_run(mongo_db, est_plain, s._user_id)
    mongo_db.estimates.update_one({"id": est_sent}, {"$set": {"status_label": "sent"}})
    try:
        import run_archive
        archived = _run_fresh(run_archive, "backfill_artifact_referenced_runs")
        assert run_sent in archived
        assert mongo_db.fixture_runs.find_one({"run_id": run_sent})
        # unreferenced runs keep the 30-day TTL — never blanket-archived
        assert run_plain not in archived
        assert mongo_db.fixture_runs.find_one({"run_id": run_plain}) is None
    finally:
        _cleanup(mongo_db, s, est_sent, [run_sent])
        _cleanup(mongo_db, s, est_plain, [run_plain])


def test_archive_helper_idempotent(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Archive Idem"}, timeout=15).json()["id"]
    run_id = _clone_letrick_run(mongo_db, est_id, s._user_id)
    try:
        import run_archive
        for reason in ("quote-send", "quote-send", "m-freeze"):
            got = _run_fresh(run_archive, "archive_run_for_artifact",
                             estimate_id=est_id, run_id=run_id, reason=reason)
            assert got == run_id
        assert mongo_db.fixture_runs.count_documents({"run_id": run_id}) == 1
        arch = mongo_db.fixture_runs.find_one({"run_id": run_id})
        assert sorted(arch["artifact_reasons"]) == ["m-freeze", "quote-send"]
    finally:
        _cleanup(mongo_db, s, est_id, [run_id])
