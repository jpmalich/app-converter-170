"""Iter 79j.43 — Run1 defect fixes.

Four defects surfaced by the run-1 trace analysis:
  1. Silent empty extractions (Phase A returned nothing for photo 2/7)
     → orchestrator must retry once and, if still empty, surface a
     UI-visible warning naming the photo + orphaned walls.
  2. Dormer width display bug (reconciled 18 ft rendered as 7.2 with a
     green DIRECT badge) → width value cascade must respect the
     AI-provided `width_source` and never silently swap in a
     client-derived guess.
  3. Dormer scan openings misassigned to the wall + face sf not
     credited → `_merge_dormer_hits` must set `on_dormer=True`, mint
     a stable opening_id, populate `_source_photo_indices`, and
     synthesise a face_sqft estimate when Claude returns 0.
  4. `direct_consensus` tag was applied to a SINGLE-photo reading →
     schema now enumerates `direct_single_reading` (amber) as its
     own value, reserving `direct_consensus` for 2+ agreeing readings.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))


def _mod():
    if "routes.ai_measure" in sys.modules:
        del sys.modules["routes.ai_measure"]
    return importlib.import_module("routes.ai_measure")


# ------------------------------------------------------------------ #
# 1. Empty extraction detection                                      #
# ------------------------------------------------------------------ #
def test_is_empty_extraction_detects_all_empty():
    m = _mod()
    assert m._is_empty_extraction({}) is True
    assert m._is_empty_extraction({"index": 0}) is True
    assert m._is_empty_extraction({"index": 0, "walls_visible": []}) is True
    assert m._is_empty_extraction({"index": 0, "walls_visible": [""]}) is True
    assert m._is_empty_extraction({"index": 0, "openings_this_photo": []}) is True
    assert m._is_empty_extraction({"index": 0, "dormers_observed_count": 0}) is True


def test_is_empty_extraction_ignores_true_extraction():
    m = _mod()
    assert m._is_empty_extraction({"index": 0, "walls_visible": ["front"]}) is False
    assert m._is_empty_extraction({"index": 0, "openings_this_photo": [{"type": "window"}]}) is False
    assert m._is_empty_extraction({"index": 0, "eave_height_ft_observed": 8.5}) is False
    assert m._is_empty_extraction({"index": 0, "pitch_ratio_observed": 6}) is False
    assert m._is_empty_extraction({"index": 0, "gable_triangle_height_ft_observed": 4}) is False
    assert m._is_empty_extraction({"index": 0, "dormers_observed_count": 1}) is False


def test_is_empty_extraction_flags_extraction_errors():
    m = _mod()
    assert m._is_empty_extraction({"_extraction_error": "timeout"}) is True


# ------------------------------------------------------------------ #
# 2 & 3. Dormer-scan merge — attachment + face sf crediting          #
# ------------------------------------------------------------------ #
def test_merge_dormer_hits_tags_on_dormer_and_opening_id():
    m = _mod()
    raw = {"openings": [], "walls": [{"label": "front", "width_ft": 30}]}
    hits = [
        {
            "type": "dormer",
            "width_in": 30,
            "height_in": 42,
            "wall": "front",
            "dormer_face_sqft": 40,
            "_photo_index": 3,
        }
    ]
    m._merge_dormer_hits(raw, hits)
    ops = raw["openings"]
    assert len(ops) == 1, "hit should be appended as an opening"
    op = ops[0]
    assert op["on_dormer"] is True, "dormer-scan hits MUST be tagged on_dormer=True"
    assert op["opening_id"].startswith("dormer_scan_"), "must mint stable opening_id"
    assert "along_wall_ft" in op, "must populate along_wall_ft field (even null)"
    assert op["along_wall_ft"] is None
    assert op["photo_idx"] == 3
    assert op["_source_photo_indices"] == [3]
    assert op["_via_dormer_scan"] is True
    # Face sf crediting on the wall.
    front = next(w for w in raw["walls"] if w["label"] == "front")
    assert front["dormer_face_sqft"] == 40


def test_merge_dormer_hits_synthesizes_face_sf_when_zero():
    """If Claude returns valid width/height but 0 face_sqft, we still
    must credit an estimated face area — an empty
    dormer_scan_added_sf_by_wall map was the run-1 bug."""
    m = _mod()
    raw = {"openings": [], "walls": [{"label": "front", "width_ft": 30}]}
    hits = [
        {
            "type": "dormer",
            "width_in": 36,
            "height_in": 48,
            "wall": "front",
            "dormer_face_sqft": 0,
            "_photo_index": 2,
        }
    ]
    m._merge_dormer_hits(raw, hits)
    assert raw["dormer_scan_synthesized_face_sf"] is True
    assert "front" in raw["dormer_scan_added_sf_by_wall"]
    sf = raw["dormer_scan_added_sf_by_wall"]["front"]
    assert 16.0 <= sf <= 72.0, f"estimated face_sqft should fall in 16-72 band, got {sf}"
    front = next(w for w in raw["walls"] if w["label"] == "front")
    assert front["dormer_face_sqft"] == sf


def test_merge_dormer_hits_preserves_multiple_hits():
    m = _mod()
    raw = {"openings": [], "walls": [
        {"label": "front", "width_ft": 30},
        {"label": "back", "width_ft": 30},
    ]}
    hits = [
        {"type": "dormer", "width_in": 30, "height_in": 42, "wall": "front",
         "dormer_face_sqft": 40, "_photo_index": 1},
        {"type": "dormer", "width_in": 30, "height_in": 42, "wall": "back",
         "dormer_face_sqft": 40, "_photo_index": 4},
    ]
    m._merge_dormer_hits(raw, hits)
    assert len(raw["openings"]) == 2
    # Each opening must carry a UNIQUE opening_id.
    ids = {o["opening_id"] for o in raw["openings"]}
    assert len(ids) == 2
    # Each opening must attach to the right dormer face wall.
    front_op = next(o for o in raw["openings"] if o["wall"] == "front")
    back_op = next(o for o in raw["openings"] if o["wall"] == "back")
    assert front_op["photo_idx"] == 1
    assert back_op["photo_idx"] == 4
    assert front_op["on_dormer"] is True and back_op["on_dormer"] is True


# ------------------------------------------------------------------ #
# 4. RECONCILE_PROMPT — single-reading + consensus + tag enumeration #
# ------------------------------------------------------------------ #
def test_reconcile_prompt_enumerates_direct_single_reading():
    """Schema and rules must list `direct_single_reading` alongside
    the other width_source values so the reconciler emits the right
    tag when only one photo cardinally read a dormer."""
    m = _mod()
    prompt = m.RECONCILE_PROMPT
    assert "direct_single_reading" in prompt
    # Dormer width_source enumeration includes the new tag.
    assert '"width_source":        "direct_consensus" | "direct_single_reading"' in prompt
    # Eave height_ft_source enumeration includes the new tag.
    assert '"height_ft_source":           "direct_consensus" | "direct_single_reading"' in prompt


def test_reconcile_prompt_requires_two_readings_for_direct_consensus():
    """The rule text must be explicit that direct_consensus requires
    at LEAST 2 readings. A lone reading trivially agrees with itself
    and would over-promise green in the UI."""
    m = _mod()
    prompt = m.RECONCILE_PROMPT
    # Eave rule (rule 1) — 2+ readings for consensus.
    assert "TWO OR MORE direct readings agree" in prompt
    assert "EXACTLY ONE direct-view reading" in prompt


# ------------------------------------------------------------------ #
# 5. Two-phase orchestrator — empty-photo metadata surfaces          #
# ------------------------------------------------------------------ #
def test_aggregate_surfaces_empty_photos_meta():
    """_aggregate_to_hover_shape passes _empty_photos + _orphaned_walls
    through as measurements[_ai_empty_photos / _ai_orphaned_walls] so
    the frontend banner has the data it needs."""
    m = _mod()
    raw = {
        "walls": [
            {"label": "front", "width_ft": 30, "height_ft": 9, "gable_triangle_height_ft": 0,
             "dormer_face_sqft": 0, "siding_pct_this_wall": 100, "confidence": 90},
        ],
        "openings": [],
        "avg_wall_height_ft": 9,
        "_empty_photos": [{"photo_idx": 2, "reason": "empty"}],
        "_orphaned_walls": ["left"],
    }
    measurements = m._aggregate_to_hover_shape(raw)
    assert measurements.get("_ai_empty_photos") == [{"photo_idx": 2, "reason": "empty"}]
    assert measurements.get("_ai_orphaned_walls") == ["left"]


def test_aggregate_omits_empty_metadata_on_healthy_run():
    m = _mod()
    raw = {
        "walls": [
            {"label": "front", "width_ft": 30, "height_ft": 9, "gable_triangle_height_ft": 0,
             "dormer_face_sqft": 0, "siding_pct_this_wall": 100, "confidence": 90},
        ],
        "openings": [],
        "avg_wall_height_ft": 9,
    }
    measurements = m._aggregate_to_hover_shape(raw)
    assert measurements.get("_ai_empty_photos") == []
    assert measurements.get("_ai_orphaned_walls") == []
