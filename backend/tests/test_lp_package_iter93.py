"""Iter 79j.93 — September LP package assembly pins (Phase 1).
Whole-piece rounding everywhere; C3 corner-location OSC override with
amber/elevated flags (presence guarantee carries into the takeoff);
fallback to outside_corner_lf when no corner locations exist."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_package import OSC_ITEM, assemble_lp_package, osc_from_corner_locations  # noqa: E402

LETRICK_HEIGHTS = {"front": 8.5, "back": 10.3, "left": 8.3, "right": 8.5}


def _loc(walls, tier="confirmed", elevated=False):
    return {"type": "outside", "walls": walls, "tier": tier, "elevated": elevated}


def _letrick_locations():
    return [
        _loc(["front", "left"]),                     # min(8.5, 8.3) = 8.3
        _loc(["front", "right"]),                    # 8.5
        _loc(["back", "left"]),                      # 8.3
        _loc(["back", "right"]),                     # 8.5
        _loc(["back"]),                              # chase front-left 10.3
        _loc(["back"]),                              # chase front-right 10.3
        _loc(["back"], tier="unconfirmed"),          # p3 drift residual 10.3
    ]


MEAS = {"siding_sqft": 1832.7, "outside_corner_lf": 37.6, "_ai_avg_wall_height_ft": 8.9}


def test_osc_letrick_pattern():
    osc = osc_from_corner_locations(_letrick_locations(), LETRICK_HEIGHTS, 8.9)
    assert osc["osc_count"] == 7
    assert osc["total_lf"] == 64.5  # 8.3+8.5+8.3+8.5+10.3*3
    assert osc["qty"] == 5          # ceil(64.5/16)
    assert osc["amber"] == 1
    assert "field verify" in osc["note"]


def test_osc_inside_corners_never_counted():
    locs = [{"type": "inside", "walls": ["back"], "tier": "confirmed"}]
    assert osc_from_corner_locations(locs, LETRICK_HEIGHTS, 8.9) is None


def test_osc_two_wall_uses_shorter_adjacent_wall():
    osc = osc_from_corner_locations([_loc(["back", "left"])], LETRICK_HEIGHTS, 8.9)
    assert osc["total_lf"] == 8.3


def test_osc_elevated_flagged_full_wall_height():
    osc = osc_from_corner_locations(
        [_loc(["left"], tier="unconfirmed", elevated=True)], LETRICK_HEIGHTS, 8.9)
    assert osc["elevated"] == 1
    assert "full wall height" in osc["note"]
    assert osc["total_lf"] == 8.3


def test_assemble_osc_override_replaces_spec_line():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    osc_lines = [l for l in pkg["lines"] if l["name"] == OSC_ITEM]
    assert len(osc_lines) == 1
    assert osc_lines[0]["qty"] == 5
    assert "C3 corner locations" in osc_lines[0]["note"]
    assert pkg["summary"]["osc_source"] == "c3_corner_locations"
    assert any("amber" in f for f in pkg["summary"]["flags"])


def test_assemble_fallback_without_corner_locations():
    pkg = assemble_lp_package(MEAS, None, None)
    osc_lines = [l for l in pkg["lines"] if l["name"] == OSC_ITEM]
    assert len(osc_lines) == 1
    assert osc_lines[0]["qty"] == 3  # ceil(37.6/16) whole-piece (spec round → ceil'd)
    assert pkg["summary"]["osc_source"] == "outside_corner_lf"
    assert pkg["summary"]["flags"] == []


def test_assemble_whole_piece_everywhere_and_lp_only():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    assert pkg["lines"], "package must not be empty"
    for l in pkg["lines"]:
        assert l["tab"] == "lp_smart"
        assert isinstance(l["qty"], int), f"{l['name']} qty not whole-piece: {l['qty']}"
    assert pkg["summary"]["total_pieces"] >= pkg["summary"]["osc_detail"]["qty"]


def test_assemble_install_system_auto_adds_present():
    pkg = assemble_lp_package(MEAS, None, None)
    names = {l["name"] for l in pkg["lines"]}
    for expected in (".019 Coil", "Touch up kits", "OSI Quad Max Caulking"):
        assert expected in names, f"install-system auto-add missing: {expected}"
