"""P5 DORMERS pins — round three (C-5 ruling → field-compare FAIL fixes →
paired reconciliation + offset evidence + ratified anchor, 2026-07-22/23).

RULINGS PINNED HERE:
1. PAIRED-FEATURE RECONCILIATION (founding example: red house): matching
   dormers on OPPOSITE faces (width AND knee within 6") bind ONE
   reconciled band, drawn LEVEL on both — independent per-wall scales
   never produce asymmetric twins. PIN AMENDED (before → after):
   LEFT band 10.54–15.54 / RIGHT 10.14–15.14 → BOTH 10.34–15.34.
2. OFFSET EVIDENCE → CENTER LADDER: the binder bound wall-center +
   offset_x_ft (18.5' both walls, reconciler-rounded "offset 0"). The
   structured evidence (on-dormer window positions, bbox-consistent to
   ⅝"/2") shows LEFT ≈17.8', RIGHT ≈19.8'. RULED a binder fix: the
   windows-centered norm (already ratified for v-pos) + structured
   bboxes outrank the rounded claim. PIN AMENDED: center 18.5 → LEFT
   17.8', RIGHT 20.0' (tag: ESTIMATED windows-centered norm).
3. HEAD-ANCHOR 6'-8" (80"): RATIFIED CONTRACTOR-SPEC — pinned,
   re-ratification to change. A convention, not a promise.
4. SILL-BINDING EXTENSION (AUTHORIZED): doorless walls bind wall-window
   sills through the same head chain (LEFT W1/W3 29" · W5 30"; RIGHT W1
   40.7" · W3 37.2"). Corner-shot guard: position-less windows (no
   along_wall_ft) never carry or receive the chain (right W4–W6 stay "—",
   retiring a −94.1" nonsense bind caught in development).
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from routes.elevation_sheets import (  # noqa: E402
    PAIRED_DORMER_TOL_FT,
    WINDOW_HEAD_ANCHOR_IN,
    _bind_dormers,
    _dormer_vpos,
    _paired_dormer,
    detect_collisions,
)

API = "https://app-converter-170.preview.emergentagent.com/api"
REDHOUSE_EST = "673707d5-9b7e-4d8f-8eaf-63c86820f611"  # EST-910869
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"
SHEET_JSX = Path("/app/frontend/src/pages/ElevationSheet.jsx").read_text()


def test_head_anchor_constant_ratified_contractor_spec():
    """RATIFIED (Howard 2026-07-22): 6'-8" (80") — CONTRACTOR-SPEC,
    pinned; re-ratification to change."""
    assert WINDOW_HEAD_ANCHOR_IN == 80.0
    assert PAIRED_DORMER_TOL_FT == 0.5


def _left_openings():
    return [
        {"wall": "left", "type": "window", "height_in": 51, "photo_idx": 2,
         "along_wall_ft": 8.5, "bbox": {"x": 0.2375, "y": 0.5625, "w": 0.05625, "h": 0.125}},
        {"wall": "left", "type": "window", "height_in": 51, "photo_idx": 2,
         "along_wall_ft": 17.6, "bbox": {"x": 0.4375, "y": 0.5625, "w": 0.05625, "h": 0.125}},
        {"wall": "left", "type": "window", "height_in": 50, "photo_idx": 2,
         "along_wall_ft": 26.9, "bbox": {"x": 0.640625, "y": 0.5625, "w": 0.05625, "h": 0.1225}},
        {"wall": "left", "type": "window", "height_in": 38, "photo_idx": 2,
         "along_wall_ft": 14.9, "on_dormer": True, "dormer_face": "left",
         "bbox": {"x": 0.365625, "y": 0.3375, "w": 0.078125, "h": 0.0791666667}},
        {"wall": "left", "type": "window", "height_in": 36, "photo_idx": 2,
         "along_wall_ft": 20.7, "on_dormer": True, "dormer_face": "left",
         "bbox": {"x": 0.49375, "y": 0.3333333333, "w": 0.078125, "h": 0.0816666667}},
    ]


def _right_openings():
    return [
        {"wall": "right", "type": "window", "height_in": 40, "photo_idx": 7,
         "along_wall_ft": 13, "bbox": {"x": 0.29875, "y": 0.5458333333, "w": 0.0925, "h": 0.0916666667}},
        {"wall": "right", "type": "window", "height_in": 42, "photo_idx": 7,
         "along_wall_ft": 27, "bbox": {"x": 0.584375, "y": 0.5458333333, "w": 0.10625, "h": 0.1}},
        {"wall": "right", "type": "window", "height_in": 36, "photo_idx": 7,
         "along_wall_ft": 20, "on_dormer": True, "dormer_face": "right",
         "bbox": {"x": 0.439375, "y": 0.3333333333, "w": 0.096875, "h": 0.09}},
    ]


def _dormer(face):
    return {"face": face, "width_ft": 15, "knee_wall_height_ft": 5.0,
            "offset_x_ft": 0, "width_source": "direct_single_reading"}


def _raw_two_faces():
    return {"dormers": [_dormer("left"), _dormer("right")],
            "openings": _left_openings() + _right_openings()}


def test_vpos_per_wall_chains_exact():
    """Per-wall chains, at the run's own numbers: LEFT scale 408, band
    center 76.5" above head → 10.54–15.54; RIGHT scale 428, 71.7" →
    10.14–15.14. The RATIFIED anchor closes both."""
    raw = _raw_two_faces()
    vl = _dormer_vpos(raw, "left", 5.0)
    vr = _dormer_vpos(raw, "right", 5.0)
    assert vl["base_ft"] == pytest.approx(10.54, abs=0.02)
    assert vr["base_ft"] == pytest.approx(10.14, abs=0.02)
    assert "CONTRACTOR-SPEC" in vl["tag"] and "RATIFIED" in vl["basis"]


def test_paired_reconciliation_one_level_band_both_faces():
    """FOUNDING PIN: opposite-face twins bind ONE band drawn LEVEL —
    10.54/10.14 reconcile to 10.34; tops to 15.34. Both faces carry it."""
    raw = _raw_two_faces()
    assert _paired_dormer(raw, raw["dormers"][0]) is raw["dormers"][1]
    dl, _ = _bind_dormers({}, raw, "left", 37.0, 9.3, {"ridge_ft": 17.65})
    dr, _ = _bind_dormers({}, raw, "right", 37.0, 8.1, {"ridge_ft": 16.4})
    assert dl["base_ft"] == dr["base_ft"] == pytest.approx(10.34, abs=0.01)
    assert dl["top_ft"] == dr["top_ft"] == pytest.approx(15.34, abs=0.01)
    assert "PAIRED-RECONCILED" in dl["vpos_tag"] and "PAIRED-RECONCILED" in dr["vpos_tag"]
    assert "LEVEL" in dl["base_note"]


def test_paired_reconciliation_tolerance_gate():
    """Twins outside the 6" width/knee tolerance never reconcile —
    each face keeps its own chain."""
    raw = _raw_two_faces()
    raw["dormers"][1]["width_ft"] = 16  # 1' apart — beyond tolerance
    assert _paired_dormer(raw, raw["dormers"][0]) is None
    dl, _ = _bind_dormers({}, raw, "left", 37.0, 9.3, {"ridge_ft": 17.65})
    assert dl["base_ft"] == pytest.approx(10.54, abs=0.02)
    assert "PAIRED-RECONCILED" not in dl["vpos_tag"]


def test_paired_tape_closes_both_faces():
    """Tape on EITHER twin closes both (they are LEVEL by reconciliation);
    own-face tape still outranks the pair's."""
    raw = _raw_two_faces()
    est = {"lp_appendage_dims": {"dormer:right": {
        "base_ft": {"value": 10.6, "status": "user_measured"}}}}
    dl, _ = _bind_dormers(est, raw, "left", 37.0, 9.3, {"ridge_ft": 17.65})
    assert dl["base_ft"] == 10.6 and dl["vpos_tag"] == "TAPED (user-measured · paired)"
    dr, _ = _bind_dormers(est, raw, "right", 37.0, 8.1, {"ridge_ft": 16.4})
    assert dr["base_ft"] == 10.6 and dr["vpos_tag"] == "TAPED (user-measured)"


