"""Unit tests for the J-channel HOVER mapping helper.

Howard's formula (Iter 78 — eaves moved to Finish Trim):
  pcs = ceil( (window + patio_door perimeter + rakes) / 12.5 )

Eaves used to be added here too, but that double-counted eave LF against
the Finish Trim line (which already includes eaves). Per the LETRICK
reconciliation, eaves now belong exclusively to Finish Trim.

HOVER reports `opening_perimeter_lf` as one lumped value covering all
openings, so we back out entry-door (~19 LF) and garage-door (~32 LF)
typical perimeters via their counts.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from routes.hover import _j_channel_pcs  # noqa: E402


def test_typical_house_with_entry_door():
    """Mid-size 2-story: ~180 LF total opening perim (entry door + windows
    + patio door), rakes 60, 1 entry door, 0 garage. Eaves no longer in J."""
    m = {
        "opening_perimeter_lf": 180,
        "entry_door_count": 1,
        "garage_door_count": 0,
        "eaves_lf": 100,  # ignored by J-channel now
        "rakes_lf": 60,
    }
    # win+patio = 180 - 19 = 161
    # total = 161 + 60 = 221 LF
    # pcs = ceil(221 / 12.5) = 18
    assert _j_channel_pcs(m) == 18


def test_house_with_garage_door():
    """Garage door perimeter (~32 LF) is also subtracted, then added back."""
    m = {
        "opening_perimeter_lf": 250,
        "entry_door_count": 1,
        "garage_door_count": 1,
        "eaves_lf": 120,  # ignored
        "rakes_lf": 80,
    }
    # win+patio = 250 - 19 - 32 = 199
    # total = 199 + 32 (garage back in) + 80 = 311 LF
    # pcs = ceil(311 / 12.5) = 25
    assert _j_channel_pcs(m) == 25


def test_zero_inputs():
    assert _j_channel_pcs({}) == 0


def test_rounds_up_not_to_nearest():
    """1 LF over a piece boundary must still round up."""
    m = {
        "opening_perimeter_lf": 0,
        "eaves_lf": 0,
        "rakes_lf": 13,    # 13 / 12.5 = 1.04 → 2 pcs
    }
    assert _j_channel_pcs(m) == 2


def test_entry_door_subtraction_clamped_at_zero():
    """If counts over-estimate, win+patio can't go negative.
    With eaves removed, only rakes drive the count here."""
    m = {
        "opening_perimeter_lf": 10,
        "entry_door_count": 5,  # 5 × 19 = 95 → would be negative
        "eaves_lf": 50,         # ignored
        "rakes_lf": 12,
    }
    # win+patio clamped to 0, total = 12 → ceil(12/12.5) = 1
    assert _j_channel_pcs(m) == 1


def test_only_rakes():
    """If no openings, J-channel covers rake runs only (eaves go to Finish Trim)."""
    m = {
        "eaves_lf": 150,  # ignored
        "rakes_lf": 70,
    }
    # total = 70 → ceil(70/12.5) = 6
    assert _j_channel_pcs(m) == 6


def test_letrick_reconciliation():
    """LETRICK final-construction-prints regression: 54×30 1-story L-shape
    with 9 windows, 2 entry doors, ~108 eaves, ~34 rakes. After the
    Iter 78 eaves-removal fix, the formula should land near Howard's
    actual order of 20 pcs (still slightly conservative because the
    fallback window-perim is 14 LF/window; AI returns individual dims)."""
    m = {
        "window_count": 9,
        "entry_door_count": 2,
        "garage_door_count": 0,
        "patio_door_count": 0,
        "eaves_lf": 108,  # ignored — verifies the fix
        "rakes_lf": 34,
        "windows": [
            {"width_in": 36, "height_in": 60} for _ in range(4)
        ] + [
            {"width_in": 32, "height_in": 48},
        ] + [
            {"width_in": 72, "height_in": 66} for _ in range(3)
        ] + [
            {"width_in": 28, "height_in": 48},
        ],
    }
    # windows perim = 2 × (36+60)×4 + 2 × (32+48) + 2 × (72+66)×3 + 2 × (28+48)
    #               = 768 + 160 + 828 + 152 = 1908 in = 159 LF
    # total = 159 + 34 = 193 LF → ceil(193/12.5) = 16 pcs
    # (Within 4 pcs of Howard's actual 20 — the gap is entry-door wrap
    # which the formula doesn't add. Acceptable.)
    pcs = _j_channel_pcs(m)
    assert 14 <= pcs <= 22, f"LETRICK J-channel expected ~16-20, got {pcs}"
