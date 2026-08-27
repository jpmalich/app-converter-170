"""SEND-136 PINS — (A) NO PHOTO, NO WALL · (B) NAME THE PLANE.

BLOCK A. Howard, 2026-08-27: on a job with ONE front picture, the panel
priced BACK / LEFT / RIGHT. The read itself admitted it: back's width
came back `assumed_symmetric`, the sides `estimated_no_direct_view`, and
all three carried `_source_photo_indices: []`. Corners, starter and
J-channel were then built over those invented walls and offered as money.
That is the Standing Prohibition, on the photo path.

THE RULE, registered: A WALL QUANTITY REQUIRES A PHOTO THAT SHOWS THAT
WALL. Missing face → REFUSE that face. No mirroring, no symmetry
assumption, no copied width, height, gable or depth — including when the
house "looks rectangular". A refused face writes no ft², no linear
accessory derived from it, and no quote line. Gables follow the face.

BLOCK B. The silent fronto-parallel assumption ends: every photo figure
carries a `plane_basis` of SQUARE-ON, OBLIQUE or UNKNOWN — three values,
no fourth, and no default that reads as square-on.

Nothing here is tuned toward 370, 252, 1,243.8 or any dollar total. The
arithmetic pins below use invented round numbers.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/app/backend")
from routes.ai_measure import (_aggregate_to_hover_shape, _face_photo_evidence,
                              REFUSING_WIDTH_HEIGHT_SOURCES)
from routes.photo_takeoff import _plane_basis, _quantities

FE = Path("/app/frontend/src")


def _wall(label, w, h, gable=0.0, photos=(0,), wsrc="direct_ref",
          hsrc="direct_single_reading"):
    return {"label": label, "width_ft": w, "height_ft": h,
            "gable_triangle_height_ft": gable,
            "width_ft_source": wsrc, "height_ft_source": hsrc,
            "_source_photo_indices": list(photos),
            "siding_pct_this_wall": 100, "confidence": 90}


def _raw(walls, openings=None, **extra):
    raw = {"walls": walls, "openings": openings or [],
           "eaves_lf": 60.0, "rakes_lf": 40.0, "starter_lf": 120.0,
           "outside_corner_lf": 40.0, "inside_corner_lf": 8.0,
           "avg_wall_height_ft": 10.0, "roof_type": "gable"}
    raw.update(extra)
    return raw


# ── BLOCK A — THE FACE GATE ──────────────────────────────────────────
def test_a_face_with_no_photo_of_its_own_is_refused():
    ok, why = _face_photo_evidence(_wall("back", 30, 10, photos=()))
    assert ok is False
    assert "BACK — no photo of this wall" in why
    assert "Not copied from another face" in why


@pytest.mark.parametrize("src", sorted(REFUSING_WIDTH_HEIGHT_SOURCES))
def test_a_mirrored_or_estimated_dimension_is_refused(src):
    ok, why = _face_photo_evidence(_wall("left", 20, 10, wsrc=src))
    assert ok is False, (
        f"{src!r} passed the face gate — a width that came from another "
        "face or from nothing is not a measurement")
    assert "LEFT" in why and "Not measured" in why


def test_a_photographed_face_passes():
    ok, why = _face_photo_evidence(_wall("front", 30, 10, photos=(0, 2)))
    assert ok is True and why is None


def test_a_front_only_job_prices_the_front_and_refuses_three_faces():
    """The exact shape of the defect. Invented numbers: a 30 ft front at
    10 ft with a 6 ft gable rise; the read mirrors it to the back and
    guesses 20 ft sides."""
    walls = [
        _wall("front", 30.0, 10.0, gable=6.0, photos=(0,)),
        _wall("back", 30.0, 10.0, gable=6.0, photos=(),
              wsrc="assumed_symmetric", hsrc="assumed_symmetric"),
        _wall("left", 20.0, 10.0, photos=(),
              wsrc="estimated_no_direct_view", hsrc="assumed_symmetric"),
        _wall("right", 20.0, 10.0, photos=(),
              wsrc="estimated_no_direct_view", hsrc="assumed_symmetric"),
    ]
    m = _aggregate_to_hover_shape(_raw(walls))
    assert m["_faces_measured"] == ["front"], m["_faces_measured"]
    labels = sorted(f["label"] for f in m["_faces_refused"])
    assert labels == ["back", "left", "right"]
    # THE FRONT ONLY. 30 × 10 = 300 body + ONE gable, ½ × 30 × 6 = 90
    # (NAMED PIN UPDATE, SEND-137 2026-08-27: the measured triangle; the
    # 0.70 field factor is retired — SEND-136's subject, the REFUSED REAR,
    # is unchanged) = 390. The refused rear gable adds nothing.
    assert m["siding_sqft"] == pytest.approx(390.0, abs=0.6), m["siding_sqft"]
    assert m["_ai_gable_sqft"] == pytest.approx(90.0, abs=0.6)
    # NO ACCESSORY FROM AN INVENTED WALL. These are REFUSALS (None), and
    # a refusal is never a 0.
    for key in ("eaves_lf", "rakes_lf", "outside_corner_lf",
                "inside_corner_lf", "footprint_perimeter_ft"):
        assert m[key] is None, (
            f"{key} came back {m[key]!r} on a front-only job — it was "
            "computed over the faces the read mirrored")
    # starter IS per face: it runs along the bottom of the wall we
    # measured, and the payload says so in words.
    assert m["starter_lf"] == pytest.approx(30.0)
    assert "MEASURED FACES ONLY" in m["_starter_basis"]
    assert "front" in m["_starter_basis"]
    # the gap is named, in the contractor's own terms
    note = m["_face_refusal_note"]
    for token in ("BACK", "LEFT", "RIGHT", "no photo of this wall",
                  "not zeros"):
        assert token in note, token
    assert "NO PHOTO, NO WALL" in m["_face_rule"]
    # what the read CLAIMED stays on the record — as a claim, never money
    back = next(f for f in m["_faces_refused"] if f["label"] == "back")
    assert back["claimed_width_ft"] == 30.0
    assert back["claimed_width_source"] == "assumed_symmetric"


def test_a_gable_on_an_unphotographed_face_is_not_copied():
    """GABLES FOLLOW THE FACE. The mirrored rear gable contributes
    nothing — the front's gable is counted once, not twice."""
    walls = [
        _wall("front", 30.0, 10.0, gable=6.0, photos=(0,)),
        _wall("back", 30.0, 10.0, gable=6.0, photos=(),
              wsrc="assumed_symmetric", hsrc="assumed_symmetric"),
    ]
    m = _aggregate_to_hover_shape(_raw(walls))
    # NAMED PIN UPDATE (SEND-137): ½ × width × rise, the measured triangle.
    one_gable = 0.5 * 30.0 * 6.0
    assert m["_ai_gable_sqft"] == pytest.approx(one_gable, abs=0.6), (
        "the rear gable was copied from the front elevation")