def test_center_ladder_windows_norm_outranks_rounded_offset():
    """OFFSET EVIDENCE ruling: on-dormer window positions (structured,
    bbox-consistent) outrank the reconciler's rounded offset_x_ft=0.
    LEFT midpoint (14.9+20.7)/2 = 17.8'; RIGHT single window = 20.0'."""
    raw = _raw_two_faces()
    dl, _ = _bind_dormers({}, raw, "left", 37.0, 9.3, {"ridge_ft": 17.65})
    dr, _ = _bind_dormers({}, raw, "right", 37.0, 8.1, {"ridge_ft": 16.4})
    assert dl["center_ft"] == pytest.approx(17.8, abs=0.01)
    assert dr["center_ft"] == pytest.approx(20.0, abs=0.01)
    assert dl["center_tag"] == "ESTIMATED (windows-centered norm)"
    # no on-dormer window positions → falls back to wall center + offset
    raw2 = {"dormers": [_dormer("left")], "openings": []}
    d2, _ = _bind_dormers({}, raw2, "left", 37.0, 9.3, {"ridge_ft": 17.65})
    assert d2["center_ft"] == 18.5 and d2["center_tag"] != "ESTIMATED (windows-centered norm)"


def test_binder_unresolved_falls_back_mid_slope_flagged():
    raw = {"dormers": [_dormer("left")]}
    d, _ = _bind_dormers({}, raw, "left", 37.0, 9.3,
                         {"kind": "eave_ridge", "ridge_ft": 16.3})
    assert d["vpos_tag"] == "UNRESOLVED"
    assert d["base_ft"] == pytest.approx(10.3, abs=0.01)


