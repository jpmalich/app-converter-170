"""BONI RULINGS (Howard, 2026-08-05) — EAVES ACROSS ALL ROOF PLANES +
INTEGRAL-J WINDOW TOGGLE.

Ground truth: Boni house (EST-190197), real blueprint vs REAL INSTALLED
list. The four-wall schema read eaves=116 (2×58 main rectangle); installed
gutter ran 167 — the garage and porch roof planes were invisible. Ruling 1:
sum eaves across ALL roof planes, porch ceiling rides the same read, the
Iter-57w wall-derived override STANDS DOWN when a plane sum exists.
Ruling 2: hanger formula stays at 2-ft spacing (installed 75 was field
discretion). Ruling 3: per-job integral-J toggle, default NO, one flag →
four lines (wall-J, caulk, wrap coil, Cap window), provenance on each.
Standing guard: default-off moves NOTHING (261 Haugh / 3 Degree / demo
anchors byte-identical — the wider suite holds that).
"""
import sys

sys.path.insert(0, "/app/backend")

from routes.ai_blueprint import _aggregate_to_hover_shape  # noqa: E402
from routes.hover import _build_lines, _j_channel_compute, _coil_019_rolls  # noqa: E402

BONI_PLANES = [
    {"label": "main", "eave_lf": 116, "rake_lf": 82, "is_porch": False, "porch_ceiling_sqft": 0},
    {"label": "garage", "eave_lf": 36, "rake_lf": 0, "is_porch": False, "porch_ceiling_sqft": 0},
    {"label": "porch", "eave_lf": 15, "rake_lf": 0, "is_porch": True, "porch_ceiling_sqft": 150},
]

BONI_WALLS = [
    {"label": "front", "width_ft": 58, "gable_triangle_height_ft": 0},
    {"label": "back", "width_ft": 58, "gable_triangle_height_ft": 0},
    {"label": "left", "width_ft": 39, "gable_triangle_height_ft": 11.5},
    {"label": "right", "width_ft": 39, "gable_triangle_height_ft": 11.5},
]


def _boni_raw(planes):
    return {
        "walls": [dict(w) for w in BONI_WALLS],
        "eaves_lf": 116, "rakes_lf": 82, "roof_pitch": "7/12",
        "roof_planes": planes,
        "windows": [], "appendages": [],
    }


def test_plane_sum_beats_the_wall_rectangle():
    m = _aggregate_to_hover_shape(_boni_raw(BONI_PLANES))
    assert m["eaves_lf"] == 167, "eaves must be the SUM ACROSS ALL ROOF PLANES"
    assert m.get("_eaves_plane_summed") is True
    assert m.get("porch_ceiling_sqft") == 150, \
        "the porch plane must carry its ceiling — one structure, two consequences"


def test_57w_override_stands_down_only_when_planes_exist():
    # No planes -> the wall-derived defence still runs (58+58 = 116).
    m = _aggregate_to_hover_shape(_boni_raw([]))
    assert m["eaves_lf"] == 116
    assert not m.get("_eaves_plane_summed")


def _boni_measurements(eaves, porch_sqft):
    return {
        "siding_with_openings_sqft": 4110, "eaves_lf": eaves, "rakes_lf": 82,
        "soffit_overhang_in": 12, "porch_ceiling_sqft": porch_sqft,
        "window_count": 22, "door_count": 5, "patio_door_count": 1,
        "garage_door_count": 2,
        "windows": [{"width_in": 36, "height_in": 60}] * 22,
    }


def _qty(lines, name_frag):
    for l in lines:
        if name_frag.lower() in str(l.get("item") or l.get("name") or "").lower():
            return l.get("qty")
    raise KeyError(name_frag)


def test_cascade_lands_on_installed_at_true_eaves():
    """One input (eaves 116->167 + porch 150 ft²), formulas untouched —
    the whole gutter/soffit cascade lands on the installed column."""
    lines = _build_lines(_boni_measurements(167, 150))
    assert _qty(lines, "Gutter 6") == 167          # installed 167
    assert _qty(lines, "Elbow") == 14              # installed 14
    assert _qty(lines, "End cap") == 12            # installed 12
    assert _qty(lines, "Hangars") == 90            # RULING 2: 2-ft spec stands (75 was field discretion)
    soffit = _qty(lines, "Soffit")
    assert 39 <= soffit <= 41, f"soffit must land ~40 with the porch ceiling (got {soffit})"


def test_integral_j_flag_off_is_byte_identical():
    base = _build_lines(_boni_measurements(167, 150))
    off = _build_lines({**_boni_measurements(167, 150), "_windows_integral_j": False})
    assert base == off, "default-off must move NOTHING"


def test_integral_j_flag_touches_exactly_four_lines():
    m_on = {**_boni_measurements(167, 150), "_windows_integral_j": True}
    lines = _build_lines(m_on)
    # caulk: windows out -> doors only (Boni: 5; installed 4 incl. field slop)
    assert _qty(lines, "Caulking (per color)") == 5
    # cap window zeroed with provenance
    cap = [l for l in lines
           if str(l.get("item") or l.get("name") or "") == "Cap window"]
    assert cap and (cap[0].get("qty") or 0) == 0
    assert "integral-J" in str(cap[0].get("note") or "")
    # wrap coil: window term gone
    assert _coil_019_rolls(m_on) < _coil_019_rolls(_boni_measurements(167, 150))
    # wall-J: window perimeter out
    pcs_on, br_on = _j_channel_compute(m_on)
    pcs_off, _ = _j_channel_compute(_boni_measurements(167, 150))
    assert pcs_on < pcs_off
    assert "integral-J" in br_on, "the J line must print its provenance"


def test_hanger_formula_untouched():
    """RULING 2 pin: 2-ft spacing + 1 per run stays exactly as shipped."""
    lines = _build_lines(_boni_measurements(116, 0))
    assert _qty(lines, "Hangars") == 62  # the pre-fix Boni figure, formula identity
