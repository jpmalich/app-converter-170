"""SEND-145 PINS — THE ANCHOR WAS WRONG, THE SHAPE WAS FINE
(Howard ruled 2026-08-28, after his field run on EST-176308).

  "Placement uses 80% of photo width, near the BOTTOM OF THE PHOTO. That is
   a photo rule, not a wall rule. A yard or a patio puts the box on the
   grass. The same rule parked the dormer on the first floor."

The law these pins hold:
  · THE BODY BOTTOM IS A WALL LINE, NOT A PHOTO EDGE — it sits on the sill
    line of the LOWEST FIRST-FLOOR opening the read boxed on THAT photo.
  · THE PLANE SCALE COMES FROM ONE NAMED BOX — the BIGGEST first-floor
    opening, its own measured width against its own pixels. Nothing averaged.
  · A DORMER OPENING AND A GABLE-PEAK WINDOW SET NEITHER. The dormer opening
    is excluded outright (`on_dormer`); the gable window is dropped because
    it sits above the wall band the run's own height describes, and it is
    NAMED as dropped.
  · NO FIRST-FLOOR TYPED SIZE → the photo bottom, and the basis SAYS it is a
    photo edge and NOT a wall line. INDETERMINATE, never a silent fallback
    that looks measured.
  · THE DORMER SITS ABOVE THE BODY TOP, never at the photo bottom.
  · The starter-line / WALL-REF / corner-tick anchors stay in the code as the
    doors they will be — and they answer honestly with nothing today.
"""
import pathlib
import sys

sys.path.insert(0, "/app/backend")

from photo_zone_proposals import (  # noqa: E402
    PHOTO_BOTTOM_SENTENCE, _base_mark_line, _wall_ref_bar, build_zone_marks,
    first_floor_anchor)

MODULE = pathlib.Path("/app/backend/photo_zone_proposals.py").read_text()
W, H = 1000.0, 800.0


def _op(oid, x, y, w, h, width_in, on_dormer=False, otype="window"):
    # SEND-146 PIN UPDATE, BY NAME: the fixture now carries the `type` the live
    # opening rows have always carried, because a bottom is CLASSIFIED before
    # it is placed — a door to grade may set it, a window sill may not.
    return {"opening_id": oid, "bbox_photo_idx": 0, "width_in": width_in,
            "on_dormer": on_dormer, "type": otype,
            "bbox": {"x": x, "y": y, "w": w, "h": h}}


#  a wall 30 ft × 10 ft: a garage door (9 ft) low on the wall, a small window
#  beside it, a GABLE window up in the peak and a DORMER window.
OPENINGS = [
    _op("gd1", 0.30, 0.55, 0.18, 0.15, 108, otype="garage_door"),  # 9 ft / 180 px
    _op("w1", 0.55, 0.58, 0.05, 0.09, 30),
    _op("gable-w", 0.45, 0.18, 0.06, 0.05, 36),     # up in the peak
    _op("dormer-w", 0.62, 0.20, 0.06, 0.04, 40, on_dormer=True),
]
WALL = {"label": "front", "width_ft": 30.0, "width_ft_source": "direct_ref",
        "height_ft": 10.0, "height_ft_source": "direct_consensus",
        "confidence": 85, "gable_triangle_height_ft": 6.0,
        "dormer_face_sqft": 0}


def _run(openings=OPENINGS, walls=None, dormers=None, hints=None):
    return {"run_id": "pin145", "photo_paths": "p0.jpg",
            "result": {"raw_ai": {
                "photos": [{"index": 0, "elevation": "front"}],
                "walls": walls or [WALL],
                "openings": openings,
                "dormers": dormers or []},
                "measurements": {"_faces_measured": ["front"],
                                 "_ai_pin_gap_hints": hints or []}}}


