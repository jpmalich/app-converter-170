"""Iter 79j.71 — Shake quantity composition audit fixes.

Pins the EXACT 584.3 ft² decomposition from run f423c216 (2026-07-08
11:56) that billed dormer faces up to 3× and the contractor's annotation
boxes 2×, and asserts the single-owner composition rules:

  1. apply_roof_type_material_math never re-adds a reconciler-filled face
     (face owner: reconciler > geometry; cheeks always geometry-owned).
  2. Claude accent echoes of contractor boxes (from_annotation / ground-
     truth phrasing) are skipped — the annotation overlay is sole owner.
  3. Annotation boxes located on dormer/gable OVERRIDE that surface's
     profile (no added ft²); "body" boxes move area between families
     (accent added + wall body deducted).
  4. Malformed (string) accents skip with a counter instead of crashing
     the whole breakdown (the run-4 `_per_profile_sqft: {}` regression).
  5. Composition tripwire: conflicted families are amber-flagged by the
     catalog mapper (qty 0 + warning note) instead of printing a number.
"""
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from profile_callouts import (  # noqa: E402
    apply_annotations_to_breakdown,
    breakdown_walls_by_profile,
)
from routes.ai_measure import apply_roof_type_material_math  # noqa: E402
from routes.hover import _profile_siding_lines  # noqa: E402


# ───────────────────────── run f423c216 fixture ─────────────────────────
# Reconciler walls BEFORE apply_roof_type_material_math (dormer faces are
# the reconciler's own reads: left 62.0 = 15.5×4.0, right 74.25 = 16.5×4.5).
def _f423_walls():
    return [
        {"label": "front", "width_ft": 27.0, "height_ft": 8.5,
         "gable_triangle_height_ft": 9.0, "dormer_face_sqft": 0,
         "wall_body_profile_callout": 'lap 4"', "gable_profile_callout": 'lap 4"',
         "dormer_profile_callout": "", "siding_pct_this_wall": 100, "accent_profiles": []},
        {"label": "back", "width_ft": 27.0, "height_ft": 9.3,
         "gable_triangle_height_ft": 8.5, "dormer_face_sqft": 0,
         "wall_body_profile_callout": 'lap 4"', "gable_profile_callout": 'lap 4"',
         "dormer_profile_callout": "", "siding_pct_this_wall": 88, "accent_profiles": []},
        {"label": "left", "width_ft": 37.0, "height_ft": 9.0,
         "gable_triangle_height_ft": 0, "dormer_face_sqft": 62.0,
         "wall_body_profile_callout": 'lap 4"', "gable_profile_callout": "",
         "dormer_profile_callout": "shake", "siding_pct_this_wall": 98,
         "accent_profiles": [
             {"location": "shed dormer face (contractor ground truth, photo 2)",
              "profile_callout": "shake", "approx_sqft": 49},
             {"location": "front-left upper set-back section (contractor ground truth, photo 1)",
              "profile_callout": "shake", "approx_sqft": 11},
         ]},
        {"label": "right", "width_ft": 37.0, "height_ft": 8.5,
         "gable_triangle_height_ft": 0, "dormer_face_sqft": 74.25,
         "wall_body_profile_callout": 'lap 4"', "gable_profile_callout": "",
         "dormer_profile_callout": "shake", "siding_pct_this_wall": 100,
         "accent_profiles": [
             {"location": "right elevation contractor-tagged region (ground truth, photo 6)",
              "profile_callout": "shake", "approx_sqft": 57},
             {"location": "front-right upper band (contractor ground truth, photo 7)",
              "profile_callout": "shake", "approx_sqft": 16},
             {"location": "rear-right accent (contractor ground truth, photo 5)",
              "profile_callout": "shake", "approx_sqft": 14},
         ]},
    ]


