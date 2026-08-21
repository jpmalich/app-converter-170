"""SEND-84 — DELETION LEDGER pins (wired after EST-713272's nine human
zones proved unrecoverable from every persistent source).

Every zone deletion, on EVERY estimate, leaves a full recoverable
snapshot in `zone_deletion_ledger`:
  • human_delete — the DELETE endpoint snapshots the victim verbatim.
  • propose_rebuild_wipe — re-proposing snapshots the derived
    proposals it replaces (a rule change overwrites old geometry; the
    ledger keeps what the superseded rules had drawn).
Restores nothing — the ledger records; recovery stays Howard's word.
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creds_for_tests import TEST_PASSWORD  # noqa: E402

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(_ENV["MONGO_URL"])
    return c[_ENV["DB_NAME"]]


@pytest.fixture()
def rig(s, mongo):
    r = s.post(f"{API}/estimates",
               json={"customer_name": f"SEND84-{uuid.uuid4().hex[:6]}",
                     "kind": "siding"})
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    yield eid
    mongo.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    mongo.zone_deletion_ledger.delete_many({"estimate_id": eid})
    mongo.ai_blueprint_runs.delete_many({"estimate_id": eid})
    s.delete(f"{API}/estimates/{eid}")
    mongo.estimates.delete_many({"id": eid})


def test_human_delete_leaves_full_recoverable_snapshot(s, mongo, rig):
    eid = rig
    pid = f"send84-{uuid.uuid4().hex[:8]}"
    poly = {
        "id": pid, "estimate_id": eid, "page": 1, "face_id": "front",
        "material_class": "siding", "provenance": "human",
        "vertices_pct": [[0.1, 0.1], [0.4, 0.1], [0.4, 0.5], [0.1, 0.5]],
        "sqft": 480.0, "derived_baseline_qty": 20.0,
        "author_email": "howard@example.com",
    }
    mongo.pdf_overlay_polygons.insert_one(dict(poly))
    r = s.delete(f"{API}/estimates/{eid}/pdf-overlay/{pid}")
    assert r.status_code == 200, r.text
    led = mongo.zone_deletion_ledger.find_one(
        {"estimate_id": eid, "kind": "human_delete"}, {"_id": 0})
    assert led, "deletion left no ledger entry"
    assert led["actor_email"] == ADMIN_EMAIL
    snap = led["polygon"]
    for k, v in poly.items():
        assert snap.get(k) == v, f"snapshot lost field {k}"
    assert mongo.pdf_overlay_polygons.count_documents({"id": pid}) == 0


def test_propose_rebuild_wipe_ledgers_replaced_proposals(s, mongo, rig):
    eid = rig
    # a minimal 'done' run so propose passes the OCR gate; no faces
    # derive, so the endpoint only wipes and re-proposes nothing.
    mongo.ai_blueprint_runs.insert_one({
        "test_artifact": True,
        "estimate_id": eid, "status": "done",
        "run_id": f"send84-{uuid.uuid4().hex[:8]}",
        "created_at": datetime.now(timezone.utc),
        "source_files": [],
        "result": {"raw_ai": {"_ocr_text_by_page": {
            "1": {"page_w": 100, "page_h": 100, "runs": []}}}},
    })
    old = {
        "id": f"send84-{uuid.uuid4().hex[:8]}", "estimate_id": eid,
        "page": 1, "face_id": "left", "material_class": "siding",
        "provenance": "proposed",
        "vertices_pct": [[0.2, 0.2], [0.6, 0.2], [0.6, 0.7], [0.2, 0.7]],
        "geometry_tier": "wall_outline",
    }
    mongo.pdf_overlay_polygons.insert_one(dict(old))
    r = s.post(f"{API}/estimates/{eid}/pdf-overlay/propose")
    assert r.status_code == 200, r.text
    led = mongo.zone_deletion_ledger.find_one(
        {"estimate_id": eid, "kind": "propose_rebuild_wipe"}, {"_id": 0})
    assert led, "rebuild wipe left no ledger entry"
    snaps = led["polygons"]
    assert any(p.get("id") == old["id"]
               and p.get("vertices_pct") == old["vertices_pct"]
               for p in snaps), "wiped proposal not snapshotted verbatim"


def test_no_wipe_entry_when_nothing_wiped(s, mongo, rig):
    eid = rig
    mongo.ai_blueprint_runs.insert_one({
        "test_artifact": True,
        "estimate_id": eid, "status": "done",
        "run_id": f"send84-{uuid.uuid4().hex[:8]}",
        "created_at": datetime.now(timezone.utc),
        "source_files": [],
        "result": {"raw_ai": {"_ocr_text_by_page": {
            "1": {"page_w": 100, "page_h": 100, "runs": []}}}},
    })
    r = s.post(f"{API}/estimates/{eid}/pdf-overlay/propose")
    assert r.status_code == 200, r.text
    assert mongo.zone_deletion_ledger.count_documents(
        {"estimate_id": eid}) == 0
