"""Unit tests for the J-channel HOVER mapping helper.

Howard's formula (Iter 78 eaves-to-Finish-Trim, REVISED by the Boni
ruling 2026-08-05 — EAVE/PORCH-J):
  pcs = ceil( (window + patio_door perimeter + rakes
               + eave wall-channel + porch ceiling channel) / 12.5 )

Iter 78 removed eaves because they double-counted against Finish Trim's
undersill run. The Boni ruling put a DIFFERENT eave run back: the
wall-side receiving channel the eave soffit panels tuck into — a real
material on every VINYL/ASCEND soffit job (never LP SmartSide; family
scoping pinned in test_boni_rulings_2026_08_05). Finish Trim keeps its
own eave term — two different channels on the same run.

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
    + patio door), rakes 60, 1 entry door, 0 garage. Eaves ride as the
    wall-side soffit channel (ruled 2026-08-05)."""
    m = {
        "opening_perimeter_lf": 180,
        "entry_door_count": 1,
        "garage_door_count": 0,
        "eaves_lf": 100,  # wall-side eave receiving channel
        "rakes_lf": 60,
    }
    # win+patio = 180 - 19 = 161
    # total = 161 + 60 + 100 eave channel = 321 LF
    # pcs = ceil(321 / 12.5) = 26   (pre-ruling: 18)
    assert _j_channel_pcs(m) == 26


def test_house_with_garage_door():
    """Garage door perimeter (~32 LF) is also subtracted, then added back."""
    m = {
        "opening_perimeter_lf": 250,
        "entry_door_count": 1,
        "garage_door_count": 1,
        "eaves_lf": 120,  # wall-side eave receiving channel
        "rakes_lf": 80,
    }
    # win+patio = 250 - 19 - 32 = 199
    # total = 199 + 32 (garage back in) + 80 + 120 eave channel = 431 LF
    # pcs = ceil(431 / 12.5) = 35   (pre-ruling: 25)
    assert _j_channel_pcs(m) == 35


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
    """If counts over-estimate, win+patio can't go negative."""
    m = {
        "opening_perimeter_lf": 10,
        "entry_door_count": 5,  # 5 × 19 = 95 → would be negative
        "eaves_lf": 50,         # wall-side eave receiving channel
        "rakes_lf": 12,
    }
    # win+patio clamped to 0, total = 12 + 50 = 62 → ceil(62/12.5) = 5
    # (pre-ruling: 1)
    assert _j_channel_pcs(m) == 5


def test_only_rakes():
    """If no openings, J covers rakes + the eave wall channel."""
    m = {
        "eaves_lf": 150,  # wall-side eave receiving channel
        "rakes_lf": 70,
    }
    # total = 70 + 150 = 220 → ceil(220/12.5) = 18   (pre-ruling: 6)
    assert _j_channel_pcs(m) == 18


def test_letrick_reconciliation():
    """LETRICK final-construction-prints regression: 54×30 1-story L-shape
    with 9 windows, 2 entry doors, ~108 eaves, ~34 rakes. Howard's actual
    order was 20 pcs. Pre-ruling formula landed 16 (4 short — entry-door
    wrap uncounted). With the 2026-08-05 eave-channel term the formula
    lands 25 (+5 over the order — NAMED in the ruling report, not hidden:
    LETRICK's crew may not have channeled the full eave run)."""
    m = {
        "window_count": 9,
        "entry_door_count": 2,
        "garage_door_count": 0,
        "patio_door_count": 0,
        "eaves_lf": 108,  # wall-side eave receiving channel
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
    # total = 159 + 34 + 108 = 301 LF → ceil(301/12.5) = 25 pcs
    pcs = _j_channel_pcs(m)
    assert pcs == 25, f"LETRICK J with eave channel expected 25, got {pcs}"
