"""P3 ROOFLINE pins (ruled 2026-07-21) — rooflines on every elevation.

Rules pinned:
  • eave views carry roofline kind=eave_ridge: ridge = THIS view's eave +
    gable rise; disagreeing side reads drawn at WORST CASE and flagged,
    never averaged; tag ESTIMATED (derived) per C-3.
  • gable ends carry kind=gable_end: apex ridge = own eave + own rise.
  • hip roofs: kind=hip_unreconciled, NAMED limitation — never a guess.
  • no rise reads: kind=none_readable, named empty state.
  • basis strings composed from the reads — nothing hardcoded.
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from routes.elevation_sheets import _bind_roofline  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"


def _raw(roof_type="gable", left_rise=8.0, right_rise=8.0,
         left_src="direct_ref", right_src="direct_ref"):
    return {"roof_type": roof_type, "walls": [
        {"label": "front", "height_ft": 9.0, "gable_triangle_height_ft": 0,
         "height_ft_source": "direct_ref"},
        {"label": "back", "height_ft": 9.0, "gable_triangle_height_ft": 0,
         "height_ft_source": "direct_ref"},
        {"label": "left", "height_ft": 9.0, "gable_triangle_height_ft": left_rise,
         "height_ft_source": left_src},
        {"label": "right", "height_ft": 9.0, "gable_triangle_height_ft": right_rise,
         "height_ft_source": right_src},
    ]}


def test_hip_named_limitation_never_a_guess():
    out = _bind_roofline(_raw(roof_type="hip"), "front", 9.0, "TAPED")
    assert out["kind"] == "hip_unreconciled"
    assert "PITCH NOT YET RECONCILED" in out["note"] and "NOT DRAWN" in out["note"]
    assert "ridge_ft" not in out  # nothing drawn, nothing guessed


def test_no_rise_reads_named_empty_state():
    raw = _raw(left_rise=0, right_rise=0)
    out = _bind_roofline(raw, "front", 9.0, "TAPED")
    assert out["kind"] == "none_readable" and "NO GABLE RISE READ" in out["note"]


def test_eave_ridge_consensus_no_flag():
    out = _bind_roofline(_raw(left_rise=8.0, right_rise=8.0), "front", 9.0, "TAPED")
    assert out["kind"] == "eave_ridge" and out["ridge_ft"] == 17.0
    assert out["tag"] == "ESTIMATED" and "note" not in out
    assert "eave TAPED" in out["basis"] and "DERIVED" in out["basis"]


def test_eave_ridge_disagreement_worst_case_flagged_never_averaged():
    out = _bind_roofline(_raw(left_rise=8.0, right_rise=9.0), "front", 9.0, "TAPED")
    assert out["ridge_ft"] == 18.0  # worst case (max), NOT the 8.5 average
    assert "disagree" in out["note"] and "flagged, not averaged" in out["note"]
    assert "left 8'-0\"" in out["note"] and "right 9'-0\"" in out["note"]


def test_gable_end_uses_own_rise():
    out = _bind_roofline(_raw(left_rise=8.8, right_rise=9.3), "left", 9.92, "TAPED-DERIVED")
    assert out["kind"] == "gable_end" and out["ridge_ft"] == 18.72
    assert "own gable rise" in out["basis"]


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
    assert r.status_code == 200, r.text
    return r.json()


def test_letrick_every_sheet_carries_a_roofline(session):
    """Acceptance (Howard, P2 field-compare): BACK shows eave+ridge;
    SIDES show true rakes. Letrick pin data: rises left 8.8 / right 9.3
    (disagreement — worst case 9.3 governs eave views, flagged)."""
    f = _sheet(session, "front")
    assert f["roofline"]["kind"] == "eave_ridge"
    assert f["roofline"]["ridge_ft"] == round(8.854 + 9.3, 3)
    assert "disagree" in f["roofline"]["note"]
    b = _sheet(session, "back")
    assert b["roofline"]["kind"] == "eave_ridge"
    assert b["roofline"]["ridge_ft"] == round(9.92 + 9.3, 3)
    lt = _sheet(session, "left")
    assert lt["roofline"]["kind"] == "gable_end"
    assert lt["roofline"]["ridge_ft"] == round(9.92 + 8.8, 3)
    rt = _sheet(session, "right")
    assert rt["roofline"]["kind"] == "gable_end"
    assert rt["roofline"]["ridge_ft"] == round(9.92 + 9.3, 3)
    for s in (f, b, lt, rt):
        assert s["roofline"]["tag"] == "ESTIMATED"
        assert "DERIVED" in s["roofline"]["basis"]
