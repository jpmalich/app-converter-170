"""BARS = CHIPS (Howard ruled 2026-08-07, Bar line d enforcement).

"Update UI logic so the coverage bar and the formula chip read from the
EXACT SAME source." Finish trim bar 637 vs chip 279 and Soffit-J bar 410
vs chip 24 died here: the client recomputed retired formulas
(full-window-perimeter finish trim, 2×rakes soffit-J, eaves/30 runs).

Now the backend emits a `viz` breakdown ON THE LINE — the same terms the
extract divided — and the card renders only that. Pins:
1. viz segments sum ÷ divisor == the line's own qty (finish trim,
   soffit-J, with and without porch).
2. gutter viz runs/downspouts equal the accessory quantities they explain.
3. The frontend carries NO retired formula copy (source grep).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.hover import (  # noqa: E402
    _build_lines, _finish_trim_viz, _soffit_j_viz, _gutter_viz,
)


def _m(**kw):
    base = {"siding_with_openings_sqft": 2000, "eaves_lf": 120,
            "rakes_lf": 60, "window_count": 8,
            "windows": [{"width_in": 36, "height_in": 60}] * 8}
    base.update(kw)
    return base


def _line(lines, frag, tab="vinyl"):
    for l in lines:
        if l["tab"] == tab and frag.lower() in str(l.get("name") or "").lower():
            return l
    raise KeyError(frag)


def test_finish_trim_bar_total_reproduces_the_chip():
    m = _m()
    lines = _build_lines(m)
    ft = _line(lines, "Finish Trim Standard color")
    viz = ft.get("viz")
    assert viz, "finish trim line must carry its viz breakdown"
    total = sum(s["lf"] for s in viz["segments"])
    assert math.ceil(total / viz["divisor"] - 1e-9) == ft["qty"], \
        "the bar total MUST divide to the same pcs the chip prints"
    labels = [s["label"] for s in viz["segments"]]
    assert "Window sills" in labels, \
        "finish trim explains SILLS (ruled 2026-08-01) — never full window perimeter"


def test_soffit_j_bar_total_reproduces_the_chip_with_porch():
    m = _m(porch_ceiling_sqft=99,
           _porch_dims=[{"width_ft": 6, "length_ft": 16.5}])
    lines = _build_lines(m)
    sj = _line(lines, "Soffit J-Channel")
    viz = sj.get("viz")
    assert viz, "soffit-J line must carry its viz breakdown"
    total = sum(s["lf"] for s in viz["segments"])
    assert math.ceil(total / viz["divisor"] - 1e-9) == sj["qty"]
    seg = {s["label"]: s["lf"] for s in viz["segments"]}
    assert seg["Rakes × 1 pass"] == 60, "ONE rake pass (R1) — never 2×"
    assert seg["Porch ceiling channel"] == 45, "real dims 2×(16.5+6)"


def test_gutter_viz_explains_the_accessory_quantities():
    m = _m(_gutter_runs=[{"label": "front", "lf": 60},
                         {"label": "back", "lf": 40},
                         {"label": "porch", "lf": 20}])
    m["eaves_lf"] = 190  # discarded plane sum
    lines = _build_lines(m)
    caps = _line(lines, "End Cap")
    viz = caps.get("viz")
    assert viz and viz["basis"] == "run_inventory"
    assert viz["runs"] == 3 and viz["run_labels"] == ["front", "back", "porch"]
    assert caps["qty"] == viz["runs"] * 2
    assert _line(lines, "elbow")["qty"] == viz["downspouts"] * 2
    assert _line(lines, "Hangars")["qty"] == viz["hangers_spaced"] + viz["runs"]
    assert viz["gutter_lf"] == 120, "chips divide the run sum, never 190"


def test_viz_absent_when_nothing_to_explain():
    assert _finish_trim_viz({"eaves_lf": 0, "window_count": 0}) is None
    assert _soffit_j_viz({"eaves_lf": 0, "rakes_lf": 0}) is None
    assert _gutter_viz({"eaves_lf": 0}) is None


def test_frontend_carries_no_retired_formula_copy():
    jsx = (Path(__file__).resolve().parents[2]
           / "frontend/src/components/estimate/TakeoffReconCard.jsx").read_text()
    for banned in ("Full Window Perim", "2 × Rakes", "rakesLf * 2",
                   "windowPerimTotalLf", "Math.ceil(eavesLf / 30)",
                   "Math.ceil(eavesLf / 25)"):
        assert banned not in jsx, \
            f"retired client-side formula copy resurfaced: {banned!r}"
    assert "vizSegments" in jsx and ".viz" in jsx, \
        "the card must render the line's server-computed viz"
