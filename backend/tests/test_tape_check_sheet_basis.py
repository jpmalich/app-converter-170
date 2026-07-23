"""Tape check → sheet basis wiring (ruled 2026-07-23, P5 close-out).

Standing geometry-source rule: tape-validated values govern wherever
they exist, sealed key or not. Before this ruling the sheets only bound
the SEALED KEY tape (Letrick); on keyless estimates the contractor's
Tape Check entries (Field Verify · ground truth) never reached the
sheet basis — a gap against the rule. Pins:

  • red house LEFT: siding height BINDS the tape check — 10.666'
    (10'-8") @ siding start datum, TAPED tag, tape-check formula +
    geometry-basis line; the AI's 9.4' read stays ON RECORD as the
    flagged deviation (governs: tape, basis_word "tape check")
  • width stays untaped — the tape check records heights only:
    extraction-run fallback, LABELED "width untaped"
  • red house BACK + RIGHT: stepped tape (7.17' / 10.67') — BOTH
    segments render, each TAPED with its own formula; step location
    honestly NOT TAPED; area not derivable
  • dormer rung STANDS: rows deliberately left empty (roof-plane dims
    not safely tapeable from grade) — ESTIMATED · PAIRED-RECONCILED
    band 10.34–15.34 untouched by the wall tape pass
  • ladder order: sealed key OUTRANKS tape check (Letrick unchanged)
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
REDHOUSE_EST = "673707d5-9b7e-4d8f-8eaf-63c86820f611"   # EST-910869
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"    # EST-373526 (sealed key)


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


def test_left_height_binds_tape_check(session):
    s = _sheet(session, "left")
    w = s["wall"]
    assert w["height_ft"] == pytest.approx(10.666, abs=0.001)
    assert w["height_label"] == "10'-8\""
    assert w["height_tag"] == "TAPED"
    assert "tape check" in w["height_formula"]
    assert "siding start" in w["height_formula"]
    assert "tape check" in s["geometry_basis"]["walls"]
    assert "field verify" in s["geometry_basis"]["walls"]


def test_left_width_stays_untaped_labeled(session):
    w = _sheet(session, "left")["wall"]
    assert w["width_tag"] != "TAPED"
    assert "width untaped" in w["width_source"]
    assert "width AI run" in _sheet(session, "left")["geometry_basis"]["walls"]


def test_left_ai_read_flagged_as_deviation(session):
    d = _sheet(session, "left")["deviation"]
    assert d is not None
    assert d["governs"] == "tape"
    assert d["basis_word"] == "tape check"
    # AI read 9.4' vs tape 10.666' — the honest record stands
    assert d["ai_height_ft"] == pytest.approx(9.4, abs=0.2)
    assert d["tape_heights_label"] == "10'-8\""


def test_back_stepped_both_segments_taped(session):
    s = _sheet(session, "back")
    w = s["wall"]
    segs = w["segments"]
    assert len(segs) == 2
    assert sorted(x["height_ft"] for x in segs) == [
        pytest.approx(7.166, abs=0.001), pytest.approx(10.666, abs=0.001)]
    assert all(x["height_tag"] == "TAPED" for x in segs)
    assert all("tape check" in x["height_formula"] for x in segs)
    assert w["step_note"] is not None and "NOT TAPED" in w["step_note"]
    assert w["area_sqft"] is None
    assert "step location untaped" in w["area_note"]


def test_right_stepped_both_segments_taped(session):
    w = _sheet(session, "right")["wall"]
    segs = w["segments"]
    assert len(segs) == 2
    assert sorted(x["height_ft"] for x in segs) == [
        pytest.approx(7.16, abs=0.001), pytest.approx(10.666, abs=0.001)]
    assert all(x["height_tag"] == "TAPED" for x in segs)


def test_front_height_binds_tape_check(session):
    w = _sheet(session, "front")["wall"]
    assert w["height_ft"] == pytest.approx(10.666, abs=0.001)
    assert w["height_tag"] == "TAPED"


def test_dormer_estimated_rung_stands(session):
    """Dormer rows deliberately left empty (roof-plane dims not safely
    tapeable from grade) — the ESTIMATED · PAIRED-RECONCILED rung stands
    per the ladder doctrine, untouched by the wall tape pass."""
    d = _sheet(session, "left")["dormer"]
    assert d["base_ft"] == pytest.approx(10.34, abs=0.01)
    assert d["top_ft"] == pytest.approx(15.34, abs=0.01)
    assert "PAIRED-RECONCILED" in d["vpos_tag"]
    assert "TAPED" not in d["vpos_tag"]


def test_sealed_key_outranks_tape_check(session):
    """Ladder order pinned: on the sealed-key estimate the key still
    governs — tape-check wiring changes nothing for Letrick."""
    s = _sheet(session, "back", est=LETRICK_EST)
    w = s["wall"]
    assert w["height_tag"] == "TAPED-DERIVED"
    assert w["width_tag"] == "TAPED"
    assert "EST-191890" in s["geometry_basis"]["walls"]
    assert "tape check" not in s["geometry_basis"]["walls"]


# ---------- human course count (ruled 2026-07-23) ----------

def test_human_course_count_governs_exposure(session):
    """HUMAN COURSE COUNT — ground truth entered on the record (Howard,
    on-site): LEFT wall = 33 full + 1 cut. Exposure derives from the
    human total against the TAPED height: 127.99"/34 = 3.76" — CONFIRMS
    the fixture's known 3.75". Basis 'human-counted'; the AI's 29 is an
    under-count and prints as the flagged comparison, not truth."""
    w = _sheet(session, "left")["wall"]
    assert w["courses"] == 34
    assert w["courses_label"] == "33 + 1 cut"
    assert w["exposure_in"] == pytest.approx(3.76, abs=0.01)
    assert w["exposure_basis"] == "human-counted"
    assert "flagged under-count" in w["ai_count_note"]
    assert "29" in w["ai_count_note"] and "33 + 1 cut" in w["ai_count_note"]


def test_human_count_undercount_on_accuracy_record(session):
    """The under-count lands in the accuracy history via the scoring
    machinery (no hand-edits): Δc = 29 − 34 = −5, tape side labeled
    '33 + 1 cut', accuracy pct unchanged (95.2 — course delta is a
    first-class metric alongside, not inside, the height score)."""
    r = session.get(f"{API}/estimates/{REDHOUSE_EST}/tape-check", timeout=20)
    assert r.status_code == 200
    hist = r.json()["history"]
    assert hist, "no scored runs on record"
    left = hist[-1]["walls"]["left"]
    assert left["ai_courses"] == 29
    assert left["tape_courses"] == 34
    assert left["tape_courses_label"] == "33 + 1 cut"
    assert left["course_delta"] == -5
    assert hist[-1]["accuracy_pct"] == 95.2


def test_courses_entry_path_validation(session):
    """The COUNT affordance validates: cut_courses 0-4, courses 1-200 —
    junk rejected, the stored record never carries a synthesized shape."""
    r = session.put(f"{API}/estimates/{REDHOUSE_EST}/tape-check", json={
        "walls": {"left": {"segments": [{"height_ft": 10.0, "courses": 30, "cut_courses": 9}]}},
    }, timeout=20)
    assert r.status_code == 400 and "cut_courses" in r.text
    r = session.put(f"{API}/estimates/{REDHOUSE_EST}/tape-check", json={
        "walls": {"left": {"segments": [{"height_ft": 10.0, "cut_courses": "x"}]}},
    }, timeout=20)
    assert r.status_code == 400


def test_tape_panel_jsx_courses_affordance():
    """Click path pinned: the Tape Check panel carries a human course
    count input per wall (and per segment on stepped walls), parsed as
    '33' or '33+1' — the entry path Howard uses himself."""
    jsx = Path("/app/frontend/src/components/estimate/TapeCheckPanel.jsx").read_text()
    assert 'data-testid={`tape-check-courses-${w}`}' in jsx
    assert 'data-testid={`tape-check-courses2-${w}`}' in jsx
    assert "cut_courses" in jsx
    sheet_jsx = Path("/app/frontend/src/pages/ElevationSheet.jsx").read_text()
    assert 'data-testid="elevation-ai-count-flag"' in sheet_jsx
    assert "human-counted" in sheet_jsx
