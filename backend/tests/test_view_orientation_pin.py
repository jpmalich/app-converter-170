"""VIEW-ORIENTATION PIN + PAIRED-FEATURE MIRROR (ruled 2026-07-26,
EST-986945 field-compare — horizontal axis).

Mechanism (evidence on record): the renderer's per-view axis convention
was ALREADY the standard exterior projection — the along_wall_ft datum
(extraction prompt iter 79j.40: left corner as viewed from OUTSIDE) is
each sheet's drawing-left corner, so openings map 1:1 on every view and
all four EST-986945 sheets matched their annotated site photos. The
user-visible defect was CROSS-VIEW: paired twin dormers bound horizontal
centers PER VIEW (quad-through-anchor / windows-centered jitter), so one
physical dormer drew on the SAME side of wall-center in BOTH opposite
side views (left 17.9' / right 17.5' on 37' walls) — physically
impossible for an off-center box seen from opposite sides. Pinned here:
  1. the per-view datum table (no future renderer change flips a view),
  2. the profile-side table's mirror property,
  3. the 1:1 opening x-mapping (no per-view flip),
  4. horizontal PAIRED-FEATURE MIRROR reconciliation (twin centers bind
     ONE mirrored span: center_here + center_opp = wall width).
"""
from pathlib import Path

from routes.elevation_sheets import (
    _PROFILE_SIDE,
    _VIEW_DATUM,
    _bind_dormers,
    _bind_openings,
)

SHEETS_SRC = (Path(__file__).resolve().parent.parent / "routes" / "elevation_sheets.py").read_text()
SHEET_JSX = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" /
             "pages" / "ElevationSheet.jsx").read_text()


# ── 1. per-view datum pin ──────────────────────────────────────────────

def test_view_datum_table_sealed():
    assert _VIEW_DATUM == {
        "front": {"drawing_left": "front-LEFT corner (left elevation adjoins)",
                  "drawing_right": "front-RIGHT corner (right elevation adjoins)"},
        "back":  {"drawing_left": "back-RIGHT corner (right elevation adjoins)",
                  "drawing_right": "back-LEFT corner (left elevation adjoins)"},
        "left":  {"drawing_left": "BACK corner",
                  "drawing_right": "FRONT corner"},
        "right": {"drawing_left": "FRONT corner",
                  "drawing_right": "BACK corner"},
    }


def test_orientation_note_in_payload_and_rendered():
    assert '"orientation_note"' in SHEETS_SRC
    assert "VIEW-ORIENTATION PIN" in SHEETS_SRC
    assert 'data-testid="elevation-orientation-note"' in SHEET_JSX


# ── 2. profile-side table mirror property ──────────────────────────────

def test_profile_side_table_sealed():
    assert _PROFILE_SIDE == {("front", "left"): "left", ("front", "right"): "right",
                             ("back", "left"): "right", ("back", "right"): "left",
                             ("left", "front"): "right", ("left", "back"): "left",
                             ("right", "front"): "left", ("right", "back"): "right"}


def test_profile_side_opposite_views_mirror():
    flip = {"left": "right", "right": "left"}
    opp = {"front": "back", "back": "front", "left": "right", "right": "left"}
    for (view, face), side in _PROFILE_SIDE.items():
        assert _PROFILE_SIDE[(opp[view], face)] == flip[side], (
            f"{view}/{face} draws {side} but {opp[view]}/{face} does not mirror")


# ── 3. opening x-mapping — 1:1, no per-view flip ───────────────────────

def test_opening_centers_pass_through_unflipped():
    for wall in ("front", "back", "left", "right"):
        raw = {"openings": [
            {"opening_id": f"{wall}-w1", "wall": wall, "type": "window",
             "width_in": 36, "height_in": 48, "along_wall_ft": 5.5},
            {"opening_id": f"{wall}-w2", "wall": wall, "type": "window",
             "width_in": 36, "height_in": 48, "along_wall_ft": 21.0},
        ]}
        out = _bind_openings(raw, wall, [])
        assert [o["center_ft"] for o in out] == [5.5, 21.0], wall


# ── 4. horizontal PAIRED-FEATURE MIRROR ────────────────────────────────

def _twin_raw(c_left, c_right, w=15.0, knee=3.5, wall_w=37.0):
    return {
        "walls": [{"label": "left", "width_ft": wall_w},
                  {"label": "right", "width_ft": wall_w}],
        "dormers": [{"face": "left", "width_ft": w, "knee_wall_height_ft": knee},
                    {"face": "right", "width_ft": w, "knee_wall_height_ft": knee}],
        "openings": [
            {"wall": "left", "type": "window", "on_dormer": True,
             "along_wall_ft": c_left, "width_in": 36, "height_in": 24,
             "bbox": {"x": 0.4, "y": 0.2, "w": 0.05, "h": 0.05}},
            {"wall": "right", "type": "window", "on_dormer": True,
             "along_wall_ft": c_right, "width_in": 36, "height_in": 24,
             "bbox": {"x": 0.5, "y": 0.2, "w": 0.05, "h": 0.05}},
        ],
    }


def test_paired_twin_centers_bind_one_mirrored_span():
    # red-house pattern: left 17.8 / right 20.0 on 37' walls — unreconciled
    # these disagree by 0.8' in the shared frame; reconciled they MIRROR
    raw = _twin_raw(17.8, 20.0)
    left, _ = _bind_dormers({}, raw, "left", 37.0, 8.0, None)
    right, _ = _bind_dormers({}, raw, "right", 37.0, 8.0, None)
    assert abs(left["center_ft"] - 17.4) < 0.05
    assert abs(right["center_ft"] - 19.6) < 0.05
    # the mirror invariant: one physical box, opposite exterior views
    assert abs((left["center_ft"] + right["center_ft"]) - 37.0) < 0.05
    for band in (left, right):
        assert "PAIRED-RECONCILED MIRROR" in band["center_tag"]
        assert "PAIRED-FEATURE MIRROR (ruled 2026-07-26)" in band["center_note"]


def test_unpaired_dormers_keep_their_own_centers():
    # width apart by 2' — NOT twins (AI tol 0.5'); centers stay per-view
    raw = _twin_raw(17.8, 20.0)
    raw["dormers"][1]["width_ft"] = 13.0
    left, _ = _bind_dormers({}, raw, "left", 37.0, 8.0, None)
    right, _ = _bind_dormers({}, raw, "right", 37.0, 8.0, None)
    assert left["center_ft"] == 17.8 and right["center_ft"] == 20.0
    assert "MIRROR" not in left["center_tag"]


def test_already_mirrored_twins_untouched():
    # perfect mirror (17.0 / 20.0 on 37') — reconciliation is a no-op,
    # no flag added (nothing disagreed)
    raw = _twin_raw(17.0, 20.0)
    left, _ = _bind_dormers({}, raw, "left", 37.0, 8.0, None)
    right, _ = _bind_dormers({}, raw, "right", 37.0, 8.0, None)
    assert left["center_ft"] == 17.0 and right["center_ft"] == 20.0
    assert "MIRROR" not in left["center_tag"]
    assert "MIRROR" not in right["center_tag"]
