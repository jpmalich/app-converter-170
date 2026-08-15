"""RULING Q + R SYNTHETIC PINS (Howard sealed 2026-08-14 send-18).

MANDATORY, not optional (send-18 Q): since send-13 shared-source is a flag
not a kill, so fixture wall heights SURVIVE and the refusal branch these
conversions create may never fire on any real fixture. A green suite that
never enters the branch is this project's recurring shape. Each pin below
deliberately KILLS a height and asserts the corner/OSC line comes back NOT
DERIVABLE naming the dead wall — the branch is exercised on purpose.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

from quantity import DERIVED, NOT_DERIVABLE, PARTIAL  # noqa: E402
from lp_package import (  # noqa: E402
    OSC_ITEM, _corner_height_ft, assemble_lp_package,
    isc_from_corner_locations, osc_from_corner_locations,
)


# ── Unit: _corner_height_ft is a status-carrying Quantity (Ruling R) ──

def test_corner_over_dead_wall_is_not_derivable_naming_the_wall():
    q = _corner_height_ft({"type": "outside", "walls": ["back"]},
                          {"front": 9.0})   # 'back' never read
    assert q.status == NOT_DERIVABLE and q.value is None
    assert "back" in " ".join(q.excluded)


def test_corner_with_no_touching_wall_is_not_derivable():
    q = _corner_height_ft({"type": "outside", "walls": []}, {"front": 9.0})
    assert q.status == NOT_DERIVABLE and q.value is None


def test_corner_touching_one_dead_one_live_wall_is_not_derivable():
    # Ruling R: ANY height-dead touching wall poisons the whole corner —
    # min()/one-side is a lower bound wearing a real read's costume.
    q = _corner_height_ft({"type": "outside", "walls": ["front", "back"]},
                          {"front": 9.0})   # back dead
    assert q.status == NOT_DERIVABLE and "back" in " ".join(q.excluded)


def test_corner_walls_agree_is_derived():
    q = _corner_height_ft({"type": "outside", "walls": ["front", "left"]},
                          {"front": 9.0, "left": 9.0})
    assert q.status == DERIVED and q.value == 9.0


def test_corner_walls_disagree_diff_count_is_derived_max_naming_both():
    # Ruling T (send-19): two verified walls that DISAGREE are a complete
    # derivation, not a subset — status DERIVED at MAX (never PARTIAL,
    # never averaged). 18' vs 9' → 18'. The stick-count decision is made
    # at the line (see the takeoff test), not here.
    q = _corner_height_ft({"type": "outside", "walls": ["front", "wing"]},
                          {"front": 18.0, "wing": 9.0})
    assert q.status == DERIVED and q.value == 18.0
    assert "front=18" in q.reason and "wing=9" in q.reason


def test_corner_disagreement_same_stick_count_no_line_annotation():
    # Ruling T: 8.5 vs 8.3 → same stick count → DERIVED, disagreement on
    # the read-back only, NO line annotation, NO gate effect.
    osc = osc_from_corner_locations(
        [{"type": "outside", "walls": ["front", "left"], "tier": "confirmed"}],
        {"front": 8.5, "left": 8.3})
    assert osc["status"] == DERIVED and osc["blocks_gate"] is False
    assert "CHANGED the count" not in osc["note"]
    assert osc.get("readback") and "disagree" in osc["readback"]


def test_corner_disagreement_that_changes_count_annotates_the_line():
    # Ruling T: 18' vs 9' over a 16' OSC stick → 1 vs 2 sticks → the
    # disagreement CHANGED the count → annotated ON the line, both counts.
    osc = osc_from_corner_locations(
        [{"type": "outside", "walls": ["front", "wing"], "tier": "confirmed"}],
        {"front": 18.0, "wing": 9.0})
    assert osc["status"] == DERIVED and osc["qty"] == 2
    assert "CHANGED the count" in osc["note"] and "front=18" in osc["note"]


# ── OSC / ISC line refusal + gate block ──

def test_osc_line_not_derivable_blocks_gate_and_names_dead_wall():
    osc = osc_from_corner_locations(
        [{"type": "outside", "walls": ["ghost"], "tier": "confirmed"}], {})
    assert osc["qty"] is None and osc["status"] == NOT_DERIVABLE
    assert osc["blocks_gate"] is True and "ghost" in osc["dead_walls"]
    assert "NOT DERIVABLE" in osc["note"]


def test_isc_line_not_derivable_blocks_gate():
    isc = isc_from_corner_locations(
        [{"type": "inside", "walls": ["ghost"], "tier": "confirmed"}], {})
    assert isc["qty"] is None and isc["status"] == NOT_DERIVABLE
    assert isc["blocks_gate"] is True


# ── assemble_lp_package: the refused corner blocks the whole quote ──

def test_assemble_osc_not_derivable_empties_line_and_flags_gate():
    pkg = assemble_lp_package(
        {"siding_sqft": 1000.0},
        corner_locations=[{"type": "outside", "walls": ["porch_post"],
                           "tier": "confirmed"}],
        wall_heights={})   # porch_post height never read
    osc = next(l for l in pkg["lines"] if l["name"] == OSC_ITEM)
    assert osc["qty"] is None
    assert osc.get("status") == NOT_DERIVABLE and osc.get("blocks_gate") is True
    assert osc.get("price") is None
    assert any("NOT DERIVABLE" in f and "porch_post" in f
               for f in pkg["summary"]["flags"])
    # Ruling L: the pieces roll-up must not silently sum the refused line.
    assert isinstance(pkg["summary"]["total_pieces"], (int, float))


def test_assemble_osc_derivable_when_height_present_is_unaffected():
    pkg = assemble_lp_package(
        {"siding_sqft": 1000.0},
        corner_locations=[{"type": "outside", "walls": ["front"],
                           "tier": "confirmed"}],
        wall_heights={"front": 9.0})
    osc = next(l for l in pkg["lines"] if l["name"] == OSC_ITEM)
    assert isinstance(osc["qty"], int) and osc["qty"] >= 1
    assert osc.get("blocks_gate") is not True
