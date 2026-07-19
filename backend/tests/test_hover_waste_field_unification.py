"""HOVER WASTE UNIFICATION (Howard, ruled 2026-07-20) — pins.

The ruled Hover 10% default is NO LONGER applied silently anywhere in the
engine. On a NEW Hover import, hover-lp-run writes 10.0 directly into the
estimate's visible, contractor-editable waste_pct field; every downstream
formula reads THAT field (via _apply_contractor_waste). Pre-existing Hover
estimates are untouched (no backfill).

Pins:
1. _hover_mapping_contract injects NO _waste_pct when none is passed —
   the estimate field governs; explicit override still wins.
2. hover-lp-run writes waste_pct=10.0 onto the estimate document.
3. lp-package preview on that estimate applies AND reports 0.10 — sourced
   from the field, not a constant.
4. The import worker bakes ZERO waste into draft lines and surfaces the
   field pre-fill as _waste_field_prefill_pct (the retired silent
   _lp_waste_pct_applied mechanism is gone from the worker).
5. Frontend: the LP apply path bakes the field pre-fill via the same
   raw_qty mechanism the SettingsRow knob uses, and pre-fills waste_pct.
"""
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
BACKEND = Path(__file__).resolve().parent.parent
FRONTEND = BACKEND.parent / "frontend"


def _mongo():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


def test_pin1_contract_no_silent_waste_pct():
    from routes.lp_package_routes import _hover_mapping_contract
    m, _ = _hover_mapping_contract({"siding_sqft": 1000}, "lap")
    assert "_waste_pct" not in m  # field governs — nothing injected
    m2, _ = _hover_mapping_contract({"siding_sqft": 1000}, "lap", waste_pct=0.15)
    assert m2["_waste_pct"] == 0.15  # explicit override wins


@pytest.fixture(scope="module")
def materialized(session):
    """Temp LP estimate + synthetic done Hover run → hover-lp-run."""
    db = _mongo()
    me = session.get(f"{API}/auth/me", timeout=15).json()
    user_id = me.get("id") or (me.get("user") or {}).get("id")
    assert user_id, me
    r = session.post(f"{API}/estimates",
                     json={"kind": "lp_smart",
                           "customer_name": "ZZ hover-waste-unification TEMP"},
                     timeout=15)
    est_id = r.json()["id"]
    hover_run_id = uuid.uuid4().hex
    db.hover_import_runs.insert_one({
        "test_artifact": True,  # harness doctrine (ruled 2026-07-18)
        "run_id": hover_run_id,
        "user_id": user_id,
        "status": "done",
        "stage": "done",
        "created_at": datetime.now(timezone.utc),
        "result": {"measurements": {"siding_sqft": 1000.0,
                                    "overhang_in": 12.0}},
    })
    rr = session.post(f"{API}/estimates/{est_id}/hover-lp-run",
                      json={"hover_run_id": hover_run_id, "profile": "lap"},
                      timeout=30)
    assert rr.status_code == 200, rr.text
    lp_run_id = rr.json()["lp_run_id"]
    yield {"est_id": est_id, "lp_run_id": lp_run_id, "db": db}
    session.delete(f"{API}/estimates/{est_id}", timeout=15)
    db.hover_import_runs.delete_one({"run_id": hover_run_id})
    db.ai_measure_runs.delete_one({"run_id": lp_run_id})
    db.fixture_runs.delete_many({"run_id": {"$in": [hover_run_id, lp_run_id]}})


def test_pin2_import_writes_10_into_visible_field(session, materialized):
    est = session.get(f"{API}/estimates/{materialized['est_id']}", timeout=15).json()
    assert est["waste_pct"] == 10.0  # written to the field, not applied silently


def test_pin2b_materialized_run_carries_no_waste_pct(materialized):
    run = materialized["db"].ai_measure_runs.find_one(
        {"run_id": materialized["lp_run_id"]})
    meas = ((run or {}).get("result") or {}).get("measurements") or {}
    assert "_waste_pct" not in meas  # the field is the ONLY carrier


def test_pin3_preview_waste_sourced_from_field(session, materialized):
    p = session.post(f"{API}/estimates/{materialized['est_id']}/lp-package/preview",
                     json={}, timeout=60).json()
    assert p["summary"]["waste_pct_applied"] == 0.10  # 10.0 field → 0.10 applied
    lap = next(l for l in p["lines"] if "38 Series Lap 3/8" in l["name"])
    # 1000 ÷ 100 × 11 = 110 base; × 1.10 field waste = 121, ceil once.
    assert lap["math"]["base_qty"] == 110.0
    assert lap["qty"] == 121


def test_pin4_worker_bakes_zero_and_surfaces_prefill():
    src = (BACKEND / "routes" / "hover.py").read_text()
    assert '_lp_waste_pct_applied' not in src  # retired silent mechanism
    assert 'measurements["_waste_pct"] = 0.0' in src  # BASE draft lines
    assert 'measurements["_waste_field_prefill_pct"] = DEFAULT_WASTE_PCT' in src


def test_pin5_frontend_field_prefill_mechanism():
    jsx = (FRONTEND / "src" / "components" / "estimate"
           / "HoverImportButton.jsx").read_text()
    assert "_lp_waste_pct_applied" not in jsx
    assert "_waste_field_prefill_pct" in jsx
    # LP bakes the field pre-fill via the SettingsRow raw_qty mechanism…
    assert 'srcKind === "lp_smart" ? lpWasteFieldPrefill : 0' in jsx
    # …and writes the value into the visible field on apply + save.
    assert jsx.count('{ waste_pct: wastePct }') >= 2