def _f423_raw(walls):
    return {
        "roof_type": "gable-shed-dormer",
        "roof_type_confidence": 0.9,
        "dormers": [
            {"face": "left", "width_ft": 15.5, "knee_wall_height_ft": 4.0},
            {"face": "right", "width_ft": 16.5, "knee_wall_height_ft": 4.5},
        ],
        "openings": [
            {"type": "window", "width_in": 44, "height_in": 36, "wall": "left", "on_dormer": True},
            {"type": "window", "width_in": 43, "height_in": 36, "wall": "left", "on_dormer": True},
            {"type": "window", "width_in": 46, "height_in": 36, "wall": "right", "on_dormer": True},
        ],
        "walls": walls,
    }


# The 6 annotation boxes as they were at the time of the run.
def _f423_annotations():
    return {
        "1": [{"elevation_label": "left", "profile": "shake", "sqft": 48.9, "location": "body"}],
        "2": [{"elevation_label": "right", "profile": "shake", "sqft": 57.0, "location": "body"}],
        "3": [{"elevation_label": "front-left", "profile": "shake", "sqft": 11.3, "location": "body"}],
        "4": [{"elevation_label": "rear-left", "profile": "shake", "sqft": 15.5, "location": "body"}],
        "5": [{"elevation_label": "rear-right", "profile": "shake", "sqft": 13.7, "location": "body"}],
        "6": [{"elevation_label": "front-right", "profile": "shake", "sqft": 15.7, "location": "body"}],
    }


def _run_f423_pipeline():
    walls = _f423_walls()
    raw = _f423_raw(walls)
    apply_roof_type_material_math(raw, walls, gable_sqft=236.2, dormer_sqft=136.25)
    breakdown = breakdown_walls_by_profile(walls)
    return apply_annotations_to_breakdown(breakdown, _f423_annotations())


# ─────────────── 1. geometry: reconciler face never re-added ───────────────
def test_reconciler_filled_face_not_double_added():
    walls = _f423_walls()
    raw = _f423_raw(walls)
    apply_roof_type_material_math(raw, walls, 236.2, 136.25)
    left = next(w for w in walls if w["label"] == "left")
    right = next(w for w in walls if w["label"] == "right")
    # left: face 62 (reconciler) − openings 21.75 + cheeks 16 = 56.25
    assert left["dormer_face_sqft"] == pytest.approx(56.25, abs=0.1)
    assert left["_dormer_composition"]["face_owner"] == "reconciler"
    # right: face 74.25 − opening 11.5 + cheeks 20.25 = 83.0
    assert right["dormer_face_sqft"] == pytest.approx(83.0, abs=0.1)
    # The OLD math carried 118.25 / 157.0 (face counted twice).
    assert left["dormer_face_sqft"] < 118.0
    assert right["dormer_face_sqft"] < 156.0


def test_zero_face_still_filled_by_geometry():
    walls = [{"label": "front", "width_ft": 30, "height_ft": 10,
              "gable_triangle_height_ft": 0, "dormer_face_sqft": 0}]
    raw = {"roof_type": "gable-shed-dormer", "roof_type_confidence": 0.9,
           "dormers": [{"face": "front", "width_ft": 10, "knee_wall_height_ft": 5}],
           "openings": []}
    _, d = apply_roof_type_material_math(raw, walls, 0.0, 0.0)
    assert walls[0]["dormer_face_sqft"] == pytest.approx(75.0, abs=0.1)  # 50 face + 25 cheeks
    assert walls[0]["_dormer_composition"]["face_owner"] == "geometry"
    assert d == pytest.approx(75.0, abs=0.1)


