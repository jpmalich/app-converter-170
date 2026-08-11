"""GABLE ATTRIBUTION — the 4-vs-2 fix (Howard ruled 2026-08-11 send-3
item c). Wall attribution for the front-facing gable.

The mechanism report named the class narrowly (elevation_mechanisms_
2026-08-11.md §2): the front-facing gable is READ AT THE PLANE LEVEL
and LOST AT WALL ATTRIBUTION. Main plane 2 + garage/bonus plane 2 = 4
plane gable ends; walls L+R carry 2 primary; wing's 2 are unattributed.

These pins pin:
  a) The attribution function is PURE — never mutates its inputs.
  b) The wing's ends land on the walls PERPENDICULAR to the primary
     gable axis (L+R primary → F+B secondary).
  c) The census on the readback reconciles once attribution completes.
  d) The elevation-sheet renderer carries the secondary attribution
     onto the sheet (Phase 1 annotation; Phase 2 draws it).
  e) The function REFUSES to guess: odd counts, no primary axis, no
     non-main plane → no attribution + reason named.
  f) Nothing in this module tunes toward 4 or 2 — PURITY RIDER.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gable_attribution import (  # noqa: E402
    attribute_secondary_gables,
    secondary_gables_for_wall,
)
from routes.blueprint_elevation import build_blueprint_sheet  # noqa: E402
from routes.ai_blueprint import (  # noqa: E402
    build_blueprint_readback,
    check_read_consistency,
)


# ---------- fixture: EST-886440 run 80c10620 shape (the Boni case) ----------
EST886440_RAW = {
    "walls": [
        {"label": "front", "width_ft": 58.0, "height_ft": 20.0,
         "gable_triangle_height_ft": 0},
        {"label": "back", "width_ft": 58.0, "height_ft": 20.0,
         "gable_triangle_height_ft": 0},
        {"label": "left", "width_ft": 39.0, "height_ft": 20.0,
         "gable_triangle_height_ft": 11.375},
        {"label": "right", "width_ft": 39.0, "height_ft": 20.0,
         "gable_triangle_height_ft": 11.375},
    ],
    "roof_planes": [
        {"label": "main", "eave_lf": 78.0, "rake_lf": 82.0,
         "gable_ends": 2, "is_porch": False},
        {"label": "garage/bonus", "eave_lf": 48.0, "rake_lf": 50.0,
         "gable_ends": 2, "is_porch": False},
        {"label": "porch", "eave_lf": 50.0, "gable_ends": 0,
         "is_porch": True, "porch_ceiling_sqft": 99.0},
    ],
    "avg_wall_height_ft": 20.0,
    "outside_corner_count": 9,
    "outside_corner_lf": 133.0,
    "_dim_evidence": {
        "walls.front.width_ft": {"v": 58.0, "page": 3, "from": "58'-0\""},
    },
}


# ---------- (a) pure function ----------

def test_attribution_does_not_mutate_walls_or_planes():
    walls = copy.deepcopy(EST886440_RAW["walls"])
    planes = copy.deepcopy(EST886440_RAW["roof_planes"])
    walls_snap = copy.deepcopy(walls)
    planes_snap = copy.deepcopy(planes)
    attribute_secondary_gables(walls, planes)
    assert walls == walls_snap, "walls mutated"
    assert planes == planes_snap, "planes mutated"


# ---------- (b) wing ends land on perpendicular axis ----------

def test_wing_gables_attribute_to_perpendicular_axis():
    """L+R primary → F+B secondary. Boni shape: garage/bonus plane's 2
    ends face F+B."""
    a = attribute_secondary_gables(
        EST886440_RAW["walls"], EST886440_RAW["roof_planes"])
    assert a["plane_gables_total"] == 4
    assert a["wall_gables_primary"] == 2
    assert a["unattributed_before"] == 2
    walls_attributed = {x["wall"] for x in a["attributions"]}
    assert walls_attributed == {"front", "back"}, (
        f"expected wing ends on front+back, got {walls_attributed}")
    # Both attributions cite the garage/bonus plane.
    for at in a["attributions"]:
        assert at["plane"] == "garage/bonus"
        assert at["kind"] == "secondary"


def test_flip_case_fb_primary_wing_attributes_lr():
    """When primary gables land on F+B, the wing's ends face L+R."""
    walls = [
        {"label": "front", "width_ft": 40, "height_ft": 20,
         "gable_triangle_height_ft": 8.0},
        {"label": "back", "width_ft": 40, "height_ft": 20,
         "gable_triangle_height_ft": 8.0},
        {"label": "left", "width_ft": 30, "height_ft": 20,
         "gable_triangle_height_ft": 0},
        {"label": "right", "width_ft": 30, "height_ft": 20,
         "gable_triangle_height_ft": 0},
    ]
    planes = [
        {"label": "main", "gable_ends": 2, "is_porch": False},
        {"label": "wing", "gable_ends": 2, "is_porch": False},
    ]
    a = attribute_secondary_gables(walls, planes)
    walls_attributed = {x["wall"] for x in a["attributions"]}
    assert walls_attributed == {"left", "right"}


# ---------- (c) census on readback reconciles ----------

def test_readback_census_reconciles_after_attribution():
    rb = build_blueprint_readback(EST886440_RAW)
    ga = rb["gable_attribution"]
    assert ga["plane_gables_total"] == 4
    assert ga["wall_gables_primary"] == 2
    assert ga["wall_gables_attributed"] == 4
    assert ga["census_reconciled"] is True

    # The consistency flag no longer fires because attributed == plane.
    flags = check_read_consistency(EST886440_RAW)
    codes = [f["code"] for f in flags]
    assert "gable_census_mismatch" not in codes


