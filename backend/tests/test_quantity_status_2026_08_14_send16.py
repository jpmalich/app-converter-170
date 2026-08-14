"""RULING J / K / L — status-carrying quantities (send-16, 2026-08-14).

J: status is a property of the quantity (DERIVED / PARTIAL / NOT DERIVABLE);
   a quantity cannot exist without one; status PROPAGATES (worst wins).
K: a NOT DERIVABLE line is present, names the dead input, price column is
   EMPTY (not $0), and blocks the quote gate.
L: any total summing over a NOT DERIVABLE line is INCOMPLETE, states how
   many lines are refused, and is never presented as a price.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import quantity as q  # noqa: E402


# ---- Ruling J: a quantity cannot exist without a status --------------

def test_quantity_requires_a_valid_status():
    with pytest.raises(ValueError):
        q.Quantity(100.0, "DERIVEDish")     # typo'd / defaulted status rejected
    with pytest.raises(ValueError):
        q.Quantity(100.0, "")


def test_not_derivable_never_carries_a_number():
    nd = q.not_derivable("wall width not read", dead_input="walls.left.width_ft")
    assert nd.value is None
    assert nd.derivable is False
    assert "walls.left.width_ft" in nd.excluded


def test_status_propagates_worst_wins():
    d = q.derived(10.0)
    p = q.partial(6.0, excluded=["garage wing"])
    nd = q.not_derivable("height died", dead_input="walls.back.height_ft")
    # all derived -> derived
    assert q.propagate([d, d], value=20.0).status == q.DERIVED
    # any partial, no not-derivable -> partial
    assert q.propagate([d, p], value=16.0).status == q.PARTIAL
    # any not-derivable -> not derivable, value dropped, dead input named
    poisoned = q.propagate([d, p, nd], value=99.0)
    assert poisoned.status == q.NOT_DERIVABLE
    assert poisoned.value is None
    assert "walls.back.height_ft" in poisoned.excluded


# ---- Ruling K: a NOT DERIVABLE line ----------------------------------

def test_not_derivable_line_empty_price_names_input_blocks_gate():
    line = q.render_line(
        q.not_derivable("wall width not read", dead_input="walls.left.width_ft"))
    assert line["price"] is None            # EMPTY, not 0
    assert line["value"] is None
    assert "NOT DERIVABLE" in line["quantity_text"]
    assert "walls.left.width_ft" in line["quantity_text"]
    assert line["blocks_gate"] is True


def test_partial_line_shows_subset_and_names_excluded():
    line = q.render_line(q.partial(200.0, excluded=["garage wing"]))
    assert line["value"] == 200.0
    assert "PARTIAL" in line["quantity_text"]
    assert "garage wing" in line["quantity_text"]
    assert line["blocks_gate"] is False


def test_derived_line_renders_normally():
    line = q.render_line(q.derived(42.0))
    assert line["value"] == 42.0 and line["blocks_gate"] is False


# ---- Ruling L: an incomplete total is not a price --------------------

def test_total_over_a_not_derivable_line_is_incomplete_never_a_price():
    total = q.rollup_total([
        q.derived(100.0), q.derived(50.0),
        q.not_derivable("height died", dead_input="walls.back.height_ft")])
    assert total["incomplete"] is True
    assert total["refused_count"] == 1
    assert total["is_price"] is False       # NEVER presented as a price
    assert total["value"] is None


def test_total_over_a_partial_line_is_partial_not_a_price():
    total = q.rollup_total([q.derived(100.0),
                            q.partial(40.0, excluded=["wing"])])
    assert total["status"] == q.PARTIAL
    assert total["is_price"] is False
    assert total["incomplete"] is True


def test_clean_total_is_a_price():
    total = q.rollup_total([q.derived(100.0), q.derived(50.0)])
    assert total["is_price"] is True and total["value"] == 150.0
