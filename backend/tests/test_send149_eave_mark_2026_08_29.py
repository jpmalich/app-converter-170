"""SEND-149 PINS — THE EAVE MARK. HUMAN TWO-TAP, SAME PATTERN AS WALL_BASE.
(Howard ruled 2026-08-29, after his field check: Left / Front / Back bottoms
sit on the starter he tapped, lawn out, Left dormer on the bump-out, Right
empty. "The top now gets the same kind of evidence.")

The law these pins hold:
  · kind `eave`, shape `line`, PHASE 1, EXACTLY 2 points — the LEFT end of
    the eave / frieze, then the RIGHT end.
  · It belongs to ONE photo_key and is never read for another photo or face.
  · It stores `a`, `b`, `y` (the mean of the two ends) and `tilt_px`, so a
    sloped tap is REPORTED, not hidden. It lands PROVISIONAL.
  · NO LF. NO PRICE. NO LENGTH. It is not a soffit and it is not a fascia —
    neither run is built.
  · WHEN IT EXISTS IT SETS THE BODY TOP: "top from eave mark on this photo —
    the frieze YOU tapped." The bottom does NOT move and not one x changes.
  · A HAND-MOVED BODY FOLLOWS THE EAVE TAP ON ITS TOP, exactly as SEND-148
    ruled for the bottom, and a CONFIRMED body drops back to PROVISIONAL.
  · NO EAVE MARK → THE TOP STAYS EXACTLY AS IT IS.
  · NO AI EAVE FINDER. No soffit, fascia, corner tick or J-channel.
  · THE GABLE AND THE DORMER ARE NOT RESHAPED. If the new top crosses a
    dormer it is REPORTED, never auto-fixed.
  · RIGHT STAYS REFUSED.
"""
import asyncio
import pathlib
import sys

sys.path.insert(0, "/app/backend")

from photo_zone_proposals import (  # noqa: E402
    _edge_follows_the_line, _eave_mark_line, build_zone_marks)
from routes.photo_takeoff import (  # noqa: E402
    ANCHOR_KINDS, EAVE_BASIS, KIND_POINTS, PHASE1_KINDS, PHASE2_KINDS,
    _trim_rows, _wall_base_record)

MODULE = pathlib.Path("/app/backend/photo_zone_proposals.py").read_text()
ROUTES = pathlib.Path("/app/backend/routes/photo_takeoff.py").read_text()
EDITOR = pathlib.Path(
    "/app/frontend/src/components/estimate/PhotoTakeoffEditor.jsx").read_text()
VOCAB = pathlib.Path(
    "/app/frontend/src/components/estimate/phototakeoff/marks.js").read_text()

W, H = 1000.0, 800.0
IPP = 0.05


def _op(oid, x, y, w, h, width_in, otype="garage_door"):
    return {"opening_id": oid, "bbox_photo_idx": 0, "width_in": width_in,
            "type": otype, "style": "", "on_dormer": False,
            "bbox": {"x": x, "y": y, "w": w, "h": h}}


DOOR = [_op("gd1", 0.20, 0.50, 0.18, 0.20, 108)]            # sill at 0.70
WALL = {"label": "front", "width_ft": 25.0, "width_ft_source": "direct_ref",
        "height_ft": 10.0, "height_ft_source": "direct_consensus",
        "confidence": 82, "gable_triangle_height_ft": 0, "dormer_face_sqft": 0}


def _run():
    return {"run_id": "pin149", "photo_paths": "p0.jpg",
            "result": {"raw_ai": {
                "photos": [{"index": 0, "elevation": "front"}],
                "walls": [dict(WALL)], "openings": DOOR, "dormers": []},
                "measurements": {"_faces_measured": ["front"]}}}


def _line(y, kind="eave", status="provisional", tilt=0.0):
    pts = [{"x": 60.0, "y": float(y) - tilt / 2}, {"x": 940.0, "y": float(y) + tilt / 2}]
    return {"id": f"{kind}-{y}", "kind": kind, "status": status,
            "points": pts, kind: _wall_base_record(pts),
            "updated_at": "2026-08-29T13:00:00+00:00"}


def _body(eave=None):
    return build_zone_marks(_run(), "front", dict(WALL), "p0.jpg", W, H,
                            "e", "c", None, eave_mark=eave)[0]


def _box(pts):
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


class _Coll:
    def __init__(self):
        self.updates = []

    async def update_one(self, key, doc):
        self.updates.append((key, doc["$set"]))


class _DB:
    def __init__(self):
        self.photo_takeoff_marks = _Coll()


BODY_PTS = [{"x": 300.0, "y": 300.0}, {"x": 900.0, "y": 300.0},
            {"x": 900.0, "y": 700.0}, {"x": 300.0, "y": 700.0}]


