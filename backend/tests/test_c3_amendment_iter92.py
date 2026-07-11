"""Iter 79j.92 — pinned tests for the two Howard-ruled fixes:
(1) clarifying amendment to 79j.91: identical two-wall pair set = one
    physical junction, merge regardless of position_frac; opposite types
    on that pair = corner_type_conflict (one junction, disputed type);
(2) truncation-salvage rung in the JSON repair ladder (empty class 4):
    salvage ONLY fields fully parsed before the stop, never invent,
    mark _json_repaired="truncation" + _extraction_partial.
Both live OUTSIDE the hashed prompt contract — hash must be UNCHANGED."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    _apply_corner_locations, _clean_json_reply, _salvage_truncated_json,
    _prompt_version_hash,
)

HASH_C3 = "cbcb392fc94104fa"  # same pin as iter91 — code fixes, not contract


def _sight(ctype, walls, pos, locator="x"):
    return {"type": ctype, "walls": walls, "position_frac": pos, "locator": locator}


def _ex(idx, corners):
    return {"index": idx, "corner_locations_this_photo": corners, "walls_visible": []}


def _final(lengths=None):
    lengths = lengths or {}
    return {"walls": [{"label": l, "length_ft": lengths.get(l)} for l in ("front", "back", "left", "right")]}


def test_hash_unchanged_by_92_fixes():
    assert _prompt_version_hash() == HASH_C3


# ---- (1) frame-duplication dedupe amendment ----

def test_two_wall_pair_merges_regardless_of_frac():
    # same physical corner seen as front@1.0 and right@0.0 frames
    f = _final({"front": 30, "right": 20})
    _apply_corner_locations(f, [
        _ex(0, [_sight("outside", ["front", "right"], 1.0)]),
        _ex(5, [_sight("outside", ["front", "right"], 0.0)]),
    ])
    locs = f["corner_locations"]
    assert len(locs) == 1
    assert locs[0]["sightings"] == 2
    assert locs[0]["tier"] == "confirmed"


def test_letrick_frame_dup_pattern_resolves_to_four_house_corners():
    # dce41292 pattern: all 4 house corners doubled via opposing frames
    f = _final({"front": 40, "back": 40, "left": 26, "right": 26})
    _apply_corner_locations(f, [
        _ex(0, [_sight("outside", ["front", "left"], 0.0),
                _sight("outside", ["front", "right"], 1.0)]),
        _ex(2, [_sight("outside", ["back", "left"], 0.0),
                _sight("outside", ["front", "left"], 1.0)]),
        _ex(4, [_sight("outside", ["back", "right"], 0.0),
                _sight("outside", ["back", "left"], 1.0)]),
        _ex(7, [_sight("outside", ["front", "right"], 0.0),
                _sight("outside", ["back", "right"], 1.0)]),
    ])
    locs = f["corner_locations"]
    assert len(locs) == 4
    assert all(l["type"] == "outside" and l["sightings"] == 2 for l in locs)
    assert all(l["tier"] == "confirmed" for l in locs)


def test_opposite_types_on_same_pair_is_type_conflict_not_adjacent():
    f = _final({"front": 30})
    _apply_corner_locations(f, [
        _ex(0, [_sight("outside", ["front", "left"], 0.0)]),
        _ex(1, [_sight("inside", ["front", "left"], 1.0)]),
    ])
    locs = f["corner_locations"]
    assert len(locs) == 2  # opposite types still NEVER merge
    assert all(l.get("corner_type_conflict") for l in locs)
    assert not any(l.get("adjacent_opposite_type") for l in locs)


def test_single_wall_drift_beyond_cap_still_separate():
    # chase drift regression guard: amendment must not touch 1-wall corners
    f = _final({"back": 40})
    _apply_corner_locations(f, [
        _ex(0, [_sight("outside", ["back"], 0.35)]),
        _ex(1, [_sight("outside", ["back"], 0.63)]),  # ~11ft apart > 4ft cap
    ])
    assert len(f["corner_locations"]) == 2


# ---- (2) truncation-salvage rung ----

def test_truncation_salvages_complete_fields_only():
    reply = '{"index": 3, "walls_visible": ["back", "left"], "notes": "cut mid-sen'
    out = _clean_json_reply(reply)
    assert out.get("_json_repaired") == "truncation"
    assert out.get("_extraction_partial") is True
    assert out["index"] == 3
    assert out["walls_visible"] == ["back", "left"]
    assert "notes" not in out  # truncated field dropped, NOT completed


def test_truncation_mid_array_drops_whole_array():
    reply = '{"index": 1, "openings_this_photo": [{"w": 3, "h": 5}, {"w": 2,'
    out = _clean_json_reply(reply)
    assert out.get("_json_repaired") == "truncation"
    assert out["index"] == 1
    assert "openings_this_photo" not in out  # partially-parsed structure never salvaged


def test_truncation_trailing_bare_number_never_salvaged():
    # digits may be cut: 47 could have been 472 — never invent
    reply = '{"index": 2, "eave_height_ft_observed": 47'
    out = _clean_json_reply(reply)
    assert out.get("_json_repaired") == "truncation"
    assert out == {"index": 2, "_json_repaired": "truncation", "_extraction_partial": True}


def test_truncation_with_nothing_complete_stays_parse_error():
    out = _clean_json_reply('{"index')
    assert "_parse_error" in out


def test_non_truncation_error_not_salvaged():
    # mid-body corruption (error far from end) must stay diagnosable
    reply = '{"a": 1, "b": ~broken~, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6}'
    out = _clean_json_reply(reply)
    assert "_parse_error" in out
    assert "_json_repaired" not in out


def test_existing_ladder_rungs_unaffected():
    assert _clean_json_reply('{"a": 1,}') == {"a": 1, "_json_repaired": True}
    assert _clean_json_reply('prose then {"a": 1} trailing') == {"a": 1}


def test_salvage_helper_complete_object_roundtrip():
    # a fully valid object never reaches the rung, but the helper itself
    # must not drop anything when input happens to be complete
    out = _salvage_truncated_json('{"a": 1, "b": "x"}')
    assert out == {"a": 1, "b": "x"}


def test_one_photo_echo_never_confirms():
    # Howard ruling (C3 Letrick verdict, sub-item b): confirmed tier
    # requires >=2 DISTINCT PHOTOS, never >=2 sightings. Fixture is the
    # live p3 double-sighting: one photo echoing the same chase edge twice.
    f = _final({"back": 40})
    _apply_corner_locations(f, [
        _ex(3, [_sight("outside", ["back"], 0.60),
                _sight("outside", ["back"], 0.61)]),
    ])
    locs = f["corner_locations"]
    assert len(locs) == 1
    assert locs[0]["sightings"] == 2
    assert locs[0]["photo_idxs"] == [3]
    assert locs[0]["tier"] == "unconfirmed"  # echo is not agreement
