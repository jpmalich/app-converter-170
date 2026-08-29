"""SEND-148 PINS — A START LINE HE JUST MARKED OUTRANKS THE OLD DRAG.
(Howard ruled 2026-08-29, after SEND-147 protected his FRONT tweak too well.)

  "FRONT's tweaked body should FOLLOW the wall_base tap. A start line he just
   marked outranks the old drag. Do not clear the zone. Do not touch the
   gable. RIGHT stays refused."

The law these pins hold:
  · A HUMAN-TOUCHED **BODY** FOLLOWS THE TAP — but only its BOTTOM EDGE.
  · THE ZONE IS NOT CLEARED AND NOT RE-PLACED: his sides and his top are HIS
    evidence and they stay, so the box's height becomes HIS, and the basis
    says exactly that.
  · A TOUCHED **GABLE** OR **DORMER** IS NOT TOUCHED AT ALL.
  · NO START LINE → NOTHING FOLLOWS. Deleting the line does not drag a
    hand-moved body back; only a FRESH zone reverts.
  · A CONFIRMED BODY GOES BACK TO PROVISIONAL when its bottom moves — a
    confirmation cannot outlive the figure it was given for.
  · RIGHT STAYS REFUSED: a start line is not a licence to place a box on a
    wall nobody measured.
"""
import asyncio
import pathlib
import sys

sys.path.insert(0, "/app/backend")

from photo_zone_proposals import (  # noqa: E402
    _bottom_follows_the_line, _zone_is_human_touched, face_for_photo)

MODULE = pathlib.Path("/app/backend/photo_zone_proposals.py").read_text()

#  the FRONT shape: a box he dragged, bottom edge at y=1386.9
BODY = [{"x": 300.0, "y": 739.3}, {"x": 1969.0, "y": 739.3},
        {"x": 1969.0, "y": 1386.9}, {"x": 300.0, "y": 1386.9}]
LINE = {"y": 1450.0, "status": "provisional", "mark_id": "wb-1"}


class _Coll:
    def __init__(self):
        self.updates = []

    async def update_one(self, key, doc):
        self.updates.append((key, doc["$set"]))


class _DB:
    def __init__(self):
        self.photo_takeoff_marks = _Coll()


def _zone(part="body", status="provisional", points=None, **kw):
    return dict({"id": f"z-{part}", "label": f"AI front {part}",
                 "status": status, "human_touched": True,
                 "basis": "AI STARTING ZONE — the read measured this FRONT "
                          "face at 27.0 ft × 10.9 ft.",
                 "points": [dict(p) for p in (points or BODY)],
                 "ai": {"ref_id": f"face:front:{part}", "run_id": "r1",
                        "anchor": "first_floor_door_to_grade"}}, **kw)


def _run(db, cur, line=LINE, why="you have already moved it by hand"):
    return asyncio.get_event_loop().run_until_complete(
        _bottom_follows_the_line(db, "e", "c", cur, line, why))


def test_a_hand_moved_body_follows_the_tap_with_its_bottom_edge_only():
    db = _DB()
    note = _run(db, _zone())
    assert note and "YOUR START LINE OUTRANKS THE OLD DRAG" in note
    assert "moved from y=1386.9 px to the wall_base line you tapped" in note
    assert "(y=1450.0 px)" in note
    (key, upd), = db.photo_takeoff_marks.updates
    assert key["id"] == "z-body"
    pts = upd["points"]
    #  the two LOWEST vertices went to the line; the top two never moved
    assert sorted(round(p["y"], 1) for p in pts) == [739.3, 739.3, 1450.0, 1450.0]
    #  and not one x changed — his sides are his
    assert [p["x"] for p in pts] == [p["x"] for p in BODY]


def test_the_zone_is_not_cleared_and_not_re_placed():
    db = _DB()
    _run(db, _zone())
    (key, upd), = db.photo_takeoff_marks.updates
    #  an UPDATE on the same mark id — no delete, no insert, no new id
    assert "id" in key and "points" in upd
    assert "delete" not in MODULE.split("_bottom_follows_the_line")[1][:2500]
    #  his own basis survives and the new sentence is APPENDED
    assert upd["basis"].startswith("AI STARTING ZONE — the read measured")
    assert "your sides and your top are yours and they stayed" in upd["basis"]
    assert "this box's HEIGHT is now YOURS and not the read's" in upd["basis"]
    assert upd["ai"]["anchor"] == "wall_base_mark"
    assert upd["ai"]["anchor_wall_base_y"] == 1450.0
    assert upd["ai"]["bottom_followed_your_line"] is True
    #  the read's own claim is not rewritten
    assert upd["ai"]["run_id"] == "r1"


def test_a_touched_gable_or_dormer_is_not_touched_at_all():
    for part in ("gable", "dormer"):
        db = _DB()
        assert _run(db, _zone(part)) is None
        assert db.photo_takeoff_marks.updates == []


def test_no_start_line_means_nothing_follows():
    db = _DB()
    assert _run(db, _zone(), line=None) is None
    assert db.photo_takeoff_marks.updates == []
    #  and a bottom already ON the line is left alone — no pointless write
    db = _DB()
    on_it = [dict(p, y=1450.0) if p["y"] > 1000 else dict(p) for p in BODY]
    assert _run(db, _zone(points=on_it)) is None
    assert db.photo_takeoff_marks.updates == []


def test_a_confirmed_body_goes_back_to_provisional_when_its_bottom_moves():
    db = _DB()
    note = _run(db, _zone(status="confirmed"))
    (_, upd), = db.photo_takeoff_marks.updates
    assert upd["status"] == "provisional"
    assert upd["confirmed_at"] is None and upd["confirmed_basis"] is None
    assert upd["refused_reason"] == ("the bottom moved to the wall_base line "
                                     "you tapped — re-confirm the new figure")
    assert "a confirmation cannot outlive the figure it was given for" in note


def test_the_reason_his_hand_was_recorded_is_still_named_in_the_note():
    db = _DB()
    note = _run(db, _zone(),
                why="it was edited after it was placed (before this app "
                    "stamped hand edits), and an edit is a hand")
    assert "It was edited after it was placed" in note
    #  and the detector that produced that reason is untouched by this send
    assert _zone_is_human_touched({"status": "confirmed"})
    assert _zone_is_human_touched({"status": "provisional"}) is None


def test_right_stays_refused_even_with_a_start_line_tapped():
    run = {"run_id": "r1", "photo_paths": "p6.jpg",
           "result": {"raw_ai": {
               "photos": [{"index": 0, "elevation": "right"}],
               "walls": [{"label": "right", "width_ft": 27.0,
                          "width_ft_source": "assumed_symmetric",
                          "height_ft": 9.0, "confidence": 40}],
               "openings": [], "dormers": []},
               "measurements": {"_faces_measured": ["front", "left", "back"]}}}
    who = face_for_photo(run, "p6.jpg")
    assert who["refusal"]
    assert "this read did not measure this face" in who["refusal"]
    assert "Not measured. Not copied from another face" in who["refusal"]
    assert "no body zone, no gable zone, no dormer zone" in who["refusal"]
