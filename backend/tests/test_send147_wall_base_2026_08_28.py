"""SEND-147 PINS — THE WALL-BASE MARK. HUMAN TWO-TAP, NO DETECTOR.
(Howard picked option 2 on 2026-08-28.)

  "The start line gets its own stored y. That y is the body bottom when it
   exists."

The law these pins hold:
  · IT IS A HUMAN GESTURE, the same two-tap as the scale, on THAT photo only:
    tap 1 = the LEFT end of the starter / wall base, tap 2 = the RIGHT end.
  · IT STORES `a`, `b` AND `y` in that photo's own natural pixels.
  · IT WRITES NO LF AND NO PRICE — this send is an ANCHOR, not a trim
    takeoff. The phase-2 `starter` RUN stays unbuilt and still refuses.
  · WHEN IT EXISTS IT BEATS THE DOOR SILL AND IT BEATS
    WINDOW-INDETERMINATE. The basis says "bottom from wall_base mark on this
    photo".
  · WHEN IT DOES NOT EXIST, SEND-146 IS UNCHANGED.
  · NO AI STARTER FINDER. No corner tick, no eave, no soffit, no fascia.
  · IT IS NEVER COPIED FROM ANOTHER PHOTO OR ANOTHER FACE.
  · A HUMAN-TOUCHED BODY STAYS PUT. A fresh provisional body may move.
"""
import pathlib
import sys

sys.path.insert(0, "/app/backend")

from photo_zone_proposals import (  # noqa: E402
    _base_mark_line, build_zone_marks, first_floor_anchor)
from routes.photo_takeoff import (  # noqa: E402
    ANCHOR_KINDS, KIND_POINTS, PHASE1_KINDS, PHASE2_KINDS, WALL_BASE_BASIS,
    _wall_base_record)

MODULE = pathlib.Path("/app/backend/photo_zone_proposals.py").read_text()
ROUTES = pathlib.Path("/app/backend/routes/photo_takeoff.py").read_text()
EDITOR = pathlib.Path(
    "/app/frontend/src/components/estimate/PhotoTakeoffEditor.jsx").read_text()
VOCAB = pathlib.Path(
    "/app/frontend/src/components/estimate/phototakeoff/marks.js").read_text()

W, H = 1000.0, 800.0


def _op(oid, x, y, w, h, width_in, otype="window", style="", on_dormer=False):
    return {"opening_id": oid, "bbox_photo_idx": 0, "width_in": width_in,
            "type": otype, "style": style, "on_dormer": on_dormer,
            "bbox": {"x": x, "y": y, "w": w, "h": h}}


#  THE LEFT SHAPE: three Double Hung windows, no door to grade.
DH_ONLY = [
    _op("dh1", 0.20, 0.50, 0.06, 0.15, 30, style="Double Hung"),
    _op("dh2", 0.45, 0.50, 0.06, 0.14, 30, style="Double Hung"),
    _op("dh3", 0.70, 0.48, 0.07, 0.13, 30, style="Double Hung"),
]
#  THE FRONT SHAPE: a garage door at grade.
WITH_DOOR = [
    _op("gd1", 0.20, 0.50, 0.18, 0.20, 108, otype="garage_door"),   # sill 0.70
    _op("w1", 0.55, 0.52, 0.05, 0.10, 30, style="Double Hung"),
]
WALL = {"label": "left", "width_ft": 30.0, "width_ft_source": "direct_ref",
        "height_ft": 8.4, "height_ft_source": "direct_consensus",
        "confidence": 82, "gable_triangle_height_ft": 0, "dormer_face_sqft": 0}


def _run(openings, elev="left"):
    return {"run_id": "pin147", "photo_paths": "p0.jpg",
            "result": {"raw_ai": {
                "photos": [{"index": 0, "elevation": elev}],
                "walls": [dict(WALL, label=elev)],
                "openings": openings, "dormers": []},
                "measurements": {"_faces_measured": [elev]}}}


def _mark(y_left, y_right=None, status="provisional", kind="wall_base",
          updated="2026-08-28T20:00:00+00:00"):
    pts = [{"x": 60.0, "y": float(y_left)},
           {"x": 940.0, "y": float(y_right if y_right is not None else y_left)}]
    return {"id": f"wb-{y_left}-{status}", "kind": kind, "status": status,
            "points": pts, "wall_base": _wall_base_record(pts),
            "updated_at": updated}


def _body(openings, base_mark=None, elev="left"):
    w = dict(WALL, label=elev)
    return build_zone_marks(_run(openings, elev), elev, w, "p0.jpg", W, H,
                            "e", "c", None, base_mark=base_mark)[0]


def _box(pts):
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# WHAT IT IS — THE MARK RECORD
# ---------------------------------------------------------------------------
def test_the_record_stores_a_and_b_and_its_own_y_in_this_photos_pixels():
    rec = _wall_base_record([{"x": 940.0, "y": 604.0}, {"x": 60.0, "y": 600.0}])
    #  `a` is ALWAYS the left end, whichever way the taps went
    assert rec["a"] == {"x": 60.0, "y": 600.0}
    assert rec["b"] == {"x": 940.0, "y": 604.0}
    assert rec["y"] == 602.0                     # the mean of the two ends
    assert rec["tilt_px"] == 4.0                 # and the tilt is REPORTED
    assert rec["units"] == "natural pixels of this photo"


