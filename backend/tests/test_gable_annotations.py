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
        # "not auto-injected into the estimate" — keyed EN/ES since the
        # 2026-08-04 Spanish sweep (fv.gables.sub in dictionaries.js)
        assert "fv.gables.sub" in FVC

    def test_sheet_callout(self):
        assert 'data-testid="elevation-contractor-gable-callout"' in SHEET


class TestParseContractorGables:
    def test_valid_rows_clamped(self):
        from routes.ai_measure import parse_contractor_gables
        rows = parse_contractor_gables(
            '[{"elevation":"Front","pitch":6.04,"base_ft":24.02,"rise_ft":6.0,'
            '"area_ft":72.06,"masked_ft":0,"photo":"p1.jpg",'
            '"x_center_frac":0.51234,"y_eave_frac":0.6,"peak_x_frac":0.5,'
            '"base_frac":0.4,"rise_frac":0.2}]')
        assert rows == [{"elevation": "front", "pitch": 6.0, "base_ft": 24.0,
                         "rise_ft": 6.0, "area_ft": 72.1, "masked_ft": 0,
                         "photo": "p1.jpg", "x_center_frac": 0.5123,
                         "y_eave_frac": 0.6, "peak_x_frac": 0.5,
                         "base_frac": 0.4, "rise_frac": 0.2}]

    def test_fracs_clamped_to_unit_interval(self):
        from routes.ai_measure import parse_contractor_gables
        row = parse_contractor_gables(
            '[{"x_center_frac":1.5,"base_frac":-0.1,"peak_x_frac":"x"}]')[0]
        assert row["x_center_frac"] is None
        assert row["base_frac"] is None
        assert row["peak_x_frac"] is None

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

    def test_positioned_triangle_flags_governs_drawn_gable(self):
        from routes.elevation_sheets import contractor_gables_for
        run = {"contractor_gables": [
            {"elevation": "front", "base_ft": 24.0, "rise_ft": 6.0,
             "area_ft": 72.0, "pitch": 6.0, "masked_ft": 0,
             "x_center_frac": 0.5},
        ]}
        assert "GOVERNS DRAWN GABLE" in contractor_gables_for(run, "front")[0]["label"]


GB_RAW_ANCHORED = {
    "openings": [{"wall": "front", "type": "window", "along_wall_ft": 10.0,
                  "height_in": 48.0, "on_dormer": False,
                  "bbox": {"x": 0.3, "y": 0.25, "w": 0.1, "h": 0.1},
                  "bbox_photo_idx": 1}],
}


def _tri_run(**over):
    row = {"elevation": "front", "base_ft": 24.0, "rise_ft": 6.0,
           "area_ft": 72.0, "pitch": 6.0, "masked_ft": 0, "photo": "p2.jpg",
           "x_center_frac": 0.5, "y_eave_frac": 0.6, "peak_x_frac": 0.55,
           "base_frac": 0.4, "rise_frac": 0.2}
    row.update(over)
    return {"contractor_gables": [row], "photo_paths": "p1.jpg,p2.jpg"}


class TestContractorTriangleGovernsDrawnGable:
    """Ruled 2026-07-25 follow-up #2: the triangle IS the drawn gable —
    exact mirror of the dormer-quad governing model."""

    def _bands(self, run, raw=None):
        from routes.elevation_sheets import _contractor_gable_bands
        return _contractor_gable_bands(run, raw or GB_RAW_ANCHORED, "front", 40.0)

    def test_triangle_binds_dims_center_and_peak(self):
        bands = self._bands(_tri_run())
        assert len(bands) == 1
        b = bands[0]
        assert b["base_ft"] == 24.0 and b["rise_ft"] == 6.0
        assert b["tag"] == "TAPED (contractor triangle)"
        # center: triangle's own scale 24/0.4 = 60 ft/frac; window anchor
        # at frac 0.35 ↔ 10 ft → 10 + (0.5 − 0.35) × 60 = 19.0
        assert b["center_ft"] == 19.0
        assert b["center_tag"] == "TAPED (contractor triangle)"
        # asymmetric peak: (0.55 − 0.5) × 60 = 3.0 ft right of base center
        assert b["peak_offset_ft"] == 3.0
        assert "CONTRACTOR GABLE TRIANGLE GOVERNS" in b["basis"]

    def test_legacy_rows_without_fracs_fall_back_flagged(self):
        bands = self._bands(_tri_run(x_center_frac=None, peak_x_frac=None,
                                     base_frac=None, rise_frac=None))
        b = bands[0]
        assert b["base_ft"] == 24.0  # dims still govern
        assert b["center_ft"] == 20.0  # wall center
        assert "INDICATIVE" in b["center_tag"]
        assert b["peak_offset_ft"] == 0.0

    def test_no_anchor_windows_fall_back_flagged(self):
        bands = self._bands(_tri_run(), raw={"openings": []})
        assert "INDICATIVE" in bands[0]["center_tag"]

    def test_center_clamped_inside_the_wall(self):
        bands = self._bands(_tri_run(x_center_frac=1.0, peak_x_frac=1.0))
        # unclamped: 10 + (1.0 − 0.35) × 60 = 49 → clamp max(40 − 12) = 28
        assert bands[0]["center_ft"] == 28.0

    def test_multiple_gables_each_get_a_band(self):
        run = _tri_run()
        run["contractor_gables"].append(dict(run["contractor_gables"][0],
                                             x_center_frac=0.2, base_ft=12.0,
                                             base_frac=0.2, rise_ft=4.0))
        assert len(self._bands(run)) == 2

    def test_no_rows_returns_empty_ai_untouched(self):
        assert self._bands({"contractor_gables": []}) == []

    def test_payload_and_svg_replacement_wired(self):
        from pathlib import Path as _P
        es = (BACKEND / "routes" / "elevation_sheets.py").read_text()
        assert '"contractor_gable_bands": _contractor_gable_bands' in es
        sheet = (FE / "pages" / "ElevationSheet.jsx").read_text()
        # band[0] replaces the AI gable on gable-end views…
        assert "const gableGoverns = !!(rl && rl.kind === \"gable_end\" && cgb.length > 0)" in sheet
        assert "GOVERNS DRAWN GABLE" in sheet
        # …and extras/eave-view bands draw as standalone governed triangles
        assert "elevation-contractor-gable-triangle-" in sheet

    def test_frontend_sends_position_fracs(self):
        assert "y_eave_frac" in AIBTN and "peak_x_frac" in AIBTN
        assert "base_frac" in AIBTN and "rise_frac" in AIBTN
