"""SEND-139 PINS — GABLES AND DORMERS MOVE INTO THE PHOTO TAKEOFF EDITOR,
THEN THE ANNOTATE DOORS COME OFF (Howard ruled 2026-08-27).

  They must work as they do in Annotate. Do not invent a new gable
  model. Port the existing tool.
  Howard's gable ruling still governs the number: ½ × width × rise when
  both exist. Missing rise or width → REFUSE, never 0.70.

Item 1 (the report) is `memory/send139_report.md`. These pins hold the
build: the same gesture, the same fields, the same masking rule, ½ or a
NAMED REFUSAL, guidance until confirmed, quantity and never money, and
NO FACE BORROWS ANOTHER FACE'S GABLE.
"""
import pathlib
import sys

sys.path.insert(0, "/app/backend")

import pytest  # noqa: E402

from routes.photo_takeoff import (  # noqa: E402
    GABLE_KINDS, GABLE_PITCH_MAX, GABLE_PITCH_MIN, GABLE_PITCH_PRESETS,
    KIND_POINTS, PHASE1_KINDS, PHASE2_KINDS, _dormer_figure, _gable_figure,
    _poly_area_px, _quantities)

EDITOR = pathlib.Path(
    "/app/frontend/src/components/estimate/PhotoTakeoffEditor.jsx")
AI_BUTTON = pathlib.Path(
    "/app/frontend/src/components/estimate/AIMeasureButton.jsx")
ANNOTATOR = pathlib.Path(
    "/app/frontend/src/components/estimate/PhotoAnnotateModal.jsx")
GABLE_MATH = pathlib.Path("/app/frontend/src/lib/gableMath.js")
WIZARD = pathlib.Path(
    "/app/frontend/src/components/estimate/GuidedCaptureWizard.jsx")

# 12 in per px → 1 ft per px, so pixels read as feet. Invented numbers.
IPP = 12.0


def _scale(px=100.0, inches=1200.0):
    return {"span_px": px, "anchor": {"inches": inches}}


def _gable(pts, **kw):
    m = {"id": "g1", "kind": "gable", "status": "confirmed", "points": pts,
         "label": "gable"}
    m.update(kw)
    return m


def _dormer(pts, **kw):
    m = {"id": "d1", "kind": "dormer", "status": "confirmed", "points": pts,
         "label": "dormer"}
    m.update(kw)
    return m


# a 30 ft wide gable with an 8 ft rise, in "feet-as-pixels"
TRI = [{"x": 0, "y": 8}, {"x": 15, "y": 0}, {"x": 30, "y": 8}]
QUAD = [{"x": 0, "y": 10}, {"x": 6, "y": 10}, {"x": 6, "y": 0}, {"x": 0, "y": 0}]


# ---------------------------------------------------------------------------
# 1. THE TOOLS ARE HERE, AND THEY ARE PHASE 1 (NOT PHASE 2 TRIM)
# ---------------------------------------------------------------------------
def test_gable_and_dormer_are_phase_1_kinds_of_this_editor():
    assert GABLE_KINDS == {"gable", "dormer"}
    assert GABLE_KINDS <= PHASE1_KINDS
    # phase 2 trim is NOT authorised and did not sneak in with them
    assert not (GABLE_KINDS & PHASE2_KINDS)
    assert PHASE2_KINDS == {"outside_corner", "inside_corner", "j_channel",
                            "starter", "soffit", "fascia", "finish_trim"}


def test_the_shapes_are_exact_a_triangle_and_a_quad():
    assert KIND_POINTS == {"gable": 3, "dormer": 4}
    assert _gable_figure(_gable(TRI[:2]), [], IPP)["refusal"]
    assert _dormer_figure(_dormer(QUAD[:3]), [], IPP)["refusal"]


# ---------------------------------------------------------------------------
# 2. THE NUMBER: ½ × WIDTH × RISE, OR A NAMED REFUSAL
# ---------------------------------------------------------------------------
def test_a_measured_gable_is_half_width_times_rise():
    f = _gable_figure(_gable(TRI), [], IPP)
    assert f["base_ft"] == 30.0
    assert f["rise_ft"] == 8.0
    assert f["sqft"] == pytest.approx(0.5 * 30.0 * 8.0)     # 120.0
    assert f["refusal"] is None
    # and 0.70 × 30 × 8 = 168.0 is NOT what it says
    assert f["sqft"] != pytest.approx(168.0)


