"""BONI SECOND SEND (Howard, 2026-08-05) — ROOF GEOMETRY PASS pins.

Three consecutive full-sheet reads dropped the garage roof plane and the
garage-wing corners (attention dilution across 11 dense sheets). The fix
is a FOCUSED second call (roof plan + elevations + floor plan only) with
a CONSERVATIVE pure merge. These pins hold the merge honest:
- planes accepted ONLY when they add the garage entry the main read lacks
- corners accepted ONLY when the walk invariant (out − in = 4) holds and
  the count did not shrink
- pitch accepted ONLY in N/12 form — and a corrected pitch recomputes the
  gable triangles by the schema's own printed-pitch formula
- junk from the pass changes NOTHING (main read stands)
"""
import sys

sys.path.insert(0, "/app/backend")

from routes.ai_blueprint import (  # noqa: E402
    _merge_roof_pass,
    _roof_pass_needed,
    _roof_pass_sheet_indexes,
)


def _main_raw(planes=None, oc=6, ic=2, oclf=92):
    return {
        "walls": [
            {"label": "front", "width_ft": 58, "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 58, "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 39, "gable_triangle_height_ft": 19.5},
            {"label": "right", "width_ft": 39, "gable_triangle_height_ft": 19.5},
        ],
        "doors": [{"id": "G1", "type_hint": "garage"}],
        "roof_pitch": "12/12",
        "roof_planes": planes if planes is not None else [
            {"label": "main", "eave_lf": 116, "rake_lf": 84, "gable_ends": 2,
             "is_porch": False, "porch_ceiling_sqft": 0},
            {"label": "porch", "eave_lf": 24, "rake_lf": 0, "gable_ends": 0,
             "is_porch": True, "porch_ceiling_sqft": 99},
        ],
        "outside_corner_count": oc, "inside_corner_count": ic,
        "outside_corner_lf": oclf, "inside_corner_lf": 36,
        "sheets_identified": [
            {"page": 1, "useful_for": "elevation"},
            {"page": 2, "useful_for": "elevation"},
            {"page": 3, "useful_for": "other"},
            {"page": 6, "useful_for": "floor_plan"},
            {"page": 7, "useful_for": "floor_plan"},
            {"page": 11, "useful_for": "roof"},
        ],
    }


GOOD_PASS = {
    "roof_pitch": "7/12",
    "roof_planes": [
        {"label": "main", "eave_lf": 116, "rake_lf": 82, "gable_ends": 2,
         "is_porch": False, "porch_ceiling_sqft": 0},
        {"label": "garage", "eave_lf": 36, "rake_lf": 42, "gable_ends": 1,
         "is_porch": False, "porch_ceiling_sqft": 0},
        {"label": "porch", "eave_lf": 15, "rake_lf": 0, "gable_ends": 0,
         "is_porch": True, "porch_ceiling_sqft": 99},
    ],
    "outside_corner_count": 8, "inside_corner_count": 4,
    "outside_corner_lf": 128, "inside_corner_lf": 72,
    "notes": "garage/bonus wing 8/12 and 10/12, porch mono 4/12",
}


def test_pass_fires_only_on_garage_evidence_without_garage_plane():
    assert _roof_pass_needed(_main_raw()) is True
    with_garage = _main_raw(planes=GOOD_PASS["roof_planes"])
    assert _roof_pass_needed(with_garage) is False
    # garage plane present but gable-blind (rake 0, no ends) → fire
    blind = _main_raw(planes=[
        {"label": "main", "eave_lf": 116, "rake_lf": 82, "gable_ends": 2,
         "is_porch": False, "porch_ceiling_sqft": 0},
        {"label": "garage", "eave_lf": 50, "rake_lf": 0, "gable_ends": 0,
         "is_porch": False, "porch_ceiling_sqft": 0},
    ])
    assert _roof_pass_needed(blind) is True
    no_evidence = _main_raw()
    no_evidence["doors"] = []
    assert _roof_pass_needed(no_evidence) is False


