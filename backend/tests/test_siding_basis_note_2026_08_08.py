"""SIDING BASIS TRUTH (Howard's open question, answered 2026-08-08).

The question: "the estimate card displays WASTE · 0% while the soffit
line carries x1.20 — answer whether the SIDING SQUARE COUNT carries any
hidden multiplier of its own."

The answer, pinned: NO multiplier — but the LABEL lied on blueprint
jobs. Blueprint aggregation aliased the gross area into
`siding_with_openings_sqft`, so the Charter Oak note printed "From
HOVER 'SIDING WASTE TOTALS → + Openings < 20ft² +10%'" over a number
that never received 10% of anything. The quantity was always gross
wall area ÷ 100 (openings NOT deducted — ruled convention), ×1.0.

Fix: the alias dies; the note is a callable that names the actual
basis. The +10% claim prints ONLY when the HOVER waste-totals row
actually fed the number. PURITY: the quantity itself is untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import _aggregate_to_hover_shape  # noqa: E402
from routes.hover import HOVER_MAPPING_SPEC  # noqa: E402


def _spec():
    rows = [s for s in HOVER_MAPPING_SPEC
            if "Charter Oak Standard color Dutch Lap" in str(s.get("item"))]
    assert len(rows) == 1
    return rows[0]


def test_hover_job_keeps_the_plus10_provenance_note():
    s = _spec()
    m = {"siding_with_openings_sqft": 4110, "siding_sqft": 3736}
    assert s["extract"](m) == 41.1
    assert "+ Openings < 20ft² +10%" in s["note"](m)


def test_blueprint_job_names_the_real_basis_no_false_plus10_claim():
    s = _spec()
    m = {"siding_with_openings_sqft": None, "siding_sqft": 3990}
    assert s["extract"](m) == 39.9, "fallback keeps the identical quantity"
    note = s["note"](m)
    assert "+10%" not in note, "a +10% claim over a number that never got it"
    assert "openings NOT deducted" in note
    assert "no waste inside this number" in note


def test_blueprint_aggregation_never_aliases_the_hover_row():
    m = _aggregate_to_hover_shape(
        {"walls": [{"label": "front", "width_ft": 40, "height_ft": 10},
                   {"label": "back", "width_ft": 40, "height_ft": 10},
                   {"label": "left", "width_ft": 25, "height_ft": 10},
                   {"label": "right", "width_ft": 25, "height_ft": 10}]})
    assert m["siding_with_openings_sqft"] is None
    assert m["siding_sqft"] > 0
