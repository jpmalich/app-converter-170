"""CASILE ITEM 3 — MASTER-SHEET BINDING pins (2026-07-24).

Root cause found: the Pro-Quote company's `price_tier_id` DANGLED (tier
reseed churn recreated price_tiers with new ids) so `_load_tier_sheet_for`
returned an EMPTY sheet — every sheet-bound row (gutter, capping, cleanup)
went pending with a MISLEADING 'no dealer cost' reason. Also: the sheet
index ignored the company's catalog OVERRIDES (Gutter 6" carries their
$1.00/LF labor), so binding spoke different numbers than the tabs.

FIX PINNED here:
  • dangling tier pointer → default-tier sheet fallback (the SAME fallback
    the catalog surface applies) — never an empty sheet
  • company catalog overrides merge into the sheet index (section::name
    keyed, exactly like the catalog surface) — one sheet everywhere
  • $0.00 sheet rows STAY pending — escalated by name, never a placeholder
    (Casile: Cap window / Cap entry door / Cap patio door / Cap single
    garage door / clean up-haul away hold $0.00 on EVERY tier sheet)
"""
import asyncio
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

CASILE_EST = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"  # EST-523061
CASILE_COMPANY = "ecfe9396-0b00-4839-94c0-79cdba1cb8fc"

# The ONLY honest pendings on the Casile package: $0.00 on every tier
# sheet — escalated to Howard BY NAME, never placeholder-priced.
ZERO_DOLLAR_SHEET_ROWS = {
    "cap window", "cap entry door", "cap patio door",
    "cap single garage door", "clean up/ haul away job debris",
}


@pytest.fixture(scope="module")
def loop():
    """One loop for every direct-db call in this module — with a FRESH
    motor client patched in, so the app's shared client never binds to
    (and outlives) this module's loop."""
    l = asyncio.new_event_loop()
    yield l
    l.close()


@pytest.fixture(scope="module")
def patched_db(loop):
    import os
    from motor.motor_asyncio import AsyncIOMotorClient
    import routes.lp_package_routes as lpr
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    fresh = client[os.environ["DB_NAME"]]
    orig = lpr.db
    lpr.db = fresh
    yield fresh
    lpr.db = orig
    client.close()


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def pkg(session):
    r = session.post(f"{API}/estimates/{CASILE_EST}/lp-package/preview",
                     json={}, timeout=90)
    assert r.status_code == 200, r.text
    return r.json()


def _load_sheet(loop, est: dict) -> dict:
    from routes.lp_package_routes import _load_tier_sheet_for
    return loop.run_until_complete(_load_tier_sheet_for(est))


def test_dangling_tier_pointer_falls_back_never_empty(loop, patched_db):
    """A company whose price_tier_id resolves to NO tier doc still gets
    the default tier sheet — an empty sheet unbinds every row (the bug)."""

    async def run():
        cid = f"zz-test-dangling-{uuid.uuid4().hex[:8]}"
        await patched_db.companies.insert_one({"id": cid, "name": "ZZ dangling-tier test co",
                                               "price_tier_id": "does-not-exist-anymore"})
        try:
            from routes.lp_package_routes import _load_tier_sheet_for
            return await _load_tier_sheet_for({"company_id": cid})
        finally:
            await patched_db.companies.delete_one({"id": cid})

    idx = loop.run_until_complete(run())
    assert len(idx) > 100, "fallback sheet must load — empty sheet is the pinned bug"
    assert 'gutter 6"' in idx


def test_company_overrides_merge_into_sheet(loop, patched_db):
    """The sheet the contractor SEES is tier + their overrides: Pro-Quote
    carries Gutter/Downspout 6\" labor $1.00/LF as catalog overrides —
    the binding index must speak the same numbers as the tabs."""
    idx = _load_sheet(loop, {"company_id": CASILE_COMPANY})
    assert idx['gutter 6"']["lab"] == 1.0, idx.get('gutter 6"')
    assert idx['gutter 6"']["mat"] > 0
    assert idx['downspout 6"']["lab"] == 1.0, idx.get('downspout 6"')


def test_casile_gutter_lines_bind_to_master_sheet(pkg):
    """Gutter 6\" = sheet mat 3.25 + override lab 1.00 → unit sell 4.25;
    sheet numbers are SELL-side, no LP margin re-applies (ruled)."""
    by_name = {str(l.get("name") or "").lower(): l for l in pkg["lines"]}
    g = by_name['gutter 6"']
    assert g["pricing_status"] == "priced", g
    assert g["unit_sell"] == 4.25, g
    d = by_name['downspout 6"']
    assert d["pricing_status"] == "priced" and d["unit_sell"] == 3.8, d
    for n in ("elbow", "end cap", "mitre", "pipe clips",
              "gutter sealant", "hangars with screws"):
        assert by_name[n]["pricing_status"] == "priced", (n, by_name[n])


def test_zero_dollar_rows_escalate_by_name_never_placeholder(pkg):
    """EVERY pending line on the Casile package is one of the five $0.00
    master-sheet rows — nothing else may be pending, and none of the five
    may carry an invented price."""
    pending = {str(l.get("name") or "").lower()
               for l in pkg["lines"] if l.get("pricing_status") == "pending"}
    assert pending == ZERO_DOLLAR_SHEET_ROWS, pending
    summary = (pkg.get("summary") or {}).get("pricing") or {}
    assert summary.get("pending_lines") == len(ZERO_DOLLAR_SHEET_ROWS)
    for l in pkg["lines"]:
        if str(l.get("name") or "").lower() in ZERO_DOLLAR_SHEET_ROWS:
            assert l.get("unit_sell") is None, l
