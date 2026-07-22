"""P5 DORMERS pins (C-5 ruling, shipped 2026-07-23).

C-5 (Spec v2, ruled 2026-07-20/21): dormers draw on the roof plane in
position on their FACE-ON elevation; cheek PROFILES draw on the
perpendicular (gable) elevations; on_dormer openings JOIN the sheets and
schedules. Confirmation-weighted: width/knee/center from the run's dormer
read (tagged per width_source); the v-position on the roof plane is NOT
READ — base drawn at the eave line, flagged INDICATIVE.

COUNT PINS AMENDED (before → after, red house EST-910869, run c2002212):
  • LEFT  openings 3 → 5 (W2* @ 14'-10⅞", W4* @ 20'-8⅜" join) · windows 3 → 5
  • RIGHT openings 5 → 6 (W2* @ 20'-0" joins) · windows 5 → 6
  • FRONT/BACK openings unchanged (G1 W1 G2 D1 · W1 W2 P1) — profiles only

PLANE RULE: dormer-plane elements never guard against wall-plane elements
(separated by construction — the dormer sits above the eave). Red house
LEFT W2* (12.8'–17.0') horizontally overlaps wall W3 (16.3'–19.3') by
~8½" — different planes, NO flag.
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from routes.elevation_sheets import _bind_dormers, detect_collisions  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
REDHOUSE_EST = "673707d5-9b7e-4d8f-8eaf-63c86820f611"  # EST-910869
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"
SHEET_JSX = Path("/app/frontend/src/pages/ElevationSheet.jsx").read_text()


# ---------- unit: binder + plane rule ----------

def _raw_two_dormers():
    return {"dormers": [
        {"face": "left", "width_ft": 15, "knee_wall_height_ft": 5.0,
         "offset_x_ft": 0, "width_source": "direct_single_reading"},
        {"face": "right", "width_ft": 15, "knee_wall_height_ft": 5.0,
         "offset_x_ft": 0, "width_source": "direct_single_reading"},
    ]}


def test_binder_face_on_and_profiles():
    d, profs = _bind_dormers(_raw_two_dormers(), "left", 37.0, 9.3,
                             {"kind": "eave_ridge", "ridge_ft": 16.3})
    assert d is not None and d["face"] == "left"
    assert d["width_ft"] == 15.0 and d["knee_ft"] == 5.0
    assert d["center_ft"] == 18.5  # 37/2 + offset 0
    assert d["width_tag"] == "AI-READ ✓" and d["knee_tag"] == "AI-READ ✓"
    assert d["base_ft"] == 9.3 and "NOT READ" in d["base_note"]
    assert d["top_note"] is None  # 9.3 + 5 = 14.3 ≤ ridge 16.3
    # the right-face dormer is perpendicular to the LEFT view — no profile
    # (left/right faces profile on front/back only)
    assert profs == []


def test_binder_profiles_on_gable_ends_with_back_mirror():
    _, front = _bind_dormers(_raw_two_dormers(), "front", 24.0, 12.0, None)
    assert {(p["face"], p["drawing_side"]) for p in front} == {("left", "left"), ("right", "right")}
    _, back = _bind_dormers(_raw_two_dormers(), "back", 24.0, 12.0, None)
    assert {(p["face"], p["drawing_side"]) for p in back} == {("left", "right"), ("right", "left")}
    for p in front + back:
        assert "NOT READ" in p["note"] and "INDICATIVE" in p["note"]


def test_binder_top_exceeding_ridge_flags_never_suppresses():
    d, _ = _bind_dormers(_raw_two_dormers(), "left", 37.0, 9.3,
                         {"kind": "eave_ridge", "ridge_ft": 12.0})
    assert d is not None  # still draws
    assert "exceeds the drawn ridge" in d["top_note"]


def test_plane_rule_dormer_never_guards_against_wall():
    """Red house LEFT: dormer W2* h-overlaps wall W3 by ~8½" — different
    planes, separated by construction, NO flag. Same-plane pairs still
    flag (dormer × dormer at the same numbers would)."""
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


def test_redhouse_left_dormer_openings_join(session):
    """COUNT PIN AMENDED: LEFT openings 3 → 5, windows 3 → 5."""
    s = _sheet(session, "left")
    assert [o["tag"] for o in s["openings"]] == ["W1", "W2", "W3", "W4", "W5"]
    assert [o["tag"] for o in s["openings"] if o["on_dormer"]] == ["W2", "W4"]
    assert s["opening_counts"] == {"windows": 5, "doors": 0, "patio_doors": 0,
                                   "vents": 0, "garage_doors": 0}
    for o in s["openings"]:
        if o["on_dormer"]:
            assert o["dormer_face"] == "left"
            assert o["sill_in"] is None and o["sill_label"] == "—"  # dormer plane, never grade-anchored
    # PLANE RULE live: dormer W2 h-overlaps wall W3 — no flag
    assert s["collisions"] == []


def test_redhouse_left_dormer_face_on(session):
    s = _sheet(session, "left")
    d = s["dormer"]
    assert d is not None and d["face"] == "left"
    assert d["width_ft"] == 15.0 and d["width_label"] == "15'-0\""
    assert d["knee_ft"] == 5.0 and d["width_tag"] == "AI-READ ✓"
    assert d["center_ft"] == 18.5  # wall 37' / 2, offset 0 (posts center it)
    assert "NOT READ" in d["base_note"] and "INDICATIVE" in d["base_note"]
    assert s["dormer_profiles"] == []  # eave view — no perpendicular profiles


def test_redhouse_right_dormer_openings_join(session):
    """COUNT PIN AMENDED: RIGHT openings 5 → 6, windows 5 → 6."""
    s = _sheet(session, "right")
    assert s["opening_counts"]["windows"] == 6
    dorm = [o for o in s["openings"] if o["on_dormer"]]
    assert len(dorm) == 1 and dorm[0]["tag"] == "W2" and dorm[0]["center_ft"] == 20
    assert s["dormer"] is not None and s["dormer"]["face"] == "right"


def test_redhouse_front_back_profiles(session):
    """FRONT/BACK gable ends: no face-on dormer, TWO cheek profiles each;
    BACK mirrors left/right (exterior-view convention). Opening rosters
    unchanged (front G1 W1 G2 D1 · back W1 W2 P1)."""
    f = _sheet(session, "front")
    assert f["dormer"] is None
    assert {(p["face"], p["drawing_side"]) for p in f["dormer_profiles"]} == {("left", "left"), ("right", "right")}
    assert [o["tag"] for o in f["openings"]] == ["G1", "W1", "G2", "D1"]
    b = _sheet(session, "back")
    assert {(p["face"], p["drawing_side"]) for p in b["dormer_profiles"]} == {("left", "right"), ("right", "left")}
    assert [o["tag"] for o in b["openings"]] == ["W1", "W2", "P1"]


def test_undormered_fixture_unchanged(session):
    """Letrick has no dormers[] — nothing invents one."""
    s = _sheet(session, "front", est=LETRICK_EST)
    assert s["dormer"] is None and s["dormer_profiles"] == []


# ---------- JSX wiring ----------

def test_sheet_jsx_dormer_wiring():
    assert "elevation-dormer" in SHEET_JSX
    assert "elevation-dormer-profile-" in SHEET_JSX
    assert "elevation-schedule-dormer-legend" in SHEET_JSX
    # schedule rows mark dormer openings: W2* + legend
    assert "_tagLabel" in SHEET_JSX
    # dormer windows center in the dormer face band, not the wall mid-band
    assert "dormerG.baseY" in SHEET_JSX
