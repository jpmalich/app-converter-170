"""DORMER CROSS-VIEW CONSISTENCY + ROOFLINE BOUNDS + CONTAINMENT
(ruled 2026-07-26, EST-986945 field-compare defects).

Mechanism (evidence in PRD): contractor W×KNEE quads entered OUTSIDE the
reconciliation path — face-on bands bound each quad's own photo chain
(left 11.22 / right 10.39, never leveled), profiles kept AI dims/v-pos,
and nothing bounded a band at the drawn roof edge. One physical dormer =
ONE band on every view, pinned here.
"""
from pathlib import Path

from routes.elevation_sheets import (
    CONTRACTOR_PAIR_TOL_W_FT,
    PAIRED_DORMER_TOL_FT,
    _clamp_band_to_roof,
)

SHEETS_SRC = (Path(__file__).resolve().parent.parent / "routes" / "elevation_sheets.py").read_text()
SHEET_JSX = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" /
             "pages" / "ElevationSheet.jsx").read_text()


def test_contractor_pair_tolerance_amended():
    # PIN AMENDMENT (2026-07-26): tap jitter — contractor twin identity
    # accepts width within 1'-3"; AI pairs keep the sealed 0.5'
    assert CONTRACTOR_PAIR_TOL_W_FT == 1.25
    assert PAIRED_DORMER_TOL_FT == 0.5


def test_roofline_bounds_clamps_and_flags():
    band = {"base_ft": 11.22, "top_ft": 14.62, "base_label": "x", "top_label": "y"}
    out = _clamp_band_to_roof(band, 14.5)
    assert out["top_ft"] == 14.5
    assert out["base_ft"] == 11.1
    assert "BAND CLAMPED to the drawn roof edge" in out["top_note"]
    assert "14'-7" in out["top_note"]  # the photo-chain read is preserved


def test_roofline_bounds_noop_inside_ridge():
    band = {"base_ft": 10.8, "top_ft": 14.2}
    assert _clamp_band_to_roof(dict(band), 14.5)["top_ft"] == 14.2
    assert "top_note" not in _clamp_band_to_roof(dict(band), 14.5)


def test_contractor_quads_enter_reconciliation():
    # dims govern cross-view + leveled v-pos rung sits above the AI chain
    assert 'cq = c_rows.get(face)' in SHEETS_SRC
    assert 'elif face in c_vpos:' in SHEETS_SRC
    assert "PAIRED-RECONCILED LEVEL" in SHEETS_SRC
    # face-on band binds the SAME reconciled v-pos
    assert 'cd["base_ft"] = c_vpos[which]["base"]' in SHEETS_SRC
    # every view clamps at its drawn roofline
    assert "_clamp_band_to_roof(face_on, _ridge)" in SHEETS_SRC
    assert "_clamp_band_to_roof(p, _ridge) for p in profiles" in SHEETS_SRC


def test_on_dormer_window_containment_pinned():
    assert "ON-DORMER WINDOW CONTAINMENT (ruled 2026-07-26)" in SHEET_JSX
    assert "bottom = Math.min(bottom, dormerG.baseY - 1)" in SHEET_JSX
