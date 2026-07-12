"""Iter 79j.94 — pins for the LP material-usage CONVENTIONS layer
(Howard's spec block) + the Letrick truck-list acceptance harness.
Doctrine pins: waste before whole-piece round-up; trap check (8\" lap
face is 7-7/8\" NOT 7-1/4\"); shake reveal never silently defaulted;
pendings never filled from other sources; discrepancies flagged never
silently picked."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_conventions import (  # noqa: E402
    LAP8_WRONG_FACE_IN, LAP_FACE_IN, LAP_PCS_PER_SQUARE_12FT,
    LAP_PCS_PER_SQUARE_16FT, PENDING_CONFIRMATIONS, SOFFIT_BUNDLE_PCS,
    batten_takeoff_flags, coverage_per_board_sqft, line_math,
    pieces_per_square, reveal_from_face, shake_takeoff,
    soffit_panel_for_overhang, soffit_takeoff_eave_length,
    spec_discrepancies,
)
from lp_smartside_formulas import NICKEL_GAP_COVERAGE_SQFT_PER_PC  # noqa: E402
from lp_truck_reconcile import LETRICK_TRUCK_LIST, reconcile_letrick_truck  # noqa: E402


# ── core formula + tables ──

def test_lap_tables_16ft_and_12ft():
    for name, face in LAP_FACE_IN.items():
        reveal = reveal_from_face(face)
        assert pieces_per_square(reveal, 16) == LAP_PCS_PER_SQUARE_16FT[name]
        assert pieces_per_square(reveal, 12) == LAP_PCS_PER_SQUARE_12FT[name]


def test_estimating_trap_8_lap_face():
    # face 7-7/8" → reveal 6-7/8" → 9.17 sqft/board → 11 pcs/square
    assert reveal_from_face(LAP_FACE_IN["8\" Lap"]) == 6.875
    assert coverage_per_board_sqft(6.875, 16) == 9.17
    assert pieces_per_square(6.875, 16) == 11
    # the WRONG 7-1/4" face changes the answer — the check has teeth
    assert pieces_per_square(reveal_from_face(LAP8_WRONG_FACE_IN), 16) != 11


def test_no_internal_spec_discrepancies():
    assert spec_discrepancies() == []


def test_shake_pcs_per_square_bounds():
    assert pieces_per_square(6.875, 4) == 44   # minimum reveal
    assert pieces_per_square(9.875, 4) == 31   # maximum reveal


def test_nickel_gap_locked():
    assert NICKEL_GAP_COVERAGE_SQFT_PER_PC == 9.33  # fixed 7" reveal, never job-variable


# ── doctrine: waste before round-up, transparency triple ──

def test_waste_before_whole_piece_roundup():
    m = line_math(100.0, 9.17)
    assert m["base_qty"] == 10.91
    assert m["ordered_pcs"] == 12  # ceil(10.905 × 1.10) — waste FIRST, then up
    assert m["waste_pct"] == 10


# ── shake reveal: never silently defaulted ──

def test_shake_unspecified_reveal_flags_and_worst_cases():
    m = shake_takeoff(500.0)
    assert m["reveal_in"] == 6.875  # minimum reveal = worst case, more pieces
    assert any("reveal: unconfirmed" in f for f in m["flags"])
    assert any("PENDING" in f for f in m["flags"])  # shake waste pending
    specified = shake_takeoff(500.0, reveal_in=9.875, waste=0.10)
    assert specified["flags"] == []
    assert m["ordered_pcs"] > specified["ordered_pcs"]


def test_batten_spacing_flag():
    assert batten_takeoff_flags(None) != []
    assert batten_takeoff_flags("16\" o.c.") == []


# ── soffit: width matching, rip waste, bundles ──

def test_soffit_next_width_up_with_rip_note():
    assert soffit_panel_for_overhang(12)["panel"] == "12\" Soffit"
    assert soffit_panel_for_overhang(12)["rip_waste_note"] is None
    sel17 = soffit_panel_for_overhang(17)
    assert sel17["panel"] == "24\" Soffit"
    assert "rip waste" in sel17["rip_waste_note"]


def test_soffit_eave_length_method():
    m = soffit_takeoff_eave_length(108.0, 12.0)
    assert m["panel"] == "12\" Soffit"
    assert m["base_qty"] == 6.75          # 108 ÷ 16' boards
    assert m["ordered_pcs"] == 8          # × 1.10 → 7.43 → up
    assert str(SOFFIT_BUNDLE_PCS) in m["bundle_note"]


# ── pendings: never filled from other sources ──

def test_pending_confirmations_exactly_two():
    assert set(PENDING_CONFIRMATIONS) == {"shake_waste_factor", "lp_trim_accessory_conventions"}


# ── Letrick truck-list harness ──

LETRICK_GEOMETRY = {
    "siding_sqft": 1832.7, "eaves_lf": 108.0, "rakes_lf": 73.4,
    "starter_lf": 168.0, "opening_perimeter_lf": 219.3, "overhang_in": 12.0,
}


def _c3_locations(n_isc=3):
    osc = [{"type": "outside", "walls": ["front", "left"], "tier": "confirmed"}] * 4 + \
          [{"type": "outside", "walls": ["back"], "tier": "confirmed"}] * 2 + \
          [{"type": "outside", "walls": ["back"], "tier": "unconfirmed"}]
    isc = [{"type": "inside", "walls": ["back"], "tier": "confirmed"}] + \
          [{"type": "inside", "walls": ["back"], "tier": "unconfirmed"}] * (n_isc - 1)
    return osc + isc


def test_truck_fixture_is_pinned():
    assert {l["item"]: l["qty"] for l in LETRICK_TRUCK_LIST} == {
        "D4.5 siding": 20, "Starter": 20, "OSC": 10, "ISC": 2, "J-channel": 30,
        "Coil": 2, "Finish trim": 23, "Soffit": 24, "Soffit J": 18,
    }


def test_truck_reconcile_statuses():
    out = reconcile_letrick_truck(LETRICK_GEOMETRY, _c3_locations())
    by = {l["item"]: l for l in out["lines"]}
    assert by["D4.5 siding"]["derived_qty"] == 21  # 18.33 sq × 1.10 → whole-square up
    assert by["OSC"]["derived_qty"] == 7 and by["OSC"]["status"] == "deviation"
    assert "10-pieces/6-locations" in by["OSC"]["cause"]
    assert by["ISC"]["derived_qty"] == 3 and "amber" in by["ISC"]["cause"]
    # pending lines never derived from unconfirmed rules
    for item in ("Starter", "J-channel", "Coil", "Finish trim", "Soffit J"):
        assert by[item]["status"] == "pending_confirmation"
        assert by[item]["derived_qty"] is None
    assert out["summary"]["pending_confirmation"] == 5


def test_truck_reconcile_isc_match_when_two():
    out = reconcile_letrick_truck(LETRICK_GEOMETRY, _c3_locations(n_isc=2))
    by = {l["item"]: l for l in out["lines"]}
    assert by["ISC"]["status"] == "match" and by["ISC"]["derived_qty"] == 2
