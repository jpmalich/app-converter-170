"""ARCHIVED-RUN READ-SIDE for the blueprint source-sheet viewer (Howard,
ruled 2026-07-20 — AUTHORIZED after the substrate reconciliation). Pins:

1. TTL DEFUSAL: when the live ai_blueprint_runs doc is gone, the
   latest-for-estimate endpoint serves the CUT-archived copy from
   fixture_runs (substrate ai_blueprint_runs) with page_paths intact and
   archived=True named on the response.
2. FRESH-RUN BEHAVIOR UNCHANGED: a live doc serves exactly as before,
   archived=False.
3. EMPTY STATE only for genuinely absent substrate (no live, no archive):
   {"run": None}.
4. READ PATH ONLY: the endpoint performs no writes; archive access goes
   through run_archive.find_archived_run (fork-boundary ownership); the
   CUT-archive WRITE path (blueprint-applied) is untouched this slice.
"""
import inspect
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"


def _mongo():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


@pytest.fixture(scope="module")
def substrate(session):
    """Temp estimate + one LIVE run + one ARCHIVED-ONLY run for a second
    temp estimate. All docs tagged test_artifact (harness doctrine)."""
    db = _mongo()
    me = session.get(f"{API}/auth/me", timeout=15).json()
    user_id = me.get("id") or (me.get("user") or {}).get("id")
    now = datetime.now(timezone.utc)

    def mk_est(tag):
        r = session.post(f"{API}/estimates", json={
            "kind": "lp_smart",
            "customer_name": f"ZZ archived-readside {tag} TEMP"}, timeout=15)
        return r.json()["id"]

    est_live, est_arch, est_none = mk_est("live"), mk_est("arch"), mk_est("none")
    run_live, run_arch = uuid.uuid4().hex, uuid.uuid4().hex
    base = {
        "test_artifact": True,  # harness doctrine (ruled 2026-07-18)
        "user_id": user_id, "status": "done", "stage": "done",
        "page_count": 2, "page_paths": "bp_pin_a.png,bp_pin_b.png",
        "created_at": now, "updated_at": now, "completed_at": now,
        "error": None,
        "result": {"measurements": {"siding_sqft": 1234.0}},
    }
    # test_artifact stamped at creation via `base` (harness doctrine)
    db.ai_blueprint_runs.insert_one(
        {**base, "run_id": run_live, "estimate_id": est_live})
    # Archived-only: fixture_runs copy EXACTLY as the CUT writes it
    # (full doc + substrate) — no live counterpart (TTL already reaped).
    # test_artifact stamped at creation via `base` (harness doctrine)
    db.fixture_runs.insert_one(
        {**base, "run_id": run_arch, "estimate_id": est_arch,
         "substrate": "ai_blueprint_runs",
         "artifact_reasons": ["blueprint-apply"]})
    yield {"est_live": est_live, "est_arch": est_arch, "est_none": est_none,
           "run_live": run_live, "run_arch": run_arch}
    for eid in (est_live, est_arch, est_none):
        session.delete(f"{API}/estimates/{eid}", timeout=15)
    db.ai_blueprint_runs.delete_one({"run_id": run_live})
    db.fixture_runs.delete_many({"run_id": {"$in": [run_live, run_arch]}})


def _latest(session, est_id):
    r = session.get(f"{API}/measure/ai-blueprint/latest-for-estimate/{est_id}",
                    timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["run"]


def test_pin1_archived_index_serves_pages_past_ttl(session, substrate):
    run = _latest(session, substrate["est_arch"])
    assert run is not None, "archived index must serve — TTL defusal"
    assert run["run_id"] == substrate["run_arch"]
    assert run["archived"] is True
    assert run["page_paths"] == "bp_pin_a.png,bp_pin_b.png"
    assert run["status"] == "done"


def test_pin2_fresh_run_behavior_unchanged(session, substrate):
    run = _latest(session, substrate["est_live"])
    assert run is not None
    assert run["run_id"] == substrate["run_live"]
    assert run["archived"] is False
    assert run["page_paths"] == "bp_pin_a.png,bp_pin_b.png"


def test_pin3_empty_only_for_genuinely_absent_substrate(session, substrate):
    assert _latest(session, substrate["est_none"]) is None


def test_pin4_read_path_only_no_writes():
    from routes.ai_blueprint import ai_blueprint_latest_for_estimate
    src = inspect.getsource(ai_blueprint_latest_for_estimate)
    for verb in ("insert_one", "update_one", "delete_one", "insert_many",
                 "update_many", "delete_many", "archive_run_for_artifact"):
        assert verb not in src, f"read side must not write — found {verb}"
    assert "find_archived_run" in src  # fork-boundary ownership honored
