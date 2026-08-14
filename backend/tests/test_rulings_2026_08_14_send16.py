"""RULINGS REGISTER — SEND-16 (2026-08-14).

STANDING PRINCIPLE, SEALED (verbatim, per Ruling C — governs all future
work and supersedes any conflicting earlier instruction, including
Howard's own):

    MONEY IS DERIVED FROM THE MATERIAL QUANTITIES.
    Measure the house → produce an honest material list, where every
    quantity carries its real status → populate the correct line items →
    derive the money from those quantities.
    Do not build special money-line logic, averages, or silent zeros.
    If the takeoff is honest, the money is honest. If a quantity is NOT
    DERIVABLE, the money that depends on it must reflect that — not be
    filled in quietly.

Full send prose archived verbatim at backend/rulings_archive/send16.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import quantity as q  # noqa: E402


def test_ruling_J_status_is_a_property_of_the_quantity():
    """RULING J (send-16): 'Every derived quantity carries a STATUS
    alongside its value: DERIVED · PARTIAL · NOT DERIVABLE. A quantity
    cannot exist without a status. Status PROPAGATES: any quantity
    computed from a PARTIAL input is at best PARTIAL; any quantity computed
    from a NOT DERIVABLE input is NOT DERIVABLE.' Built in quantity.py,
    pinned in test_quantity_status_2026_08_14_send16.py."""
    with pytest.raises(ValueError):
        q.Quantity(1.0, "")                       # no status → error
    nd = q.not_derivable("h died", dead_input="walls.back.height_ft")
    assert q.propagate([q.derived(10.0), nd]).status == q.NOT_DERIVABLE


def test_ruling_K_not_derivable_line_shape():
    """RULING K (send-16): 'quantity column reads NOT DERIVABLE and names
    the input that died. Its price column is EMPTY — not zero. It registers
    as a blocker on the quote gate.'"""
    line = q.render_line(q.not_derivable("width not read",
                                         dead_input="walls.left.width_ft"))
    assert line["price"] is None and line["blocks_gate"] is True
    assert "walls.left.width_ft" in line["quantity_text"]


def test_ruling_L_incomplete_total_is_not_a_price():
    """RULING L (send-16): 'Any total, subtotal, or grand total that sums
    over a NOT DERIVABLE line is marked INCOMPLETE, states how many lines
    are refused, and is never presented as a price.'"""
    t = q.rollup_total([q.derived(100.0),
                        q.not_derivable("h died", dead_input="x")])
    assert t["incomplete"] and t["refused_count"] == 1 and t["is_price"] is False


def test_ruling_E_and_I_carried_from_send15_still_hold():
    """RULING E (invert axis catalog) and RULING I (archive send prose)
    were built in send-15 and remain on the record; send-16 leaves them
    unchanged. Cross-ref: test_axis_declaration_2026_08_14_send15.py and
    test_rulings_archive_2026_08_14_send15.py."""
    import routes.ai_blueprint as ab
    assert ab._leaf_axis("parapet_ft") == "U"
    assert (Path(__file__).resolve().parents[1]
            / "rulings_archive" / "send16.md").exists()


def test_rulings_G_H_wired_end_to_end_through_quantity():
    # BUILT send-18 (Ruling Q/R): the corner/OSC average, base-course, and
    # batten readers now carry status, and propagate() flows a NOT DERIVABLE
    # input into the line (blocks the gate) rather than a silent number.
    # REMAINING OWNER (send-18 acceptance): Howard's EST-713272 four-face
    # re-fire stamps that the derivation is honest before money is wired
    # onto the surface — that is Howard's side, not a build here.
    from lp_package import osc_from_corner_locations
    osc = osc_from_corner_locations(
        [{"type": "outside", "walls": ["ghost"], "tier": "confirmed"}], {})
    assert osc["status"] == q.NOT_DERIVABLE and osc["blocks_gate"] is True
    assert "ghost" in osc["dead_walls"]


@pytest.mark.skip(reason=(
    "ruling:held: RULING F RETIRED as written (send-16 supersedes send-15 "
    "F). Money-line flagging / conflict-only-vs-all-shares is NOT built and "
    "will NOT be: status travels with the quantity (J) and the money "
    "surface renders what arrived — building money-line logic would violate "
    "the sealed principle ('no special money-line logic'). What survives is "
    "only a display/zoom rendering choice, made after the status plumbing "
    "is wired. WHAT WOULD UNHOLD IT: nothing to build here by design; a "
    "future display-choice ruling, if any."))
def test_ruling_F_money_line_flagging_retired():
    raise AssertionError("retired by send-16 — see reason")
