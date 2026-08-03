"""RULE 1 (Howard ruled 2026-07-31, pre-purge): A MATERIAL LIST IS BUILT
ONLY FROM ITS OWN ESTIMATE'S DATA. Deleting estimate A must never change
estimate B's list. The corner_locators flag once printed "261 Haugh" on
3 Degree — the class is real, so the guarantee is pinned, not asserted.

NO EXCEPTIONS (Howard ruled 2026-08-03): the former "one named exception"
— the pair-lp sibling-run fallback — was REVOKED and severed. Estimates
are self-contained; no estimate reads another estimate, ever. Cross-family
fill is post-September.
"""
import json
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creds_for_tests import TEST_PASSWORD

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", TEST_PASSWORD)

MEAS_A = {"siding_sqft": 2000, "eaves_lf": 120, "rakes_lf": 80,
          "soffit_sqft": 200, "outside_corner_count": 4,
          "inside_corner_count": 2, "window_count": 10, "door_count": 2,
          "overhang_in": 12}
MEAS_B = {"siding_sqft": 3100, "eaves_lf": 150, "rakes_lf": 95,
          "soffit_sqft": 260, "outside_corner_count": 6,
          "inside_corner_count": 1, "window_count": 14, "door_count": 3,
          "overhang_in": 16}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture()
def est_factory(s):
    made = []

    def make(kind, meas):
        r = s.post(f"{API}/estimates",
                   json={"customer_name": f"TEST_ISO-{uuid.uuid4().hex[:6]}",
                         "kind": kind})
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        made.append(eid)
        if meas:
            r = s.put(f"{API}/estimates/{eid}",
                      json={"hover_measurements": dict(meas), "waste_pct": 10})
            assert r.status_code == 200, r.text
        return eid

    yield make
    for eid in made:
        s.delete(f"{API}/estimates/{eid}")


def _rederive(s, eid):
    r = s.post(f"{API}/estimates/{eid}/rederive", json={"trigger": "test"})
    assert r.status_code == 200, r.text
    return r.json()["lines"]


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


# ═══════════ THE GUARANTEE — delete A, B is byte-identical ═════════════
def test_material_list_reads_only_its_own_estimate(est_factory, s):
    """Two estimates, different houses. Snapshot B's full doc and derived
    lines, DELETE A, prove B is BYTE-IDENTICAL and re-derives identically."""
    a = est_factory("siding", MEAS_A)
    b = est_factory("siding", MEAS_B)
    lines_b_before = _rederive(s, b)
    doc_b_before = s.get(f"{API}/estimates/{b}").text

    r = s.delete(f"{API}/estimates/{a}")
    assert r.status_code == 200, r.text
    assert s.get(f"{API}/estimates/{a}").status_code == 404, "A must be gone"

    doc_b_after = s.get(f"{API}/estimates/{b}").text
    assert doc_b_after == doc_b_before, \
        "estimate B's stored doc changed when A was deleted — cross-read"
    lines_b_after = _rederive(s, b)
    assert _canon(lines_b_after) == _canon(lines_b_before), \
        "estimate B's derived material list changed when A was deleted"


def test_derivation_quantities_come_from_own_measurements(est_factory, s):
    """B's wrap roll count must derive from B's squares — never A's.
    A: 20 SQ → HW ceil(20/9 × 1.1) = 3 · B: 31 SQ → ceil(31/9 × 1.1) = 4."""
    est_factory("siding", MEAS_A)  # exists as bait
    b = est_factory("siding", MEAS_B)
    hw = [l for l in _rederive(s, b)
          if l.get("name") == "House Wrap" and l.get("tab") == "vinyl"][0]
    assert hw["qty"] == 4.0, f"B must derive from ITS 31 SQ: {hw}"


# ═══════════ LP: no run of your own + no pair stamp = NOTHING ══════════
def test_lp_preview_never_borrows_another_estimates_run(est_factory, s):
    """A fresh LP estimate with no runs and no pair stamp must get NO
    package — not a latest-run borrow from any other estimate (other
    estimates in this DB have done runs right now)."""
    b = est_factory("lp_smart", None)
    r = s.post(f"{API}/estimates/{b}/lp-package/preview", json={})
    assert r.status_code != 200, \
        f"fresh LP estimate composed a package from someone else's run: {r.text[:200]}"


def test_paired_read_is_severed():
    """REVOKED EXCEPTION (Howard ruled 2026-08-03): _load_run reads ONLY
    the requesting estimate's own runs — no paired-sibling fallback, no
    paired-latest binding, no cross-estimate run borrow of any kind."""
    src = Path("/app/backend/routes/lp_package_routes.py").read_text()
    assert 'paired_id = est.get(' not in src, \
        "the paired-sibling run fallback grew back into _load_run"
    assert '"paired-latest"' not in src, \
        "paired-latest binding label must stay retired"
    # and every run query in the loader is estimate-scoped
    assert '{"estimate_id": est_id, "status": "done"}' in src, \
        "run lookups must be scoped to the requesting estimate's id"


# ═══════════ HYGIENE — a test estimate can never dodge the purge ═══════
def test_test_named_estimate_is_tagged_at_creation(est_factory, s):
    """TEST-DATA HYGIENE (ruled 2026-07-31): TEST_-named estimates tag
    test_artifact at creation, same class as companies — the purge tool
    reaches them even if a suite crashes before its teardown."""
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    eid = est_factory("siding", None)

    async def check():
        dbx = AsyncIOMotorClient(_ENV["MONGO_URL"])[_ENV["DB_NAME"]]
        return await dbx.estimates.find_one({"id": eid}, {"test_artifact": 1})
    doc = asyncio.new_event_loop().run_until_complete(check())
    assert doc and doc.get("test_artifact") is True, \
        f"TEST_-named estimate must carry test_artifact at creation: {doc}"
