"""SEND-68 pins — GABLE STARTING SHAPES.

Howard's ruling: gables enter the propose loop as a band_rectangle-style
STARTING SHAPE stating plainly the triangle could not be read. NO
triangle computed from pitch and width. Bottom: TOP OF PLATE datum.
Top: top of the face's drawing band. Sides: the body zone's span.
LOWEST tier; the derived gable figure shown alongside; the strongest
divergence notice (a rectangle over a gable OVERSTATES it). Only faces
the roof read says carry a gable end get one.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")


def test_no_triangle_is_computed_from_pitch_and_width():
    """The 0.70 gable convention lives on the derived side and stays
    there — the propose path never imports or applies it."""
    with open("/app/backend/routes/pdf_overlay.py", encoding="utf-8") as f:
        src = f.read()
    assert "GABLE_FACTOR" not in src
    assert "gable_rise" not in src
    assert '"tier": "gable_rectangle"' in src


def test_gable_rectangle_is_the_lowest_tier():
    from routes.pdf_overlay import _TIER_RANK
    assert _TIER_RANK["gable_rectangle"] == max(_TIER_RANK.values())


# ---------------------------------------------------------------------------
# live pins — cloned run + walk detail carrying gables on two faces
# ---------------------------------------------------------------------------
from api_base import API  # noqa: E402
from creds_for_tests import TEST_PASSWORD  # noqa: E402


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
                        "customer_name": "ZZ TEST_send68 TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send68-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    # walk detail: LEFT derives a gable, RIGHT's gable refuses, the
    # front/back rows carry none — only gable-bearing faces propose one.
    db.estimates.update_one({"id": eid}, {"$set": {
        "hover_measurements": {"_wall_walk_detail": [
            {"label": "front", "gable_sqft": 0, "gable_refusal": None},
            {"label": "back", "gable_sqft": 0, "gable_refusal": None},
            {"label": "left", "gable_sqft": 183.75, "gable_refusal": None},
            {"label": "right", "gable_sqft": None,
             "gable_refusal": ("wall width not read — gable area not "
                               "derivable")},
        ]}}})
    resp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                     timeout=60)
    assert resp.status_code == 200, resp.text
    yield {"eid": eid, "db": db, "run_id": clone["run_id"],
           "proposed": resp.json()["proposed"],
           "skipped": resp.json()["skipped"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_correction_events.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def _by_face(rig):
    return {p["face_id"]: p for p in rig["proposed"]}


def test_live_only_gable_bearing_faces_get_a_gable_zone(rig):
    faces = set(_by_face(rig))
    assert "gable:left" in faces
    assert "gable:right" in faces
    assert "gable:front" not in faces
    assert "gable:back" not in faces


def test_live_gable_shape_bounds_and_basis(rig):
    g = _by_face(rig)["gable:left"]
    assert g["tier"] == "gable_rectangle"
    assert g["provenance"] == "proposed"
    assert g["sqft"] is None                 # feeds no quantity
    assert len(g["vertices_pct"]) == 4       # a rectangle, never a triangle
    body = _by_face(rig)["left"]
    # sides: the body zone's span, same basis
    assert (g["proposed_from"]["span_x_pct"]
            == body["proposed_from"]["span_x_pct"])
    # top: top of the face's drawing band
    band_top = g["proposed_from"]["band"][0] / 100.0
    ys = [v[1] for v in g["vertices_pct"]]
    assert abs(min(ys) - band_top) < 1e-6
    assert max(ys) > min(ys)                 # bottom (plate) below the top
    assert "TOP OF PLATE" in g["basis"]
    assert "top of this face's drawing band" in g["basis"]
    assert "ridge could not be read" in g["basis"]


def test_live_derived_gable_shown_alongside_with_overstate_notice(rig):
    g = _by_face(rig)["gable:left"]
    assert g["derived_gable_sqft"] == 183.75
    assert "183.75" in g["divergence_notice"]
    assert "OVERSTATE" in g["divergence_notice"]
    assert "pull it in to the roof line first" in g["divergence_notice"]


def test_live_refused_gable_names_the_refusal_and_still_warns(rig):
    g = _by_face(rig)["gable:right"]
    assert g["derived_gable_sqft"] is None
    assert "not derivable" in g["divergence_notice"]
    assert "OVERSTATE" in g["divergence_notice"]


def test_live_confirming_a_gable_retains_the_divergence_notice(sess, rig):
    g = _by_face(rig)["gable:left"]
    r = sess.put(f"{API}/estimates/{rig['eid']}/pdf-overlay", json={
        "id": g["id"], "page": g["page"], "face_id": g["face_id"],
        "material_class": g["material_class"],
        "vertices_pct": g["vertices_pct"], "scale_ref": g.get("scale_ref"),
        "page_w_px": g.get("page_w_px"), "page_h_px": g.get("page_h_px"),
        "provenance": "human"}, timeout=30)
    assert r.status_code == 200, r.text
    poly = r.json()["polygon"]
    cf = poly["confirmed_from"]
    assert cf["tier"] == "gable_rectangle"
    assert "OVERSTATE" in (cf.get("divergence_notice") or "")
    assert cf.get("derived_gable_sqft") == 183.75
