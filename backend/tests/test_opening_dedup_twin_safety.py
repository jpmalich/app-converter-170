"""Iter 79j.40 — Opening dedup MUST NOT collapse twins/triples.

The old safety net grouped by (wall, type, size, style) and dropped
every duplicate — that murders two 36×60 double-hungs on the same
bedroom wall down to one, silently under-counting J-channel by 50-75%
per lost twin. New rule keys on position (along_wall_ft) and only
merges when positions agree within ±2 ft. Missing position on either
row = keep both (false duplicates are cheaper than lost twins).

Guards both layers:
  a) SYSTEM_PROMPT + RECONCILE_PROMPT — Claude must be told twins survive.
  b) _dedupe_openings Python safety net — must respect along_wall_ft.
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
    PER_PHOTO_EXTRACT_PROMPT,
    _dedupe_openings,
)


# ---------------------------------------------------------------------
# PROMPT GUARDS
# ---------------------------------------------------------------------

def test_reconcile_prompt_forbids_wall_type_size_shortcut():
    """Rule 3 must ban dedup on (wall, type, size) alone — the exact
    heuristic that murders twins."""
    p = RECONCILE_PROMPT
    p_flat = " ".join(p.split())
    # Positive assertions — the new dedup criteria must be spelled out.
    assert "twins" in p.lower() or "TWINS" in p
    assert "POSITION ALONG THE WALL" in p_flat
    # Must reference the ±2 ft position tolerance.
    assert "±2 ft" in p or "within 2 ft" in p.lower()
    # Twin configurations must be enumerated in the single-call SYSTEM_PROMPT
    # (RECONCILE_PROMPT references them in general; the concrete list of
    # examples lives on the single-call path since that prompt sees photos
    # directly and needs to recognise the shapes visually).
    sp_flat = " ".join(SYSTEM_PROMPT.split())
    for surviving in (
        "Twin double-hungs",
        "Triple casements",
        "Matched pair",
        "sunroom",
        "garage doors side-by-side",
    ):
        assert surviving in sp_flat, f"SYSTEM_PROMPT missing twin example: {surviving}"


def test_reconcile_prompt_treats_null_position_as_keep_both():
    """Absent position evidence must default to KEEP, not MERGE."""
    p_flat = " ".join(RECONCILE_PROMPT.split())
    assert "KEEP BOTH" in p_flat.upper()
    # Rationale must be present — false duplicates < lost twins.
    assert "False duplicates cost less than lost twins" in p_flat


def test_reconcile_prompt_bans_opening_id_as_cross_photo_key():
    """Phase A opening_ids are only unique within a photo. Reconciler
    must know this or it'll silently under-count."""
    p_flat = " ".join(RECONCILE_PROMPT.split())
    assert "NOT a cross-photo match key" in p_flat or "IS NOT a cross-photo match key" in p_flat


def test_single_call_prompt_matches_two_phase_rule():
    """Both paths must behave the same for twin survival. If someone
    unsets AI_MEASURE_TWO_PHASE, single-call must not resurrect the
    old (wall, type, size) shortcut."""
    p_flat = " ".join(SYSTEM_PROMPT.split())
    assert "twins" in p_flat.lower()
    assert "POSITION ALONG THE WALL" in p_flat or "along_wall_ft" in p_flat
    assert "KEEP BOTH" in p_flat.upper()
    # The old naive line must be GONE from the single-call prompt.
    assert "Group openings by (wall, type, approximate size)" not in SYSTEM_PROMPT


def test_per_photo_prompt_requests_along_wall_ft():
    """Phase A MUST emit along_wall_ft so Phase B has position evidence
    to dedup on. Without this the reconciler falls back to keep-both
    for every collision and no cross-photo dedup happens at all."""
    p = PER_PHOTO_EXTRACT_PROMPT
    assert "along_wall_ft" in p
    # Must instruct Claude to set null when not measurable.
    p_flat = " ".join(p.split())
    assert "set null" in p_flat.lower() or "null and the reconciler will KEEP" in p_flat


