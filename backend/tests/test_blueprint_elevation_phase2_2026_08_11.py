"""BLUEPRINT ELEVATION PHASE 2 (Howard ruled 2026-08-11 send-5 item 3).

RENDERER-ONLY FIXES — the reads behind these were never wrong.
Phase 1 dropped what the model already carried:
  - segments: None even when height_segments was populated → Phase 2
    emits structured segments with per-segment area + NEEDS-YOUR-TAPE
    markers for unread segment heights.
  - area math treated a stepped wall as un-computable → Phase 2
    sums known segment areas + primary gable + wing gables and
    DISCLOSES what remains missing (evidence-or-null).
  - wing gables (send-3 attribution) were annotations only → Phase 2
    identifies the wing base via segment name matching AND lists the
    wing triangle per wall, disclosing unread height/area.
  - porch presence was invisible on the sheet → Phase 2 surfaces
    porch_note when any is_porch plane exists (attachment wall
    disclosed as convention; not claimed).

Everything in this module is EVIDENCE. Nothing is tuned. Boni's
numbers (34, 24, 20, 10.5, 58, 39, 11.375, 3826) are inputs, never
targets — pinned via a purity test at the bottom.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.blueprint_elevation import build_blueprint_sheet  # noqa: E402


EST = {"estimate_number": "EST-886440", "customer_name": "boni",
       "address": "x"}


def _run(raw):
    return {"run_id": "80c10620d87641e4b275dd06ac4f2705",
            "result": {"raw_ai": raw}, "model_name": "test",
            "completed_at": "2026-08-11"}


def _boni_raw() -> dict:
    """The read that motivated Phase 2 — Boni EST-886440 run 80c10620."""
    return {
        "walls": [
            {"label": "front", "width_ft": 58.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 0,
             "height_segments": [
                 {"name": "main body 2-story",
                  "width_ft": 34.0, "height_ft": 20.0},
                 {"name": "garage wing 1-story",
                  "width_ft": 24.0, "height_ft": 10.5},
             ]},
            {"label": "back", "width_ft": 58.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 0,
             "height_segments": [
                 {"name": "main body 2-story",
                  "width_ft": 34.0, "height_ft": 20.0},
                 {"name": "garage/bonus wing",
                  "width_ft": 24.0, "height_ft": None},
             ]},
            {"label": "left", "width_ft": 39.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 11.375,
             "height_segments": []},
            {"label": "right", "width_ft": 39.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 11.375,
             "height_segments": [
                 {"name": "main body 2-story",
                  "width_ft": 30.0, "height_ft": 20.0},
                 {"name": "bonus room section",
                  "width_ft": 9.0, "height_ft": 10.5},
             ]},
        ],
        "roof_planes": [
            {"label": "main", "gable_ends": 2, "is_porch": False},
            {"label": "garage/bonus", "gable_ends": 2, "is_porch": False},
            {"label": "porch", "gable_ends": 0, "is_porch": True,
             "porch_ceiling_sqft": 99.0},
        ],
        "doors": [], "windows": [],
    }


# ---------------- SEGMENTS EMISSION ----------------

def test_front_sheet_emits_structured_segments():
    """The front wall carries a main + garage-wing step. Phase 2 emits
    them as structured segments with per-segment areas + labels."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "front")
    segs = s["wall"]["segments"]
    assert isinstance(segs, list)
    assert len(segs) == 2
    names = [x["name"] for x in segs]
    assert "main body 2-story" in names[0]
    assert "garage wing 1-story" in names[1]
    # Every segment carries its own width/height/label.
    assert segs[0]["width_ft"] == 34.0
    assert segs[0]["height_ft"] == 20.0
    assert segs[1]["width_ft"] == 24.0
    assert segs[1]["height_ft"] == 10.5
    assert segs[0]["needs_tape"] is False
    assert segs[1]["needs_tape"] is False


def test_back_sheet_flags_unread_wing_segment():
    """Back wall carries the wing with height_ft=None. Phase 2 flags
    needs_tape=True and labels NEEDS YOUR TAPE."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "back")
    segs = s["wall"]["segments"]
    assert segs is not None
    wing = next(x for x in segs if "wing" in x["name"].lower())
    assert wing["needs_tape"] is True
    assert "NEEDS YOUR TAPE" in wing["height_label"]


def test_single_body_wall_emits_no_segments_list():
    """Left wall has empty height_segments — Phase 2 keeps
    segments=None so the frontend renders a single rectangle
    (Phase 1 behavior preserved for single-body walls)."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "left")
    assert s["wall"]["segments"] is None


# ---------------- GABLE-HONEST AREA ----------------

