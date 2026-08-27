"""SEND-132 PINS — ONE EDITOR, TWO STAGES (Howard ruled 2026-08-26).

Annotate's capabilities move INTO PhotoTakeoffEditor. Two stages in one
editor, not two apps. What these pins hold:

  1. THE STAGE IS PER PHOTO. A completed read on another photo unlocks
     nothing here — Stage 2 and the proposals refuse BY NAME.
  2. THE STAGE-2 PULL TAKES EVERY KIND THE READ PRODUCED, and says
     plainly which kinds the read produces none of. NOTHING IS INVENTED
     to fill the gap — no wall proposal the read never made.
  3. THE PULL IS IDEMPOTENT per (run_id, mark ref) — a second pull adds
     nothing.
  4. GUIDANCE AND EVIDENCE STAY DISTINCT. Confirming the contractor's
     own Stage 1 mark does NOT launder it into "checked after AI": the
     origin survives, the basis says GUIDANCE-CONFIRMED, and the
     quantity payload reports the count.
  5. A CONFIRM STILL NEEDS A SCALE — no anchor and no tape is a named
     refusal, never a 0.
  6. A PRODUCT CHANGE IS RECORDED AND DOES NOT DROP THE MARK. The
     history row carries from → to, when, who, and the ft² at the
     moment of the swap; the basis keeps `confirmed_under_product` and
     names the divergence.
  7. ONLY BODY-SIDING PRODUCTS ALREADY ON THE JOB may ride a zone.
  8. THE ANNOTATOR'S CLAIMS COME ACROSS INTACT — style and typed height
     arrive with the imported mark, provisional.

All live HTTP. Writes land on a DISPOSABLE estimate with a CLONED read;
cleanup always runs. No real estimate is touched.
"""
import sys
import uuid
from pathlib import Path

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API  # env-derived
from creds_for_tests import TEST_PASSWORD

