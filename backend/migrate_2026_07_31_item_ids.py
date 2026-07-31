"""ID BINDING MIGRATION — STAMPS, NEVER DERIVES (Howard ruled 2026-07-31).

Adds `item_id` (catalog_ids.py literals) to price-tier items and estimate
lines. THE WRITER IS SELF-REFUSING: before writing an estimate it builds
the after-image and proves every line identical to before with ONLY
item_id added — any other difference aborts that estimate's write
entirely. Unresolved names are LEFT ALONE and named on the receipt.
Idempotent. Pre-heal backups written before the first write.
"""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from catalog_ids import ITEM_IDS, NAME_INDEX  # noqa: E402


def resolve(section, name):
    return ITEM_IDS.get((section, name)) or NAME_INDEX.get(name)


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

    os.makedirs("/app/memory/backups", exist_ok=True)
    ests = [e async for e in db.estimates.find({})]
    tiers = [t async for t in db.price_tiers.find({})]
    for d in ests + tiers:
        d.pop("_id", None)
    with open("/app/memory/backups/20260731_150000_estimates_pre_item_ids.json", "w") as f:
        json.dump(ests, f, default=str)
    with open("/app/memory/backups/20260731_150000_price_tiers_pre_item_ids.json", "w") as f:
        json.dump(tiers, f, default=str)
    print(f"backups: {len(ests)} estimates, {len(tiers)} tier docs")

    unresolved = []

    for tier in tiers:
        stamped = 0
        for sec in tier.get("sections", []) or []:
            for it in sec.get("items", []) or []:
                if it.get("item_id"):
                    continue
                iid = resolve(sec.get("title"), it.get("name"))
                if iid:
                    it["item_id"] = iid
                    stamped += 1
                else:
                    unresolved.append(f"tier {tier['name']}: [{sec.get('title')}] {it.get('name')}")
        if stamped:
            await db.price_tiers.replace_one({"id": tier["id"]}, tier)
        print(f"tier '{tier['name']}': {stamped} items stamped")

    for e in ests:
        before = [dict(l) for l in (e.get("lines") or [])]
        after = []
        stamped = skipped = 0
        for l in before:
            n = dict(l)
            if not n.get("item_id"):
                iid = resolve(n.get("section"), n.get("name"))
                if iid:
                    n["item_id"] = iid
                    stamped += 1
                else:
                    skipped += 1
                    unresolved.append(f"est {e['id'][:8]} '{(e.get('customer_name') or '')[:20]}': "
                                      f"[{n.get('section')}] {n.get('name')}")
            after.append(n)
        # SELF-REFUSING DIFF: every line identical except the added key.
        ok = True
        for b, a in zip(before, after):
            a2 = {k: v for k, v in a.items() if not (k == "item_id" and "item_id" not in b)}
            if canon(a2) != canon(b):
                ok = False
                print(f"  !! ABORT est {e['id'][:8]}: a non-item_id field would move on "
                      f"[{b.get('section')}] {b.get('name')} — NOTHING written")
                break
        if not ok:
            continue
        if stamped:
            await db.estimates.update_one({"id": e["id"]}, {"$set": {"lines": after}})
        print(f"est {e['id'][:8]} {(e.get('customer_name') or '(unnamed)')[:24]:24s} | "
              f"{stamped:3d} stamped · {skipped} left-alone · bytes-identical-otherwise: YES")

    print("\nUNRESOLVED (left alone, need a human):" if unresolved else "\nALL ROWS RESOLVED")
    for u in unresolved:
        print("  ", u)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
