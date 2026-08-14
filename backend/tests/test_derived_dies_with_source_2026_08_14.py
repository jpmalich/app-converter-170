"""A DERIVED VALUE DIES WITH ITS SOURCE (Howard ruled 2026-08-14).

THE ORPHAN (Boni EST-886440, run 5df22e6d): the AI emitted
`walls.left.width_ft = 39` and `walls.right.width_ft = 39`, each backed
by the quote "39'-0"" that no OCR pass could locate near the wall
(loc: null → recorded as an OCR miss). The value should have died with
its killed source, but the frozen (pre-SEND-8) read carried it straight
into the per-elevation breakdown as a 39×20 = 780 ft² body + a
0.70×39×gable ft² gable — an area that outlived the evidence that was
branded fabricated.

THE MECHANISM: the current kill (`_null_unverified_quotes`) DOES null an
unlocatable-quote wall width. The residual defect was one surface up —
`breakdown_walls_by_profile` / `walk_walls` turned the nulled width into
a SILENT ZERO (or, with intact segments, a rectangle), which shrinks the
house instead of flagging it. Howard's correction: an unreadable width is
UNKNOWN, not zero — the face is NULL AND NAMED and the aggregate
discloses that a face is missing from it.

THESE PINS (relationships, never magnitudes — Howard's purity rider bars
a number off his house from becoming an assertion target; every expected
value is derived IN-TEST from the fixture's own inputs):

  (a) an unlocatable-quote wall width → the derived body AND gable are
      NOT DERIVABLE (None, never 0), the face is named in
      faces_not_derivable, and the killed area never reaches per_profile.
  (b) a LOCATED width is NEVER dropped — its body == width × height read
      from the wall the fixture actually carries.
  (c) the aggregate never silently sums a subset — if any face is not
      derivable, the disclosure says which.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import _null_unverified_quotes  # noqa: E402
from profile_callouts import breakdown_walls_by_profile  # noqa: E402
import measure_staging as staging  # noqa: E402


def _fixture():
    """The Boni orphan shape, self-contained: one wall whose width quote
    is unlocatable (an OCR miss, loc null) + one wall whose width quote
    LOCATED. Both carry a gable so the gable-dies-too leg is exercised on
    the killed wall and the kept wall proves a located width survives.
    The numbers here are INPUT DATA (what the read carried), never
    assertion targets — the pins compute every expected value from them.
    """
    return {
        "roof_pitch": "",
        "walls": [
            {
                "label": "killedside",
                "width_ft": 39.0,          # the fabricated 39'-0" (unlocatable)
                "height_ft": 20.0,
                "gable_triangle_height_ft": 11.375,
                "wall_body_profile_callout": "SIDING",
            },
            {
                "label": "goodback",
                "width_ft": 58.0,          # located quote — must survive
                "height_ft": 20.0,
                "gable_triangle_height_ft": 0,
                "wall_body_profile_callout": "SIDING",
            },
        ],
        "_dim_evidence": {
            "walls.killedside.width_ft": {
                "v": 39.0, "page": 6, "from": "39'-0\"", "loc": None,
            },
            "walls.goodback.width_ft": {
                "v": 58.0, "page": 6, "from": "58'-0\"",
                "loc": {"x_pct": 55.5, "y_pct": 18.1, "w_pct": 1.3, "h_pct": 0.9},
            },
        },
        # The locator recorded the fabricated width as a miss; the located
        # one is NOT a miss (it found its rect).
        "_ocr_quote_misses": [
            {"path": "walls.killedside.width_ft", "page": 6,
             "from": "39'-0\"", "reason": "quote not found on page"},
        ],
    }


# ---------------------------------------------------------------------------
# DIRECTION (a): the derived body AND gable DIE with the killed source.
# ---------------------------------------------------------------------------

def test_killed_width_makes_body_not_derivable_not_zero():
    raw = _fixture()

    # Before the kill the width is present → the body is derivable.
    before = breakdown_walls_by_profile(copy.deepcopy(raw)["walls"])
    killed_before = next(e for e in before["per_elevation"] if e["label"] == "killedside")
    assert killed_before["wall_body_sqft"] is not None
    assert killed_before["wall_body_derivable"] is True

    # The kill nulls the unlocatable width...
    _null_unverified_quotes(raw)
    assert raw["walls"][0]["width_ft"] is None  # source is dead

    # ...and the derived value dies WITH it — NOT DERIVABLE, never 0.
    after = breakdown_walls_by_profile(raw["walls"])
    killed = next(e for e in after["per_elevation"] if e["label"] == "killedside")
    assert killed["wall_body_sqft"] is None, "a killed width must not credit a body"
    assert killed["wall_body_sqft"] != 0, "silent zero shrinks the house — banned"
    assert killed["wall_body_derivable"] is False
    # The gable dies with the same source (a gable needs its wall width).
    assert killed["gable_sqft"] is None


def test_killed_face_is_named_in_faces_not_derivable():
    raw = _fixture()
    _null_unverified_quotes(raw)
    bd = breakdown_walls_by_profile(raw["walls"])
    nd = bd["faces_not_derivable"]
    surfaces = {(f["elevation"], f["surface"]) for f in nd}
    assert ("killedside", "body") in surfaces
    assert ("killedside", "gable") in surfaces
    # Every disclosure carries a human reason naming the missing source.
    for f in nd:
        assert "not derivable" in f["reason"].lower()


def test_killed_area_never_reaches_per_profile():
    """The orphaned 780 (+ gable) must not appear anywhere in the
    aggregate. The killed wall contributes NOTHING to per_profile — the
    total is the located wall's body alone."""
    raw = _fixture()
    good_w = float(raw["walls"][1]["width_ft"])
    good_h = float(raw["walls"][1]["height_ft"])
    _null_unverified_quotes(raw)
    bd = breakdown_walls_by_profile(raw["walls"])
    # Only the located wall (lap) contributes; expected derived from ITS
    # own inputs, never a memorised house number.
    expected_lap = round(good_w * good_h, 1)
    assert bd["per_profile_sqft"].get("lap") == expected_lap


