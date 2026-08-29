"""SEND-146 PINS — A WINDOW SILL IS MID-WALL (Howard ruled 2026-08-28, after
his field run on SEND-145's boxes).

  BACK  — close, the patio-door sill is near the start line.
  FRONT — bottom at grade, garage doors.
  LEFT  — WRONG. The bottom sat on the DH window sills and the wall from the
          starter up to those sills was outside the box.
  RIGHT — still empty. Correct.

The law these pins hold:
  · CLASSIFY, THEN PLACE. The bottom is decided by the opening row's OWN
    `type`: a DOOR TO GRADE may set it, a WINDOW may not, and `style` never
    promotes a window (a "2-Lite Slider" WINDOW is a window).
  · A DOOR GOVERNS EVEN WHEN A WINDOW SITS LOWER, and the ignored window is
    NAMED on the row.
  · NO DOOR TO GRADE → the bottom is INDETERMINATE and says so in the basis:
    "no door-to-grade opening on this photo — bottom is not a wall line".
    The box keeps its TOP and its WIDTH.
  · NO DROP FROM A SILL AND NO TYPICAL SILL HEIGHT — not a constant, not a
    fraction, not a fallback.
  · THE SCALE IS UNTOUCHED: a window is an honest RULER even when it is not a
    FLOOR. The biggest first-floor box still sets px-per-foot.
  · THERE IS NO NEW DETECTOR. The module reads `type` and nothing else.
"""
import pathlib
import sys

sys.path.insert(0, "/app/backend")

from photo_zone_proposals import (  # noqa: E402
    DOOR_TO_GRADE_TYPES, WINDOW_SILL_SENTENCE, _is_door_to_grade,
    build_zone_marks, first_floor_anchor)

MODULE = pathlib.Path("/app/backend/photo_zone_proposals.py").read_text()
W, H = 1000.0, 800.0


def _op(oid, x, y, w, h, width_in, otype="window", style="", on_dormer=False):
    return {"opening_id": oid, "bbox_photo_idx": 0, "width_in": width_in,
            "type": otype, "style": style, "on_dormer": on_dormer,
            "bbox": {"x": x, "y": y, "w": w, "h": h}}


WALL = {"label": "left", "width_ft": 30.0, "width_ft_source": "direct_ref",
        "height_ft": 8.4, "height_ft_source": "direct_consensus",
        "confidence": 82, "gable_triangle_height_ft": 0,
        "dormer_face_sqft": 0}

#  THE LEFT SHAPE, in miniature: three Double Hung windows and nothing else.
DH_ONLY = [
    _op("dh1", 0.20, 0.50, 0.06, 0.15, 30, style="Double Hung"),
    _op("dh2", 0.45, 0.50, 0.06, 0.14, 30, style="Double Hung"),
    _op("dh3", 0.70, 0.48, 0.07, 0.13, 30, style="Double Hung"),
]
#  THE FRONT SHAPE: a garage door at grade, plus a window whose sill is LOWER.
DOOR_PLUS_LOW_WINDOW = [
    _op("gd1", 0.20, 0.50, 0.18, 0.20, 108, otype="garage_door"),  # sill 0.70
    _op("w-low", 0.55, 0.60, 0.05, 0.15, 30, style="Double Hung"),  # sill 0.75
]


def _run(openings, wall=None, elev="left"):
    return {"run_id": "pin146", "photo_paths": "p0.jpg",
            "result": {"raw_ai": {
                "photos": [{"index": 0, "elevation": elev}],
                "walls": [dict(wall or WALL, label=elev)],
                "openings": openings, "dormers": []},
                "measurements": {"_faces_measured": [elev]}}}


def _body(openings, wall=None, elev="left"):
    w = dict(wall or WALL, label=elev)
    return build_zone_marks(_run(openings, wall, elev), elev, w, "p0.jpg",
                            W, H, "e", "c", None)[0]


def _box(pts):
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# ITEM 1 — CLASSIFY
# ---------------------------------------------------------------------------
def test_the_classifier_reads_the_rows_own_type_and_style_never_promotes():
    assert _is_door_to_grade({"type": "garage_door"})
    assert _is_door_to_grade({"type": "entry_door"})
    assert _is_door_to_grade({"type": "patio_door", "style": "2-Lite Slider"})
    #  a WINDOW is a window whatever its style says
    assert not _is_door_to_grade({"type": "window", "style": "2-Lite Slider"})
    assert not _is_door_to_grade({"type": "window", "style": "Slider Door"})
    assert not _is_door_to_grade({"type": "window", "style": "Double Hung"})
    #  an unrecognised or missing type is NOT a door — it falls to
    #  indeterminate, never to a guess
    assert not _is_door_to_grade({"type": "transom", "style": ""})
    assert not _is_door_to_grade({})
    assert "window" not in DOOR_TO_GRADE_TYPES


def test_there_is_no_new_detector_and_no_sill_height_convention():
    for banned in ("sill_height", "typical_sill", "SILL_DROP", "sill_drop",
                   "SILL_HEIGHT_FT", "3.0  # sill", "detect_door"):
        assert banned not in MODULE, banned
    #  the classifier is one read of `type`; style is never consulted there
    fn = MODULE.split("def _is_door_to_grade")[1].split("def ")[0]
    code = [l for l in fn.splitlines() if l.strip().startswith("return")]
    assert code and 'o.get("type")' in code[0]
    assert 'o.get("style")' not in fn        # style never reaches the decision


