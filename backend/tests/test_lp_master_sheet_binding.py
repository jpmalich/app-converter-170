"""CASILE ITEM 3 — MASTER-SHEET BINDING pins (2026-07-24).

Root cause found: the Pro-Quote company's `price_tier_id` DANGLED (tier
reseed churn recreated price_tiers with new ids) so `_load_tier_sheet_for`
returned an EMPTY sheet — every sheet-bound row (gutter, capping, cleanup)
went pending with a MISLEADING 'no dealer cost' reason. Also: the sheet
index ignored the company's catalog OVERRIDES, so binding spoke different
numbers than the tabs.

FIX PINNED here:
  • dangling tier pointer → default-tier sheet fallback (the SAME fallback
    the catalog surface applies) — never an empty sheet
  • company catalog overrides merge into the sheet index (section::name
    keyed, exactly like the catalog surface) — one sheet everywhere
  • $0.00 sheet rows: the five misc-labor rows price at $0 (labor is the
    contractor's, v3 zeroing sealed 2026-07-24); any OTHER $0.00 sheet row
    stays pending — escalated by name, never a placeholder
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

# The five misc-labor rows (v3 zeroing, sealed 2026-07-24): $0.00 on EVERY
# tier sheet AND $0 labor until the contractor fills them — the Price
# Catalog LABOR column is the standing home; never a placeholder, never a
# supplier-side guess.
MISC_LABOR_NAMES = (
    "cap window", "cap entry door", "cap patio door",
    "cap single garage door", "clean up/ haul away job debris",
)
ZERO_DOLLAR_SHEET_ROWS = set(MISC_LABOR_NAMES)


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
    """Supplier-admin cost-preview: ONE MONEY SURFACE (2026-07-23) strips
    every dollar from the contractor preview — binding dollar pins ride
    the admin surface (same engine, same sheet binding)."""
    import os
    tok = os.environ.get("TEST_ADMIN_TOKEN") or os.environ.get("SUPPLIER_ADMIN_TOKEN", "")
    r = session.post(f"{API}/admin/estimates/{CASILE_EST}/lp-package/cost-preview",
                     json={}, headers={"X-Admin-Token": tok}, timeout=90)
    assert r.status_code == 200, r.text
    return r.json()


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
    """The sheet the contractor SEES is tier + their overrides — the
    binding index must speak the same numbers as the catalog surface.
    (V3 zeroing healed the machine-era lab residue, so the mechanism is
    exercised with a temporary override, cleaned up after.)"""
    key = 'Seamless Gutter::Gutter 6"'

    async def run():
        await patched_db.catalogs.update_one(
            {"company_id": CASILE_COMPANY},
            {"$set": {f"overrides.{key}": {"lab": 1.0}}})
        try:
            from routes.lp_package_routes import _load_tier_sheet_for
            return await _load_tier_sheet_for({"company_id": CASILE_COMPANY})
        finally:
            await patched_db.catalogs.update_one(
                {"company_id": CASILE_COMPANY},
                {"$unset": {f"overrides.{key}": ""}})

    idx = loop.run_until_complete(run())
    assert idx['gutter 6"']["lab"] == 1.0, idx.get('gutter 6"')
    assert idx['gutter 6"']["mat"] > 0


def test_no_machine_era_lab_residue_in_casile_catalog(loop, patched_db):
    """V3 zeroing (sealed 2026-07-24): the machine-seeded catalog labor
    overrides (siding $250, gutter/downspout $1.00/LF, soffit $2, …) were
    HEALED — labor overrides exist only when the contractor typed them."""
    async def run():
        cat = await patched_db.catalogs.find_one(
            {"company_id": CASILE_COMPANY}, {"_id": 0, "overrides": 1})
        return (cat or {}).get("overrides") or {}

    overrides = loop.run_until_complete(run())
    labbed = {k: v for k, v in overrides.items()
              if isinstance(v, dict) and float(v.get("lab") or 0) > 0}
    assert labbed == {}, labbed


def test_casile_gutter_lines_bind_to_master_sheet(pkg):
    """Gutter 6\" = sheet mat 3.25, labor $0 (contractor's) → unit sell
    3.25; sheet numbers are SELL-side, no LP margin re-applies (ruled)."""
    by_name = {str(l.get("name") or "").lower(): l for l in pkg["lines"]}
    g = by_name['gutter 6"']
    assert g["pricing_status"] == "priced", g
    assert g["unit_sell"] == 3.25, g
    d = by_name['downspout 6"']
    assert d["pricing_status"] == "priced" and d["unit_sell"] == 2.8, d
    for n in ("elbow", "end cap", "mitre", "pipe clips",
              "gutter sealant", "hangars with screws"):
        assert by_name[n]["pricing_status"] == "priced", (n, by_name[n])


def test_zero_dollar_rows_price_at_zero_labor(pkg):
    """V3 ZEROING (sealed 2026-07-24): the five $0.00-sheet rows price at
    $0 — labor is the contractor's, basis named, NOTHING pending on the
    Casile package, never a supplier-side guess."""
    pending = {str(l.get("name") or "").lower()
               for l in pkg["lines"] if l.get("pricing_status") == "pending"}
    assert pending == set(), pending
    by_name = {str(l.get("name") or "").lower(): l for l in pkg["lines"]}
    for name in MISC_LABOR_NAMES:
        l = by_name[name]
        assert l["pricing_status"] == "priced", l
        assert l["unit_sell"] == 0.0, (name, l.get("unit_sell"))
        assert "labor is the contractor's" in str(l.get("price_basis")), l.get("price_basis")
    summary = (pkg.get("summary") or {}).get("pricing") or {}
    assert summary.get("pending_lines") == 0


def test_contractor_preview_same_pending_escalations(session):
    """The (unpriced) contractor preview mirrors the escalation state —
    with conventions bound there is nothing pending on Casile."""
    r = session.post(f"{API}/estimates/{CASILE_EST}/lp-package/preview",
                     json={}, timeout=90)
    assert r.status_code == 200, r.text
    pending = {str(l.get("name") or "").lower()
               for l in r.json()["lines"] if l.get("pricing_status") == "pending"}
    assert pending == set(), pending
