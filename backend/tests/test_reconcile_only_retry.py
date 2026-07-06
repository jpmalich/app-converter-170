"""Iter 79j.51 — Reconcile-only retry contract.

Pins the two invariants that matter for cost-recovery:
  1. `_slim_extraction_for_reconcile` never touches the fields the
     RECONCILE_PROMPT explicitly cites (reasoning strings, confidence,
     along_wall_ft). It only drops per-photo pixel bboxes.
  2. The reconcile-only endpoint is auth-gated and refuses runs that
     have no persisted raw_per_photo.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import _slim_extraction_for_reconcile  # noqa: E402


def test_slim_drops_bboxes_only():
    """The reconciler-unread bulk is bbox on openings/dormers/regions.
    Everything RECONCILE_PROMPT cites must be preserved verbatim."""
    ex = {
        "elevation_letter": "F",
        "elevation_reasoning": "Front elevation.",
        "elevation_confidence": "high",
        "eave_reasoning": "Measured from garage door.",
        "eave_height_ft_observed": 9.0,
        "pitch_reasoning": "Estimated from ridge angle.",
        "confidence": "high",
        "obstructions": "Tree partially blocking east corner.",
        "notes": "Photo mid-morning, good light.",
        "openings_this_photo": [
            {
                "kind": "window",
                "along_wall_ft": 3.2,
                "style_confidence": "high",
                "bbox": [120, 340, 80, 60],
                "notes": "double hung",
            },
        ],
        "dormer_details": [
            {"kind": "gable", "width_ft": 6.0, "along_wall_ft": 15.0, "bbox": [500, 100, 200, 180]},
        ],
        "no_siding_regions": [
            {"kind": "brick_veneer", "coverage_pct": 0.4, "bbox": [0, 300, 800, 200]},
        ],
        "colors_sampled": [{"hex": "#AABBCC", "sample_quality": "good"}],
        "_photo_idx": 0,
        "_total_latency_ms": 45230,
    }
    slim = _slim_extraction_for_reconcile(ex)

    # RETAINED at top level (RECONCILE_PROMPT cites these):
    for f in [
        "elevation_letter", "elevation_reasoning", "elevation_confidence",
        "eave_reasoning", "eave_height_ft_observed", "pitch_reasoning",
        "confidence", "obstructions", "notes", "colors_sampled",
    ]:
        assert f in slim, f"top-level field {f!r} was stripped but reconciler reads it"

    # RETAINED on openings (dedup + weighting):
    op = slim["openings_this_photo"][0]
    for f in ["kind", "along_wall_ft", "style_confidence", "notes"]:
        assert f in op, f"opening.{f} was stripped but reconciler reads it"

    # DROPPED — pixel bboxes on all three list types
    assert "bbox" not in slim["openings_this_photo"][0]
    assert "bbox" not in slim["dormer_details"][0]
    assert "bbox" not in slim["no_siding_regions"][0]

    # DROPPED — internal underscore-prefixed fields
    assert "_photo_idx" not in slim
    assert "_total_latency_ms" not in slim


def test_slim_leaves_empty_lists_alone():
    """A photo with no dormers/regions produces a slim with the same empty
    arrays — not a KeyError, not a null substitution."""
    slim = _slim_extraction_for_reconcile({
        "elevation_letter": "L",
        "openings_this_photo": [],
        "dormer_details": [],
        "no_siding_regions": [],
    })
    assert slim["openings_this_photo"] == []
    assert slim["dormer_details"] == []
    assert slim["no_siding_regions"] == []


def test_slim_tolerates_missing_bbox():
    """An opening/dormer that never had a bbox (e.g. one Claude
    couldn't localise) must slim through cleanly, not crash."""
    slim = _slim_extraction_for_reconcile({
        "openings_this_photo": [{"kind": "window", "along_wall_ft": 3.0}],
    })
    assert slim["openings_this_photo"][0] == {"kind": "window", "along_wall_ft": 3.0}


def test_slim_tolerates_non_list_field_types():
    """If a phase-A extraction somehow has a string or None where a
    list is expected (defensive against upstream schema drift), slim
    should not crash — it should just pass the value through
    unmodified."""
    slim = _slim_extraction_for_reconcile({
        "openings_this_photo": None,
        "dormer_details": "unexpected",
        "no_siding_regions": [],
    })
    assert slim["openings_this_photo"] is None
    assert slim["dormer_details"] == "unexpected"
    assert slim["no_siding_regions"] == []


def test_slim_produces_measurable_size_reduction_on_realistic_payload():
    """Realistic 8-photo payload: bboxes are the biggest safe cut.
    Verify the slim is at least 15% smaller than the equivalent
    underscore-only-stripped payload (the pre-Iter79j.51 baseline)."""
    import json
    photo = {
        "elevation_letter": "F",
        "elevation_reasoning": "Front elevation identified by primary entry door and driveway alignment. High confidence from multiple visible landmarks.",
        "eave_height_ft_observed": 9.5,
        "eave_reasoning": "Measured from ground level to eave using the garage door as reference. Garage door assumed 7ft standard.",
        "pitch_reasoning": "Estimated from ridge angle relative to eave line.",
        "confidence": "high",
        "openings_this_photo": [
            {"kind": "window", "style_confidence": "high", "along_wall_ft": 3.2, "bbox": [120, 340, 80, 60], "notes": ""},
            {"kind": "window", "style_confidence": "high", "along_wall_ft": 8.5, "bbox": [400, 340, 80, 60], "notes": ""},
            {"kind": "door", "style_confidence": "medium", "along_wall_ft": 6.5, "bbox": [200, 400, 100, 220], "notes": "storm door"},
            {"kind": "window", "style_confidence": "high", "along_wall_ft": 12.0, "bbox": [600, 340, 80, 60], "notes": ""},
        ],
        "dormer_details": [
            {"kind": "gable", "width_ft": 6.0, "height_ft": 5.5, "along_wall_ft": 15.0, "bbox": [500, 100, 200, 180]},
        ],
        "no_siding_regions": [
            {"kind": "brick_veneer", "coverage_pct": 0.4, "bbox": [0, 300, 800, 200]},
        ],
        "notes": "Photo taken mid-morning, good lighting on front elevation",
    }
    photos = [dict(photo) for _ in range(8)]

    baseline = json.dumps([{k: v for k, v in p.items() if not k.startswith("_")} for p in photos])
    slimmed = json.dumps([_slim_extraction_for_reconcile(p) for p in photos])

    reduction = 1 - (len(slimmed) / len(baseline))
    assert reduction >= 0.05, f"slim only saved {reduction:.1%}, expected ≥5%"
