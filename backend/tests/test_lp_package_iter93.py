"""Iter 79j.93/.94 — September LP package assembly pins.
Ruled LP trim system: OSC whole-sticks-per-location; 440 4/4"×4" per ISC
location; 440 4/4"×8" fascia+rake; composition guard (J/finish trim/coil
= composition bugs on LP-native); pendings flagged never defaulted."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_conventions import FASCIA_RAKE_ITEM, ISC_TRIM_ITEM  # noqa: E402
from lp_package import (  # noqa: E402
    OSC_ITEM, assemble_lp_package, isc_from_corner_locations,
    osc_from_corner_locations,
)

LETRICK_HEIGHTS = {"front": 8.5, "back": 10.3, "left": 8.3, "right": 8.5}


def _loc(walls, tier="confirmed", elevated=False, ctype="outside"):
    return {"type": ctype, "walls": walls, "tier": tier, "elevated": elevated}


def _letrick_locations():
    return [
        _loc(["front", "left"]),
        _loc(["front", "right"]),
        _loc(["back", "left"]),
        _loc(["back", "right"]),
        _loc(["back"]),                              # chase front-left
        _loc(["back"]),                              # chase front-right
        _loc(["back"], tier="unconfirmed"),          # p3 drift residual
        _loc(["back"], ctype="inside"),              # chase left junction
        _loc(["back"], ctype="inside", tier="unconfirmed"),  # chase right junction
    ]


MEAS = {"siding_sqft": 1832.7, "outside_corner_lf": 37.6, "inside_corner_lf": 40.0,
        "_ai_avg_wall_height_ft": 8.9, "eaves_lf": 108.0, "rakes_lf": 73.4,
        "opening_count": 12, "window_count": 10, "entry_door_count": 2,
        "opening_perimeter_lf": 219.3}


def test_osc_whole_sticks_per_location():
    # RULED: whole sticks PER LOCATION, never pooled LF — 7 locations,
    # all heights <= 16' → 7 sticks (pooled 64.5/16 would give 5)
    osc = osc_from_corner_locations(
        [l for l in _letrick_locations() if l["type"] == "outside"], LETRICK_HEIGHTS, 8.9)
    assert osc["osc_count"] == 7
    assert osc["qty"] == 7
    assert osc["amber"] == 1
    assert "stick length pending" in osc["note"]
    assert "field verify" in osc["note"]


def test_osc_over_stick_flags_splice_pending():
    osc = osc_from_corner_locations(
        [_loc(["back"])], {"back": 18.5}, 8.9)
    assert osc["qty"] == 2  # ceil(18.5/16) held pending splice ruling
    assert "splice rule pending" in osc["note"]


def test_isc_sticks_per_location():
    isc = isc_from_corner_locations(_letrick_locations(), LETRICK_HEIGHTS, 8.9)
    assert isc["isc_count"] == 2
    assert isc["qty"] == 2
    assert isc["amber"] == 1


def test_osc_inside_corners_never_counted():
    assert osc_from_corner_locations(
        [_loc(["back"], ctype="inside")], LETRICK_HEIGHTS, 8.9) is None


def test_osc_elevated_flagged_full_wall_height():
    osc = osc_from_corner_locations(
        [_loc(["left"], tier="unconfirmed", elevated=True)], LETRICK_HEIGHTS, 8.9)
    assert osc["elevated"] == 1
    assert "full wall height" in osc["note"]


def test_assemble_ruled_trim_system():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    by = {l["name"]: l for l in pkg["lines"]}
    assert by[OSC_ITEM]["qty"] == 7
    # 440 4/4"×4" is ISC-only now (horizontal runs superseded by 4/4"×8")
    assert by[ISC_TRIM_ITEM]["qty"] == 2
    assert "ISC locations" in by[ISC_TRIM_ITEM]["note"]
    # 440 4/4"×8" fascia + rake: (108 + 73.4) × 1.10 ÷ 16 = 12.47 → 13
    assert by[FASCIA_RAKE_ITEM]["qty"] == 13
    assert "splice-and-round-up assumed" in by[FASCIA_RAKE_ITEM]["note"]
    assert pkg["summary"]["osc_source"] == "c3_corner_locations"


def test_assemble_composition_guard_strips_coil():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    names = {l["name"] for l in pkg["lines"]}
    assert not any("coil" in n.lower() for n in names)  # coil = composition bug
    assert any("Coil" in n for n in pkg["summary"]["composition_guard_removed"])
    # J blocks are mounting blocks, NOT J-channel — must survive the guard
    assert "J blocks" in names


def test_assemble_install_auto_adds_survive():
    pkg = assemble_lp_package(MEAS, None, None)
    names = {l["name"] for l in pkg["lines"]}
    for expected in ("Touch up kits", "OSI Quad Max Caulking"):
        assert expected in names


def test_assemble_fallback_without_corner_locations():
    pkg = assemble_lp_package(MEAS, None, None)
    by = {l["name"]: l for l in pkg["lines"]}
    assert by[OSC_ITEM]["qty"] == 3  # ceil(37.6/16) whole-piece
    assert pkg["summary"]["osc_source"] == "outside_corner_lf"


def test_assemble_whole_piece_everywhere_and_lp_only():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    for l in pkg["lines"]:
        assert l["tab"] == "lp_smart"
        assert isinstance(l["qty"], int)


def test_assemble_pendings_surfaced():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    pend = " ".join(pkg["summary"]["pending_confirmations"])
    assert "stick length" in pend
    assert "3-side vs 4-side" in pend
    assert "splice convention" in pend or "Fascia/rake splice" in pend
