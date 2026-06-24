"""Unit tests for the trim/accessory HOVER mappers updated per Howard's
siding-takeoff HTML formulas (Iter 46).

Formulas:
  • Starter pcs        = ceil(starter_lf / 12.5)
  • Outside corner pcs = ceil(outside_corner_lf / 12.5)   (min 1)
  • Inside corner pcs  = ceil(inside_corner_lf / 12.5)
  • Fascia LF          = eaves_lf + rakes_lf
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from routes.hover import HOVER_MAPPING_SPEC  # noqa: E402


def _spec(item_name: str, tab: str):
    for s in HOVER_MAPPING_SPEC:
        if s.get("item") == item_name and tab in (s.get("tabs") or []):
            return s
    raise AssertionError(f"Spec not found: {item_name} on tab {tab}")


def test_starter_vinyl_ceil_12_5():
    s = _spec("Starter", "vinyl")
    # 100 LF / 12.5 = 8 pcs
    assert s["extract"]({"starter_lf": 100}) == 8
    # 101 LF / 12.5 = 8.08 → 9 pcs (round up)
    assert s["extract"]({"starter_lf": 101}) == 9
    # Zero in → zero out
    assert s["extract"]({}) == 0


def test_outside_corner_vinyl_ceil_12_5_min_1():
    s = _spec("Outside corners Standard color", "vinyl")
    # 50 LF / 12.5 = 4 pcs
    assert s["extract"]({"outside_corner_lf": 50}) == 4
    # 51 LF → 4.08 → 5 pcs
    assert s["extract"]({"outside_corner_lf": 51}) == 5
    # Zero in → still 1 (always need at least one)
    assert s["extract"]({}) == 1


def test_inside_corner_vinyl_ceil_12_5_zero_ok():
    s = _spec("Inside Corners (Siding) Standard color", "vinyl")
    assert s["extract"]({"inside_corner_lf": 12.5}) == 1
    assert s["extract"]({"inside_corner_lf": 13}) == 2
    # Some houses have no inside corners
    assert s["extract"]({}) == 0


def test_fascia_includes_rakes():
    s = _spec('Fascia/rake or frieze up to 8" coverage', "vinyl")
    # 100 eaves + 60 rakes → 160 LF
    assert s["extract"]({"eaves_lf": 100, "rakes_lf": 60}) == 160
    # Eaves only (no gables)
    assert s["extract"]({"eaves_lf": 100}) == 100


def test_starter_ascend_matches_vinyl():
    v = _spec("Starter", "vinyl")
    a = _spec("Ascend - Starter", "ascend")
    m = {"starter_lf": 175}
    assert v["extract"](m) == a["extract"](m) == 14


def test_finish_trim_full_window_perimeter_when_dims_available():
    """Iter 78f — Finish Trim uses FULL window perimeter (top + sides + bottom)
    when per-window dimensions are present in `windows[]`."""
    s = _spec("Finish Trim Standard color", "vinyl")
    # 100 eaves + 2 windows @ 36x48 + 48x60 → perim_in = 2×(36+48) + 2×(48+60)
    # = 168 + 216 = 384 in / 12 = 32 LF. Total = 132 LF / 12.5 = 10.56 → 11 pcs.
    assert s["extract"]({
        "eaves_lf": 100,
        "windows": [
            {"width_in": 36, "height_in": 48},
            {"width_in": 48, "height_in": 60},
        ],
    }) == 11


def test_finish_trim_falls_back_to_14lf_per_window():
    """Iter 78f — When HOVER didn't break out per-window dims, fall back to
    14 LF/window (3'0" × 4'0" typical replacement window perimeter)."""
    s = _spec("Finish Trim Standard color", "vinyl")
    # 100 eaves + 5 windows × 14 LF = 170 LF / 12.5 = 13.6 → 14 pcs
    assert s["extract"]({
        "eaves_lf": 100,
        "window_count": 5,
    }) == 14
