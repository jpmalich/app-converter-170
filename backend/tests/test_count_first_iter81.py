"""Iter 79j.82 — candidate 1b REVERTED per pre-registration FAIL.
Pins: (a) the reversion itself (prompt hash == the 1a-era capture hash,
1b markers absent), (b) the KEPT infrastructure — per-wall signed
course-delta scoring (fix deliverable, independent of prompts)."""
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    PER_PHOTO_EXTRACT_PROMPT, RECONCILE_PROMPT, _prompt_version_hash,
)

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = "Admin123!"

HASH_1A = "f23780909828f9a8"  # Howard-confirmed 1a-validated contract


def test_reversion_hash_matches_1a_era():
    assert _prompt_version_hash() == HASH_1A


def test_1b_markers_absent():
    for p in (PER_PHOTO_EXTRACT_PROMPT, RECONCILE_PROMPT):
        assert "COUNT FIRST, HEIGHT SECOND" not in p
        assert "count_enumeration_evidence" not in p
        assert "count_disputed_by_pixel" not in p
        assert "arithmetic, not corroboration" not in p


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


def test_score_emits_signed_course_delta(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Course Delta"}, timeout=15).json()["id"]
    run_id = uuid.uuid4().hex
    mongo_db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": s._user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.6, "height_ft_source": "direct_consensus", "eave_courses_counted": 27},
            {"label": "left", "height_ft": 9.2, "height_ft_source": "direct_consensus", "eave_courses_counted": 26},
            {"label": "back", "height_ft": 9.9, "height_ft_source": "direct_consensus"},
        ], "photos": []}},
    })
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check", json={"walls": {
            "front": {"segments": [{"height_ft": 8.96, "courses": 25}], "start_ref": "siding_start"},
            "left": {"segments": [{"height_ft": 8.96, "courses": 25}, {"height_ft": 9.92, "courses": 28}], "start_ref": "siding_start"},
            "back": {"segments": [{"height_ft": 9.92, "courses": 28}], "start_ref": "siding_start"},
        }, "dormers": []}, timeout=15)
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        w = r.json()["entry"]["walls"]
        assert w["front"]["course_delta"] == 2 and w["front"]["ai_courses"] == 27 and w["front"]["tape_courses"] == 25
        # left ai 9.2 → nearest segment by height is 8.96 (25c): 26 - 25 = +1
        assert w["left"]["course_delta"] == 1
        assert w["back"].get("course_delta") is None
        assert w["back"]["tape_courses"] == 28
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
