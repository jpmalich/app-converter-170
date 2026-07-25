"""DORMER FACE MEASUREMENT SUPPORT (ruled 2026-07-25).

Mirror of the gable tool (test_gable_annotations.py). Pinned contract:
  • Add Dormer mode in the photo annotator: 4 taps (bottom-left →
    bottom-right → top-right → top-left) over the VERTICAL dormer face,
    all four corners draggable, translucent green rectangle (dashed — reads
    apart from gable triangles), live width × height = ft² label, multiple
    dormers per photo, NO-SIDING masks inside the rectangle subtract.
  • Scale ladder: the exact same WALL → WINDOW anchor system Gable and
    Wall already trust — no anchor → dims pend, the face still saves.
  • Takeoff landing (same rule as gables): structured rows persist on the
    run doc (contractor_dormers) + burn into the photo as ground truth;
    Field Verify shows separate "Contractor dormers" rows; NEVER
    auto-injected into derivation (no estimate line item).
  • Elevation sheets: labeled TAPED-class callout per contractor dormer,
    stacked under the gable callouts.
  • The existing Gable tool, window pins, masks and scale anchors are
    untouched — the tool only appears when tapped.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

FE = BACKEND.parent / "frontend" / "src"
MATH = (FE / "lib" / "gableMath.js").read_text()
MODAL = (FE / "components" / "estimate" / "PhotoAnnotateModal.jsx").read_text()
AIBTN = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
BURN = (FE / "lib" / "photoAnnotate.js").read_text()
FVC = (FE / "components" / "estimate" / "FieldVerifyCard.jsx").read_text()
SHEET = (FE / "pages" / "ElevationSheet.jsx").read_text()
AIM_PY = (BACKEND / "routes" / "ai_measure.py").read_text()


class TestDormerMathPins:
    def test_area_formula_and_mask_subtraction(self):
        # area = width × height; masks inside the quad subtract
        assert "out.grossAreaFt = out.widthFt * out.heightFt" in MATH
        assert "export function dormerNetArea" in MATH
        assert "export function pointInPolygon" in MATH

    def test_same_scale_ladder_as_gable(self):
        # dormerDims consumes the same inPerPx the gable ladder resolves
        assert "export function dormerDims(pts, inPerPx)" in MATH
        assert "for (const ref of [reference, windowReference])" in MATH

    def test_four_corner_shape(self):
        assert "pts.length !== 4" in MATH
        assert "[bl, br, tr, tl] = pts" in MATH


class TestAnnotatorPins:
    def test_dormer_mode_exists_and_is_optional(self):
        assert 'const MODE_DORMER = "dormer"' in MODAL
        assert 'data-testid="annotate-mode-dormer"' in MODAL

    def test_four_tap_flow_with_hints(self):
        assert "Tap the BOTTOM-LEFT corner" in MODAL
        assert "Tap the BOTTOM-RIGHT corner" in MODAL
        assert "Tap the TOP-RIGHT corner" in MODAL
        assert "Tap the TOP-LEFT corner" in MODAL

    def test_draggable_corners(self):
        assert "dormerDrag" in MODAL
        assert "moveDormerPoint" in MODAL

    def test_no_scale_still_saves(self):
        assert "dormer-no-scale-warning" in MODAL
        assert "The face still saves" in MODAL

    def test_save_carries_dormers(self):
        assert "dormers: localDormers" in MODAL

    def test_multiple_dormers_and_delete(self):
        assert "add another dormer" in MODAL
        assert "dormer-delete-" in MODAL

    def test_gable_tool_untouched(self):
        # the sealed gable pins still hold verbatim
        assert 'const MODE_GABLE = "gable"' in MODAL
        assert 'data-testid="annotate-mode-gable"' in MODAL
        assert "gables: localGables" in MODAL
        assert "gableDrag" in MODAL


class TestPipelinePins:
    def test_burned_ground_truth_sentence(self):
        assert "GREEN DASHED RECTANGLES marked DORMER are CONTRACTOR-MEASURED" in BURN
        assert "width, height AND position as GROUND TRUTH" in BURN

    def test_launch_sends_structured_rows(self):
        assert 'fd.append("contractor_dormers"' in AIBTN
        assert "dormerNetArea(dm, da.zones || []" in AIBTN

    def test_backend_accepts_and_persists(self):
        assert "contractor_dormers: Optional[str] = Form(None)" in AIM_PY
        assert '"contractor_dormers": parse_contractor_dormers(contractor_dormers)' in AIM_PY
        # latest-for-estimate exposes them to Field Verify
        assert '"contractor_dormers": doc.get("contractor_dormers") or []' in AIM_PY

    def test_field_verify_rows(self):
        assert 'data-testid="field-verify-contractor-dormers"' in FVC
        assert "contractor-dormer-row-" in FVC
        assert "Contractor dormers" in FVC

    def test_sheet_callout(self):
        assert 'data-testid="elevation-contractor-dormer-callout"' in SHEET


class TestParseContractorDormers:
    def test_valid_rows_clamped(self):
        from routes.ai_measure import parse_contractor_dormers
        rows = parse_contractor_dormers(
            '[{"elevation":"Front","width_ft":8.04,"height_ft":6.0,'
            '"area_ft":48.22,"masked_ft":0,"photo":"p1.jpg",'
            '"x_center_frac":0.51234,"y_bottom_frac":0.2,'
            '"width_frac":0.2,"height_frac":0.15}]')
        assert rows == [{"elevation": "front", "width_ft": 8.0,
                         "height_ft": 6.0, "area_ft": 48.2, "masked_ft": 0,
                         "photo": "p1.jpg", "x_center_frac": 0.5123,
                         "y_bottom_frac": 0.2, "width_frac": 0.2,
                         "height_frac": 0.15}]

    def test_fracs_clamped_to_unit_interval(self):
        from routes.ai_measure import parse_contractor_dormers
        row = parse_contractor_dormers(
            '[{"x_center_frac":1.5,"y_bottom_frac":-0.1,"width_frac":"x"}]')[0]
        assert row["x_center_frac"] is None
        assert row["y_bottom_frac"] is None
        assert row["width_frac"] is None

    def test_garbage_never_lands(self):
        from routes.ai_measure import parse_contractor_dormers
        assert parse_contractor_dormers(None) == []
        assert parse_contractor_dormers("not json") == []
        assert parse_contractor_dormers('{"a":1}') == []
        assert parse_contractor_dormers('[1, "x"]') == []
        row = parse_contractor_dormers('[{"width_ft":-5,"height_ft":"abc"}]')[0]
        assert row["width_ft"] is None and row["height_ft"] is None

    def test_capped_at_twenty(self):
        from routes.ai_measure import parse_contractor_dormers
        import json
        rows = parse_contractor_dormers(json.dumps([{"elevation": "front"}] * 50))
        assert len(rows) == 20


class TestSheetCalloutBinder:
    def test_filters_by_wall_and_labels_dims(self):
        from routes.elevation_sheets import contractor_dormers_for
        run = {"contractor_dormers": [
            {"elevation": "front", "width_ft": 8.0, "height_ft": 6.0,
             "area_ft": 48.0, "masked_ft": 0},
            {"elevation": "rear", "width_ft": 6.0, "height_ft": 5.0,
             "area_ft": 26.5, "masked_ft": 3.5},
            {"elevation": "left", "width_ft": None, "height_ft": None,
             "area_ft": None, "masked_ft": 0},
        ]}
        front = contractor_dormers_for(run, "front")
        assert len(front) == 1
        assert "width 8′ × height 6′ = 48 ft²" in front[0]["label"]
        assert "photo-taped, scale-anchored" in front[0]["basis"]
        back = contractor_dormers_for(run, "back")  # rear → back normalizer
        assert len(back) == 1 and "net of 3.5 ft² masks" in back[0]["label"]
        left = contractor_dormers_for(run, "left")
        assert "no scale ref" in left[0]["label"]
        assert contractor_dormers_for(run, "right") == []
        assert contractor_dormers_for({}, "front") == []

    def test_positioned_quad_flags_governs_drawn_band(self):
        from routes.elevation_sheets import contractor_dormers_for
        run = {"contractor_dormers": [
            {"elevation": "front", "width_ft": 8.0, "height_ft": 6.0,
             "area_ft": 48.0, "masked_ft": 0, "x_center_frac": 0.5},
        ]}
        assert "GOVERNS DRAWN BAND" in contractor_dormers_for(run, "front")[0]["label"]


RAW_ANCHORED = {
    "dormers": [{"face": "front", "width_ft": 17.0, "knee_wall_height_ft": 4.0,
                 "width_source": "estimated", "offset_x_ft": 0.0}],
    "openings": [{"wall": "front", "type": "window", "along_wall_ft": 10.0,
                  "height_in": 48.0, "on_dormer": False,
                  "bbox": {"x": 0.3, "y": 0.25, "w": 0.1, "h": 0.1},
                  "bbox_photo_idx": 1}],
}


def _quad_run(**over):
    row = {"elevation": "front", "width_ft": 8.0, "height_ft": 6.0,
           "area_ft": 48.0, "masked_ft": 0, "photo": "p2.jpg",
           "x_center_frac": 0.5, "y_bottom_frac": 0.2,
           "width_frac": 0.2, "height_frac": 0.15}
    row.update(over)
    return {"contractor_dormers": [row], "photo_paths": "p1.jpg,p2.jpg"}


class TestContractorQuadGovernsDrawnBand:
    """Ruled 2026-07-25 follow-up: the quad IS the drawn geometry."""

    def _bind(self, run, raw=None):
        from routes.elevation_sheets import _bind_dormers
        return _bind_dormers({}, raw or RAW_ANCHORED, "front", 40.0, 9.0,
                             {"ridge_ft": 16.0}, run=run)

    def test_quad_overrides_ai_band_dims_and_position(self):
        face_on, _ = self._bind(_quad_run())
        assert face_on["contractor_quad"] is True
        assert face_on["width_ft"] == 8.0 and face_on["knee_ft"] == 6.0
        assert face_on["width_tag"] == "TAPED (contractor quad)"
        # center: quad's own scale 8/0.2 = 40 ft/frac; window anchor at
        # frac 0.35 ↔ 10 ft → 10 + (0.5 − 0.35) × 40 = 16.0
        assert face_on["center_ft"] == 16.0
        assert face_on["center_tag"] == "TAPED (contractor quad)"
        # base: 80" + (0.25 − 0.2) × (6/0.15) × 12 = 104" → 8.67 ft
        assert face_on["base_ft"] == 8.67
        assert face_on["top_ft"] == 14.67
        assert "TAPED (contractor quad" in face_on["vpos_tag"]
        assert "CONTRACTOR DORMER QUAD GOVERNS" in face_on["basis"]
        assert face_on["top_note"] is None  # 14.67 ≤ ridge 16

    def test_quad_draws_even_when_ai_missed_the_dormer(self):
        raw = {"dormers": [], "openings": RAW_ANCHORED["openings"]}
        face_on, _ = self._bind(_quad_run(), raw=raw)
        assert face_on is not None and face_on["contractor_quad"] is True
        assert face_on["center_ft"] == 16.0

    def test_legacy_rows_without_fracs_fall_back_flagged(self):
        run = _quad_run(x_center_frac=None, y_bottom_frac=None,
                        width_frac=None, height_frac=None)
        face_on, _ = self._bind(run)
        assert face_on["width_ft"] == 8.0  # dims still govern
        assert face_on["center_ft"] == 20.0  # wall center
        assert "INDICATIVE" in face_on["center_tag"]
        assert "INDICATIVE" in face_on["vpos_tag"]

    def test_no_contractor_rows_leaves_ai_binding_untouched(self):
        face_on, _ = self._bind({"contractor_dormers": []})
        assert face_on is not None
        assert face_on.get("contractor_quad") is None
        assert face_on["width_ft"] == 17.0  # the AI read

    def test_center_clamped_inside_the_wall(self):
        face_on, _ = self._bind(_quad_run(x_center_frac=1.0))
        # unclamped: 10 + (1.0 − 0.35) × 40 = 36 → clamp max(40 − 4) = 36
        assert face_on["center_ft"] == 36.0

    def test_frontend_sends_position_fracs(self):
        assert "x_center_frac" in AIBTN and "y_bottom_frac" in AIBTN
        assert "width_frac" in AIBTN and "height_frac" in AIBTN
        # natural dims round-trip on the annotation save
        assert "imageDims: imageDims || prev[annotateOpenFor]?.imageDims" in AIBTN