# ─────────────── 2+3. the pinned 584.3 fixture, recomposed ───────────────
def test_f423_shake_no_longer_584():
    """Old composition: 275.2 (double-counted dormers) + 147.0 (Claude
    echoes) + 162.1 (annotation overlay) = 584.3. New composition:
    dormers once (56.25 + 83.0 = 139.25) + annotations once (162.1),
    echoes skipped, body boxes deducted from lap."""
    result = _run_f423_pipeline()
    shake = result["per_profile_sqft"]["shake"]
    assert shake == pytest.approx(139.25 + 162.1, abs=1.0)
    assert shake < 584.3 * 0.6
    # echoes were skipped, not silently dropped
    assert result["skipped_echo_accents"] == 5
    assert result["conflicts"] == []


def test_f423_body_boxes_move_area_out_of_lap():
    result = _run_f423_pipeline()
    by_label = {e["label"]: e for e in result["per_elevation"]}
    # left body was 326.3 (37×9×0.98) → minus the 48.9 box
    assert by_label["left"]["wall_body_sqft"] == pytest.approx(326.3 - 48.9, abs=0.2)
    # right body was 314.5 (37×8.5) → minus the 57.0 box
    assert by_label["right"]["wall_body_sqft"] == pytest.approx(314.5 - 57.0, abs=0.2)


def test_f423_composition_lists_each_surface_once():
    result = _run_f423_pipeline()
    comp = result["composition"]["shake"]
    keys = [(s["elevation"], s["surface"]) for s in comp]
    assert len(keys) == len(set(keys)), f"duplicate surface owners: {keys}"
    # total equals the component sum exactly
    assert result["per_profile_sqft"]["shake"] == pytest.approx(
        sum(s["sqft"] for s in comp), abs=0.5)
    owners = {s["owner"] for s in comp}
    assert owners <= {"geometry", "geometry+user-profile", "annotation", "ai-accent"}
    # the 2 dormer surfaces are geometry-owned, the boxes annotation-owned
    assert sum(1 for s in comp if s["surface"] == "dormer") == 2
    assert sum(1 for s in comp if s["owner"] == "annotation") == 6


def test_dormer_located_box_overrides_profile_not_adds():
    walls = [{"label": "left", "width_ft": 37, "height_ft": 9,
              "gable_triangle_height_ft": 0, "dormer_face_sqft": 56.25,
              "wall_body_profile_callout": 'lap 4"',
              "dormer_profile_callout": "lap", "siding_pct_this_wall": 100,
              "accent_profiles": []},
             {"label": "front", "width_ft": 27, "height_ft": 10,
              "gable_triangle_height_ft": 0, "dormer_face_sqft": 0,
              "wall_body_profile_callout": "shake",
              "siding_pct_this_wall": 100, "accent_profiles": []}]
    breakdown = breakdown_walls_by_profile(walls)
    annotations = {"0": [{"elevation_label": "left", "profile": "shake",
                          "sqft": 40.0, "location": "dormer"}]}
    result = apply_annotations_to_breakdown(breakdown, annotations)
    left = next(e for e in result["per_elevation"] if e["label"] == "left")
    assert left["dormer_profile"] == "shake"          # profile overridden
    assert left["dormer_sqft"] == pytest.approx(56.25, abs=0.1)  # ft² unchanged (geometry owns)
    assert left["accents"] == []                       # no added row
    # shake total = dormer 56.25 + front body 270; the box's 40 ft² was NOT added
    assert result["per_profile_sqft"]["shake"] == pytest.approx(56.25 + 270.0, abs=0.6)


# ─────────────── 4. malformed accents no longer crash ───────────────
def test_string_accents_skip_instead_of_crash():
    """Run-4 regression: Claude emitted accent_profiles as strings →
    the whole breakdown crashed → _per_profile_sqft: {} → zero shake."""
    walls = [{"label": "right", "width_ft": 37, "height_ft": 8.1,
              "gable_triangle_height_ft": 0, "dormer_face_sqft": 163.0,
              "wall_body_profile_callout": 'lap 4"',
              "dormer_profile_callout": 'lap 4"', "siding_pct_this_wall": 100,
              "accent_profiles": [
                  "shake (user-annotated SHAKE ≈ 59 ft² on photo 8; treat as ground truth)",
              ]}]
    breakdown = breakdown_walls_by_profile(walls)
    assert breakdown["malformed_accents"] == 1
    assert breakdown["per_profile_sqft"]["lap"] > 0   # breakdown survived


