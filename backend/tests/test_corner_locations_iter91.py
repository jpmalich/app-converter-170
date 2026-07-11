"""Iter 79j.91 — Candidate 3 corner-location pins (pre-registered,
Howard-approved: presence guarantee, ±10%/±2ft tolerance hard-capped ±4ft,
opposite types never merge, corner_type_conflict vs adjacent_opposite_type,
elevated dormer posts count)."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    _apply_corner_locations, _prompt_version_hash, PER_PHOTO_EXTRACT_PROMPT,
)

HASH_C3 = "cbcb392fc94104fa"


def _sight(idx, ctype, walls, pos, elevated=False, locator="x"):
    return {"type": ctype, "walls": walls, "position_frac": pos,
            "locator": locator, "elevated": elevated}


def _ex(idx, corners, walls_visible=None):
    return {"index": idx, "corner_locations_this_photo": corners,
            "walls_visible": walls_visible or []}


def _final(lengths=None):
    lengths = lengths or {}
    return {"walls": [{"label": l, "length_ft": lengths.get(l)} for l in ("front", "back", "left", "right")]}


def test_c3_hash_and_prompt_markers():
    assert _prompt_version_hash() == HASH_C3
    assert "corner_locations_this_photo" in PER_PHOTO_EXTRACT_PROMPT
    assert "never skip a corner because it does not reach" in PER_PHOTO_EXTRACT_PROMPT


def test_two_photo_agreement_confirms():
    f = _final({"front": 30})
    _apply_corner_locations(f, [
        _ex(0, [_sight(0, "outside", ["front", "left"], 0.0)]),
        _ex(1, [_sight(1, "outside", ["front", "left"], 0.03)]),
    ])
    locs = f["corner_locations"]
    assert len(locs) == 1 and locs[0]["tier"] == "confirmed"
    assert f["_corner_location_audit"]["totals"]["outside"] == 1


def test_single_photo_unconfirmed_but_present():
    f = _final()
    _apply_corner_locations(f, [_ex(0, [_sight(0, "outside", ["back"], 0.4, elevated=True)])])
    locs = f["corner_locations"]
    assert len(locs) == 1
    assert locs[0]["tier"] == "unconfirmed"  # amber, flagged for field check
    assert locs[0]["elevated"] is True       # elevated posts always enter takeoff


def test_tolerance_hard_cap_on_long_wall():
    # 54' wall: ±10% = 5.4' would merge chase corners; cap = 4' → 4/54 ≈ 0.074
    f = _final({"back": 54})
    _apply_corner_locations(f, [
        _ex(0, [_sight(0, "outside", ["back"], 0.40)]),
        _ex(1, [_sight(1, "outside", ["back"], 0.49)]),  # 0.09 apart > 0.074 cap → separate
    ])
    assert len(f["corner_locations"]) == 2


def test_small_wall_two_ft_floor():
    # 10' wall: 2ft floor → 0.2 tolerance merges 0.15-apart sightings
    f = _final({"left": 10})
    _apply_corner_locations(f, [
        _ex(0, [_sight(0, "outside", ["left"], 0.30)]),
        _ex(1, [_sight(1, "outside", ["left"], 0.45)]),
    ])
    assert len(f["corner_locations"]) == 1


def test_opposite_types_never_merge_adjacent_flag():
    # chase geometry: OSC and ISC nearby (within tolerance, beyond same-spot eps)
    f = _final({"back": 30})
    _apply_corner_locations(f, [
        _ex(0, [_sight(0, "outside", ["back"], 0.40)]),
        _ex(1, [_sight(1, "inside", ["back"], 0.46)]),
    ])
    locs = f["corner_locations"]
    assert len(locs) == 2  # both kept — presence guarantee
    assert all(l.get("adjacent_opposite_type") for l in locs)
    assert not any(l.get("corner_type_conflict") for l in locs)


def test_same_spot_type_disagreement_is_type_conflict():
    f = _final({"back": 30})
    _apply_corner_locations(f, [
        _ex(0, [_sight(0, "outside", ["back"], 0.40)]),
        _ex(1, [_sight(1, "inside", ["back"], 0.41)]),  # within 0.025 eps
    ])
    locs = f["corner_locations"]
    assert len(locs) == 2  # still never merged
    assert all(l.get("corner_type_conflict") for l in locs)


def test_geometry_mismatch_demotes_never_deletes():
    f = _final()
    _apply_corner_locations(f, [
        _ex(0, [_sight(0, "outside", ["back"], 0.5)], walls_visible=["front"]),
    ])
    locs = f["corner_locations"]
    assert len(locs) == 1
    assert locs[0]["geometry_mismatch"] is True
    assert locs[0]["tier"] == "unconfirmed"


def test_totals_and_residual():
    f = _final({"front": 30})
    _apply_corner_locations(f, [
        _ex(0, [_sight(0, "outside", ["front", "left"], 0.0), _sight(0, "inside", ["front"], 0.5)]),
        _ex(1, [_sight(1, "outside", ["front", "left"], 0.0)]),
    ])
    t = f["_corner_location_audit"]["totals"]
    assert t == {"outside": 1, "inside": 1, "confirmed": 1, "unconfirmed": 1}
    assert "never auto-deleted" in f["_corner_location_audit"]["residual_note"]


def test_no_sightings_no_stamp():
    f = _final()
    _apply_corner_locations(f, [_ex(0, [])])
    assert "corner_locations" not in f
