"""SEND-48 live pins — the ZONE BINDING flow over HTTP.

Clone a real blueprint run under a DISPOSABLE estimate (never touching a
real estimate), then: propose → provisional zones exist and feed NO
quantity; confirm one (human) → per-surface Law A math on the line;
delete → derived value restored. Cleanup always runs.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API  # env-derived
from creds_for_tests import TEST_PASSWORD


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": "hhunt6677@yahoo.com",
                     "password": TEST_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip("env:live_auth: test login unavailable")
    return s


@pytest.fixture(scope="module")
def rig(sess):
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"],
                     serverSelectionTimeoutMS=2000)[os.environ["DB_NAME"]]
    src = db.ai_blueprint_runs.find_one(
        {"estimate_id": "264b6230-5d0f-49ea-b07d-8d33a537f293",
         "status": "done"}, sort=[("created_at", -1)])
    if not src:
        pytest.skip("env:fixture_data: source blueprint run not in datastore")
    r = sess.post(f"{API}/estimates",
                  json={"kind": "lp_smart",
                        "customer_name": "ZZ TEST_zone-binding TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    est = r.json()
    lines = [{"tab": "vinyl", "section": "Siding", "unit": "SQ",
              "qty": 44.0, "raw_qty": 44.0, "qty_src": "derived",
              "name": "D4 Clapboard"}]
    est["lines"] = lines
    rr = sess.put(f"{API}/estimates/{eid}", json=est, timeout=15)
    assert rr.status_code == 200, rr.text
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_zone-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def _siding(sess, eid):
    est = sess.get(f"{API}/estimates/{eid}", timeout=15).json()
    return next(l for l in est["lines"]
                if (l.get("section") or "").lower().startswith("siding"))


def test_propose_creates_provisional_zones_feeding_no_quantity(sess, rig):
    r = sess.post(f"{API}/estimates/{rig['eid']}/pdf-overlay/propose",
                  timeout=30)
    assert r.status_code == 200, r.text
    proposed = r.json()["proposed"]
    # letrick-shaped run: SEND-55 ladder — EVERY evaluated face proposes
    # (three DERIVED chains + rear's contested tier). Coverage is a
    # fact, not a success metric.
    assert len(proposed) == 4
    assert {p["face_id"] for p in proposed} == {"front", "back",
                                                "left", "right"}
    assert all(p["provenance"] == "proposed" for p in proposed)
    assert all(p["sqft"] is None for p in proposed)
    assert _siding(sess, rig["eid"])["qty"] == 44.0  # untouched


def test_confirming_a_proposal_makes_it_human_and_applies_law_a(sess, rig):
    polys = sess.get(f"{API}/estimates/{rig['eid']}/pdf-overlay",
                     timeout=15).json()["polygons"]
    prop = next(p for p in polys if p["provenance"] == "proposed")
    body = {"id": prop["id"], "page": prop["page"],
            "face_id": prop["face_id"], "material_class": "siding",
            "vertices_pct": prop["vertices_pct"],
            "scale_ref": prop["scale_ref"],
            "page_w_px": prop["page_w_px"], "page_h_px": prop["page_h_px"],
            "provenance": "human"}
    r = sess.put(f"{API}/estimates/{rig['eid']}/pdf-overlay", json=body,
                 timeout=15)
    assert r.status_code == 200, r.text
    out = r.json()["polygon"]
    assert out["provenance"] == "human"
    assert out["sqft"] and out["sqft"] > 0        # trace scale computed
    sid = _siding(sess, rig["eid"])
    assert sid["overlay_superseded"] is True
    assert sid["superseded_qty"] == 44.0          # previous number SHOWN
    assert sid["qty"] != 44.0
    assert sid["qty_src"] == "human"


def test_delete_restores_the_derived_value(sess, rig):
    polys = sess.get(f"{API}/estimates/{rig['eid']}/pdf-overlay",
                     timeout=15).json()["polygons"]
    human = next(p for p in polys if p["provenance"] == "human")
    r = sess.delete(
        f"{API}/estimates/{rig['eid']}/pdf-overlay/{human['id']}",
        timeout=15)
    assert r.status_code == 200 and r.json()["retired_override"] is True
    sid = _siding(sess, rig["eid"])
    assert sid["qty"] == 44.0
    assert sid.get("qty_src") == "derived"


def test_propose_is_a_derived_write_and_423s_on_the_protected_estimate(sess):
    protected = sess.get(f"{API}/estimates", timeout=15).json()
    est = next((e for e in protected
                if e.get("estimate_number") == "EST-886440"), None)
    if not est:
        pytest.skip("env:fixture_data: protected estimate not present")
    r = sess.post(f"{API}/estimates/{est['id']}/pdf-overlay/propose",
                  timeout=15)
    assert r.status_code == 423
