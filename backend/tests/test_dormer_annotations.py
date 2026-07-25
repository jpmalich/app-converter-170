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
            '"area_ft":48.22,"masked_ft":0,"photo":"p1.jpg"}]')
        assert rows == [{"elevation": "front", "width_ft": 8.0,
                         "height_ft": 6.0, "area_ft": 48.2, "masked_ft": 0,
                         "photo": "p1.jpg"}]

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
