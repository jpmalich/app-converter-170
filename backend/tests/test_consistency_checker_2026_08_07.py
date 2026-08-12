"""INTERNAL CONSISTENCY CHECKER (Howard ruled 2026-08-07).

"The entire point is that the card arrives already clean. If it lands
after, I grade contradictions the app could have caught itself."

The checker compares a read's numbers against OTHER FACTS IN THE SAME
READ — never against a target, never against an installed list (purity
rider). Pins one flag per Boni-graded contradiction class:
  1. corner_taller_than_wall — two reads disagreeing about one house
     (CORRECTED 2026-08-08: the flag was right, the wall table was the
     wrong side; the flag resolves toward NEITHER source).
  2. corner_lf_not_sum — the 188-vs-141 class.
  3. gable_census_mismatch — 3 plane gables vs 2 walls (the garage gable
     with no wall to live on).
  4. box_model — mirrored elevations while the footprint proves a wing.
  5. run_exceeds_facade — a continuous run can't outrun its facade.
Plus: a clean read produces ZERO flags, and the card names the clean
state (never silent). EN+ES strings pinned.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    build_blueprint_readback, check_read_consistency,
)


def _clean_raw():
    return {
        "avg_wall_height_ft": 18,
        "walls": [
            {"label": "front", "width_ft": 58, "height_ft": 18,
             "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 58, "height_ft": 18,
             "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 39, "height_ft": 18,
             "gable_triangle_height_ft": 11.4},
            {"label": "right", "width_ft": 40, "height_ft": 18,
             "gable_triangle_height_ft": 11.4},
        ],
        "roof_planes": [
            {"label": "main", "eave_lf": 116, "rake_lf": 82,
             "gable_ends": 2, "is_porch": False},
        ],
        "outside_corner_count": 4,
        "outside_corner_heights_ft": [18, 18, 10.5, 10.5],
        "outside_corner_lf": 57,
        "inside_corner_count": 0,
        "footprint_area_sqft": 58 * 39,
        "gutter_runs": [{"label": "front", "lf": 58},
                        {"label": "back", "lf": 58}],
    }


def test_clean_read_raises_no_flags():
    assert check_read_consistency(_clean_raw()) == []


def test_corner_cannot_exceed_the_tallest_wall():
    """CORRECTED 2026-08-08 (Howard: the wall table's height was the
    WRONG one; the corner ledger was right). The INCONSISTENCY flag was
    correct — only resolution language was wrong. The flag names both
    sources and resolves toward NEITHER; a taped or contractor-entered
    height outranks every read."""
    raw = _clean_raw()
    raw["outside_corner_heights_ft"] = [20.5, 20.5, 20.5, 20.5]
    raw["outside_corner_lf"] = 82
    flags = check_read_consistency(raw)
    codes = [f["code"] for f in flags]
    assert "corner_taller_than_wall" in codes
    f = next(x for x in flags if x["code"] == "corner_taller_than_wall")
    assert f["vars"]["wall"] == "18", \
        "the flag must NAME the wall table's number beside the corner ledger's — resolving toward neither"
    assert f["level"] == "loud"


def test_corner_lf_must_equal_the_sum_of_its_own_heights():
    raw = _clean_raw()
    raw["outside_corner_heights_ft"] = [20.5] * 4 + [10.5] * 4 + [8.5] * 2
    raw["outside_corner_lf"] = 188  # sum is 141 — the graded defect
    flags = check_read_consistency(raw)
    f = next(x for x in flags if x["code"] == "corner_lf_not_sum")
    assert f["vars"]["lf"] == "188" and f["vars"]["sum"] == "141"


def test_gable_census_must_match_the_walls():
    """Ruled 2026-08-11 send-3 item c, HARDENED send-6 item 1: the
    attribution now requires plane-side `gable_end_faces` evidence.
    Without evidence, wing ends orphan and the flag fires loudly."""
    # Case A — attribution completes with faces evidence:
    raw = _clean_raw()
    raw["roof_planes"].append(
        {"label": "garage", "eave_lf": 24, "rake_lf": 26,
         "gable_ends": 1, "gable_end_faces": ["front"],
         "is_porch": False})
    flags = check_read_consistency(raw)
    codes = [x["code"] for x in flags]
    assert "gable_census_mismatch" not in codes, (
        "attribution should reconcile the 1-end garage onto FRONT; "
        f"got flags: {codes}")

    # Case B — no primary axis + no faces evidence → orphan surfaces,
    # census fires loudly, orphan planes named.
    raw2 = _clean_raw()
    for w in raw2["walls"]:
        w["gable_triangle_height_ft"] = 0
    raw2["roof_planes"].append(
        {"label": "garage", "eave_lf": 24, "rake_lf": 26,
         "gable_ends": 1, "is_porch": False})
    flags2 = check_read_consistency(raw2)
    f = next(x for x in flags2 if x["code"] == "gable_census_mismatch")
    assert f["vars"]["planes"] == 3
    assert f["vars"]["walls"] == 0
    assert f["vars"]["primary"] == 0
    assert f["vars"]["secondary"] == 0
    assert f["vars"].get("orphans") == 1
    assert "garage" in f["vars"].get("orphan_planes", "")


def test_mirrored_elevations_with_a_wing_flag_the_box_model():
    raw = _clean_raw()
    raw["walls"][3]["width_ft"] = 39  # left == right exactly
    raw["footprint_area_sqft"] = 2351  # rectangle is 58×39 = 2262
    flags = check_read_consistency(raw)
    assert any(f["code"] == "box_model" for f in flags)
    # same mirror WITHOUT the wing evidence → no accusation
    raw2 = _clean_raw()
    raw2["walls"][3]["width_ft"] = 39
    raw2["footprint_area_sqft"] = 58 * 39
    assert not any(f["code"] == "box_model"
                   for f in check_read_consistency(raw2))


def test_a_run_cannot_outrun_its_facade():
    raw = _clean_raw()
    raw["gutter_runs"] = [{"label": "front", "lf": 75}]
    flags = check_read_consistency(raw)
    f = next(x for x in flags if x["code"] == "run_exceeds_facade")
    assert f["vars"]["run"] == "75" and f["vars"]["wall"] == "58"


def test_consistency_rides_the_readback_card():
    rb = build_blueprint_readback(_clean_raw())
    assert rb["consistency"] == [], "clean state must be NAMED, never absent"
    raw = _clean_raw()
    raw["outside_corner_heights_ft"] = [20.5] * 4
    raw["outside_corner_lf"] = 82
    rb2 = build_blueprint_readback(raw)
    assert any(f["code"] == "corner_taller_than_wall"
               for f in rb2["consistency"])


def test_checker_strings_exist_in_both_languages():
    text = (Path(__file__).resolve().parents[2]
            / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")
    for code in ("corner_taller_than_wall", "corner_lf_not_sum",
                 "gable_census_mismatch", "box_model",
                 "run_exceeds_facade", "clean"):
        key = f"bp.rb.consistency.{code}"
        assert text.count(f'"{key}"') == 2, f"{key} must exist in EN and ES"


def test_checker_is_pure_no_targets_no_lists():
    """PURITY RIDER: the checker source may carry no job figure and no
    installed-list number as a constant."""
    import inspect
    src = inspect.getsource(check_read_consistency)
    for evidence in ("1044", "20.5", "188", "141", "167", "132.5", "16.5"):
        assert evidence not in src, f"evidence figure {evidence} leaked into code"
