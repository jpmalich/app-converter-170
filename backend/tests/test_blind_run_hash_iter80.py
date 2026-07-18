from creds_for_tests import TEST_PASSWORD
"""Iter 79j.80 — blind-run provability: prompt hash locked at CAPTURE
(run creation), compared at scoring. held_out flag roundtrips."""
import hashlib
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


def test_hash_algorithm_pinned():
    from routes.ai_measure import (
        _prompt_version_hash, PER_PHOTO_EXTRACT_PROMPT, RECONCILE_PROMPT,
    )
    expect = hashlib.sha256(
        (PER_PHOTO_EXTRACT_PROMPT + RECONCILE_PROMPT).encode("utf-8")
    ).hexdigest()[:16]
    assert _prompt_version_hash() == expect
    assert len(_prompt_version_hash()) == 16


def test_held_out_roundtrips(admin_session):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Blind Flag"}, timeout=15).json()["id"]
    try:
        r = s.put(f"{API}/estimates/{est_id}/tape-check",
                  json={"walls": {"front": 9.0}, "dormers": [], "held_out": True}, timeout=15)
        assert r.status_code == 200 and r.json()["held_out"] is True
        assert s.get(f"{API}/estimates/{est_id}/tape-check", timeout=15).json()["held_out"] is True
        r = s.put(f"{API}/estimates/{est_id}/tape-check",
                  json={"walls": {"front": 9.0}, "dormers": []}, timeout=15)
        assert r.json()["held_out"] is False
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def _seed_and_score(s, mongo_db, prompt_hash):
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Blind Hash"}, timeout=15).json()["id"]
    run_id = uuid.uuid4().hex
    doc = {
        "run_id": run_id, "user_id": s._user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.0, "height_ft_source": "direct_consensus"},
        ], "photos": []}},
    }
    if prompt_hash is not None:
        doc["prompt_hash"] = prompt_hash
    doc["test_artifact"] = True
    mongo_db.ai_measure_runs.insert_one(doc)
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check",
              json={"walls": {"front": 9.0}, "dormers": []}, timeout=15)
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()["entry"]
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_score_marks_unchanged_when_hash_matches(admin_session, mongo_db):
    from routes.ai_measure import _prompt_version_hash
    e = _seed_and_score(admin_session, mongo_db, _prompt_version_hash())
    assert e["prompt_unchanged"] is True
    assert e["prompt_hash"] == _prompt_version_hash()


def test_score_marks_changed_when_hash_differs(admin_session, mongo_db):
    e = _seed_and_score(admin_session, mongo_db, "deadbeefdeadbeef")
    assert e["prompt_unchanged"] is False


def test_score_null_when_legacy_run_has_no_hash(admin_session, mongo_db):
    e = _seed_and_score(admin_session, mongo_db, None)
    assert e["prompt_unchanged"] is None
    assert e["prompt_hash"] is None
