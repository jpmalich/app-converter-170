"""SEND-100 register (Howard, 2026-08-14): browser verification found
the confirm path LAUNDERING chase zones — `resolve_face_from_bands`
knew "gable:" but not "chase:", so confirming a proposed chase zone
stripped the prefix and merged it into body-class math (no chase quote
row, no Ruling L block, contested area priced silently). Two fixes,
pinned here:
1. a surface prefix (gable:/chase:) SURVIVES band resolution;
2. confirmation upgrades AUTHORITY, not EVIDENCE — the proposal's
   tier/basis stay on the zone (a contested chase must still refuse).
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API
from creds_for_tests import TEST_PASSWORD
from routes.pdf_overlay import resolve_face_from_bands

_BANDS = {"rear": (0.0, 50.0), "front": (50.0, 100.0)}
_TOP = [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]


def test_chase_prefix_survives_band_resolution():
    r = resolve_face_from_bands(_BANDS, _TOP, "chase:back")
    assert r["status"] == "RESOLVED"
    assert r["resolved_face_id"] == "chase:back"
    assert r["disagrees"] is False
    # the host face still resolves from the band, not the tag
    r2 = resolve_face_from_bands(_BANDS, _TOP, "chase:front")
    assert r2["resolved_face_id"] == "chase:back"
    assert r2["disagrees"] is True
    # gable behavior unchanged
    r3 = resolve_face_from_bands(_BANDS, _TOP, "gable:back")
    assert r3["resolved_face_id"] == "gable:back"


def test_chase_prefix_survives_ambiguity_candidates():
    straddle = [[0.1, 0.4], [0.3, 0.4], [0.3, 0.6], [0.1, 0.6]]
    r = resolve_face_from_bands(_BANDS, straddle, "chase:back")
    assert r["status"] == "AMBIGUOUS"
    assert all(c.startswith("chase:") for c in r["candidates"])


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
                  json={"kind": "siding",
                        "customer_name": "ZZ TEST_chase100 TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    # one aggregate siding line so chase rows have a takeoff to land in
    db.estimates.update_one({"id": eid}, {"$set": {"lines": [
        {"name": "Charter Oak Standard color Dutch Lap 4.5\" .046",
         "unit": "SQ", "qty": 11.77, "raw_qty": 11.77, "mat": 151.31,
         "lab": 0.0, "tab": "vinyl", "section": "Vinyl Siding"}]}})
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_chase100-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_deletion_ledger.delete_many({"estimate_id": eid})
    db.zone_correction_events.delete_many({"estimate_id": eid})
    db.human_dimensions.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def _confirm(sess, eid, poly):
    r = sess.put(f"{API}/estimates/{eid}/pdf-overlay", json={
        "id": poly["id"], "page": poly["page"], "face_id": poly["face_id"],
        "material_class": poly["material_class"],
        "vertices_pct": poly["vertices_pct"],
        "scale_ref": poly.get("scale_ref"),
        "page_w_px": poly.get("page_w_px"),
        "page_h_px": poly.get("page_h_px"),
        "provenance": "human", "face_confirmed": False}, timeout=120)
    assert r.status_code == 200, r.text
    return r.json()["polygon"]


def test_live_confirmed_contested_chase_refuses_on_the_quote(sess, rig):
    """The full journey the browser travels: propose → confirm the
    contested chase:back → the zone KEEPS its face and its contest, the
    quote grows a REFUSED chase row (Ruling L), and the gate registry
    emits chase_contested_scale."""
    eid = rig["eid"]
    rp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                   timeout=240)
    assert rp.status_code == 200, rp.text
    props = rp.json()["proposed"]
    back = next(p for p in props if p["face_id"] == "chase:back")
    assert back["tier"] == "contested_pick_larger"
    saved = _confirm(sess, eid, back)
    # fix 1: the prefix survived
    assert saved["face_id"] == "chase:back"
    # fix 2: authority upgraded, evidence kept
    assert saved["tier"] == "contested_pick_larger"
    assert "chimney chase" in (saved["basis"] or "")
    est = sess.get(f"{API}/estimates/{eid}", timeout=60).json()
    row = next(ln for ln in est["lines"] if ln.get("overlay_chase_line"))
    assert row["name"] == "Chimney Chase — rear"
    assert row["qty"] is None and row["not_derivable"]
    assert "Ruling L" in row["not_derivable_reason"]
    assert "CONTESTED" in row["not_derivable_reason"]
    rd = sess.get(f"{API}/estimates/{eid}/readiness", timeout=60).json()
    assert any(i.get("kind") == "chase_refused" and i.get("blocking")
               for i in rd["items"]), rd["items"]


def test_live_tape_then_reconfirm_prices_the_chase(sess, rig):
    """After a band-matched tape resolves the contest, the re-proposed
    chase carries taped_human; confirming it prices the row and the
    chase gate clears."""
    eid = rig["eid"]
    r = sess.post(f"{API}/estimates/{eid}/pdf-overlay/tape",
                  json={"face_id": "back", "text": "9'-6\"",
                        "ref_from": "first_floor_line",
                        "ref_to": "top_of_plate_line"}, timeout=15)
    assert r.status_code == 200, r.text
    rp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                   timeout=240)
    assert rp.status_code == 200, rp.text
    new_back = next(p for p in rp.json()["proposed"]
                    if p["face_id"] == "chase:back")
    assert new_back["tier"] == "taped_human"
    # replace the contested confirmed zone with the taped one
    old = rig["db"].pdf_overlay_polygons.find_one(
        {"estimate_id": eid, "face_id": "chase:back",
         "provenance": "human"})
    rd0 = sess.delete(
        f"{API}/estimates/{eid}/pdf-overlay/{old['id']}", timeout=60)
    assert rd0.status_code == 200
    saved = _confirm(sess, eid, new_back)
    assert saved["face_id"] == "chase:back"
    assert saved["tier"] == "taped_human"
    est = sess.get(f"{API}/estimates/{eid}", timeout=60).json()
    row = next(ln for ln in est["lines"] if ln.get("overlay_chase_line"))
    assert row["qty"] is not None and not row.get("not_derivable")
    assert "Basis:" in row["note"]
    rd = sess.get(f"{API}/estimates/{eid}/readiness", timeout=60).json()
    assert not any(i.get("kind") == "chase_refused" for i in rd["items"])
