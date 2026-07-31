"""Iter 78z (P1.2) — Per-profile siding line splitting in _build_lines.

Verifies that when measurements carry a multi-profile `_per_profile_sqft`
breakdown (Campbell-style mixed Lap/Shake/B&B house), the catalog mapper
emits SEPARATE siding lines per profile per tab instead of lumping
everything into the default Charter Oak Dutch Lap.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package is on sys.path even when invoked from /app.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from routes.hover import _build_lines, _profile_siding_lines


def _siding_lines(lines: list, tab: str) -> list[dict]:
    return [l for l in lines if l["tab"] == tab and l["section"] in (
        "Vinyl Siding", "Ascend Cladding", "LP Smart Siding"
    )]


def test_single_profile_keeps_default_mapping():
    """One profile only → default single-SKU mapping kicks in."""
    m = {
        "siding_with_openings_sqft": 2000.0,
        "_per_profile_sqft": {"lap": 2000.0},
        "_per_elevation_breakdown": [],
    }
    lines = _profile_siding_lines(m)
    assert lines == []  # No multi-profile override fired


def test_no_breakdown_keeps_default_mapping():
    """HOVER PDF imports don't carry `_per_profile_sqft` — default wins."""
    m = {"siding_with_openings_sqft": 1500.0}
    lines = _profile_siding_lines(m)
    assert lines == []


def test_multi_profile_emits_one_line_per_family_per_tab():
    """Campbell case — Lap body + Shake gables + B&B porch."""
    m = {
        "siding_with_openings_sqft": 2100.0,
        "_per_profile_sqft": {
            "lap": 1840.0,
            "shake": 168.0,
            "board_batten": 60.0,
        },
    }
    lines = _profile_siding_lines(m)
    vinyl = _siding_lines(lines, "vinyl")
    # Lap → Charter Oak DL, Shake → Pelican Bay, B&B → Vertical B&B
    names = {l["name"] for l in vinyl}
    assert 'Charter Oak Standard color Dutch Lap 4.5" .046' in names
    assert 'Pelican Bay Shakes 9"' in names
    assert 'vertical board and batten Standard color 7"' in names
    # Per-elevation breakdown note format
    for l in vinyl:
        assert l["note"].startswith("Per-elevation breakdown:")
    # Qty check — R3 (Howard ruled 2026-07-31): Pelican Bay orders by the
    # HALF SQUARE (13 pcs per 1/2 SQ) — 168 sqft ÷ 50 = 3.4 half squares
    shake_line = next(l for l in vinyl if l["name"] == 'Pelican Bay Shakes 9"')
    assert abs(shake_line["qty"] - 3.4) < 0.05


def test_build_lines_skips_default_when_multi_profile():
    """`_build_lines` must NOT emit BOTH the default Charter Oak line
    AND the per-profile lines — that would double-count."""
    m = {
        "siding_with_openings_sqft": 2100.0,
        "siding_sqft": 2100.0,
        "_per_profile_sqft": {
            "lap":   1840.0,
            "shake": 168.0,
        },
    }
    lines = _build_lines(m)
    vinyl_siding = [
        l for l in lines
        if l["tab"] == "vinyl" and l["section"] == "Vinyl Siding"
    ]
    # Should be exactly 2 lines: Charter Oak DL (lap) + Pelican Bay (shake)
    names = [l["name"] for l in vinyl_siding]
    assert names.count('Charter Oak Standard color Dutch Lap 4.5" .046') == 1
    assert names.count('Pelican Bay Shakes 9"') == 1
    # And nothing weird crept in
    assert len(vinyl_siding) == 2


def test_lp_uses_pcs_unit_with_correct_conversion():
    """LP tab uses PCS — 9.09 sqft/pc for Lap/Shake/Nickel-Gap."""
    m = {
        "siding_with_openings_sqft": 1000.0,
        "_per_profile_sqft": {
            "lap":   500.0,
            "shake": 500.0,
        },
    }
    lines = _profile_siding_lines(m)
    lp = _siding_lines(lines, "lp_smart")
    lap_line = next(l for l in lp if "Lap" in l["name"])
    assert lap_line["unit"] == "PCS"
    # 500 sqft at book 11 pcs/sq (LAP UNIFY register #3, 2026-07-28) =
    # 55 pcs × 1.10 family-default waste = 60.5 → 61 (was 60 via PDF 9.17)
    assert 50 <= lap_line["qty"] <= 61


def test_stone_brick_excluded_from_siding_lines():
    """Stone / brick / stucco families should never produce a siding line."""
    m = {
        "siding_with_openings_sqft": 1500.0,
        "_per_profile_sqft": {
            "lap":   1200.0,
            "stone": 300.0,
        },
    }
    lines = _profile_siding_lines(m)
    vinyl = _siding_lines(lines, "vinyl")
    # Only Lap should be emitted — stone is masonry, not siding.
    # NOTE: the breakdown helper already strips stone from per_profile_sqft,
    # but defense in depth: if it ever leaks through, _PROFILE_SKU_MAP
    # has no key for it so nothing's emitted.
    for l in vinyl:
        assert "Charter Oak" in l["name"]


def test_zero_or_negative_sqft_skipped():
    m = {
        "_per_profile_sqft": {
            "lap":   1500.0,
            "shake": 0.0,
            "board_batten": -10.0,
        },
    }
    lines = _profile_siding_lines(m)
    # Only 1 positive family → not multi-profile → falls back to default
    assert lines == []


def test_unknown_family_silently_skipped():
    """A family with no SKU mapping (e.g. unknown future profile) is
    silently skipped per tab, but other families still emit lines."""
    m = {
        "_per_profile_sqft": {
            "lap":        1500.0,
            "shake":      168.0,
            "future_xyz": 100.0,  # Not in _PROFILE_SKU_MAP
        },
    }
    lines = _profile_siding_lines(m)
    # Lap + Shake should still emit on vinyl tab
    vinyl_names = {l["name"] for l in lines if l["tab"] == "vinyl"}
    assert 'Charter Oak Standard color Dutch Lap 4.5" .046' in vinyl_names
    assert 'Pelican Bay Shakes 9"' in vinyl_names
