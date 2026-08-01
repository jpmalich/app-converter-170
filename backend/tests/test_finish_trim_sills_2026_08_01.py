"""STEP 3 SEALS — FINISH TRIM = SILLS + TOP COURSE (Howard ruled 2026-08-01,
10e closing). wbw primary · per-window sill sum next · window_count × 3'
fallback (×14 full-opening constant retired for this term). J-channel
UNCHANGED at full perimeter. NAMED DELTA pinned: 3 Degree vinyl 59 → 32."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routes.hover import (_finish_trim_pcs, _finish_trim_sill_lf,
                          _j_channel_pcs, _window_perim_total_lf,
                          FINISH_TRIM_SILL_LF_FALLBACK, _build_lines)


def test_sill_fallback_is_3_feet_ruled():
    assert FINISH_TRIM_SILL_LF_FALLBACK == 3.0


def test_named_delta_3degree_vinyl_59_to_32():
    """3 Degree vinyl (EST-979583) stored measurements: eaves 308.25,
    30 windows, no per-window dims, no wbw. Old full-perimeter formula
    billed 59 pcs; the ruled sills+top-course formula bills 32."""
    m = {"eaves_lf": 308.25, "window_count": 30}
    assert _finish_trim_pcs(m) == 32
    old = math.ceil((308.25 + 30 * 14.0) / 12.5 - 1e-9)
    assert old == 59  # the retired number, kept as the named-delta record


def test_wbw_is_primary_sill_input():
    m = {"eaves_lf": 100, "window_count": 10,
         "window_bottom_width_total_lf": 28.5,
         "windows": [{"width_in": 60, "height_in": 60}]}
    assert _finish_trim_sill_lf(m) == 28.5          # measured wbw wins
    assert _finish_trim_pcs(m) == math.ceil(128.5 / 12.5)


def test_per_window_sill_sum_before_count_fallback():
    m = {"eaves_lf": 0,
         "windows": [{"width_in": 36, "height_in": 54}, {"width_in": 48, "height_in": 60}]}
    assert _finish_trim_sill_lf(m) == (36 + 48) / 12.0


def test_j_channel_unchanged_at_full_perimeter():
    """Howard: 'J-channel UNCHANGED at full perimeter' — the J still reads
    the full window perimeter helper, untouched by the sill ruling."""
    m = {"windows": [{"width_in": 36, "height_in": 48}], "rakes_lf": 0}
    assert _window_perim_total_lf(m) == 2 * (36 + 48) / 12.0
    assert _j_channel_pcs(m) == math.ceil((2 * (36 + 48) / 12.0) / 12.5 - 1e-9)


def test_only_finish_trim_moved_on_a_full_build():
    """Regression fence: on identical measurements, ONLY the Finish Trim
    rows differ between the retired and ruled formulas — every other line
    is byte-identical (checked by rebuilding with wbw forcing the same
    sill total the old formula would have used)."""
    m = {"eaves_lf": 308.25, "window_count": 30, "siding_sqft": 4239,
         "rakes_lf": 136, "starter_lf": 304, "opening_perimeter_lf": 574,
         "door_count": 7, "entry_door_count": 3, "patio_door_count": 3,
         "garage_door_count": 1, "outside_corner_count": 20,
         "outside_corner_lf": 140, "inside_corner_count": 6,
         "inside_corner_lf": 37}
    new_lines = {(l["tab"], l["name"]): l.get("qty") for l in _build_lines(dict(m))}
    m_old_basis = dict(m, window_bottom_width_total_lf=30 * 14.0)  # replicate old total
    old_lines = {(l["tab"], l["name"]): l.get("qty") for l in _build_lines(m_old_basis)}
    moved = {k for k in new_lines if new_lines[k] != old_lines.get(k)}
    assert all("Finish Trim" in k[1] for k in moved), f"non-ruled rows moved: {moved}"
    assert moved, "finish trim must move — silence here is the alarm"