def _box(pts):
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# THE ANCHOR ITSELF
# ---------------------------------------------------------------------------
def test_the_bottom_is_the_lowest_first_floor_sill_and_the_scale_is_the_biggest_box():
    # Howard, 2026-08-28: "Biggest opening for scale. Lowest opening for the
    # bottom." LOWEST means lowest ON THE WALL — the garage door reaches
    # nearest the grade, so its sill governs the bottom, not the little
    # window beside it whose sill sits higher.
    a = first_floor_anchor(_run(), 0, W, H, 10.0)
    assert a["bottom_from"] == "gd1"              # the lowest sill on the wall
    assert round(a["bottom_px"] / H, 3) == 0.700
    assert a["scale_from"] == "gd1"               # the biggest first-floor box
    assert a["scale_from_ft"] == 9.0 and a["scale_from_px"] == 180
    assert round(a["ppf"], 2) == 20.0
    assert a["first_floor_boxes"] == 2


def test_the_lowest_box_sets_the_bottom_even_when_another_box_sets_the_scale():
    """SEND-146 PIN UPDATE, BY NAME — the rule this pin held was CORRECTED by
    Howard's field run: the two choices are still INDEPENDENT, but a WINDOW
    dropped below the garage door no longer takes the bottom, because a window
    sill is MID-WALL. The DOOR still governs, and the ignored window is NAMED.
    The scale still comes from the biggest box, untouched."""
    low_win = _op("w-low", 0.55, 0.66, 0.05, 0.09, 30)   # sill at 0.75
    a = first_floor_anchor(_run(openings=[OPENINGS[0], low_win,
                                          OPENINGS[2], OPENINGS[3]]),
                           0, W, H, 10.0)
    assert a["bottom_from"] == "gd1"
    assert a["bottom_kind"] == "door_to_grade"
    assert a["windows_below_the_door"] == ["w-low"]
    assert round(a["bottom_px"] / H, 3) == 0.700
    assert a["scale_from"] == "gd1"
    assert round(a["ppf"], 2) == 20.0


def test_a_dormer_opening_and_a_gable_window_set_neither_and_the_drop_is_named():
    a = first_floor_anchor(_run(), 0, W, H, 10.0)
    assert a["dropped_above_the_wall_band"] == ["gable-w"]
    # the dormer opening never even reached the candidates
    assert "dormer-w" not in (a["dropped_above_the_wall_band"] or [])
    assert a["bottom_from"] != "dormer-w" and a["scale_from"] != "dormer-w"
    body = build_zone_marks(_run(), "front", WALL, "p0.jpg", W, H, "e", "c", None)[0]
    assert "Dropped above the wall band (not first floor): gable-w" in body["basis"]


def test_the_scale_is_one_named_box_never_an_average():
    body = build_zone_marks(_run(), "front", WALL, "p0.jpg", W, H, "e", "c", None)[0]
    assert "SCALE from 'gd1' (9.0 ft wide, 180 px on this photo)" in body["basis"]
    assert "no scale is averaged" in body["basis"]
    assert body["ai"]["px_per_ft"] == 20.0
    for banned in ("mean(", "sum(", "statistics", "/ len("):
        assert banned not in MODULE, banned


def test_the_body_bottom_is_a_wall_line_and_says_to_pull_it_to_the_start_line():
    body = build_zone_marks(_run(), "front", WALL, "p0.jpg", W, H, "e", "c", None)[0]
    x0, y0, x1, y1 = _box(body["points"])
    assert round(y1 / H, 3) == 0.700              # the sill line, not 0.92
    assert round((y1 - y0) / 20.0, 2) == 10.0     # 10 ft at the plane scale
    assert round((x1 - x0) / 20.0, 2) == 30.0     # 30 ft at the plane scale
    assert "BOTTOM anchored to the sill line of 'gd1'" in body["basis"]
    assert "the wall BASE is not marked here" in body["basis"]
    assert "pull it down to the start line" in body["basis"]
    # SEND-146 PIN UPDATE, BY NAME: the value now names WHICH kind of opening
    # the bottom came from — a door to grade, never just "an opening".
    assert body["ai"]["anchor"] == "first_floor_door_to_grade"


def test_the_gable_stacks_on_the_body_top_in_the_bodys_own_scale():
    marks = build_zone_marks(_run(), "front", WALL, "p0.jpg", W, H, "e", "c", None)
    body, gable = marks[0], marks[1]
    _, by0, _, _ = _box(body["points"])
    peak = min(p["y"] for p in gable["points"])
    assert round((by0 - peak) / 20.0, 2) == 6.0   # the run's own 6 ft rise
    assert max(p["y"] for p in gable["points"]) == by0