# the source read to clone (real estimate, READ ONLY — never written)
SRC_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"
SRC = Path("/app/backend/routes/photo_takeoff.py")


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
    """A disposable estimate carrying a CLONE of a real photo read, plus
    a body-siding product line so the product picker has something real
    to offer."""
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"],
                     serverSelectionTimeoutMS=2000)[os.environ["DB_NAME"]]
    src = db.ai_measure_runs.find_one(
        {"estimate_id": SRC_EST, "status": "done"},
        sort=[("created_at", -1)])
    if not src:
        pytest.skip("env:fixture_data: no completed photo read to clone")
    names = [n for n in str(src.get("photo_paths") or "").split(",") if n]
    ops = [o for o in
           (((src.get("result") or {}).get("raw_ai") or {}).get("openings") or [])
           if isinstance(o, dict) and isinstance(o.get("bbox"), dict)
           and float(o["bbox"].get("w") or 0) > 0]
    if not names or not ops:
        pytest.skip("env:fixture_data: the read carries no boxed openings")
    from PIL import Image
    from config import UPLOAD_DIR
    if not (UPLOAD_DIR / names[0]).exists():
        pytest.skip("env:fixture_data: the read's first photo is not on disk")
    with Image.open(UPLOAD_DIR / names[0]) as im:
        nat = im.size
    r = sess.post(f"{API}/estimates",
                  json={"kind": "lp_smart",
                        "customer_name": "ZZ TEST_send132-two-stage TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    est = r.json()
    eid = est["id"]
    est["lines"] = [
        {"tab": "lp_smart", "section": "LP Smart Siding",
         "name": 'TEST 38 Series Lap 3/8" x 8" x 16\'', "unit": "PCS",
         "qty": 100.0},
        {"tab": "lp_smart", "section": "LP Smart Siding",
         "name": "TEST Board & Batten Panel", "unit": "PCS", "qty": 10.0},
        {"tab": "lp_smart", "section": "LP Siding Accessories",
         "name": "TEST J blocks", "unit": "Each", "qty": 4.0},
    ]
    assert sess.put(f"{API}/estimates/{eid}", json=est,
                    timeout=15).status_code == 200
    clone = dict(src)
    clone.pop("_id", None)
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send132-{uuid.uuid4().hex[:8]}"
    clone["test_artifact"] = True
    db.ai_measure_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"],
           "photo": names[0], "other_photo": "TEST_send132_unread_photo.jpg",
           "openings_on_photo0": [
               o for o in ops
               if (o.get("bbox_photo_idx") == 0
                   or (o.get("bbox_photo_idx") is None
                       and o.get("photo_idx") == 0))],
           "nat": nat}
    db.ai_measure_runs.delete_many({"run_id": clone["run_id"]})
    db.photo_takeoff_marks.delete_many({"estimate_id": eid})
    db.photo_takeoff_scale.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def _box(x, y, w, h):
    return [{"x": x, "y": y}, {"x": x + w, "y": y},
            {"x": x + w, "y": y + h}, {"x": x, "y": y + h}]


def _get(sess, eid, photo):
    r = sess.get(f"{API}/estimates/{eid}/photo-takeoff",
                 params={"photo_key": photo}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


def _photo(sess, eid, photo):
    return (_get(sess, eid, photo)["per_photo"] or {}).get(photo) or {}


def _wipe(sess, eid, photo):
    for m in _get(sess, eid, photo)["marks"]:
        sess.delete(f"{API}/estimates/{eid}/photo-takeoff/marks/{m['id']}",
                    timeout=15)
    sess.put(f"{API}/estimates/{eid}/photo-takeoff/scale",
             json={"photo_key": photo, "clear": True}, timeout=15)


def _scale(sess, eid, photo, inches=100.0):
    r = sess.put(f"{API}/estimates/{eid}/photo-takeoff/scale",
                 json={"photo_key": photo,
                       "anchor": {"p1": {"x": 0, "y": 0},
                                  "p2": {"x": 100, "y": 0},
                                  "inches": inches}}, timeout=15)
    assert r.status_code == 200, r.text


def _add(sess, eid, **kw):
    return sess.post(f"{API}/estimates/{eid}/photo-takeoff/marks",
                     json=kw, timeout=15)


# ── PIN 1 — THE STAGE IS PER PHOTO ───────────────────────────────────
def test_the_stage_is_per_photo_and_an_unread_photo_stays_stage_one(sess, rig):
    body = _get(sess, rig["eid"], rig["photo"])
    read_photo = (body["per_photo"] or {})[rig["photo"]]
    assert read_photo["stage"] == 2, read_photo
    assert read_photo["ai_read"] and read_photo["ai_read"]["run_id"] == rig["run_id"]
    assert read_photo["proposals_refusal"] is None
    other = _photo(sess, rig["eid"], rig["other_photo"])
    assert other["stage"] == 1, (
        "a read that never carried this photo unlocked Stage 2 on it")
    assert other["ai_read"] is None
    assert "unlocks nothing on this one" in (other["proposals_refusal"] or "")
    assert "GUIDANCE" in (other["stage_note"] or "")


def test_proposals_refuse_by_name_on_a_photo_with_no_read(sess, rig):
    r = sess.post(f"{API}/estimates/{rig['eid']}/photo-takeoff/propose",
                  params={"photo_key": rig["other_photo"]}, timeout=20)
    assert r.status_code == 400, r.text
    d = r.json()["detail"]
    assert "no completed AI read carries this photo" in d
    assert "unlocks nothing on this one" in d


# ── PIN 2 + 3 — THE PULL: EVERY KIND THE READ MADE, IDEMPOTENT ───────
def test_the_pull_takes_the_reads_own_marks_and_names_what_it_lacks(sess, rig):
    _wipe(sess, rig["eid"], rig["photo"])
    r = sess.post(f"{API}/estimates/{rig['eid']}/photo-takeoff/propose",
                  params={"photo_key": rig["photo"]}, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["run_id"] == rig["run_id"]
    assert b["proposed"] == len(rig["openings_on_photo0"]), (
        f"{b['proposed']} proposed vs {len(rig['openings_on_photo0'])} boxed "
        "openings the read placed on this photo")
    assert b["proposed"] > 0
    # EVERY PROPOSAL IS PROVISIONAL AND CARRIES ITS PROVENANCE
    for m in b["marks"]:
        assert m["status"] == "provisional"
        assert m["origin"] == "ai_proposal"
        assert m["stage"] == 2
        assert "AI PROPOSAL" in m["basis"]
        assert m["ai"]["run_id"] == rig["run_id"] and m["ai"]["ref_id"]
        # placed in THIS photo's own natural pixels, inside the frame
        xs = [p["x"] for p in m["points"]]
        ys = [p["y"] for p in m["points"]]
        assert 0 <= min(xs) and max(xs) <= rig["nat"][0] + 1, (m["points"], rig["nat"])
        assert 0 <= min(ys) and max(ys) <= rig["nat"][1] + 1
    # the read's own style / size claims come across
    assert any(m.get("style") for m in b["marks"]), (
        "the read's style claims were dropped")
    assert any(m.get("width_in") for m in b["marks"])
    # WHAT THE READ DOES NOT PRODUCE IS SAID PLAINLY, NOT INVENTED
    for kind in ("siding_zone", "non_siding_zone"):
        assert kind in b["kinds_absent"], kind
        assert "NO" in b["kinds_absent"][kind]
        assert "invented" in b["kinds_absent"][kind] or "yourself" in b["kinds_absent"][kind]
    assert all(m["kind"] == "opening" for m in b["marks"]), (
        "a zone proposal appeared from a read that produces no zone "
        "geometry — that would be an invented wall")


def test_the_pull_is_idempotent(sess, rig):
    before = len(_get(sess, rig["eid"], rig["photo"])["marks"])
    r = sess.post(f"{API}/estimates/{rig['eid']}/photo-takeoff/propose",
                  params={"photo_key": rig["photo"]}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["proposed"] == 0, (
        "a second pull duplicated the read's proposals")
    assert len(_get(sess, rig["eid"], rig["photo"])["marks"]) == before


def test_an_opening_the_read_could_not_box_is_named_never_placed(sess, rig):
    """An opening the read placed on this photo with no box cannot be
    drawn. It is NAMED and left to the hand — never dropped at a guessed
    spot."""
    src = SRC.read_text()
    assert "openings_without_a_box" in src
    assert "NOT placed at a guessed" in src


# ── PIN 4 — GUIDANCE NEVER LAUNDERS INTO EVIDENCE ────────────────────
def test_confirming_a_stage_one_mark_keeps_its_guidance_provenance(sess, rig):
    photo = rig["other_photo"]           # no read on this photo → Stage 1
    _wipe(sess, rig["eid"], photo)
    _scale(sess, rig["eid"], photo)
    r = _add(sess, rig["eid"], photo_key=photo, kind="siding_zone",
             points=_box(0, 0, 120, 120))
    assert r.status_code == 200, r.text
    m = r.json()["mark"]
    assert m["origin"] == "contractor_stage1" and m["stage"] == 1
    assert "GUIDANCE" in m["basis"]
    r = sess.patch(
        f"{API}/estimates/{rig['eid']}/photo-takeoff/marks/{m['id']}",
        json={"status": "confirmed"}, timeout=15)
    assert r.status_code == 200, r.text
    got = r.json()["mark"]
    assert got["origin"] == "contractor_stage1", (
        "the confirm rewrote the origin — a Stage 1 mark was laundered "
        "into 'checked after AI'")
    assert got["confirmed_stage"] == 1
    assert got["confirmed_after_ai_read"] is False
    assert "GUIDANCE-CONFIRMED" in got["confirmed_basis"]
    assert "NOT evidence" in got["confirmed_basis"]
    q = _photo(sess, rig["eid"], photo)["quantities"]
    assert q["siding_sqft"] == 100.0, "the guidance confirm wrote no quantity"
    assert q["guidance_confirmed"] == 1
    assert "NOT evidence" in (q["guidance_confirmed_note"] or "")


def test_a_confirmed_ai_proposal_is_evidence(sess, rig):
    photo = rig["photo"]
    _scale(sess, rig["eid"], photo)
    marks = [m for m in _get(sess, rig["eid"], photo)["marks"]
             if m["origin"] == "ai_proposal"]
    assert marks, "no AI proposal to confirm"
    r = sess.patch(
        f"{API}/estimates/{rig['eid']}/photo-takeoff/marks/{marks[0]['id']}",
        json={"status": "confirmed"}, timeout=15)
    assert r.status_code == 200, r.text
    got = r.json()["mark"]
    assert got["origin"] == "ai_proposal"
    assert got["confirmed_stage"] == 2
    assert got["confirmed_after_ai_read"] is True
    assert got["confirmed_basis"].startswith("EVIDENCE")
    q = _photo(sess, rig["eid"], photo)["quantities"]
    assert not q["guidance_confirmed"], (
        "an AI-proposal confirm was counted as guidance")


# ── PIN 5 — A CONFIRM STILL NEEDS A SCALE ────────────────────────────
def test_a_confirm_with_no_scale_is_a_named_refusal(sess, rig):
    photo = rig["other_photo"]
    _wipe(sess, rig["eid"], photo)
    mid = _add(sess, rig["eid"], photo_key=photo, kind="siding_zone",
               points=_box(0, 0, 120, 120)).json()["mark"]["id"]
    r = sess.patch(f"{API}/estimates/{rig['eid']}/photo-takeoff/marks/{mid}",
                   json={"status": "confirmed"}, timeout=15)
    assert r.status_code == 400, (
        "a mark was confirmed on a photo with no anchor and no tape")
    assert "no scale on this photo" in r.json()["detail"]


# ── PIN 6 + 7 — THE PRODUCT ──────────────────────────────────────────
def test_only_a_body_product_already_on_the_job_may_ride_a_zone(sess, rig):
    body = _get(sess, rig["eid"], rig["photo"])
    names = [p["name"] for p in body["products"]]
    assert 'TEST 38 Series Lap 3/8" x 8" x 16\'' in names
    assert "TEST Board & Batten Panel" in names
    assert not any("J blocks" in n for n in names), (
        "an ACCESSORY was offered as a body-siding product")
    r = _add(sess, rig["eid"], photo_key=rig["other_photo"],
             kind="siding_zone", points=_box(0, 0, 10, 10),
             product="Cedar Impressions Perfection Shingle")
    assert r.status_code == 400, (
        "a product the job does not carry was accepted on a zone")
    assert "not a body-siding product on this job" in r.json()["detail"]


def test_a_product_change_is_recorded_and_does_not_drop_the_confirmation(sess, rig):
    photo = rig["other_photo"]
    _wipe(sess, rig["eid"], photo)
    _scale(sess, rig["eid"], photo)
    lap = 'TEST 38 Series Lap 3/8" x 8" x 16\''
    bnb = "TEST Board & Batten Panel"
    mid = _add(sess, rig["eid"], photo_key=photo, kind="siding_zone",
               points=_box(0, 0, 120, 120), product=lap).json()["mark"]["id"]
    sess.patch(f"{API}/estimates/{rig['eid']}/photo-takeoff/marks/{mid}",
               json={"status": "confirmed"}, timeout=15)
    q = _photo(sess, rig["eid"], photo)["quantities"]
    assert q["siding_by_product"] == {lap: 100.0}, q["siding_by_product"]
    # THE SWAP: output changes, geometry does not
    r = sess.patch(f"{API}/estimates/{rig['eid']}/photo-takeoff/marks/{mid}",
                   json={"product": bnb}, timeout=15)
    assert r.status_code == 200, r.text
    m = r.json()["mark"]
    assert m["status"] == "confirmed", (
        "a product change dropped the mark to provisional — it alters the "
        "output, not the geometry")
    assert m["product"] == bnb
    assert m["confirmed_under_product"] == lap, (
        "the basis lost the product the quantity was confirmed under")
    hist = m["product_history"]
    assert len(hist) == 1, hist
    row = hist[0]
    assert row["from"] == lap and row["to"] == bnb
    assert row["at"] and row["by"]
    assert row["sqft_at_swap"] == 100.0, row
    q = _photo(sess, rig["eid"], photo)["quantities"]
    assert q["siding_by_product"] == {bnb: 100.0}
    note = " ".join(q["product_basis_notes"] or [])
    assert f"confirmed under {lap!r}" in note and f"now assigned {bnb!r}" in note
    assert "the geometry did not change; the output did" in note
    # and geometry STILL drops it — the two rules do not blur
    r = sess.patch(f"{API}/estimates/{rig['eid']}/photo-takeoff/marks/{mid}",
                   json={"points": _box(0, 0, 240, 240)}, timeout=15)
    assert r.json()["mark"]["status"] == "provisional"


# ── PIN 8 — THE ANNOTATOR'S CLAIMS COME ACROSS INTACT ────────────────
def test_the_import_carries_kind_style_and_height(sess, rig):
    photo = rig["other_photo"]
    _wipe(sess, rig["eid"], photo)
    ann = {photo: {
        "elevation": "left",
        "zones": [{"id": "z-1", "kind": "rect", "category": "stone",
                   "points": _box(10, 10, 60, 60)}],
        "windows": [{"id": "w-1", "x": 300, "y": 200, "style": "2-Lite Slider",
                     "width_in": 48, "height_in": 36}],
    }}
    assert sess.put(f"{API}/measure/sessions/{rig['eid']}",
                    json={"estimate_id": rig["eid"], "photo_urls": [photo],
                          "photo_annotations": ann},
                    timeout=15).status_code == 200
    r = sess.post(
        f"{API}/estimates/{rig['eid']}/photo-takeoff/import-annotations",
        params={"photo_key": photo}, timeout=20)
    assert r.status_code == 200, r.text
    marks = r.json()["marks"]
    assert len(marks) == 2, marks
    win = next(m for m in marks if m["kind"] == "opening")
    zone = next(m for m in marks if m["kind"] == "non_siding_zone")
    assert win["style"] == "2-Lite Slider", "the window STYLE was dropped"
    assert win["height_in"] == 36 and win["width_in"] == 48, (
        "the typed window size was dropped")
    assert zone["category"] == "stone"
    for m in (win, zone):
        assert m["status"] == "provisional"
        assert m["origin"] == "imported_annotation"
        assert "GUIDANCE" in m["basis"]
    assert r.json()["imported"] == 2
    r2 = sess.post(
        f"{API}/estimates/{rig['eid']}/photo-takeoff/import-annotations",
        params={"photo_key": photo}, timeout=20)
    assert r2.json()["imported"] == 0, "the import is not idempotent"


# ── THE SURFACE ──────────────────────────────────────────────────────
FE = Path("/app/frontend/src")
EDITOR = (FE / "components" / "estimate" / "PhotoTakeoffEditor.jsx").read_text()


def test_the_editor_renders_both_stages_in_one_surface():
    for tid in ("photo-takeoff-stage-banner", "photo-takeoff-propose-btn",
                "photo-takeoff-style-input", "photo-takeoff-height-in",
                "photo-takeoff-product-select", "photo-takeoff-qty-by-product"):
        assert tid in EDITOR, tid
    # the two stages are NAMED on the surface, guidance vs evidence
    assert "GUIDANCE" in EDITOR and "EVIDENCE" in EDITOR
    assert "stage_note" in EDITOR
    assert "proposals_refusal" in EDITOR, (
        "the disabled-proposals reason is not shown — a dead button with "
        "no reason is exactly what the rail exists to prevent")
    # per-mark provenance badge
    assert "photo-takeoff-origin-" in EDITOR


def test_the_editor_never_offers_a_product_it_was_not_given():
    """The picker renders the server's `products` list and nothing else —
    no catalog, no hardcoded profile name."""
    assert "products" in EDITOR
    for invented in ("Cedar Impressions", "Charter Oak", "Ascend",
                     "Dutch Lap", "38 Series"):
        assert invented not in EDITOR, (
            f"{invented!r} is hardcoded in the editor — the picker offers "
            "only what the job carries")
