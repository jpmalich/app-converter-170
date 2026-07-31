"""SALES-UNIT MIGRATION (Howard ruled 2026-07-31) — one-off, receipted.

Converts stored data to the SALES unit for:
  · 2" Nails 30 lbs — JOB → BOX (count was already boxes; relabel, $0 delta)
  · Downspout 6" — LF → 10' Stick (qty ceil(LF/10), $2.80/LF → $28.00/stick)
  · 3/8" Fan Fold — SQ → Bundle (2 SQ/bundle, $11.06/SQ → $22.12/bundle)
  · Pelican Bay Shakes 9" — heals the R3 seed-sync gap: DB tier docs got
    the 1/2 SQ unit but kept the per-SQ price ($419.94 per half square =
    doubled money). Price → $209.97 where untouched by a human.
HOLDS (per ruling): RainDrop + House Wrap convert only after Howard's new
price pages land. Human-typed quantities are never rewritten — flagged in
the receipt instead. ISS price book untouched (its own CSV units).
"""
import asyncio
import math
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

RULED = "ruled 2026-07-31"


def _cv_downspout(l):
    lf = float(l.get("qty") or 0)
    sticks = math.ceil(lf / 10 - 1e-9)
    return sticks, 28.0 if round(float(l.get("mat") or 0), 2) == 2.8 else None, \
        f' · converted {lf:g} LF → {sticks} × 10\' stick ({RULED})'


def _cv_fanfold(l):
    sq = float(l.get("qty") or 0)
    bundles = math.ceil(sq / 2 - 1e-9)
    return bundles, 22.12 if round(float(l.get("mat") or 0), 2) == 11.06 else None, \
        f' · converted {sq:g} SQ → {bundles} bundle(s) at 2 SQ/bundle ({RULED})'


def _cv_pelican(l):
    sq = float(l.get("qty") or 0)
    halves = math.ceil(sq * 2 - 1e-9)
    return halves, 209.97 if round(float(l.get("mat") or 0), 2) == 419.94 else None, \
        f' · converted {sq:g} SQ → {halves} half square(s) (R3 {RULED})'


async def main():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    receipt = {"tier_items": 0, "lines": 0, "human_flags": []}

    # 1. price_tiers docs — units + prices where still at old seed values
    plan = {
        '2" Nails 30 lbs': {"unit": "BOX", "old": None, "new": None},
        'Downspout 6"': {"unit": "Stick", "old": 2.8, "new": 28.0},
        '3/8" Fan Fold': {"unit": "Bundle", "old": 11.06, "new": 22.12},
        'Pelican Bay Shakes 9"': {"unit": "1/2 SQ", "old": 419.94, "new": 209.97},
    }
    async for tier in db.catalogs.database.price_tiers.find({}):
        changed = False
        for sec in tier.get("sections", []) or []:
            for it in sec.get("items", []) or []:
                p = plan.get(it.get("name"))
                if not p:
                    continue
                if it.get("unit") != p["unit"]:
                    it["unit"] = p["unit"]
                    changed = True
                if p["old"] is not None and round(float(it.get("mat") or 0), 2) == p["old"]:
                    it["mat"] = p["new"]
                    changed = True
                elif p["old"] is not None and round(float(it.get("mat") or 0), 2) not in (p["old"], p["new"]):
                    receipt["human_flags"].append(
                        f"tier {tier.get('name')}: {it['name']} mat {it.get('mat')} differs from seed — left alone")
                receipt["tier_items"] += 1
        if changed:
            await db.catalogs.database.price_tiers.replace_one({"id": tier["id"]}, tier)
            print(f"tier '{tier.get('name')}' updated")

    # 2. estimate lines
    conv = {
        'Downspout 6"': ("LF", _cv_downspout),
        '3/8" Fan Fold': ("SQ", _cv_fanfold),
        'Pelican Bay Shakes 9"': ("SQ", _cv_pelican),
    }
    names = list(conv) + ['2" Nails 30 lbs']
    async for e in db.estimates.find({"lines.name": {"$in": names}}):
        dirty = False
        for l in e.get("lines", []) or []:
            nm = l.get("name")
            if nm == '2" Nails 30 lbs' and l.get("unit") == "JOB":
                l["unit"] = "BOX"
                l["note"] = ((l.get("note") or "") +
                             f' · unit relabel JOB→BOX ({RULED}) — count was already boxes, $0 delta').strip(" ·")
                dirty = True
                receipt["lines"] += 1
                continue
            if nm in conv:
                old_unit, fn = conv[nm]
                if l.get("unit") != old_unit or (l.get("qty") or 0) <= 0:
                    continue
                if (l.get("qty_src") or "") == "human":
                    receipt["human_flags"].append(
                        f"est {e['id'][:8]} '{e.get('customer_name','')}': {nm} qty {l.get('qty')} {old_unit} "
                        "is HUMAN-typed — left verbatim, needs manual review")
                    continue
                new_qty, new_mat, note = fn(l)
                old_ext = round((l.get("qty") or 0) * (l.get("mat") or 0), 2)
                l["qty"] = new_qty
                l["unit"] = plan[nm]["unit"] if nm in plan else l["unit"]
                if new_mat is not None:
                    l["mat"] = new_mat
                new_ext = round(new_qty * (l.get("mat") or 0), 2)
                l["note"] = ((l.get("note") or "") + note +
                             f" — ${old_ext:.2f} → ${new_ext:.2f}").strip(" ·")
                l["raw_qty"] = None
                dirty = True
                receipt["lines"] += 1
                print(f"est {e['id'][:8]} {(e.get('customer_name') or '')[:18]:18s} | {nm:18s} | "
                      f"${old_ext:>8.2f} → ${new_ext:>8.2f} ({new_ext-old_ext:+.2f})")
        if dirty:
            await db.estimates.update_one({"id": e["id"]}, {"$set": {"lines": e["lines"]}})

    print("RECEIPT:", receipt["tier_items"], "tier items checked,",
          receipt["lines"], "estimate lines converted")
    for f in receipt["human_flags"]:
        print("FLAG:", f)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