def _zone(part="body", status="provisional", points=None):
    return {"id": f"z-{part}", "label": f"AI front {part}", "status": status,
            "human_touched": True, "basis": "AI STARTING ZONE — 30.0 ft × 10.0 ft.",
            "points": [dict(p) for p in (points or BODY_PTS)],
            "ai": {"ref_id": f"face:front:{part}", "run_id": "r1"}}


def _follow(db, cur, mark, edge="top", why="you have already moved it by hand"):
    line = _eave_mark_line([mark]) if mark else None
    return asyncio.run(_edge_follows_the_line(db, "e", "c", cur, line, why, edge))


# ---------------------------------------------------------------------------
# WHAT IT IS — THE MARK RECORD
# ---------------------------------------------------------------------------
def test_it_is_a_phase_one_two_tap_line_and_no_run_was_built():
    assert ANCHOR_KINDS == {"wall_base", "eave"}
    assert "eave" in PHASE1_KINDS and KIND_POINTS["eave"] == 2
    #  the RUNS stay in phase 2 and stay unbuilt
    for k in ("soffit", "fascia", "outside_corner", "inside_corner",
              "j_channel"):
        assert k in PHASE2_KINDS and k not in PHASE1_KINDS
    assert "the LEFT end of the eave / frieze, then the RIGHT end" in ROUTES


def test_the_record_stores_a_and_b_and_y_and_reports_the_tilt():
    m = _line(400.0, tilt=8.0)
    rec = m["eave"]
    assert rec["a"] == {"x": 60.0, "y": 396.0}      # `a` is always the LEFT end
    assert rec["b"] == {"x": 940.0, "y": 404.0}
    assert rec["y"] == 400.0                        # the mean of the two ends
    assert rec["tilt_px"] == 8.0                    # reported, not hidden
    assert rec["units"] == "natural pixels of this photo"
    assert m["kind"] == "eave"


def test_it_carries_no_lf_and_no_price_and_is_not_a_soffit_or_a_fascia():
    assert "no LF is written" in EAVE_BASIS and "never priced" in EAVE_BASIS
    assert "ANCHOR" in EAVE_BASIS
    assert "It is not a soffit and it is not a fascia" in EAVE_BASIS
    assert "never copied to another photo or another face" in EAVE_BASIS
    assert "anchor · no LF" in EDITOR


def test_the_soffit_and_fascia_rows_stop_saying_no_eave_is_marked():
    row = {r["key"]: r for r in _trim_rows([_line(400.0)], [], IPP)[0]}
    for k in ("soffit", "fascia"):
        assert row[k]["lf"] is None
        assert "an EAVE line IS marked on this photo" in row[k]["refusal"]
        assert "ANCHOR ONLY" in row[k]["refusal"]
        assert "NO LF" in row[k]["refusal"]
        for bad in ("typical", "average", "assume", "mirror", "0 LF"):
            assert bad not in row[k]["refusal"].lower()


def test_the_gesture_is_the_two_tap_with_its_own_words():
    assert "Tap the LEFT end of the eave / frieze." in VOCAB
    assert "Tap the RIGHT end to finish the eave line." in VOCAB
    assert '{ key: "eave", label: "Eave"' in EDITOR
    assert 'tool === "wall_base" || tool === "eave"' in EDITOR
    assert "an ANCHOR for the AI body top, never an LF run" in EDITOR


# ---------------------------------------------------------------------------
# WHAT IT DOES
# ---------------------------------------------------------------------------
def test_a_fresh_body_takes_its_top_from_the_eave_and_keeps_its_bottom():
    plain = _body()
    x0, y0, x1, y1 = _box(plain["points"])
    assert round(y1, 1) == 560.0                    # gd1's sill, SEND-146
    tapped = _body(_eave_mark_line([_line(300.0)]))
    tx0, ty0, tx1, ty1 = _box(tapped["points"])
    assert round(ty0, 1) == 300.0                   # the top IS his line
    assert round(ty1, 1) == 560.0                   # the bottom did not move
    assert (round(tx0, 1), round(tx1, 1)) == (round(x0, 1), round(x1, 1))
    assert "top from eave mark on this photo" in tapped["basis"]
    assert "the frieze YOU tapped" in tapped["basis"]
    assert tapped["ai"]["top_anchor"] == "eave_mark"
    assert tapped["ai"]["anchor_eave_y"] == 300.0


def test_the_marked_height_is_printed_beside_the_reads_claim_never_averaged():
    tapped = _body(_eave_mark_line([_line(300.0)]))
    ppf = tapped["ai"]["px_per_ft"]
    assert round((560.0 - 300.0) / ppf, 2) == 13.0
    assert "13.0 ft at this photo's scale" in tapped["basis"]
    assert "NOT the read's 10.0 ft claim" in tapped["basis"]
    assert "neither is averaged" in tapped["basis"]
    #  the read's own claim is still recorded, unchanged
    assert tapped["ai"]["claimed_height_ft"] == 10.0