def test_from_annotation_flag_skips_echo():
    walls = [{"label": "left", "width_ft": 30, "height_ft": 9,
              "gable_triangle_height_ft": 0, "dormer_face_sqft": 0,
              "wall_body_profile_callout": "lap", "siding_pct_this_wall": 100,
              "accent_profiles": [
                  {"location": "upper band", "profile_callout": "shake",
                   "approx_sqft": 50, "from_annotation": True},
                  {"location": "porch face", "profile_callout": "shake",
                   "approx_sqft": 20, "from_annotation": False},
              ]}]
    breakdown = breakdown_walls_by_profile(walls)
    assert breakdown["skipped_echo_accents"] == 1
    assert breakdown["per_profile_sqft"]["shake"] == pytest.approx(20.0)


# ─────────────── 5. tripwire → amber line, not a number ───────────────
def test_dormer_composition_mismatch_flags_conflict():
    walls = [{"label": "left", "width_ft": 37, "height_ft": 9,
              "gable_triangle_height_ft": 0,
              "dormer_face_sqft": 118.25,   # a second writer inflated it
              "_dormer_composition": {"face_owner": "reconciler",
                                      "face_sqft": 62.0, "cheek_sqft": 16.0,
                                      "openings_deducted": 21.75},
              "wall_body_profile_callout": "lap",
              "dormer_profile_callout": "shake", "siding_pct_this_wall": 100,
              "accent_profiles": []}]
    breakdown = breakdown_walls_by_profile(walls)
    assert any(c["family"] == "shake" and "mismatch" in c["reason"]
               for c in breakdown["conflicts"])
    result = apply_annotations_to_breakdown(breakdown, None)
    assert result["conflicts"], "conflicts must survive finalization"


def test_conflicted_family_amber_flagged_in_lines():
    measurements = {
        "_per_profile_sqft": {"lap": 1000.0, "shake": 300.0},
        "_profile_composition_conflicts": [
            {"family": "shake", "reason": "dormer face composition mismatch on 'left'"},
        ],
        "_per_profile_composition": {
            "lap": [{"elevation": "front", "surface": "body", "owner": "geometry", "sqft": 1000.0}],
            "shake": [{"elevation": "left", "surface": "dormer", "owner": "geometry", "sqft": 300.0}],
        },
    }
    lines = _profile_siding_lines(measurements)
    shake_lines = [l for l in lines if "Pelican" in l["name"] or l["name"] == "Shake"]
    assert shake_lines, "conflicted family must still emit a line"
    for l in shake_lines:
        assert l["qty"] == 0
        assert "composition conflict" in l["note"]
        assert "verify" in l["note"]
    # clean families keep their qty + gain a composition note
    lap_lines = [l for l in lines if l["tab"] == "vinyl" and "Dutch Lap" in l["name"]]
    assert lap_lines and lap_lines[0]["qty"] == pytest.approx(10.0)
    assert "front body" in lap_lines[0]["note"]


def test_clean_lines_note_shows_one_owner_per_surface():
    result = _run_f423_pipeline()
    measurements = {
        "_per_profile_sqft": result["per_profile_sqft"],
        "_per_profile_composition": result["composition"],
        "_profile_composition_conflicts": result["conflicts"],
    }
    lines = _profile_siding_lines(measurements)
    shake_vinyl = next(l for l in lines if l["tab"] == "vinyl" and "Pelican" in l["name"])
    assert shake_vinyl["qty"] == pytest.approx((139.25 + 162.1) / 100.0, abs=0.1)
    assert "=" in shake_vinyl["note"]           # composition is itemized
    assert "left dormer" in shake_vinyl["note"]
