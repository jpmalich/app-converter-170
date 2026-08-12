"""GABLE ATTRIBUTION — the 4-vs-2 fix (Howard ruled 2026-08-11 send-3
item c) HARDENED (Howard ruled 2026-08-11 send-6 item 1).

Send-3 mechanism: the front-facing gable is READ AT THE PLANE LEVEL and
LOST AT WALL ATTRIBUTION. Main plane 2 + garage/bonus plane 2 = 4 plane
gable ends; walls L+R carry 2 primary; wing's 2 are unattributed.

Send-6 ruling (verbatim): "AN ORPHAN GABLE END IS NEVER DISTRIBUTED ONTO
AN UNRELATED [wall]. It FLAGS and stays unattributed, loud, on the card
and on the sheet." The perpendicular-axis heuristic is RETIRED; the
attribution now requires each plane to emit `gable_end_faces` naming
which elevation each triangle points at. No evidence → orphan → flag.

These pins pin:
  a) The attribution function is PURE — never mutates its inputs.
  b) With `gable_end_faces` evidence, ends land on the named walls.
  c) The census on the readback reconciles once attribution completes.
  d) The elevation-sheet renderer carries the secondary attribution
     AND the orphan disclosure onto the sheet.
  e) The function REFUSES to guess: absent/mismatched faces → orphan.
  f) Nothing in this module tunes toward 4 or 2 — PURITY RIDER.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gable_attribution import (  # noqa: E402
    attribute_secondary_gables,
    orphan_gables,
    secondary_gables_for_wall,
)
from routes.blueprint_elevation import build_blueprint_sheet  # noqa: E402
from routes.ai_blueprint import (  # noqa: E402
    build_blueprint_readback,
    check_read_consistency,
)


# ---------- fixture: EST-886440 run 80c10620 shape (the Boni case) ----------
# POST-SEND-6: the extraction fix is expected to emit `gable_end_faces`
# for every plane with gable_ends > 0. Boni's garage/bonus wing fires
# to F+B (evidenced), so the fixture carries that explicit list.
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
         "gable_ends": 2, "gable_end_faces": ["left", "right"],
         "is_porch": False},
        {"label": "garage/bonus", "eave_lf": 48.0, "rake_lf": 50.0,
         "gable_ends": 2, "gable_end_faces": ["front", "back"],
         "is_porch": False},
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


# ---------- (b) evidence-driven attribution ----------

def test_wing_gables_attribute_per_gable_end_faces():
    """Boni shape: garage/bonus plane emits gable_end_faces
    ['front','back'] — the two ends land on front + back exactly, one
    each, per the plane's own evidence."""
    a = attribute_secondary_gables(
        EST886440_RAW["walls"], EST886440_RAW["roof_planes"])
    assert a["plane_gables_total"] == 4
    assert a["wall_gables_primary"] == 2
    assert a["unattributed_before"] == 2
    walls_attributed = [x["wall"] for x in a["attributions"]]
    assert sorted(walls_attributed) == ["back", "front"], (
        f"expected wing ends on front+back, got {walls_attributed}")
    for at in a["attributions"]:
        assert at["plane"] == "garage/bonus"
        assert at["kind"] == "secondary"
    assert a["orphans"] == []


def test_flip_case_fb_primary_wing_attributes_lr_via_faces():
    """When the extraction emits gable_end_faces ['left','right'] on
    the wing, its two ends land on left + right — evidence, not axis."""
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
        {"label": "main", "gable_ends": 2,
         "gable_end_faces": ["front", "back"], "is_porch": False},
        {"label": "wing", "gable_ends": 2,
         "gable_end_faces": ["left", "right"], "is_porch": False},
    ]
    a = attribute_secondary_gables(walls, planes)
    walls_attributed = {x["wall"] for x in a["attributions"]}
    assert walls_attributed == {"left", "right"}


