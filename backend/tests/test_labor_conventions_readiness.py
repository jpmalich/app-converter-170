"""LABOR IS THE CONTRACTOR'S — v3 ZEROING (sealed 2026-07-24) +
ESTIMATE READINESS CHECKLIST / SOFT QUOTE GATE (authorized 2026-07-23).

Labor pinned:
  • ALL labor defaults = $0 until the contractor fills them — NO
    exceptions. The five provisional guesses (98/107/100/138/334)
    RETIRED ENTIRELY; both retired generations rebind on rebuild.
  • The Price Catalog per-item LABOR $ column is the standing labor
    home ("Labor is yours to set — overrides save to your company
    only") — a filled catalog rate flows through the sheet binding; a
    contractor-edited tab price (lab_src "human") wins forever.
  • The five misc-labor rows price at $0 (basis named) — never a
    "pending price" escalation, never a supplier-side guess.

Readiness pinned:
  • GET /estimates/{id}/readiness lists pending prices, open flags,
    unentered field-verify, unpriced money-surface rows, and the
    aggregated LABOR PENDING statement.
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

MISC_ROWS = ("cap window", "cap entry door", "cap patio door",
             "cap single garage door", "clean up/ haul away job debris")


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


def test_constants_are_zeroed_v3():
    import lp_conventions
    assert not hasattr(lp_conventions, "PROVISIONAL_LABOR_RATES")
    assert not hasattr(lp_conventions, "LABOR_CONVENTIONS")
    assert set(lp_conventions.MISC_LABOR_ROWS) == set(MISC_ROWS)
    assert lp_conventions.RETIRED_LABOR_DEFAULTS == {
        "cap window": {25.0, 98.0},
        "cap entry door": {75.0, 107.0},
        "cap patio door": {75.0, 100.0},
        "cap single garage door": {100.0, 138.0},
        "clean up/ haul away job debris": {150.0, 334.0},
    }


def test_price_package_zeroes_misc_labor_when_sheet_is_zero():
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
    assert cap["pricing_status"] == "priced" and cap["unit_sell"] == 0.0
    assert cap["line_sell"] == 0.0
    assert "labor is the contractor's" in cap["price_basis"]
    assert clean["unit_sell"] == 0.0
    assert "labor is the contractor's" in clean["price_basis"]


def test_filled_catalog_rate_flows_through_the_sheet():
    """The Price Catalog LABOR column is the standing home — a filled
    rate arrives through the sheet binding (tier + company overrides)."""
    from lp_costs import DEFAULT_TIER, MARGIN_TIER_SEED, price_package
    cfg = {"tiers": dict(MARGIN_TIER_SEED), "default_tier": DEFAULT_TIER,
           "category_overrides": {}, "line_overrides": {}}
    pkg = {"lines": [{"name": "Cap window", "section": "Capping", "qty": 2, "unit": "Each"}],
           "summary": {}}
    price_package(pkg, cfg, None, tier_sheet={"cap window": {"mat": 0.0, "lab": 40.0}})
    l = pkg["lines"][0]
    assert l["unit_sell"] == 40.0
    assert "master price sheet" in l["price_basis"]


def test_casile_money_surface_is_labor_zeroed(session):
    """Tab lines (the money surface) carry $0 labor in the pending state;
    the pre-existing edited row (Cap window (Windows) @ $20) is untouched —
    contractor-edited values always win."""
    est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
    rows = {(l.get("tab"), l.get("name")): l for l in est["lines"]}
    for name in ("Cap window", "Cap entry door", "Cap patio door",
                 "Cap single garage door", "clean up/ haul away job debris"):
        assert rows[("lp_smart", name)]["lab"] == 0.0, name
        assert rows[("lp_smart", name)]["lab_src"] == "pending", name
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
    # v3 zeroing: the five misc-labor rows never appear as pending prices
    labels = " | ".join(it["label"].lower() for it in d["items"])
    for name in MISC_ROWS:
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
