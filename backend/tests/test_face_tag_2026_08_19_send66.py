"""SEND-66 pins — FACE-TAG FIX (P0 money bug).

Howard's ruling: a human zone's face resolves from its CENTROID'S
ELEVATION BAND on that page, not the page tag. Straddling two bands or
sitting in no band → the write is NOT GUESSED: the API returns the
ambiguity and the UI asks. INVARIANT (outlives the handler): a zone
whose tag and centroid disagree must never bind silently, on any path.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from routes.pdf_overlay import resolve_face_from_bands  # noqa: E402

BANDS = {"front": (0.0, 45.0), "rear": (45.0, 90.0)}


def _rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def test_face_resolves_from_centroid_band_not_the_tag():
    r = resolve_face_from_bands(BANDS, _rect(0.2, 0.55, 0.6, 0.85),
                                "front")
    assert r["status"] == "RESOLVED"
    assert r["resolved_face_id"] == "back"      # rear band → back id
    assert r["disagrees"] is True


def test_agreement_is_recorded_not_assumed():
    r = resolve_face_from_bands(BANDS, _rect(0.2, 0.05, 0.6, 0.40),
                                "front")
    assert r["status"] == "RESOLVED"
    assert r["resolved_face_id"] == "front"
    assert r["disagrees"] is False


def test_zone_across_two_bands_is_ambiguous_and_says_why():
    r = resolve_face_from_bands(BANDS, _rect(0.2, 0.30, 0.6, 0.60),
                                "front")
    assert r["status"] == "AMBIGUOUS"
    assert "FRONT" in r["reason"] and "REAR" in r["reason"]
    assert "across" in r["reason"]
    assert set(r["candidates"]) == {"front", "back"}


def test_centroid_in_no_band_is_ambiguous_never_defaulted():
    r = resolve_face_from_bands(BANDS, _rect(0.2, 0.92, 0.6, 0.99),
                                "front")
    assert r["status"] == "AMBIGUOUS"
    assert "no elevation drawing" in r["reason"]
    assert set(r["candidates"]) == {"front", "back"}


def test_gable_tag_keeps_its_surface_kind_when_the_face_flips():
    r = resolve_face_from_bands(BANDS, _rect(0.2, 0.50, 0.6, 0.60),
                                "gable:front")
    assert r["status"] == "RESOLVED"
    assert r["resolved_face_id"] == "gable:back"


def test_ambiguous_candidates_carry_the_gable_kind():
    r = resolve_face_from_bands(BANDS, _rect(0.2, 0.30, 0.6, 0.60),
                                "gable:front")
    assert set(r["candidates"]) == {"gable:front", "gable:back"}


def test_no_bands_on_page_means_the_tag_stands():
    r = resolve_face_from_bands({}, _rect(0.2, 0.3, 0.6, 0.6), "front")
    assert r["status"] == "NO_BANDS"


def test_dormer_zones_carry_no_elevation_face():
    r = resolve_face_from_bands(BANDS, _rect(0.2, 0.5, 0.6, 0.6),
                                "dormer:shed")
    assert r["status"] == "NO_BANDS"


def test_invariant_the_human_write_path_resolves_never_binds_the_raw_tag():
    """The pin that outlives the fix: the upsert (the only human write
    door to pdf_overlay_polygons) resolves the face through the band
    machinery, and the stored face_id is the RESOLVED one — the raw
    payload tag is never written as the binding face."""
    with open("/app/backend/routes/pdf_overlay.py", encoding="utf-8") as f:
        src = f.read()
    assert "resolve_face_from_bands(" in src
    assert '"face_id": payload.face_id' not in src
    assert '"face_resolution": face_resolution' in src
    # and pdf_overlay_polygons is written from this module only —
    # no other path can bind a zone around the resolution. The one
    # exception is the authorized EST-886440 MUV-rebuild duplicator,
    # which CLONES existing docs verbatim (tag↔centroid consistency is
    # preserved by construction — it never assigns a face).
    import glob
    hits = []
    for path in glob.glob("/app/backend/**/*.py", recursive=True):
        if "/tests/" in path:
            continue
        with open(path, encoding="utf-8") as f:
            s = f.read()
        if ("pdf_overlay_polygons.insert_one" in s
                or "pdf_overlay_polygons.replace_one" in s):
            hits.append(path)
    clone_script = "/app/backend/scripts/duplicate_est886440_muv_rebuild.py"
    assert sorted(hits) == sorted(["/app/backend/routes/pdf_overlay.py",
                                   clone_script])
    with open(clone_script, encoding="utf-8") as f:
        s = f.read()
    assert '"face_id"' not in s and "'face_id'" not in s


# ---------------------------------------------------------------------------
# live pins — cloned blueprint run under a disposable estimate
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
                        "customer_name": "ZZ TEST_send66 TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send66-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    raw = ((clone.get("result") or {}).get("raw_ai") or {})
    ot = raw.get("_ocr_text_by_page")
    if not ot and raw.get("_ocr_text_ref"):
        ref = db.ai_blueprint_ocr.find_one(
            {"run_id": raw["_ocr_text_ref"]}, {"_id": 0, "pages": 1})
        ot = (ref or {}).get("pages")
    from height_read import elevation_page_faces
    pages = elevation_page_faces(ot or {})
    combo = next((pg for pg, b in pages.items() if len(b) >= 2), None)
    if not combo:
        pytest.skip("env:fixture_data: no combined face sheet on the run")
    yield {"eid": eid, "db": db, "run_id": clone["run_id"],
           "page": combo, "bands": pages[combo]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_correction_events.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def _put(sess, eid, page, face_id, verts, face_confirmed=False):
    return sess.put(f"{API}/estimates/{eid}/pdf-overlay", json={
        "page": int(page), "face_id": face_id, "material_class": "siding",
        "vertices_pct": verts, "provenance": "human",
        "face_confirmed": face_confirmed}, timeout=30)


def test_live_mis_tagged_zone_binds_to_the_bands_face_and_records_it(
        sess, rig):
    faces = sorted(rig["bands"].items(), key=lambda kv: kv[1][0])
    tag_face, _ = faces[0]
    other_face, (b0, b1) = faces[1]
    mid = (b0 + b1) / 200.0
    h = (b1 - b0) / 1000.0
    from routes.pdf_overlay import _BAND_FACE_TO_ID
    r = _put(sess, rig["eid"], rig["page"], _BAND_FACE_TO_ID[tag_face],
             _rect(0.30, mid - h, 0.50, mid + h))
    assert r.status_code == 200, r.text
    poly = r.json()["polygon"]
    assert poly["face_id"] == _BAND_FACE_TO_ID[other_face]
    fr = poly["face_resolution"]
    assert fr["method"] == "centroid_band"
    assert fr["disagreed_with_tag"] is True
    assert fr["submitted_face_id"] == _BAND_FACE_TO_ID[tag_face]


def test_live_straddling_zone_409s_then_binds_on_explicit_choice(
        sess, rig):
    faces = sorted(rig["bands"].items(), key=lambda kv: kv[1][0])
    (_, (a0, a1)), (_, (c0, c1)) = faces[0], faces[1]
    verts = _rect(0.30, (a0 + a1) / 200.0, 0.50, (c0 + c1) / 200.0)
    r = _put(sess, rig["eid"], rig["page"], "front", verts)
    assert r.status_code == 409, r.text
    d = r.json()["detail"]
    assert d["code"] == "FACE_AMBIGUOUS"
    assert "across" in d["reason"]
    assert len(d["candidates"]) >= 2
    r2 = _put(sess, rig["eid"], rig["page"], d["candidates"][0], verts,
              face_confirmed=True)
    assert r2.status_code == 200, r2.text
    poly = r2.json()["polygon"]
    assert poly["face_id"] == d["candidates"][0]
    assert poly["face_resolution"]["method"] == "human_choice_on_ambiguity"
