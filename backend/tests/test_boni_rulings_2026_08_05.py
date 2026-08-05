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


def test_garage_gable_rakes_ride_the_plane_sum():
    """BONI SECOND SEND (Howard, 2026-08-05): the right elevation shows a
    separate garage gable / intersecting double gable. When the plane read
    returns its rake_lf, the plane sum overrides the wall-rectangle 82 —
    and the gable-end census reports how many ends the read carries."""
    planes = [
        {"label": "main", "eave_lf": 116, "rake_lf": 82, "gable_ends": 2,
         "is_porch": False, "porch_ceiling_sqft": 0},
        {"label": "garage", "eave_lf": 36, "rake_lf": 42, "gable_ends": 1,
         "is_porch": False, "porch_ceiling_sqft": 0},
        {"label": "porch", "eave_lf": 15, "rake_lf": 0, "gable_ends": 0,
         "is_porch": True, "porch_ceiling_sqft": 150},
    ]
    m = _aggregate_to_hover_shape(_boni_raw(planes))
    assert m["rakes_lf"] == 124, "garage gable rakes must sum with the main pair"
    assert m.get("_gable_ends_plane_read") == 3
    # rake_lf 0 on the secondary planes keeps the wall-derived 82 (max guard)
    m0 = _aggregate_to_hover_shape(_boni_raw(BONI_PLANES))
    assert m0["rakes_lf"] == 82


def test_outside_corner_lf_is_per_corner_summed_never_averaged():
    """BONI SECOND SEND: installed OSC = 11 pcs. 6 main-body corners at
    18 ft + 2 garage-wing corners at their OWN ~10 ft height = 128 LF →
    ceil(128 / 12.5) = 11. The 261 Haugh never-average doctrine applies:
    the aggregator passes the model's per-corner SUM straight through."""
    raw = _boni_raw(BONI_PLANES)
    raw["outside_corner_count"] = 8
    raw["outside_corner_lf"] = 128  # 6 × 18 + 2 × 10, summed per corner
    m = _aggregate_to_hover_shape(raw)
    assert m["outside_corner_lf"] == 128
    lines = _build_lines({**_boni_measurements(167, 150),
                          "outside_corner_lf": 128})
    assert _qty(lines, "Outside corners") == 11, \
        "vinyl OSC pieces must land installed 11 from the per-corner LF sum"


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
    # wall-J: window perimeter OUT + eave/porch channel IN → installed 30 EXACT
    pcs_on, br_on = _j_channel_compute(m_on)
    pcs_off, _ = _j_channel_compute(_boni_measurements(167, 150))
    assert pcs_on < pcs_off
    assert pcs_on == 30, \
        f"BONI ACCEPTANCE: wall-J must land installed 30 (got {pcs_on})"
    assert "integral-J" in br_on, "the J line must print its provenance"
    assert "eave/porch-J" in br_on, "the J line must print the channel provenance"


def test_eave_porch_j_is_family_scoped():
    """RULED 2026-08-05: the eave/porch-J term (wall-side eave receiving
    channel + porch ceiling channel) is REAL on vinyl and Ascend soffit
    systems and NEVER on LP SmartSide. This pin fails if it ever appears
    on an LP line or disappears from a vinyl/Ascend J line."""
    m = _boni_measurements(167, 150)
    lines = _build_lines(m)
    for tab in ("vinyl", "ascend"):
        j = [l for l in lines if l["tab"] == tab
             and "j-channel" in str(l.get("name") or "").lower()
             and "soffit" not in str(l.get("name") or "").lower()
             or (tab == "ascend" and l["tab"] == tab
                 and l.get("name") == "Ascend - J - Channel")]
        assert j, f"{tab} wall-J line missing"
        assert any("eave/porch-J" in str(l.get("note") or "") for l in j), \
            f"{tab} wall-J lost the eave/porch channel term"
    lp = [l for l in lines if l["tab"] == "lp_smart"]
    assert lp, "LP tab produced no lines"
    for l in lp:
        blob = f"{l.get('name') or ''} {l.get('note') or ''}"
        assert "eave/porch-J" not in blob, \
            f"eave/porch-J bled onto LP line: {l.get('name')}"
        assert "j-channel" not in str(l.get("name") or "").lower(), \
            f"LP must carry no J-channel line at all: {l.get('name')}"
    # exact plane geometry: porch plane 15 LF eave × 10 ft deep = 35 LF channel
    pcs, br = _j_channel_compute({
        **m, "_windows_integral_j": True,
        "_roof_planes": [{"label": "porch", "is_porch": True,
                          "eave_lf": 15, "porch_ceiling_sqft": 150}],
    })
    assert pcs == 30 and "35 porch ceiling channel" in br


def test_hanger_formula_untouched():
    """RULING 2 pin: 2-ft spacing + 1 per run stays exactly as shipped."""
    lines = _build_lines(_boni_measurements(116, 0))
    assert _qty(lines, "Hangars") == 62  # the pre-fix Boni figure, formula identity