def test_plane_rule_dormer_never_guards_against_wall():
    dormer_w2 = {"name": "W2", "kind": "opening", "plane": "dormer:left",
                 "base": "b", "lo_ft": 12.82, "hi_ft": 16.98}
    wall_w3 = {"name": "W3", "kind": "opening", "plane": "wall",
               "base": "b", "lo_ft": 16.27, "hi_ft": 19.27}
    assert detect_collisions([dormer_w2, wall_w3]) == []
    assert len(detect_collisions([dormer_w2, dict(wall_w3, plane="dormer:left")])) == 1


# ---------- live: red house acceptance sheets ----------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def _sheet(session, which, est=REDHOUSE_EST):
    r = session.get(f"{API}/estimates/{est}/elevation-sheet/{which}", timeout=30)
    assert r.status_code == 200, f"{which}: {r.text}"
    return r.json()


def test_redhouse_left_reconciled_band_center_and_sills(session):
    """PINS AMENDED (before → after): band 10.54–15.54 → 10.34–15.34
    (paired-reconciled); center 18.5 → 17.8 (windows-centered norm);
    wall sills None → W1/W3 29" · W5 30" (sill-binding extension).
    Counts unchanged: 5 openings (5 windows)."""
    s = _sheet(session, "left")
    d = s["dormer"]
    assert d["base_ft"] == pytest.approx(10.34, abs=0.01)
    assert d["top_ft"] == pytest.approx(15.34, abs=0.01)
    assert "PAIRED-RECONCILED" in d["vpos_tag"]
    assert d["center_ft"] == pytest.approx(17.8, abs=0.01)
    assert d["center_tag"] == "ESTIMATED (windows-centered norm)"
    assert [o["tag"] for o in s["openings"]] == ["W1", "W2", "W3", "W4", "W5"]
    sills = {o["tag"]: o["sill_in"] for o in s["openings"]}
    assert sills["W1"] == pytest.approx(29.0, abs=0.3)   # wall, head chain
    assert sills["W3"] == pytest.approx(29.0, abs=0.3)
    assert sills["W5"] == pytest.approx(30.0, abs=0.3)
    assert sills["W2"] == pytest.approx(139.5, abs=0.3)  # dormer plane
    assert sills["W4"] == pytest.approx(140.2, abs=0.3)
    assert s["opening_counts"]["windows"] == 5
    assert s["collisions"] == []


def test_redhouse_right_reconciled_band_center_and_corner_guard(session):
    """PINS AMENDED: band 10.14–15.14 → 10.34–15.34 (LEVEL with left);
    center 18.5 → 20.0; W1 40.7" / W3 37.2" bound; W4–W6 (corner-shot,
    position-less) stay '—' — the −94.1" nonsense bind is retired."""
    s = _sheet(session, "right")
    d = s["dormer"]
    assert d["base_ft"] == pytest.approx(10.34, abs=0.01)
    assert d["top_ft"] == pytest.approx(15.34, abs=0.01)
    assert d["center_ft"] == pytest.approx(20.0, abs=0.01)
    sills = {o["tag"]: o["sill_in"] for o in s["openings"]}
    assert sills["W1"] == pytest.approx(40.7, abs=0.3)
    assert sills["W3"] == pytest.approx(37.2, abs=0.3)
    assert sills["W4"] is None and sills["W5"] is None and sills["W6"] is None
    assert sills["W2"] == pytest.approx(132.5, abs=0.3)
    assert s["opening_counts"]["windows"] == 6


def test_redhouse_profiles_level_both_slopes(session):
    """PHOTO PIN (Howard's ground truth): both dormer eaves LEVEL — all
    four profiles (front + back) carry the SAME reconciled band."""
    bands = set()
    for view in ("front", "back"):
        s = _sheet(session, view)
        assert len(s["dormer_profiles"]) == 2
        for p in s["dormer_profiles"]:
            bands.add((p["base_ft"], p["top_ft"]))
    assert bands == {(10.34, 15.34)}


def test_redhouse_front_roster_unchanged(session):
    f = _sheet(session, "front")
    assert f["dormer"] is None
    assert [o["tag"] for o in f["openings"]] == ["G1", "W1", "G2", "D1"]
    # door-anchored walls keep the door anchor — extension never fires
    w1 = next(o for o in f["openings"] if o["tag"] == "W1")
    assert w1["sill_in"] == pytest.approx(137.1, abs=0.3)


