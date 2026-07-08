"""Iter 79j.67 — (a) Re-run calibration carryover + (b)/(c) prompt candidate.

(a) BUG: the Re-run path hardcoded `siding_exposure_in=None`,
`brick_course_in=None`, `reference_dim=None`, `elevation_tags=None` —
every re-run ever fired silently discarded contractor calibration.
Found when the failed validation run's course counting never fired:
the contractor's 3.75" exposure never reached Phase A.

(b) Exposure-based course counting extended to WALL HEIGHTS (courses
are plane-correct by construction).

(c) Depth-plane rule + fail-loudly cross-plane flag. Taped control
case (verbatim, the rule's justification forever):
    same ref, same plane = exact; same ref, cross-plane = +45%.
"""
from __future__ import annotations

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

import sys
sys.path.insert(0, "/app/backend")
from routes import ai_measure as aim  # noqa: E402

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

EMAIL = "hhunt6677@yahoo.com"
PASSWORD = "Admin123!"


# ---------------------------------------------------------------------------
# (a) Re-run calibration carryover — HTTP integration
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture()
def prev_run(session):
    """Seed a completed run doc carrying calibration + one junk photo on
    disk (PIL can't open it → worker fails fast, no LLM cost)."""
    user = MONGO.users.find_one({"email": EMAIL})
    run_id = uuid.uuid4().hex
    photo_name = f"tape-cal-{uuid.uuid4().hex[:8]}.jpg"
    from config import UPLOAD_DIR
    (UPLOAD_DIR / photo_name).write_bytes(b"not-a-real-image")
    MONGO.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": user["id"],
        "estimate_id": None, "status": "done",
        "photo_paths": photo_name, "kind": "siding",
        "model_choice": "claude-opus-4-5",
        "reference_dim": "WALL REF front = 324in",
        "brick_course_in": 8.0,
        "siding_exposure_in": 3.75,
        "elevation_tags": "front",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "result": {"measurements": {"overhang_in": 12.0}},
    })
    yield {"run_id": run_id, "photo_name": photo_name}
    MONGO.ai_measure_runs.delete_many({"$or": [{"run_id": run_id}, {"rerun_of": run_id}]})
    (UPLOAD_DIR / photo_name).unlink(missing_ok=True)


def test_rerun_carries_calibration_onto_new_run_doc(session, prev_run):
    r = session.post(f"{BASE}/measure/ai-measure/rerun/{prev_run['run_id']}", json={}, timeout=30)
    assert r.status_code == 200, r.text
    new_id = r.json()["run_id"]
    doc = MONGO.ai_measure_runs.find_one({"run_id": new_id})
    assert doc is not None
    assert doc["siding_exposure_in"] == 3.75, "3.75in exposure must survive re-run"
    assert doc["brick_course_in"] == 8.0
    assert doc["reference_dim"] == "WALL REF front = 324in"
    assert doc["elevation_tags"] == "front"
    assert doc["rerun_of"] == prev_run["run_id"]


def test_rerun_body_calibration_wins_over_prev_doc(session, prev_run):
    """The contractor's CURRENT Calibrate popover values (request body)
    take precedence over the previous run's stored calibration."""
    r = session.post(
        f"{BASE}/measure/ai-measure/rerun/{prev_run['run_id']}",
        json={"siding_exposure_in": 4.5, "brick_course_in": 7.625},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    doc = MONGO.ai_measure_runs.find_one({"run_id": r.json()["run_id"]})
    assert doc["siding_exposure_in"] == 4.5
    assert doc["brick_course_in"] == 7.625
    # reference_dim not in body → still inherited from prev doc
    assert doc["reference_dim"] == "WALL REF front = 324in"


def test_rerun_of_legacy_run_without_calibration_is_null_not_crash(session):
    """Legacy run docs predate persistence — rerun must behave as before
    (None), not 500."""
    user = MONGO.users.find_one({"email": EMAIL})
    run_id = uuid.uuid4().hex
    photo_name = f"tape-legacy-{uuid.uuid4().hex[:8]}.jpg"
    from config import UPLOAD_DIR
    (UPLOAD_DIR / photo_name).write_bytes(b"junk")
    MONGO.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": user["id"], "estimate_id": None,
        "status": "done", "photo_paths": photo_name, "kind": "siding",
        "created_at": datetime.now(timezone.utc),
    })
    try:
        r = session.post(f"{BASE}/measure/ai-measure/rerun/{run_id}", json={}, timeout=30)
        assert r.status_code == 200, r.text
        doc = MONGO.ai_measure_runs.find_one({"run_id": r.json()["run_id"]})
        assert doc.get("siding_exposure_in") is None
    finally:
        MONGO.ai_measure_runs.delete_many({"$or": [{"run_id": run_id}, {"rerun_of": run_id}]})
        (UPLOAD_DIR / photo_name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# (b)+(c) prompt candidate content
# ---------------------------------------------------------------------------

class TestPromptCandidate:
    def test_exposure_line_covers_wall_heights(self):
        p = aim._build_phase_a_prompt(
            photo_idx=0, address=None, reference_dim=None,
            brick_course_in=None, siding_exposure_in=3.75,
            annotation_hint="",
        )
        assert "3.75 in per row" in p
        assert "WALL HEIGHTS" in p
        assert "eave_courses_counted" in p
        assert "plane-correct" in p

    def test_no_exposure_no_counting_instruction(self):
        p = aim._build_phase_a_prompt(
            photo_idx=0, address=None, reference_dim=None,
            brick_course_in=None, siding_exposure_in=None,
            annotation_hint="",
        )
        assert "SIDING EXPOSURE" not in p

    def test_phase_a_static_prompt_has_depth_plane_rule(self):
        src = aim.PER_PHOTO_EXTRACT_PROMPT if hasattr(aim, "PER_PHOTO_EXTRACT_PROMPT") else None
        blob = src or open("/app/backend/routes/ai_measure.py").read()
        assert "ONLY WORK ON THEIR OWN WALL PLANE" in blob
        assert "eave_scale_cross_plane" in blob
        # The control case, verbatim — the rule's justification forever.
        assert "same\n   ref, same plane = exact; same ref, cross-plane = +45%" in blob \
            or "same ref, same plane = exact; same ref, cross-plane = +45%" in blob.replace("\n   ", " ")

    def test_reconcile_prompt_has_cross_plane_flag(self):
        blob = open("/app/backend/routes/ai_measure.py").read()
        assert '"height_scale_flag"' in blob or "height_scale_flag" in blob
        assert "cross_plane" in blob

    def test_failed_revision_rules_stay_out(self):
        """The rolled-back 79j.65 mitigations must NOT ride back in with
        this candidate (experiment isolation)."""
        blob = open("/app/backend/routes/ai_measure.py").read()
        assert "VERTICAL SCALE FOR VERTICAL MEASUREMENTS" not in blob
        assert "GRADE OCCLUSION + NO ROUNDING" not in blob
        assert "NO PRIOR, NO SYMMETRY BIAS" not in blob
