"""LP APPLY GATE — lp-package/materialize (ruled 2026-07-25).

Regression: photo-sourced lp_smart estimates lost their quantity path when
the Estimate consolidation (2026-07-24) removed the panel's item/qty table.
HOVER imports materialize tab lines server-side (hover-lp-run rebuild);
photo/blueprint runs had NO equivalent, so Apply Measurements left every
group tab at $0.00 with "Derived — not applied" stuck forever.

Pins:
  • materialize writes derived lp_smart tab lines (qty > 0) from the
    governing photo run through the SAME rebuild machinery hover uses
  • human-typed rows (qty_src == "human") survive re-materialize verbatim
  • v3 labor: derived rows never carry unflagged labor (human/company/0)
  • lp_smart-kind only — other kinds are refused (400)
  • no completed run → 404 (honest failure, nothing written)
  • the governing run is archived + stamped as lp_source_run_id
  • frontend apply gate wired: JobInfoPanel lp_smart branch calls the
    endpoint (THE CUT stands — no composition lines merge client-side)
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

LAP = '38 Series Lap 3/8" x 8" x 16\''


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def mongo_db():
    import os
    from pymongo import MongoClient
    client = MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _photo_run_doc(est_id: str, run_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "test_artifact": True,
        "run_id": run_id,
        "estimate_id": est_id,
        "status": "done",
        "source": "photo",
        "created_at": now,
        "updated_at": now,
        "result": {
            "measurements": {
                "siding_sqft": 2000,
                "siding_with_openings_sqft": 2000,
                "eaves_lf": 120,
                "rakes_lf": 80,
                "starter_lf": 120,
                "window_count": 4,
                "entry_door_count": 1,
                "opening_count": 5,
                "_per_profile_sqft": {"lap": 2000},
            },
            "raw_ai": {"walls": [], "openings": [], "corner_locations": []},
        },
    }


@pytest.fixture()
def photo_est(session, mongo_db):
    r = session.post(f"{API}/estimates",
                     json={"kind": "lp_smart", "customer_name": "TEST_lp materialize"},
                     timeout=15)
    est_id = r.json()["id"]
    run_id = "test-lpmat-" + uuid.uuid4().hex[:10]
    # test_artifact stamp lives inside _photo_run_doc (ruled 2026-07-18)
    mongo_db.ai_measure_runs.insert_one(_photo_run_doc(est_id, run_id))
    yield est_id, run_id
    session.delete(f"{API}/estimates/{est_id}", timeout=15)
    mongo_db.estimates.delete_one({"id": est_id})
    mongo_db.estimates_trash.delete_one({"id": est_id})
    mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
    mongo_db.fixture_runs.delete_many({"run_id": run_id})


class TestMaterializeWritesTabLines:
    def test_derived_lp_lines_land_with_qty(self, session, photo_est):
        est_id, run_id = photo_est
        r = session.post(f"{API}/estimates/{est_id}/lp-package/materialize",
                         json={}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["ok"] is True and body["run_id"] == run_id
        assert body["line_count"] > 0
        est = session.get(f"{API}/estimates/{est_id}", timeout=15).json()
        lp = [l for l in (est.get("lines") or [])
              if (l.get("tab") or "vinyl") == "lp_smart"]
        derived = [l for l in lp if (l.get("qty") or 0) > 0]
        assert derived, "materialize wrote no lp_smart quantities"
        lap = next((l for l in lp if l.get("name") == LAP), None)
        assert lap is not None and (lap.get("qty") or 0) > 0, \
            f"lap siding row missing/empty: {[(l['name'], l.get('qty')) for l in lp][:8]}"
        # v3 labor: no unflagged labor — every derived LP row is
        # human/company-bound or an explicit $0.
        for l in lp:
            if (l.get("lab") or 0) > 0:
                assert l.get("lab_src") in ("human", "company"), \
                    f"unflagged labor on {l.get('name')}: {l.get('lab')} ({l.get('lab_src')})"

    def test_source_run_stamped_and_archived(self, session, mongo_db, photo_est):
        est_id, run_id = photo_est
        r = session.post(f"{API}/estimates/{est_id}/lp-package/materialize",
                         json={}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        doc = mongo_db.estimates.find_one({"id": est_id}, {"lp_source_run_id": 1})
        assert doc.get("lp_source_run_id") == run_id
        arch = mongo_db.fixture_runs.find_one({"run_id": run_id})
        assert arch and "lp-materialize" in (arch.get("artifact_reasons") or [])

    def test_human_typed_qty_survives_rematerialize(self, session, mongo_db, photo_est):
        est_id, run_id = photo_est
        r = session.post(f"{API}/estimates/{est_id}/lp-package/materialize",
                         json={}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        est = session.get(f"{API}/estimates/{est_id}", timeout=15).json()
        lines = est.get("lines") or []
        lap = next(l for l in lines if l.get("name") == LAP)
        lap["qty"] = 999
        lap["qty_src"] = "human"
        pr = session.put(f"{API}/estimates/{est_id}",
                         json={"lines": lines}, timeout=15)
        assert pr.status_code == 200, pr.text[:300]
        r2 = session.post(f"{API}/estimates/{est_id}/lp-package/materialize",
                          json={}, timeout=60)
        assert r2.status_code == 200, r2.text[:300]
        est2 = session.get(f"{API}/estimates/{est_id}", timeout=15).json()
        lap2 = next(l for l in (est2.get("lines") or []) if l.get("name") == LAP)
        assert lap2.get("qty") == 999 and lap2.get("qty_src") == "human", \
            f"human qty clobbered: {lap2.get('qty')} ({lap2.get('qty_src')})"


class TestMaterializeRefusals:
    def test_non_lp_kind_refused(self, session, mongo_db):
        r = session.post(f"{API}/estimates",
                         json={"customer_name": "TEST_lpmat siding"}, timeout=15)
        est_id = r.json()["id"]
        run_id = "test-lpmat-sd-" + uuid.uuid4().hex[:8]
        # test_artifact stamp lives inside _photo_run_doc (ruled 2026-07-18)
        mongo_db.ai_measure_runs.insert_one(_photo_run_doc(est_id, run_id))
        try:
            rr = session.post(f"{API}/estimates/{est_id}/lp-package/materialize",
                              json={}, timeout=30)
            assert rr.status_code == 400, rr.text[:200]
        finally:
            session.delete(f"{API}/estimates/{est_id}", timeout=15)
            mongo_db.estimates.delete_one({"id": est_id})
            mongo_db.estimates_trash.delete_one({"id": est_id})
            mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
            mongo_db.fixture_runs.delete_many({"run_id": run_id})

    def test_no_run_is_404_nothing_written(self, session, mongo_db):
        r = session.post(f"{API}/estimates",
                         json={"kind": "lp_smart", "customer_name": "TEST_lpmat norun"},
                         timeout=15)
        est_id = r.json()["id"]
        try:
            rr = session.post(f"{API}/estimates/{est_id}/lp-package/materialize",
                              json={}, timeout=30)
            assert rr.status_code == 404, rr.text[:200]
            doc = mongo_db.estimates.find_one({"id": est_id}, {"lines": 1})
            assert not [l for l in (doc.get("lines") or []) if (l.get("qty") or 0) > 0]
        finally:
            session.delete(f"{API}/estimates/{est_id}", timeout=15)
            mongo_db.estimates.delete_one({"id": est_id})
            mongo_db.estimates_trash.delete_one({"id": est_id})


class TestFrontendApplyGateWired:
    def test_jobinfopanel_calls_materialize_on_lp_apply(self):
        src = Path("/app/frontend/src/components/estimate/JobInfoPanel.jsx").read_text()
        assert "lp-package/materialize" in src, \
            "JobInfoPanel lp_smart apply branch no longer calls the materialize apply gate"
        # THE CUT stands: the lp_smart branch still returns before the
        # frontend line-merge path.
        cut_idx = src.index('srcKind === "lp_smart"')
        merge_idx = src.index("bakeWasteIntoLines(aiLines")
        assert cut_idx < merge_idx

    def test_hover_rebuild_shares_the_helper(self):
        src = Path("/app/backend/routes/hover.py").read_text()
        assert "async def rebuild_lp_tab_lines" in src
        assert src.count("rebuild_lp_tab_lines(") >= 2  # def + hover call
