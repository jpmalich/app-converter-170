"""ONE MONEY SURFACE — P0 pins (Howard ruling, 2026-07-23).

DEFECT (live customer quote, caught by human review pre-send): the
customer total was double-counting — the quote composed the AI Material
List's margin-applied package sells back through the estimate margin on
top of the group tabs.

PERMANENT RULE pinned here:
  1. ALL pricing lives exclusively on the group tabs/summary. The
     customer quote, base cost, header total and every frozen/QR output
     derive from that surface alone — no second contributor possible.
  2. The AI Material List is the VERIFICATION surface: items, quantities,
     units, derivations, provenance chips only. NO unit prices, NO line
     totals, NO materials-total row — dollar keys never leave the server
     on a contractor/customer package payload.
  3. The accept page totals from the SAME tab scope the sent quote was
     composed from (quote_tab_scope) — never an all-tab sum.
  Supplier-admin cost-preview (X-Admin-Token) keeps the full pricing
  layer — it is not a contractor/customer surface.
"""
import asyncio
import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
sys_path_added = str(BACKEND)
import sys  # noqa: E402

sys.path.insert(0, sys_path_added)
load_dotenv(BACKEND / ".env")
from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

CASILE_EST = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"  # EST-523061
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"
ADMIN_TOKEN = os.environ.get("TEST_ADMIN_TOKEN") or os.environ.get("SUPPLIER_ADMIN_TOKEN", "")
FRONTEND_SRC = BACKEND.parent / "frontend" / "src"

DOLLAR_KEYS = {"unit_sell", "line_sell", "total_sell", "price_basis",
               "unit_cost", "line_cost", "total_cost", "cost_basis"}