def test_entry_plane_landing_on_one_face():
    """SEND-6 CANONICAL CASE: an entry gable emitted as its own plane
    with gable_ends=1 and gable_end_faces=['front'] lands on FRONT only
    — never split across the perpendicular pair."""
    walls = [
        {"label": "front", "gable_triangle_height_ft": 0},
        {"label": "back", "gable_triangle_height_ft": 0},
        {"label": "left", "gable_triangle_height_ft": 8.0},
        {"label": "right", "gable_triangle_height_ft": 8.0},
    ]
    planes = [
        {"label": "main", "gable_ends": 2,
         "gable_end_faces": ["left", "right"], "is_porch": False},
        {"label": "entry", "gable_ends": 1,
         "gable_end_faces": ["front"], "is_porch": False},
    ]
    a = attribute_secondary_gables(walls, planes)
    assert len(a["attributions"]) == 1
    assert a["attributions"][0]["wall"] == "front"
    assert a["attributions"][0]["plane"] == "entry"
    assert a["orphans"] == []
    assert a["census_reconciled"] is True


# ---------- (c) census on readback reconciles ----------

def test_readback_census_reconciles_after_attribution():
    rb = build_blueprint_readback(EST886440_RAW)
    ga = rb["gable_attribution"]
    assert ga["plane_gables_total"] == 4
    assert ga["wall_gables_primary"] == 2
    assert ga["wall_gables_attributed"] == 4
    assert ga["census_reconciled"] is True

    flags = check_read_consistency(EST886440_RAW)
    codes = [f["code"] for f in flags]
    assert "gable_census_mismatch" not in codes


