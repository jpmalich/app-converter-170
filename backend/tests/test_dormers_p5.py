"""P5 DORMERS pins (C-5 ruling, shipped 2026-07-23; AMENDED same day by
Howard's field-compare FAIL ruling — two defects fixed, pins amended).

DEFECT #1 (profile orientation, FRONT/BACK): profiles were drawn rotated
~90° (tall-narrow mid-rake triangle). AFTER: the dormer renders as its
ROOF EDGE — a LEVEL line projecting off the main slope — with the
vertical FACE EDGE below it (height = knee by construction) and the
CHEEK closing back to the roof plane. Wide and low, per the site photo.

DEFECT #2 (v-pos, LEFT/RIGHT): base-at-eave was an unratified assumption
— RETIRED. AFTER: v-pos is BOUND from the run's same-photo bboxes
(evidence): wall-plane scale = height_in/bbox.h over the wall windows
sharing the dormer's photo; dormer window-band center converted to
inches above the wall-window head line; absolute anchor = the PROPOSED
ASSUMED 6'-8" (80") standard header height (PENDING RATIFICATION).
Ladder: TAPED (appendage dims, AUTHORIZED) > ESTIMATED (photo-scaled) >
mid-slope UNRESOLVED flag (default pending ratification).

PIN AMENDMENTS (before → after, red house EST-910869, run c2002212):
  • LEFT dormer band: base 9'-3⅝" (eave) → 10'-6½" (10.54'), top 15'-6½"
    — dormer eave 2'-1⅜" below the 17'-7⅞" ridge (matches the site photo)
  • RIGHT dormer band: base 8'-1¼" (eave) → 10'-1⅝" (10.14'), top 15'-1⅝"
  • Dormer window sills: None ("—") → BOUND: LEFT W2* 139.5" / W4* 140.2",
    RIGHT W2* 132.5" — ESTIMATED (photo-scaled, head-anchored)
  • Count pins UNCHANGED: LEFT openings 5 (3→5 at P5 ship), RIGHT 6 (5→6)
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from routes.elevation_sheets import (  # noqa: E402
    DORMER_WINDOW_HEAD_ANCHOR_IN,
    _bind_dormers,
    _dormer_vpos,
    detect_collisions,
)

API = "https://app-converter-170.preview.emergentagent.com/api"
REDHOUSE_EST = "673707d5-9b7e-4d8f-8eaf-63c86820f611"  # EST-910869
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"
SHEET_JSX = Path("/app/frontend/src/pages/ElevationSheet.jsx").read_text()


# ---------- unit: v-pos binder (defect #2) ----------

def test_head_anchor_constant_is_proposed_80in():
    """PROPOSED ASSUMED (pending ratification): 6'-8" standard header —
    changing it requires ratification, not a code edit."""
    assert DORMER_WINDOW_HEAD_ANCHOR_IN == 80.0


def _raw_redhouse_left_shape():
    """Red house left, at the run's own bbox numbers."""
    return {
        "dormers": [{"face": "left", "width_ft": 15, "knee_wall_height_ft": 5.0,
                     "offset_x_ft": 0, "width_source": "direct_single_reading"}],
        "openings": [
            {"wall": "left", "type": "window", "height_in": 51, "photo_idx": 2,
             "bbox": {"x": 0.2375, "y": 0.5625, "w": 0.05625, "h": 0.125}},
            {"wall": "left", "type": "window", "height_in": 51, "photo_idx": 2,
             "bbox": {"x": 0.4375, "y": 0.5625, "w": 0.05625, "h": 0.125}},
            {"wall": "left", "type": "window", "height_in": 50, "photo_idx": 2,
             "bbox": {"x": 0.640625, "y": 0.5625, "w": 0.05625, "h": 0.1225}},
            {"wall": "left", "type": "window", "height_in": 38, "photo_idx": 2,
             "on_dormer": True, "dormer_face": "left",
             "bbox": {"x": 0.365625, "y": 0.3375, "w": 0.078125, "h": 0.0791666667}},
            {"wall": "left", "type": "window", "height_in": 36, "photo_idx": 2,
             "on_dormer": True, "dormer_face": "left",
             "bbox": {"x": 0.49375, "y": 0.3333333333, "w": 0.078125, "h": 0.0816666667}},
        ],
    }


