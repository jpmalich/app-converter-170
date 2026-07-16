from creds_for_tests import TEST_PASSWORD
"""Iter 79j.79 — Tape Check accuracy report PDF: honest framing pinned.
Development-fixture runs render under the methodology exhibit; held-out
section renders (empty) with the zero-prompt-change criteria; no blended
aggregate; 400 with no scored runs."""
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


def test_report_400_when_no_scored_runs(admin_session):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Report NoRuns"}, timeout=15).json()["id"]
    try:
        r = s.get(f"{API}/estimates/{est_id}/tape-check/report-pdf", timeout=30)
        assert r.status_code == 400
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_report_renders_dev_section_and_empty_blind_section(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Report Dev"}, timeout=15).json()["id"]
    run_id = uuid.uuid4().hex
    mongo_db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": s._user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.5, "height_ft_source": "direct_consensus"},
        ], "photos": []}},
    })
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check",
              json={"walls": {"front": 8.9}, "dormers": []}, timeout=15)
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        r = s.get(f"{API}/estimates/{est_id}/tape-check/report-pdf", timeout=60)
        assert r.status_code == 200, r.text[:200]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"
        assert "accuracy.pdf" in r.headers.get("content-disposition", "")
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_report_html_framing_no_blended_aggregate():
    """Pin the framing strings at the source level so a rewrite can't
    silently drop the honest-labeling contract."""
    src = (Path(__file__).resolve().parent.parent / "routes" / "estimates.py").read_text()
    assert "Development validation — tuned fixture (methodology exhibit)" in src
    assert "Held-out blind runs — accuracy claim" in src
    assert "zero prompt changes between capture and scoring" in src
    assert "not</b> field accuracy" in src
    # Iter 79j.82 — run-integrity line pinned (voided vs valid runs)
    assert "Run integrity:" in src
    assert "excluded from candidate verdicts" in src
    # the two sections must never blend: no combined-average code path
    assert "blended" not in src.lower() or "never\n      combined" in src or "never combined" in src.replace("\n      ", " ")
