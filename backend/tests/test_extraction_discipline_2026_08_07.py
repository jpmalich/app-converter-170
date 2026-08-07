"""EXTRACTION DISCIPLINE (Howard ruled 2026-08-07 — the LAST item of the
confirmed order, informed by the probe: Boni is a SCAN, so the vision
path hardens).

Rulings pinned:
1. PRINTED DIMENSIONS ARE SACRED — never snapped to a catalog size; a
   catalog size prints BESIDE the printed one, never over it.
2. SH is never typed double_hung (single_hung mapped end to end).
3. INTERIOR DOORS never pollute the exterior count — no exterior
   evidence → dropped AND flagged (doors drive J-channel and coil).
4. TRADE-SPEC FIELDS (eave overhang, fascia width) fill from the plans
   or FLAG — a silently-held default never passes as a read value.
5. CORNER HEIGHTS ARE READ, NEVER CALCULATED — no ceiling-stack
   derivations; a calculated height returns null + a note.
6. PORCH PRINTED DIMS ride the plane — an area does not determine a
   shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _aggregate_to_hover_shape, build_blueprint_readback,
)
from routes.hover import _porch_geom  # noqa: E402


def _raw(**kw):
    base = {
        "avg_wall_height_ft": 18,
        "walls": [
            {"label": "front", "width_ft": 58, "height_ft": 18},
            {"label": "back", "width_ft": 58, "height_ft": 18},
            {"label": "left", "width_ft": 40, "height_ft": 18,
             "gable_triangle_height_ft": 11},
            {"label": "right", "width_ft": 39, "height_ft": 18,
             "gable_triangle_height_ft": 11},
        ],
        "windows": [], "doors": [], "roof_planes": [],
        "eaves_lf": 116, "rakes_lf": 82, "starter_lf": 194,
        "outside_corner_count": 4, "outside_corner_lf": 72,
        "inside_corner_count": 0, "inside_corner_lf": 0,
    }
    base.update(kw)
    return base


# ------------------------------------------------------------ prompt pins
def test_prompt_carries_the_rulings_verbatim_intent():
    for must in (
        "NEVER snap a printed dimension to a catalog size",
        "single_hung",
        "SH = single_hung",
        "exterior_evidence",
        "NEVER derive a corner height by stacking ceiling heights",
        "porch_width_ft",
        "eave_overhang_in",
        "fascia_width_in",
        "an area does not determine a shape",
    ):
        assert must in SYSTEM_PROMPT, f"prompt lost the ruling: {must!r}"


# ------------------------------------------------------- interior doors
def test_interior_doors_dropped_and_flagged_never_counted():
    raw = _raw(doors=[
        {"id": "D1", "width_in": 36, "height_in": 80, "qty": 1,
         "type_hint": "entry", "exterior_evidence": "elevation",
         "elevation": "front"},
        {"id": "D7", "width_in": 32, "height_in": 80, "qty": 4,
         "type_hint": "entry", "exterior_evidence": "none",
         "elevation": "unknown"},
    ])
    m = _aggregate_to_hover_shape(raw)
    assert m["entry_door_count"] == 1, \
        "interior 32x80s must never pollute the exterior count (1→5 class)"
    assert m["_interior_doors_dropped"] == 1
    rb = build_blueprint_readback(raw)
    assert any(f["code"] == "interior_doors_dropped" for f in rb["rail"]), \
        "the drop is FLAGGED on the card, never silent"


# ------------------------------------------------------ trade-spec fields
def test_printed_overhang_and_fascia_land_in_measurements():
    m = _aggregate_to_hover_shape(_raw(eave_overhang_in=16, fascia_width_in=6))
    assert m["_overhang_in_printed"] == 16.0
    assert m["fascia_width_in"] == 6.0 and m["_fascia_src"] == "printed"
    rb = build_blueprint_readback(_raw(eave_overhang_in=16, fascia_width_in=6))
    codes = [f["code"] for f in rb["rail"]]
    assert "overhang_printed" in codes and "fascia_printed" in codes


def test_undimensioned_spec_fields_are_flagged_not_defaulted():
    raw = _raw()
    m = _aggregate_to_hover_shape(raw)
    assert "_overhang_in_printed" not in m and "fascia_width_in" not in m
    rb = build_blueprint_readback(raw)
    codes = [f["code"] for f in rb["rail"]]
    assert "overhang_default" in codes and "fascia_default" in codes, \
        "a held default must be NAMED on the rail (12\"/8\" sitting silently was the defect)"


def test_worker_prefers_the_printed_overhang():
    src = Path(__file__).resolve().parents[1].joinpath(
        "routes/ai_blueprint.py").read_text()
    assert '_overhang_in_printed' in src
    assert '"_overhang_src"' in src or "'_overhang_src'" in src
    assert 'measurements["_overhang_src"] = "printed"' in src
    assert 'measurements["_overhang_src"] = "form_default"' in src


# --------------------------------------------------------- window sizes
def test_schedule_prints_both_printed_and_catalog_sizes():
    raw = _raw(windows=[
        {"id": "A", "printed_size": "3-0x5-0", "catalog_size": "38x54",
         "width_in": 36, "height_in": 60, "qty": 1,
         "type_hint": "single_hung", "elevation": "front"},
    ])
    m = _aggregate_to_hover_shape(raw)
    row = [r for r in m["_ai_openings_schedule"] if r["type"] == "window"][0]
    assert row["width_in"] == 36 and row["height_in"] == 60, \
        "printed dims are the authority — never the catalog's 38x54"
    assert row["printed_size"] == "3-0x5-0"
    assert row["catalog_size"] == "38x54"
    assert "3-0x5-0" in row["size_label"] and "catalog 38x54" in row["size_label"], \
        "PRINT BOTH — the catalog size sits beside the printed one"
    assert row["style"] == "Single Hung", "SH is never typed double_hung"


def test_single_hung_flows_to_derived_openings():
    raw = _raw(windows=[
        {"id": "B", "width_in": 36, "height_in": 60, "qty": 2,
         "type_hint": "single_hung", "elevation": "front"},
    ])
    m = _aggregate_to_hover_shape(raw)
    assert m is not None
    styles = {o["style"] for o in raw["openings"] if o["type"] == "window"}
    assert styles == {"Single Hung"}


# ------------------------------------------------------------ porch dims
def test_printed_porch_dims_ride_the_plane_into_the_shape():
    g = _porch_geom({
        "porch_ceiling_sqft": 99,
        "_roof_planes": [{"label": "porch", "is_porch": True,
                          "eave_lf": 0, "rake_lf": 0,
                          "porch_width_ft": 16.5, "porch_depth_ft": 6}],
    })
    assert g["basis"] == "porch_plane"
    assert g["perimeter_lf"] == 45.0
    assert g["wall_lf"] == 16.5
    assert "printed porch dims" in g["text"]
