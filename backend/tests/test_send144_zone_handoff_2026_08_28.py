"""SEND-144 PINS — THE AI'S FINDINGS BECOME STARTING ZONES, AND NOTHING ELSE
(Howard ruled 2026-08-28).

  8 photos + his annotations → the read that ALREADY FINISHED → starting
  zones on those photos → he adjusts → CONFIRMED shapes only count.

The law these pins hold:
  · NO SECOND FINDER. The handoff reads the finished run: no OCR, no photo
    pass, no height/gable/dormer engine, no pitch.
  · A REFUSED FACE GETS NO ZONE — in the run's own words. A width the run
    marked `assumed_symmetric` is NOT a measured width.
  · A CORNER SHOT IS NOT A FIFTH WALL.
  · SHAPE from the face's own W×H; PLACEMENT is a starting position and is
    NOT a measurement.
  · A CONTESTED HEIGHT IS NOT AVERAGED — both readings named, the larger
    used so it can be pulled down.
  · A PROPOSAL IS NOT A QUANTITY: provisional zones feed nothing, and the
    four unsupported trims stay named refusals even with a confirmed body.
  · A RE-PULL NEVER OVERWRITES A ZONE A HUMAN TOUCHED.
"""
import pathlib
import sys

sys.path.insert(0, "/app/backend")

from photo_zone_proposals import (  # noqa: E402
    BODY_BOTTOM_FRAC, BODY_WIDTH_FRAC, PLACEMENT_SENTENCE, _dormer_for,
    _height_for, _refusal_for_face, build_zone_marks, face_for_photo)
from routes.photo_takeoff import ORIGINS, _quantities, _trim_rows  # noqa: E402

BACKEND = pathlib.Path("/app/backend")
MODULE = (BACKEND / "photo_zone_proposals.py").read_text()
ROUTE = (BACKEND / "routes" / "photo_takeoff.py").read_text()
AIM = (BACKEND / "routes" / "ai_measure.py").read_text()
FE = pathlib.Path("/app/frontend/src/components/estimate")
EDGES = (FE / "phototakeoff" / "CandidateEdges.jsx").read_text()
EDITOR = (FE / "PhotoTakeoffEditor.jsx").read_text()

NAT = (2400.0, 1800.0)


def _py_code(src: str) -> str:
    """Only the CODE of a python file — every comment and every string
    literal removed. A rule the module NAMES in its own prose ("no OCR",
    "no material line") must not trip the pin that enforces it: what
    matters is that no line of code does the thing."""
    import io
    import tokenize
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        out.append(tok.string)
    return " ".join(out)


def _js_code(src: str) -> str:
    return "\n".join(l for l in src.splitlines()
                      if not l.strip().startswith(("//", "*", "/*")))


MODULE_CODE = _py_code(MODULE)
EDGES_CODE = _js_code(EDGES)

# a run shaped exactly like the live one: front measured with a contested
# height and a gable, left measured with an UNANCHORED dormer, right
# refused because its width was mirrored off the left wall, and four corner
# shots that own no plane.
RUN = {
    "run_id": "pin144run",
    "status": "done",
    "estimate_id": "est-1",
    "photo_paths": "p_front.jpg,p_corner.jpg,p_left.jpg,p_right.jpg",
    "result": {
        "raw_ai": {
            "photos": [
                {"index": 0, "elevation": "front", "elevation_confidence": 98},
                {"index": 1, "elevation": "front-left"},
                {"index": 2, "elevation": "left"},
                {"index": 3, "elevation": "right"},
            ],
            "walls": [
                {"label": "front", "width_ft": 27.0, "width_ft_source": "direct_ref",
                 "height_ft": 10.9, "height_ft_source": "direct_disagreement",
                 "confidence": 70, "gable_triangle_height_ft": 6.5,
                 "dormer_face_sqft": 0,
                 "_per_photo_readings": [{"eave_ft": 10.9}, {"eave_ft": 9.0}]},
                {"label": "left", "width_ft": 37.0, "width_ft_source": "direct_ref",
                 "height_ft": 8.4, "height_ft_source": "direct_consensus",
                 "confidence": 82, "gable_triangle_height_ft": 0,
                 "dormer_face_sqft": 47.6},
                {"label": "right", "width_ft": 37.0,
                 "width_ft_source": "assumed_symmetric", "height_ft": 8.0,
                 "height_ft_source": "direct_single_reading", "confidence": 40,
                 "gable_triangle_height_ft": 0, "dormer_face_sqft": 56.0},
            ],
            "dormers": [
                {"face": "left", "width_ft": 14.1, "knee_wall_height_ft": 3.5,
                 "width_source": "direct_consensus", "offset_x_ft": -0.5},
                {"face": "right", "width_ft": 14.9, "knee_wall_height_ft": 3.8,
                 "width_source": "assumed_symmetric"},
            ],
        },
        "measurements": {
            "_faces_measured": ["front", "left"],
            "_faces_refused": [{"label": "right", "refusal": (
                "RIGHT — no photo measured this wall's width "
                "(assumed_symmetric). Not measured. Not copied from another "
                "face.")}],
            "_ai_pin_gap_hints": [
                {"kind": "unanchored_dormer_width", "elevation": "left",
                 "message": "no reference marker in frame on the dormer face"},
                {"kind": "unanchored_dormer_width", "elevation": "right",
                 "message": "no reference marker in frame"},
            ],
            "_per_elevation_breakdown": [
                {"label": "left", "stone_sqft": 0},
                {"label": "front", "stone_sqft": 0},
            ],
        },
    },
}


