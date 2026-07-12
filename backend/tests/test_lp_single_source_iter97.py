"""Iter 97 — SINGLE-SOURCE CUT pins (Howard, authorized 2026-07-12).
LP lines price EXCLUSIVELY from the cost×margin engine at the corrected
ladder (whole-sale 35 / Contractor 30 default / Builder-Dealer 25 /
one-opp 20). Legacy LP list entries archived, not deleted. Composition
pin: the derived takeoff never composes cross-domain lines; the 5
coil/flash-tape rows are explicit MANUAL-add exceptions."""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_costs import (  # noqa: E402
    CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS, DEFAULT_TIER, LP_SECTION_TITLES,
    MARGIN_TIER_SEED, cost_for, lp_engine_mat, sell_price,
)
from lp_package import assemble_lp_package  # noqa: E402

MEAS = {
    "siding_with_openings_sqft": 3000, "siding_sqft": 3000,
    "window_count": 14, "entry_door_count": 1, "patio_door_count": 1,
    "outside_corner_lf": 80, "inside_corner_lf": 24, "starter_lf": 180,
    "eaves_lf": 200, "rakes_lf": 100,
}


# ── exception scope pinned by name (ruled: manual adds only) ──
def test_cross_domain_exception_list_is_exactly_five():
    assert CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS == {
        ".019 Coil", "Trim Coil Aluminum 24\" x 50'", "PVC Trim Coil",
        "Performance G8 Trim Coil", "Flash tape 3 3/4\" x 90'",
    }
    for name in CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS:
        assert cost_for(name, "mill") is None  # truly no BlueLinx cost


def test_lp_section_titles():
    assert LP_SECTION_TITLES == {"LP Smart Siding", "LP SmartSide Trim",
                                 "LP Siding Accessories", "LP SmartSide Soffit"}


# ── engine catalog price contract: never a silent 0 / legacy value ──
def test_lp_engine_mat_mill_basis():
    assert lp_engine_mat("38 Series Lap 3/8\" x 8\" x 16'", 30.0) == 30.99
    assert lp_engine_mat("38 Series Lap 3/8\" x 8\" x 16'", 35.0) == 33.37


def test_lp_engine_mat_none_when_no_cost():
    assert lp_engine_mat(".019 Coil", 30.0) is None
    assert lp_engine_mat("Invented Product", 30.0) is None


# ── COMPOSITION PIN: derived takeoff never composes cross-domain lines ──
def test_hover_derived_lp_lines_contain_no_cross_domain_items():
    """.019 Coil auto-add RETIRED from the LP tab (an auto-add is derived
    composition — ruled). The row stays in the catalog for manual adds."""
    from routes.hover import _build_lines
    lp_lines = [l for l in _build_lines(dict(MEAS))
                if l.get("tab") == "lp_smart" and l.get("section") in LP_SECTION_TITLES]
    names = {l["name"] for l in lp_lines}
    assert not (names & CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS), names


def test_lp_package_derivation_contains_no_cross_domain_items():
    pkg = assemble_lp_package(dict(MEAS))
    names = {l["name"] for l in pkg["lines"]}
    assert not (names & CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS), names


def _fetch_archive():
    """Fresh Motor client per call — the shared `db` client binds to the
    first asyncio.run loop and breaks on the second."""
    import os
    from motor.motor_asyncio import AsyncIOMotorClient

    async def go():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        try:
            coll = client[os.environ["DB_NAME"]].lp_legacy_price_archive
            return [r async for r in coll.find({}, {"_id": 0})]
        finally:
            client.close()
    return asyncio.run(go())


# ── PENNY-PARITY PIN (ruled): the engine reproduces the ARCHIVED legacy
# prices to the penny at mill basis — finding (c) says it must ──
def test_engine_reproduces_archived_legacy_prices_to_the_penny():
    rows = _fetch_archive()
    assert len(rows) == 31, "archive must hold all 31 LP rows × 4 tiers"
    checked = 0
    for r in rows:
        if r.get("cross_domain_manual_add"):
            continue  # vinyl-domain mirrors — no BlueLinx cost, exempt
        mill = cost_for(r["name"], "mill")
        assert mill is not None, r["name"]
        for tier_name, legacy in (r.get("legacy_prices") or {}).items():
            m = MARGIN_TIER_SEED[tier_name]  # identity mapping (ruled)
            assert sell_price(mill, m) == round(float(legacy), 2), \
                f"{r['name']} @ {tier_name}: engine {sell_price(mill, m)} != legacy {legacy}"
            checked += 1
    assert checked == 26 * 4


def test_archive_carries_provenance():
    r = next(x for x in _fetch_archive()
             if x["name"] == "38 Series Lap 3/8\" x 8\" x 16'")
    assert r and r["archived_at"] and "retired per single-source ruling" in r["reason"]
    assert "MILL cost ÷ (1 − m)" in r["derivation_hypothesis"]
    assert r["legacy_prices"] == {"whole-sale": 33.37, "Contractor": 30.99,
                                  "Builder-Dealer": 28.92, "one-opp": 27.11}


# ── identity mapping pin: no company changes margin level ──
def test_company_tier_identity_mapping():
    assert set(MARGIN_TIER_SEED) == {"whole-sale", "Contractor", "Builder-Dealer", "one-opp"}
    assert MARGIN_TIER_SEED["whole-sale"] == 35.0
    assert DEFAULT_TIER == "Contractor"