# ---------------------------------------------------------------------------
# DIRECTION (b): a LOCATED width is NEVER dropped.
# ---------------------------------------------------------------------------

def test_located_width_body_equals_width_times_height():
    raw = _fixture()
    _null_unverified_quotes(raw)
    good = raw["walls"][1]
    assert good["width_ft"] is not None, "a located width must survive the kill"
    bd = breakdown_walls_by_profile(raw["walls"])
    e = next(x for x in bd["per_elevation"] if x["label"] == "goodback")
    expected = round(float(good["width_ft"]) * float(good["height_ft"]), 1)
    assert e["wall_body_derivable"] is True
    assert e["wall_body_sqft"] == expected


# ---------------------------------------------------------------------------
# DIRECTION (c): the aggregate never silently sums a subset.
# ---------------------------------------------------------------------------

def test_walk_walls_discloses_the_missing_face():
    raw = _fixture()
    _null_unverified_quotes(raw)
    walk = staging.walk_walls(raw["walls"])
    nd = walk["faces_not_derivable"]
    labels = {f["label"] for f in nd}
    assert "killedside" in labels, "the money walk must name the wall it could not derive"
    assert "goodback" not in labels, "a located wall is never flagged not-derivable"


def test_aggregate_total_is_the_derivable_subset_and_says_which_is_missing():
    """Both halves of Howard's rule in one pin: the sum is the derivable
    faces only AND the omission is disclosed — never a subset summed in
    silence."""
    raw = _fixture()
    good_w = float(raw["walls"][1]["width_ft"])
    good_h = float(raw["walls"][1]["height_ft"])
    _null_unverified_quotes(raw)
    walk = staging.walk_walls(raw["walls"])
    # The located wall's body is in the money total...
    assert round(walk["siding_sqft"], 1) == round(good_w * good_h, 1)
    # ...and the wall the walk could not derive is NAMED, not dropped.
    assert walk["faces_not_derivable"], "a subset total must disclose its missing face"
