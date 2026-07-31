"""WRAP ROLL CONVERSION PINS (Howard ruled 2026-07-31).

House Wrap sells by the ROLL (9.00 SQ/roll, $119.11) · RainDrop by the
ROLL (11.25 SQ/roll, $336.13). TWO divisors — never a shared number.
Howard's admin entry landed TRANSPOSED and only his sanity check caught
it; the direction pin below is that check, made permanent:
31.5 SQ of House Wrap was $363.83 per-SQ → 4 rolls × $119.11 = $476.44.
Whole rolls rounded up can only move a wrap line UP or hold it.
"""
import math

import pytest

from catalog_seed import IDENTICAL_PRICES, ITEM_META
from routes.hover import (
    HOUSE_WRAP_SQ_PER_ROLL,
    HOVER_MAPPING_SPEC,
    RAINDROP_SQ_PER_ROLL,
    _bake_tab_waste,
)


def _spec(item):
    rows = [s for s in HOVER_MAPPING_SPEC if s.get("item") == item]
    assert len(rows) == 1, f"exactly one mapping row for {item}"
    return rows[0]


class TestSeedPins:
    def test_two_distinct_divisors(self):
        assert HOUSE_WRAP_SQ_PER_ROLL == 9.00
        assert RAINDROP_SQ_PER_ROLL == 11.25
        assert HOUSE_WRAP_SQ_PER_ROLL != RAINDROP_SQ_PER_ROLL

    def test_units_are_roll(self):
        assert ITEM_META["House Wrap"][0] == "ROLL"
        assert ITEM_META["RainDrop"][0] == "ROLL"

    def test_roll_prices_not_transposed(self):
        # The defect this file exists for: HW/RD landed crossed on the
        # admin page. $119.11 is the HOUSE WRAP roll; $336.13 is RAINDROP.
        assert IDENTICAL_PRICES["House Wrap"] == 119.11
        assert IDENTICAL_PRICES["RainDrop"] == 336.13


class TestMappingEmitsRolls:
    def test_house_wrap_unit_and_math(self):
        s = _spec("House Wrap")
        assert s["unit"] == "ROLL"
        assert s["extract"]({"siding_with_openings_sqft": 2835}) == round(28.35 / 9.0, 2)

    def test_raindrop_unit_and_math(self):
        s = _spec("RainDrop")
        assert s["unit"] == "ROLL"
        assert s["extract"]({"siding_with_openings_sqft": 2835}) == round(28.35 / 11.25, 2)

    def test_waste_ceils_on_the_roll_only(self):
        # Fractional rolls from the mapping; the ONE waste emitter bakes
        # the field % then ceils — the roll is the only rounded unit.
        out = _bake_tab_waste([{"name": "House Wrap", "section": "Siding Accessories",
                                "qty": 3.5, "unit": "ROLL", "mat": 119.11}], 10)
        assert out[0]["qty"] == 4.0
        assert out[0]["raw_qty"] == 3.5


class TestHowardsCheck:
    def test_31_5_sq_house_wrap_is_4_rolls_476_44(self):
        rolls = math.ceil(31.5 / HOUSE_WRAP_SQ_PER_ROLL - 1e-9)
        assert rolls == 4
        assert round(rolls * IDENTICAL_PRICES["House Wrap"], 2) == 476.44
        assert round(31.5 * 11.55, 2) == 363.83  # the old per-SQ dollar he quoted

    @pytest.mark.parametrize("sq", [9, 16, 27, 31.5, 32, 42.4, 47, 50])
    def test_house_wrap_only_moves_up_or_holds(self, sq):
        old = sq * 11.55
        new = math.ceil(sq / HOUSE_WRAP_SQ_PER_ROLL - 1e-9) * 119.11
        assert new >= old, f"wrap line moved CHEAPER at {sq} SQ — roll math inverted"
