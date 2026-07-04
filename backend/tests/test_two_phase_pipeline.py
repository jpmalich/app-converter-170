"""Iter 79j.37 — Guards for the two-phase EXTRACT + RECONCILE pipeline.

The old single-call worker sent every photo to Claude in one shot,
mixing extraction and reconciliation into a black box. The two-phase
pipeline splits it: N parallel per-photo extractions, then a single
reconciliation call. Both prompts must remain schema-compatible with
the aggregator, and the pipeline entry points must be importable.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    PER_PHOTO_EXTRACT_PROMPT,
    RECONCILE_PROMPT,
    _extract_one_photo,
    _reconcile_extractions,
    _run_two_phase_pipeline,
)


def test_two_phase_entry_points_are_importable():
    """The three coroutines that make up the two-phase pipeline must
    stay exported so main-agent refactors don't silently break the
    gated path."""
    for coro in (_extract_one_photo, _reconcile_extractions, _run_two_phase_pipeline):
        assert callable(coro)


def test_per_photo_prompt_asks_only_for_extraction():
    p = PER_PHOTO_EXTRACT_PROMPT
    # Must NOT ask for reconciled house-level scalars — those come in
    # Phase B. If someone edits this prompt and adds `avg_wall_height`
    # (a reconciled field), that's a sign the split has been reversed.
    assert "extraction only" in p.lower() or "EXTRACTION ONLY" in p
    # Must ask for per-photo observations, not merged aggregates.
    for field in (
        "eave_height_ft_observed",
        "walls_visible",
        "openings_this_photo",
        "opening_id",
        "colors_sampled",
    ):
        assert field in p, f"Phase A prompt lost field: {field}"


def test_reconcile_prompt_targets_aggregator_schema():
    p = RECONCILE_PROMPT
    # Phase B output MUST match the shape `_aggregate_to_hover_shape`
    # reads or downstream code breaks silently. Assert the key top-level
    # fields are still requested.
    for field in (
        '"walls":',
        '"openings":',
        '"dormer":',
        '"avg_wall_height_ft":',
        '"roof_type":',
        '"dominant_colors":',
        '"eaves_lf":',
        '"outside_corner_lf":',
        '"_reconciliation_notes":',
    ):
        assert field in p, f"Phase B prompt lost aggregator field: {field}"


def test_reconcile_prompt_carries_provenance_slots():
    """Per-wall and per-opening provenance slots ARE the point of the
    split — they must remain in Phase B's output schema."""
    p = RECONCILE_PROMPT
    for field in (
        "_source_photo_indices",
        "_per_photo_readings",
        "_reconciliation_note",
    ):
        assert p.count(field) >= 1, f"Phase B prompt lost provenance: {field}"


def test_reconcile_rules_present():
    """The merge/dedup/discard rules are what stop reconciliation from
    silently drifting between runs. Guard the section header + a few
    keystone rules so a prompt refactor can't quietly drop them."""
    p = RECONCILE_PROMPT
    p_flat = " ".join(p.split())
    assert "RECONCILIATION RULES:" in p
    assert "EAVE HEIGHT PER WALL" in p
    assert "OPENING DEDUP" in p
    assert "DISCARD any photo tagged as" in p_flat
    assert "aerial" in p