def test_no_eave_mark_leaves_the_top_exactly_as_it_is():
    plain = _body()
    assert plain["ai"]["top_anchor"] == "read_height_claim"
    assert plain["ai"]["anchor_eave_y"] is None
    assert "eave mark" not in plain["basis"]
    assert _eave_mark_line([]) is None
    assert _eave_mark_line([_line(300.0, kind="wall_base")]) is None
    assert _eave_mark_line([_line(300.0, status="refused")]) is None


def test_an_eave_below_the_bottom_is_refused_in_words_and_moves_nothing():
    tapped = _body(_eave_mark_line([_line(700.0)]))
    _, y0, _, y1 = _box(tapped["points"])
    assert round(y1, 1) == 560.0
    assert round(y0, 1) == round(_box(_body()["points"])[1], 1)   # unmoved
    assert "sits at or BELOW this box's bottom, so it cannot be a top" \
        in tapped["basis"]
    assert "nothing was guessed" in tapped["basis"]


def test_a_hand_moved_body_follows_the_eave_on_its_top_only():
    db = _DB()
    note = _follow(db, _zone(), _line(220.0))
    assert note and "YOUR EAVE LINE OUTRANKS THE OLD DRAG" in note
    assert "the TOP EDGE of 'AI front body' moved from y=300.0 px" in note
    (key, upd), = db.photo_takeoff_marks.updates
    assert key["id"] == "z-body"
    pts = upd["points"]
    #  the two HIGHEST vertices went to the line; the bottom two never moved
    assert sorted(round(p["y"], 1) for p in pts) == [220.0, 220.0, 700.0, 700.0]
    assert [p["x"] for p in pts] == [p["x"] for p in BODY_PTS]
    assert upd["ai"]["top_anchor"] == "eave_mark"
    assert upd["ai"]["top_followed_your_line"] is True
    #  his own basis survives, the sentence is appended
    assert upd["basis"].startswith("AI STARTING ZONE — 30.0 ft")


def test_a_confirmed_body_drops_back_to_provisional_when_its_top_moves():
    db = _DB()
    note = _follow(db, _zone(status="confirmed"), _line(220.0))
    (_, upd), = db.photo_takeoff_marks.updates
    assert upd["status"] == "provisional"
    assert upd["refused_reason"] == ("the top moved to the eave line you "
                                     "tapped — re-confirm the new figure")
    assert "a confirmation cannot outlive the figure it was given for" in note


def test_a_touched_gable_or_dormer_is_not_reshaped_by_an_eave_tap():
    for part in ("gable", "dormer"):
        db = _DB()
        assert _follow(db, _zone(part), _line(220.0)) is None
        assert db.photo_takeoff_marks.updates == []
    #  and a FRESH gable or dormer is left alone too: an eave tap re-bases
    #  with scope="body"
    assert 'scope="body" if body.kind == "eave" else "all"' in ROUTES
    assert 'if scope == "body" and part != "body":' in MODULE
    assert "the gable and the dormer stay " in MODULE


def test_a_crossed_dormer_is_reported_and_never_auto_fixed():
    assert "THE NEW BODY TOP CROSSES" in MODULE
    assert "NOTHING was " in MODULE and "auto-fixed" in MODULE
    assert "reported for you to settle" in MODULE
    #  nothing in the placer nudges a dormer out of the way
    for banned in ("shrink_dormer", "nudge", "auto_fix", "clip_dormer"):
        assert banned not in MODULE, banned


def test_there_is_no_ai_eave_finder():
    for banned in ("find_eave", "detect_eave", "eave_finder", "frieze_finder",
                   "soffit_mark", "fascia_mark", "corner_tick"):
        assert banned not in MODULE and banned not in ROUTES, banned
    fn = MODULE.split("def _two_tap_line_mark")[1].split("\ndef ")[0]
    assert "cv2" not in fn and "numpy" not in fn


def test_a_refused_face_gets_nothing_even_with_an_eave_tapped():
    from photo_zone_proposals import face_for_photo
    run = _run()
    run["result"]["raw_ai"]["photos"][0]["elevation"] = "right"
    run["result"]["raw_ai"]["walls"][0].update(
        label="right", width_ft_source="assumed_symmetric")
    run["result"]["measurements"]["_faces_measured"] = ["front", "left", "back"]
    who = face_for_photo(run, "p0.jpg")
    assert who["refusal"]
    assert "no body zone, no gable zone, no dormer zone" in who["refusal"]
