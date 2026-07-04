"""Iter 79j.41 — Dormers as ARRAY end-to-end.

Root cause of the missing right-slope dormer on Howard's red house
was a singular `dormer` object all the way through the pipeline:
prompt → raw JSON → aggregator → 3D viewer. Every additional dormer
past the first was silently dropped.

This test locks the array shape at three layers:

  1. RECONCILE_PROMPT + SYSTEM_PROMPT — must ask Claude for `dormers[]`
     (not `dormer` singular).
  2. `_aggregate_to_hover_shape` — must emit `measurements._ai_dormers`
     as a list, with legacy `_ai_dormer` as the first entry only.
  3. `apply_roof_type_material_math` — must iterate the full list and
     credit face/cheek sqft for each dormer.

Acceptance the user asked for: a reconciled raw with 2 dormer entries
(one on each slope) produces 2 rows in `measurements._ai_dormers` and
adds face+cheek sqft for BOTH to `dormer_sqft`.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    RECONCILE_PROMPT,
    SYSTEM_PROMPT,
    _aggregate_to_hover_shape,
)


# ---------------------------------------------------------------------
# PROMPT — both prompts must ask for the ARRAY
# ---------------------------------------------------------------------

def test_reconcile_prompt_requests_dormers_array():
    p = RECONCILE_PROMPT
    p_flat = " ".join(p.split())
    # The array key must exist.
    assert '"dormers":' in p
    # Rule 5 header must be plural.
    assert "DORMERS (ARRAY)" in p
    # Must explicitly forbid collapsing to a single object.
    assert "ONE ENTRY PER PHYSICAL DORMER" in p_flat
    # Must call out the red-house symptom the bug produced.
    assert "missing right dormer" in p or "missing right dormer" in p_flat


def test_reconcile_prompt_never_collapses_different_face_dormers():
    p_flat = " ".join(RECONCILE_PROMPT.split())
    # Explicit ban on merging different-face dormers.
    assert "TWO DIFFERENT dormers" in p_flat or "two entries" in p_flat.lower()
    assert "Never collapse different-face dormers" in p_flat


def test_single_call_prompt_also_emits_dormers_array():
    """SYSTEM_PROMPT is used when AI_MEASURE_TWO_PHASE=0. It must also
    request dormers[] so both paths behave the same."""
    assert '"dormers":' in SYSTEM_PROMPT
    sp_flat = " ".join(SYSTEM_PROMPT.split())
    assert "one entry per PHYSICAL dormer" in sp_flat


# ---------------------------------------------------------------------
# AGGREGATOR — reads dormers[] and preserves both
# ---------------------------------------------------------------------

def _mk_raw(*, dormers=None, legacy_dormer=None, roof_type="gable-shed-dormer", walls=None):
    return {
        "scale_confidence": "high",
        "reference_used": "test",
        "story_count": 2,
        "avg_wall_height_ft": 9.0,
        "siding_coverage_pct": 100,
        "roof_type": roof_type,
        "roof_type_confidence": 1.0,
        "dormers": dormers,
        "dormer": legacy_dormer,
        "walls": walls or [
            {"label": "front", "width_ft": 40, "height_ft": 9,
             "gable_triangle_height_ft": 0, "dormer_face_sqft": 0,
             "siding_pct_this_wall": 100},
            {"label": "back", "width_ft": 40, "height_ft": 9,
             "gable_triangle_height_ft": 0, "dormer_face_sqft": 0,
             "siding_pct_this_wall": 100},
            {"label": "left", "width_ft": 30, "height_ft": 9,
             "gable_triangle_height_ft": 6, "dormer_face_sqft": 0,
             "siding_pct_this_wall": 100},
            {"label": "right", "width_ft": 30, "height_ft": 9,
             "gable_triangle_height_ft": 6, "dormer_face_sqft": 0,
             "siding_pct_this_wall": 100},
        ],
        "openings": [],
        "openings_schedule": [],
        "eaves_lf": 80, "rakes_lf": 60, "starter_lf": 80,
        "outside_corner_lf": 36, "inside_corner_lf": 0,
        "dominant_colors": {},
    }


def test_aggregator_preserves_both_dormers_from_array():
    """The red-house acceptance case: 2 dormer entries on opposite
    roof slopes must BOTH end up in _ai_dormers."""
    raw = _mk_raw(dormers=[
        {"face": "front", "width_ft": 12, "knee_wall_height_ft": 4,
         "offset_x_ft": 0, "width_source": "direct_consensus"},
        {"face": "rear",  "width_ft": 10, "knee_wall_height_ft": 4,
         "offset_x_ft": 0, "width_source": "back_solved_from_opening"},
    ])
    m = _aggregate_to_hover_shape(raw)
    assert isinstance(m["_ai_dormers"], list)
    assert len(m["_ai_dormers"]) == 2
    faces = sorted(d["face"] for d in m["_ai_dormers"])
    assert faces == ["front", "rear"]
    # Legacy singular field points at the first entry.
    assert m["_ai_dormer"] is not None
    assert m["_ai_dormer"]["face"] == "front"


def test_aggregator_wraps_legacy_singular_into_array():
    """When Claude returns a lone `dormer` (legacy path), the aggregator
    must wrap it as _ai_dormers=[that] so downstream code has a uniform
    shape."""
    raw = _mk_raw(dormers=None, legacy_dormer={
        "face": "front", "width_ft": 12, "knee_wall_height_ft": 4,
        "offset_x_ft": 0,
    })
    m = _aggregate_to_hover_shape(raw)
    assert m["_ai_dormers"] == [raw["dormer"]]
    assert m["_ai_dormer"] is raw["dormer"]


def test_aggregator_material_math_credits_both_dormers():
    """apply_roof_type_material_math must sum face + cheek sqft
    across the WHOLE dormer list, not just the first. Silently
    ignoring the second under-quotes the takeoff by dormer #2's
    material."""
    raw = _mk_raw(dormers=[
        # 12 ft × 4 ft face + 2 cheek triangles = 48 + 16 = 64 ft²
        {"face": "front", "width_ft": 12, "knee_wall_height_ft": 4, "offset_x_ft": 0},
        # 10 ft × 4 ft face + 2 cheek triangles = 40 + 16 = 56 ft²
        {"face": "rear",  "width_ft": 10, "knee_wall_height_ft": 4, "offset_x_ft": 0},
    ])
    # Aggregator applies the material math; result goes onto walls[]
    # (per-elevation) and into _per_elevation_breakdown.
    _aggregate_to_hover_shape(raw)
    walls_by_label = {w["label"]: w for w in raw["walls"]}
    front_dsqft = float(walls_by_label["front"].get("dormer_face_sqft") or 0)
    rear_dsqft = float(walls_by_label["back"].get("dormer_face_sqft") or 0)  # aggregator maps rear→back
    # Front should have gained ~64 ft²
    assert 60 <= front_dsqft <= 68, (
        f"front dormer material missing — front got {front_dsqft:.1f} ft², expected ≈64"
    )
    # Rear should have gained ~56 ft²
    assert 52 <= rear_dsqft <= 60, (
        f"rear dormer material missing — this is the red-house 'missing right dormer' regression. "
        f"back wall got {rear_dsqft:.1f} ft², expected ≈56"
    )


def test_aggregator_empty_dormers_list_is_safe():
    """No dormers → _ai_dormers = [], _ai_dormer = None. No crash."""
    raw = _mk_raw(dormers=[], legacy_dormer=None, roof_type="gable")
    m = _aggregate_to_hover_shape(raw)
    assert m["_ai_dormers"] == []
    assert m["_ai_dormer"] is None
