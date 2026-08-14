"""THREE CORRECTIONS + TWO READABLE SPECS (Howard ruled 2026-08-08).

1. CORNERS ~20'-0¼" — the 20.5' read was essentially correct; the 18'
   ground truth was Howard's error and everything built on it is VOID.
   DO NOT "fix" the corner read. (No code change — pinned as doctrine:
   nothing tunes the corner read downward.)
2. THE CHECKER POINTED AT THE WRONG SOURCE — the flag was correct, the
   resolution language wasn't. Authoritative wording stripped: flags
   name both sources, resolve toward NEITHER, tape/contractor outranks.
3. CATEGORY ERROR — 2351 was TOTAL FINISHED LIVING (storeys summed)
   read as a footprint. Real footprint ≈ first floor + garage. The
   area table reads AS LABELLED; the wing/box checks consume
   first_floor + garage when the table holds them; a footprint equal to
   TOTAL FINISHED with a second storey present is self-caught.
4. UNDIMENSIONED SECTION (Boni back garage wall — the first genuine
   undimensioned quantity on the job): FLAG, never a guess.
5. READABLE SPECS: soffit finish ("VENTED (EAVES)"/"SOLID (RAKE)") and
   per-location overhang (12" at the garage; FASCIA ONLY NO OVERHANG
   elsewhere) — read or flag, never silently defaulted.
PURITY: 20'-0¼", 9'-11"×24', 1019, 1332, 795, 2351 are EVIDENCE — no
constant, no default, no assertion target, and Howard's 14'-5" enters
as contractor-estimated, never TAPED.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from measure_staging import wall_body_gross_sqft  # noqa: E402
from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _read_footprint_sqft, build_blueprint_readback,
    check_read_consistency,
)


def _raw(**kw):
    base = {
        "walls": [
            {"label": "front", "width_ft": 58, "height_ft": 20},
            {"label": "back", "width_ft": 58, "height_ft": 20},
            {"label": "left", "width_ft": 39, "height_ft": 20},
            {"label": "right", "width_ft": 39, "height_ft": 20},
        ],
        "roof_planes": [{"label": "main", "eave_lf": 116, "rake_lf": 82,
                         "gable_ends": 0, "is_porch": False}],
        "outside_corner_count": 4,
        "outside_corner_heights_ft": [20, 20, 10, 10],
        "outside_corner_lf": 60,
        "footprint_area_sqft": None,
        "area_table": {"total_finished_sqft": 2400,
                       "first_floor_sqft": 1000,
                       "second_floor_sqft": 1400,
                       "garage_sqft": 800, "porch_sqft": 100},
        "gutter_runs": [], "windows": [],
    }
    base.update(kw)
    return base


# ---------------------------------------------------- correction 3: areas
def test_footprint_is_first_floor_plus_garage_never_total_finished():
    assert _read_footprint_sqft(_raw()) == 1800
    assert _read_footprint_sqft({"footprint_area_sqft": 1500}) == 1500
    assert _read_footprint_sqft({}) == 0.0


def test_labelled_areas_kill_the_category_error_in_the_wing_check():
    raw = _raw()  # mirrored walls; true footprint 1800 < rect 2262
    flags = check_read_consistency(raw)
    assert not any(f["code"] == "box_model" for f in flags), \
        "TOTAL FINISHED (2400) must never drive the wing accusation"
    assert not any(f["code"] == "footprint_missing" for f in flags)
    rb = build_blueprint_readback(raw)
    assert rb["wing_check"]["footprint_area_sqft"] == 1800


def test_footprint_equal_to_total_finished_is_self_caught():
    raw = _raw(footprint_area_sqft=2400)
    f = next(x for x in check_read_consistency(raw)
             if x["code"] == "footprint_is_total_finished")
    assert f["vars"] == {"fp": "2400", "tf": "2400"}


# ------------------------------------------- correction 2: no authority
def test_checker_claims_no_authoritative_source():
    src = inspect.getsource(check_read_consistency)
    dict_text = (Path(__file__).resolve().parents[2]
                 / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")
    for banned in ("already holds the right height",
                   "ya tiene la altura correcta"):
        assert banned not in src and banned not in dict_text, \
            f"authoritative resolution wording resurfaced: {banned!r}"
    assert "resolves toward NEITHER" in dict_text


# --------------------------------------- undimensioned section: flag it
def test_undimensioned_section_is_flagged_never_guessed():
    raw = _raw()
    raw["walls"][1]["height_segments"] = [
        {"label": "main body", "width_ft": 34, "height_ft": 20},
        {"label": "garage (no printed height)", "width_ft": 24,
         "height_ft": None},
    ]
    flags = check_read_consistency(raw)
    f = next(x for x in flags if x["code"] == "wall_segment_undimensioned")
    assert f["vars"]["label"] == "back"
    assert "garage" in f["vars"]["section"]
    assert not any(x["code"] == "wall_segments_mismatch" for x in flags), \
        "an undimensioned section is its own flag — not a broken-walk accusation"
    gross, segs, deriv = wall_body_gross_sqft(raw["walls"][1])
    # SEND-13: reports the derivable main body, NAMES the garage as the
    # missing piece — never holds the full 58×20 rectangle over a
    # segment whose height was never read.
    assert gross == 34 * 20 and segs == [(34.0, 20.0)], \
        "the math reports the subset — it never guesses the missing height"
    assert deriv["subset"] is True


# --------------------------------------------- readable specs: soffit
def test_soffit_finish_reads_or_flags():
    rb = build_blueprint_readback(_raw(soffit_finish={
        "eaves": "vented", "rakes": "solid",
        "source_note": "VENTED SOFFIT (EAVES) (TYP) / SOLID SOFFIT (RAKE) (TYP)"}))
    f = next(x for x in rb["rail"] if x["code"] == "soffit_finish_printed")
    assert f["text"] == "eaves vented · rakes solid"
    rb2 = build_blueprint_readback(_raw())
    assert any(x["code"] == "soffit_finish_default" for x in rb2["rail"]), \
        "an unread vented-vs-solid steer must be NAMED"


def test_per_location_overhang_variation_is_named():
    rb = build_blueprint_readback(_raw(
        eave_overhang_in=12,
        overhang_notes=[
            {"where": "garage eave", "overhang_in": 12, "text": "1'-0\""},
            {"where": "left elevation", "overhang_in": 0,
             "text": "FASCIA ONLY NO OVERHANG"},
        ]))
    f = next(x for x in rb["rail"] if x["code"] == "overhang_varies")
    assert "garage eave" in f["text"] and "FASCIA ONLY NO OVERHANG" in f["text"]
    rb2 = build_blueprint_readback(_raw(
        eave_overhang_in=12,
        overhang_notes=[{"where": "eave", "overhang_in": 12, "text": "1'-0\""}]))
    assert not any(x["code"] == "overhang_varies" for x in rb2["rail"]), \
        "one consistent printed overhang is not a variation"


# ------------------------------------------------------------ prompt pins
def test_prompt_carries_the_corrections():
    for must in ("NEVER the \"TOTAL FINISHED\"",
                 "area_table", "soffit_finish", "overhang_notes",
                 "FLAG, never a guess",
                 "FASCIA ONLY NO OVERHANG"):
        assert must in SYSTEM_PROMPT, f"prompt lost the ruling: {must!r}"


def test_new_strings_exist_in_both_languages():
    text = (Path(__file__).resolve().parents[2]
            / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")
    for key in ("bp.rb.consistency.wall_segment_undimensioned",
                "bp.rb.consistency.footprint_is_total_finished",
                "bp.rb.rail.soffit_finish_printed",
                "bp.rb.rail.soffit_finish_default",
                "bp.rb.rail.overhang_varies"):
        assert text.count(f'"{key}"') == 2, f"{key} must exist in EN and ES"
