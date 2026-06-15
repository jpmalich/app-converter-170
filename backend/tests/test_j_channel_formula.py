"""Unit tests for the J-channel HOVER mapping helper.

Howard's formula (Iter 45):
  pcs = ceil( (window + patio_door perimeter + eaves + rakes) / 12.5 )

HOVER reports `opening_perimeter_lf` as one lumped value covering all
openings, so we back out entry-door (~19 LF) and garage-door (~32 LF)
typical perimeters via their counts.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tests import the module directly, which would otherwise pull in
# routes/__init__.py → ai_measure → deps → db.MONGO_URL. Side-step that
# by ensuring env vars are loaded before the import.
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from routes.hover import _j_channel_pcs  # noqa: E402


def test_typical_house_with_entry_door():
    """Mid-size 2-story: ~180 LF total opening perim (entry door + windows
    + patio door), eaves 100, rakes 60, 1 entry door, 0 garage."""
    m = {
        "opening_perimeter_lf": 180,
        "entry_door_count": 1,
        "garage_door_count": 0,
        "eaves_lf": 100,
        "rakes_lf": 60,
    }
    # win+patio = 180 - 19 = 161
    # total = 161 + 100 + 60 = 321 LF
    # pcs = ceil(321 / 12.5) = 26
    assert _j_channel_pcs(m) == 26


def test_house_with_garage_door():
    """Garage door perimeter (~32 LF) is also subtracted."""
    m = {
        "opening_perimeter_lf": 250,
        "entry_door_count": 1,
        "garage_door_count": 1,
        "eaves_lf": 120,
        "rakes_lf": 80,
    }
    # win+patio = 250 - 19 - 32 = 199
    # total = 199 + 120 + 80 = 399 LF
    # pcs = ceil(399 / 12.5) = 32
    assert _j_channel_pcs(m) == 32


def test_zero_inputs():
    assert _j_channel_pcs({}) == 0


def test_rounds_up_not_to_nearest():
    """1 LF over a piece boundary must still round up."""
    m = {
        "opening_perimeter_lf": 0,
        "eaves_lf": 13,    # 13 / 12.5 = 1.04 → 2 pcs
        "rakes_lf": 0,
    }
    assert _j_channel_pcs(m) == 2


def test_entry_door_subtraction_clamped_at_zero():
    """If counts over-estimate, win+patio can't go negative."""
    m = {
        "opening_perimeter_lf": 10,
        "entry_door_count": 5,  # 5 × 19 = 95 → would be negative
        "eaves_lf": 50,
        "rakes_lf": 0,
    }
    # win+patio clamped to 0, total = 50 → ceil(50/12.5) = 4
    assert _j_channel_pcs(m) == 4


def test_only_eaves_rakes():
    """If no openings, J-channel still covers eave + rake runs."""
    m = {
        "eaves_lf": 150,
        "rakes_lf": 70,
    }
    # total = 220 → ceil(220/12.5) = 18
    assert _j_channel_pcs(m) == 18
