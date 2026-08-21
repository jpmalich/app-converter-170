"""SEND-69 pins — LINE-WORK READ wired into propose (wall outline only).

RESOLVED overrides datum-span geometry with the basis stating so.
INDETERMINATE keeps the datum span under ITS OWN geometry tier — a
disclosed fallback never looks like a resolved outline. The sheet
border is excluded STRUCTURALLY (band containment), never by a size
threshold. Prediction file written FIRST:
/app/memory/send69_linework_prediction.md.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from linework_read import wall_outline_from_segments  # noqa: E402

BAND = (10.0, 50.0)
PLATE = (25.5, 26.5)
FLOOR = (43.5, 44.5)


def _walls(extra=()):
    segs = [
        {"x0": 20, "x1": 20, "top": 25, "bottom": 45},   # left wall
        {"x0": 60, "x1": 60, "top": 25, "bottom": 45},   # right wall
        {"x0": 20, "x1": 60, "top": 26, "bottom": 26},   # plate line
        {"x0": 20, "x1": 60, "top": 44, "bottom": 44},   # floor line
    ]
    return segs + list(extra)


def test_plain_rectangle_resolves_with_four_vertices():
    r = wall_outline_from_segments(_walls(), BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 60.0]
    assert r["n_vertices"] == 4


def test_a_step_resolves_through_a_jointed_chain_with_extra_vertices():
    segs = [
        {"x0": 20, "x1": 20, "top": 25, "bottom": 45},
        {"x0": 60, "x1": 60, "top": 25, "bottom": 35},   # upper right
        {"x0": 65, "x1": 65, "top": 35, "bottom": 45},   # projection
        {"x0": 60, "x1": 65, "top": 35, "bottom": 35},   # the drawn joint
        {"x0": 20, "x1": 60, "top": 26, "bottom": 26},
        {"x0": 20, "x1": 65, "top": 44, "bottom": 44},
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 65.0]
    assert r["n_vertices"] == 6              # the step survived


def test_unjoined_verticals_never_chain():
    """Two verticals terminating at the same y with NO horizontal whose
    ends meet them are not a boundary — a crossing is not a joint."""
    segs = [
        {"x0": 20, "x1": 20, "top": 25, "bottom": 45},
        {"x0": 60, "x1": 60, "top": 25, "bottom": 35},
        {"x0": 65, "x1": 65, "top": 35, "bottom": 45},
        # a long horizontal CROSSES both x's but its ends meet neither:
        {"x0": 10, "x1": 90, "top": 35, "bottom": 35},
        {"x0": 20, "x1": 60, "top": 26, "bottom": 26},
        {"x0": 20, "x1": 65, "top": 44, "bottom": 44},
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    # only ONE full spanner (left wall) remains → indeterminate
    assert r["status"] == "INDETERMINATE"


def test_sheet_border_is_excluded_structurally_by_band_containment():
    border = (
        {"x0": 1, "x1": 1, "top": 1, "bottom": 99},
        {"x0": 99, "x1": 99, "top": 1, "bottom": 99},
        {"x0": 1, "x1": 99, "top": 1, "bottom": 1},
        {"x0": 1, "x1": 99, "top": 99, "bottom": 99},
    )
    r = wall_outline_from_segments(_walls(border), BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 60.0]       # never page width
    # and a border ALONE (no wall strokes) resolves nothing:
    r2 = wall_outline_from_segments(list(border) + [
        {"x0": 20, "x1": 60, "top": 26, "bottom": 26},
        {"x0": 20, "x1": 60, "top": 44, "bottom": 44},
    ], BAND, PLATE, FLOOR, [])
    assert r2["status"] == "INDETERMINATE"


def test_masked_glyph_strokes_never_become_a_boundary():
    glyph = {"x0": 12, "x1": 12, "top": 25, "bottom": 45}
    r = wall_outline_from_segments(
        _walls([glyph]), BAND, PLATE, FLOOR,
        [(11.0, 24.0, 13.0, 46.0)])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 60.0]       # the masked stroke lost


def test_unclosed_boundaries_refuse_with_the_level_named():
    segs = [s for s in _walls() if not (s["top"] == 26 and s["bottom"] == 26)]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "INDETERMINATE"
    assert "plate level" in r["reason"]


def test_twin_strokes_at_one_corner_refuse():
    """Two boundaries within the line-weight scale are ONE drawn corner
    (a double-stroked line) — never a resolvable width."""
    segs = [
        {"x0": 20, "x1": 20, "top": 25, "bottom": 45},
        {"x0": 20.3, "x1": 20.3, "top": 25, "bottom": 45},
        {"x0": 20, "x1": 60, "top": 26, "bottom": 26},
        {"x0": 20, "x1": 60, "top": 44, "bottom": 44},
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "INDETERMINATE"


def test_fragmented_strokes_rejoin_as_drawn_continuity():
    """CAD strokes break at intersections — collinear pieces within the
    line-weight scale are one drawn stroke, so a corner drawn in three
    pieces still spans the datum interval."""
    segs = [
        {"x0": 20, "x1": 20, "top": 25, "bottom": 32},
        {"x0": 20, "x1": 20, "top": 32.2, "bottom": 39},
        {"x0": 20, "x1": 20, "top": 39.1, "bottom": 45},
        {"x0": 60, "x1": 60, "top": 25, "bottom": 45},
        {"x0": 20, "x1": 40, "top": 26, "bottom": 26},
        {"x0": 40.2, "x1": 60, "top": 26, "bottom": 26},
        {"x0": 20, "x1": 60, "top": 44, "bottom": 44},
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 60.0]


def test_a_datum_level_line_is_a_closure_never_a_jog():
    """A horizontal AT datum level cannot join two verticals into a
    'step' — otherwise the plate line itself would chain a loose stub
    into a page-wide boundary."""
    segs = _walls([
        # a stub INSIDE the plate box at x=10 …
        {"x0": 10, "x1": 10, "top": 25.5, "bottom": 26.4},
        # … a tall vertical at x=80 starting just under the plate …
        {"x0": 80, "x1": 80, "top": 26.6, "bottom": 45},
        # … and the plate-level line running across both. NOT a jog.
        {"x0": 10, "x1": 80, "top": 26.1, "bottom": 26.1},
        {"x0": 20, "x1": 80, "top": 44, "bottom": 44},
    ])
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 60.0]


def test_prediction_file_written_before_the_wiring():
    with open("/app/memory/send69_linework_prediction.md",
              encoding="utf-8") as f:
        txt = f.read()
    assert "near zero" in txt
    assert "chimney" in txt
    assert "checks, never targets" in txt


# ---------------------------------------------------------------------------
# SEND-71 item 5 — GABLE LINE-WORK (trace the drawn triangle)
# ---------------------------------------------------------------------------
from linework_read import gable_triangle_from_segments  # noqa: E402

GBAND = (5.0, 50.0)
GPLATE = (25.5, 26.5)


def _rake(x0, y0, x1, y1):
    return {"x0": min(x0, x1), "x1": max(x0, x1),
            "top": min(y0, y1), "bottom": max(y0, y1),
            "p0": [x0, y0], "p1": [x1, y1]}


def test_gable_triangle_traces_the_drawn_rakes():
    segs = [_rake(20, 26, 40, 10), _rake(40, 10, 60, 26)]
    r = gable_triangle_from_segments(segs, GBAND, GPLATE,
                                     (20.0, 60.0), 26.0, [])
    assert r["status"] == "RESOLVED"
    assert abs(r["apex"][0] - 40) < 0.5 and abs(r["apex"][1] - 10) < 0.5
    assert len(r["vertices_pct"]) == 3


def test_gable_refuses_when_a_rake_stops_short_of_the_apex():
    segs = [_rake(20, 26, 30, 18), _rake(40, 10, 60, 26)]
    r = gable_triangle_from_segments(segs, GBAND, GPLATE,
                                     (20.0, 60.0), 26.0, [])
    assert r["status"] == "INDETERMINATE"
    assert "stops short" in r["reason"]


def test_gable_refuses_with_no_rake_at_a_corner():
    segs = [_rake(40, 10, 60, 26)]
    r = gable_triangle_from_segments(segs, GBAND, GPLATE,
                                     (20.0, 60.0), 26.0, [])
    assert r["status"] == "INDETERMINATE"
    assert "left wall corner" in r["reason"]


def test_gable_masked_diagonals_never_trace():
    segs = [_rake(20, 26, 40, 10), _rake(40, 10, 60, 26)]
    r = gable_triangle_from_segments(
        segs, GBAND, GPLATE, (20.0, 60.0), 26.0,
        [(15.0, 5.0, 65.0, 30.0)])           # everything under text
    assert r["status"] == "INDETERMINATE"


def test_gable_read_never_computes_from_pitch_or_convention():
    with open("/app/backend/linework_read.py", encoding="utf-8") as f:
        src = f.read()
    assert "0.70" not in src
    assert "GABLE_FACTOR" not in src


# ---------------------------------------------------------------------------
# live pins — every proposal discloses its geometry tier
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
                        "customer_name": "ZZ TEST_send69 TEMP"},
                  timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send69-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    resp = sess.post(f"{API}/estimates/{eid}/pdf-overlay/propose",
                     timeout=120)
    assert resp.status_code == 200, resp.text
    yield {"eid": eid, "db": db, "run_id": clone["run_id"],
           "proposed": resp.json()["proposed"]}
    db.ai_blueprint_runs.delete_many({"run_id": clone["run_id"]})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.zone_correction_events.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})


def test_live_every_proposal_discloses_its_geometry_tier(rig):
    assert rig["proposed"], "nothing proposed"
    for p in rig["proposed"]:
        assert p["geometry_tier"] in (
            "wall_outline", "datum_span",
            "datum_span_after_linework_refused",
            "chase_outline"), p["face_id"]   # SEND-94: chase surfaces
        if p["face_id"].startswith("gable:"):
            continue                      # gables are out of scope (walls only)
        if p["geometry_tier"] == "chase_outline":
            # SEND-94: a chase rides a RESOLVED outline's linework
            assert p["face_id"].startswith("chase:")
            assert p["proposed_from"]["linework"]["status"] == "RESOLVED"
            continue
        lw = p["proposed_from"]["linework"]
        assert lw["status"] in ("RESOLVED", "INDETERMINATE",
                                "NOT_ATTEMPTED")
        if p["geometry_tier"] == "wall_outline":
            assert lw["status"] == "RESOLVED"
            assert "WALL OUTLINE" in p["basis"]
            assert p["proposed_from"]["datum_span_x_pct"] is not None
            assert len(p["vertices_pct"]) >= 4
        elif p["geometry_tier"] == "datum_span_after_linework_refused":
            assert lw["status"] == "INDETERMINATE"
            assert "carries the leader offset" in p["basis"]
        else:
            assert lw["status"] == "NOT_ATTEMPTED"
            assert lw["reason"]


def test_live_a_resolved_outline_never_wears_datum_span_clothes(rig):
    for p in rig["proposed"]:
        if p["face_id"].startswith("gable:"):
            continue
        if p["geometry_tier"] != "wall_outline":
            assert "WALL OUTLINE" not in p["basis"], (
                "a fallback wearing a read's clothes: " + p["face_id"])
