"""BONI RULINGS (Howard, 2026-08-05) — the vinyl/blueprint ground-truth
anchor (EST-190197), landed across TWO sends.

FIRST SEND: eaves across ALL roof planes (installed gutter 167 vs the
four-wall 116); per-job integral-J toggle, default NO, one flag → four
lines (wall-J, caulk, wrap coil, Cap window), provenance on each;
hangers stay at 2-ft spec (installed 75 was field discretion). Then the
EAVE/PORCH-J ruling: wall-side eave receiving channel + porch-ceiling
channel are REAL on vinyl/Ascend (soffit panels tuck into a wall
channel) and NEVER on LP SmartSide.

SECOND SEND (the garage wing): garage gable rakes ride the plane sum
(rakes 82 → 118); STANDARD PRACTICE ruling — J-channel runs on BOTH
wall AND rake, so the garage rake feeds the wall-J term. Corner LF is
per-corner heights SUMMED (main ~19-21 ft, garage ~10 ft — 261 Haugh
never-average doctrine) → oc_lf ~126 → OSC 11 = installed. Porch is the
FRONT ONLY, printed 99 ft² (16'6" × 6') — the rear is a WALKOUT DECK,
not a porch; no phantom rear porch props any number.

FIELD-ANOMALY FLAG (Howard's order — flag, never chase): installed
wall-J was 30, BELOW the standard-practice derivation. With the ruled
inputs the method derives 32 (garage rake +36 in the term, REAL porch
channel 28 LF from the printed 99 ft² — Howard's quoted 33 predated the
porch correction). Pending Howard's site visit; do NOT silently bend
the formula toward 30. Soffit derives 39 vs installed 40 — the 1-pc
residual is REAL and named (the phantom 150 porch used to paper it).

Standing guard: default-off toggle + blueprint-door geometry move
NOTHING on 261 Haugh / 3 Degree / demo (LP/HOVER anchors — the wider
suite holds byte-identity).
"""
import sys

sys.path.insert(0, "/app/backend")

from routes.ai_blueprint import _aggregate_to_hover_shape  # noqa: E402
from routes.hover import _build_lines, _j_channel_compute, _coil_019_rolls  # noqa: E402

