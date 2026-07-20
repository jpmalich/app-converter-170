"""SOURCE VIEW GENERALIZED to every intake door (Howard, approved
2026-07-20). Pins:

1. PHOTO TTL DEFUSAL: ai-measure/latest-for-estimate serves the
   CUT-archived copy (fixture_runs, substrate ai_measure_runs) when the
   live doc is gone — archived=True named; photo_paths intact.
2. FRESH photo-run behavior unchanged (archived=False); genuinely absent
   substrate → {"run": None}; READ path only (no writes in the endpoint).
3. UNIFIED ROUTE: /estimate/:id/source-view registered; the accepted
   blueprint URL /source-sheets survives as an alias to the same page.
4. PHOTO MODE render contract: per-photo provenance (Photo i of n · kind
   · filename · run), consumption-order numbering note, same-run AI
   summary, 30-day boundary named, read-only, /api/uploads store.
5. HOVER MODE honesty: "No visual source retained" note + imported
   measurements reference — never a fake visual.
6. ADAPTIVE LINK: covered in test_3d_dark_all_audiences pin 5 (one link,
   label per door, no dead links).
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
FE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
JSX = (FE / "pages" / "SourceSheets.jsx").read_text()
APP = (FE / "App.js").read_text()


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
    db = _mongo()
    me = session.get(f"{API}/auth/me", timeout=15).json()
    user_id = me.get("id") or (me.get("user") or {}).get("id")
    now = datetime.now(timezone.utc)

    def mk_est(tag):
        r = session.post(f"{API}/estimates", json={
            "kind": "lp_smart",
            "customer_name": f"ZZ photo-readside {tag} TEMP"}, timeout=15)
        return r.json()["id"]

    est_live, est_arch, est_none = mk_est("live"), mk_est("arch"), mk_est("none")
    run_live, run_arch = uuid.uuid4().hex, uuid.uuid4().hex
    base = {
        "test_artifact": True,  # harness doctrine (ruled 2026-07-18)
        "user_id": user_id, "status": "done", "stage": "done",
        "photo_count": 2, "photo_paths": "ai_pin_a.jpg,ai_pin_b.jpg",
        "photo_kinds": "front,back",
        "created_at": now, "updated_at": now, "completed_at": now,
        "error": None,
        "result": {"raw_ai": {"walls": []},
                   "measurements": {"siding_sqft": 1500.0}},
    }
    # test_artifact stamped at creation via `base` (harness doctrine)
    db.ai_measure_runs.insert_one(
        {**base, "run_id": run_live, "estimate_id": est_live})
    # Archived-only copy, exactly as the CUT writes it (full doc + substrate).
    # test_artifact stamped at creation via `base` (harness doctrine)
    db.fixture_runs.insert_one(
        {**base, "run_id": run_arch, "estimate_id": est_arch,
         "substrate": "ai_measure_runs",
         "artifact_reasons": ["photo-apply"]})
    yield {"est_live": est_live, "est_arch": est_arch, "est_none": est_none,
           "run_live": run_live, "run_arch": run_arch}
    for eid in (est_live, est_arch, est_none):
        session.delete(f"{API}/estimates/{eid}", timeout=15)
    db.ai_measure_runs.delete_one({"run_id": run_live})
    db.fixture_runs.delete_many({"run_id": {"$in": [run_live, run_arch]}})


def _latest(session, est_id):
    r = session.get(f"{API}/measure/ai-measure/latest-for-estimate/{est_id}",
                    timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["run"]


def test_pin1_photo_archived_index_serves_past_ttl(session, substrate):
    run = _latest(session, substrate["est_arch"])
    assert run is not None, "archived photo index must serve — 30-day TTL defusal"
    assert run["run_id"] == substrate["run_arch"]
    assert run["archived"] is True
    assert run["photo_paths"] == "ai_pin_a.jpg,ai_pin_b.jpg"


def test_pin2_fresh_photo_run_unchanged_and_absent_none(session, substrate):
    run = _latest(session, substrate["est_live"])
    assert run["run_id"] == substrate["run_live"]
    assert run["archived"] is False
    assert run["photo_kinds"] == "front,back"
    assert _latest(session, substrate["est_none"]) is None


def test_pin2b_read_path_only_no_writes():
    from routes.ai_measure import ai_measure_latest_for_estimate
    src = inspect.getsource(ai_measure_latest_for_estimate)
    for verb in ("insert_one", "update_one", "delete_one", "insert_many",
                 "update_many", "delete_many", "archive_run_for_artifact"):
        assert verb not in src, f"read side must not write — found {verb}"
    assert "find_archived_run" in src


def test_pin3_unified_route_plus_alias():
    assert '<Route path="/estimate/:id/source-view" element={<SourceSheets />} />' in APP
    assert '<Route path="/estimate/:id/source-sheets" element={<SourceSheets />} />' in APP


def test_pin4_photo_mode_render_contract():
    assert 'data-testid="source-photos-provenance"' in JSX
    assert "photo extraction run {pid8}" in JSX
    assert "Photo {i + 1} of {photos.length}" in JSX  # per-photo numbering
    assert "{photoKinds[i] ?" in JSX                   # which upload kind
    assert 'data-testid="source-photos-ai-summary"' in JSX
    assert "AI-READ · photo extraction run {pid8}" in JSX
    assert "30 days" in JSX and "TTL" in JSX and "24h" in JSX  # boundaries named
    assert "elevation sheets" in JSX  # numbering matches the sheets' citations


def test_pin5_hover_mode_honesty():
    assert 'data-testid="source-hover-reference"' in JSX
    assert "No visual source retained" in JSX
    assert 'testid="source-hover-summary-table"' in JSX


def test_pin6_still_read_only():
    assert "api.get(" in JSX
    for verb in ("api.post", "api.put", "api.patch", "api.delete"):
        assert verb not in JSX, f"source view must stay read-only — found {verb}"
