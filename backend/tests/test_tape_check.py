"""Iter 79j.65 — Tape Check endpoints: persistent per-wall ground truth
+ accuracy history scored against AI Measure runs.

HTTP integration tests against the real API with a seeded estimate +
run doc, mirroring the test_stale_worker_detector.py pattern.
Verdict thresholds: |Δ| ≤ 0.5 pass · ≤ 1.0 amber · > 1.0 fail.
"""
from __future__ import annotations
from creds_for_tests import TEST_PASSWORD

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path("/app/backend/.env"))
load_dotenv(Path("/app/frontend/.env"), override=False)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

EMAIL = "hhunt6677@yahoo.com"
PASSWORD = TEST_PASSWORD


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def fixture_ids(session):
    """Seed a throwaway estimate + a done ai_measure run with known walls."""
    est_id = f"tape-test-{uuid.uuid4().hex[:8]}"
    user = MONGO.users.find_one({"email": EMAIL})
    company_id = user["company_id"]
    MONGO.estimates.insert_one({
        "id": est_id, "company_id": company_id, "kind": "siding",
        "estimate_number": "EST-TAPETEST", "lines": [],
        "created_at": datetime.now(timezone.utc),
    })
    run_id = uuid.uuid4().hex
    MONGO.ai_measure_runs.insert_one({"test_artifact": True, 
        "run_id": run_id, "estimate_id": est_id, "user_id": user["id"],
        "status": "done", "model_name": "claude-test",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "result": {"raw_ai": {
            "walls": [
                {"label": "front", "height_ft": 9.0, "height_ft_source": "direct_consensus",
                 "_source_photo_indices": [0]},
                {"label": "back", "height_ft": 9.3, "height_ft_source": "direct_consensus",
                 "_source_photo_indices": [4]},
                {"label": "left", "height_ft": 9.0, "height_ft_source": "direct_consensus",
                 "_source_photo_indices": [2]},
                {"label": "right", "height_ft": 8.5, "height_ft_source": "direct_single_reading",
                 "height_scale_flag": "cross_plane", "_source_photo_indices": [6]},
            ],
            "dormers": [
                {"face": "left", "width_ft": 15.5},
                {"face": "right", "width_ft": 16.5},
            ],
            # Iter 79j.68 — photo traces drive per-wall measurement mode:
            # photo 2 carries a course count → LEFT is count-derived;
            # photos 0/4 have no count → FRONT/BACK pixel-derived;
            # RIGHT carries height_scale_flag → cross-plane.
            "photos": [
                {"index": 0, "eave_height_ft_observed": 9.0, "eave_courses_counted": None},
                {"index": 2, "eave_height_ft_observed": 9.0, "eave_courses_counted": 29},
                {"index": 4, "eave_height_ft_observed": 9.3, "eave_courses_counted": None},
                {"index": 6, "eave_height_ft_observed": 8.5, "eave_courses_counted": None},
            ],
        }},
    })
    yield {"est_id": est_id, "run_id": run_id}
    MONGO.estimates.delete_one({"id": est_id})
    MONGO.ai_measure_runs.delete_one({"run_id": run_id})