def test_the_dormer_sits_above_the_body_top_and_never_at_the_photo_bottom():
    wall = dict(WALL, gable_triangle_height_ft=0, dormer_face_sqft=47.6)
    run = _run(walls=[wall],
               dormers=[{"face": "front", "width_ft": 14.0,
                         "knee_wall_height_ft": 3.5,
                         "width_source": "direct_consensus"}])
    marks = build_zone_marks(run, "front", wall, "p0.jpg", W, H, "e", "c", None)
    body = marks[0]
    dormer = [m for m in marks if m["kind"] == "dormer"][0]
    _, by0, _, by1 = _box(body["points"])
    _, dy0, _, dy1 = _box(dormer["points"])
    assert dy1 == by0                            # it stands ON the body top
    assert dy0 < by0 and dy1 < by1               # entirely above the body
    assert round((dy1 - dy0) / 20.0, 2) == 3.5   # the run's own knee wall
    assert "ABOVE THE BODY TOP" in dormer["basis"]
    assert "never at the photo bottom" in dormer["basis"]


# ---------------------------------------------------------------------------
# WHEN THERE IS NOTHING TO ANCHOR TO, IT SAYS SO
# ---------------------------------------------------------------------------
def test_no_first_floor_typed_size_falls_back_and_calls_itself_indeterminate():
    run = _run(openings=[_op("dormer-w", 0.6, 0.2, 0.06, 0.04, 40,
                             on_dormer=True)])
    assert first_floor_anchor(run, 0, W, H, 10.0) is None
    body = build_zone_marks(run, "front", WALL, "p0.jpg", W, H, "e", "c", None)[0]
    assert PHOTO_BOTTOM_SENTENCE in body["basis"]
    assert "INDETERMINATE" in body["basis"]
    assert "NOT a wall line" in body["basis"]
    assert body["ai"]["anchor"] == "photo_bottom_indeterminate"
    _, _, _, y1 = _box(body["points"])
    assert round(y1 / H, 2) == 0.92               # the old rule, now NAMED


def test_a_box_with_no_size_is_never_used_for_scale():
    run = _run(openings=[_op("gd1", 0.3, 0.55, 0.18, 0.15, 108,
                             otype="garage_door"),
                         _op("untyped", 0.5, 0.60, 0.30, 0.12, 0)])
    a = first_floor_anchor(run, 0, W, H, 10.0)
    assert a["scale_from"] == "gd1"               # the untyped box is ignored
    assert a["bottom_from"] == "gd1"


def test_the_other_two_anchors_are_doors_that_answer_honestly_today():
    assert _base_mark_line([]) is None
    assert _wall_ref_bar(_run(), 0) is None
    assert "would be" in MODULE and "circular" in MODULE
    assert "writes no pixel geometry for it" in MODULE
    # the ruled order is written down where the code can be read
    for line in ("the starter-candidate / wall-base MARK",
                 "the WALL REF bar", "FIRST-FLOOR OPENING BOXES",
                 "else the photo bottom"):
        assert line in MODULE, line


def test_a_wall_that_does_not_fit_the_frame_is_cut_and_says_so():
    wide = dict(WALL, width_ft=90.0)              # 90 ft at 20 px/ft = 1800 px
    body = build_zone_marks(_run(walls=[wide]), "front", wide, "p0.jpg", W, H,
                            "e", "c", None)[0]
    x0, _, x1, _ = _box(body["points"])
    assert x0 >= 0 and x1 <= W                    # cut at the frame
    assert "does not fit the frame" in body["basis"]
    assert "the sides run past the frame edge" in body["basis"]
    assert "move the sides onto what you can actually see" in body["basis"]


def test_the_placement_is_still_never_called_a_measurement():
    body = build_zone_marks(_run(), "front", WALL, "p0.jpg", W, H, "e", "c", None)[0]
    assert "NOT a measurement" in body["basis"]
    assert body["status"] == "provisional"
    assert body["origin"] == "ai_zone_proposal"