def test_vpos_same_photo_bbox_chain_exact():
    """Mechanism pin: scale 408 in/frac (51/0.125 ×2, 50/0.1225), head
    0.5625, window band 0.3333–0.4150, center 76.5" above head → band
    center 156.5" above grade → base 10.54', top 15.54'."""
    v = _dormer_vpos(_raw_redhouse_left_shape(), "left", 5.0)
    assert v is not None
    assert v["base_ft"] == pytest.approx(10.54, abs=0.02)
    assert v["top_ft"] == pytest.approx(15.54, abs=0.02)
    assert v["tag"].startswith("ESTIMATED (photo-scaled")
    assert "PENDING RATIFICATION" in v["basis"]


def test_vpos_none_without_same_photo_wall_windows():
    raw = _raw_redhouse_left_shape()
    raw["openings"] = [o for o in raw["openings"] if o.get("on_dormer")]
    assert _dormer_vpos(raw, "left", 5.0) is None


def test_binder_unresolved_falls_back_mid_slope_flagged():
    """No bbox chain → NO silent base-at-eave (retired): mid-slope,
    UNRESOLVED flag, default pending ratification."""
    raw = {"dormers": [{"face": "left", "width_ft": 15, "knee_wall_height_ft": 5.0,
                        "offset_x_ft": 0, "width_source": "direct_single_reading"}]}
    d, _ = _bind_dormers({}, raw, "left", 37.0, 9.3,
                         {"kind": "eave_ridge", "ridge_ft": 16.3})
    assert d["vpos_tag"] == "UNRESOLVED"
    assert d["base_ft"] == pytest.approx(10.3, abs=0.01)  # 9.3 + (16.3-9.3-5)/2
    assert "PENDING RATIFICATION" in d["base_note"]


def test_binder_tape_ladder_authorized():
    """AUTHORIZED (Howard 2026-07-22): user_measured knee_ft/base_ft via
    lp_appendage_dims dormer:{face} outrank every rung — TAPED tags."""
    est = {"lp_appendage_dims": {"dormer:left": {
        "knee_ft": {"value": 5.2, "status": "user_measured"},
        "base_ft": {"value": 10.8, "status": "user_measured"}}}}
    raw = _raw_redhouse_left_shape()
    d, _ = _bind_dormers(est, raw, "left", 37.0, 9.3,
                         {"kind": "eave_ridge", "ridge_ft": 17.65})
    assert d["knee_ft"] == 5.2 and d["knee_tag"] == "TAPED (user-measured)"
    assert d["base_ft"] == 10.8 and d["top_ft"] == 16.0
    assert d["vpos_tag"] == "TAPED (user-measured)"
    # 'assumed' status never overrides (standing appendage-dims rule)
    est2 = {"lp_appendage_dims": {"dormer:left": {
        "base_ft": {"value": 12.0, "status": "assumed"}}}}
    d2, _ = _bind_dormers(est2, raw, "left", 37.0, 9.3,
                          {"kind": "eave_ridge", "ridge_ft": 17.65})
    assert d2["base_ft"] == pytest.approx(10.54, abs=0.02)


def test_binder_profiles_carry_vpos_and_mirror():
    raw = _raw_redhouse_left_shape()
    _, front = _bind_dormers({}, raw, "front", 24.0, 12.0, None)
    assert [(p["face"], p["drawing_side"]) for p in front] == [("left", "left")]
    p = front[0]
    assert p["base_ft"] == pytest.approx(10.54, abs=0.02)
    assert p["top_ft"] == pytest.approx(15.54, abs=0.02)
    assert "roof edge drawn LEVEL" in p["note"]
    _, back = _bind_dormers({}, raw, "back", 24.0, 12.0, None)
    assert [(p["face"], p["drawing_side"]) for p in back] == [("left", "right")]


def test_plane_rule_dormer_never_guards_against_wall():
    """Dormer-plane vs wall-plane: separated by construction, NO flag;
    same-plane pairs still flag."""
    dormer_w2 = {"name": "W2", "kind": "opening", "plane": "dormer:left",
                 "base": "b", "lo_ft": 12.82, "hi_ft": 16.98}
    wall_w3 = {"name": "W3", "kind": "opening", "plane": "wall",
               "base": "b", "lo_ft": 16.27, "hi_ft": 19.27}
    assert detect_collisions([dormer_w2, wall_w3]) == []
    same_plane = dict(wall_w3, plane="dormer:left")
    assert len(detect_collisions([dormer_w2, same_plane])) == 1


# ---------- live: red house acceptance sheets ----------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def _sheet(session, which, est=REDHOUSE_EST):
    r = session.get(f"{API}/estimates/{est}/elevation-sheet/{which}", timeout=30)
    assert r.status_code == 200, f"{which}: {r.text}"
    return r.json()


