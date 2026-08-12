"""SEND-6 WING GABLE MECHANISM + PITCH PER PLANE (Howard ruled
2026-08-11 send-6).

Two rulings, both required:

1. THE READ FIX: EXTRACTION MUST EMIT A PLANE FOR EVERY GABLE END IT
   COUNTS. If the read says four, four planes carry them. The entry
   gable becomes its own plane, with its own rake, soffit, fascia and
   area. The prompt now REQUIRES gable_end_faces per plane (length ==
   gable_ends), plus a self-check block spelling out the invariant.

2. THE SEAM GUARD: AN ORPHAN GABLE END IS NEVER DISTRIBUTED ONTO AN
   UNRELATED WALL. It FLAGS and stays unattributed, loud, on the card
   and on the sheet. The perpendicular-axis heuristic is retired.

Addendum to (1): PITCH PER PLANE — a plane that carries no printed
pitch FLAGS rather than inheriting the house value. The entry gable at
10/12 against a main roof at 7/12 is the live case, and a wrong
inherited pitch computes a wrong rise on a gable that is currently
honestly null.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, ROOF_PASS_PROMPT, build_blueprint_readback,
)
from routes.blueprint_elevation import build_blueprint_sheet  # noqa: E402


# ---------- (A) prompt-side: schema requires the new fields ----------

def test_system_prompt_declares_gable_end_faces():
    """The main extraction schema names gable_end_faces on the roof
    plane object AND lists it as REQUIRED when gable_ends > 0."""
    assert "gable_end_faces" in SYSTEM_PROMPT
    assert "REQUIRED when gable_ends > 0" in SYSTEM_PROMPT


def test_system_prompt_names_the_entry_plane_and_orphan_rule():
    """Send-6 read-fix language: the entry gable is ITS OWN plane; an
    orphan end (no face named) is refused by the app's attribution."""
    assert "entry" in SYSTEM_PROMPT.lower()
    assert "orphan" in SYSTEM_PROMPT.lower()
    assert "silently distributed" in SYSTEM_PROMPT.lower()


def test_system_prompt_declares_per_plane_pitch():
    """Per-plane pitch — a plane's own printed pitch, empty when unread
    (the app flags rather than inheriting)."""
    assert '"pitch"' in SYSTEM_PROMPT
    # NEVER inherit the main body pitch — the addendum to send-6.
    assert "NEVER inherit" in SYSTEM_PROMPT


def test_system_prompt_carries_the_self_check_block():
    """Explicit S1/S2/S3 self-checks (EMIT-ONE-PER-END, FACES-PER-END,
    PITCH-PER-PLANE)."""
    assert "EMIT-ONE-PER-END" in SYSTEM_PROMPT
    assert "FACES-PER-END" in SYSTEM_PROMPT
    assert "PITCH-PER-PLANE" in SYSTEM_PROMPT


def test_roof_pass_prompt_mirrors_the_schema():
    """The focused roof-pass prompt carries the same fields — a plane
    the roof pass emits must satisfy the same invariants as the main
    read."""
    assert "gable_end_faces" in ROOF_PASS_PROMPT
    assert '"pitch"' in ROOF_PASS_PROMPT
    assert "EMIT-ONE-PER-END" in ROOF_PASS_PROMPT


# ---------- (B) sheet renders per-plane pitch, orphans loud ----------

EST = {"estimate_number": "EST-886440", "customer_name": "boni",
       "address": "x"}


def _sheet(raw: dict, which: str) -> dict:
    run = {"run_id": "send-6-pins", "result": {"raw_ai": raw},
           "model_name": "test", "completed_at": "2026-08-11"}
    return build_blueprint_sheet(EST, run, which)


