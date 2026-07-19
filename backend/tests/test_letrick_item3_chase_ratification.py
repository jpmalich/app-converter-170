"""LETRICK REGRESSION GUARD — pins the Letrick estimate
(8f95c9c2-add9-416a-92f3-786a4ea2ce83), item-3 chase ratification.
Renamed from test_item3_chase_ratification.py (hygiene order, 2026-07-20):
the filename now states the estimate this file pins.

ITEM-3 CHASE-SIDING RATIFICATION + SEALED CORNER CONVENTION (Howard,
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
    """Face math pinned: outboard = width × (chase h − wall h); sides =
    2 × depth × chase h; wall-abutting face carried by the wall's gross
    strip. WASTE NOTE AMENDED (lap unification ruling, 2026-07-19):
    CHASE_FACE_WASTE is RETIRED with the DEFAULT_WASTE auto-default —
    provenance constant only; chase faces carry NO own waste, the
    contractor's field applies once at the lap line."""
    from lp_package import CHASE_FACE_WASTE, chase_face_sqft
    from lp_smartside_formulas import DEFAULT_WASTE
    assert CHASE_FACE_WASTE == DEFAULT_WASTE == 0.10  # provenance only
    faces = chase_face_sqft(64 / 12.0, 2.583, 19.552, 9.92)
    assert faces["outboard_sqft"] == 51.37
    assert faces["sides_sqft"] == 101.01
    assert faces["total_sqft"] == 152.38


def test_app_ledger_key_bound_area_and_unified_lap(pkg):
    """PIN AMENDED (lap unification ruling, 2026-07-19; was 227→230 swap
    pin): APP line now KEY-BOUND + book formula + contractor waste —
    area 2099.7 (sealed key raw), base 2099.7 ÷ 100 × 11 = 230.97 (NO
    baked waste), contractor's field 10% → 254.06 → ceil = 255 = the
    sealed key EXACTLY (residual zero). Receipts on the line note."""
    lap = _line(pkg, "38 Series Lap 3/8")
    assert lap["qty"] == 255
    assert lap["math"]["base_qty"] == 230.97
    assert lap["math"]["ordered_pcs"] == 255
    assert lap["math"]["waste_pct"] == 10.0
    assert "book 11 pcs/sq" in lap["math"]["formula"]
    assert "AREA BASIS KEY-BOUND" in lap["note"]
    assert "CHASE FACES RATIFIED (item-3, 2026-07-19)" in lap["note"]
    assert "SUPERSEDE AI-attributed 130 ft² (swap, no double count)" in lap["note"]
    cfr = pkg["summary"]["chase_face_ratification"]
    assert cfr["total_sqft"] == 152.39 and cfr["ai_sqft"] == 130.0
    assert cfr["siding_sqft_effective"] == 2099.7


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
    2099.7, lap 254 → 255. LEDGERS UNIFIED (lap unification ruling,
    2026-07-19): the app line binds the key area + book formula +
    contractor waste and lands on the SAME 255 — residual zero."""
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
    passes through _apply_key_bound_areas untouched (AI values stay the
    NAMED FALLBACK where no sealed key exists — geometry-source rule)."""
    from routes.lp_package_routes import _apply_key_bound_areas
    m = {"siding_sqft": 1000.0, "_ai_appendage_sqft": 50.0}
    out = _apply_key_bound_areas(m, {"estimate_number": "EST-999999"})
    assert out == m
    out2 = _apply_key_bound_areas(m, {"estimate_number": "EST-373526",
                                      "lp_appendage_dims": {}})
    assert out2 == m  # no machinery dims → gate stays shut