def test_an_opening_on_a_refused_face_is_refused_too():
    walls = [
        _wall("front", 30.0, 10.0, photos=(0,)),
        _wall("back", 30.0, 10.0, photos=(), wsrc="assumed_symmetric"),
    ]
    openings = [
        {"opening_id": "f1", "wall": "front", "type": "window",
         "width_in": 36, "height_in": 60},
        {"opening_id": "b1", "wall": "back", "type": "window",
         "width_in": 36, "height_in": 60},
    ]
    m = _aggregate_to_hover_shape(_raw(walls, openings))
    assert m["window_count"] == 1, (
        "a window in a wall no photo showed was counted")
    refused = m["_openings_refused"]
    assert len(refused) == 1 and refused[0]["wall"] == "back"
    assert "no photo of this wall" in refused[0]["refusal"]


def test_an_unlabelled_opening_is_kept():
    """An opening with no wall label was still SEEN in some photo. The
    label is missing; the evidence is not. It is not thrown away."""
    walls = [_wall("front", 30.0, 10.0, photos=(0,)),
             _wall("back", 30.0, 10.0, photos=(), wsrc="assumed_symmetric")]
    openings = [{"opening_id": "x1", "type": "window", "width_in": 36,
                 "height_in": 60}]
    m = _aggregate_to_hover_shape(_raw(walls, openings))
    assert m["window_count"] == 1
    assert not m["_openings_refused"]