# ---------------------------------------------------------------------
# PYTHON SAFETY NET GUARDS — behavioural, not schema
# ---------------------------------------------------------------------

def _op(wall, otype, w, h, along, style="", src=None, photo_idx=None):
    return {
        "wall": wall,
        "type": otype,
        "width_in": w,
        "height_in": h,
        "along_wall_ft": along,
        "style": style,
        "_source_photo_indices": src or [],
        "photo_idx": photo_idx,
    }


def test_dedupe_preserves_twins_at_different_positions():
    """Two 36×60 double-hungs on the front wall — the exact bedroom-
    twin configuration — MUST survive dedup."""
    twins = [
        _op("front", "window", 36, 60, along=6.0, style="Double Hung", photo_idx=0),
        _op("front", "window", 36, 60, along=10.5, style="Double Hung", photo_idx=0),
    ]
    kept = _dedupe_openings(twins)
    assert len(kept) == 2, (
        f"Twin murder detected — 2 windows collapsed to {len(kept)}. "
        "This is the exact regression the rewrite fixes."
    )


def test_dedupe_collapses_true_cross_photo_duplicate():
    """Same physical window seen in a front photo AND a corner photo —
    positions agree within ±2 ft → collapse to one."""
    same_window = [
        _op("front", "window", 36, 60, along=16.0, style="Double Hung", src=[0], photo_idx=0),
        _op("front", "window", 36, 60, along=16.5, style="Double Hung", src=[2], photo_idx=2),
    ]
    kept = _dedupe_openings(same_window)
    assert len(kept) == 1
    # Provenance must union both source photos.
    src = set(kept[0].get("_source_photo_indices") or [])
    assert 0 in src and 2 in src


def test_dedupe_keeps_both_when_position_missing():
    """When along_wall_ft is null on either row, we can't confirm
    same-window → KEEP BOTH. This is the twin-safety default."""
    ambiguous = [
        _op("front", "window", 36, 60, along=None, style="Double Hung", photo_idx=0),
        _op("front", "window", 36, 60, along=8.0, style="Double Hung", photo_idx=2),
    ]
    kept = _dedupe_openings(ambiguous)
    assert len(kept) == 2, (
        "Null-position pair merged — dedup must default to KEEP when "
        "position evidence is missing."
    )


def test_dedupe_preserves_triple_casements():
    """Three matched casements in a bank — position gap ~2.5 ft each —
    all three survive."""
    triple = [
        _op("back", "window", 30, 60, along=5.0, style="Casement"),
        _op("back", "window", 30, 60, along=7.75, style="Casement"),
        _op("back", "window", 30, 60, along=10.5, style="Casement"),
    ]
    kept = _dedupe_openings(triple)
    assert len(kept) == 3


def test_dedupe_preserves_matched_pair_of_garage_doors():
    """Two 96×84 single garage doors side by side — position gap ~10
    ft — must both survive."""
    pair = [
        _op("front", "garage_door", 96, 84, along=6.0),
        _op("front", "garage_door", 96, 84, along=16.0),
    ]
    kept = _dedupe_openings(pair)
    assert len(kept) == 2


def test_dedupe_different_styles_at_same_position_kept():
    """Existing Iter 57d behaviour — different styles at the same
    position are NOT the same opening (rare but real: a Picture window
    replaced with a Casement retrofit-side-by-side)."""
    same_spot = [
        _op("right", "window", 36, 36, along=8.0, style="Picture"),
        _op("right", "window", 36, 36, along=8.0, style="Casement"),
    ]
    kept = _dedupe_openings(same_spot)
    assert len(kept) == 2


def test_dedupe_different_sizes_kept():
    """Bin width is 6 in — 24" bathroom vs 36" bedroom at the same
    position must NOT collapse."""
    kept = _dedupe_openings([
        _op("left", "window", 24, 36, along=4.0),
        _op("left", "window", 36, 60, along=4.0),
    ])
    assert len(kept) == 2