def test_it_is_a_phase_one_two_tap_mark_and_the_starter_run_stays_unbuilt():
    assert ANCHOR_KINDS == {"wall_base"}
    assert "wall_base" in PHASE1_KINDS
    assert KIND_POINTS["wall_base"] == 2         # exactly two ends, ever
    #  the phase-2 STARTER RUN is a different thing and it is still refused
    assert "starter" in PHASE2_KINDS
    assert "wall_base" not in PHASE2_KINDS
    #  the two ends are asked for by name
    assert "the LEFT end of the wall base, then the RIGHT end" in ROUTES


def test_it_carries_no_lf_and_no_price_anywhere():
    assert "no LF is written" in WALL_BASE_BASIS
    assert "never priced" in WALL_BASE_BASIS
    assert "ANCHOR" in WALL_BASE_BASIS
    #  no lineal figure is COMPUTED for it — checked on the CODE, not the words
    wb = ROUTES.split("def _wall_base_record")[1].split("WALL_BASE_BASIS")[0]
    code = wb.split('"""')[2] if wb.count('"""') >= 2 else wb
    for banned in ("lineal", "price", "cost", "hypot", "span_px"):
        assert banned not in code.lower(), banned
    assert "anchor · no LF" in EDITOR


def test_the_gesture_is_the_two_tap_and_the_tool_exists_with_its_own_words():
    assert 'Tap the LEFT end of the starter / wall base.' in VOCAB
    assert 'Tap the RIGHT end to finish the start line.' in VOCAB
    assert '{ key: "wall_base", label: "Wall base"' in EDITOR
    assert 'addMark([pts[0], p], "line")' in EDITOR
    assert "an ANCHOR for the AI body bottom, never an LF run" in EDITOR


# ---------------------------------------------------------------------------
# WHAT IT DOES
# ---------------------------------------------------------------------------
def test_the_mark_beats_the_window_indeterminate_answer():
    #  without the mark: SEND-146's indeterminate answer, unchanged
    before = _body(DH_ONLY)
    assert before["ai"]["anchor"] == "window_sill_indeterminate"
    #  with it: the tapped y IS the bottom
    after = _body(DH_ONLY, _base_mark_line([_mark(700.0)]))
    assert after["ai"]["anchor"] == "wall_base_mark"
    assert after["ai"]["anchor_wall_base_y"] == 700.0
    assert "bottom from wall_base mark on this photo" in after["basis"]
    _, _, _, y1 = _box(after["points"])
    assert round(y1, 1) == 700.0
    #  and it DROPPED from the DH sill line, which is the whole point
    assert y1 > _box(before["points"])[3]


def test_the_mark_beats_the_door_sill_too():
    door = _body(WITH_DOOR, None, "front")
    assert door["ai"]["anchor"] == "first_floor_door_to_grade"
    assert round(_box(door["points"])[3], 1) == 560.0        # gd1's sill
    tapped = _body(WITH_DOOR, _base_mark_line([_mark(612.0)]), "front")
    assert tapped["ai"]["anchor"] == "wall_base_mark"
    assert round(_box(tapped["points"])[3], 1) == 612.0
    assert "beats every opening: an opening sill is not the wall base" \
        in tapped["basis"]


def test_the_scale_still_comes_from_the_read_never_from_the_start_line():
    """A start line says WHERE the wall ends, never HOW BIG a foot is."""
    a = first_floor_anchor(_run(DH_ONLY), 0, W, H, 8.4)
    tapped = _body(DH_ONLY, _base_mark_line([_mark(700.0)]))
    assert tapped["ai"]["px_per_ft"] == round(a["ppf"], 2) == 28.0
    assert "SCALE from 'dh3'" in tapped["basis"]
    assert tapped["ai"]["anchor_scale_from"] == "dh3"
    #  the shape is still the read's own figures at that scale
    x0, y0, x1, y1 = _box(tapped["points"])
    assert round((x1 - x0) / 28.0, 2) == 30.0
    assert round((y1 - y0) / 28.0, 2) == 8.4


def test_no_mark_leaves_send146_exactly_as_it_was():
    assert _base_mark_line([]) is None
    assert _base_mark_line(None) is None
    assert _body(DH_ONLY, None)["ai"]["anchor"] == "window_sill_indeterminate"
    assert _body(WITH_DOOR, None, "front")["ai"]["anchor"] \
        == "first_floor_door_to_grade"


def test_a_refused_line_is_not_an_anchor_and_confirmed_outranks_provisional():
    assert _base_mark_line([_mark(700.0, status="refused")]) is None
    both = _base_mark_line([_mark(700.0), _mark(650.0, status="confirmed")])
    assert both["y"] == 650.0 and both["status"] == "confirmed"
    #  among equals the LATEST tap governs — his most recent word
    later = _base_mark_line([
        _mark(700.0, updated="2026-08-28T20:00:00+00:00"),
        _mark(690.0, updated="2026-08-28T21:00:00+00:00")])
    assert later["y"] == 690.0