def test_a_four_photo_job_still_prices_four_walls():
    """THE RULE DOES NOT COST AN HONEST JOB ANYTHING. Each wall has its
    own photo, so all four are DERIVED and every house-level run is back."""
    walls = [
        _wall("front", 30.0, 10.0, gable=6.0, photos=(0,)),
        _wall("back", 30.0, 10.0, gable=6.0, photos=(1,)),
        _wall("left", 20.0, 10.0, photos=(2,)),
        _wall("right", 20.0, 10.0, photos=(3,)),
    ]
    m = _aggregate_to_hover_shape(_raw(walls))
    assert m["_faces_refused"] == []
    assert m["_faces_measured"] == ["front", "back", "left", "right"]
    assert m["_face_refusal_note"] is None
    # 2×(30×10) + 2×(20×10) = 1000 body, + TWO measured gables at
    # ½ × 30 × 6 = 90 each (NAMED PIN UPDATE, SEND-137) = 1180
    assert m["siding_sqft"] == pytest.approx(1180.0, abs=1.0), m["siding_sqft"]
    for key in ("eaves_lf", "rakes_lf", "outside_corner_lf",
                "footprint_perimeter_ft", "starter_lf"):
        assert m[key] is not None and m[key] > 0, (
            f"{key} was refused on a job where every wall has its own photo")
    assert m["footprint_perimeter_ft"] == pytest.approx(100.0)
    assert "MEASURED FACES ONLY" not in m["_starter_basis"]


def test_a_job_with_no_photographed_face_refuses_everything():
    walls = [_wall("front", 30.0, 10.0, photos=(), wsrc="assumed_symmetric")]
    m = _aggregate_to_hover_shape(_raw(walls))
    assert m["siding_sqft"] == 0
    assert m["starter_lf"] is None
    assert "REFUSED" in m["_starter_basis"]


# ── BLOCK A — THE SURFACES MAY NOT PUT THE NUMBER BACK ───────────────
def test_the_live_recompute_skips_a_refused_face():
    """`recomputeFromWalls` is a SECOND money surface: it re-totals the
    walls in the browser. If it kept summing the mirrored faces the
    headline would put back exactly the ft² the read refused."""
    src = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
    body = src.split("const recomputeFromWalls = (walls) => {")[1][:900]
    assert "if (w._refused) continue;" in body, (
        "the live recompute still sums faces the read refused")


def test_the_wall_table_shows_a_refusal_and_offers_no_number_to_type():
    """NOT A GUESS IN THE OTHER DIRECTION either: a refused face gets no
    editable width box. A missing photo stays missing until a photo
    arrives or the face is drawn on a photo in the editor."""
    src = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
    assert "ai-measure-wall-refused-" in src
    assert "ai-measure-faces-refused-banner" in src
    block = src.split("if (w._refused) {")[1].split("const width =")[0]
    assert "REFUSED" in block
    assert "<input" not in block, (
        "a refused face still offers a typing box — that replaces one "
        "guess with another")
    assert "takeoff editor" in block


def test_the_3d_panel_prints_the_refusal_instead_of_a_wall_total():
    src = (FE / "components" / "estimate" / "HouseModel3D.jsx").read_text()
    assert "refused: !!wallData?._refused," in src
    assert "ai-measure-3d-facade-refused-" in src
    assert "facade.refused ?" in src, (
        "the per-facade panel still prints ft² for a refused face")


