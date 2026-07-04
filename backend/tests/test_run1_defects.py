"""Iter 79j.43 — Run1 defect fixes.

Four defects surfaced by the run-1 trace analysis:
  1. Silent empty extractions (Phase A returned nothing for photo 2/7)
     → orchestrator must retry once and, if still empty, surface a
     UI-visible warning naming the photo + orphaned walls.
  2. Dormer width display bug (reconciled 18 ft rendered as 7.2 with a
     green DIRECT badge) → width value cascade must respect the
     AI-provided `width_source` and never silently swap in a
     client-derived guess.
  3. Dormer scan subsystem removed in Iter 79j.44 — Phase A/B now owns
     dormer detection end-to-end. Prior test cases for
     `_merge_dormer_hits` deleted alongside the helper itself.
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


# ------------------------------------------------------------------ #
# 6. Iter 79j.44 — dormer-scan subsystem removed                     #
# ------------------------------------------------------------------ #
def test_dormer_scan_helpers_are_gone():
    """The DORMER_PROMPT + _crop_top_strip + _run_dormer_pass_for_photo
    + _is_skyline_photo + _merge_dormer_hits helpers were injecting
    corrupt data (null opening_ids, hits on `rear-left`, wrong-wall
    face SF crediting). Two-phase Phase A/B now owns dormer detection.
    Verify the legacy helpers are truly gone so no code path can
    accidentally re-invoke them."""
    m = _mod()
    for name in ("DORMER_PROMPT", "_crop_top_strip",
                 "_run_dormer_pass_for_photo", "_is_skyline_photo",
                 "_merge_dormer_hits"):
        assert not hasattr(m, name), (
            f"{name} is still defined in ai_measure — legacy dormer-scan "
            f"code paths must be fully removed."
        )


def test_deep_dormer_scan_flag_still_accepted_but_noop():
    """The `deep_dormer_scan` Form flag is preserved on the request
    schema for backward compat, but any invocation of the scan block
    inside _execute_ai_measure_worker has been replaced by a no-op."""
    src = Path("/app/backend/routes/ai_measure.py").read_text()
    # The active worker no longer references dormer_scan_added_* fields.
    assert "raw[\"dormer_scan_added" not in src
    # The legacy scan-orchestration block (stage flip + parallel dispatch)
    # is gone.
    assert "await _set_stage(\"dormer_scan\")" not in src
    assert "dormer_coros" not in src
    # Flag still accepted as Form input for older clients.
    assert "deep_dormer_scan: bool = Form(False)" in src

