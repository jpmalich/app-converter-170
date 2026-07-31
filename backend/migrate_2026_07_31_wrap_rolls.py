"""WRAP ROLL CONVERSION (Howard ruled 2026-07-31) — one-off, receipted.

House Wrap SQ → ROLL (9.00 SQ/roll, $119.11/roll) · RainDrop SQ → ROLL
(11.25 SQ/roll, $336.13/roll). Howard's admin entry landed TRANSPOSED
(HW $336.13 / RD $119.11) — his sanity check caught it; he ruled
CROSS-CORRECT AND GO. Unit and price land together, atomically per doc.

STOP RULE (Howard): any line that moves CHEAPER is HELD + flagged, never
converted silently. Human-typed quantities never rewritten. Pre-heal
backups at /app/memory/backups/20260731_120500_*_wrap_roll_conversion.json.
"""
import asyncio
import math
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from price_age import stamp_price_change  # noqa: E402

RULED = "ruled 2026-07-31"
PLAN = {
    "House Wrap": {"divisor": 9.00, "roll_price": 119.11, "old_sq_price": 11.55,
                   "swapped_as": 336.13},
    "RainDrop": {"divisor": 11.25, "roll_price": 336.13, "old_sq_price": 30.73,
                 "swapped_as": 119.11},
}


async def main():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    flags = []

    # 1. price_tiers — cross-correct the transposed entry + flip unit, one
    #    replace_one per doc so unit and dollar land together.
    async for tier in db.price_tiers.find({}):
        changed = False
        for sec in tier.get("sections", []) or []:
            for it in sec.get("items", []) or []:
                p = PLAN.get(it.get("name"))
                if not p:
                    continue
                mat = round(float(it.get("mat") or 0), 2)
                if mat not in (p["swapped_as"], p["old_sq_price"], p["roll_price"]):
                    flags.append(f"tier {tier.get('name')}: {it['name']} mat {mat} "
                                 "unexpected — row left alone, needs a human")
                    continue
                if it.get("unit") != "ROLL" or mat != p["roll_price"]:
                    it["unit"] = "ROLL"
                    it["mat"] = p["roll_price"]
                    stamp_price_change(it, "swap cross-correct — Howard price pages (ruled 2026-07-31)")
                    changed = True
        if changed:
            await db.price_tiers.replace_one({"id": tier["id"]}, tier)
            print(f"tier '{tier.get('name')}': HW → ROLL $119.11 · RD → ROLL $336.13 (one write)")

    # 2. estimate lines — one named qty+dollar delta per line.
    async for e in db.estimates.find({"lines.name": {"$in": list(PLAN)}}):
        dirty = False
        for l in e.get("lines", []) or []:
            p = PLAN.get(l.get("name"))
            if not p or l.get("unit") != "SQ" or (l.get("qty") or 0) <= 0:
                continue
            tag = f"est {e['id'][:8]} '{(e.get('customer_name') or '').strip()}': {l['name']}"
            if (l.get("qty_src") or "") == "human":
                flags.append(f"{tag} qty {l.get('qty')} SQ is HUMAN-typed — left verbatim")
                continue
            if round(float(l.get("mat") or 0), 2) != p["old_sq_price"]:
                flags.append(f"{tag} mat {l.get('mat')} differs from the old seed "
                             f"{p['old_sq_price']} — NOT converted over an unknown number")
                continue
            sq = float(l["qty"])
            rolls = math.ceil(sq / p["divisor"] - 1e-9)
            old_ext = round(sq * p["old_sq_price"], 2)
            new_ext = round(rolls * p["roll_price"], 2)
            if new_ext < old_ext - 0.005:
                flags.append(f"{tag} MOVES CHEAPER ({sq:g} SQ ${old_ext:.2f} → {rolls} ROLL "
                             f"${new_ext:.2f}, {new_ext - old_ext:+.2f}) — HELD per Howard's stop rule")
                continue
            l["qty"] = float(rolls)
            l["unit"] = "ROLL"
            l["mat"] = p["roll_price"]
            l["raw_qty"] = None
            l["note"] = ((l.get("note") or "") +
                         f" · converted {sq:g} SQ → {rolls} ROLL @ {p['divisor']:g} SQ/roll "
                         f"— ${old_ext:.2f} → ${new_ext:.2f} ({RULED})").strip(" ·")
            dirty = True
            print(f"est {e['id'][:8]} {(e.get('customer_name') or '')[:20]:20s} | {l['name']:10s} | "
                  f"{sq:5g} SQ ${old_ext:>8.2f} → {rolls} ROLL ${new_ext:>9.2f} ({new_ext - old_ext:+.2f})")
        if dirty:
            await db.estimates.update_one({"id": e["id"]}, {"$set": {"lines": e["lines"]}})

    print("\nFLAGS:" if flags else "\nNO FLAGS")
    for f in flags:
        print(" ", f)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
