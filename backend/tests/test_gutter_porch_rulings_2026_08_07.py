"""GUTTER ACCESSORIES + PORCH-J ASSEMBLY SPLIT (Howard ruled 2026-08-07).

1. ACCESSORIES CONSUME THE RUN INVENTORY: end caps, hangers, downspouts,
   elbows divide the gutter figure (run sum when a door read runs) and
   take the run COUNT from the inventory — never again 7 invented runs
   off a plane-sum the card printed as 3. The ~1-run-per-30-LF estimate
   survives ONLY as the no-inventory fallback (byte-identical).
2. PORCH-J SPLIT: the ceiling-receiving channel prints on the SOFFIT-J
   line at FULL PERIMETER; the wall J beneath prints on the WALL-J line
   at wall-abutting length only.
3. AN AREA DOES NOT DETERMINE A SHAPE: real dims govern (contractor
   entry or porch roof plane); square-assumption survives only as a
   DISCLOSED MINIMUM with a flag. Never a fabricated rectangle.

PURITY: fixtures are synthetic; no assertion targets an installed list.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.hover import (  # noqa: E402
    _build_lines, _downspout_count, _elbow_breakdown, _eave_porch_j_lf,
    _gutter_run_count, _hangers_count, _hangers_breakdown, _porch_geom,
    _porch_soffit_j_lf,
)


def _m(**kw):
    base = {"siding_with_openings_sqft": 2000, "eaves_lf": 120,
            "rakes_lf": 60, "window_count": 8,
            "windows": [{"width_in": 36, "height_in": 60}] * 8}
    base.update(kw)
    return base


RUNS = [{"label": "front", "lf": 60}, {"label": "back", "lf": 40},
        {"label": "porch", "lf": 20}]


def _qty(lines, frag, tab="vinyl"):
    for l in lines:
        if l["tab"] == tab and frag.lower() in str(l.get("name") or "").lower():
            return l
    raise KeyError(frag)


# ---------------------------------------------------------------- gutter
def test_run_count_comes_from_the_inventory():
    m = _m(_gutter_runs=RUNS)
    assert _gutter_run_count(m) == 3, "3 read runs must never become 7"
    # fallback unchanged when no inventory
    assert _gutter_run_count(_m()) == max(2, math.ceil(120 / 30))


def test_end_caps_hangers_downspouts_divide_the_run_sum():
    m = _m(_gutter_runs=RUNS)  # run sum 120 == eaves here? no: 60+40+20=120
    m["eaves_lf"] = 190  # plane-sum DIFFERS — the discarded figure
    lines = _build_lines(m)
    caps = _qty(lines, "End Cap")
    assert caps["qty"] == 6, "2 caps × 3 read runs"
    assert "run inventory" in str(caps["note"])
    assert "front" in str(caps["note"]) and "porch" in str(caps["note"])
    assert _downspout_count(m) == max(2, math.ceil(120 / 25))
    assert _qty(lines, "elbow")["qty"] == _downspout_count(m) * 2
    assert _hangers_count(m) == math.ceil(120 / 2) + 3
    hb = _hangers_breakdown(m)
    assert "run inventory" in hb and "190" not in hb, \
        "no accessory may divide the discarded plane sum"
    assert "door-read run inventory" in hb
    eb = _elbow_breakdown(m)
    assert "120" in eb and "190" not in eb


def test_no_inventory_fallback_is_byte_identical():
    m = _m()
    lines = _build_lines(m)
    caps = _qty(lines, "End Cap")
    assert caps["qty"] == max(2, math.ceil(120 / 30)) * 2
    assert "min 2 runs" in str(caps["note"])
    assert _hangers_count(m) == math.ceil(120 / 2) + max(2, math.ceil(120 / 30))


# ----------------------------------------------------------- porch shape
def test_real_dims_govern_the_porch_shape():
    g = _porch_geom(_m(porch_ceiling_sqft=99,
                       _porch_dims=[{"width_ft": 6, "length_ft": 16.5}]))
    assert g["basis"] == "real_dims"
    assert g["perimeter_lf"] == 45.0
    assert g["wall_lf"] == 16.5, "the longer side is the wall side"


def test_porch_plane_reads_beat_the_square_assumption():
    g = _porch_geom(_m(porch_ceiling_sqft=150, _roof_planes=[
        {"label": "porch", "eave_lf": 15, "rake_lf": 20, "is_porch": True}]))
    assert g["basis"] == "porch_plane"
    assert g["perimeter_lf"] == 2 * (15 + 10)
    assert g["wall_lf"] == 15


def test_area_alone_is_a_flagged_minimum_never_a_rectangle():
    g = _porch_geom(_m(porch_ceiling_sqft=99))
    assert g["basis"] == "square_minimum"
    assert abs(g["perimeter_lf"] - 4 * math.sqrt(99)) < 1e-9
    _, br = _porch_soffit_j_lf(_m(porch_ceiling_sqft=99))
    assert "MINIMUM" in br and "does not determine a shape" in br
    wl, wbr = _eave_porch_j_lf(_m(porch_ceiling_sqft=99))
    assert "MINIMUM" in wbr and "FLAG" in wbr


# ------------------------------------------------------------- the split
def test_ceiling_channel_prints_on_the_soffit_j_line():
    m = _m(porch_ceiling_sqft=99,
           _porch_dims=[{"width_ft": 6, "length_ft": 16.5}])
    lines = _build_lines(m)
    sj = _qty(lines, "Soffit J-Channel")
    assert sj["qty"] == math.ceil((120 + 60 + 45) / 12.5 - 1e-9)
    note = str(sj["note"])
    assert "porch ceiling channel" in note and "FULL PERIMETER" in note
    assert "real dims" in note


def test_wall_j_carries_only_the_wall_abutting_length():
    m = _m(porch_ceiling_sqft=99,
           _porch_dims=[{"width_ft": 6, "length_ft": 16.5}])
    lf, br = _eave_porch_j_lf(m)
    assert lf == 120 + 16.5
    assert "wall-abutting side only" in br
    assert "moved to the Soffit-J line" in br
    assert "45" not in br.split("porch wall-J")[1][:40], \
        "the full perimeter must not ride the wall-J line"


def test_no_porch_is_named_on_both_lines_never_silent():
    lf, br = _eave_porch_j_lf(_m())
    assert "no porch ceiling identified" in br
    plf, pbr = _porch_soffit_j_lf(_m())
    assert plf == 0.0
