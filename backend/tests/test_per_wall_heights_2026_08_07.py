"""PER-WALL HEIGHT VARIATION + 8-7 EVENING GRADE (Howard ruled 2026-08-07).

"PER-WALL HEIGHT VARIATION IS NOW THE TOP ITEM. It is the root of both
the siding over-count and the corner heights, and it is worth more than
everything else on this card combined."

THE 10-SQUARE MECHANISM: the box model applied one wall height to the
whole envelope — a front wall that is half 2-story body and half 1-story
garage wing was sided at the tall height end to end. Siding a 10-foot
wall at 19 feet over-orders every low section on the house.

Pins:
1. height_segments govern the wall gross: Σ(w×h), never width×tallest.
2. ONE COPY: walk_walls and the profile breakdown consume the same
   helper — the siding line and the Field Verify table can never hold
   different answers about the same wall.
3. Broken segment walks fall back to the rectangle AND get flagged.
4. Checker source-naming (Howard's condition): flags name both sources,
   resolve toward NEITHER; taped/contractor heights outrank (EN+ES).
5. New ruled checks: porch run = printed width; stated dims reproduce
   stated area; footprint ABSENCE named; printed-size transcription.
6. Bar (d): the waste step PRINTS on the line (soffit 40 → 48 must
   explain its ×1.20), idempotently, backend + frontend mirrored.
PURITY: fixtures synthetic; nothing tuned toward 34 squares.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from measure_staging import walk_walls, wall_body_gross_sqft  # noqa: E402
from profile_callouts import breakdown_walls_by_profile  # noqa: E402
from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _parse_printed_size, check_read_consistency,
)
from routes.hover import _bake_tab_waste  # noqa: E402


SEGMENTED_WALL = {
    "label": "front", "width_ft": 58, "height_ft": 19,
    "height_segments": [
        {"label": "main body", "width_ft": 30, "height_ft": 19},
        {"label": "garage wing", "width_ft": 28, "height_ft": 10},
    ],
}


# ------------------------------------------------------------- geometry
def test_segments_govern_the_wall_gross():
    gross, segs = wall_body_gross_sqft(SEGMENTED_WALL)
    assert gross == 30 * 19 + 28 * 10  # 850, not 58×19 = 1102
    assert len(segs) == 2


def test_broken_segment_walk_falls_back_to_the_rectangle():
    w = {**SEGMENTED_WALL, "height_segments": [
        {"label": "main", "width_ft": 30, "height_ft": 19}]}  # sums to 30 ≠ 58
    gross, segs = wall_body_gross_sqft(w)
    assert gross == 58 * 19 and segs == []


def test_no_segments_keeps_the_rectangle_byte_identical():
    gross, segs = wall_body_gross_sqft(
        {"label": "back", "width_ft": 58, "height_ft": 19})
    assert gross == 58 * 19 and segs == []


def test_walk_walls_and_profile_breakdown_hold_one_answer():
    walls = [SEGMENTED_WALL,
             {"label": "back", "width_ft": 58, "height_ft": 19}]
    walk = walk_walls(walls)
    assert walk["siding_sqft"] == (850) + (58 * 19)
    front_detail = [d for d in walk["detail"] if d["label"] == "front"][0]
    assert front_detail["segments"] == [(30.0, 19.0), (28.0, 10.0)]
    bd = breakdown_walls_by_profile(walls, default_body_profile="D4")
    assert bd["per_profile_sqft"]["D4"] == walk["siding_sqft"], \
        "the siding line and the Field Verify table must hold ONE answer"


def test_prompt_demands_the_section_walk():
    for must in ("height_segments", "A HOUSE IS NOT A UNIFORM BOX",
                 "Segment widths MUST sum to width_ft"):
        assert must in SYSTEM_PROMPT, f"prompt lost the ruling: {must!r}"


# -------------------------------------------------------------- checker
def _raw(**kw):
    base = {
        "walls": [
            dict(SEGMENTED_WALL),
            {"label": "back", "width_ft": 58, "height_ft": 19},
            {"label": "left", "width_ft": 39, "height_ft": 19},
            {"label": "right", "width_ft": 40, "height_ft": 19},
        ],
        "roof_planes": [
            {"label": "main", "eave_lf": 116, "rake_lf": 82,
             "gable_ends": 0, "is_porch": False},
            {"label": "porch", "eave_lf": 16, "rake_lf": 12,
             "gable_ends": 0, "is_porch": True,
             "porch_ceiling_sqft": 99, "porch_width_ft": 16.5,
             "porch_depth_ft": 6},
        ],
        "outside_corner_count": 4,
        "outside_corner_heights_ft": [19, 19, 10, 10],
        "outside_corner_lf": 58,
        "footprint_area_sqft": 58 * 39,
        "gutter_runs": [{"label": "front", "lf": 58},
                        {"label": "porch", "lf": 16.5}],
        "windows": [],
    }
    base.update(kw)
    return base


def test_segments_count_toward_the_tallest_wall():
    raw = _raw()
    raw["walls"] = [{"label": "front", "width_ft": 58, "height_ft": 10,
                     "height_segments": [
                         {"label": "main", "width_ft": 30, "height_ft": 19},
                         {"label": "wing", "width_ft": 28, "height_ft": 10}]}]
    raw["outside_corner_heights_ft"] = [19, 19, 10, 10]
    codes = [f["code"] for f in check_read_consistency(raw)]
    assert "corner_taller_than_wall" not in codes, \
        "a 19' corner is legal against a 19' SEGMENT even when height_ft reads 10"


def test_mismatched_segment_walk_is_flagged():
    raw = _raw()
    raw["walls"][0]["height_segments"] = [
        {"label": "main", "width_ft": 30, "height_ft": 19}]
    flags = check_read_consistency(raw)
    f = next(x for x in flags if x["code"] == "wall_segments_mismatch")
    assert f["vars"] == {"label": "front", "sum": "30", "width": "58"}


def test_porch_run_must_equal_its_printed_width():
    raw = _raw()
    raw["gutter_runs"] = [{"label": "porch", "lf": 24}]
    f = next(x for x in check_read_consistency(raw)
             if x["code"] == "porch_run_vs_width")
    assert f["vars"] == {"run": "24", "width": "16.5"}
    assert not any(x["code"] == "porch_run_vs_width"
                   for x in check_read_consistency(_raw()))


def test_stated_dims_must_reproduce_the_stated_area():
    raw = _raw()
    raw["roof_planes"][1]["porch_width_ft"] = 16  # 16×6 = 96 vs area 99? 3% — inside tolerance
    raw["roof_planes"][1]["porch_ceiling_sqft"] = 110  # 96 vs 110 > 5%
    raw["gutter_runs"] = [{"label": "front", "lf": 58}]
    f = next(x for x in check_read_consistency(raw)
             if x["code"] == "porch_dims_vs_area")
    assert f["vars"]["product"] == "96" and f["vars"]["area"] == "110"


def test_footprint_absence_is_named_never_silent():
    raw = _raw()
    raw["footprint_area_sqft"] = None
    assert any(f["code"] == "footprint_missing"
               for f in check_read_consistency(raw)), \
        "the wing check going silent was graded — absence must be NAMED"
    assert not any(f["code"] == "footprint_missing"
                   for f in check_read_consistency(_raw()))


def test_printed_size_transcription_check_catches_mark_b():
    raw = _raw(windows=[
        {"id": "B", "printed_size": "2'-4\" x 5'-4\"",
         "width_in": 28, "height_in": 48, "qty": 1,
         "type_hint": "single_hung", "elevation": "front"}])
    f = next(x for x in check_read_consistency(raw)
             if x["code"] == "window_size_parse_mismatch")
    assert f["vars"]["mark"] == "B"
    assert f["vars"]["parsed"] == "28×64" and f["vars"]["carried"] == "28×48"


def test_printed_size_parser_never_guesses():
    assert _parse_printed_size("3-0x5-0") == (36, 60)
    assert _parse_printed_size("3050") == (36, 60)
    assert _parse_printed_size("SH 2-4_5-4") == (28, 64)
    assert _parse_printed_size("2'-4\" x 5'-4\"") == (28, 64)
    assert _parse_printed_size("see schedule") is None
    assert _parse_printed_size("") is None


def test_checker_names_sources_and_authority_in_both_languages():
    text = (Path(__file__).resolve().parents[2]
            / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")
    assert "resolves toward NEITHER" in text
    assert "A taped or contractor-entered height outranks both" in text
    assert "no resuelve hacia NINGUNA" in text
    for code in ("wall_segments_mismatch", "footprint_missing",
                 "porch_run_vs_width", "porch_dims_vs_area",
                 "window_size_parse_mismatch"):
        assert text.count(f'"bp.rb.consistency.{code}"') == 2, \
            f"{code} must exist in EN and ES"


# ------------------------------------------------------------ waste chip
def test_the_waste_step_prints_on_the_line():
    lines = [{"tab": "vinyl", "section": "Vinyl Soffit with Siding",
              "name": "Soffit & fascia Charter Oak Standard Color",
              "unit": "PCS", "qty": 40.0, "note": "(overhang × runs + porch) ÷ 10"}]
    baked = _bake_tab_waste(lines, 20)
    assert baked[0]["qty"] == 48.0 and baked[0]["raw_qty"] == 40.0
    assert baked[0]["note"].endswith("· ×1.20 waste (20%): 40 → 48"), \
        f"the 48 must explain its last step, got: {baked[0]['note']!r}"
    # idempotent — a re-bake never stacks chips
    rebaked = _bake_tab_waste(baked, 20)
    assert rebaked[0]["note"].count("waste (") == 1


def test_frontend_mirrors_the_waste_chip():
    js = (Path(__file__).resolve().parents[2]
          / "frontend/src/lib/wasteLogic.js").read_text(encoding="utf-8")
    assert "export function withWasteChip" in js
    assert js.count("withWasteChip(l.note") >= 3, \
        "bake + recompute + recomputeAll must all print the step"
