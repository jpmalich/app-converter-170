"""Iter 78z — Profile annotation overlay.

Verifies `apply_annotations_to_breakdown` injects user-drawn boxes
as authoritative accents and re-aggregates `_per_profile_sqft`
correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from profile_callouts import apply_annotations_to_breakdown


def _base_breakdown():
    """Mock primary breakdown: pure-lap house with 4 elevations."""
    return {
        "per_elevation": [
            {"label": "front", "wall_body_sqft": 500, "wall_body_profile": "lap",
             "gable_sqft": 100, "gable_profile": "lap",
             "dormer_sqft": 0, "dormer_profile": "", "accents": [], "stone_sqft": 0},
            {"label": "right", "wall_body_sqft": 400, "wall_body_profile": "lap",
             "gable_sqft": 0, "gable_profile": "", "dormer_sqft": 0,
             "dormer_profile": "", "accents": [], "stone_sqft": 0},
        ],
        "per_profile_sqft": {"lap": 1000.0},
    }


def test_no_annotations_returns_breakdown_unchanged():
    bd = _base_breakdown()
    out = apply_annotations_to_breakdown(bd, None)
    # Iter 79j.71 — the finalizer now always attaches a composition trace
    # + conflicts, but the numbers must be untouched.
    assert out["per_elevation"] == bd["per_elevation"]
    assert out["per_profile_sqft"] == bd["per_profile_sqft"]
    assert out["conflicts"] == []
    assert "composition" in out
    out2 = apply_annotations_to_breakdown(bd, {})
    assert out2["per_elevation"] == bd["per_elevation"]
    assert out2["per_profile_sqft"] == bd["per_profile_sqft"]


def test_shake_annotation_injects_as_accent():
    """User draws a shake box on the front gable. Should appear as an
    accent on the front elevation AND show up in per_profile_sqft."""
    bd = _base_breakdown()
    annotations = {
        "0": [
            {"elevation_label": "front", "profile": "shake",
             "sqft": 60, "callout": "front gable scallop"},
        ],
    }
    out = apply_annotations_to_breakdown(bd, annotations)
    front = next(e for e in out["per_elevation"] if e["label"] == "front")
    assert len(front["accents"]) == 1
    acc = front["accents"][0]
    assert acc["profile"] == "shake"
    assert acc["sqft"] == 60
    assert acc["_source"] == "annotation"
    # New profile family now in the aggregation
    assert out["per_profile_sqft"]["shake"] == 60.0
    assert out["per_profile_sqft"]["lap"] == 1000.0


def test_multiple_annotations_merge():
    """Two shake boxes + one B&B box. All should appear."""
    bd = _base_breakdown()
    annotations = {
        "0": [
            {"elevation_label": "front", "profile": "shake", "sqft": 60},
            {"elevation_label": "right", "profile": "shake", "sqft": 40},
        ],
        "1": [
            {"elevation_label": "front", "profile": "board_batten",
             "sqft": 48, "callout": "porch face"},
        ],
    }
    out = apply_annotations_to_breakdown(bd, annotations)
    assert out["per_profile_sqft"]["shake"] == 100.0
    assert out["per_profile_sqft"]["board_batten"] == 48.0
    assert out["per_profile_sqft"]["lap"] == 1000.0
    front = next(e for e in out["per_elevation"] if e["label"] == "front")
    assert len(front["accents"]) == 2  # 1 shake + 1 B&B


def test_zero_sqft_annotation_skipped():
    bd = _base_breakdown()
    annotations = {"0": [{"elevation_label": "front", "profile": "shake", "sqft": 0}]}
    out = apply_annotations_to_breakdown(bd, annotations)
    assert "shake" not in out["per_profile_sqft"]


def test_case_insensitive_label_match():
    """User typed elevation label in mixed case — should still match."""
    bd = _base_breakdown()
    annotations = {
        "0": [{"elevation_label": "FRONT", "profile": "shake", "sqft": 60}],
    }
    out = apply_annotations_to_breakdown(bd, annotations)
    front = next(e for e in out["per_elevation"] if e["label"] == "front")
    assert len(front["accents"]) == 1


def test_annotation_on_unknown_elevation_creates_synthetic_row():
    """If user tags an elevation Claude didn't surface, we synthesize
    a row so the accent still hits the catalog mapper."""
    bd = _base_breakdown()
    annotations = {
        "0": [{"elevation_label": "porch", "profile": "shake", "sqft": 30}],
    }
    out = apply_annotations_to_breakdown(bd, annotations)
    # 2 original + 1 synthetic
    assert len(out["per_elevation"]) == 3
    synth = next(e for e in out["per_elevation"] if e["label"] == "porch")
    assert synth["wall_body_sqft"] == 0.0
    assert len(synth["accents"]) == 1
    assert out["per_profile_sqft"]["shake"] == 30.0


def test_non_siding_annotations_dont_emit_accent():
    """Stone / brick / stucco annotations are non-siding — they should
    NOT become a siding accent (the catalog mapper would emit nothing
    for them anyway, but we strip them at the source for cleanliness)."""
    bd = _base_breakdown()
    annotations = {
        "0": [{"elevation_label": "front", "profile": "stone", "sqft": 200}],
    }
    out = apply_annotations_to_breakdown(bd, annotations)
    # No new accents added, no new entry in per_profile_sqft
    front = next(e for e in out["per_elevation"] if e["label"] == "front")
    assert len(front["accents"]) == 0
    assert "stone" not in out["per_profile_sqft"]


def test_scale_refs_key_ignored():
    """The reserved `_scale_refs` key shouldn't be treated as boxes."""
    bd = _base_breakdown()
    annotations = {
        "_scale_refs": {"0": {"px_height": 220, "real_ft": 6.67}},
        "0": [{"elevation_label": "front", "profile": "shake", "sqft": 60}],
    }
    out = apply_annotations_to_breakdown(bd, annotations)
    assert out["per_profile_sqft"]["shake"] == 60.0


def test_unknown_profile_skipped():
    bd = _base_breakdown()
    annotations = {
        "0": [
            {"elevation_label": "front", "profile": "unknown", "sqft": 60},
            {"elevation_label": "front", "profile": "", "sqft": 60},
        ],
    }
    out = apply_annotations_to_breakdown(bd, annotations)
    assert "unknown" not in out["per_profile_sqft"]
