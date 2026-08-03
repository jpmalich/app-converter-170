"""STEP 5 SEALS — PENDING, NOT DISCARDED (Howard ruled 2026-08-01, findings
2 + 10d). An unapplied measure run (photo AND blueprint) sits visibly
flagged, never silently prices, never vanishes — dollars only on apply.
The Iter-99 silent LP-pair seeding from the latest unapplied run is RETIRED.
Self-cleaning: every estimate/run this file creates is deleted at the end."""
import os
import uuid
import inspect
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
TEST_PASSWORD = _ENV.get("ADMIN_PASSWORD", "")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", TEST_PASSWORD)


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


def _mongo():
    from pymongo import MongoClient
    return MongoClient(_ENV["MONGO_URL"])[_ENV["DB_NAME"]]


@pytest.fixture()
def est_with_run(s):
    made, run_ids = [], []
    db = _mongo()

    def make(door="photo", applied=False):
        r = s.post(f"{API}/estimates",
                   json={"customer_name": f"TEST_PEND-{uuid.uuid4().hex[:6]}",
                         "kind": "siding"})
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        made.append(eid)
        rid = f"test-{uuid.uuid4().hex[:10]}"
        run_ids.append(rid)
        coll = db.ai_measure_runs if door == "photo" else db.ai_blueprint_runs
        coll.insert_one({
            "run_id": rid, "estimate_id": eid, "status": "done",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": {"measurements": {"siding_sqft": 1500.0, "window_count": 9,
                                        "eaves_lf": 90, "_run_id": rid}},
        })
        if applied:
            r = s.put(f"{API}/estimates/{eid}", json={
                "hover_measurements": {"siding_sqft": 1500.0, "eaves_lf": 90,
                                       "_run_id": rid, "_source": door}})
            assert r.status_code == 200, r.text
        return eid, rid

    yield make
    for eid in made:
        s.delete(f"{API}/estimates/{eid}")
    db.ai_measure_runs.delete_many({"run_id": {"$in": run_ids}})
    db.ai_blueprint_runs.delete_many({"run_id": {"$in": run_ids}})


def test_unapplied_photo_run_flags_pending(s, est_with_run):
    eid, rid = est_with_run("photo", applied=False)
    r = s.get(f"{API}/estimates/{eid}/pending-runs")
    assert r.status_code == 200, r.text
    pend = r.json()["pending"]
    assert [p["run_id"] for p in pend] == [rid]
    assert pend[0]["door"] == "photo" and pend[0]["siding_sqft"] == 1500.0


def test_unapplied_blueprint_run_flags_pending_10d(s, est_with_run):
    """10d: blueprint runs surface identically — no empty-pair blind spot."""
    eid, rid = est_with_run("blueprint", applied=False)
    pend = s.get(f"{API}/estimates/{eid}/pending-runs").json()["pending"]
    assert [p["run_id"] for p in pend] == [rid]
    assert pend[0]["door"] == "blueprint"


def test_applied_run_is_not_pending(s, est_with_run):
    eid, rid = est_with_run("photo", applied=True)
    body = s.get(f"{API}/estimates/{eid}/pending-runs").json()
    assert body["pending"] == []
    assert rid in body["applied_run_ids"]


def test_lp_pair_never_seeds_from_unapplied_run(s, est_with_run):
    """FINDING 2, SUPERSEDED BY RETIREMENT (Howard ruled 2026-08-03):
    the pair-lp door is GONE — doors are single-family and estimates are
    self-contained; cross-family fill is post-September. The human-gate
    guarantee this test pinned (an unapplied run must never price) now
    holds by construction: there is no pairing path at all."""
    eid, rid = est_with_run("photo", applied=False)
    r = s.post(f"{API}/estimates/{eid}/pair-lp")
    assert r.status_code in (404, 405), \
        f"the retired pair-lp route answered {r.status_code} — pairing is back"


def test_lp_pair_still_seeds_from_APPLIED_measurements(s, est_with_run):
    """SUPERSEDED BY RETIREMENT (Howard ruled 2026-08-03): even the
    human-blessed pairing path is post-September — applied measurements
    seed ONLY the estimate's own family through its own door."""
    eid, rid = est_with_run("photo", applied=True)
    r = s.post(f"{API}/estimates/{eid}/pair-lp")
    assert r.status_code in (404, 405), \
        f"the retired pair-lp route answered {r.status_code} — pairing is back"


def test_silent_seeding_source_is_gone():
    """No-resurrection pin: the pair-lp route no longer consults the runs
    collection for measurements."""
    import routes.estimates as est_mod
    src = inspect.getsource(est_mod.pair_lp) if hasattr(est_mod, "pair_lp") else \
        inspect.getsource(est_mod)
    seg = src[src.find("pair-lp"):src.find("pair-lp") + 4000] if "pair-lp" in src else src
    assert "ai_measure_runs.find_one" not in seg
