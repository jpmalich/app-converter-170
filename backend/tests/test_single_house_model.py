"""SINGLE HOUSE MODEL — vertical geometry (ruled 2026-07-26).

The per-view patch era ends: _dormer_solids reconciles each dormer ONCE
(W × KNEE × band × center, rung-aware), every view renders a PROJECTION.
Pinned consequences, each by construction:
  1. one dormer = one size on every view (two-size profiles impossible);
     equal-rung twin dims bind the PER-DIMENSION WORST CASE — flagged,
     never averaged (P3 precedent; W × KNEE feeds siding area);
  2. opposite-slope profiles on the same view sit LEVEL;
  3. the CLAMP IS RETIRED — roofline bounds FLAG, never relocate; a
     TAPED band re-derives the eave-view ridge UPWARD at the route;
  4. dormers SEAT on their roof plane in every projection (rendered
     plane, face-on views);
  5. per-wall grade datums stand — named on-sheet, with the implied
     grade slope printed when front/back ridge figures differ.
"""
from pathlib import Path

import pytest

from routes.elevation_sheets import _bind_dormers, _dormer_solids, _flag_band_vs_roof

SHEETS_SRC = (Path(__file__).resolve().parent.parent / "routes" / "elevation_sheets.py").read_text()
SHEET_JSX = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" /
             "pages" / "ElevationSheet.jsx").read_text()


def _twin_raw(w_l=14.1, k_l=3.4, w_r=15.1, k_r=3.8):
    return {
        "walls": [{"label": "left", "width_ft": 37.0},
                  {"label": "right", "width_ft": 37.0}],
        "dormers": [{"face": "left", "width_ft": w_l, "knee_wall_height_ft": k_l},
                    {"face": "right", "width_ft": w_r, "knee_wall_height_ft": k_r}],
        "openings": [
            {"wall": "left", "type": "window", "on_dormer": True,
             "along_wall_ft": 18.0, "width_in": 36, "height_in": 24,
             "bbox": {"x": 0.4, "y": 0.2, "w": 0.05, "h": 0.05}},
            {"wall": "right", "type": "window", "on_dormer": True,
             "along_wall_ft": 19.0, "width_in": 36, "height_in": 24,
             "bbox": {"x": 0.5, "y": 0.2, "w": 0.05, "h": 0.05}},
        ],
    }


RUN_QUADS = {"contractor_dormers": [
    {"elevation": "left", "width_ft": 14.1, "height_ft": 3.4},
    {"elevation": "right", "width_ft": 15.1, "height_ft": 3.8},
]}


# ── 1. one dormer = one size, worst case, never averaged ──────────────

def test_equal_rung_twins_bind_worst_case_dims_flagged():
    solids = _dormer_solids({}, _twin_raw(), RUN_QUADS)
    for face in ("left", "right"):
        s = solids[face]
        assert s["w"] == pytest.approx(15.1), "width = worst case, not mean 14.6"
        assert s["knee"] == pytest.approx(3.8), "knee = worst case, not mean 3.6"
        assert "PAIR worst-case" in s["w_tag"] and "PAIR worst-case" in s["k_tag"]
        joined = " ".join(s["dim_notes"])
        assert "worst case" in joined and "not averaged" in joined
        assert "14'-1" in joined and "15'-1" in joined  # both reads on record
        assert "Δ" in joined  # delta printed


def test_stronger_rung_governs_the_pair():
    # left is a contractor quad, right an AI read within tolerance
    run = {"contractor_dormers": [{"elevation": "left", "width_ft": 14.1, "height_ft": 3.4}]}
    solids = _dormer_solids({}, _twin_raw(w_r=14.3, k_r=3.6), run)
    assert solids["right"]["w"] == pytest.approx(14.1)
    assert solids["right"]["knee"] == pytest.approx(3.4)
    assert "pair-governed" in solids["right"]["w_tag"]
    assert "supersedes" in " ".join(solids["right"]["dim_notes"])


def test_one_size_on_every_view():
    raw = _twin_raw()
    face_l, _ = _bind_dormers({}, raw, "left", 37.0, 8.0, None, run=RUN_QUADS)
    face_r, _ = _bind_dormers({}, raw, "right", 37.0, 8.0, None, run=RUN_QUADS)
    _, prof_f = _bind_dormers({}, raw, "front", 27.0, 9.0, None, run=RUN_QUADS)
    _, prof_b = _bind_dormers({}, raw, "back", 27.0, 9.0, None, run=RUN_QUADS)
    sizes = {(face_l["width_ft"], face_l["knee_ft"]), (face_r["width_ft"], face_r["knee_ft"])}
    sizes |= {(p["width_ft"], p["knee_ft"]) for p in prof_f + prof_b}
    assert sizes == {(15.1, 3.8)}, f"two-size dormers are impossible: {sizes}"


# ── 2. opposite-slope profiles sit LEVEL on the same view ──────────────

def test_profiles_on_same_view_sit_level():
    raw = _twin_raw()
    for view in ("front", "back"):
        _, profs = _bind_dormers({}, raw, view, 27.0, 9.0, None, run=RUN_QUADS)
        bands = {(p["base_ft"], p["top_ft"]) for p in profs if p["base_ft"] is not None}
        assert len(profs) == 2 and len(bands) <= 1, (view, profs)


# ── 3. the clamp is retired — flag only, ridge re-derives upward ───────

def test_roofline_bounds_flag_only_never_relocate():
    band = {"base_ft": 10.8, "top_ft": 14.6, "vpos_tag": "TAPED (contractor quad)"}
    out = _flag_band_vs_roof(dict(band), 14.4)
    assert out["base_ft"] == 10.8 and out["top_ft"] == 14.6, "geometry relocated!"
    assert "FLAGGED" in out["top_note"] and "clamp retired" in out["top_note"]
    ok = _flag_band_vs_roof(dict(band), 15.0)
    assert ok.get("top_note") is None


def test_clamp_is_gone_and_ridge_rederives_in_route():
    assert "_clamp_band_to_roof" not in SHEETS_SRC, "the clamp must stay retired"
    assert "RIDGE RE-DERIVED UPWARD (clamp retired, ruled 2026-07-26)" in SHEETS_SRC
    assert "_flag_band_vs_roof(dormer, _ridge_now)" in SHEETS_SRC
    assert 'roofline_obj.get("kind") == "eave_ridge"' in SHEETS_SRC


# ── 4. seating — the roof plane renders under the face-on dormer ───────

def test_dormer_seats_on_a_rendered_roof_plane():
    assert 'data-testid="elevation-roof-plane"' in SHEET_JSX
    assert "DORMER SEATS ON THIS PLANE" in SHEET_JSX


# ── 5. per-wall grade datums — named, implied slope printed ────────────

def test_grade_datum_named_and_implied_slope_flagged():
    assert "heights above this wall's grade (per-wall datum)" in SHEETS_SRC
    assert "implied grade slope" in SHEETS_SRC
    assert 'data-testid="elevation-grade-note"' in SHEET_JSX
