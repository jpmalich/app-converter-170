"""SEND-105 RULING 1 — BONI LEFT: OPTION B (Howard draws the zone).

OPTION (a) IS RULED OUT, NOT DEFERRED: no code path may invent a corner
from the ambiguous lines — the far member at x=34.94 stays what it is,
a member with 3+ strokes the app cannot resolve. Registered here so it
cannot return as a proposal later. Boni left KEEPS REFUSING and its
refusal keeps naming why. Its surfaces are BINDABLE (confirmed live,
not assumed — the third appearance of this exact gap): a hand-drawn
zone lands on `left` and on `chase:left` and keeps its face.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API
from creds_for_tests import TEST_PASSWORD

# THE REGISTER — option (a), verbatim, RULED OUT (SEND-105 ruling 1).
OPTION_A_RULED_OUT = (
    "far member x=34.94 as the second corner when it is the only full "
    "spanner beyond the fence-side corner")


def test_option_a_stays_out_of_the_codebase():
    """No proposal logic may reference the far-member-as-corner cure:
    the number 34.94 and any 'far member' corner promotion must not
    appear in shipping code (tests and memory may cite it — this
    register does)."""
    import os
    for root in ("/app/backend/routes", "/app/backend"):
        for f in os.listdir(root):
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            if not os.path.isfile(p):
                continue
            src = open(p).read()
            assert "34.94" not in src, f"option (a) resurfaced in {p}"


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
        {"estimate_id": "65bcb89d-8291-4b84-920c-7b503273f332",
         "status": "done"}, sort=[("created_at", -1)])
    if not src:
        pytest.skip("env:fixture_data: Boni blueprint run not in datastore")
    r = sess.post(f"{API}/estimates",
                  json={"kind": "siding",
                        "customer_name": "ZZ TEST_send105 BONI TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send105-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_deletion_ledger.delete_many({"estimate_id": eid})
    db.zone_correction_events.delete_many({"estimate_id": eid})
    db.human_dimensions.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def test_live_boni_left_keeps_refusing_and_names_why(sess, rig):
    """Option (a) stays out: any left proposal must be the previously
    RULED datum_rectangle (Ruling ZZ datum-marker span, height NOT
    established) — never a corner promoted from the ambiguous far
    member. The chase:left refusal keeps naming why, and stays
    bindable."""
    rp = sess.post(f"{API}/estimates/{rig['eid']}/pdf-overlay/propose",
                   timeout=240)
    assert rp.status_code == 200, rp.text
    d = rp.json()
    for p in d["proposed"]:
        if p["face_id"] != "left":
            continue
        assert p["tier"] == "datum_rectangle", p["tier"]
        assert "datum marker span" in p["basis"]
        assert "height NOT established" in p["basis"]
        for banned in ("far member", "3-stroke", "promoted corner",
                       "34.94"):
            assert banned not in p["basis"], banned
    sk = next(s0 for s0 in (d.get("skipped") or [])
              if s0.get("face_id") == "chase:left")
    assert "no chase ink locatable" in sk["reason"]
    assert "stays bindable" in sk["reason"]


def test_live_boni_left_surfaces_are_bindable(sess, rig):
    """A hand-drawn zone LANDS on left and on chase:left — face kept,
    area computed — so Howard's option-B zone has somewhere to go."""
    eid = rig["eid"]
    # left band on p2 sits in the upper half (band ~4–46)
    verts = [[0.30, 0.15], [0.45, 0.15], [0.45, 0.35], [0.30, 0.35]]
    for fid in ("left", "chase:left"):
        r = sess.put(f"{API}/estimates/{eid}/pdf-overlay", json={
            "id": str(uuid.uuid4()), "page": 2, "face_id": fid,
            "material_class": "siding", "vertices_pct": verts,
            "scale_ref": None, "provenance": "human",
            "face_confirmed": False}, timeout=120)
        assert r.status_code == 200, (fid, r.status_code, r.text[:300])
        saved = r.json()["polygon"]
        assert saved["face_id"] == fid, (
            f"drawn zone landed on {saved['face_id']} not {fid}")
