"""STEP 4 SEALS — CONFIDENCE GATE + STARTER UNIFY + PHOTO DOOR IDENTITY
(Howard ruled 2026-08-01, findings 4 + 8 + 9a).
· A substituted height is a zero-confidence read: DISCLOSED on the wall and
  raised on the gate — no silent 18-ft substitution ever again.
· Walls the model marks <50 ("barely visible / inferred") raise the gate.
· Photo starter = wall perimeter + engine door deduction (blueprint rule
  extended), basis note always stamped.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routes.ai_measure import _aggregate_to_hover_shape as photo_agg


def test_substituted_height_is_disclosed_and_gated():
    walls = [{"label": "right", "width_ft": 40, "height_ft": 3.2}]
    m = photo_agg({"walls": walls, "openings": [], "story_count": 2})
    gate = m["_confidence_gate"]
    sub = gate["substituted_walls"][0]
    assert sub["label"] == "right" and sub["read_ft"] == 3.2
    assert sub["substituted_ft"] == 18.0
    # the wall itself carries the disclosure (preview chips read these)
    assert walls[0]["_height_flag"] == "substituted_story_default"
    assert "REPLACED" in walls[0]["_reconciliation_note"]
    assert "zero-confidence" in walls[0]["_reconciliation_note"]


def test_low_confidence_wall_raises_gate_at_model_own_threshold():
    m = photo_agg({"walls": [
        {"label": "left", "width_ft": 30, "height_ft": 9, "confidence": 12,
         "confidence_reasoning": "barely visible behind hedge"},
        {"label": "front", "width_ft": 40, "height_ft": 9, "confidence": 85},
    ], "openings": []})
    lows = m["_confidence_gate"]["low_confidence_walls"]
    assert [w["label"] for w in lows] == ["left"]
    assert lows[0]["confidence"] == 12 and "hedge" in lows[0]["reasoning"]


def test_low_scale_confidence_raises_gate():
    m = photo_agg({"walls": [{"label": "front", "width_ft": 40, "height_ft": 9}],
                   "openings": [], "scale_confidence": "low"})
    assert m["_confidence_gate"]["scale_confidence"] == "low"


def test_clean_run_raises_no_gate():
    m = photo_agg({"walls": [
        {"label": "front", "width_ft": 40, "height_ft": 9, "confidence": 90}],
        "openings": [], "scale_confidence": "high"})
    assert "_confidence_gate" not in m


def test_photo_starter_unifies_to_perimeter_plus_deduction():
    """Finding 8 (ruled): perimeter basis, blueprint rule extended. The
    eaves fallback that shorted both gable ends is retired to last resort."""
    m = photo_agg({"walls": [
        {"label": "front", "width_ft": 32, "height_ft": 9},
        {"label": "back", "width_ft": 32, "height_ft": 9},
        {"label": "left", "width_ft": 32, "height_ft": 9},
        {"label": "right", "width_ft": 32, "height_ft": 9}],
        "openings": [], "eaves_lf": 103, "starter_lf": 0})
    assert m["starter_lf"] == 128                       # perimeter, not eaves 103
    assert "perimeter" in m["_starter_basis"]
    assert "entry-door widths" in m["_starter_basis"]   # engine deduction named
    # ladder rung 2: no walls → AI-read starter
    m2 = photo_agg({"walls": [], "openings": [], "starter_lf": 88, "eaves_lf": 70})
    assert m2["starter_lf"] == 88 and "AI-read" in m2["_starter_basis"]
    # last resort: eaves, named as legacy
    m3 = photo_agg({"walls": [], "openings": [], "eaves_lf": 70})
    assert m3["starter_lf"] == 70 and "last resort" in m3["_starter_basis"]
