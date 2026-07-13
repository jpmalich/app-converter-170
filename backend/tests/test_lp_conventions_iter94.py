"""Iter 79j.94 — pins for the LP material-usage CONVENTIONS layer +
Letrick truck-list harness, updated to Howard's consolidated rulings
(shake waste ruled 10% provisional; LP composition: no J/finish trim/coil;
whole-square doctrine + near_boundary; OSC reconciled-by-key; ISC exact;
soffit basis explicit + rake-corrected held pending)."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_conventions import (  # noqa: E402
    LAP8_WRONG_FACE_IN, LAP_FACE_IN, LAP_PCS_PER_SQUARE_12FT,
    LAP_PCS_PER_SQUARE_16FT, PENDING_CONFIRMATIONS, SOFFIT_BUNDLE_PCS,
    batten_takeoff_flags, coverage_per_board_sqft, fascia_rake_takeoff,
    line_math, lp_composition_bugs, near_boundary, pieces_per_square,
    rake_slope_length_ft, reveal_from_face, shake_takeoff,
    soffit_panel_for_overhang, soffit_run_area_sqft,
    soffit_takeoff_eave_length, spec_discrepancies,
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
    assert reveal_from_face(LAP_FACE_IN["8\" Lap"]) == 6.875
    assert coverage_per_board_sqft(6.875, 16) == 9.17
    assert pieces_per_square(6.875, 16) == 11
    assert pieces_per_square(reveal_from_face(LAP8_WRONG_FACE_IN), 16) != 11


def test_no_internal_spec_discrepancies():
    assert spec_discrepancies() == []


def test_shake_pcs_per_square_bounds():
    assert pieces_per_square(6.875, 4) == 44
    assert pieces_per_square(9.875, 4) == 31


def test_nickel_gap_locked():
    assert NICKEL_GAP_COVERAGE_SQFT_PER_PC == 9.33


# ── doctrine: waste before round-up, near-boundary annotation ──

def test_waste_before_whole_piece_roundup():
    m = line_math(100.0, 9.17)
    assert m["base_qty"] == 10.91
    assert m["ordered_pcs"] == 12
    assert m["waste_pct"] == 10


def test_near_boundary_annotation():
    assert near_boundary(20.16) is True    # within 0.5 of lower whole square
    assert near_boundary(20.4) is True
    assert near_boundary(20.7) is False
    assert near_boundary(21.0) is False    # exact whole square — no boundary call


# ── shake: reveal never silently defaulted; waste RULED 10% (no flag) ──

def test_shake_unspecified_reveal_flags_and_worst_cases():
    m = shake_takeoff(500.0)
    assert m["reveal_in"] == 6.875
    assert any("reveal: unconfirmed" in f for f in m["flags"])
    assert not any("PENDING" in f for f in m["flags"])  # waste ruled, no longer pending
    specified = shake_takeoff(500.0, reveal_in=9.875)
    assert specified["flags"] == []
    assert m["ordered_pcs"] > specified["ordered_pcs"]


def test_batten_spacing_flag():
    assert batten_takeoff_flags(None) != []
    assert batten_takeoff_flags("16\" o.c.") == []


# ── soffit: width matching, rakes included, rip waste, bundles ──

def test_soffit_next_width_up_with_rip_note():
    assert soffit_panel_for_overhang(12)["panel"] == "12\" Soffit"
    sel17 = soffit_panel_for_overhang(17)
    assert sel17["panel"] == "24\" Soffit"
    assert "rip waste" in sel17["rip_waste_note"]


def test_soffit_eave_length_method():
    m = soffit_takeoff_eave_length(108.0, 12.0)
    assert m["base_qty"] == 6.75
    assert m["ordered_pcs"] == 8
    assert str(SOFFIT_BUNDLE_PCS) in m["bundle_note"]


def test_soffit_run_area_panels_eaves_and_rakes():
    # conventions fix: eaves AND rakes, wherever overhangs carry soffit
    assert soffit_run_area_sqft(108, 73.4, 12) == 181.4
    assert soffit_run_area_sqft(108, 73.4, 12, include_rakes=False) == 108.0


def test_rake_slope_never_plan_view():
    # 7/12 over 15' half-span ≈ 17.4' slope
    assert abs(rake_slope_length_ft(7, 15) - 17.37) < 0.05
    assert rake_slope_length_ft(7, 15) > 15  # slope always exceeds plan view


# ── LP fascia/rake + composition guard ──

def test_fascia_rake_takeoff():
    # C4 (ruled 2026-07-13): stick-count lines carry NO percentage waste —
    # whole-stick rounding is the entire allowance. 181.4 ÷ 16 → 12.
    fr = fascia_rake_takeoff(108.0, 73.4)
    assert fr["total_lf"] == 181.4
    assert fr["ordered_pcs"] == 12
    assert fr["flags"] == []  # splice-and-round-up + always-present RULED


def test_lp_composition_bugs_detector():
    lines = [{"name": ".019 Coil"}, {"name": "Finish trim 12'"},
             {"name": "1/2\" J-Channel"}, {"name": "J blocks"},
             {"name": "38 Series Lap 3/8\" x 8\" x 16'"}]
    bugs = lp_composition_bugs(lines)
    assert ".019 Coil" in bugs and "Finish trim 12'" in bugs and "1/2\" J-Channel" in bugs
    assert "J blocks" not in bugs  # mounting blocks, not channel


def test_pending_confirmations_ruled_set():
    # six-ruling block reconciled — genuinely open items only
    assert set(PENDING_CONFIRMATIONS) == {
        "starter_rule_divisor", "expertfinish_availability_matrix",
        "bluelinx_sku_upload", "letrick_hand_takeoff",
    }
    # starter item must state BOTH derivations precisely
    s = PENDING_CONFIRMATIONS["starter_rule_divisor"]
    assert "14" in s and "17" in s and "12.5" in s and "10" in s


def test_per_system_derivation_table():
    from lp_conventions import SYSTEM_DERIVATION, soffit_run_area_sqft
    assert "eaves only" in SYSTEM_DERIVATION["lp"]["soffit_runs"]
    assert SYSTEM_DERIVATION["vinyl"]["soffit_runs"] == "eaves+rakes"
    assert soffit_run_area_sqft(108, 73.4, 12, include_rakes=False) == 108.0
    assert soffit_run_area_sqft(108, 73.4, 12, include_rakes=True) == 181.4


# ── Letrick truck-list harness (per consolidated rulings) ──

LETRICK_GEOMETRY = {
    "siding_sqft": 1832.7, "eaves_lf": 108.0, "rakes_lf": 73.4,
    "starter_lf": 168.0, "opening_perimeter_lf": 219.3, "overhang_in": 12.0,
}


def _c3_locations():
    return ([{"type": "outside", "walls": ["front"], "tier": "confirmed"}] * 6
            + [{"type": "outside", "walls": ["back"], "tier": "unconfirmed"}]
            + [{"type": "inside", "walls": ["back"], "tier": "confirmed"}] * 2
            + [{"type": "inside", "walls": ["back"], "tier": "unconfirmed"}])


def test_truck_fixture_is_pinned():
    assert {l["item"]: l["qty"] for l in LETRICK_TRUCK_LIST} == {
        "D4.5 siding": 20, "Starter": 20, "OSC": 10, "ISC": 2, "J-channel": 30,
        "Coil": 2, "Finish trim": 23, "Soffit": 24, "Soffit J": 18,
    }


def test_truck_reconcile_per_rulings():
    widths = [6.0, 6.0, 6.0, 2.33, 3.67, 3.0, 3.0, 2.5, 3.0, 2.0]  # Σ 37.5
    out = reconcile_letrick_truck(LETRICK_GEOMETRY, _c3_locations(), widths)
    by = {l["item"]: l for l in out["lines"]}
    # whole-square doctrine + near_boundary annotation
    assert by["D4.5 siding"]["derived_qty"] == 21
    assert "crew_judgment_short_order" in by["D4.5 siding"]["cause"]
    assert "trim-or-keep" in by["D4.5 siding"]["near_boundary"]
    # OSC reconciled-by-key + splice verification; ISC exact, distinct causes
    assert by["OSC"]["status"] == "reconciled_by_key" and by["OSC"]["derived_qty"] == 10
    assert "SPLICE-RULE VERIFICATION" in by["OSC"]["cause"]
    assert by["ISC"]["status"] == "match" and by["ISC"]["derived_qty"] == 2
    assert "no pieces/locations conversion" in by["ISC"]["cause"]
    # starter comment/code discrepancy FLAGGED, never silently picked
    assert "discrepancy" in by["Starter"]["cause"]
    # coil + soffit-J derive to exact matches under rules on file
    assert by["Coil"]["status"] == "match" and by["Coil"]["derived_qty"] == 2
    assert by["Soffit J"]["status"] == "match" and by["Soffit J"]["derived_qty"] == 18
    # soffit: SCORED per amendment (vinyl system rule = eaves+rakes)
    assert by["Soffit"]["status"] == "deviation"
    assert "RECONCILED" in by["Soffit"]["cause"]
    assert "Charter Oak" in by["Soffit"]["basis"]
    assert by["Soffit"]["derived_qty"] == 20
    # finish trim: ruled formula validated vs 23 — NOT reproduced, reported
    assert by["Finish trim"]["status"] == "deviation"
    assert by["Finish trim"]["derived_qty"] == 12  # (37.5 + 108) ÷ 12.5
    assert "NOT reproduced" in by["Finish trim"]["cause"]
    assert out["summary"]["match"] == 3
    assert "pending_confirmation" not in out["summary"]
