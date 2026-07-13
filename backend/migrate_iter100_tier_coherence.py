"""Iter 100 — TIER COHERENCE migration (ruled): one estimate, one tier,
one truth. Backfills lp_pricing_tier on LP-kind estimates (seeded from
company tier, identity-mapped) and reprices stored engine-priced LP
lines to each estimate's tier. Idempotent."""
import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from db import db  # noqa: E402
from lp_costs import DEFAULT_TIER, MARGIN_TIER_SEED  # noqa: E402


async def main():
    from routes.lp_admin import load_margin_cfg, reprice_lp_engine_lines

    cfg = await load_margin_cfg()
    tier_names = {}
    async for t in db.price_tiers.find({}, {"id": 1, "name": 1}):
        tier_names[t["id"]] = t["name"]
    now = datetime.now(timezone.utc).isoformat()
    backfilled = repriced_total = 0
    async for e in db.estimates.find({"kind": "lp_smart"},
                                     {"lines": 1, "lp_pricing_tier": 1, "company_id": 1,
                                      "estimate_number": 1}):
        tier = e.get("lp_pricing_tier")
        if not tier:
            company = await db.companies.find_one({"id": e["company_id"]}, {"price_tier_id": 1})
            name = tier_names.get((company or {}).get("price_tier_id"))
            tier = name if name in MARGIN_TIER_SEED else DEFAULT_TIER
            backfilled += 1
        lines, repriced = reprice_lp_engine_lines(
            e.get("lines") or [], float(cfg["tiers"][tier]))
        repriced_total += repriced
        await db.estimates.update_one(
            {"_id": e["_id"]},
            {"$set": {"lp_pricing_tier": tier, "lines": lines, "updated_at": now}})
        if repriced:
            print(f"{e.get('estimate_number')}: tier={tier}, repriced {repriced} engine lines")
    print(f"backfilled tiers: {backfilled} | repriced engine lines: {repriced_total}")


if __name__ == "__main__":
    asyncio.run(main())