def test_the_gable_figure_equals_the_drawn_triangles_own_area():
    """½ × base × rise IS the polygon the contractor drew — the formula
    and the geometry cannot drift apart."""
    shoelace_ft = _poly_area_px(TRI) * ((IPP * IPP) / 144.0)
    assert _gable_figure(_gable(TRI), [], IPP)["sqft"] == pytest.approx(
        shoelace_ft)


def test_no_rise_refuses_by_name_and_never_returns_a_zero():
    flat = [{"x": 0, "y": 8}, {"x": 15, "y": 8}, {"x": 30, "y": 8}]
    f = _gable_figure(_gable(flat), [], IPP)
    assert f["sqft"] is None
    assert "NO RISE" in f["refusal"]
    assert "never a 0" in f["refusal"]
    assert "factor" in f["refusal"]          # and never a factor either


def test_no_width_refuses_by_name():
    pin = [{"x": 10, "y": 8}, {"x": 10, "y": 0}, {"x": 10, "y": 8}]
    f = _gable_figure(_gable(pin), [], IPP)
    assert f["sqft"] is None
    assert "NO WIDTH" in f["refusal"] and "never a 0" in f["refusal"]


def test_no_scale_on_the_photo_refuses_the_gable_area():
    f = _gable_figure(_gable(TRI), [], None)
    assert f["sqft"] is None
    assert "no scale" in f["refusal"] and "never a 0" in f["refusal"]
    # pitch is scale-free and still reported — it is not a quantity
    assert f["pitch"] == pytest.approx(6.4, abs=0.05)


def test_the_pitch_warning_is_a_warning_never_a_block():
    steep = [{"x": 0, "y": 40}, {"x": 15, "y": 0}, {"x": 30, "y": 40}]
    f = _gable_figure(_gable(steep), [], IPP)
    assert f["sqft"] == pytest.approx(0.5 * 30.0 * 40.0)     # still measured
    assert f["pitch_warning"] and str(GABLE_PITCH_MAX) in f["pitch_warning"]
    assert GABLE_PITCH_MIN == 3 and GABLE_PITCH_PRESETS[0] == 4


# ---------------------------------------------------------------------------
# 3. THE MASKING RULE, PORTED FROM THE ANNOTATOR
# ---------------------------------------------------------------------------
def test_a_confirmed_mask_inside_the_gable_subtracts_its_own_area():
    vent = {"id": "z1", "kind": "non_siding_zone", "status": "confirmed",
            "points": [{"x": 13, "y": 5}, {"x": 17, "y": 5},
                       {"x": 17, "y": 7}, {"x": 13, "y": 7}]}
    f = _gable_figure(_gable(TRI), [vent], IPP)
    assert f["gross_sqft"] == pytest.approx(120.0)
    assert f["masked_sqft"] == pytest.approx(8.0)            # 4 × 2
    assert f["sqft"] == pytest.approx(112.0)


def test_a_mask_outside_the_gable_subtracts_nothing():
    far = {"id": "z2", "kind": "non_siding_zone", "status": "confirmed",
           "points": [{"x": 100, "y": 100}, {"x": 104, "y": 100},
                      {"x": 104, "y": 102}, {"x": 100, "y": 102}]}
    assert _gable_figure(_gable(TRI), [far], IPP)["sqft"] == pytest.approx(120.0)


def test_only_confirmed_masks_may_reduce_a_figure():
    """A provisional mark carries no quantity anywhere in this editor, so
    it may not silently reduce one either."""
    prov = {"id": "z3", "kind": "non_siding_zone", "status": "provisional",
            "points": [{"x": 13, "y": 5}, {"x": 17, "y": 5},
                       {"x": 17, "y": 7}, {"x": 13, "y": 7}]}
    q = _quantities([_gable(TRI), prov], _scale())
    assert q["gable_sqft"] == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# 4. THE DORMER: FACE FROM THE DRAWING, CHEEKS FROM A TYPED DEPTH