def _wall(face):
    return next(w for w in RUN["result"]["raw_ai"]["walls"]
                if w["label"] == face)


def _build(face, photo):
    return build_zone_marks(RUN, face, _wall(face), photo, NAT[0], NAT[1],
                            "est-1", "co-1", "pin@example.com")


# ---------------------------------------------------------------------------
# NO SECOND FINDER, ONE OPENING PROPOSER
# ---------------------------------------------------------------------------
def test_the_handoff_reads_the_finished_run_and_finds_nothing_itself():
    for banned in ("anthropic", "openai", "gemini", "prompt", "pytesseract",
                   "ocr", "Image.open", "pdfplumber", "fitz", "pitch",
                   "assumed", "symmetric_", "average"):
        assert banned not in MODULE_CODE.lower().replace("assumed_symmetric", ""), banned
    # it never builds an opening: there is ONE opening proposer in this app
    assert '"opening"' not in MODULE_CODE
    assert "propose_from_read(est_id, photo_key, user)" in ROUTE


def test_the_pull_fires_from_the_door_and_from_the_finished_run():
    assert "photo-takeoff/propose-zones" in ROUTE
    # auto-propose is hooked at BOTH completion points of the worker
    assert AIM.count("from photo_zone_proposals import maybe_propose_zones") == 2
    assert AIM.count("await maybe_propose_zones(run_id)") == 2
    assert 'data-testid="photo-takeoff-zones-btn"' in EDITOR


def test_a_protected_estimate_gets_no_proposal_not_even_a_provisional_one():
    assert ("detail=\"protected estimate — a zone proposal is still a write\""
            in ROUTE)
    assert "protected estimate — no derived write, not " in MODULE


# ---------------------------------------------------------------------------
# WHICH PHOTO OWNS A FACE — AND WHICH OWNS NONE
# ---------------------------------------------------------------------------
def test_a_head_on_photo_owns_its_face():
    who = face_for_photo(RUN, "p_front.jpg")
    assert who["face"] == "front" and who["refusal"] is None
    assert who["wall"]["width_ft"] == 27.0


def test_a_corner_shot_is_not_a_fifth_wall():
    who = face_for_photo(RUN, "p_corner.jpg")
    assert who["face"] is None
    assert "corner shot is NOT a fifth wall" in who["refusal"]
    assert "foreshortened" in who["refusal"]


def test_a_refused_face_answers_in_the_runs_own_words_and_gets_no_zone():
    who = face_for_photo(RUN, "p_right.jpg")
    assert who["face"] == "right"
    assert "no photo measured this wall's width (assumed_symmetric)" in who["refusal"]
    assert "Not copied from another face" in who["refusal"]
    assert "no body zone, no gable zone, no dormer zone" in who["refusal"]


def test_a_mirrored_width_is_not_a_measured_width():
    assert _refusal_for_face(RUN, "right")
    assert _refusal_for_face(RUN, "front") is None
    assert _refusal_for_face(RUN, "left") is None


