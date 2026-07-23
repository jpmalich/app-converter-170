"""Elevation Sheets LEFT/BACK/RIGHT (EL-2..EL-4) — Phase 2 pins
(ruled 2026-07-18, baseline 345aa68).

Pass criteria pinned here:
  • all four sheets 200; unknown label 404
  • stepped sides carry BOTH tape segments, each with its own courses ×
    exposure basis formula — no silent interpolation; step_note present
  • BACK binds sealed key EST-191890: width 54 TAPED, 9.92' = 28 × 4.25"
  • chase (back) annotated AI-READ, footprint untaped — NOT TO SCALE
  • deviation box per elevation wherever tape ≠ AI
  • CLOSED five-key opening contract {windows, doors, patio_doors, vents,
    garage_doors} (AMENDED by ruling 2026-07-20, Spec v2 C-6/C-7 — was
    three-key per 2026-07-18); the left wall's vent renders V-tagged with
    AI-READ position
  • verb machinery remove→reset pinned per sheet (LEFT, BACK) + cross-wall
    isolation (RIGHT untouched by BACK removals)
  • basis-line completeness: every rendered dimension names its basis —
    no untagged values on any sheet
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"   # Mark Letrick EST-373526
LETRICK_RUN = "d66794488ef848509446431b355db8e5"        # archived: elevation-sheet-pin

ALLOWED_TAGS = {"TAPED", "TAPED-DERIVED", "AI-READ ✓", "AI-READ ⚠", "ESTIMATED"}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def _sheet(session, which):
    r = session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/{which}", timeout=30)
    assert r.status_code == 200, f"{which}: {r.text}"
    return r.json()


def test_all_four_sheets_200_and_unknown_404(session):
    codes = {}
    for which in ("front", "left", "back", "right"):
        s = _sheet(session, which)
        codes[which] = s["sheet_code"]
        assert s["sheet"] == which
    assert codes == {"front": "EL-1", "left": "EL-2", "back": "EL-3", "right": "EL-4"}
    r = session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/roof", timeout=15)
    assert r.status_code == 404


def test_back_binds_sealed_key(session):
    s = _sheet(session, "back")
    w = s["wall"]
    assert w["width_ft"] == 54.0 and w["width_tag"] == "TAPED"
    assert "EST-191890" in w["width_source"]
    # 9.92' = 28 × 4.25" ÷ 12 — bound to the sealed key, never retyped
    assert w["height_ft"] == 9.92
    assert w["height_label"] == "9'-11\""
    assert w["height_tag"] == "TAPED-DERIVED"
    assert "28" in w["height_formula"] and "4.25" in w["height_formula"]
    assert w["courses"] == 28 and w["exposure_in"] == 4.25
    assert w["segments"] and len(w["segments"]) == 1
    assert w["step_note"] is None
    assert w["area_sqft"] == 535.7  # 54 × 9.92
    assert "EST-191890" in s["geometry_basis"]["walls"]


def test_back_chase_taped_dims_and_ratified_position(session):
    """Chase ratification (ruled 2026-07-19): dims TAPED via sealed-key
    amendment. POSITION — PIN AMENDED BY RULING 2026-07-19 (collision
    ruling, supersedes the AI corner-read binding of center 21.9'): the
    chase sits LEFT of D1 with a siding strip between — relationship
    CONFIRMED (human, photo); right edge ≈17" left of D1's trim edge —
    offset ESTIMATED (photo-scaled, untaped), entered via the ratify
    machinery (appendage:back door_offset_ft 1.417 photo_scaled). FRAME
    RESOLUTION (ruled close-out correction, 2026-07-19): the photo's
    600" WALL REF is the AI's 50' read; tape governs derivations, so the
    offset is stated on the TAPED 54' = 648" reference (648 ÷ 1589 px =
    0.4078"/px × 41.5 px = 16.9" → ≈17"). The run's D1 24.3' is a
    50'-frame coordinate — pixel positions cross-confirm the run only in
    its own frame (internal consistency, not absolute); D1 stays where
    the run put it per standing convention. D1 left edge 24.3'; the AI
    corner-read band (0.35–0.46 → center 21.9') stays ON RECORD as the
    flagged comparison. A later tape upgrades the offset by the normal
    amendment path."""
    s = _sheet(session, "back")
    ch = s["chase"]
    assert ch is not None
    assert "chase" in ch["note"].lower()
    assert ch["tag"] == "AI-READ ✓"
    assert ch["width_in"] == 64 and ch["depth_in"] == 31 and ch["height_in"] == 234.625
    assert ch["height_label"] == "19'-6⅝\""
    assert ch["dims_tag"] == "TAPED"
    assert "TAPED (2026-07-19)" in ch["footprint"]
    assert "ruled 2026-07-19" in ch["ratified"]
    # ratified door-relative position: 24.3 − 1.417 − 64/24 = 20.217 → 20.2
    assert ch["center_ft"] == 20.2
    assert ch["position_tag"] == "CONFIRMED (human, photo)"
    assert "left of D1, siding strip between" in ch["position"]
    assert "CONFIRMED (human, photo)" in ch["position"]
    assert "17\" left of D1 trim edge" in ch["position"]
    assert "ESTIMATED (photo-scaled, untaped)" in ch["position"]
    # AI corner-read band stays on record as the FLAGGED COMPARISON
    band = ch["ai_band"]
    assert band["center_ft"] == 21.9 and band["frac_lo"] == 0.35 and band["frac_hi"] == 0.46
    assert "FLAGGED COMPARISON" in band["note"]
    assert "INDICATIVE" not in str(ch)
    assert "indicative_center_ft" not in ch and "placement_basis" not in ch
    # geometry holds: chase right edge sits a siding strip LEFT of D1
    d1 = next(o for o in s["openings"] if o["tag"] == "D1")
    d1_left = d1["center_ft"] - d1["width_in"] / 24.0
    assert ch["center_ft"] + 64 / 24.0 < d1_left
    # collision guard: clean post-ratification — nothing suppressed
    assert s["collisions"] == []
    assert not ch.get("suppressed")


def test_chase_profile_on_sides_and_cap_on_front(session):
    """Ruled 2026-07-19 (supersedes the earlier chase=None-on-sides pin):
    sides render the chase in PROFILE — 31\" TAPED depth to 19'-6⅝\",
    position ANCHORED (abuts back wall) so no indicative label on position.
    FRONT: taped cap 19'-6⅝\" clears the WORST-CASE AI ridge estimate →
    legitimately visible → rendered, with the ridge band labeled AI-READ ⚠
    and only the along-wall position INDICATIVE."""
    for which in ("left", "right"):
        s = _sheet(session, which)
        assert s["chase"] is None, which  # the accent itself stays back-wall
        p = s["chase_profile"]
        assert p is not None, which
        assert p["depth_in"] == 31 and p["height_in"] == 234.625
        assert p["height_label"] == "19'-6⅝\"" and p["dims_tag"] == "TAPED"
        assert "anchored" in p["anchor"] and p["corner"] == "back"
        assert "INDICATIVE" not in str(p)  # anchored — nothing indicative here
    f = _sheet(session, "front")
    assert f["chase"] is None
    cap = f["chase_cap"]
    assert cap is not None
    assert cap["cap_ft"] == 19.552 and cap["cap_label"] == "19'-6⅝\""
    assert cap["cap_tag"] == "TAPED" and cap["width_in"] == 64
    assert cap["visible"] is True
    assert cap["ridge_max_ft"] < cap["cap_ft"]
    assert 17.0 < cap["ridge_min_ft"] < cap["ridge_max_ft"] < 19.552
    assert "AI-READ ⚠" in cap["ridge_basis"]
    # cap position — PIN AMENDED BY RULING 2026-07-19 (collision ruling;
    # offset restated on the TAPED 648" reference per close-out
    # correction): mirror of the RATIFIED door-relative back center
    # (54 − 20.217 → 33.8); relationship CONFIRMED (human, photo), offset
    # ESTIMATED (photo-scaled, untaped) — both bases named on the sheet
    assert cap["position_tag"] == "CONFIRMED (human, photo)"
    assert "mirrored" in cap["position"] and "door-relative" in cap["position"]
    assert "CONFIRMED (human, photo)" in cap["position"]
    assert "ESTIMATED (photo-scaled, untaped)" in cap["position"]
    assert cap["center_ft"] == 33.8
    assert cap["center_ft"] == round(54 - _sheet(session, "back")["chase"]["center_ft"], 1)
    # back sheet carries no profile/cap; sides carry no cap
    assert _sheet(session, "back")["chase_profile"] is None
    assert _sheet(session, "left")["chase_cap"] is None


def test_chase_ratification_provenance(session):
    """Ratification entered via the appendage machinery (journey-logged):
    appendage:back height_ft 19.552 / depth_ft 2.583 user_measured. PIN
    AMENDED BY RULING 2026-07-19 (collision ruling): door_offset_ft joins
    the machinery — 1.417' (≈17") photo_scaled, the chase right-edge
    offset left of D1's trim RESTATED on the TAPED 648" reference
    (close-out correction, 2026-07-19; was 1.25' in the AI's 600" frame);
    a later tape upgrades it by the normal amendment path (user_measured). Width STILL rides the sealed-key amendment only
    — the dims machinery pin rejects width_ft (400) and pins are amended
    by ruling, not silently."""
    r = session.get(f"{API}/estimates/{LETRICK_EST}/lp-appendage-dims", timeout=20)
    assert r.status_code == 200
    back = (r.json()["dims"] or {}).get("appendage:back") or {}
    assert back.get("height_ft", {}).get("value") == 19.552
    assert back.get("height_ft", {}).get("status") == "user_measured"
    assert back.get("depth_ft", {}).get("value") == 2.583
    assert back.get("depth_ft", {}).get("status") == "user_measured"
    assert back.get("door_offset_ft", {}).get("value") == 1.417
    assert back.get("door_offset_ft", {}).get("status") == "photo_scaled"
    # PIN AMENDED BY RULING 2026-07-22 (confirmation-weighted geometry):
    # width_ft JOINS the machinery — the tape-upgrade path for the ASSUMED
    # standard chase width 48". BEFORE: 400 (not a machinery field).
    rr = session.post(f"{API}/estimates/{LETRICK_EST}/lp-appendage-dims",
                      json={"key": "appendage:back", "field": "width_ft", "value": 5.333}, timeout=20)
    assert rr.status_code == 200, rr.text
    rv = session.post(f"{API}/estimates/{LETRICK_EST}/lp-appendage-dims",
                      json={"key": "appendage:back", "field": "width_ft", "action": "revert"}, timeout=20)
    assert rv.status_code == 200, rv.text
    # unknown fields still refuse — the contract stays closed
    bad = session.post(f"{API}/estimates/{LETRICK_EST}/lp-appendage-dims",
                       json={"key": "appendage:back", "field": "girth_ft", "value": 1.0}, timeout=20)
    assert bad.status_code == 400


def test_view_convention_and_mirror_consistency(session):
    """Ruled pin (defect-1): LEFT and RIGHT are mirror views — segments in
    drawing order must be exact reverses on (courses, adjacent); openings
    need no flip (along_wall_ft datum is already exterior-view, sealed in
    the extraction prompt). Every sheet states the convention."""
    left = _sheet(session, "left")
    right = _sheet(session, "right")
    lsegs = [(s["courses"], s["adjacent"]) for s in left["wall"]["segments"]]
    rsegs = [(s["courses"], s["adjacent"]) for s in right["wall"]["segments"]]
    assert lsegs == list(reversed(rsegs)), "LEFT/RIGHT step positions must mirror"
    assert left["view"]["mirrored_segments"] is True
    assert right["view"]["mirrored_segments"] is False
    for which in ("front", "left", "back", "right"):
        v = _sheet(session, which)["view"]
        assert "exterior" in v["convention"]
        assert "left corner as viewed from outside" in v["datum"]


def test_chase_not_rendered_as_accent_on_sides(session):
    """AMENDED BY RULING 2026-07-19: the human ground truth ratified the
    chase's projection, so sides now render a TAPED PROFILE (see
    test_chase_profile_on_sides_and_cap_on_front). This pin narrows to:
    the chase ACCENT (annotation box + on-wall glyph) remains back-only."""
    for which in ("left", "right", "front"):
        assert _sheet(session, which)["chase"] is None, which


def test_back_deviation_both_axes(session):
    d = _sheet(session, "back")["deviation"]
    assert d is not None and d["governs"] == "tape"
    assert d["ai_width_ft"] == 50 and d["ai_height_ft"] == 8.6
    assert d["width_disputed"] is True
    assert d["delta_width_label"].startswith("-4'")
    assert d["run_short"] == LETRICK_RUN[:8]


def test_back_openings_and_counts(session):
    s = _sheet(session, "back")
    # pin AMENDED by ruling 2026-07-20 (five-key contract)
    assert s["opening_counts"] == {"windows": 5, "doors": 1, "patio_doors": 0,
                                   "vents": 0, "garage_doors": 0}
    tags = [o["tag"] for o in s["openings"]]
    assert tags == ["W1", "W2", "D1", "W3", "W4", "W5"]  # along-wall order
    d1 = next(o for o in s["openings"] if o["tag"] == "D1")
    assert d1["sill_in"] == 0.0  # door anchors sills on this wall
    for o in s["openings"]:
        if o["tag"].startswith("W"):
            assert o["sill_in"] is not None and o["sill_tag"] == "ESTIMATED"
            assert o["sill_in"] + o["height_in"] < 9.92 * 12


def _assert_stepped_segments(w, which):
    """Stepped side pins. VIEW CONVENTION (ruled defect-1 fix): sheets are
    viewed from EXTERIOR; the run's along_wall_ft datum is the left corner
    as viewed from outside (extraction prompt iter 79j.40). Segments emit
    in DRAWING order: RIGHT sheet front-corner-left → [25, 28]; LEFT sheet
    front-corner-right → [28, 25]. Mirror-consistent by construction."""
    segs = w["segments"]
    assert segs and len(segs) == 2, "stepped side must carry BOTH tape segments"
    expect = ([25, 28], ["front", "back"]) if which == "right" else ([28, 25], ["back", "front"])
    assert [s["courses"] for s in segs] == expect[0], which
    assert [s["adjacent"] for s in segs] == expect[1], which
    by_courses = {s["courses"]: s for s in segs}
    assert by_courses[25]["height_ft"] == 8.854 and by_courses[25]["height_label"] == "8'-10¼\""
    assert by_courses[28]["height_ft"] == 9.92 and by_courses[28]["height_label"] == "9'-11\""
    for s in segs:
        assert s["height_tag"] == "TAPED-DERIVED"
        assert "4.25" in s["height_formula"] and str(s["courses"]) in s["height_formula"]
    assert w["step_note"] and "NOT TAPED" in w["step_note"]
    # honesty: stepped area needs the untaped step location — not derivable
    assert w["area_sqft"] is None and "untaped" in w["area_note"]


def test_left_stepped_segments_and_untaped_width(session):
    s = _sheet(session, "left")
    w = s["wall"]
    _assert_stepped_segments(w, "left")
    assert w["height_ft"] == 9.92  # tallest segment drives the frame
    # width untaped on sides: AI fallback, LABELED
    assert w["width_ft"] == 30 and w["width_tag"] == "AI-READ ✓"
    assert "untaped" in w["width_source"] and LETRICK_RUN[:8] in w["width_source"]
    gb = s["geometry_basis"]["walls"]
    assert "EST-191890" in gb and "heights" in gb and LETRICK_RUN[:8] in gb
    assert w["gable_triangle_ft"] == 8.8 and w["gable_tag"] in ALLOWED_TAGS


def test_right_stepped_segments_no_openings(session):
    s = _sheet(session, "right")
    _assert_stepped_segments(s["wall"], "right")
    assert s["wall"]["width_ft"] == 30
    assert s["opening_counts"] == {"windows": 0, "doors": 0, "patio_doors": 0,
                                   "vents": 0, "garage_doors": 0}
    assert s["openings"] == []
    assert "No openings" in s["schedule_note"]
    assert s["wall"]["gable_triangle_ft"] == 9.3


def test_sides_height_deviation(session):
    # AI single-height read misses EVERY tape segment on both sides
    for which, ai_h in (("left", 9.0), ("right", 8.3)):
        d = _sheet(session, which)["deviation"]
        assert d is not None, which
        assert d["ai_height_ft"] == ai_h and d["governs"] == "tape"
        assert d["width_disputed"] is False  # sides: width untaped, not disputed
        assert d["delta_width_label"] is None
        assert "8'-10¼\"" in d["tape_heights_label"] and "9'-11\"" in d["tape_heights_label"]


def test_left_vent_five_key_contract(session):
    # pin AMENDED by ruling 2026-07-20 (five-key contract)
    s = _sheet(session, "left")
    assert s["opening_counts"] == {"windows": 1, "doors": 0, "patio_doors": 0,
                                   "vents": 1, "garage_doors": 0}
    tags = [o["tag"] for o in s["openings"]]
    assert tags == ["V1", "W1"]  # vent at 15.0' precedes window at 21.0'
    v1 = next(o for o in s["openings"] if o["tag"] == "V1")
    assert v1["type"] == "Vent" and v1["width_in"] == 12 and v1["height_in"] == 8
    assert v1["position_tag"] == "AI-READ ✓"
    # pin AMENDED by the SILL-BINDING EXTENSION (authorized 2026-07-22):
    # BEFORE — no door → all sills None ("—"). AFTER — the wall WINDOW
    # head-anchors at the ratified CONTRACTOR-SPEC 6'-8" header:
    # W1 (54") sill 26" ESTIMATED. Vents stay out of the extension ("—").
    assert v1["sill_in"] is None and v1["sill_label"] == "—"
    w1 = next(o for o in s["openings"] if o["tag"] == "W1")
    assert w1["sill_in"] == 26.0 and w1["sill_tag"] == "ESTIMATED"
    assert "head-anchored" in s["schedule_note"] and "No door" in s["schedule_note"]


def test_basis_line_completeness_all_sheets(session):
    """Ruled pin: every rendered dimension on every sheet names its basis —
    no untagged values anywhere."""
    for which in ("front", "left", "back", "right"):
        s = _sheet(session, which)
        w = s["wall"]
        assert w["width_tag"] in ALLOWED_TAGS, which
        assert w["width_source"], which
        assert w["height_tag"] in ALLOWED_TAGS, which
        assert w["height_formula"], which
        for seg in (w["segments"] or []):
            assert seg["height_tag"] in ALLOWED_TAGS, which
            assert seg["height_formula"], which
        if w["gable_triangle_ft"]:
            assert w["gable_tag"] in ALLOWED_TAGS, which
        for o in s["openings"]:
            assert o["position_tag"] in ALLOWED_TAGS, (which, o["tag"])
            assert o["sill_tag"] in ALLOWED_TAGS, (which, o["tag"])
        if s["chase"]:
            assert s["chase"]["tag"] in ALLOWED_TAGS, which
            assert s["chase"]["dims_tag"] in ALLOWED_TAGS, which
        if s.get("chase_profile"):
            assert s["chase_profile"]["dims_tag"] in ALLOWED_TAGS, which
        if s.get("chase_cap"):
            assert s["chase_cap"]["cap_tag"] in ALLOWED_TAGS, which
        if s["deviation"]:
            assert s["deviation"]["governs"] == "tape", which


def test_verb_remove_reset_left_vent(session):
    """Verb machinery per-sheet pin (LEFT): user_removed vent row (schedule
    index 4) drops from the sheet; reset restores it."""
    key = f"open:{LETRICK_RUN[:8]}:4"
    url = f"{API}/estimates/{LETRICK_EST}/openings-review"
    r = session.post(url, json={"key": key, "action": "remove"}, timeout=20)
    assert r.status_code == 200, r.text
    try:
        s = _sheet(session, "left")
        assert [o["tag"] for o in s["openings"]] == ["W1"]
        assert s["opening_counts"] == {"windows": 1, "doors": 0, "patio_doors": 0,
                                       "vents": 0, "garage_doors": 0}
    finally:
        rr = session.post(url, json={"key": key, "action": "reset"}, timeout=20)
        assert rr.status_code == 200, rr.text
    s = _sheet(session, "left")
    assert [o["tag"] for o in s["openings"]] == ["V1", "W1"]
    assert s["opening_counts"] == {"windows": 1, "doors": 0, "patio_doors": 0,
                                   "vents": 1, "garage_doors": 0}


def test_verb_remove_reset_back_window_group(session):
    """Verb machinery per-sheet pin (BACK): removing the 36×54 group
    (schedule index 5, 2 members) drops BOTH raw members; cross-wall
    isolation: RIGHT stays empty and 200 throughout; reset restores."""
    key = f"open:{LETRICK_RUN[:8]}:5"
    url = f"{API}/estimates/{LETRICK_EST}/openings-review"
    r = session.post(url, json={"key": key, "action": "remove"}, timeout=20)
    assert r.status_code == 200, r.text
    try:
        s = _sheet(session, "back")
        assert not any(o["height_in"] == 54 for o in s["openings"])
        assert s["opening_counts"] == {"windows": 3, "doors": 1, "patio_doors": 0,
                                       "vents": 0, "garage_doors": 0}
        assert [o["tag"] for o in s["openings"]] == ["D1", "W1", "W2", "W3"]
        # cross-wall isolation
        sr = _sheet(session, "right")
        assert sr["openings"] == []
        sl = _sheet(session, "left")
        assert sl["opening_counts"] == {"windows": 1, "doors": 0, "patio_doors": 0,
                                        "vents": 1, "garage_doors": 0}
    finally:
        rr = session.post(url, json={"key": key, "action": "reset"}, timeout=20)
        assert rr.status_code == 200, rr.text
    s = _sheet(session, "back")
    assert s["opening_counts"] == {"windows": 5, "doors": 1, "patio_doors": 0,
                                   "vents": 0, "garage_doors": 0}


def test_collision_guard_trips_on_prefix_letrick_back_data():
    """COLLISION GUARD — PIN AMENDED BY RULING 2026-07-21 (flag-always,
    suppress-never; original 2026-07-19 suppression predated C-4 scale-
    rendered chases). BEFORE: opening × appendage → CHASE drawing
    suppressed ('opening governs'). AFTER: the guard still TRIPS on the
    pre-fix Letrick BACK state (~3.2\" overlap) but BOTH elements draw
    and flag; the callout directs to Field Verify location review."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from routes.elevation_sheets import detect_collisions
    half_chase = 64 / 24.0
    elements = [
        {"name": "D1", "kind": "opening",
         "base": "position AI-READ ✓ · center 25'-9⅝\"",
         "lo_ft": 25.8 - 1.5, "hi_ft": 25.8 + 1.5},
        {"name": "CHASE", "kind": "appendage",
         "base": "position AI-READ ✓ (pre-ratification corner-read binding) · center 21'-10¾\"",
         "lo_ft": 21.9 - half_chase, "hi_ft": 21.9 + half_chase},
    ]
    cols = detect_collisions(elements)
    assert len(cols) == 1
    c = cols[0]
    assert set(c["elements"]) == {"D1", "CHASE"}
    assert c["suppressed"] is None             # AMENDED: suppress-never
    assert 3.0 < c["overlap_in"] < 3.5         # the reported ~3" overlap
    assert len(c["bases"]) == 2 and all(c["bases"])
    assert "flagged" in c["resolution"] and "unverified" in c["resolution"]
    assert "Field Verify" in c["resolution"]   # the flag is an instruction


def test_collision_guard_opening_pair_and_order_independence():
    """Guard semantics — PIN AMENDED BY RULING 2026-07-21: (a) opening ×
    opening — both flagged unverified (unchanged); (b) opening × appendage
    now behaves IDENTICALLY (BEFORE: appendage suppressed regardless of
    order; AFTER: suppressed is None, both flagged, Field Verify direction);
    (c) exact abutment does NOT trip (tolerance guards float noise)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from routes.elevation_sheets import detect_collisions
    pair = detect_collisions([
        {"name": "W1", "kind": "opening", "base": "b1", "lo_ft": 3.0, "hi_ft": 6.0},
        {"name": "W2", "kind": "opening", "base": "b2", "lo_ft": 5.0, "hi_ft": 8.0}])
    assert len(pair) == 1 and pair[0]["suppressed"] is None
    assert "unverified" in pair[0]["resolution"]
    swapped = detect_collisions([
        {"name": "CHASE", "kind": "appendage", "base": "b1", "lo_ft": 20.0, "hi_ft": 25.0},
        {"name": "D1", "kind": "opening", "base": "b2", "lo_ft": 24.3, "hi_ft": 27.3}])
    assert swapped[0]["suppressed"] is None    # AMENDED: kind never suppresses
    assert swapped[0]["resolution"] == pair[0]["resolution"]
    abut = detect_collisions([
        {"name": "W1", "kind": "opening", "base": "b1", "lo_ft": 3.0, "hi_ft": 6.0},
        {"name": "CHASE", "kind": "appendage", "base": "b2", "lo_ft": 6.0, "hi_ft": 9.0}])
    assert abut == []


def test_collision_guard_live_on_every_sheet(session):
    """The guard runs on ALL sheets (payload key always present) and is
    CLEAN post-ratification: no overlaps, nothing suppressed, no opening
    collision flags anywhere."""
    for which in ("front", "left", "back", "right"):
        s = _sheet(session, which)
        assert s["collisions"] == [], which
        assert not any(o["collision"] for o in s["openings"]), which
        if s["chase"]:
            assert not s["chase"].get("suppressed"), which


def test_read_only_behavioral_all_sheets(session):
    from pymongo import MongoClient
    import os
