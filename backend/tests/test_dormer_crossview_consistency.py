"""DORMER CROSS-VIEW CONSISTENCY + ROOFLINE BOUNDS + CONTAINMENT
(ruled 2026-07-26, EST-986945 field-compare defects).

Mechanism (evidence in PRD): contractor W×KNEE quads entered OUTSIDE the
reconciliation path — face-on bands bound each quad's own photo chain
(left 11.22 / right 10.39, never leveled), profiles kept AI dims/v-pos,
and nothing bounded a band at the drawn roof edge. One physical dormer =
ONE band on every view, pinned here.

PIN AMENDMENT (SINGLE HOUSE MODEL ruling, 2026-07-26 follow-up): the
CLAMP IS RETIRED — roofline bounds FLAG and never relocate (a taped
measurement is never crushed to fit a guess; the ridge re-derives
UPWARD at the route instead), and the reconciliation now lives in
_dormer_solids (one solid, every view a projection). The retired
per-view pins below are amended accordingly.
"""
from pathlib import Path

from routes.elevation_sheets import (
    CONTRACTOR_PAIR_TOL_W_FT,
    PAIRED_DORMER_TOL_FT,
    _flag_band_vs_roof,
)

SHEETS_SRC = (Path(__file__).resolve().parent.parent / "routes" / "elevation_sheets.py").read_text()
SHEET_JSX = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" /
             "pages" / "ElevationSheet.jsx").read_text()


def test_contractor_pair_tolerance_amended():
    # PIN AMENDMENT (2026-07-26): tap jitter — contractor twin identity
    # accepts width within 1'-3"; AI pairs keep the sealed 0.5'
    assert CONTRACTOR_PAIR_TOL_W_FT == 1.25
    assert PAIRED_DORMER_TOL_FT == 0.5


def test_roofline_bounds_flag_and_never_relocate():
    # AMENDED (clamp retired): the same 14.62-over-14.5 case now keeps
    # its geometry and prints the disagreement
    band = {"base_ft": 11.22, "top_ft": 14.62, "base_label": "x", "top_label": "y"}
    out = _flag_band_vs_roof(dict(band), 14.5)
    assert out["top_ft"] == 14.62 and out["base_ft"] == 11.22
    assert "FLAGGED" in out["top_note"] and "clamp retired" in out["top_note"]
    assert "14'-7" in out["top_note"]  # the read is preserved on record


def test_roofline_bounds_noop_inside_ridge():
    band = {"base_ft": 10.8, "top_ft": 14.2}
    assert _flag_band_vs_roof(dict(band), 14.5)["top_ft"] == 14.2
    assert _flag_band_vs_roof(dict(band), 14.5).get("top_note") is None


def test_contractor_quads_enter_reconciliation():
    # AMENDED: the reconciliation is the SINGLE HOUSE MODEL —
    # contractor quads enter _dormer_solids as a rung above the AI chain,
    # bands level across the pair, and every view projects the one solid
    assert 'cq = c_rows.get(face)' in SHEETS_SRC
    assert "PAIRED-RECONCILED LEVEL" in SHEETS_SRC
    assert "def _dormer_solids(" in SHEETS_SRC
    assert "solids = _dormer_solids(est, raw, run," in SHEETS_SRC
    # flag-only bounds at the route — the clamp stays retired
    assert "_flag_band_vs_roof(dormer, _ridge_now)" in SHEETS_SRC
    assert "_flag_band_vs_roof(p, _ridge_now) for p in (dormer_profiles or [])" in SHEETS_SRC


def test_on_dormer_window_containment_pinned():
    assert "ON-DORMER WINDOW CONTAINMENT (ruled 2026-07-26)" in SHEET_JSX
    assert "bottom = Math.min(bottom, dormerG.baseY - 1)" in SHEET_JSX