def test_a_photo_outside_the_run_unlocks_nothing():
    assert "unlocks nothing here" in face_for_photo(RUN, "stranger.jpg")["refusal"]


# ---------------------------------------------------------------------------
# THE BODY ZONE — SHAPE FROM THE RUN, PLACEMENT SAID OUT LOUD
# ---------------------------------------------------------------------------
def test_the_body_rectangle_carries_the_faces_own_proportion():
    body = _build("left", "p_left.jpg")[0]
    p = body["points"]
    w = p[1]["x"] - p[0]["x"]
    h = p[2]["y"] - p[1]["y"]
    assert round(w / h, 3) == round(37.0 / 8.4, 3)          # W:H from the run
    assert round(w / NAT[0], 2) == BODY_WIDTH_FRAC          # 80% of the photo
    assert round(p[2]["y"] / NAT[1], 2) == BODY_BOTTOM_FRAC  # near the bottom
    assert body["kind"] == "siding_zone" and body["shape"] == "rect"


def test_the_basis_says_the_placement_is_not_a_measurement():
    body = _build("front", "p_front.jpg")[0]
    assert PLACEMENT_SENTENCE in body["basis"]
    assert "27.0 ft × 10.9 ft" in body["basis"]
    assert "width direct_ref" in body["basis"]
    assert "confidence 70" in body["basis"]


def test_a_contested_height_is_named_and_never_averaged():
    used, note = _height_for(_wall("front"))
    assert used == 10.9                      # the LARGER, so it can be pulled down
    assert used != (10.9 + 9.0) / 2
    assert "DISAGREE" in note and "10.9 ft vs 9.0 ft" in note
    assert "NOT averaged" in note
    body = _build("front", "p_front.jpg")[0]
    assert "NOT averaged" in body["basis"]
    assert body["ai"]["height_readings_disagree"] is True


# ---------------------------------------------------------------------------
# GABLE AND DORMER — ONLY WHERE THE RUN REPORTS ONE
# ---------------------------------------------------------------------------
def test_a_gable_only_where_the_run_reports_a_rise_and_never_from_pitch():
    kinds = [m["kind"] for m in _build("front", "p_front.jpg")]
    assert kinds == ["siding_zone", "gable"]
    g = _build("front", "p_front.jpg")[1]
    assert len(g["points"]) == 3                     # eave · peak · eave
    assert g["points"][1]["y"] < g["points"][0]["y"]  # the peak is up
    assert g["ai"]["claimed_gable_rise_ft"] == 6.5
    assert "NOT derived from a pitch" in g["basis"]
    # the left face has no rise, so it gets no triangle
    assert "gable" not in [m["kind"] for m in _build("left", "p_left.jpg")]


def test_the_gable_rise_is_the_runs_own_figure_in_the_bodys_own_scale():
    body, g = _build("front", "p_front.jpg")
    ppf = (body["points"][1]["x"] - body["points"][0]["x"]) / 27.0
    rise_px = body["points"][0]["y"] - g["points"][1]["y"]
    assert round(rise_px / ppf, 2) == 6.5


def test_a_dormer_only_where_the_run_reports_one_and_it_says_unanchored():
    d = [m for m in _build("left", "p_left.jpg") if m["kind"] == "dormer"]
    assert len(d) == 1
    d = d[0]
    assert d["ai"]["claimed_dormer_width_ft"] == 14.1
    assert d["ai"]["unanchored"] is True
    assert "UNANCHORED: no reference marker in frame" in d["basis"]
    assert d["depth_ft"] is None                     # cheeks refuse until typed
    assert "cheeks refuse until you type it" in d["basis"]
    dormer, unanchored = _dormer_for(RUN, "left")
    assert dormer["width_ft"] == 14.1 and unanchored


def test_the_refused_faces_dormer_is_not_parked_anywhere():
    """RIGHT's 14.9 × 3.8 dormer only proposes once RIGHT has a measured
    width of its own — it is never placed on a corner shot or on LEFT."""
    for face, photo in (("left", "p_left.jpg"), ("front", "p_front.jpg")):
        for m in _build(face, photo):
            assert m["ai"].get("claimed_dormer_width_ft") != 14.9
    assert face_for_photo(RUN, "p_right.jpg")["refusal"]


