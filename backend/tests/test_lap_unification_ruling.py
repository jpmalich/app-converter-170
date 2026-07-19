"""LAP UNIFICATION RULING (Howard, 2026-07-19) — four seals, pinned:

1. GEOMETRY-SOURCE RULE EXTENDS TO MATERIALS: material-list areas bind
   the sealed key's taped/TAPED-DERIVED dims wherever they exist; AI-run
   values are the NAMED FALLBACK only; every area line names its basis.
2. GABLE CONVENTION SEALED: book w×h×0.7 governs estimating area; the
   AI true-triangle read stays on record, deviation-flagged.
3. PIECE FORMULA SEALED: lap = 11 pcs/square (area ÷ 100); the 9.17 PDF
   divisor is RETIRED for 38 Series lap (reference pedigree only).
4. WASTE IS THE CONTRACTOR'S: estimate waste_pct field only (default 0,
   per-estimate, surfaced); DEFAULT_WASTE auto-default RETIRED; no
   formula anywhere silently includes waste.
Result: Letrick app lap = 255 = sealed key EXACTLY (residual zero).
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


def test_seal1_key_bound_area_every_line_names_basis(pkg):
    """Item 1: siding area = sealed key raw 2099.7 (closes the +201.2
    frame gap by construction); every component names its basis; the AI
    read stays on record as the named fallback/comparison."""
    ab = pkg["summary"]["area_basis"]
    comps = {b["component"]: b for b in ab}
    assert comps["front wall"]["sqft"] == 478.1
    assert comps["back wall"]["sqft"] == 535.7
    assert comps["stepped side walls"]["sqft"] == 566.4
    assert comps["gables"]["sqft"] == 367.5
    assert comps["chase faces"]["sqft"] == 152.39
    assert all(("TAPED" in b["basis"] or "BOOK" in b["basis"]) for b in ab)
    # itemization carries the key's own rounding ("~566.4" sides) —
    # governing total is the key raw 2099.7, bound below
    assert abs(sum(b["sqft"] for b in ab) - 2099.7) <= 0.5
    assert pkg["summary"]["chase_face_ratification"]["siding_sqft_effective"] == 2099.7
    ai = pkg["summary"]["area_basis_ai_comparison"]
    assert ai["siding_sqft"] == 1889.1
    assert "named fallback" in ai["note"]


def test_seal2_gable_book_convention_with_deviation_flag(pkg):
    """Item 2: book w×h×0.7 governs (367.5); AI true-triangle 380.1 on
    record, Δ −12.6 flagged. Constant sealed in code."""
    from lp_package import GABLE_BOOK_FACTOR
    assert GABLE_BOOK_FACTOR == 0.7
    g = next(b for b in pkg["summary"]["area_basis"] if b["component"] == "gables")
    assert "BOOK w×h×0.7" in g["basis"]
    assert "380.1 on record" in g["basis"] and "-12.6 flagged" in g["basis"]


def test_seal3_book_piece_formula_pdf_retired(pkg):
    """Item 3: 11 pcs/sq (book counter convention, cited); base count
    carries NO baked waste: 2099.7 ÷ 100 × 11 = 230.97."""
    from lp_conventions import LAP_PCS_PER_SQUARE_16FT
    from lp_smartside_formulas import LAP_PCS_PER_SQUARE
    assert LAP_PCS_PER_SQUARE == LAP_PCS_PER_SQUARE_16FT['8" Lap'] == 11
    lap = next(l for l in pkg["lines"] if "38 Series Lap 3/8" in l["name"])
    assert lap["math"]["base_qty"] == 230.97          # no waste baked
    assert "book 11 pcs/sq" in lap["math"]["formula"]
    assert "PDF 9.17 retired" in lap["math"]["formula"]


def test_seal4_waste_is_contractors_no_silent_waste(pkg):
    """Item 4: the applied waste is the estimate's waste_pct field
    (Letrick field = 10 → 0.10 applied AND reported); assemble with no
    _waste_pct applies and reports 0 — no formula silently adds waste."""
    assert pkg["summary"]["waste_pct_applied"] == 0.10  # contractor's field, surfaced
    from lp_package import assemble_lp_package
    d = assemble_lp_package({"siding_sqft": 1000.0})
    lap = next(l for l in d["lines"] if "38 Series Lap 3/8" in l["name"])
    assert lap["qty"] == 110                       # ceil(1000 ÷ 100 × 11), zero waste
    assert d["summary"]["waste_pct_applied"] == 0.0


def test_letrick_identity_app_equals_key_residual_zero(pkg):
    """Item 5 receipt: restated app lap (key-bound area, book formula,
    contractor 10%) = 255 = the sealed key's 255 — residual ZERO."""
    from letrick_hand_takeoff_key import LETRICK_HAND_TAKEOFF_KEY as KEY
    key_lap = next(l for l in KEY["lines"] if "38 Series Lap" in l["item"])
    app_lap = next(l for l in pkg["lines"] if "38 Series Lap 3/8" in l["name"])
    assert app_lap["qty"] == key_lap["qty"] == 255
