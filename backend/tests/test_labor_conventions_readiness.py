"""LABOR CONVENTIONS (Howard's standing defaults, re-priced by the
2026-07-24 Casile close-out ruling) + ESTIMATE READINESS CHECKLIST /
SOFT QUOTE GATE (authorized 2026-07-23).

Conventions pinned:
  • Cap window $98 · Cap entry door $107 · Cap patio door $100 ·
    Cap single garage door $138 · clean up/haul away $334/job
  • Rows still carrying a RETIRED default (2026-07-23 provisional set:
    25/75/75/100/150) are machine bindings — they REBIND on rebuild.
  • NOT master-sheet SKUs — they bind wherever the named row would
    otherwise be $0.00; a REAL sheet price outranks the convention; a
    contractor-edited tab price inherits through rebuilds and wins
    (contractor-editable per estimate, same class as waste).

Readiness pinned:
  • GET /estimates/{id}/readiness lists pending prices, open flags,
    unentered field-verify, unpriced money-surface rows.
  • SOFT ONLY (ruled): the Customer Quote flow shows the warning and
    always lets the contractor proceed — never a hard block.
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")
from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

CASILE_EST = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"
FRONTEND_SRC = BACKEND.parent / "frontend" / "src"

EXPECTED = {
    "cap window": 98.0, "cap entry door": 107.0, "cap patio door": 100.0,
    "cap single garage door": 138.0, "clean up/ haul away job debris": 334.0,
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


def test_constants_are_howards_numbers():
    from lp_conventions import LABOR_CONVENTIONS
    assert LABOR_CONVENTIONS == EXPECTED


def test_price_package_binds_conventions_when_sheet_is_zero():
    from lp_costs import DEFAULT_TIER, MARGIN_TIER_SEED, price_package
    cfg = {"tiers": dict(MARGIN_TIER_SEED), "default_tier": DEFAULT_TIER,
           "category_overrides": {}, "line_overrides": {}}
    pkg = {"lines": [
        {"name": "Cap window", "section": "Capping", "qty": 4, "unit": "Each"},
        {"name": "clean up/ haul away job debris", "section": "Misc", "qty": 1, "unit": "JOB"},
    ], "summary": {}}
    sheet = {"cap window": {"mat": 0.0, "lab": 0.0},
             "clean up/ haul away job debris": {"mat": 0.0, "lab": 0.0}}
    price_package(pkg, cfg, None, tier_sheet=sheet)
    cap, clean = pkg["lines"]
    assert cap["pricing_status"] == "priced" and cap["unit_sell"] == 98.0
    assert cap["line_sell"] == 392.0
    assert "labor convention" in cap["price_basis"]
    assert clean["unit_sell"] == 334.0 and "labor convention" in clean["price_basis"]


def test_real_sheet_price_outranks_convention():
    from lp_costs import DEFAULT_TIER, MARGIN_TIER_SEED, price_package
    cfg = {"tiers": dict(MARGIN_TIER_SEED), "default_tier": DEFAULT_TIER,
           "category_overrides": {}, "line_overrides": {}}
    pkg = {"lines": [{"name": "Cap window", "section": "Capping", "qty": 2, "unit": "Each"}],
           "summary": {}}
    price_package(pkg, cfg, None, tier_sheet={"cap window": {"mat": 0.0, "lab": 40.0}})
    l = pkg["lines"][0]
    assert l["unit_sell"] == 40.0
    assert "master price sheet" in l["price_basis"]


def test_casile_money_surface_carries_conventions(session):
    """Tab lines (the money surface) carry the standing labor defaults;
    the pre-existing edited row (Cap window (Windows) @ $20) is untouched —
    contractor-edited values always win."""
    est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
    rows = {(l.get("tab"), l.get("name")): l for l in est["lines"]}
    assert rows[("lp_smart", "Cap window")]["lab"] == 98.0
    assert rows[("lp_smart", "Cap entry door")]["lab"] == 107.0
    assert rows[("lp_smart", "Cap patio door")]["lab"] == 100.0
    assert rows[("lp_smart", "Cap single garage door")]["lab"] == 138.0
    assert rows[("lp_smart", "clean up/ haul away job debris")]["lab"] == 334.0
    assert rows[("windows", "Cap window (Windows)")]["lab"] == 20.0  # edited value wins


def test_readiness_endpoint_shape_and_content(session):
    r = session.get(f"{API}/estimates/{CASILE_EST}/readiness", timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d) >= {"items", "open_count", "ready"}
    assert d["open_count"] == len(d["items"])
    kinds = {it["kind"] for it in d["items"]}
    # Casile today: open mapping flags + genuinely unpriced money rows;
    # every item carries a human label.
    assert "open_flag" in kinds
    assert all(it.get("label") for it in d["items"])
    # conventions bound → the five labor rows never appear as pending
    labels = " | ".join(it["label"].lower() for it in d["items"])
    for name in EXPECTED:
        assert f"pending price (escalated by name): {name}" not in labels


def test_quote_gate_is_soft_never_blocking():
    """JSX pins: the readiness warning renders inside the quote flow,
    states it is soft, and NOTHING gates the send/print actions on it."""
    qm = (FRONTEND_SRC / "components" / "QuoteModal.jsx").read_text()
    assert "quote-readiness-warning" in qm
    assert "you can proceed" in qm.lower()
    # no action is disabled by readiness state — soft only (ruled)
    assert "readiness" not in qm[qm.index("send-email-btn") - 600:qm.index("send-email-btn")].lower()
    ts = (FRONTEND_SRC / "components" / "estimate" / "TotalsSummary.jsx").read_text()
    assert "readiness-btn" in ts and "ReadinessPanel" in ts
    rp = (FRONTEND_SRC / "components" / "estimate" / "ReadinessPanel.jsx").read_text()
    assert "readiness-panel" in rp and "never a hard block" in rp