# ---------------------------------------------------------------------------
# A PROPOSAL IS NOT A QUANTITY
# ---------------------------------------------------------------------------
def test_every_zone_is_provisional_stage_two_and_keyed_for_a_safe_repull():
    marks = _build("front", "p_front.jpg") + _build("left", "p_left.jpg")
    for m in marks:
        assert m["status"] == "provisional"
        assert m["origin"] == "ai_zone_proposal" and m["stage"] == 2
        assert m["ai"]["run_id"] == "pin144run"
        assert m["confirmed_at"] is None and m["confirmed_basis"] is None
    refs = [m["ai"]["ref_id"] for m in marks]
    assert refs == ["face:front:body", "face:front:gable",
                    "face:left:body", "face:left:dormer"]
    assert len(set(refs)) == len(refs)               # a re-pull matches, not doubles
    assert "ai_zone_proposal" in ORIGINS


def test_provisional_zones_feed_no_quantity():
    marks = _build("front", "p_front.jpg")
    q = _quantities(marks, {"span_px": 10.0, "tape_inches": 120.0})
    assert q["siding_sqft"] is None                  # nothing counts unconfirmed
    assert q["gable_sqft"] is None
    assert q["j_channel_lf"] is None and q["gable_rake_lf"] is None


def test_a_confirmed_body_zone_still_leaves_the_four_trims_refused():
    body = _build("front", "p_front.jpg")[0]
    body["status"] = "confirmed"
    rows, _, _ = _trim_rows([body], [], 12.0)
    by = {r["key"]: r for r in rows}
    for k in ("starter", "outside_corner", "inside_corner", "soffit", "fascia"):
        assert by[k]["lf"] is None and by[k]["refusal"]


# ---------------------------------------------------------------------------
# THE CANDIDATE EDGES ARE LINES WITH A WORD — NOT A SECOND QUANTITY ENGINE
# ---------------------------------------------------------------------------
def test_the_candidate_edges_carry_a_word_and_no_figure():
    for word in ("starter candidate", "corner candidate",
                 "eave / frieze candidate"):
        assert word in EDGES
    for banned in ("LF", "toFixed", "sqft", "ft²", "qty", "lf("):
        assert banned not in EDGES_CODE, banned
    assert "strokeDasharray" in EDGES               # dashed, as ruled
    assert "<CandidateEdges marks={marks} nMark={nMark} />" in EDITOR


def test_the_handoff_writes_no_money_and_no_material_line():
    for banned in ("total_sell", "unit_price", "sell_price", "margin",
                   "material", "lines", "price"):
        assert banned not in MODULE_CODE, banned

# ---------------------------------------------------------------------------
# THE ZONES ARE REACHABLE — AN ANNOTATED PHOTO IS A DIFFERENT FILE
# ---------------------------------------------------------------------------
def test_the_photos_the_read_read_are_openable_from_the_preview():
    """An annotated photo is uploaded as a NEW FILE (`ai_<uuid>.jpg`), so the
    read's findings — and its starting zones — live on a different file from
    the one attached to the estimate. The preview now opens the takeoff on
    the file the read ACTUALLY READ, so no zone is ever out of reach and no
    mapping between the two files is guessed."""
    btn = (FE / "AIMeasureButton.jsx").read_text()
    assert 'data-testid="ai-measure-read-photos"' in btn
    assert "ai-measure-read-photo-takeoff-${i}" in btn
    assert "setReadPhotos(" in btn
    # the elevation shown beside each photo is the READ'S OWN call
    assert "preview?.raw_ai?.photos" in btn
    assert "The photos this read read — starting zones live here" in btn


def test_the_read_photo_is_stored_where_a_pod_cannot_take_it():
    """SEND-144 found a FOURTH upload door the SEND-142 move did not name:
    the annotated photo the read reads was written to the pod's disk only.
    It is now the photo that carries the zones, so it goes to object storage
    too, and a failed store REFUSES the read."""
    assert "await aput(upload_path(name), raw, ctype)" in AIM
    assert "await save_blob(name, raw, ctype)" in AIM
    assert "read was NOT started" in " ".join(AIM.split())