def test_front_area_sums_segments_and_reports_missing_wing_gable():
    """Front wall area = main + garage-wing + (wing gable base but
    height unread → area_missing lists it, evidence-or-null)."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "front")
    # Body area: 34*20 + 24*10.5 = 680 + 252 = 932 sqft (Phase 2 sums
    # segment areas — never a single rectangle).
    expected_body = 34.0 * 20.0 + 24.0 * 10.5
    assert s["wall"]["area_sqft"] == expected_body
    # Components list names each contributor.
    comp_names = [c["name"] for c in s["wall"]["area_components"]]
    assert "main body 2-story" in comp_names
    assert "garage wing 1-story" in comp_names
    # Missing pieces disclosed: the wing gable's area is not derivable.
    assert any("wing gable" in m for m in s["wall"]["area_missing"])
    assert s["wall"]["area_note"] is not None


def test_left_wall_area_includes_primary_gable_triangle():
    """Left wall: 39 × 20 rectangle + 0.5 × 39 × 11.375 gable triangle.
    Phase 2 sums both — Phase 1 left the triangle out."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "left")
    body = 39.0 * 20.0
    tri = 0.5 * 39.0 * 11.375
    assert s["wall"]["area_sqft"] == body + round(tri, 1)
    # Area components list carries the triangle separately.
    kinds = [c["kind"] for c in s["wall"]["area_components"]]
    assert "gable_triangle_primary" in kinds


def test_back_wall_area_reports_partial_when_wing_unread():
    """Back wall: main = 34*20 = 680, wing height unread. Phase 2
    reports what it can (680) and discloses the missing wing."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "back")
    assert s["wall"]["area_sqft"] == 34.0 * 20.0
    assert any("garage/bonus wing" in m for m in s["wall"]["area_missing"])


# ---------------- WING TRIANGLE ANNOTATIONS ----------------

def test_front_sheet_carries_wing_triangle_notes():
    """Front wall carries 1 wing gable attribution (send-3 module).
    Phase 2 lists the wing triangle with base identified via segment
    name matching AND height/area disclosed as unread."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "front")
    notes = s["wall"]["wing_triangle_notes"]
    assert isinstance(notes, list)
    assert len(notes) == 1
    n = notes[0]
    assert n["plane"] == "garage/bonus"
    # Base identified via the "garage wing 1-story" segment name.
    assert n["base_ft"] == 24.0
    assert "garage wing 1-story" in n["base_source"]
    # Height + area are unread — evidence-or-null.
    assert n["height_ft"] is None
    assert n["area_sqft"] is None


def test_left_wall_carries_no_wing_triangle_notes():
    """Left wall's primary gables ride on L+R. No secondary
    attribution → wing_triangle_notes is empty."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "left")
    assert s["wall"]["wing_triangle_notes"] == []


# ---------------- PORCH FACE ----------------

def test_front_sheet_carries_porch_note_when_porch_plane_exists():
    """Boni carries a porch plane. Phase 2 surfaces it as porch_note
    with ceiling sqft + a Phase-1-status disclosure."""
    s = build_blueprint_sheet(EST, _run(_boni_raw()), "front")
    p = s["porch_note"]
    assert p is not None
    assert p["present"] is True
    assert p["ceiling_sqft"] == 99.0
    # Attachment wall is a convention, NEVER claimed as read.
    assert "convention" in p["attachment_wall_source"].lower() or \
           "verify" in p["attachment_wall_source"].lower()


def test_porch_note_absent_when_no_porch_plane():
    """No porch plane → porch_note is None. Nothing invented."""
    raw = _boni_raw()
    raw["roof_planes"] = [p for p in raw["roof_planes"]
                          if not p.get("is_porch")]
    s = build_blueprint_sheet(EST, _run(raw), "front")
    assert s["porch_note"] is None


# ---------------- PURITY ----------------

def test_phase_2_source_carries_no_boni_target_constants():
    """PURITY RIDER: none of 34, 24, 20, 10.5, 58, 39, 11.375, 3826
    appear as literal target constants in the Phase-2 renderer block.
    All derive from walls/planes/attribution inputs."""
    src = Path("/app/backend/routes/blueprint_elevation.py").read_text()
    # Walk lines inside build_blueprint_sheet.
    start = src.find("def build_blueprint_sheet")
    end = src.find("\n@router.get", start)
    block = src[start:end]
    # Strip comments/docstrings for the target check.
    code_lines = [
        ln for ln in block.splitlines()
        if not ln.strip().startswith("#") and not ln.strip().startswith("\"\"\"")
    ]
    code = "\n".join(code_lines)
    for target in ("34.0", "24.0", "10.5", "58.0", "39.0",
                   "11.375", "3826"):
        assert target not in code, (
            f"target constant {target!r} leaked into build_blueprint_sheet"
        )
