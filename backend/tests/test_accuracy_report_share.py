"""Accuracy Report share link — /m/ doctrine reused for /r/: frozen
verbatim HTML (honest-framing pins carry), tokenized + expiring, public
read-only, newer-runs banner flag, revocable. 400 with no scored runs."""
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
ADMIN_PASSWORD = "Admin123!"


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


@pytest.fixture()
def scored_estimate(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Share Accuracy"}, timeout=15).json()["id"]
    run_id = uuid.uuid4().hex
    mongo_db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": s._user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.5, "height_ft_source": "direct_consensus"},
        ], "photos": []}},
    })
    s.put(f"{API}/estimates/{est_id}/tape-check",
          json={"walls": {"front": 8.9}, "dormers": []}, timeout=15)
    r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
    assert r.status_code == 200, r.text
    yield est_id, run_id
    mongo_db.ai_measure_runs.delete_many({"estimate_id": est_id})
    mongo_db.accuracy_report_snapshots.delete_many({"estimate_id": est_id})
    s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_freeze_400_when_no_scored_runs(admin_session):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Share NoRuns"}, timeout=15).json()["id"]
    try:
        assert s.post(f"{API}/estimates/{est_id}/accuracy-report/freeze", timeout=30).status_code == 400
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_freeze_and_public_view_carry_framing_verbatim(admin_session, scored_estimate):
    s = admin_session
    est_id, _ = scored_estimate
    r = s.post(f"{API}/estimates/{est_id}/accuracy-report/freeze", timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    token = body["token"]
    assert body["share_path"] == f"/r/{token}"

    pub = requests.get(f"{API}/public/accuracy-report/{token}", timeout=30)
    assert pub.status_code == 200, pub.text
    data = pub.json()
    html = data["html"]
    # honest-framing pins carry VERBATIM to the shared view
    assert "Development validation — tuned fixture (methodology exhibit)" in html
    assert "Held-out blind runs — accuracy claim" in html
    assert "zero prompt changes between capture and scoring" in html
    assert "Run integrity:" in html
    assert "never\n      combined" in html or "never combined" in html.replace("\n      ", " ")
    assert data["newer_available"] is False
    assert data["meta"]["customer_name"] == "Share Accuracy"


def test_public_view_flags_newer_runs_never_silent_swap(admin_session, mongo_db, scored_estimate):
    s = admin_session
    est_id, _ = scored_estimate
    token = s.post(f"{API}/estimates/{est_id}/accuracy-report/freeze", timeout=60).json()["token"]

    run_id = uuid.uuid4().hex
    mongo_db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": s._user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.1, "height_ft_source": "direct_consensus"},
        ], "photos": []}},
    })
    assert s.post(f"{API}/estimates/{est_id}/tape-check/score",
                  json={"run_id": run_id}, timeout=15).status_code == 200

    pub = requests.get(f"{API}/public/accuracy-report/{token}", timeout=30).json()
    assert pub["newer_available"] is True
    # frozen html untouched — the second run must NOT be in the shared doc
    assert run_id[:8] not in pub["html"]


def test_revoke_kills_link(admin_session, scored_estimate):
    s = admin_session
    est_id, _ = scored_estimate
    token = s.post(f"{API}/estimates/{est_id}/accuracy-report/freeze", timeout=60).json()["token"]
    assert s.post(f"{API}/estimates/{est_id}/accuracy-report/revoke",
                  json={"token": token}, timeout=15).status_code == 200
    assert requests.get(f"{API}/public/accuracy-report/{token}", timeout=15).status_code == 404


def test_bogus_token_404():
    assert requests.get(f"{API}/public/accuracy-report/nope", timeout=15).status_code == 404
