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
        '"dormers":',      # Iter 79j.41 — ARRAY; singular `dormer` was the missing-right-dormer bug.
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
    assert "aerial" in p_flat
    # Old blanket "DISCARD any photo tagged as `aerial`" replaced in
    # 79j.38 with the more precise direct-view rule below — the reject
    # list still explicitly names aerial/roof-only/detail shots.
    assert "Signals to REJECT" in p or "aerial / roof-only" in p


def test_eave_disagreement_rule_amber_estimated():
    """Iter 79j.38 — When direct-view eave readings spread >1 ft, the
    reconciler must NOT average them. Instead: keep the strongest
    reading and flag the wall amber. Gable-end photos never inform
    eave height. Missing direct view → amber-estimated placeholder."""
    p = RECONCILE_PROMPT
    p_flat = " ".join(p.split())

    # Must call out the >1 ft disagreement threshold explicitly.
    assert "MORE THAN 1 ft" in p or "more than 1 ft" in p.lower()

    # Must forbid averaging incompatible readings.
    assert "do NOT average" in p_flat or "not average them" in p_flat.lower()

    # Must call out that gable-end photos NEVER inform eave height.
    assert "NEVER inform eave height" in p_flat or "never inform eave height" in p_flat.lower()

    # Must emit the source tag values the frontend badges key off.
    for tag in ("direct_consensus", "direct_disagreement", "estimated_no_direct_view"):
        assert tag in p, f"Prompt lost height_ft_source tag: {tag}"

    # walls[] schema must declare height_ft_source explicitly.
    walls_block = p.split('"walls": [', 1)[1].split('"openings":', 1)[0]
    assert "height_ft_source" in walls_block

    # Must include a "no direct view" fallback description.
    assert "no direct-view" in p_flat.lower() or "no direct view" in p_flat.lower() or "NO direct-view reading" in p


def test_dormer_width_rule_matches_eave_rigor():
    """Iter 79j.39 — "widest reading wins" was the same trap as "average
    all eave readings". Rewritten Rule 5 must:
      - reject aerials / corner shots / telephoto for WIDTH (aerials
        still OK for count & face)
      - not average or take-max when readings spread > 1 ft
      - back-solve from an on-dormer opening if no direct view exists
      - flag amber-estimated (12 ft placeholder) as last resort
    Guards on the tag values so the frontend badges stay in sync."""
    p = RECONCILE_PROMPT
    p_flat = " ".join(p.split())

    # The old naive line must be GONE.
    assert 'use the photo with the widest' not in p, (
        "Rule 5 still uses 'widest reading wins' — the trap that inflates "
        "dormer widths whenever one photo is off-axis."
    )

    # Must explicitly ban averaging / max-taking on disagreement.
    assert "do NOT average or take the max" in p_flat, (
        "Rule 5 disagreement clause missing — averaging or maxing "
        "dormer widths hides the problem."
    )

    # Must call out that aerials are OK for count/face but NEVER width.
    assert "NEVER width" in p_flat or "never width" in p_flat.lower()

    # Must include the four provenance tags the frontend keys off.
    for tag in (
        "direct_consensus",
        "direct_disagreement",
        "back_solved_from_opening",
        "estimated_no_direct_view",
    ):
        # `direct_consensus` and `direct_disagreement` also appear in
        # rule 1 (eaves), but back_solved_from_opening only appears
        # in rule 5 — guarding all four ensures the dormer clause is
        # self-contained.
        assert tag in p, f"Rule 5 lost width_source tag: {tag}"

    # Dormer schema block MUST declare width_source (frontend reads
    # aiDormer.width_source; missing key defaults to legacy behaviour).
    # Iter 79j.41 — key is now `dormers` (array), not singular.
    dormer_block = p.split('"dormers":', 1)[1].split('"walls":', 1)[0]
    assert "width_source" in dormer_block


def test_dormer_schema_carries_per_photo_readings():
    """Provenance readings must be requested so the debug view can
    show which photos contributed to width vs face vs count."""
    p = RECONCILE_PROMPT
    dormer_block = p.split('"dormers":', 1)[1].split('"walls":', 1)[0]
    for f in ("_source_photo_indices", "_per_photo_readings", "approx_width_ft"):
        assert f in dormer_block, f"Dormer schema lost per-photo field: {f}"