def _dollar_keys_in(obj, found=None):
    found = found if found is not None else set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in DOLLAR_KEYS:
                found.add(k)
            _dollar_keys_in(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _dollar_keys_in(v, found)
    return found


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


# ── Rule 2: the AI Material List surfaces are UNPRICED ──────────────────

def test_contractor_preview_carries_no_dollars(session):
    r = session.post(f"{API}/estimates/{CASILE_EST}/lp-package/preview",
                     json={}, timeout=90)
    assert r.status_code == 200, r.text
    found = _dollar_keys_in(r.json())
    assert not found, f"dollar keys leaked on the contractor preview: {found}"


def test_frozen_qr_snapshot_carries_no_dollars(session):
    """Freeze mints the QR share; the public read (legacy snapshots
    included) must render unpriced."""
    r = session.post(f"{API}/estimates/{LETRICK_EST}/lp-material-list/freeze",
                     json={}, timeout=90)
    assert r.status_code == 200, r.text
    token = r.json().get("token") or r.json().get("share", {}).get("token")
    assert token, r.text
    pub = requests.get(f"{API}/public/lp-material-list/{token}", timeout=30)
    assert pub.status_code == 200, pub.text
    found = _dollar_keys_in(pub.json())
    assert not found, f"dollar keys leaked on the public QR list: {found}"


def test_admin_cost_preview_keeps_full_pricing(session):
    """The supplier-admin surface is NOT a contractor surface — the full
    cost/sell layer stays available there."""
    r = session.post(f"{API}/admin/estimates/{LETRICK_EST}/lp-package/cost-preview",
                     json={}, headers={"X-Admin-Token": ADMIN_TOKEN}, timeout=60)
    assert r.status_code == 200, r.text
    pr = r.json()["summary"]["pricing"]
    assert pr["total_sell"] > 0 and pr["total_cost"] > 0


# ── Rule 1: the quote composes from the group tabs alone ────────────────

def test_quote_composition_has_no_package_contributor():
    """JSX pin: the retired pkgLines merge (the double-count vector) must
    never return — quoteEstimate derives from est.lines only."""
    src = (FRONTEND_SRC / "pages" / "EstimateEditor.jsx").read_text()
    assert "ONE MONEY SURFACE" in src
    assert "pkgLines" not in src, "package lines composing the quote again — the pinned P0"
    m = re.search(r"const quoteEstimate = useMemo\(\(\) => \{(.*?)\}, \[", src, re.S)
    assert m, "quoteEstimate memo missing"
    body = m.group(1)
    assert "lpPkg" not in body, "quoteEstimate reads the package — second contributor"


def test_material_list_surfaces_render_no_money():
    """JSX pins: no materials-total row, no price columns on the panel,
    the print HTML, or the QR share page."""
    panel = (FRONTEND_SRC / "components" / "estimate" / "LpMaterialListPanel.jsx").read_text()
    assert "lp-material-total" not in panel
    assert "lp-material-unpriced-note" in panel
    assert "Unit $" not in panel and "Line $" not in panel
    share = (FRONTEND_SRC / "pages" / "MaterialListShare.jsx").read_text()
    assert "material-share-total" not in share
    assert "material-share-unpriced-note" in share
    assert "Unit $" not in share and "Line $" not in share
    print_html = (FRONTEND_SRC / "lib" / "lpMaterialList.js").read_text()
    assert "Materials total" not in print_html
    assert "Unit $" not in print_html


# ── Rule 3: accept page totals from the sent quote's tab scope ──────────

@pytest.fixture(scope="module")
def loop():
    l = asyncio.new_event_loop()
    yield l
    l.close()


def test_accept_page_totals_from_quote_scope_only(loop):
    from motor.motor_asyncio import AsyncIOMotorClient

    from services import calc_totals

    est_id = f"zz-money-surface-{uuid.uuid4().hex[:8]}"
    token = uuid.uuid4().hex
    est = {
        "id": est_id, "accept_token": token, "quote_tab_scope": ["lp_smart"],
        "company_id": "ecfe9396-0b00-4839-94c0-79cdba1cb8fc",
        "estimate_number": "ZZ-MONEY-1", "customer_name": "ZZ Test",
        "waste_pct": 0, "margin_pct": 30.0, "pricing_mode": "margin",
        "tax_enabled": False,
        "lines": [
            {"tab": "lp_smart", "section": "S", "name": "A", "qty": 10, "mat": 10.0, "lab": 0.0},
            {"tab": "vinyl", "section": "S", "name": "B", "qty": 10, "mat": 99.0, "lab": 0.0},
        ],
    }

    async def run(action, *args):
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        try:
            if action == "insert":
                await db.estimates.insert_one(dict(args[0]))
            else:
                await db.estimates.delete_one({"id": args[0]})
        finally:
            client.close()

    loop.run_until_complete(run("insert", est))
    try:
        r = requests.get(f"{API}/public/accept/{token}", timeout=30)
        assert r.status_code == 200, r.text
        total = r.json()["total"]
        scoped = round(calc_totals(est, tabs=["lp_smart"])["sell"], 2)
        all_tabs = round(calc_totals(est)["sell"], 2)
        assert total == scoped, (total, scoped)
        assert total != all_tabs, "accept page summed ALL tabs — second contributor"
    finally:
        loop.run_until_complete(run("delete", est_id))


def test_calc_totals_scope_filters_lines_misc_and_openings():
    from services import calc_totals

    est = {
        "waste_pct": 0, "margin_pct": 0, "pricing_mode": "margin", "tax_enabled": False,
        "lines": [
            {"tab": "lp_smart", "section": "S", "name": "A", "qty": 1, "mat": 100.0, "lab": 0.0},
            {"tab": "vinyl", "section": "S", "name": "B", "qty": 1, "mat": 50.0, "lab": 0.0},
        ],
        "misc_labor": [{"tab": "vinyl", "qty": 1, "rate": 25.0}],
        "vero_openings": [{"qty": 1}],
        "mezzo_openings": [{"qty": 1}],
    }
    scoped = calc_totals(est, tabs=["lp_smart"])
    assert scoped["sub_mat"] == 100.0
    every = calc_totals(est)
    assert every["sub_mat"] >= 150.0