def test_get_empty(session, fixture_ids):
    r = session.get(f"{BASE}/estimates/{fixture_ids['est_id']}/tape-check", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["walls"] == {} and d["history"] == []


def test_score_without_tape_400(session, fixture_ids):
    r = session.post(f"{BASE}/estimates/{fixture_ids['est_id']}/tape-check/score", json={}, timeout=15)
    assert r.status_code == 400
    assert "tape" in r.json()["detail"].lower()


def test_put_validates_range(session, fixture_ids):
    r = session.put(f"{BASE}/estimates/{fixture_ids['est_id']}/tape-check",
                    json={"walls": {"left": 999}}, timeout=15)
    assert r.status_code == 400


def test_put_and_score_red_house_truth(session, fixture_ids):
    """Red-house tape truth against Run 3-shaped walls: left −1.31 fail,
    right +1.31 fail, dormers +0.5 pass / +1.5 fail, accuracy ≈ 88.9%."""
    est = fixture_ids["est_id"]
    r = session.put(f"{BASE}/estimates/{est}/tape-check", json={
        "walls": {"left": 10.3125, "right": 7.1875},
        "dormers": [{"face": "left", "width_ft": 15.0}, {"face": "right", "width_ft": 15.0}],
    }, timeout=15)
    assert r.status_code == 200

    r = session.post(f"{BASE}/estimates/{est}/tape-check/score",
                     json={"run_id": fixture_ids["run_id"]}, timeout=15)
    assert r.status_code == 200, r.text
    e = r.json()["entry"]
    assert e["walls"]["left"] == {
        "ai": 9.0, "tape": 10.3125, "delta": -1.31,
        "verdict": "fail", "source": "direct_consensus", "mode": "count",
    }
    assert e["walls"]["right"]["delta"] == 1.31
    assert e["walls"]["right"]["verdict"] == "fail"
    # Iter 79j.68 — per-wall measurement mode from the run trace.
    assert e["walls"]["right"]["mode"] == "cross-plane"
    # front/back have no tape → not scored
    assert "front" not in e["walls"] and "back" not in e["walls"]
    dorm = {d["face"]: d for d in e["dormers"]}
    assert dorm["left"]["verdict"] == "pass" and dorm["left"]["delta"] == 0.5
    assert dorm["right"]["verdict"] == "fail" and dorm["right"]["delta"] == 1.5
    assert e["accuracy_pct"] == 88.9
    assert (e["passes"], e["ambers"], e["fails"]) == (1, 0, 3)


def test_rescore_replaces_not_duplicates(session, fixture_ids):
    est = fixture_ids["est_id"]
    r = session.post(f"{BASE}/estimates/{est}/tape-check/score",
                     json={"run_id": fixture_ids["run_id"]}, timeout=15)
    assert r.status_code == 200
    r = session.get(f"{BASE}/estimates/{est}/tape-check", timeout=15)
    hist = r.json()["history"]
    assert len(hist) == 1, "re-scoring the same run must replace, not append"


def test_amber_band(session, fixture_ids):
    """Δ of exactly 0.8 lands amber (0.5 < |Δ| ≤ 1.0)."""
    est = fixture_ids["est_id"]
    session.put(f"{BASE}/estimates/{est}/tape-check", json={
        "walls": {"back": 8.5},  # AI back = 9.3 → Δ +0.8
    }, timeout=15)
    r = session.post(f"{BASE}/estimates/{est}/tape-check/score",
                     json={"run_id": fixture_ids["run_id"]}, timeout=15)
    e = r.json()["entry"]
    assert e["walls"]["back"]["verdict"] == "amber"
    assert e["walls"]["back"]["mode"] == "pixel"


def test_legacy_run_without_trace_fields_scores_as_pixel(session, fixture_ids):
    """Runs scored before Iter 79j.67 have no photos/flags — mode must
    default to 'pixel', never crash."""
    user = MONGO.users.find_one({"email": EMAIL})
    run_id = uuid.uuid4().hex
    MONGO.ai_measure_runs.insert_one({"test_artifact": True, 
        "run_id": run_id, "estimate_id": fixture_ids["est_id"],
        "user_id": user["id"], "status": "done",
        "created_at": datetime.now(timezone.utc),
        "result": {"raw_ai": {"walls": [
            {"label": "back", "height_ft": 9.3},
        ]}},
    })
    try:
        r = session.post(f"{BASE}/estimates/{fixture_ids['est_id']}/tape-check/score",
                         json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["entry"]["walls"]["back"]["mode"] == "pixel"
    finally:
        MONGO.ai_measure_runs.delete_one({"run_id": run_id})


def test_tape_persists_across_score(session, fixture_ids):
    r = session.get(f"{BASE}/estimates/{fixture_ids['est_id']}/tape-check", timeout=15)
    assert r.json()["walls"]["back"] == 8.5


def test_cross_company_404():
    s = requests.Session()  # unauthenticated
    r = s.get(f"{BASE}/estimates/does-not-exist/tape-check", timeout=15)
    assert r.status_code in (401, 403)