def test_entry_gable_at_own_pitch_computes_rise_from_plane_pitch():
    """Entry gable emitted as its own plane, pitch 10/12, base 8 ft →
    rise 8/2 × 10/12 = 3.33 ft. Main body pitch 7/12 is NOT inherited."""
    raw = {
        "walls": [
            {"label": "front", "width_ft": 40.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 0,
             "height_segments": [
                 {"name": "main body", "width_ft": 32.0,
                  "height_ft": 20.0},
                 {"name": "entry portico", "width_ft": 8.0,
                  "height_ft": 20.0},
             ]},
            {"label": "back", "width_ft": 40, "height_ft": 20,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
            {"label": "right", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
        ],
        "roof_planes": [
            {"label": "main", "gable_ends": 2,
             "gable_end_faces": ["left", "right"],
             "pitch": "7/12", "is_porch": False},
            {"label": "entry", "gable_ends": 1,
             "gable_end_faces": ["front"], "pitch": "10/12",
             "is_porch": False},
        ],
        "doors": [], "windows": [],
    }
    s = _sheet(raw, "front")
    notes = s["wall"]["wing_triangle_notes"]
    assert len(notes) == 1
    n = notes[0]
    assert n["plane"] == "entry"
    assert n["base_ft"] == 8.0
    assert n["plane_pitch"] == "10/12"
    expected = round(8.0 / 2 * (10.0 / 12.0), 2)
    assert n["height_ft"] == expected, (
        f"expected {expected}, got {n['height_ft']}")
    # Area = 0.5 × 8 × height
    assert n["area_sqft"] == round(0.5 * 8.0 * expected, 1)
    # Area flows into the wall area total (gable_triangle_secondary).
    kinds = [c["kind"] for c in s["wall"]["area_components"]]
    assert "gable_triangle_secondary" in kinds


def test_wing_without_plane_pitch_leaves_height_null_and_says_why():
    """A wing plane with no printed pitch does NOT inherit the main
    body pitch — the height stays null and the sheet says so."""
    raw = {
        "walls": [
            {"label": "front", "width_ft": 40.0, "height_ft": 20.0,
             "gable_triangle_height_ft": 0,
             "height_segments": [
                 {"name": "main body", "width_ft": 32.0,
                  "height_ft": 20.0},
                 {"name": "entry", "width_ft": 8.0,
                  "height_ft": 20.0},
             ]},
            {"label": "back", "width_ft": 40, "height_ft": 20,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
            {"label": "right", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
        ],
        "roof_planes": [
            {"label": "main", "gable_ends": 2,
             "gable_end_faces": ["left", "right"],
             "pitch": "7/12", "is_porch": False},
            {"label": "entry", "gable_ends": 1,
             "gable_end_faces": ["front"], "pitch": "",
             "is_porch": False},
        ],
        "doors": [], "windows": [],
    }
    s = _sheet(raw, "front")
    n = s["wall"]["wing_triangle_notes"][0]
    assert n["height_ft"] is None
    assert n["area_sqft"] is None
    # The disclosure names WHY, and does NOT inherit main's 7/12.
    assert "plane pitch UNREAD" in n["height_source"]
    assert "does not inherit" in n["height_source"].lower()


def test_orphan_gable_surfaces_loud_on_the_sheet():
    """A plane emits gable_ends > 0 with no gable_end_faces evidence
    → the ends are ORPHANS. The sheet carries a LOUD orphan_note on
    every wall — never silently on the perpendicular pair."""
    raw = {
        "walls": [
            {"label": "front", "width_ft": 40, "height_ft": 20,
             "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 40, "height_ft": 20,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
            {"label": "right", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
        ],
        "roof_planes": [
            {"label": "main", "gable_ends": 2,
             "gable_end_faces": ["left", "right"], "is_porch": False},
            # Wing with no gable_end_faces evidence — the orphan case.
            {"label": "garage/bonus", "gable_ends": 2,
             "is_porch": False},
        ],
        "doors": [], "windows": [],
    }
    for which in ("front", "back", "left", "right"):
        s = _sheet(raw, which)
        # Wing gables MUST NOT silently attribute to the perpendicular pair.
        if which in ("front", "back"):
            assert s["wall"]["secondary_gables"] == [], (
                f"{which} wall received a silent perpendicular attribution")
        # Orphan disclosure lives on every sheet.
        assert s["wall"]["orphan_gables"], (
            f"orphan missing on {which} sheet")
        assert "UNATTRIBUTED WING GABLE" in (
            s["wall"]["orphan_note"] or "")


# ---------- (C) readback rail fires per-plane pitch / overhang / wall ----------

def _multi_plane_raw() -> dict:
    """Cross-gable house: entry gable at 10/12 with its own 12" overhang;
    garage plane at 7/12 with a printed 9'-11 7/8" wall height and NO
    overhang printed (FASCIA ONLY NO OVERHANG on that face); main body
    at 7/12."""
    return {
        "walls": [
            {"label": "front", "width_ft": 40, "height_ft": 20,
             "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 40, "height_ft": 20,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
            {"label": "right", "width_ft": 30, "height_ft": 20,
             "gable_triangle_height_ft": 8.0},
        ],
        "roof_planes": [
            {"label": "main", "gable_ends": 2,
             "gable_end_faces": ["left", "right"], "pitch": "7/12",
             "overhang_in": 12, "is_porch": False},
            {"label": "entry", "gable_ends": 1,
             "gable_end_faces": ["front"], "pitch": "10/12",
             "overhang_in": 12, "is_porch": False},
            {"label": "garage", "gable_ends": 1,
             "gable_end_faces": ["front"], "pitch": "",
             "overhang_in": 0, "wall_height_ft": 9.99,
             "is_porch": False},
        ],
        "roof_pitch": "7/12",
    }


def test_rail_names_pitch_missing_and_varying_planes():
    """The rail names the entry plane at 10/12 (pitch_varies_by_plane)
    AND the garage plane with no printed pitch (pitch_missing_on_planes) —
    never a silent inheritance."""
    rb = build_blueprint_readback(_multi_plane_raw())
    codes = {r["code"]: r for r in rb["rail"]}
    assert "pitch_varies_by_plane" in codes
    assert "entry=10/12" in codes["pitch_varies_by_plane"]["text"]
    assert "pitch_missing_on_planes" in codes
    assert "garage" in codes["pitch_missing_on_planes"]["text"]


def test_rail_names_overhang_by_plane_and_missing():
    """Per-plane overhang surfaces — one plane at 12", another at 0"
    (the FASCIA ONLY NO OVERHANG case) → overhang_by_plane is loud
    with both. A plane with null overhang (not read) fires
    overhang_missing_on_planes."""
    raw = _multi_plane_raw()
    # Add a fourth plane with NO overhang read to fire the miss code.
    raw["roof_planes"].append(
        {"label": "portico", "gable_ends": 0,
         "pitch": "7/12", "is_porch": False})
    rb = build_blueprint_readback(raw)
    codes = {r["code"]: r for r in rb["rail"]}
    assert "overhang_by_plane" in codes
    text = codes["overhang_by_plane"]["text"]
    assert "main=12" in text and "garage=0" in text
    assert "overhang_missing_on_planes" in codes
    assert "portico" in codes["overhang_missing_on_planes"]["text"]


def test_rail_names_printed_garage_wall_height():
    """A plane carrying a printed wall_height_ft (garage 9'-11 7/8")
    surfaces on the readback rail — never silently tuned to reach
    the sided height."""
    rb = build_blueprint_readback(_multi_plane_raw())
    codes = {r["code"]: r for r in rb["rail"]}
    assert "wall_height_by_plane" in codes
    assert "garage" in codes["wall_height_by_plane"]["text"]
