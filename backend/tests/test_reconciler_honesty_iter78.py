from creds_for_tests import TEST_PASSWORD
"""Iter 79j.78 — reconciler honesty: imputed wall heights
(`height_ft_source: estimated_no_direct_view`) are EXCLUDED from Tape
Check scoring and surfaced as `imputed: true`, never as a pass."""
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
    me = s.get(f"{API}/auth/me", timeout=10)
    s._user_id = me.json()["id"]
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def _seed_run(db, est_id, user_id, walls):
    run_id = uuid.uuid4().hex
    db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": walls, "photos": []}},
    })
    return run_id


def test_imputed_wall_excluded_from_scoring(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Honesty Test"}, timeout=15).json()["id"]
    run_id = _seed_run(mongo_db, est_id, s._user_id, [
        {"label": "front", "height_ft": 9.6, "height_ft_source": "direct_disagreement"},
        {"label": "back", "height_ft": 9.6, "height_ft_source": "estimated_no_direct_view"},
    ])
    try:
        r = s.put(f"{API}/estimates/{est_id}/tape-check",
                  json={"walls": {"front": 8.9, "back": 9.9}, "dormers": []}, timeout=15)
        assert r.status_code == 200, r.text
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        e = r.json()["entry"]
        back = e["walls"]["back"]
        assert back["imputed"] is True
        assert back["verdict"] is None and back["delta"] is None
        assert back["ai"] == 9.6 and back["tape"] == 9.9
        # back contributes NOTHING to counts or accuracy
        assert e["passes"] + e["ambers"] + e["fails"] == 1
        front = e["walls"]["front"]
        assert front["verdict"] == "amber" and front.get("imputed") is None
        # accuracy derives from front only: 1 - 0.7/8.9
        assert abs(e["accuracy_pct"] - round(100 * (1 - 0.7 / 8.9), 1)) < 0.15
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_all_walls_imputed_rejects_scoring(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Honesty Test 2"}, timeout=15).json()["id"]
    run_id = _seed_run(mongo_db, est_id, s._user_id, [
        {"label": "front", "height_ft": 9.6, "height_ft_source": "estimated_no_direct_view"},
    ])
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check",
              json={"walls": {"front": 8.9}, "dormers": []}, timeout=15)
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 400
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_explicit_height_imputed_flag_also_excluded(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Honesty Test 3"}, timeout=15).json()["id"]
    run_id = _seed_run(mongo_db, est_id, s._user_id, [
        {"label": "front", "height_ft": 9.0, "height_ft_source": "direct_consensus"},
        {"label": "left", "height_ft": 10.0, "height_imputed": True},
    ])
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check",
              json={"walls": {"front": 9.0, "left": 9.0}, "dormers": []}, timeout=15)
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        e = r.json()["entry"]
        assert e["walls"]["left"]["imputed"] is True
        assert e["walls"]["front"]["verdict"] == "pass"
        assert e["accuracy_pct"] == 100.0
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