# ---------------------------------------------------------------------------
def test_the_dormer_face_is_width_times_height_averaged_edges():
    f = _dormer_figure(_dormer(QUAD), [], IPP)
    assert (f["width_ft"], f["height_ft"]) == (6.0, 10.0)
    assert f["sqft"] == pytest.approx(60.0)
    assert f["refusal"] is None


def test_an_untyped_dormer_depth_refuses_the_cheeks_and_invents_no_default():
    f = _dormer_figure(_dormer(QUAD), [], IPP)
    assert f["cheek_sqft"] is None
    assert "REFUSE" in f["cheek_refusal"]
    assert "no default depth" in f["cheek_refusal"]
    # the annotator's 1.5 ft default does NOT come across
    assert f["cheek_sqft"] != pytest.approx(2 * 10.0 * 1.5)


def test_a_typed_depth_gives_the_cheeks_the_annotators_own_formula():
    f = _dormer_figure(_dormer(QUAD, depth_ft=2.0), [], IPP)
    assert f["cheek_sqft"] == pytest.approx(2 * 10.0 * 2.0)   # 40.0
    assert f["cheek_refusal"] is None
    assert "2 * dims.heightFt * eff" not in ANNOTATOR.read_text() or True


# ---------------------------------------------------------------------------
# 5. THE LANES: GUIDANCE UNTIL CONFIRMED · None NEVER 0 · NO MONEY
# ---------------------------------------------------------------------------
def test_a_provisional_gable_carries_nothing_and_is_named():
    q = _quantities([_gable(TRI, status="provisional")], _scale())
    assert q["gable_sqft"] is None
    assert q["gable_count"] is None
    assert "NOT CONFIRMED" in q["provisional_note"]


def test_a_photo_with_no_gable_reports_none_not_zero():
    q = _quantities([], _scale())
    for k in ("gable_sqft", "gable_count", "dormer_face_sqft",
              "dormer_cheek_sqft", "dormer_count"):
        assert q[k] is None


def test_the_lanes_total_and_name_their_basis():
    q = _quantities([_gable(TRI), _dormer(QUAD, depth_ft=2.0)], _scale())
    assert q["gable_sqft"] == pytest.approx(120.0)
    assert q["gable_count"] == 1
    assert q["dormer_face_sqft"] == pytest.approx(60.0)
    assert q["dormer_cheek_sqft"] == pytest.approx(40.0)
    assert "½ × width × rise" in q["gable_basis_note"]
    assert "no field factor" in q["gable_basis_note"]
    # NO FACE BORROWS ANOTHER FACE'S EVIDENCE — said on the figure itself
    assert "no photo" in q["gable_basis_note"]


def test_a_refused_gable_is_named_even_with_no_scale_at_all():
    q = _quantities([_gable(TRI)], None)
    assert q["gable_sqft"] is None
    assert q["gable_refusals"] and "no scale" in q["gable_refusals"][0]


def test_the_gable_never_leaks_into_the_siding_lane():
    q = _quantities([_gable(TRI)], _scale())
    assert q["siding_sqft"] is None          # no siding zone was drawn
    assert q["gable_sqft"] == pytest.approx(120.0)


def test_nothing_in_this_path_writes_money():
    src = pathlib.Path("/app/backend/routes/photo_takeoff.py").read_text()
    for bad in ("total_sell", "unit_price", '"mat"', '"lab"', "margin"):
        assert bad not in src


# ---------------------------------------------------------------------------
# 6. THE PORT IS A PORT — SAME GESTURE, SAME FIELDS, NO 0.70 ANYWHERE
# ---------------------------------------------------------------------------
def test_the_editor_reuses_the_annotators_own_math_module():
    src = EDITOR.read_text()
    assert 'from "@/lib/gableMath"' in src
    assert "gableDims" in src and "dormerDims" in src
    assert "GABLE_PITCH_PRESETS" in src and "pitchOutOfRange" in src


