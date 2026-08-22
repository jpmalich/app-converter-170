"""SEND-104 register (Howard, 2026-08-14) — REACHABLE-PLANE RULINGS.
The card asks: "Measure from the top of the foundation to the bottom of
the soffit." A taped measurement resolves the SIDED HEIGHT directly (no
conversion into DP-1's band) and CALIBRATES that face's scale ONLY where
both endpoint datums are drawn on that face (item 1). No soffit line is
drawn on either house — the topmost TOP OF PLATE closure is the upper
datum, difference recorded, never decided (item 2). A taped scale stays
on its own face (item 3, Ruling AAA — a scale that leaks between faces
is the mirrored-39 defect wearing better provenance)."""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API
from creds_for_tests import TEST_PASSWORD
from routes.pdf_overlay import _reachable_scale


def test_reachable_scale_needs_both_drawn_datums():
    cand = {"datum_lines": ["TOP_OF_PLATE@20.4", "FIRST_FLOOR@29.8",
                            "TOP_OF_FOUNDATION@30.9"]}
    plate, tof, why = _reachable_scale(cand)
    assert why is None and plate == 20.4 and tof == 30.9
    # multiple plates: the TOPMOST closure is the upper datum
    plate, tof, why = _reachable_scale(
        {"datum_lines": ["TOP_OF_PLATE@13.9", "TOP_OF_PLATE@26.5",
                         "TOP_OF_FOUNDATION@34.2"]})
    assert plate == 13.9 and tof == 34.2
    # either endpoint missing → HEIGHT only, named
    _, _, why = _reachable_scale({"datum_lines": ["TOP_OF_PLATE@20.0"]})
    assert "TOP OF FOUNDATION not located" in why
    assert "no drawn gap" in why
    _, _, why = _reachable_scale({"datum_lines": []})
    assert "TOP OF PLATE" in why and "TOP OF FOUNDATION" in why


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
                        "customer_name": "ZZ TEST_send104 TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send104-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_deletion_ledger.delete_many({"estimate_id": eid})
    db.zone_correction_events.delete_many({"estimate_id": eid})
    db.human_dimensions.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def test_live_card_wording_exactly_as_ruled(sess, rig):
    r = sess.get(f"{API}/estimates/{rig['eid']}/pdf-overlay/height-cards",
                 timeout=120)
    assert r.status_code == 200
    cards = r.json()["cards"]
    assert cards
    for c in cards:
        assert c["tape_points"]["label"] == (
            "Measure from the top of the foundation to the bottom of "
            "the soffit.")


def test_live_reachable_tape_governs_height_and_scale(sess, rig):
    """Letrick rear: contested 9'-11" vs 9'-1⅛"; TOF and plate are both
    drawn (plate y 65.9, TOF y 76.3). A TOF→soffit tape governs the
    sided height directly AND calibrates the rear scale — TEST FIGURE
    9'-6", not Howard's measurement."""
    eid = rig["eid"]
    r = sess.post(f"{API}/estimates/{eid}/pdf-overlay/tape",
                  json={"face_id": "back", "text": "9-6",
                        "ref_from": "top_of_foundation",
                        "ref_to": "bottom_of_soffit"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tape"]["resolves"] == "height+scale"
    assert "SIDED HEIGHT directly" in d["statement"]
    assert "AND this face's SCALE" in d["statement"]
    assert "contested rails" in d["statement"]   # contestants kept
    rp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                   timeout=240)
    assert rp.status_code == 200, rp.text
    out = rp.json()
    back = next(p for p in out["proposed"] if p["face_id"] == "back")
    pf = back["proposed_from"]
    assert back["tier"] == "taped_human"
    assert pf["height_ft"] == 9.5
    assert pf["height_source"].startswith(
        "TAPED (top of foundation → bottom of soffit)")
    assert "no conversion into DP-1's band" in pf["height_source"]
    assert pf["scale_source"].startswith("TAPED — calibrated over")
    assert "difference recorded, not decided" in pf["scale_source"]
    assert "CALIBRATES this face's scale" in back["basis"]
    assert "this face alone, never another (Ruling AAA)" in back["basis"]
    assert "Kept in the record" in back["basis"]
    t = out["tapes"]["back"]
    assert t["governs"] is True
    assert "height AND scale" in t["statement"]
    assert "both contestants kept in the record" in t["statement"]


def test_live_taped_scale_stays_on_its_own_face(sess, rig):
    """SEND-104 item 3 pin — a tape on REAR calibrates REAR ALONE. The
    other three faces stay on DP-1 FALLBACK, stated, with no TAPED
    wording anywhere on them."""
    eid = rig["eid"]
    rp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                   timeout=240)
    assert rp.status_code == 200, rp.text
    out = rp.json()
    assert set(out.get("tapes") or {}) == {"back"}
    for p in out["proposed"]:
        fid = p["face_id"]
        if fid.startswith(("chase:", "gable:")) or fid == "back":
            continue
        pf = p["proposed_from"]
        assert pf["scale_source"].startswith("DP-1 FALLBACK"), fid
        assert pf["height_source"].startswith("DP-1 FALLBACK"), fid
        assert "TAPED" not in (p["basis"] or ""), fid
        assert p["tier"] != "taped_human", fid
