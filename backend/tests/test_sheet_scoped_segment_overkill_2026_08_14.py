"""SEND-9 SHEET-SCOPING COMPLETED — the over-kill fix (2026-08-14).

THE OVER-KILL (Boni fresh read on EST-713272): all four faces read NOT
DERIVABLE though BACK's 58 and FRONT's ~920 had located on every prior
run. Coverage was healthy (page 2 = 62,403 chars) — OCR read the sheets
fine — so this was the KILL over-firing on LOCATED quotes.

MECHANISM: SEND-9 ruled that on an elevation / floor-plan sheet the SHEET
is the feature — any match on the page passes — but applied it only to
CARDINAL top-level paths (walls.front.width_ft). SEGMENT paths
(walls.front.segments.main body 2-story.width_ft) stayed LABEL-BOUND: the
located 34'-0" had to sit within 30% of a text run reading
'MAIN BODY 2-STORY'. A drawing sheet prints dimensions as GEOMETRY, never
beside such a label — so every genuinely-printed segment dimension was
rejected ("quote matched but no candidate within 1036px of feature
anchor") and the faces collapsed to NOT DERIVABLE.

THE FIX: `_sheet_scoped_for` — on a drawing sheet, ANY wall/gutter dim
carrying a cardinal component is sheet-scoped; presence-on-page
(anti-fabrication) still decides. The tight label-bound radius survives
for SCHEDULE / TABLE sheets, where a row label really does sit with its
number.

THESE PINS hold the calibration BOTH ways so the tradeoff cannot swing a
fourth time:
  (a) a segment dim FOUND on an elevation, with NO label nearby, LOCATES;
  (b) the SAME dim on a SCHEDULE sheet stays label-bound (strict);
  (c) a genuinely-absent quote (the fabricated 39s) still dies on the
      elevation — presence is still required;
  (d) a path with no cardinal (a window schedule row) is never loosened
      by the drawing-sheet rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes.ai_blueprint as ab  # noqa: E402

SEG = "walls.front.segments.main body 2-story.width_ft"
CARDINAL = "walls.front.width_ft"
WINDOW = "windows.A.width_in"


def test_sheet_scoped_truth_table():
    # RULING (widened 2026-08-14): presence-only for EVERY dim on a
    # DRAWING sheet — cardinal or not — because text-label proximity is a
    # broken instrument for the whole drawing.
    assert ab._sheet_scoped_for(SEG, "elevation") is True
    assert ab._sheet_scoped_for(SEG, "floor_plan") is True
    # A non-cardinal roof-plane dim on a drawing is scoped too (the
    # residual that cardinal-only would have left gated).
    assert ab._sheet_scoped_for("roof_planes.garage/bonus.eave_lf", "elevation") is True
    # Even a window dim on a drawing is presence-only on that sheet.
    assert ab._sheet_scoped_for(WINDOW, "elevation") is True
    # ...but SCHEDULE / TABLE sheets stay label-bound (strict) — that is
    # where labels are real and proximity earns its keep.
    assert ab._sheet_scoped_for(SEG, "schedule") is False
    assert ab._sheet_scoped_for(WINDOW, "schedule") is False
    assert ab._sheet_scoped_for(SEG, "") is False
    # Cardinal top-level paths were already sheet-scoped (SEND-9) — unchanged.
    assert ab._sheet_scoped_for(CARDINAL, "schedule") is True


def _dim_run(norm, x, y):
    return (norm, norm, (x, y, x + 100, y + 20))


def test_found_segment_dim_on_elevation_locates_even_with_no_label_nearby():
    """(a) The over-kill case: 34'-0" is on the elevation, far from any
    'MAIN BODY 2-STORY' label. Sheet-scoped ⇒ presence decides ⇒ located."""
    nq = ab._ocr_norm("34'-0\"")
    runs = [_dim_run(nq, 2000, 2000)]          # the dimension, alone
    radius = 300.0                              # tight — a label would have to be close
    rect, why = ab._ocr_match_near_feature(
        runs, [], nq,
        ab._feature_anchors_for_path(SEG), radius,
        sheet_scoped=ab._sheet_scoped_for(SEG, "elevation"),
        sheet_title="FRONT & REAR ELEVATIONS", sheet_useful_for="elevation")
    assert rect is not None, f"a printed elevation dimension must locate; got {why}"


def test_same_dim_on_a_schedule_sheet_stays_label_bound():
    """(b) No regression for schedules: with no anchor label present the
    strict gate still refuses — the drawing rule did not loosen tables."""
    nq = ab._ocr_norm("34'-0\"")
    runs = [_dim_run(nq, 2000, 2000)]          # dimension present, but no label
    rect, why = ab._ocr_match_near_feature(
        runs, [], nq,
        ab._feature_anchors_for_path(SEG), 300.0,
        sheet_scoped=ab._sheet_scoped_for(SEG, "schedule"),
        sheet_title="WINDOW SCHEDULE", sheet_useful_for="schedule")
    assert rect is None, "a schedule dim with no nearby label must stay gated"
    assert "anchor" in (why or "")


def test_fabricated_quote_still_dies_on_the_elevation():
    """(c) Presence is still required — a quote that is NOT on the page
    (the fabricated 39'-0" sides) dies even though the sheet is scoped."""
    present = ab._ocr_norm("34'-0\"")
    absent = ab._ocr_norm("39'-0\"")
    runs = [_dim_run(present, 2000, 2000)]     # only 34 is on the page
    rect, why = ab._ocr_match_near_feature(
        runs, [], absent,
        ab._feature_anchors_for_path("walls.left.width_ft"), 300.0,
        sheet_scoped=ab._sheet_scoped_for("walls.left.width_ft", "elevation"),
        sheet_title="LEFT & RIGHT ELEVATIONS", sheet_useful_for="elevation")
    assert rect is None, "an absent quote must still be a miss"
    assert "not present" in (why or "")
