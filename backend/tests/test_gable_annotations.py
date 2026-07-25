"""GABLE / ABOVE-EAVE MEASUREMENT SUPPORT (ruled 2026-07-24).

Pinned contract:
  • Add Gable mode in the photo annotator: 3 taps (left eave → peak →
    right eave), symmetric default ON, pitch presets 4/12–12/12 + custom,
    draggable points, translucent triangle, live dims label, gentle
    warning outside 3/12–18/12, multiple gables per photo, NO-SIDING
    masks inside the triangle subtract from its area.
  • Scale ladder: WALL scale anchor first, WINDOW anchor second — no
    anchor → dims pend, the triangle still saves.
  • Takeoff landing (ruled): structured rows persist on the run doc
    (contractor_gables) + burn into the photo as ground truth; Field
    Verify shows separate rows; NEVER auto-injected into derivation.
  • Ridge cross-check tolerance 1.0 ft (ruled) — gentle amber, never a
    block.
  • Elevation sheets: labeled TAPED-class callout per contractor gable.
  • The rectangular-house workflow is untouched — the tool only appears
    when tapped.
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


class TestGableMathPins:
    def test_pitch_presets_and_warning_range(self):
        assert "GABLE_PITCH_PRESETS = [4, 5, 6, 7, 8, 9, 10, 12]" in MATH
        assert "GABLE_PITCH_MIN = 3" in MATH
        assert "GABLE_PITCH_MAX = 18" in MATH

    def test_ridge_tolerance_is_one_foot_ruled(self):
        assert "RIDGE_TOLERANCE_FT = 1.0" in MATH
        assert "export function crossCheckRidges" in MATH

    def test_area_formula_and_mask_subtraction(self):
        # area = base × rise / 2; masks inside the triangle subtract
        assert "(out.baseFt * out.riseFt) / 2" in MATH
        assert "export function gableNetArea" in MATH
        assert "pointInTriangle" in MATH

    def test_scale_ladder_wall_then_window(self):
        assert "for (const ref of [reference, windowReference])" in MATH


class TestAnnotatorPins:
    def test_gable_mode_exists_and_is_optional(self):
        assert 'const MODE_GABLE = "gable"' in MODAL
        assert 'data-testid="annotate-mode-gable"' in MODAL

    def test_three_tap_flow_with_hints(self):
        assert "Tap the LEFT EAVE point" in MODAL
        assert "Tap the PEAK (ridge) point" in MODAL
        assert "Tap the RIGHT EAVE point" in MODAL

    def test_symmetric_default_on_and_toggle(self):
        assert "symmetric: true" in MODAL
        assert "gable-symmetric-" in MODAL
        assert "Symmetric gable" in MODAL

    def test_pitch_both_directions_live(self):
        # preset moves the peak; peak drag re-derives pitch (pitch_set cleared)
        assert "applyGablePitch" in MODAL
        assert "(basePx / 2) * (pitch / 12)" in MODAL
        assert "moveGablePoint" in MODAL
        assert "pitch_set: null" in MODAL
        assert "gable-pitch-select-" in MODAL
        assert "gable-pitch-custom-" in MODAL

    def test_draggable_points(self):
        assert "gableDrag" in MODAL

    def test_gentle_pitch_warning(self):
        assert "gable-pitch-warning-" in MODAL
        assert "outside the usual 3/12" in MODAL and "18/12 range" in MODAL

    def test_no_scale_still_saves(self):
        assert "gable-no-scale-warning" in MODAL
        assert "The triangle still saves" in MODAL

    def test_save_carries_gables(self):
        assert "gables: localGables" in MODAL


class TestPipelinePins:
    def test_burned_ground_truth_sentence(self):
        assert "GREEN TRIANGLES marked GABLE are CONTRACTOR-MEASURED" in BURN
        assert "GROUND TRUTH" in BURN

    def test_launch_sends_structured_rows_and_cross_check(self):
        assert 'fd.append("contractor_gables"' in AIBTN
        assert "crossCheckRidges(risesByElevation)" in AIBTN
        assert "toast.warning(ridgeWarn" in AIBTN  # gentle, never a block

    def test_backend_accepts_and_persists(self):
        assert "contractor_gables: Optional[str] = Form(None)" in AIM_PY
        assert '"contractor_gables": parse_contractor_gables(contractor_gables)' in AIM_PY
        # latest-for-estimate exposes them to Field Verify
        assert '"contractor_gables": doc.get("contractor_gables") or []' in AIM_PY

    def test_field_verify_rows_and_ridge_warning(self):
        assert 'data-testid="field-verify-contractor-gables"' in FVC
        assert "contractor-gable-ridge-warning" in FVC
        assert "not auto-injected into the estimate" in FVC

    def test_sheet_callout(self):
        assert 'data-testid="elevation-contractor-gable-callout"' in SHEET


class TestParseContractorGables:
    def test_valid_rows_clamped(self):
        from routes.ai_measure import parse_contractor_gables
        rows = parse_contractor_gables(
            '[{"elevation":"Front","pitch":6.04,"base_ft":24.02,"rise_ft":6.0,'
            '"area_ft":72.06,"masked_ft":0,"photo":"p1.jpg"}]')
        assert rows == [{"elevation": "front", "pitch": 6.0, "base_ft": 24.0,
                         "rise_ft": 6.0, "area_ft": 72.1, "masked_ft": 0,
                         "photo": "p1.jpg"}]

    def test_garbage_never_lands(self):
        from routes.ai_measure import parse_contractor_gables
        assert parse_contractor_gables(None) == []
        assert parse_contractor_gables("not json") == []
        assert parse_contractor_gables('{"a":1}') == []
        assert parse_contractor_gables('[1, "x"]') == []
        row = parse_contractor_gables('[{"base_ft":-5,"rise_ft":"abc"}]')[0]
        assert row["base_ft"] is None and row["rise_ft"] is None

    def test_capped_at_twenty(self):
        from routes.ai_measure import parse_contractor_gables
        import json
        rows = parse_contractor_gables(json.dumps([{"elevation": "front"}] * 50))
        assert len(rows) == 20


class TestSheetCalloutBinder:
    def test_filters_by_wall_and_labels_dims(self):
        from routes.elevation_sheets import contractor_gables_for
        run = {"contractor_gables": [
            {"elevation": "front", "base_ft": 24.0, "rise_ft": 6.0,
             "area_ft": 72.0, "pitch": 6.0, "masked_ft": 0},
            {"elevation": "rear", "base_ft": 12.0, "rise_ft": 4.0,
             "area_ft": 24.0, "pitch": 8.0, "masked_ft": 3.5},
            {"elevation": "left", "base_ft": None, "rise_ft": None,
             "area_ft": None, "pitch": 7.2, "masked_ft": 0},
        ]}
        front = contractor_gables_for(run, "front")
        assert len(front) == 1
        assert "base 24′ × rise 6′ = 72 ft²" in front[0]["label"]
        assert "6/12" in front[0]["label"]
        assert "photo-taped, scale-anchored" in front[0]["basis"]
        back = contractor_gables_for(run, "back")  # rear → back normalizer
        assert len(back) == 1 and "net of 3.5 ft² masks" in back[0]["label"]
        left = contractor_gables_for(run, "left")
        assert "no scale ref" in left[0]["label"] and "7.2/12" in left[0]["label"]
        assert contractor_gables_for(run, "right") == []
        assert contractor_gables_for({}, "front") == []