# ── BLOCK B ITEM 1+2 — NAME THE PLANE ────────────────────────────────
def _open_box(x, y, w, h, w_in=None, h_in=None, style="test window"):
    return {"kind": "opening", "status": "confirmed", "style": style,
            "width_in": w_in, "height_in": h_in,
            "points": [{"x": x, "y": y}, {"x": x + w, "y": y},
                       {"x": x + w, "y": y + h}, {"x": x, "y": y + h}]}


def test_the_starting_state_is_unknown_never_square_on():
    """Existing figures come back UNKNOWN. That is the correct starting
    state — there is no default that reads as square-on."""
    for marks in ([], [_open_box(0, 0, 100, 100)],
                  [{"kind": "siding_zone", "status": "confirmed",
                    "points": [{"x": 0, "y": 0}, {"x": 10, "y": 0},
                               {"x": 10, "y": 10}]}]):
        got = _plane_basis(marks, 1.0)
        assert got["plane_basis"] == "UNKNOWN", got
        assert "UNVERIFIED" in got["plane_basis_reason"]
        assert "13%" in got["plane_basis_reason"], (
            "the under-read an oblique photo produces is not stated")
        assert got["plane_basis_angle_deg"] is None


def test_a_boxed_opening_that_matches_its_typed_aspect_earns_square_on():
    # 40 in × 60 in window drawn 80 px × 120 px — the aspects agree
    got = _plane_basis([_open_box(0, 0, 80, 120, 40, 60)], 0.5)
    assert got["plane_basis"] == "SQUARE-ON", got
    assert "earned by this photo's own marks" in got["plane_basis_reason"]
    assert "40×60" in " ".join(got["plane_basis_evidence"])


def test_a_compressed_box_reads_oblique_with_the_angle_it_gives():
    # the same window drawn 40 px × 120 px: half as wide as it should be
    got = _plane_basis([_open_box(0, 0, 40, 120, 40, 60)], 0.5)
    assert got["plane_basis"] == "OBLIQUE", got
    assert got["plane_basis_angle_deg"] == pytest.approx(60.0, abs=1.0), (
        "a box compressed to half its aspect indicates ≈60°")
    assert "PROJECTION" in got["plane_basis_reason"]
    assert "fabricated ruler" in got["plane_basis_reason"], (
        "the reason must say no correction is applied")


def test_a_stretched_box_reads_oblique_and_withholds_the_angle():
    got = _plane_basis([_open_box(0, 0, 160, 120, 40, 60)], 0.5)
    assert got["plane_basis"] == "OBLIQUE"
    assert got["plane_basis_angle_deg"] is None, (
        "an angle was stated for a stretch that a turned wall and a "
        "tilted camera both explain")
    assert "cannot be told apart" in " ".join(got["plane_basis_evidence"])


def test_two_openings_disagreeing_on_scale_read_oblique():
    marks = [_open_box(0, 0, 100, 100, 40, None),
             _open_box(500, 0, 60, 60, 40, None)]
    got = _plane_basis(marks, 0.4)
    assert got["plane_basis"] == "OBLIQUE", got
    assert "falls off across" in got["plane_basis_reason"]


def test_converging_verticals_are_declared_untested_not_passed():
    got = _plane_basis([], 1.0)
    joined = " ".join(got["plane_basis_evidence"])
    assert "converging verticals: NOT TESTED" in joined, (
        "a test the phase cannot run must say so, not stay silent")


def test_there_is_no_fourth_value():
    src = Path("/app/backend/routes/photo_takeoff.py").read_text()
    body = src.split("def _plane_basis(")[1].split("\ndef ")[0]
    verdicts = {line.split('basis = "')[1].split('"')[0]
                for line in body.splitlines() if 'basis = "' in line}
    assert verdicts == {"SQUARE-ON", "OBLIQUE", "UNKNOWN"}, verdicts


def test_the_plane_rides_every_quantity_payload():
    q = _quantities([_open_box(0, 0, 80, 120, 40, 60)],
                    {"span_px": 100.0, "anchor": {"inches": 100.0}})
    assert q["plane_basis"] == "SQUARE-ON"
    assert q["plane_basis_reason"]
    # and it is stated even with NO scale, where there is no ft² at all
    q2 = _quantities([_open_box(0, 0, 40, 120, 40, 60)], None)
    assert q2["siding_sqft"] is None
    assert q2["plane_basis"] == "OBLIQUE"