def test_undormered_fixture_unchanged(session):
    s = _sheet(session, "front", est=LETRICK_EST)
    assert s["dormer"] is None and s["dormer_profiles"] == []


# ---------- JSX wiring ----------

def test_sheet_jsx_dormer_wiring():
    assert "elevation-dormer" in SHEET_JSX
    assert "elevation-dormer-profile-" in SHEET_JSX
    assert "elevation-dormer-profile-roof-edge-" in SHEET_JSX
    assert "elevation-schedule-dormer-legend" in SHEET_JSX
    assert "_tagLabel" in SHEET_JSX
    assert "dormer.top_ft" in SHEET_JSX


def test_sheet_jsx_fascia_true_extent_and_dormer_components():
    """RULED 2026-07-23 (fascia×dormer defect + component rule):
    1. MECHANISM (named with evidence): the eave fascia band was a FIXED
       22px glyph — 15½" at the red house LEFT scale (17 px/ft) — while
       the dormer clears the eave by 12½" (17.7px). The band, not the
       dormer, disagreed with the sheet's own numbers. FIX: the band
       scales as a nominal 8" fascia/soffit assembly (fasciaBandH).
    2. COMPONENT RULE: a dormer is a small house — its eave edges render
       in the FASCIA/RAKE component color on faces AND profiles, over
       the black skeleton."""
    assert "const fasciaBandH = Math.max(8, (8 / 12) * ppf)" in SHEET_JSX
    assert "y={wallTop - fasciaBandH}" in SHEET_JSX and "height={fasciaBandH}" in SHEET_JSX
    assert "wallTop - 22" not in SHEET_JSX  # fixed-pixel band retired
    assert 'data-testid="elevation-dormer-eave-fascia"' in SHEET_JSX
    # both dormer eave edges carry the fascia component color
    eave = SHEET_JSX[SHEET_JSX.index("elevation-dormer-eave-fascia") - 220:]
    assert "stroke={C.fascia}" in eave[:260]
    roof_edge = SHEET_JSX[SHEET_JSX.index("elevation-dormer-profile-roof-edge-") - 220:]
    assert "stroke={C.fascia}" in roof_edge[:260]


LP_EST = "e452a988-83b8-4e6e-9537-1223d0ecbf6f"  # EST-910869-L


def test_sheet_jsx_profile_osc_gap_closed():
    """CLAIM-VS-RENDER (logged 2026-07-23, minor): face-on OSC was wired
    and rendering (DOM-verified: two #0D9488 3.5px verticals at the
    dormer edges); PROFILES were never wired — the handback claim outran
    the render there. Closed: face-to-cheek corner edge renders OSC on
    profiles too."""
    assert "elevation-dormer-profile-osc-" in SHEET_JSX
    osc = SHEET_JSX[SHEET_JSX.index("elevation-dormer-profile-osc-") - 220:]
    assert "stroke={C.osc}" in osc[:260]


def test_redhouse_wall_course_fill_counted(session):
    """SIDING FILL cause (one line, reported 2026-07-23): plain miss —
    the hatch keyed on TAPED exposure only; the run's counted courses
    (eave_courses_counted 29 ⇒ 111.6"/29 = 3.85" lap) were never
    consulted. Fixed: counted courses derive the exposure, basis
    'counted' (never claims 'taped')."""
    s = _sheet(session, "left")
    w = s["wall"]
    assert w["courses"] == 29
    assert w["exposure_in"] == pytest.approx(3.85, abs=0.01)
    assert w["exposure_basis"] == "counted"
    assert 'W.exposure_basis === "taped" ? "taped" : "counted"' in SHEET_JSX


def test_dormer_material_lines_flagged_non_priced(session):
    """RULED 2026-07-23: dormer fascia (eave widths: 15'×2 = 30 LF) and
    dormer OSC (2 posts × 5' knee × 2 dormers = 20 LF) join the material
    list FLAGGED and NON-PRICED — footage exists, list says so, pricing
    pending Howard's ruling. Rake/soffit stay off (pitch/overhang NOT READ)."""
    r = session.post(f"{API}/estimates/{LP_EST}/lp-package/preview", json={}, timeout=60)
    assert r.status_code == 200, r.text
    lines = {l["name"]: l for l in r.json()["lines"] if "Dormer" in l["name"]}
    fas = lines["Dormer fascia (eave)"]
    osc = lines["Dormer outside corners (OSC)"]
    assert fas["qty"] == 30.0 and fas["unit"] == "LF"
    assert osc["qty"] == 20.0 and osc["unit"] == "LF"
    for l in (fas, osc):
        assert l["non_priced"] is True
        assert l["pricing_status"] == "pending"
        assert l["unit_sell"] is None and l["line_sell"] is None
        assert "pricing pending ruling" in l["note"]
    assert not any("Dormer rake" in n or "Dormer soffit" in n for n in lines)
