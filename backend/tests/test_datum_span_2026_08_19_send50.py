"""SEND-50 item 3 pins — proposal geometry from the datum pair, never the
band.

Census finding (2026-08-19, both houses, reported before this fix): the
measured datum marker span lands consistently ~+20 ft WIDE of Howard's
sealed readings (Letrick +19.2/+20.0/+20.4; Boni +23.6/+24.5/+20.1) —
the labels sit at the end of leader lines outside the wall. The offset is
the FINDING and is NOT subtracted: no constant is guessed, no threshold
admitted. The old proposal (x = 2..98% of the whole page) landed +70..+93
ft wide; the datum span is the wall's evidence-grounded extent.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from height_read import datum_lines, datum_span_x  # noqa: E402


# ---------------------------------------------------------------------------
# datum_span_x — the span rule itself (RULING ZZ: inner edge to inner edge)
# ---------------------------------------------------------------------------
def test_two_corner_markers_span_inner_edge_to_inner_edge():
    line = {"markers": [[6.7, 10.2], [60.4, 63.6], [7.1, 10.1]]}
    assert datum_span_x(line) == [10.2, 60.4]


def test_single_marker_is_indeterminate():
    assert datum_span_x({"markers": [[8.6, 11.8]]}) is None


def test_two_reads_of_the_same_corner_are_one_end_not_a_span():
    # The Letrick LEFT shape: two TOP OF PLATE boxes, both at the right
    # corner, x-overlapping. A 4.7% "span" is a label width, not a wall.
    assert datum_span_x({"markers": [[46.2, 50.9], [47.6, 50.8]]}) is None


def test_no_markers_is_indeterminate():
    assert datum_span_x({"markers": []}) is None
    assert datum_span_x({}) is None


def test_span_never_extrapolates_beyond_the_marker_boxes():
    span = datum_span_x({"markers": [[10.0, 13.0], [50.0, 53.0]]})
    assert span == [13.0, 50.0]  # inner edges exactly — no symmetry, no pad


def test_ruling_zz_the_label_box_is_never_inside_the_span():
    """A label's glyph box is not the wall by construction (Ruling ZZ):
    the span excludes BOTH label widths entirely."""
    span = datum_span_x({"markers": [[10.0, 13.0], [50.0, 53.0]]})
    assert span[0] >= 13.0 and span[1] <= 50.0


def test_ruling_aaa_registered_no_proposal_borrows_another_drawing():
    from ocr_geometry import RULINGS_REGISTER
    assert any("RULING AAA" in s for s in RULINGS_REGISTER["sealed"])
    aaa = next(s for s in RULINGS_REGISTER["sealed"] if "RULING AAA" in s)
    assert "own evidence" in aaa


def test_single_corner_faces_registered_as_a_permanent_limit():
    from ocr_geometry import RULINGS_REGISTER
    assert any("single corner" in s for s in RULINGS_REGISTER["findings"])


def test_leader_offset_limit_registered():
    from ocr_geometry import RULINGS_REGISTER
    assert any("LEADER-OFFSET LIMIT" in s
               for s in RULINGS_REGISTER["findings"])


# ---------------------------------------------------------------------------
# datum_lines — marker boxes ride the merged line
# ---------------------------------------------------------------------------
def _run(text, x, y, w=3.4, h=0.8):
    return {"raw": text, "loc": {"x_pct": x, "y_pct": y,
                                 "w_pct": w, "h_pct": h}}


def test_merged_datum_line_keeps_both_corner_markers():
    runs = [_run("TOP OF PLATE", 7.0, 20.0),
            _run("TOP OF PLATE", 60.0, 20.1)]
    lines = datum_lines(runs, 0.0, 100.0, {})
    assert len(lines) == 1
    L = lines[0]
    assert len(L["markers"]) == 2
    assert datum_span_x(L) == [10.4, 60.0]


def test_non_overlapping_same_label_lines_stay_separate_each_single_ended():
    runs = [_run("TOP OF PLATE", 7.0, 20.0),
            _run("TOP OF PLATE", 7.0, 40.0)]
    lines = datum_lines(runs, 0.0, 100.0, {})
    assert len(lines) == 2
    assert all(datum_span_x(L) is None for L in lines)


# ---------------------------------------------------------------------------
# live pins — proposals draw the datum box, not the band (cloned Letrick
# run under a DISPOSABLE estimate; cleanup always runs)
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
                        "customer_name": "ZZ TEST_datum-span TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_span-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"], "src": src}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def _face_spans_from_run(src):
    from height_read import derive_face_heights
    raw = ((src.get("result") or {}).get("raw_ai") or {})
    ot = raw.get("_ocr_text_by_page")
    assert ot, "cloned run must carry OCR"
    faces = derive_face_heights(ot)
    out = {}
    for face, r in faces.items():
        if r.get("status") != "DERIVED":
            continue
        geo = r.get("datum_geometry") or {}
        spans = [d["span_x"] for d in
                 (geo.get("top_of_plate"), geo.get("first_floor"))
                 if d and d.get("span_x")]
        if spans:
            geo = r.get("datum_geometry") or {}
            y_bot = r["span_y"][1] / 100.0
            tof = geo.get("top_of_foundation") or {}
            if tof.get("y") and tof["y"] / 100.0 > y_bot:
                y_bot = tof["y"] / 100.0  # SEND-63: proposal bottom at TOF
            out[face] = ([min(s[0] for s in spans) / 100.0,
                          max(s[1] for s in spans) / 100.0],
                         [r["span_y"][0] / 100.0, y_bot])
    return out


def test_proposals_draw_the_datum_box_not_the_band(sess, rig):
    r = sess.post(f"{API}/estimates/{rig['eid']}/pdf-overlay/propose",
                  timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    proposed = body["proposed"]
    expect = _face_spans_from_run(rig["src"])
    id_to_face = {"front": "front", "back": "rear",
                  "left": "left", "right": "right"}
    derived = [p for p in proposed if p.get("tier") == "derived_chain"
               # SEND-94: chase surfaces ride beside the body zones
               and not p["face_id"].startswith("chase:")]
    assert len(derived) == len(expect) > 0
    for p in derived:
        face = id_to_face[p["face_id"]]
        (x0, x1), (y0, y1) = expect[face]
        xs = sorted({v[0] for v in p["vertices_pct"]})
        ys = sorted({v[1] for v in p["vertices_pct"]})
        if p.get("geometry_tier") == "wall_outline":
            # SEND-69: the drawn outline OVERRIDES the datum span — the
            # span survives in proposed_from for comparison, disclosed.
            ds = (p.get("proposed_from") or {}).get("datum_span_x_pct")
            assert ds is not None
            assert abs(ds[0] - x0 * 100) < 1e-2
            assert abs(ds[1] - x1 * 100) < 1e-2
            assert "WALL OUTLINE" in (p.get("basis") or "")
        else:
            assert abs(xs[0] - x0) < 1e-6 and abs(xs[-1] - x1) < 1e-6, \
                f"{face}: x {xs} != datum span [{x0}, {x1}]"
            assert abs(ys[0] - min(y0, y1)) < 1e-6
            assert abs(ys[-1] - max(y0, y1)) < 1e-6
            basis = p.get("basis") or ""
            assert "datum marker span" in basis
        # never the old page-band rectangle
        assert xs[0] > 0.02 and xs[-1] < 0.98
    # body zone stops at the plate: y-extent is the datum pair, and the
    # proposal never reaches the band top (roof/gable stays out)
    for p in proposed:
        band = (p.get("proposed_from") or {}).get("band")
        ys = sorted({v[1] for v in p["vertices_pct"]})
        assert ys[0] > band[0] / 100.0
    # cleanup proposals written by this pin
    rig["db"].pdf_overlay_polygons.delete_many(
        {"estimate_id": rig["eid"], "provenance": "proposed"})


def test_indeterminate_span_face_still_proposes_naming_page_width(sess, rig):
    """Strip the right-corner FIRST FLOOR + TOP OF PLATE labels from one
    face's band in the clone → its span turns single-ended. Under the
    SEND-55 ladder the face STILL proposes (the refusing/unmeasured face
    is the one that most needs a starting shape) — but the x-extent
    falls to page width and the basis SAYS SO."""
    db = rig["db"]
    src = db.ai_blueprint_runs.find_one({"run_id": rig["run_id"]})
    raw = src["result"]["raw_ai"]
    ot = raw["_ocr_text_by_page"]
    from height_read import elevation_page_faces
    bands = elevation_page_faces(ot)
    # find the page+band of the derived face 'right'
    pg, (y0, y1) = next((pg, band) for pg, faces in bands.items()
                        for f, band in faces.items() if f == "right")
    page = ot[pg]
    kept = []
    import re as _re
    for run in page["runs"]:
        s = _re.sub(r"[^A-Z]", "", (run["raw"] or "").upper())
        cy = run["loc"]["y_pct"] + run["loc"]["h_pct"] / 2
        if (("TOPOFPLATE" in s or "FIRSTFLOOR" in s)
                and y0 <= cy <= y1 and run["loc"]["x_pct"] > 60):
            continue  # drop the right-corner labels only
        kept.append(run)
    page["runs"] = kept
    db.ai_blueprint_runs.update_one(
        {"run_id": rig["run_id"]},
        {"$set": {f"result.raw_ai._ocr_text_by_page.{pg}": page}})
    r = sess.post(f"{API}/estimates/{rig['eid']}/pdf-overlay/propose",
                  timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    right = next(p for p in body["proposed"] if p["face_id"] == "right")
    xs = sorted({v[0] for v in right["vertices_pct"]})
    assert right["tier"] == "datum_rectangle"
    assert "PAGE WIDTH" in (right.get("basis") or "")
    if right.get("geometry_tier") == "wall_outline":
        # SEND-69/71: line-work reads the VECTOR strokes and needs no
        # corner labels — the single-ended face is RESCUED by the drawn
        # outline instead of standing at page width. The page-width
        # datum basis is still named; the outline says what replaced it.
        assert xs[0] > 0.02 and xs[-1] < 0.98
        assert "WALL OUTLINE" in right["basis"]
    else:
        assert xs[0] == 0.02 and xs[-1] == 0.98
    rig["db"].pdf_overlay_polygons.delete_many(
        {"estimate_id": rig["eid"], "provenance": "proposed"})
