"""Iter 79j.81 — Candidate 1b: count-first-with-enumeration-evidence.
Pins the prompt contract + the per-wall signed course-delta metric."""
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
    PER_PHOTO_EXTRACT_PROMPT, RECONCILE_PROMPT, _build_phase_a_prompt,
)

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = "Admin123!"


def test_phase_a_count_first_contract():
    p = PER_PHOTO_EXTRACT_PROMPT
    assert "COUNT FIRST, HEIGHT SECOND" in p
    assert "count_enumeration_evidence" in p
    assert "Estimated or derived counts are NOT" in p
    assert "NEVER back-derive a count from a pixel height" in p


def test_phase_a_explicit_boundaries():
    p = PER_PHOTO_EXTRACT_PROMPT
    assert "the one on the starter" in p and "top of the block line" in p
    assert "meeting the\n   frieze/soffit line" in p or "meeting the frieze/soffit line" in p.replace("\n   ", " ")


def test_phase_a_partial_top_and_dispute_flags():
    p = PER_PHOTO_EXTRACT_PROMPT
    assert '"partial_top_course"' in p
    assert '"count_disputed_by_pixel"' in p
    assert "DISPUTE an enumerated count but may never AUTHOR one" in p
    assert "flag the conflict, do not harmonize it" in p


def test_exposure_injection_count_first():
    p = _build_phase_a_prompt(
        photo_idx=0, address=None, reference_dim=None,
        brick_course_in=None, siding_exposure_in=4.25, annotation_hint="",
    )
    assert "COUNT FIRST, HEIGHT SECOND" in p
    assert "never back-derive a count from a pixel height" in p
    assert "never AUTHOR one" in p


def test_phase_b_arithmetic_not_corroboration():
    p = RECONCILE_PROMPT
    assert "arithmetic, not corroboration" in p
    assert "Derived height NEVER" in p
    assert "independent cross-photo ENUMERATED counts" in p
    # per-wall count carried into the reconciled schema
    assert '"eave_courses_counted"' in p


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
        # back run has no count -> tape_courses recorded, no delta
        assert w["back"].get("course_delta") is None
        assert w["back"]["tape_courses"] == 28
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
