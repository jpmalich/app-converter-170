"""ITEM-3 CHASE-SIDING RATIFICATION + SEALED CORNER CONVENTION (Howard,
ruled 2026-07-19 close-out). Pins:

1. CHASE FACES enter Letrick materials — TAPED faces SUPERSEDE the AI's
   130 ft² attribution (SWAP, never add-on-top). Named formula-layer
   factor CHASE_FACE_WASTE = standing 10% + profile PDF coverage.
2. TWO LEDGERS, kept distinct on the record (never absorbed): the APP
   line derives via the pinned PDF formula (siding 1889.1 → 1911.5 →
   lap 227 → 230); the SEALED KEY derives via Howard's convention
   (+10% waste, 11 pcs/sq: raw 2092.8 → 2099.7 → lap 254 → 255).
   "227 → 255 (+28)" mixes the ledgers — same frame-mixing class as the
   600"/648" photo-scale correction, resolved on the record here.
3. OSC unchanged: 8 @ $271.69 (mill 190.18 ÷ 0.70, Contractor 30%).
4. POOLED corner convention SEALED as standing contractor-spec with the
   PLACEMENT RULE recorded alongside: full 16' sticks at corner BOTTOMS;
   spliced remnants upper portion only, cut from shared sticks.
5. Area gate open for THIS ratification only — other estimates untouched.
"""
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
LETRICK = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com",
                     "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def pkg(session):
    r = session.post(f"{API}/estimates/{LETRICK}/lp-package/preview", json={}, timeout=60)
    assert r.status_code == 200
    return r.json()


def _line(pkg, frag):
    return next(l for l in pkg["lines"] if frag in l["name"])


def test_chase_face_formula_named_and_pinned():
    """FORMULA-LAYER FACTOR (prices every future chase): faces ride the
    STANDING waste — CHASE_FACE_WASTE is DEFAULT_WASTE (10%), no special
    chase tier. Face math: outboard = width × (chase h − wall h);
    sides = 2 × depth × chase h; wall-abutting face carried by the
    wall's gross strip."""
    from lp_package import CHASE_FACE_WASTE, chase_face_sqft
    from lp_smartside_formulas import DEFAULT_WASTE
    assert CHASE_FACE_WASTE == DEFAULT_WASTE == 0.10
    faces = chase_face_sqft(64 / 12.0, 2.583, 19.552, 9.92)
    assert faces["outboard_sqft"] == 51.37
    assert faces["sides_sqft"] == 101.01
    assert faces["total_sqft"] == 152.38


def test_app_ledger_lap_swap_227_to_230(pkg):
    """APP ledger (pinned PDF formula): TAPED 152.38 ft² supersede AI
    130 ft² → siding 1911.5 → ceil(1911.5 ÷ 9.17 × 1.10) = 230 pcs.
    The +3 pcs price at the line's unit_sell — receipts on the line."""
    lap = _line(pkg, "38 Series Lap 3/8")
    assert lap["qty"] == 230
    assert lap["math"]["ordered_pcs"] == 230
    assert "CHASE FACES RATIFIED (item-3, 2026-07-19)" in lap["note"]
    assert "SUPERSEDE AI-attributed 130 ft² (swap, no double count)" in lap["note"]
    assert "CHASE_FACE_WASTE = standing 10% (named, formula-layer)" in lap["note"]
    cfr = pkg["summary"]["chase_face_ratification"]
    assert cfr["total_sqft"] == 152.38 and cfr["ai_sqft"] == 130.0
    assert cfr["siding_sqft_effective"] == 1911.5


def test_osc_unchanged_with_sealed_placement_rule(pkg):
    """OSC stays 8 @ $271.69 (mill 190.18 ÷ 0.70 = 271.6857 → 271.69,
    Contractor 30% true margin). The SEALED placement rule rides the
    line note so future chase specs carry it."""
    osc = _line(pkg, "540 Series OSC")
    assert osc["qty"] == 8
    assert osc["unit_sell"] == 271.69
    assert osc["line_sell"] == 2173.52
    assert "placement (sealed 2026-07-19): full sticks at corner BOTTOMS" in osc["note"]
    assert "spliced remnants upper portion only" in osc["note"]


def test_key_ledger_item3_amendment():
    """SEALED KEY ledger (Howard's convention: +10% waste, 11 pcs/sq):
    chase_outer 47.97 → 51.37, chase_sides 97.56 → 101.02, raw 2092.8 →
    2099.7, lap 254 → 255. Distinct from the app ledger BY DESIGN —
    reconciliation is the Phase-3 fixture exercise, not silent mixing."""
    from letrick_hand_takeoff_key import LETRICK_HAND_TAKEOFF_KEY as KEY
    assert KEY["inputs"]["chase_outer_sqft"] == 51.37
    assert KEY["inputs"]["chase_sides_sqft"] == 101.02
    assert KEY["inputs"]["raw_sqft"] == 2099.7
    lap = next(l for l in KEY["lines"] if "38 Series Lap" in l["item"])
    assert lap["qty"] == 255
    assert "item-3 ratified 2026-07-19" in lap["derivation"]
    osc = next(l for l in KEY["lines"] if "540 Series OSC" in l["item"])
    assert osc["qty"] == 8
    assert "POOLED convention SEALED 2026-07-19" in osc["derivation"]
    assert "pooled 58.37 LF" in osc["derivation"]


def test_gate_scoped_to_ratified_estimate_only():
    """Area gate opens for THIS ratification only — any other estimate
    passes through _apply_chase_ratification untouched."""
    from routes.lp_package_routes import _apply_chase_ratification
    m = {"siding_sqft": 1000.0, "_ai_appendage_sqft": 50.0}
    out = _apply_chase_ratification(m, {"estimate_number": "EST-999999"})
    assert out == m
    out2 = _apply_chase_ratification(m, {"estimate_number": "EST-373526",
                                         "lp_appendage_dims": {}})
    assert out2 == m  # no machinery dims → gate stays shut
