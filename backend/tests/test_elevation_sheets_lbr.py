"""Elevation Sheets LEFT/BACK/RIGHT (EL-2..EL-4) — Phase 2 pins
(ruled 2026-07-18, baseline 345aa68).

Pass criteria pinned here:
  • all four sheets 200; unknown label 404
  • stepped sides carry BOTH tape segments, each with its own courses ×
    exposure basis formula — no silent interpolation; step_note present
  • BACK binds sealed key EST-191890: width 54 TAPED, 9.92' = 28 × 4.25"
  • chase (back) annotated AI-READ, footprint untaped — NOT TO SCALE
  • deviation box per elevation wherever tape ≠ AI
  • CLOSED three-key opening contract {windows, doors, vents}; the left
    wall's vent renders V-tagged with AI-READ position
  • verb machinery remove→reset pinned per sheet (LEFT, BACK) + cross-wall
    isolation (RIGHT untouched by BACK removals)
  • basis-line completeness: every rendered dimension names its basis —
    no untagged values on any sheet
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"   # Mark Letrick EST-373526
LETRICK_RUN = "d66794488ef848509446431b355db8e5"        # archived: elevation-sheet-pin

ALLOWED_TAGS = {"TAPED", "TAPED-DERIVED", "AI-READ ✓", "AI-READ ⚠", "ESTIMATED"}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def _sheet(session, which):
    r = session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/{which}", timeout=30)
    assert r.status_code == 200, f"{which}: {r.text}"
    return r.json()


def test_all_four_sheets_200_and_unknown_404(session):
    codes = {}
    for which in ("front", "left", "back", "right"):
        s = _sheet(session, which)
        codes[which] = s["sheet_code"]
        assert s["sheet"] == which
    assert codes == {"front": "EL-1", "left": "EL-2", "back": "EL-3", "right": "EL-4"}
    r = session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/roof", timeout=15)
    assert r.status_code == 404


def test_back_binds_sealed_key(session):
    s = _sheet(session, "back")
    w = s["wall"]
    assert w["width_ft"] == 54.0 and w["width_tag"] == "TAPED"
    assert "EST-191890" in w["width_source"]
    # 9.92' = 28 × 4.25" ÷ 12 — bound to the sealed key, never retyped
    assert w["height_ft"] == 9.92
    assert w["height_label"] == "9'-11\""
    assert w["height_tag"] == "TAPED-DERIVED"
    assert "28" in w["height_formula"] and "4.25" in w["height_formula"]
    assert w["courses"] == 28 and w["exposure_in"] == 4.25
    assert w["segments"] and len(w["segments"]) == 1
    assert w["step_note"] is None
    assert w["area_sqft"] == 535.7  # 54 × 9.92
    assert "EST-191890" in s["geometry_basis"]["walls"]


def test_back_chase_annotated_not_scaled(session):
    s = _sheet(session, "back")
    ch = s["chase"]
    assert ch is not None
    assert "chase" in ch["note"].lower()
    assert ch["tag"] == "AI-READ ✓"
    assert ch["footprint"] == "untaped — NOT TO SCALE"


def test_back_deviation_both_axes(session):
    d = _sheet(session, "back")["deviation"]
    assert d is not None and d["governs"] == "tape"
    assert d["ai_width_ft"] == 50 and d["ai_height_ft"] == 8.6
    assert d["width_disputed"] is True
    assert d["delta_width_label"].startswith("-4'")
    assert d["run_short"] == LETRICK_RUN[:8]


def test_back_openings_and_counts(session):
    s = _sheet(session, "back")
    assert s["opening_counts"] == {"windows": 5, "doors": 1, "vents": 0}
    tags = [o["tag"] for o in s["openings"]]
    assert tags == ["W1", "W2", "D1", "W3", "W4", "W5"]  # along-wall order
    d1 = next(o for o in s["openings"] if o["tag"] == "D1")
    assert d1["sill_in"] == 0.0  # door anchors sills on this wall
    for o in s["openings"]:
        if o["tag"].startswith("W"):
            assert o["sill_in"] is not None and o["sill_tag"] == "ESTIMATED"
            assert o["sill_in"] + o["height_in"] < 9.92 * 12


def _assert_stepped_segments(w):
    segs = w["segments"]
    assert segs and len(segs) == 2, "stepped side must carry BOTH tape segments"
    assert [s["courses"] for s in segs] == [25, 28]
    assert [s["height_ft"] for s in segs] == [8.854, 9.92]
    assert segs[0]["height_label"] == "8'-10¼\"" and segs[1]["height_label"] == "9'-11\""
    for s in segs:
        assert s["height_tag"] == "TAPED-DERIVED"
        assert "4.25" in s["height_formula"] and str(s["courses"]) in s["height_formula"]
    assert w["step_note"] and "NOT TAPED" in w["step_note"]
    # honesty: stepped area needs the untaped step location — not derivable
    assert w["area_sqft"] is None and "untaped" in w["area_note"]


def test_left_stepped_segments_and_untaped_width(session):
    s = _sheet(session, "left")
    w = s["wall"]
    _assert_stepped_segments(w)
    assert w["height_ft"] == 9.92  # tallest segment drives the frame
    # width untaped on sides: AI fallback, LABELED
    assert w["width_ft"] == 30 and w["width_tag"] == "AI-READ ✓"
    assert "untaped" in w["width_source"] and LETRICK_RUN[:8] in w["width_source"]
    gb = s["geometry_basis"]["walls"]
    assert "EST-191890" in gb and "heights" in gb and LETRICK_RUN[:8] in gb
    assert w["gable_triangle_ft"] == 8.8 and w["gable_tag"] in ALLOWED_TAGS


def test_right_stepped_segments_no_openings(session):
    s = _sheet(session, "right")
    _assert_stepped_segments(s["wall"])
    assert s["wall"]["width_ft"] == 30
    assert s["opening_counts"] == {"windows": 0, "doors": 0, "vents": 0}
    assert s["openings"] == []
    assert "No openings" in s["schedule_note"]
    assert s["wall"]["gable_triangle_ft"] == 9.3


def test_sides_height_deviation(session):
    # AI single-height read misses EVERY tape segment on both sides
    for which, ai_h in (("left", 9.0), ("right", 8.3)):
        d = _sheet(session, which)["deviation"]
        assert d is not None, which
        assert d["ai_height_ft"] == ai_h and d["governs"] == "tape"
        assert d["width_disputed"] is False  # sides: width untaped, not disputed
        assert d["delta_width_label"] is None
        assert "8'-10¼\"" in d["tape_heights_label"] and "9'-11\"" in d["tape_heights_label"]


def test_left_vent_three_key_contract(session):
    s = _sheet(session, "left")
    assert s["opening_counts"] == {"windows": 1, "doors": 0, "vents": 1}
    tags = [o["tag"] for o in s["openings"]]
    assert tags == ["V1", "W1"]  # vent at 15.0' precedes window at 21.0'
    v1 = next(o for o in s["openings"] if o["tag"] == "V1")
    assert v1["type"] == "Vent" and v1["width_in"] == 12 and v1["height_in"] == 8
    assert v1["position_tag"] == "AI-READ ✓"
    # no door on this wall: sills not derivable — stated, not invented
    assert all(o["sill_in"] is None for o in s["openings"])
    assert all(o["sill_label"] == "—" for o in s["openings"])
    assert "No door" in s["schedule_note"]


def test_basis_line_completeness_all_sheets(session):
    """Ruled pin: every rendered dimension on every sheet names its basis —
    no untagged values anywhere."""
    for which in ("front", "left", "back", "right"):
        s = _sheet(session, which)
        w = s["wall"]
        assert w["width_tag"] in ALLOWED_TAGS, which
        assert w["width_source"], which
        assert w["height_tag"] in ALLOWED_TAGS, which
        assert w["height_formula"], which
        for seg in (w["segments"] or []):
            assert seg["height_tag"] in ALLOWED_TAGS, which
            assert seg["height_formula"], which
        if w["gable_triangle_ft"]:
            assert w["gable_tag"] in ALLOWED_TAGS, which
        for o in s["openings"]:
            assert o["position_tag"] in ALLOWED_TAGS, (which, o["tag"])
            assert o["sill_tag"] in ALLOWED_TAGS, (which, o["tag"])
        if s["chase"]:
            assert s["chase"]["tag"] in ALLOWED_TAGS, which
        if s["deviation"]:
            assert s["deviation"]["governs"] == "tape", which


def test_verb_remove_reset_left_vent(session):
    """Verb machinery per-sheet pin (LEFT): user_removed vent row (schedule
    index 4) drops from the sheet; reset restores it."""
    key = f"open:{LETRICK_RUN[:8]}:4"
    url = f"{API}/estimates/{LETRICK_EST}/openings-review"
    r = session.post(url, json={"key": key, "action": "remove"}, timeout=20)
    assert r.status_code == 200, r.text
    try:
        s = _sheet(session, "left")
        assert [o["tag"] for o in s["openings"]] == ["W1"]
        assert s["opening_counts"] == {"windows": 1, "doors": 0, "vents": 0}
    finally:
        rr = session.post(url, json={"key": key, "action": "reset"}, timeout=20)
        assert rr.status_code == 200, rr.text
    s = _sheet(session, "left")
    assert [o["tag"] for o in s["openings"]] == ["V1", "W1"]
    assert s["opening_counts"] == {"windows": 1, "doors": 0, "vents": 1}


def test_verb_remove_reset_back_window_group(session):
    """Verb machinery per-sheet pin (BACK): removing the 36×54 group
    (schedule index 5, 2 members) drops BOTH raw members; cross-wall
    isolation: RIGHT stays empty and 200 throughout; reset restores."""
    key = f"open:{LETRICK_RUN[:8]}:5"
    url = f"{API}/estimates/{LETRICK_EST}/openings-review"
    r = session.post(url, json={"key": key, "action": "remove"}, timeout=20)
    assert r.status_code == 200, r.text
    try:
        s = _sheet(session, "back")
        assert not any(o["height_in"] == 54 for o in s["openings"])
        assert s["opening_counts"] == {"windows": 3, "doors": 1, "vents": 0}
        assert [o["tag"] for o in s["openings"]] == ["D1", "W1", "W2", "W3"]
        # cross-wall isolation
        sr = _sheet(session, "right")
        assert sr["openings"] == []
        sl = _sheet(session, "left")
        assert sl["opening_counts"] == {"windows": 1, "doors": 0, "vents": 1}
    finally:
        rr = session.post(url, json={"key": key, "action": "reset"}, timeout=20)
        assert rr.status_code == 200, rr.text
    s = _sheet(session, "back")
    assert s["opening_counts"] == {"windows": 5, "doors": 1, "vents": 0}


def test_read_only_behavioral_all_sheets(session):
    from pymongo import MongoClient
    import os
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    before = db.estimates.find_one({"id": LETRICK_EST}, {"_id": 0})
    for which in ("left", "back", "right"):
        session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/{which}", timeout=30)
    after = db.estimates.find_one({"id": LETRICK_EST}, {"_id": 0})
    assert before == after
    client.close()
