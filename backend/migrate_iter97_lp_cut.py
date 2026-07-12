"""Iter 97 — THE CUT (Howard, authorized 2026-07-12). One-shot, idempotent.
1. Archive all LP rows × 4 tiers → db.lp_legacy_price_archive with
   provenance (hand-set values, derivation hypothesis, retired-at, reason).
2. Retire legacy LP mat values in price_tiers (zeroed; resolution now
   serves engine prices) — the 5 cross-domain manual-add exceptions keep
   their vinyl-domain prices.
3. Migrate P0-era estimate tier letters → corrected ladder names.
4. Supersede the A/B/C margin settings doc with the corrected ladder."""
import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from db import db  # noqa: E402
from lp_costs import (  # noqa: E402
    CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS, DEFAULT_TIER, LP_SECTION_TITLES,
    MARGIN_TIER_SEED,
)

DERIVATION_HYPOTHESIS = (
    "trace finding (c), 2026-07-12: legacy LP tier price = BlueLinx PIT00003 "
    "MILL cost ÷ (1 − m), m = {whole-sale: 35%, Contractor: 30%, "
    "Builder-Dealer: 25%, one-opp: 20%} — verified to the penny for all 26 "
    "BlueLinx-backed items; the 5 coil/flash-tape rows are vinyl-domain mirrors."
)
LETTER_MAP = {"A": "Contractor", "B": "Builder-Dealer", "C": "one-opp"}


async def main():
    now = datetime.now(timezone.utc).isoformat()

    # 1) ARCHIVE with provenance
    rows: dict = {}
    async for t in db.price_tiers.find({}, {"_id": 0}):
        for sec in t.get("sections") or []:
            if sec.get("title") not in LP_SECTION_TITLES:
                continue
            for it in sec.get("items") or []:
                key = (sec["title"], it["name"])
                r = rows.setdefault(key, {
                    "id": f"{sec['title']}::{it['name']}",
                    "section": sec["title"], "name": it["name"],
                    "unit": it.get("unit"), "lab": it.get("lab"),
                    "legacy_prices": {},
                    "cross_domain_manual_add": it["name"] in CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS,
                })
                r["legacy_prices"][t["name"]] = float(it.get("mat") or 0)
    archived = 0
    for r in rows.values():
        r.update({
            "archived_at": now,
            "reason": ("retired per single-source ruling 2026-07-12 — LP lines price "
                       "exclusively from the cost×margin engine (BlueLinx PIT00003 + "
                       "margin tiers); archived as pricing history, never deleted"),
            "derivation_hypothesis": DERIVATION_HYPOTHESIS,
            "source": "db.price_tiers hand-set values (four-tier lists)",
        })
        res = await db.lp_legacy_price_archive.update_one(
            {"id": r["id"]}, {"$setOnInsert": r}, upsert=True)
        if res.upserted_id:
            archived += 1
    print(f"archived: {archived} new (total LP rows: {len(rows)})")

    # 2) RETIRE engine rows in the active lists (zero mat; exceptions kept)
    retired = 0
    async for t in db.price_tiers.find({}):
        changed = False
        for sec in t.get("sections") or []:
            if sec.get("title") not in LP_SECTION_TITLES:
                continue
            for it in sec.get("items") or []:
                if it["name"] in CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS:
                    continue
                if float(it.get("mat") or 0) != 0.0:
                    it["mat"] = 0.0
                    it["retired_to_engine"] = True
                    changed = True
                    retired += 1
        if changed:
            await db.price_tiers.update_one(
                {"_id": t["_id"]},
                {"$set": {"sections": t["sections"], "updated_at": now}})
    print(f"retired legacy mat values: {retired}")

    # 3) Estimate tier letters → corrected ladder names
    for letter, name in LETTER_MAP.items():
        res = await db.estimates.update_many(
            {"lp_pricing_tier": letter}, {"$set": {"lp_pricing_tier": name}})
        if res.modified_count:
            print(f"estimate tier {letter} → {name}: {res.modified_count}")

    # 4) Supersede the A/B/C settings doc
    await db.settings.update_one(
        {"id": "lp_margin_tiers"},
        {"$set": {"tiers": dict(MARGIN_TIER_SEED), "default_tier": DEFAULT_TIER}},
        upsert=True)
    print("margin ladder:", MARGIN_TIER_SEED, "default:", DEFAULT_TIER)


if __name__ == "__main__":
    asyncio.run(main())