def test_merge_appends_the_missing_garage_plane_and_corner_walk():
    raw = _merge_roof_pass(_main_raw(), GOOD_PASS)
    labels = [p["label"] for p in raw["roof_planes"]]
    assert "garage" in labels
    # SURGICAL: main-read planes stay; only the missing plane is appended
    assert len(raw["roof_planes"]) == 3
    # AGREEMENT-OR-FLAG (Howard ruled 2026-08-10): the walks disagree
    # (primary 6/2, roof pass 8/4) → THE PRIMARY STANDS and the conflict
    # prints BOTH numbers. Max-wins acceptance is dead.
    assert raw["outside_corner_count"] == 6
    assert raw["outside_corner_lf"] == 92
    cwc = raw["_corner_walk_conflict"]
    assert cwc["primary"]["out"] == 6 and cwc["primary"]["in"] == 2
    assert cwc["roof_pass"]["out"] == 8 and cwc["roof_pass"]["in"] == 4
    assert raw["roof_pitch"] == "7/12"
    acc = raw["_roof_pass"]["accepted"]
    assert set(acc) == {"garage_plane_appended", "roof_pitch"}
    assert "corners" in raw["_roof_pass"]["rejected"]


def test_merge_is_surgical_on_a_gable_blind_garage_plane():
    """The full-context read keeps its EAVE figure; the focused read
    supplies ONLY the rake edges + gable-end census it missed."""
    blind = _main_raw(planes=[
        {"label": "main", "eave_lf": 116, "rake_lf": 82, "gable_ends": 2,
         "is_porch": False, "porch_ceiling_sqft": 0},
        {"label": "garage", "eave_lf": 50, "rake_lf": 0, "gable_ends": 0,
         "is_porch": False, "porch_ceiling_sqft": 0},
    ])
    raw = _merge_roof_pass(blind, GOOD_PASS)
    g = [p for p in raw["roof_planes"] if p["label"] == "garage"][0]
    assert g["eave_lf"] == 50, "eave stays with the full-context read"
    assert g["rake_lf"] == 42 and g["gable_ends"] == 1
    assert raw["_roof_pass"]["accepted"]["garage_rakes"] == {
        "rake_lf": 42.0, "gable_ends": 1}


def test_corrected_pitch_recomputes_the_gable_triangles():
    """12/12 misread inflated the gables (19.5 ft); the 7/12 correction
    lands the schema formula: (39/2) × 7/12 = 11.38 — the gable siding
    area rides the same fix."""
    raw = _merge_roof_pass(_main_raw(), GOOD_PASS)
    gables = [w["gable_triangle_height_ft"] for w in raw["walls"]
              if w["gable_triangle_height_ft"] > 0]
    assert gables == [11.38, 11.38]


def test_merge_rejects_invariant_breaks_and_shrinks():
    # invariant broken (8 − 3 ≠ 4) → corners stand
    bad = {**GOOD_PASS, "inside_corner_count": 3}
    raw = _merge_roof_pass(_main_raw(), bad)
    assert raw["outside_corner_count"] == 6
    # count shrank → corners stand
    shrunk = {**GOOD_PASS, "outside_corner_count": 4, "inside_corner_count": 0}
    raw2 = _merge_roof_pass(_main_raw(), shrunk)
    assert raw2["outside_corner_count"] == 6
    # junk pitch → pitch stands, triangles untouched
    junk = {**GOOD_PASS, "roof_pitch": "steep"}
    raw3 = _merge_roof_pass(_main_raw(), junk)
    assert raw3["roof_pitch"] == "12/12"
    assert raw3["walls"][2]["gable_triangle_height_ft"] == 19.5
    # pass without a garage entry appends nothing
    no_garage = {**GOOD_PASS,
                 "roof_planes": [p for p in GOOD_PASS["roof_planes"]
                                 if p["label"] != "garage"]}
    raw4 = _merge_roof_pass(_main_raw(), no_garage)
    assert len(raw4["roof_planes"]) == 2


def test_junk_pass_changes_nothing():
    raw = _merge_roof_pass(_main_raw(), {"roof_planes": "nope", "roof_pitch": 12})
    assert raw["outside_corner_count"] == 6
    assert raw["roof_pitch"] == "12/12"
    assert len(raw["roof_planes"]) == 2


def test_sheet_selection_prioritizes_roof_then_elevations():
    idxs = _roof_pass_sheet_indexes(_main_raw(), page_count=11)
    assert idxs[0] == 10, "roof plan (page 11) rides first"
    assert set(idxs) == {10, 0, 1, 5, 6}