def test_the_editor_prints_the_plane_where_the_quantity_appears():
    src = (FE / "components" / "estimate" / "PhotoTakeoffEditor.jsx").read_text()
    assert 'data-testid="photo-takeoff-plane-basis"' in src
    assert "qty?.plane_basis_reason" in src
    assert 'Plane: {qty?.plane_basis || "UNKNOWN"}' in src, (
        "the surface must fall back to UNKNOWN, never to square-on")


def test_no_correction_factor_was_built():
    """ITEM 3 IS NOT AUTHORISED. No homography, no rectification, no
    cosine applied to a quantity."""
    src = Path("/app/backend/routes/photo_takeoff.py").read_text()
    for token in ("homography", "rectif", "warp", "getPerspectiveTransform"):
        assert token not in src.lower(), (
            f"{token!r} appears — rectify-from-a-window is not authorised")
    # the only trig in the module reports an ANGLE; it never scales a figure
    body = src.split("def _plane_basis(")[1].split("\ndef ")[0]
    assert "math.acos" in body
    after = src.split("def _plane_basis(")[1].split("\ndef ")[1:]
    assert not any("math." in chunk for chunk in after), (
        "trigonometry escaped the classifier — a correction factor from "
        "an unmeasured angle is a fabricated ruler")


# ── BLOCK A — THE RULE REACHES EVERY RESTORE, INCLUDING OLD RUNS ──────
def test_a_run_read_before_the_rule_is_stamped_stale_on_the_way_out():
    """A run stored BEFORE the rule kept its mirrored faces and totals
    summed over them. Every restore is a door: on the way out the faces
    are stamped REFUSED and the payload is marked STALE so it cannot be
    applied. Read-side only — nothing is written back."""
    src = Path("/app/backend/routes/ai_measure.py").read_text()
    block = src.split("READ-SIDE RE-GATE")[1][:2600]
    assert '_meas["_face_rule_stale"] = True' in block
    assert '_w["_refused"] = True' in block
    assert 'if isinstance(_meas, dict) and "_faces_refused" not in _meas' in block, (
        "the re-gate must skip runs already gated at read time")
    assert "READ ONLY" in block
    # and the payload actually carries the re-gated result
    assert '"result": _result,' in src


def test_a_stale_read_cannot_be_applied():
    fe = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
    assert "if (m._face_rule_stale) return true;" in fe, (
        "Apply Measurements is still enabled on a read whose totals were "
        "summed over faces no photo showed")
    assert 'data-testid="ai-measure-face-rule-stale"' in fe
    assert "_face_refusal_note" in fe


def test_a_refused_corner_emits_no_stick():
    """A corner stands between TWO faces. With a face refused the corner
    LF and COUNT are refusals — and the stick builders must emit NOTHING
    rather than floor at one stick per lane."""
    from routes.hover import _build_lines
    walls = [_wall("front", 30.0, 10.0, photos=(0,)),
             _wall("back", 30.0, 10.0, photos=(), wsrc="assumed_symmetric"),
             _wall("left", 20.0, 10.0, photos=(), wsrc="estimated_no_direct_view"),
             _wall("right", 20.0, 10.0, photos=(), wsrc="estimated_no_direct_view")]
    m = _aggregate_to_hover_shape(_raw(walls, corner_locations=[
        {"type": "outside"}, {"type": "outside"}, {"type": "outside"},
        {"type": "outside"}]))
    assert m["outside_corner_count"] is None
    assert m["inside_corner_count"] is None
    corner_qty = [float(l.get("qty") or 0) for l in _build_lines(m)
                  if "corner" in str(l.get("name", "")).lower()]
    assert not any(q > 0 for q in corner_qty), (
        f"a corner stick was still priced from refused faces: {corner_qty}")
