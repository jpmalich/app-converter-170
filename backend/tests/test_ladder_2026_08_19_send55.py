"""SEND-55 item 2 + item 4 pins — RULING BBB ladder + the correction
metric.

RULING BBB (Howard, verbatim intent): model heights are BARRED from zone
proposals. A proposal may only use evidence that appears on that
elevation drawing itself. The ladder:
    DERIVED   → the face's own chain
    CONTESTED → the LARGER contestant, both named
    otherwise → rectangle from that elevation's own datums or title band
Bottom-edge ruling: both the derived band and the proposal stay
FIRST FLOOR → TOP OF PLATE.

Item 4: correction events (eval only, never an input): CORRECTED /
DELETED (scores zero) / ADDED_FROM_SCRATCH. Per-vertex displacement in
FEET, edge deltas, area delta as the headline. Prediction file written
FIRST: /app/memory/send55_item4_prediction.md.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from routes.pdf_overlay import (_ladder_geometry, _contested_chain_value,  # noqa: E402
                                zone_event_metrics)


# ---------------------------------------------------------------------------
# the ladder — unit pins
# ---------------------------------------------------------------------------
GEO = {"top_of_plate": {"y": 20.0, "markers": [[7, 10], [60, 63]],
                        "span_x": [10.0, 60.0]},
       "first_floor": {"y": 30.0, "markers": [[7, 10], [60, 63]],
                       "span_x": [10.2, 60.2]}}


def test_derived_face_proposes_its_own_chain():
    r = {"status": "DERIVED", "page": "1", "ft": 9.08,
         "span_y": [20.0, 30.0], "band": [15.0, 35.0],
         "datum_geometry": GEO}
    s = _ladder_geometry(r)
    assert s["tier"] == "derived_chain"
    assert s["ft"] == 9.08
    assert s["y"] == [0.20, 0.30]
    assert s["x"] == [0.10, 0.602]
    assert "derived FIRST FLOOR" in s["basis"]


def test_contested_face_proposes_the_larger_contestant_naming_both():
    r = {"status": "REFUSED", "page": "1", "band": [15.0, 35.0],
         "datum_geometry": GEO,
         "gaps": [{"from": "TOP_OF_PLATE@20.0", "to": "FIRST_FLOOR@30.0",
                   "status": "CONTESTED", "value_in": None,
                   "rails": [{"raw": "9-1%", "in": 109},
                             {"raw": "9'-11*", "in": 119}]}]}
    s = _ladder_geometry(r)
    assert s["tier"] == "contested_pick_larger"
    assert s["ft"] == round(119 / 12.0, 2)      # the LARGER, not list order
    assert "9-1%" in s["basis"] and "9'-11*" in s["basis"]  # BOTH named
    assert "never averaged" in s["basis"]


def test_contested_pick_is_by_value_not_list_order():
    # the Boni-p4 defect shape: larger listed SECOND
    v = _contested_chain_value(
        {"gaps": [{"from": "TOP_OF_PLATE@20.0", "to": "FIRST_FLOOR@30.0",
                   "status": "CONTESTED", "value_in": None,
                   "rails": [{"raw": "small", "in": 100},
                             {"raw": "large", "in": 120}]}]}, 20.0, 30.0)
    assert v[0] == 120


def test_undimensioned_gap_kills_the_chain_value():
    v = _contested_chain_value(
        {"gaps": [{"from": "TOP_OF_PLATE@20.0", "to": "SECOND_FLOOR@25.0",
                   "status": "CONTESTED", "value_in": None,
                   "rails": [{"raw": "a", "in": 100}, {"raw": "b", "in": 90}]},
                  {"from": "SECOND_FLOOR@25.0", "to": "FIRST_FLOOR@30.0",
                   "status": "UNDIMENSIONED", "value_in": None,
                   "rails": []}]}, 20.0, 30.0)
    assert v is None


def test_datums_without_value_propose_a_datum_rectangle():
    r = {"status": "REFUSED", "page": "1", "band": [15.0, 35.0],
         "datum_geometry": GEO, "gaps": []}
    s = _ladder_geometry(r)
    assert s["tier"] == "datum_rectangle"
    assert s["ft"] is None
    assert s["y"] == [0.20, 0.30]


def test_no_datums_propose_the_title_band_and_say_so():
    r = {"status": "REFUSED", "page": "1", "band": [15.0, 35.0],
         "datum_geometry": {}, "gaps": []}
    s = _ladder_geometry(r)
    assert s["tier"] == "band_rectangle"
    assert s["ft"] is None
    assert s["y"] == [0.15, 0.35]
    assert s["x"] == [0.02, 0.98]
    assert "STARTING SHAPE" in s["basis"]


# ---------------------------------------------------------------------------
# SEND-63 item 2 — proposal bottom drops to TOP OF FOUNDATION (Howard's
# ruling). DP-1's DERIVED band stays sealed at FIRST FLOOR: the proposal
# and the derivation now DELIBERATELY differ, and the zone says so.
# ---------------------------------------------------------------------------
GEO_TOF = dict(GEO, top_of_foundation={"y": 32.0, "markers": [[7, 10]],
                                       "span_x": None})


def test_located_foundation_datum_drops_the_proposal_bottom():
    r = {"status": "DERIVED", "page": "1", "ft": 9.08,
         "span_y": [20.0, 30.0], "band": [15.0, 35.0],
         "datum_geometry": GEO_TOF}
    s = _ladder_geometry(r)
    assert s["y"] == [0.20, 0.32]              # zone bottom at TOF
    assert s["scale_y"] == [0.20, 0.30]        # scale stays the datum pair
    assert s["differs_from_derived_band"] is True
    assert "bottom: TOP OF FOUNDATION datum, this elevation" in s["basis"]


def test_no_foundation_datum_keeps_first_floor_and_says_so():
    r = {"status": "DERIVED", "page": "1", "ft": 9.08,
         "span_y": [20.0, 30.0], "band": [15.0, 35.0],
         "datum_geometry": GEO}
    s = _ladder_geometry(r)
    assert s["y"] == [0.20, 0.30]
    assert s["differs_from_derived_band"] is False
    assert ("bottom: FIRST FLOOR datum — no foundation datum located"
            in s["basis"])


def test_a_foundation_datum_above_first_floor_is_never_used():
    geo = dict(GEO, top_of_foundation={"y": 25.0, "markers": [[7, 10]],
                                       "span_x": None})
    r = {"status": "DERIVED", "page": "1", "ft": 9.08,
         "span_y": [20.0, 30.0], "band": [15.0, 35.0],
         "datum_geometry": geo}
    s = _ladder_geometry(r)
    assert s["y"] == [0.20, 0.30]
    assert s["differs_from_derived_band"] is False


def test_contested_tier_also_drops_to_foundation():
    r = {"status": "REFUSED", "page": "1", "band": [15.0, 35.0],
         "datum_geometry": GEO_TOF,
         "gaps": [{"from": "TOP_OF_PLATE@20.0", "to": "FIRST_FLOOR@30.0",
                   "status": "CONTESTED", "value_in": None,
                   "rails": [{"raw": "a", "in": 109},
                             {"raw": "b", "in": 119}]}]}
    s = _ladder_geometry(r)
    assert s["tier"] == "contested_pick_larger"
    assert s["y"] == [0.20, 0.32]
    assert s["scale_y"] == [0.20, 0.30]
    assert s["differs_from_derived_band"] is True


def test_single_ended_span_falls_to_page_width_and_says_so():
    geo = {"top_of_plate": {"y": 20.0, "markers": [[7, 10]], "span_x": None},
           "first_floor": {"y": 30.0, "markers": [[8, 11]], "span_x": None}}
    r = {"status": "DERIVED", "page": "1", "ft": 9.0,
         "span_y": [20.0, 30.0], "band": [15.0, 35.0],
         "datum_geometry": geo}
    s = _ladder_geometry(r)
    assert s["tier"] == "datum_rectangle"
    assert s["x"] == [0.02, 0.98]
    assert "PAGE WIDTH" in s["basis"]


def test_ruling_bbb_no_model_height_anywhere_in_the_proposal_path():
    """Structural: the propose path never touches a model hypothesis."""
    with open("/app/backend/routes/pdf_overlay.py", encoding="utf-8") as f:
        src = f.read()
    assert "hypothesis" not in src.lower()
    assert "model_height" not in src.lower()


# ---------------------------------------------------------------------------
# item 4 — metric arithmetic pins
# ---------------------------------------------------------------------------
SCALE = {"mode": "trace", "p1": [0.5, 0.2], "p2": [0.5, 0.3],
         "real_ft": 9.0, "source": "READ"}
W, H = 3000.0, 2000.0  # 0.1 page-height = 200 px = 9 ft → 0.045 ft/px


def test_corrected_metrics_report_feet_edges_and_area_delta():
    prop = [[0.10, 0.20], [0.60, 0.20], [0.60, 0.30], [0.10, 0.30]]
    conf = [[0.15, 0.20], [0.55, 0.20], [0.55, 0.30], [0.15, 0.30]]
    m = zone_event_metrics(prop, conf, SCALE, W, H)
    assert m["ft_available"] is True
    fpp = 9.0 / 200.0
    assert abs(m["edges_ft"]["left"] - 0.05 * W * fpp) < 0.02   # +6.75 ft
    assert abs(m["edges_ft"]["right"] + 0.05 * W * fpp) < 0.02  # pulled in
    assert m["edges_ft"]["top"] == 0.0 and m["edges_ft"]["bottom"] == 0.0
    assert m["per_vertex_ft"][0]["dx_ft"] > 6.0
    # area: width 0.50→0.40 of page → delta ratio = 0.10/0.40 = 0.25
    assert abs(m["area_delta_ratio"] - 0.25) < 0.01


def test_translation_shows_in_vertices_but_barely_in_area():
    prop = [[0.10, 0.20], [0.60, 0.20], [0.60, 0.30], [0.10, 0.30]]
    conf = [[0.12, 0.20], [0.62, 0.20], [0.62, 0.30], [0.12, 0.30]]
    m = zone_event_metrics(prop, conf, SCALE, W, H)
    assert all(v["dist_ft"] > 2.0 for v in m["per_vertex_ft"])
    assert m["area_delta_ratio"] < 0.001


def test_no_scale_records_honestly_without_feet():
    prop = [[0.1, 0.2], [0.6, 0.2], [0.6, 0.3]]
    m = zone_event_metrics(prop, prop, None, W, H)
    assert m["ft_available"] is False
    assert m["per_vertex_ft"] is None


def test_prediction_file_exists_and_predates_the_metric():
    with open("/app/memory/send55_item4_prediction.md", encoding="utf-8") as f:
        txt = f.read()
    assert "Vertical error ≈ 0" in txt
    assert "10–16 ft too wide" in txt


def test_metric_is_an_eval_never_an_input():
    """Nothing reads zone_correction_events at derivation time."""
    import glob
    hits = []
    for path in glob.glob("/app/backend/**/*.py", recursive=True):
        if "/tests/" in path:
            continue
        with open(path, encoding="utf-8") as f:
            src = f.read()
        if "zone_correction_events" not in src:
            continue
        hits.append(path)
    assert hits == ["/app/backend/routes/pdf_overlay.py"]
    with open("/app/backend/routes/pdf_overlay.py", encoding="utf-8") as f:
        src = f.read()
    # only writes (replace_one), never a read
    assert "zone_correction_events.find" not in src
    assert "zone_correction_events.aggregate" not in src


# ---------------------------------------------------------------------------
# live pins — cloned Letrick run under a disposable estimate
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
                        "customer_name": "ZZ TEST_ladder TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_ladder-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    yield {"eid": eid, "db": db, "run_id": clone["run_id"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_correction_events.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def test_live_every_letrick_face_proposes_with_basis_and_tier(sess, rig):
    r = sess.post(f"{API}/estimates/{rig['eid']}/pdf-overlay/propose",
                  timeout=30)
    assert r.status_code == 200, r.text
    proposed = r.json()["proposed"]
    by_face = {p["face_id"]: p for p in proposed}
    assert set(by_face) == {"front", "back", "left", "right"}
    for p in proposed:
        assert p["provenance"] == "proposed"
        assert p["sqft"] is None            # provisional feeds no quantity
        assert p.get("tier") and p.get("basis")
    assert by_face["front"]["tier"] == "derived_chain"
    assert by_face["left"]["tier"] == "derived_chain"
    assert by_face["right"]["tier"] == "derived_chain"
    back = by_face["back"]
    assert back["tier"] == "contested_pick_larger"
    assert "9'-11" in back["basis"] and "9-1" in back["basis"]  # BOTH named
    assert back["scale_ref"]["real_ft"] == round(119 / 12.0, 2)  # larger


def test_live_tof_bottom_scale_anchor_and_band_note(sess, rig):
    """SEND-63: on Letrick every face locates TOP OF FOUNDATION — the
    zone bottom sits at TOF, the trace scale stays anchored to the datum
    pair, and the zone SAYS it is taller than the derived band."""
    polys = sess.get(f"{API}/estimates/{rig['eid']}/pdf-overlay",
                     timeout=15).json()["polygons"]
    props = [p for p in polys if p["provenance"] == "proposed"]
    assert props
    for p in props:
        ys = sorted({v[1] for v in p["vertices_pct"]})
        sr = p.get("scale_ref")
        if sr:
            # zone bottom is BELOW the scale trace's bottom (TOF < FF on
            # the page means larger y)
            assert ys[-1] > sr["p2"][1] - 1e-9
        assert "bottom: TOP OF FOUNDATION datum" in p["basis"]
        assert "confirming it will change the quantity" in (p.get("band_note") or "")
        assert (p.get("proposed_from") or {}).get("bottom_datum") == "TOP_OF_FOUNDATION"


def test_live_confirmation_retains_the_basis_and_records_corrected(sess, rig):
    polys = sess.get(f"{API}/estimates/{rig['eid']}/pdf-overlay",
                     timeout=15).json()["polygons"]
    back = next(p for p in polys if p["face_id"] == "back"
                and p["provenance"] == "proposed")
    moved = [list(v) for v in back["vertices_pct"]]
    moved[1][0] -= 0.05    # pull the top-right vertex in
    moved[2][0] -= 0.05
    body = {"id": back["id"], "page": back["page"], "face_id": "back",
            "material_class": "siding", "vertices_pct": moved,
            "scale_ref": back["scale_ref"],
            "page_w_px": back["page_w_px"], "page_h_px": back["page_h_px"],
            "provenance": "human"}
    r = sess.put(f"{API}/estimates/{rig['eid']}/pdf-overlay", json=body,
                 timeout=15)
    assert r.status_code == 200, r.text
    out = r.json()["polygon"]
    # confirmation upgrades AUTHORITY, not EVIDENCE
    assert out["provenance"] == "human"
    assert out["confirmed_from"]["tier"] == "contested_pick_larger"
    assert "9'-11" in out["confirmed_from"]["basis"]
    # SEND-63: the derived-band difference is retained on confirm
    assert "confirming it will change the quantity" in (
        out["confirmed_from"].get("band_note") or "")
    ev = rig["db"].zone_correction_events.find_one(
        {"zone_id": back["id"], "event": "CORRECTED"})
    assert ev, "CORRECTED event must be recorded"
    assert ev["tier"] == "contested_pick_larger"
    assert ev["ft_available"] is True
    assert ev["edges_ft"]["right"] < -1.0      # pulled in, in FEET
    assert ev["area_delta_ratio"] > 0.0


def test_live_deleting_a_proposal_scores_zero_never_no_data(sess, rig):
    polys = sess.get(f"{API}/estimates/{rig['eid']}/pdf-overlay",
                     timeout=15).json()["polygons"]
    prop = next(p for p in polys if p["provenance"] == "proposed")
    r = sess.delete(
        f"{API}/estimates/{rig['eid']}/pdf-overlay/{prop['id']}",
        timeout=15)
    assert r.status_code == 200, r.text
    ev = rig["db"].zone_correction_events.find_one(
        {"zone_id": prop["id"], "event": "DELETED"})
    assert ev and ev["score"] == 0.0
    assert ev["face_id"] == prop["face_id"]


def test_live_hand_drawn_zone_records_added_from_scratch(sess, rig):
    body = {"id": str(uuid.uuid4()), "page": 1, "face_id": "gable:front",
            "material_class": "siding",
            "vertices_pct": [[0.2, 0.1], [0.4, 0.1], [0.3, 0.05]],
            "scale_ref": None, "page_w_px": 3000, "page_h_px": 2000,
            "provenance": "human"}
    r = sess.put(f"{API}/estimates/{rig['eid']}/pdf-overlay", json=body,
                 timeout=15)
    assert r.status_code == 200, r.text
    ev = rig["db"].zone_correction_events.find_one(
        {"zone_id": body["id"], "event": "ADDED_FROM_SCRATCH"})
    assert ev, "hand-drawn zones are area the system MISSED"
    assert ev["face_id"] == "gable:front"
    assert ev["proposal_existed_on_face"] is False
