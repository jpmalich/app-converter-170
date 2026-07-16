from creds_for_tests import TEST_PASSWORD
"""Delete guard + soft-delete retention pins (Iter 112, ruled after the
accidental EST-191890 / EST-657226 deletions).

  • preflight names linkages (frozen runs / scored tape / live QR links)
  • deletes are SOFT — 30-day trash retention + restore (undo)
  • the frozen Letrick source run is archived beyond the runs TTL
"""
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


def test_preflight_unlinked_estimate(admin_session, mongo_db):
    s = admin_session
    eid = s.post(f"{API}/estimates", json={"customer_name": "Guard Plain"}, timeout=15).json()["id"]
    try:
        pre = s.get(f"{API}/estimates/{eid}/delete-preflight", timeout=15).json()
        assert pre["linked"] is False and pre["warnings"] == []
        assert pre["retention_days"] == 30
    finally:
        s.delete(f"{API}/estimates/{eid}", timeout=15)
        mongo_db.estimates_trash.delete_one({"id": eid})


def test_preflight_names_linkages(admin_session, mongo_db):
    s = admin_session
    eid = s.post(f"{API}/estimates", json={"customer_name": "Guard Linked"}, timeout=15).json()["id"]
    run_id = "test-guard-" + uuid.uuid4().hex[:10]
    mongo_db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": s._user_id, "estimate_id": eid,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.5, "height_ft_source": "direct_consensus"},
        ], "photos": []}},
    })
    try:
        s.put(f"{API}/estimates/{eid}/tape-check",
              json={"walls": {"front": 8.9}, "dormers": []}, timeout=15)
        assert s.post(f"{API}/estimates/{eid}/tape-check/score",
                      json={"run_id": run_id}, timeout=15).status_code == 200
        assert s.post(f"{API}/estimates/{eid}/accuracy-report/freeze", timeout=60).status_code == 200
        pre = s.get(f"{API}/estimates/{eid}/delete-preflight", timeout=15).json()
        assert pre["linked"] is True
        joined = " ".join(pre["warnings"]).lower()
        assert "frozen ai measure run" in joined
        assert "scored tape-check" in joined
        assert "share/qr link" in joined
    finally:
        mongo_db.ai_measure_runs.delete_many({"estimate_id": eid})
        mongo_db.accuracy_report_snapshots.delete_many({"estimate_id": eid})
        s.delete(f"{API}/estimates/{eid}", timeout=15)
        mongo_db.estimates_trash.delete_one({"id": eid})


def test_preflight_flags_demo_fixture(admin_session, mongo_db):
    demo = mongo_db.estimates.find_one({"demo_key": "letrick_demo"}, {"id": 1})
    if not demo:
        pytest.skip("demo not staged")
    pre = admin_session.get(
        f"{API}/estimates/{demo['id']}/delete-preflight", timeout=15).json()
    assert pre["linked"] is True
    assert any("demo fixture" in w for w in pre["warnings"])


def test_soft_delete_trash_and_restore(admin_session, mongo_db):
    s = admin_session
    eid = s.post(f"{API}/estimates", json={"customer_name": "Guard Undo"}, timeout=15).json()["id"]
    r = s.delete(f"{API}/estimates/{eid}", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["soft_deleted"] is True and body["retention_days"] == 30
    assert mongo_db.estimates.find_one({"id": eid}) is None
    trashed = mongo_db.estimates_trash.find_one({"id": eid})
    assert trashed and trashed.get("deleted_at") is not None
    # restore (the Undo path)
    assert s.post(f"{API}/estimates/trash/{eid}/restore", timeout=15).status_code == 200
    restored = mongo_db.estimates.find_one({"id": eid})
    assert restored and "deleted_at" not in restored
    assert mongo_db.estimates_trash.find_one({"id": eid}) is None
    # second restore → 404 (window language pinned)
    r2 = s.post(f"{API}/estimates/trash/{eid}/restore", timeout=15)
    assert r2.status_code == 404
    assert "retention window" in r2.json()["detail"]
    s.delete(f"{API}/estimates/{eid}", timeout=15)
    mongo_db.estimates_trash.delete_one({"id": eid})


def test_trash_has_30_day_ttl_index(mongo_db):
    info = mongo_db.estimates_trash.index_information()
    ttl = [v for v in info.values()
           if v.get("key") == [("deleted_at", 1)] and "expireAfterSeconds" in v]
    assert ttl and ttl[0]["expireAfterSeconds"] == 30 * 24 * 60 * 60


def test_letrick_source_run_archived_beyond_ttl(admin_session, mongo_db):
    """The demo's frozen source run must survive the ai_measure_runs
    30-day TTL: reset archives it into fixture_runs (no TTL)."""
    assert admin_session.post(f"{API}/demo/reset", timeout=120).status_code == 200
    arch = mongo_db.fixture_runs.find_one(
        {"run_id": "4a009e93eb5348c08cc26bfb935675ce"})
    assert arch is not None
    assert not any("expireAfterSeconds" in v
                   for v in mongo_db.fixture_runs.index_information().values())