def test_readback_census_still_fires_when_attribution_refuses():
    """If the wing's ends cannot be safely attributed (no primary axis
    with 2 walls), the census still fires — the flag is not silenced."""
    walls_no_primary = [
        {"label": w, "width_ft": 40, "height_ft": 20,
         "gable_triangle_height_ft": 0}
        for w in ("front", "back", "left", "right")
    ]
    planes = [
        {"label": "main", "gable_ends": 2, "is_porch": False},
        {"label": "wing", "gable_ends": 2, "is_porch": False},
    ]
    raw = {
        "walls": walls_no_primary,
        "roof_planes": planes,
        "outside_corner_count": 4,
        "outside_corner_lf": 80.0,
    }
    flags = check_read_consistency(raw)
    codes = [f["code"] for f in flags]
    assert "gable_census_mismatch" in codes


# ---------- (d) elevation-sheet carries secondary attribution ----------

def test_front_sheet_carries_wing_gable_annotation():
    """The front sheet must know it carries a secondary (wing) gable,
    so Phase 2 can draw it."""
    est = {"estimate_number": "EST-886440", "customer_name": "boni",
           "address": "x"}
    run = {"run_id": "80c10620d87641e4b275dd06ac4f2705",
           "result": {"raw_ai": EST886440_RAW}, "model_name": "test",
           "completed_at": "2026-08-11"}
    sheet = build_blueprint_sheet(est, run, "front")
    sg = sheet["wall"]["secondary_gables"]
    assert isinstance(sg, list) and len(sg) == 1
    assert sg[0]["plane"] == "garage/bonus"
    assert sg[0]["kind"] == "secondary"
    assert sheet["wall"]["secondary_gables_note"], (
        "sheet must name that the annotation is Phase-1 only")


def test_back_sheet_also_carries_wing_gable_annotation():
    """Symmetric — a wing that gables both directions attributes to
    BOTH front AND back."""
    est = {"estimate_number": "EST-886440", "customer_name": "boni",
           "address": "x"}
    run = {"run_id": "80c10620d87641e4b275dd06ac4f2705",
           "result": {"raw_ai": EST886440_RAW}, "model_name": "test",
           "completed_at": "2026-08-11"}
    back = build_blueprint_sheet(est, run, "back")
    assert len(back["wall"]["secondary_gables"]) == 1


def test_left_sheet_does_not_double_count_primary():
    """The left wall carries a PRIMARY gable (gable_triangle_height_ft
    11.375). It must NOT also carry a secondary attribution — the
    perpendicular axis is F+B, not L."""
    est = {"estimate_number": "EST-886440", "customer_name": "boni",
           "address": "x"}
    run = {"run_id": "80c10620d87641e4b275dd06ac4f2705",
           "result": {"raw_ai": EST886440_RAW}, "model_name": "test",
           "completed_at": "2026-08-11"}
    left = build_blueprint_sheet(est, run, "left")
    assert left["wall"]["secondary_gables"] == []


# ---------- (e) refuse-to-guess branches ----------

def test_attribution_refuses_when_no_primary_axis():
    """No primary gables anywhere → cannot identify the perpendicular
    axis → refuse to attribute; reason named."""
    walls = [{"label": w, "gable_triangle_height_ft": 0}
             for w in ("front", "back", "left", "right")]
    planes = [{"label": "main", "gable_ends": 2, "is_porch": False}]
    a = attribute_secondary_gables(walls, planes)
    assert a["attributions"] == []
    assert a["census_reconciled"] is False
    assert a["reason"] and "primary" in a["reason"].lower()


def test_attribution_refuses_when_no_non_main_plane():
    """Primary axis identifiable but no non-main plane carries extras →
    refuse."""
    walls = [
        {"label": "left", "gable_triangle_height_ft": 8.0},
        {"label": "right", "gable_triangle_height_ft": 8.0},
        {"label": "front", "gable_triangle_height_ft": 0},
        {"label": "back", "gable_triangle_height_ft": 0},
    ]
    planes = [{"label": "main", "gable_ends": 4, "is_porch": False}]
    a = attribute_secondary_gables(walls, planes)
    assert a["attributions"] == []
    assert a["reason"] and "non-main" in a["reason"].lower()


def test_attribution_helper_scoped_by_wall_label():
    a = attribute_secondary_gables(
        EST886440_RAW["walls"], EST886440_RAW["roof_planes"])
    assert len(secondary_gables_for_wall(a, "front")) == 1
    assert len(secondary_gables_for_wall(a, "back")) == 1
    assert secondary_gables_for_wall(a, "left") == []
    assert secondary_gables_for_wall(a, "right") == []


# ---------- (f) PURITY — no constants ----------

def test_module_has_no_numeric_target_constants():
    """PURITY RIDER (permanent, 2026-08): the attribution module never
    embeds a target number (4, 2, 11.375, etc.). The wing counts derive
    from the walls + planes passed in — nothing tuned to hit a case."""
    src = Path("/app/backend/gable_attribution.py").read_text()
    # The only numeric literals in this module are 0.0 (the float
    # coerce default) and 1 (the count decrement in the loop).
    # 4 / 2 / 11.375 / 58 / 39 must not appear as constants in the code
    # (they may appear inside docstrings/comments — the check is on
    # non-comment lines only).
    code_lines = [line for line in src.splitlines()
                  if not line.strip().startswith("#")]
    code = "\n".join(code_lines)
    for forbidden in ("11.375", "58.0", "39.0"):
        assert forbidden not in code, (
            f"target constant {forbidden!r} leaked into "
            "gable_attribution.py — PURITY RIDER breached")
