"""Iter 79j.36 — Regression guard for the extraction debug schema.

Howard reported 3 runs on the same house returning eave heights of
7, 8.5, and 12 ft and different dormer counts each time. To diagnose
whether that variance came from detection or reconciliation, the
prompt now requests per-photo raw observations AND top-level +
per-wall provenance/reconciliation traces. These asserts lock the
schema so a future prompt refactor doesn't silently drop them.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import SYSTEM_PROMPT  # noqa: E402


def test_photos_schema_includes_per_photo_observations():
    p = SYSTEM_PROMPT
    assert "PER-PHOTO RAW OBSERVATIONS" in p
    for field in (
        "walls_visible",
        "eave_height_ft_observed",
        "eave_reasoning",
        "pitch_ratio_observed",
        "gable_triangle_height_ft_observed",
        "dormers_observed_count",
        "openings_this_photo",
    ):
        assert field in p, f"Prompt lost per-photo field: {field}"


def test_walls_schema_includes_reconciliation_trace():
    p = SYSTEM_PROMPT
    assert "RECONCILIATION PROVENANCE" in p
    for field in (
        "_source_photo_indices",
        "_per_photo_readings",
        "_reconciliation_note",
    ):
        assert field in p, f"Prompt lost walls[] provenance field: {field}"


def test_openings_carry_opening_id_and_source_indices():
    p = SYSTEM_PROMPT
    # opening_id is the join key between photos[i].openings_this_photo
    # and top-level openings[] so the debug UI can hyperlink both
    # views. Losing it collapses the two into a same-shape-but-
    # unrelated pair of lists.
    assert '"opening_id":' in p
    # Openings must ALSO carry source_photo_indices so the debug
    # view can highlight which photo the merged size came from.
    # Search inside the openings[] block specifically.
    ops_block = p.split('"openings": [', 1)[1].split('"openings_schedule"', 1)[0]
    assert "_source_photo_indices" in ops_block
    assert "_reconciliation_note" in ops_block


def test_top_level_reconciliation_notes_block_present():
    p = SYSTEM_PROMPT
    assert '"_reconciliation_notes":' in p
    for k in ("avg_wall_height_ft", "roof_type", "dormer", "siding_coverage_pct"):
        assert f'"{k}"' in p
