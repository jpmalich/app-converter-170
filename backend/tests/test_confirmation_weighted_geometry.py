"""CONFIRMATION-WEIGHTED GEOMETRY pins (Howard's ruling 2026-07-22).

THE RULE (all photo-scaled derivations): CONFIRMED reads anchor drawn
geometry. UNCONFIRMED single-sighting reads NEVER define a drawn edge,
position, or span on their own — they render as flagged comparisons
(ai_band pattern), awaiting more sightings or human ratification.
Mixed-tier: anchor the confirmed edge; extend toward the unconfirmed
side by TAPED width (user_measured) > ASSUMED standard width 48"
(CONTRACTOR-SPEC, ratified 2026-07-22). Zero confirmed reads: no drawn
position — named state, annotation + comparison only.

FOUNDING EXAMPLE: doug jones back chase (logged in the integrity
register) — live pins in test_chase_ladder_p4.py.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from routes.elevation_sheets import (  # noqa: E402
    STANDARD_CHASE_WIDTH_IN,
    _bind_chase_position,
)


def _read(frac, tier, sightings=1, type_="outside"):
    return {"frac": frac, "tier": tier, "sightings": sightings, "type": type_}


def test_ratified_width_constant():
    """CONTRACTOR-SPEC (Howard, ratified 2026-07-22) — changing it
    requires re-ratification, not a code edit."""
    assert STANDARD_CHASE_WIDTH_IN == 48.0


def test_both_edges_confirmed_keeps_photo_scaled_span():
    ch = {}
    _bind_chase_position(ch, [_read(0.3, "confirmed", 3), _read(0.42, "confirmed", 4)], 50.0, {})
    assert ch["center_ft"] == 18.0
    assert ch["_lad_fr"] == [0.3, 0.42]  # span feeds ESTIMATED (photo-scaled)
    assert "CONFIRMED" in ch["position"] and "_width_override" not in ch


def test_mixed_tier_anchors_confirmed_edge_doug_pattern():
    """The founding-example pattern (doug's EXACT reads): confirmed
    right-edge CLUSTER (0.42 outside + 0.40 inside return — one edge,
    span < 48" discriminator), unconfirmed left (1 sighting) → anchor
    the OUTSIDE read (0.42 → 21'-0"), extend left by ASSUMED 48"; the
    unconfirmed read becomes the flagged comparison, never a drawn edge."""
    ch = {}
    _bind_chase_position(
        ch, [_read(0.42, "confirmed", 4, "outside"), _read(0.4, "confirmed", 4, "inside"),
             _read(0.3, "unconfirmed", 1, "outside")], 50.0, {})
    assert ch["center_ft"] == 19.0  # 21' − 24"
    assert ch["_width_override"] == (48.0, 'ASSUMED (standard width 48")')
    assert "anchored on CONFIRMED right-edge read" in ch["position"]
    assert "extends left" in ch["position"]
    band = ch["ai_band"]["note"]
    assert "UNCONFIRMED" in band and "1 sighting" in band
    assert 'implies 72" width' in band and "comparison only" in band


def test_edge_cluster_never_draws_a_sliver():
    """Two confirmed reads 1' apart are ONE edge cluster, not a 12\"-wide
    chase — the discriminator is the ratified 48" minimum, not a magic
    number. Direction with no unconfirmed hint: locator handedness
    ('right side' read → chase extends LEFT), data-derived."""
    ch = {}
    _bind_chase_position(
        ch, [dict(_read(0.42, "confirmed", 4, "outside"), locator="chase right side meets wall"),
             dict(_read(0.4, "confirmed", 4, "inside"), locator="chase right return")],
        50.0, {})
    assert ch.get("_lad_fr") is None and ch["_width_override"][0] == 48.0
    assert ch["center_ft"] == 19.0


def test_direction_interior_fallback_when_unhinted():
    """No unconfirmed reads, no locator handedness → extend toward the
    wall interior (deterministic last resort, stated in the position)."""
    ch = {}
    _bind_chase_position(ch, [_read(0.42, "confirmed", 4)], 50.0, {})
    assert ch["center_ft"] == 23.0  # 21' + 24" toward interior
    assert "extends right" in ch["position"]


def test_single_confirmed_edge_tape_upgrade_wins():
    est = {"lp_appendage_dims": {"appendage:back": {
        "width_ft": {"value": 5.0, "status": "user_measured"}}}}
    ch = {}
    _bind_chase_position(
        ch, [dict(_read(0.42, "confirmed", 4), locator="chase right edge")], 50.0, est)
    assert ch["_width_override"] == (60.0, "TAPED (user-measured)")
    assert ch["center_ft"] == round(21.0 - 2.5, 1)


def test_zero_confirmed_reads_named_state_nothing_drawn():
    ch = {}
    _bind_chase_position(ch, [_read(0.3, "unconfirmed", 1), _read(0.35, "unconfirmed", 1)], 50.0, {})
    assert "center_ft" not in ch  # no drawn position
    assert ch["position_tag"] == "UNCONFIRMED"
    assert "not drawn" in ch["position"]
    assert "comparison only" in ch["ai_band"]["note"]