def test_readback_census_still_fires_when_attribution_refuses():
    """A wing plane with no gable_end_faces evidence: the ends are
    ORPHANS, the census fires loud, and the flag names the plane."""
    walls_no_primary = [
        {"label": w, "width_ft": 40, "height_ft": 20,
         "gable_triangle_height_ft": 0}
        for w in ("front", "back", "left", "right")
    ]
    planes = [
        {"label": "main", "gable_ends": 2,
         "gable_end_faces": ["left", "right"], "is_porch": False},
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
    m = next(f for f in flags if f["code"] == "gable_census_mismatch")
    assert m["vars"].get("orphans") == 2
    assert "wing" in m["vars"].get("orphan_planes", "")


# ---------- (d) elevation-sheet carries secondary attribution + orphans ----------

def _boni_sheet(which: str) -> dict:
    est = {"estimate_number": "EST-886440", "customer_name": "boni",
           "address": "x"}
    run = {"run_id": "80c10620d87641e4b275dd06ac4f2705",
           "result": {"raw_ai": EST886440_RAW}, "model_name": "test",
           "completed_at": "2026-08-11"}
    return build_blueprint_sheet(est, run, which)


def test_front_sheet_carries_wing_gable_annotation():
    sheet = _boni_sheet("front")
    sg = sheet["wall"]["secondary_gables"]
    assert isinstance(sg, list) and len(sg) == 1
    assert sg[0]["plane"] == "garage/bonus"
    assert sg[0]["kind"] == "secondary"
    assert sheet["wall"]["secondary_gables_note"]
    # No orphans on this fixture — the plane emitted its faces.
    assert sheet["wall"]["orphan_gables"] == []
    assert sheet["wall"]["orphan_note"] is None


def test_back_sheet_also_carries_wing_gable_annotation():
    back = _boni_sheet("back")
    assert len(back["wall"]["secondary_gables"]) == 1


def test_left_sheet_does_not_double_count_primary():
    left = _boni_sheet("left")
    assert left["wall"]["secondary_gables"] == []


def test_orphan_gable_surfaces_on_every_sheet():
    """SEND-6: an orphan gable (no gable_end_faces evidence) is LOUD on
    every sheet — the miss is visible, never silently misfiled."""
    raw = copy.deepcopy(EST886440_RAW)
    # Retract the evidence on the garage/bonus plane — this simulates
    # a read that DID count 4 gable ends at the plane level but did
    # not identify which wall each end faces.
    for p in raw["roof_planes"]:
        if p.get("label") == "garage/bonus":
            del p["gable_end_faces"]
    est = {"estimate_number": "EST-886440", "customer_name": "boni",
           "address": "x"}
    run = {"run_id": "orphan-case", "result": {"raw_ai": raw},
           "model_name": "test", "completed_at": "2026-08-11"}
    for which in ("front", "back", "left", "right"):
        sheet = build_blueprint_sheet(est, run, which)
        assert sheet["wall"]["orphan_gables"], (
            f"orphan not surfaced on {which} sheet")
        assert "UNATTRIBUTED WING GABLE" in (
            sheet["wall"]["orphan_note"] or "")
        # The wing must NOT silently land on this sheet's wall.
        assert sheet["wall"]["secondary_gables"] == []


# ---------- (e) refuse-to-guess branches ----------

def test_attribution_refuses_when_no_faces_on_wing():
    """Wing plane with gable_ends > 0 but no gable_end_faces evidence
    → all ends orphan → attributions empty."""
    walls = [
        {"label": "left", "gable_triangle_height_ft": 8.0},
        {"label": "right", "gable_triangle_height_ft": 8.0},
        {"label": "front", "gable_triangle_height_ft": 0},
        {"label": "back", "gable_triangle_height_ft": 0},
    ]
    planes = [
        {"label": "main", "gable_ends": 2,
         "gable_end_faces": ["left", "right"], "is_porch": False},
        {"label": "garage", "gable_ends": 2, "is_porch": False},
    ]
    a = attribute_secondary_gables(walls, planes)
    assert a["attributions"] == []
    assert a["orphans"] and a["orphans"][0]["plane"] == "garage"
    assert a["orphans"][0]["count"] == 2
    assert a["census_reconciled"] is False
    assert a["reason"] and "orphan" in a["reason"].lower()


def test_attribution_refuses_when_faces_count_mismatch():
    """gable_end_faces length != gable_ends → orphan, never partial."""
    walls = [
        {"label": "left", "gable_triangle_height_ft": 8.0},
        {"label": "right", "gable_triangle_height_ft": 8.0},
        {"label": "front", "gable_triangle_height_ft": 0},
        {"label": "back", "gable_triangle_height_ft": 0},
    ]
    planes = [
        {"label": "main", "gable_ends": 2,
         "gable_end_faces": ["left", "right"], "is_porch": False},
        {"label": "wing", "gable_ends": 2,
         "gable_end_faces": ["front"], "is_porch": False},  # length 1 ≠ 2
    ]
    a = attribute_secondary_gables(walls, planes)
    assert a["attributions"] == []
    assert a["orphans"] and "length 1" in a["orphans"][0]["reason"]


def test_attribution_helper_scoped_by_wall_label():
    a = attribute_secondary_gables(
        EST886440_RAW["walls"], EST886440_RAW["roof_planes"])
    assert len(secondary_gables_for_wall(a, "front")) == 1
    assert len(secondary_gables_for_wall(a, "back")) == 1
    assert secondary_gables_for_wall(a, "left") == []
    assert secondary_gables_for_wall(a, "right") == []


def test_orphan_helper_returns_list():
    """The renderer walks orphans via this helper — the shape it
    reads is stable."""
    raw_no_ev = copy.deepcopy(EST886440_RAW)
    for p in raw_no_ev["roof_planes"]:
        if p.get("label") == "garage/bonus":
            del p["gable_end_faces"]
    a = attribute_secondary_gables(
        raw_no_ev["walls"], raw_no_ev["roof_planes"])
    orphans = orphan_gables(a)
    assert isinstance(orphans, list) and len(orphans) == 1
    assert orphans[0]["plane"] == "garage/bonus"


# ---------- (f) PURITY — no constants ----------

def test_module_has_no_numeric_target_constants():
    """PURITY RIDER (permanent, 2026-08): the attribution module never
    embeds a target number (4, 2, 11.375, etc.). The wing counts derive
    from the walls + planes passed in — nothing tuned to hit a case."""
    src = Path("/app/backend/gable_attribution.py").read_text()
    code_lines = [line for line in src.splitlines()
                  if not line.strip().startswith("#")]
    code = "\n".join(code_lines)
    for forbidden in ("11.375", "58.0", "39.0"):
        assert forbidden not in code, (
            f"target constant {forbidden!r} leaked into "
            "gable_attribution.py — PURITY RIDER breached")