# ---------------------------------------------------------------------------
# ITEM 2 — THE BOTTOM RULE
# ---------------------------------------------------------------------------
def test_a_door_to_grade_sets_the_bottom_and_is_named_by_type():
    a = first_floor_anchor(_run(DOOR_PLUS_LOW_WINDOW), 0, W, H, 8.4)
    assert a["bottom_kind"] == "door_to_grade"
    assert a["bottom_from"] == "gd1" and a["bottom_type"] == "garage_door"
    assert round(a["bottom_px"] / H, 3) == 0.700
    basis = _body(DOOR_PLUS_LOW_WINDOW)["basis"]
    assert "BOTTOM anchored to the sill line of 'gd1'" in basis
    assert "a DOOR TO GRADE (garage_door)" in basis


def test_a_window_sitting_lower_than_the_door_does_not_take_the_bottom_and_is_named():
    a = first_floor_anchor(_run(DOOR_PLUS_LOW_WINDOW), 0, W, H, 8.4)
    assert a["windows_below_the_door"] == ["w-low"]
    basis = _body(DOOR_PLUS_LOW_WINDOW)["basis"]
    assert "A window sill is MID-WALL and set nothing here: w-low" in basis
    #  and the box does NOT reach that window's sill
    _, _, _, y1 = _box(_body(DOOR_PLUS_LOW_WINDOW)["points"])
    assert round(y1 / H, 3) == 0.700


def test_windows_only_means_the_bottom_is_indeterminate_and_says_so():
    a = first_floor_anchor(_run(DH_ONLY), 0, W, H, 8.4)
    assert a["bottom_kind"] == "window_sill_indeterminate"
    assert a["bottom_from"] is None            # nothing is NAMED as the bottom
    assert a["bottom_sill_of"] == "dh1"        # what it happens to rest on
    assert a["doors_to_grade"] is None
    body = _body(DH_ONLY)
    assert WINDOW_SILL_SENTENCE in body["basis"]
    assert "no door-to-grade opening on this photo" in body["basis"]
    assert "bottom is not a wall line" in body["basis"]
    assert "A WINDOW SILL IS MID-WALL" in body["basis"]
    assert "No drop from a sill is invented and no typical sill height is used" \
        in body["basis"]
    assert body["ai"]["anchor"] == "window_sill_indeterminate"
    assert body["ai"]["anchor_bottom_from"] is None
    assert body["ai"]["anchor_bottom_sill_of"] == "dh1"


def test_the_indeterminate_box_keeps_its_top_and_its_width():
    """Ruled: keep the current box top and width. Nothing is dropped, nothing
    is stretched to the photo edge, and the ft² shape is still the read's."""
    body = _body(DH_ONLY)
    x0, y0, x1, y1 = _box(body["points"])
    ppf = body["ai"]["px_per_ft"]
    assert round((x1 - x0) / ppf, 2) == 30.0        # the read's width
    assert round((y1 - y0) / ppf, 2) == 8.4         # the read's height
    assert round(y1 / H, 3) == 0.650                # dh1's sill, and only that
    assert y1 < H                                   # never the photo edge


def test_the_scale_is_untouched_a_window_is_a_ruler_even_when_it_is_not_a_floor():
    a = first_floor_anchor(_run(DH_ONLY), 0, W, H, 8.4)
    assert a["scale_from"] == "dh3"                  # the biggest DH box
    assert a["scale_from_ft"] == 2.5 and a["scale_from_px"] == 70
    assert round(a["ppf"], 2) == 28.0
    assert "SCALE from 'dh3'" in _body(DH_ONLY)["basis"]
    assert "no scale is averaged" in _body(DH_ONLY)["basis"]


def test_no_first_floor_opening_at_all_is_still_the_photo_bottom_answer():
    from photo_zone_proposals import PHOTO_BOTTOM_SENTENCE
    run = _run([_op("dw1", 0.5, 0.2, 0.06, 0.04, 40, on_dormer=True)])
    assert first_floor_anchor(run, 0, W, H, 8.4) is None
    body = _body([_op("dw1", 0.5, 0.2, 0.06, 0.04, 40, on_dormer=True)])
    assert PHOTO_BOTTOM_SENTENCE in body["basis"]
    assert body["ai"]["anchor"] == "photo_bottom_indeterminate"


def test_a_refused_face_still_gets_nothing_a_better_bottom_is_not_a_licence():
    from photo_zone_proposals import face_for_photo
    run = _run(DH_ONLY)
    run["result"]["raw_ai"]["walls"][0]["width_ft_source"] = "assumed_symmetric"
    who = face_for_photo(run, "p0.jpg")
    assert who["refusal"] and "assumed_symmetric" in who["refusal"]
    assert "no body zone, no gable zone, no dormer zone" in who["refusal"]


def test_the_placement_is_still_never_called_a_measurement():
    body = _body(DH_ONLY)
    assert "NOT a measurement" in body["basis"]
    assert body["status"] == "provisional"
    assert body["origin"] == "ai_zone_proposal"


def test_the_starter_candidate_line_still_stores_no_geometry_to_anchor_to():
    """SEND-147 PIN UPDATE, BY NAME. This pin was written to FAIL the day the
    start line became real — Howard picked option 2 and it is real now, so the
    pin holds the part that is still true: the RENDERED candidate edge still
    carries no geometry, and the placer still does not read it back (that
    would be circular). What the placer reads is the TAPPED `wall_base` MARK,
    which has its own stored y."""
    jsx = pathlib.Path(
        "/app/frontend/src/components/estimate/phototakeoff/CandidateEdges.jsx"
    ).read_text()
    assert 'word: "starter candidate", a: bl, b: br' in jsx
    assert "no length, no LF, no key written" in jsx
    #  the placer never reads the DRAWN candidate edge back
    assert "starter_candidate" not in MODULE
    assert "circular" in MODULE
    #  it reads the TAPPED mark instead — anchor rung 1, real as of SEND-147
    assert "wall_base" in MODULE and "BEATS the door sill" in MODULE
