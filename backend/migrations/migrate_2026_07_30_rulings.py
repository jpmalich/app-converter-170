"""Migration 2026-07-30 (Howard rulings): strip-list renames on live DB,
R4 Inside Corners removal (+ per-estimate total effect), R3 retroactive
whole-unit heal on stored fractional lines (delta NAMED on each line)."""
import asyncio
import math
import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")

PAIRS = [
    ('1/2" J-Channel (2 per Sq of siding) White', '1/2" J-Channel White'),
    ('3/4" J-Channel Standard color (2 per Sq of siding)', '3/4" J-Channel Standard color'),
    ('3/4" J-Channel Architectural color (2 per Sq of siding)', '3/4" J-Channel Architectural color'),
    ('1/2" J-Channel (2 per Sq of siding)', '1/2" J-Channel'),
    ('Ascend - J - Channel  (2 per Sq of siding)', 'Ascend - J - Channel'),
    ('2" Nails 30 lbs (1 per 15 Sq)', '2" Nails 30 lbs'),
    ('Ascend Composite B&B 12" (add 30% Waste)', 'Ascend Composite B&B 12"'),
    (".019 Coil (1 per 50' fascia)", '.019 Coil'),
    ("PVC Trim Coil (1 per 50' fascia)", 'PVC Trim Coil'),
    ("Performance G8 Trim Coil (1 per 50' fascia)", 'Performance G8 Trim Coil'),
    ('PVC Trim Coil (1 per 5 Sq Siding)', 'PVC Trim Coil'),
    ('Performance G8 Trim Coil (1 per 5 Sq Siding)', 'Performance G8 Trim Coil'),
    ('Fascia/rake or frieze up to 8" coverage', 'Fascia/rake or frieze'),
]
REN = dict(PAIRS)

# Area goods keep raw for waste; every stored fractional still heals to
# whole per R3 ("every fractional line, every unit").
def main():
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

    # 1) tier sheets
    n_tier = 0
    for t in db.price_tiers.find({}):
        changed = False
        for sec in t.get("sections") or []:
            for it in sec.get("items") or []:
                if it.get("name") in REN:
                    it["name"] = REN[it["name"]]
                    changed = True
                    n_tier += 1
        if changed:
            db.price_tiers.update_one({"_id": t["_id"]}, {"$set": {"sections": t["sections"]}})
    print(f"tier item renames: {n_tier}")

    # 2) estimates: renames + R4 removal + R3 heal
    for est in db.estimates.find({}, {"customer_name": 1, "lines": 1}):
        lines = est.get("lines") or []
        out, changed, report = [], False, []
        for l in lines:
            nm = l.get("name")
            if nm in REN:
                l["name"] = REN[nm]
                changed = True
            if l.get("name") == "Inside Corners" and l.get("tab") == "ascend":
                changed = True
                report.append(
                    f"R4 removed 'Inside Corners' (ascend) qty={l.get('qty')} "
                    f"mat=${float(l.get('mat') or 0):.2f} → total effect "
                    f"${float(l.get('mat') or 0) * float(l.get('qty') or 0):.2f}")
                continue
            q = l.get("qty")
            if isinstance(q, (int, float)) and q > 0 and float(q) != int(q):
                new_q = float(math.ceil(float(q) - 1e-9))
                l.setdefault("raw_qty", float(q))
                l["qty"] = new_q
                l["note"] = ((l.get("note") or "") +
                             f" — R3 whole units (healed 2026-07-30: was {q:g})").strip(" —")
                changed = True
                mat = float(l.get("mat") or 0)
                report.append(
                    f"R3 heal {l.get('tab')}/{l.get('name')}: {q:g} → {new_q:g}"
                    + (f" (Δ${(new_q - float(q)) * mat:+.2f} mat)" if mat else ""))
            out.append(l)
        if changed:
            db.estimates.update_one({"_id": est["_id"]}, {"$set": {"lines": out}})
            print(f"— {est.get('customer_name') or '(unnamed)'}")
            for r in report:
                print("   ", r)


if __name__ == "__main__":
    main()