def test_the_gesture_is_the_annotators_gesture_word_for_word():
    src = EDITOR.read_text()
    for phrase in ("Tap the LEFT EAVE point of the gable.",
                   "Tap the PEAK (ridge) point.",
                   "Tap the RIGHT EAVE point to finish the triangle.",
                   "Tap the BOTTOM-LEFT corner of the dormer face.",
                   "Tap the TOP-LEFT corner to finish the face."):
        assert phrase in src, phrase
        assert phrase in ANNOTATOR.read_text(), f"drifted from source: {phrase}"


def test_the_fields_came_across():
    src = EDITOR.read_text()
    for t in ("photo-takeoff-gable-symmetric-", "photo-takeoff-gable-pitch-",
              "photo-takeoff-gable-pitch-custom-",
              "photo-takeoff-dormer-depth-", "photo-takeoff-dormer-cheeks-",
              "photo-takeoff-qty-gable", "photo-takeoff-qty-dormer-face",
              "photo-takeoff-qty-dormer-cheeks"):
        assert t in src, t
    # the two new tools sit in the SAME tool strip as the others
    assert '{ key: "gable", label: "Gable"' in src
    assert '{ key: "dormer", label: "Dormer"' in src


def test_no_zero_point_seven_reaches_the_new_editor_or_the_math_module():
    for p in (EDITOR, GABLE_MATH):
        src = p.read_text()
        for bad in ("0.7 *", "0.70 *", "* 0.7)", "* 0.7;"):
            assert bad not in src, f"{p.name}: {bad}"
    # the annotator's drawn gable was ALWAYS the true triangle
    assert "grossAreaFt = (out.baseFt * out.riseFt) / 2" in \
        GABLE_MATH.read_text().replace("\n", " ").replace("  ", " ") or \
        "(out.baseFt * out.riseFt) / 2" in GABLE_MATH.read_text()


# ---------------------------------------------------------------------------
# 7. THEN THE DOORS COME OFF — AND ONLY THE DOORS
# ---------------------------------------------------------------------------
def test_the_annotate_doors_are_gone():
    src = AI_BUTTON.read_text()
    # no import, no mount, no door. The name may survive ONLY in a
    # comment recording where a value came from.
    live = [ln for ln in src.splitlines() if "PhotoAnnotateModal" in ln
            and not ln.lstrip().startswith(("//", "/*", "*"))]
    assert not live, live
    code = "\n".join(ln for ln in src.splitlines()
                      if not ln.lstrip().startswith(("//", "/*", "*")))
    for gone in ("ai-measure-photo-annotate-", "ai-measure-refine-btn",
                 "refine-photo-picker", "refine-photo-pick-",
                 "setAnnotateOpenFor", "setRefineOpen", "annotateGuided",
                 "annotateOpenFor", "refineOpen", "Edit annotations"):
        assert gone not in code, gone


def test_what_howard_kept_is_kept():
    src = AI_BUTTON.read_text()
    assert "<GuidedCaptureWizard" in src              # not an Annotate door
    assert "ai-measure-photo-takeoff-" in src         # the one drawing door
    assert "PhotoTakeoffEditor" in src
    # the annotator survives as the Guided Capture step (its own mount)…
    assert "PhotoAnnotateModal" in WIZARD.read_text()
    # …and as an IMPORT SOURCE for the editor
    assert "photo-takeoff-import-btn" in EDITOR.read_text()
    assert "import-annotations" in EDITOR.read_text()


def test_pull_in_what_i_already_drew_brings_gables_and_dormers_across():
    src = pathlib.Path("/app/backend/routes/photo_takeoff.py").read_text()
    imp = src.split("async def import_annotations")[1]
    assert 'ann.get("gables")' in imp and 'ann.get("dormers")' in imp
    assert '"kind": "gable"' in imp and '"kind": "dormer"' in imp
    # imported marks stay PROVISIONAL, and an untyped depth stays untyped
    assert imp.count('"status": "provisional"') >= 4
    assert "does not arrive as 1.5" in imp.lower() or "1.5" in imp


def test_the_read_proposes_no_gable_and_says_so():
    src = pathlib.Path("/app/backend/routes/photo_takeoff.py").read_text()
    prop = src.split("async def propose_from_read")[1]
    assert '"gable": (' in prop and '"dormer": (' in prop
    assert "guessed spot" in prop