def test_a_mark_of_another_kind_is_never_read_as_a_start_line():
    assert _base_mark_line([_mark(700.0, kind="siding_zone")]) is None
    assert _base_mark_line([_mark(700.0, kind="starter")]) is None


# ---------------------------------------------------------------------------
# WHAT IT MUST NOT DO
# ---------------------------------------------------------------------------
def test_there_is_no_ai_starter_finder_and_no_new_trim_marks_in_this_send():
    for banned in ("find_starter", "detect_starter", "starter_finder",
                   "corner_tick", "eave_mark", "soffit_mark", "fascia_mark"):
        assert banned not in MODULE and banned not in ROUTES, banned
    #  the anchor is a READ of a stored mark, not a search of the photo
    fn = MODULE.split("def _base_mark_line")[1].split("\ndef ")[0]
    assert 'm.get("kind") != "wall_base"' in fn
    assert "cv2" not in fn and "numpy" not in fn


def test_it_is_never_copied_from_another_photo_or_another_face():
    #  the placer is handed ONE photo's marks and the query names that photo
    assert '"photo_key": photo_key' in MODULE
    assert "never copied to another photo or another face" in ROUTES
    fn = MODULE.split("def _base_mark_line")[1].split("\ndef ")[0]
    assert "photo_key" not in fn      # it cannot even see another photo's key


def test_a_human_touched_body_stays_and_a_hand_on_a_mark_is_recorded():
    from photo_zone_proposals import _zone_is_human_touched as touched
    assert 'upd["human_touched"] = True' in ROUTES
    assert "human_touched" in MODULE
    #  the refusal to move is NAMED, and it tells him what to do instead
    assert "outranks the anchor" in MODULE
    assert "re-placed on the line you tapped" in MODULE
    #  a fresh AI placement is NOT touched
    assert touched({"status": "provisional",
                    "created_at": "2026-08-28T20:00:00.100000+00:00",
                    "updated_at": "2026-08-28T20:00:00.400000+00:00"}) is None
    #  a stamped hand edit is
    assert touched({"status": "provisional", "human_touched": True}) \
        == "you have already moved it by hand"
    #  so is a ruling
    assert "confirmed, not provisional" in touched({"status": "confirmed"})
    #  AND SO IS A DRAG FROM BEFORE THE STAMP EXISTED — Howard tweaked FRONT's
    #  edges then, and the clock is the only witness those drags left
    assert "an edit is a hand" in touched({
        "status": "provisional",
        "created_at": "2026-08-28T16:40:00+00:00",
        "updated_at": "2026-08-28T18:12:00+00:00"})
    #  the machine's own re-base is never mistaken for a hand
    assert touched({"status": "provisional",
                    "created_at": "2026-08-28T16:40:00+00:00",
                    "rebased_at": "2026-08-29T03:00:00+00:00",
                    "updated_at": "2026-08-29T03:00:00+00:00"}) is None


def test_the_zone_is_still_provisional_and_still_not_a_measurement():
    body = _body(DH_ONLY, _base_mark_line([_mark(700.0)]))
    assert body["status"] == "provisional"
    assert body["origin"] == "ai_zone_proposal"
    assert "NOT a measurement" in body["basis"]


def test_the_tap_itself_moves_the_box_and_never_places_a_new_zone():
    """Howard's test is a TAP, not a button press: the moment the start line
    lands, a fresh provisional body drops to it. A REBASE places nothing —
    tapping a line on a photo with no zones leaves that photo empty."""
    assert "async def rebase_zones_for_photo" in MODULE
    assert "place_new=False" in MODULE
    assert "NOTHING NEW IS PLACED" in MODULE
    fn = MODULE.split("def propose_zones_for_photo")[1].split("\nasync def ")[0]
    assert "if place_new:\n                made.append(m)" in fn
    #  create, move and delete of a wall_base all re-base that photo
    assert ROUTES.count("await rebase_zones_for_photo(") == 3
    assert 'if body.kind == "wall_base" else None' in ROUTES
    assert 'if cur.get("kind") == "wall_base" else None' in ROUTES
    assert 'if (cur or {}).get("kind") == "wall_base" else None' in ROUTES
    #  a plain re-pull with no start line still overwrites nothing
    assert "if base_mark is None and place_new:" in MODULE
    #  and the editor says out loud what moved
    assert "provisional zone(s) dropped to it" in EDITOR


def test_a_refused_face_gets_nothing_even_with_a_start_line_tapped():
    from photo_zone_proposals import face_for_photo
    run = _run(DH_ONLY)
    run["result"]["raw_ai"]["walls"][0]["width_ft_source"] = "assumed_symmetric"
    who = face_for_photo(run, "p0.jpg")
    assert who["refusal"] and "assumed_symmetric" in who["refusal"]
    assert "no body zone, no gable zone, no dormer zone" in who["refusal"]