def test_redhouse_left_dormer_openings_join_with_bound_sills(session):
    """COUNT PIN (P5 ship): LEFT openings 3 → 5. SILL PIN AMENDED
    (v-pos ruling): None ('—') → W2* 139.5" / W4* 140.2" ESTIMATED."""
    s = _sheet(session, "left")
    assert [o["tag"] for o in s["openings"]] == ["W1", "W2", "W3", "W4", "W5"]
    assert [o["tag"] for o in s["openings"] if o["on_dormer"]] == ["W2", "W4"]
    assert s["opening_counts"] == {"windows": 5, "doors": 0, "patio_doors": 0,
                                   "vents": 0, "garage_doors": 0}
    w2 = next(o for o in s["openings"] if o["tag"] == "W2")
    w4 = next(o for o in s["openings"] if o["tag"] == "W4")
    assert w2["sill_in"] == pytest.approx(139.5, abs=0.3) and w2["sill_tag"] == "ESTIMATED"
    assert w4["sill_in"] == pytest.approx(140.2, abs=0.3)
    assert s["collisions"] == []  # plane rule live


def test_redhouse_left_dormer_band_bound_not_eave(session):
    """PIN AMENDED (v-pos ruling): base 9'-3⅝" (eave, RETIRED) →
    10'-6½" bound; top 15'-6½" — dormer eave 2'-1⅜" below the ridge."""
    s = _sheet(session, "left")
    d = s["dormer"]
    assert d["base_ft"] == pytest.approx(10.54, abs=0.02)
    assert d["top_ft"] == pytest.approx(15.54, abs=0.02)
    assert d["base_ft"] > s["wall"]["height_ft"]  # sits UP the slope, not at the eave
    assert d["vpos_tag"].startswith("ESTIMATED (photo-scaled")
    assert "PENDING RATIFICATION" in d["base_note"]
    assert d["width_ft"] == 15.0 and d["knee_ft"] == 5.0
    assert d["center_ft"] == 18.5
    assert s["dormer_profiles"] == []


def test_redhouse_right_dormer_band_and_sill(session):
    """PIN AMENDED: RIGHT base 8'-1¼" (eave) → 10'-1⅝"; W2* sill 132.5"."""
    s = _sheet(session, "right")
    assert s["opening_counts"]["windows"] == 6
    d = s["dormer"]
    assert d["base_ft"] == pytest.approx(10.14, abs=0.02)
    assert d["top_ft"] == pytest.approx(15.14, abs=0.02)
    dorm = [o for o in s["openings"] if o["on_dormer"]]
    assert len(dorm) == 1 and dorm[0]["tag"] == "W2"
    assert dorm[0]["sill_in"] == pytest.approx(132.5, abs=0.3)


def test_redhouse_front_back_profiles_carry_vpos(session):
    """FRONT/BACK: two profiles each, mirrored on BACK; each carries the
    bound band + the LEVEL roof-edge note. Opening rosters unchanged."""
    f = _sheet(session, "front")
    assert f["dormer"] is None
    assert {(p["face"], p["drawing_side"]) for p in f["dormer_profiles"]} == {("left", "left"), ("right", "right")}
    for p in f["dormer_profiles"]:
        assert p["base_ft"] is not None and p["top_ft"] == pytest.approx(p["base_ft"] + p["knee_ft"], abs=0.02)
        assert "roof edge drawn LEVEL" in p["note"]
    assert [o["tag"] for o in f["openings"]] == ["G1", "W1", "G2", "D1"]
    b = _sheet(session, "back")
    assert {(p["face"], p["drawing_side"]) for p in b["dormer_profiles"]} == {("left", "right"), ("right", "left")}
    assert [o["tag"] for o in b["openings"]] == ["W1", "W2", "P1"]


def test_undormered_fixture_unchanged(session):
    s = _sheet(session, "front", est=LETRICK_EST)
    assert s["dormer"] is None and s["dormer_profiles"] == []


# ---------- JSX wiring ----------

def test_sheet_jsx_dormer_wiring():
    assert "elevation-dormer" in SHEET_JSX
    assert "elevation-dormer-profile-" in SHEET_JSX
    # defect #1 fix: the LEVEL roof edge is the drawn, defining edge
    assert "elevation-dormer-profile-roof-edge-" in SHEET_JSX
    assert "roof edge LEVEL" in SHEET_JSX or "C2" in SHEET_JSX
    assert "elevation-schedule-dormer-legend" in SHEET_JSX
    assert "_tagLabel" in SHEET_JSX
    # face-on band drawn at the BOUND top, not base+knee-at-eave
    assert "dormer.top_ft" in SHEET_JSX