# Ruled Boni geometry: garage gable caught (rake 36, both ends), porch
# is the front 99 ft² only (15 LF eave run × 6.6 ft effective depth).
BONI_PLANES = [
    {"label": "main", "eave_lf": 116, "rake_lf": 82, "gable_ends": 2,
     "is_porch": False, "porch_ceiling_sqft": 0},
    {"label": "garage", "eave_lf": 36, "rake_lf": 36, "gable_ends": 2,
     "is_porch": False, "porch_ceiling_sqft": 0},
    {"label": "porch", "eave_lf": 15, "rake_lf": 0, "gable_ends": 0,
     "is_porch": True, "porch_ceiling_sqft": 99},
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
    assert m.get("porch_ceiling_sqft") == 99, \
        "the porch plane carries its PRINTED ceiling (front porch only — no phantom rear porch)"


def test_garage_gable_rakes_ride_the_plane_sum():
    """SECOND SEND: the right elevation shows the garage wing under its
    own gable intersecting the main roof. Its rake_lf sums past the
    wall-rectangle 82; the gable-end census counts every triangular end."""
    m = _aggregate_to_hover_shape(_boni_raw(BONI_PLANES))
    assert m["rakes_lf"] == 118, "garage gable rakes must sum with the main pair"
    assert m.get("_gable_ends_plane_read") == 4
    # rake_lf 0 on secondary planes keeps the wall-derived 82 (max guard)
    blind = [dict(p, rake_lf=(82 if p["label"] == "main" else 0))
             for p in BONI_PLANES]
    m0 = _aggregate_to_hover_shape(_boni_raw(blind))
    assert m0["rakes_lf"] == 82


def test_outside_corner_lf_is_per_corner_summed_never_averaged():
    """SECOND SEND ruling: per-corner OWN heights, never averaged (261
    Haugh doctrine). Main-body corners ~19-21 ft + garage-wing corners
    ~10 ft sum to ~126 LF → ceil(126 / 12.5) = OSC 11 pcs = installed."""
    raw = _boni_raw(BONI_PLANES)
    raw["outside_corner_count"] = 8
    raw["outside_corner_lf"] = 126  # summed per corner off the elevations
    m = _aggregate_to_hover_shape(raw)
    assert m["outside_corner_lf"] == 126
    lines = _build_lines({**_boni_measurements(167, 99),
                          "outside_corner_lf": 126})
    assert _qty(lines, "Outside corners") == 11, \
        "vinyl OSC pieces must land installed 11 from the per-corner LF sum"


def test_57w_override_stands_down_only_when_planes_exist():
    # No planes -> the wall-derived defence still runs (58+58 = 116).
    m = _aggregate_to_hover_shape(_boni_raw([]))
    assert m["eaves_lf"] == 116
    assert not m.get("_eaves_plane_summed")


def _boni_measurements(eaves, porch_sqft):
    return {
        "siding_with_openings_sqft": 4110, "eaves_lf": eaves, "rakes_lf": 118,
        "soffit_overhang_in": 12, "porch_ceiling_sqft": porch_sqft,
        "window_count": 22, "door_count": 5, "patio_door_count": 1,
        "garage_door_count": 2,
        "windows": [{"width_in": 36, "height_in": 60}] * 22,
        "_roof_planes": [dict(p) for p in BONI_PLANES],
    }


def _qty(lines, name_frag):
    for l in lines:
        if name_frag.lower() in str(l.get("item") or l.get("name") or "").lower():
            return l.get("qty")
    raise KeyError(name_frag)


def test_cascade_lands_on_installed_at_true_eaves():
    """Ruled inputs (eaves 167, rakes 118, porch 99), formulas untouched —
    the gutter cascade lands the installed column. Soffit derives 39 vs
    installed 40: the 1-pc residual is REAL and NAMED (the phantom 150
    rear porch used to paper it — Howard killed it 2026-08-05)."""
    lines = _build_lines(_boni_measurements(167, 99))
    assert _qty(lines, "Gutter 6") == 167          # installed 167
    assert _qty(lines, "Elbow") == 14              # installed 14
    assert _qty(lines, "End cap") == 12            # installed 12
    assert _qty(lines, "Hangars") == 90            # RULING 2: 2-ft spec stands (75 was field discretion)
    assert _qty(lines, "Fascia/rake") == 285       # eaves 167 + rakes 118
    assert _qty(lines, "Soffit & fascia") == 39, \
        "soffit derives 39 at porch 99 — installed 40, residual 1 pc NAMED"


def test_integral_j_flag_off_is_byte_identical():
    base = _build_lines(_boni_measurements(167, 99))
    off = _build_lines({**_boni_measurements(167, 99), "_windows_integral_j": False})
    assert base == off, "default-off must move NOTHING"


def test_integral_j_flag_touches_exactly_four_lines():
    m_on = {**_boni_measurements(167, 99), "_windows_integral_j": True}
    lines = _build_lines(m_on)
    # caulk: windows out -> doors only (Boni: 5; installed 4 incl. field slop)
    assert _qty(lines, "Caulking (per color)") == 5
    # cap window zeroed with provenance
    cap = [l for l in lines
           if str(l.get("item") or l.get("name") or "") == "Cap window"]
    assert cap and (cap[0].get("qty") or 0) == 0
    assert "integral-J" in str(cap[0].get("note") or "")
    # wrap coil: window term gone
    assert _coil_019_rolls(m_on) < _coil_019_rolls(_boni_measurements(167, 99))
    # wall-J: window perimeter OUT, eave channel + garage rake IN.
    # ASSEMBLY SPLIT (Howard ruled 2026-08-07): the porch CEILING channel
    # moved to the Soffit-J line at full perimeter; this line keeps only
    # the porch WALL-J at wall-abutting length. Boni's porch holds no
    # real dims (plane rake 0) → square MINIMUM √99 ≈ 10, FLAGGED.
    # Pre-split this pin read 33 (porch full-perimeter 40 on the wall
    # line); now 31 — delta NAMED, not hidden. Installed 30 stays the
    # flagged field anomaly — never chased.
    pcs_on, br_on = _j_channel_compute(m_on)
    pcs_off, _ = _j_channel_compute(_boni_measurements(167, 99))
    assert pcs_on < pcs_off
    assert pcs_on == 31, \
        f"BONI standard-practice wall-J derives 31 post-split (got {pcs_on}); installed 30 is the flagged field anomaly"
    assert "integral-J" in br_on, "the J line must print its provenance"
    assert "eave/porch-J" in br_on, "the J line must print the channel provenance"
    assert "118 rakes" in br_on, "the garage rake must print inside the J term"


def test_eave_porch_j_is_family_scoped():
    """RULED 2026-08-05: the eave/porch-J term (wall-side eave receiving
    channel + porch ceiling channel) is REAL on vinyl and Ascend soffit
    systems and NEVER on LP SmartSide. This pin fails if it ever appears
    on an LP line or disappears from a vinyl/Ascend J line."""
    m = _boni_measurements(167, 99)
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
    # ASSEMBLY SPLIT (ruled 2026-08-07, supersedes full-perimeter-on-wall):
    # wall-J carries the porch WALL-ABUTTING length only — Boni holds no
    # real porch dims → square MINIMUM √99 ≈ 10 LF, FLAGGED (an area does
    # not determine a shape). The FULL-PERIMETER ceiling channel (40)
    # prints on the Soffit-J line instead.
    pcs, br = _j_channel_compute({**m, "_windows_integral_j": True})
    assert pcs == 31 and "10 porch wall-J MINIMUM" in br
    assert "wall-side length" in br and "does not determine a shape" in br, \
        "the wall-J porch term must print the MINIMUM flag (ruled 2026-08-07)"
    # Soffit-J line carries the ceiling channel at full perimeter.
    soffit_j = [l for l in lines if l["tab"] == "vinyl"
                and str(l.get("name") or "").startswith('3/4" Soffit J-Channel')]
    assert soffit_j, "vinyl Soffit J-Channel line missing"
    assert soffit_j[0]["qty"] == 26, \
        f"soffit-J = (167+118+40 porch perimeter)/12.5 = 26, got {soffit_j[0]['qty']}"
    s_note = str(soffit_j[0].get("note") or "")
    assert "FULL PERIMETER" in s_note and "porch ceiling channel" in s_note, \
        "the Soffit-J note must print the ceiling-channel convention"


def test_hanger_formula_untouched():
    """RULING 2 pin: 2-ft spacing + 1 per run stays exactly as shipped."""
    lines = _build_lines(_boni_measurements(116, 0))
    assert _qty(lines, "Hangars") == 62  # the pre-fix Boni figure, formula identity
