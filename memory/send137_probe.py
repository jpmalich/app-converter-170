"""SEND-137 gable probe — READ ONLY. Names every live gable figure that
was computed with the retired 0.70 field factor, what 1/2 x w x rise
would have been, and what it becomes under the ruling. Writes nothing."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

rows = []
for est in db.estimates.find({}, {"estimate_number": 1, "customer_name": 1,
                                  "hover_measurements": 1, "updated_at": 1}):
    m = est.get("hover_measurements") or {}
    if not isinstance(m, dict):
        continue
    walk = m.get("_wall_walk_detail") or []
    gables = [d for d in walk if isinstance(d, dict)
              and (d.get("gable_sqft") or 0) > 0]
    refusals = [d for d in walk if isinstance(d, dict)
                and d.get("gable_refusal")]
    if not gables and not refusals and not m.get("_ai_gable_sqft"):
        continue
    rows.append({
        "est": est.get("estimate_number"),
        "src": m.get("_source"),
        "siding_sqft": m.get("siding_sqft"),
        "ai_gable_sqft": m.get("_ai_gable_sqft"),
        "faces": [{"label": d.get("label"),
                   "width": d.get("width_ft"),
                   "rise_used": d.get("rise_used"),
                   "gable_sqft": d.get("gable_sqft"),
                   "basis": d.get("gable_basis")} for d in gables],
        "refused": [{"label": d.get("label"),
                     "reason": d.get("gable_refusal")} for d in refusals],
    })

print(f"ESTIMATES CARRYING A GABLE FIGURE OR REFUSAL: {len(rows)}\n")
tot_now = tot_half = 0.0
for r in rows:
    print(f"--- {r['est']}  source={r['src']}  siding_sqft={r['siding_sqft']}"
          f"  _ai_gable_sqft={r['ai_gable_sqft']}")
    for f in r["faces"]:
        g = float(f["gable_sqft"])
        w, rise = f["width"], f["rise_used"]
        half = (0.5 * float(w) * float(rise)) if (w and rise) else None
        implied = g / 0.70
        print(f"    {str(f['label']):<7} w={w} rise={rise} "
              f"gable_sqft={round(g,2)} basis={f['basis']} "
              f"| /0.70={round(implied,2)} | HALF={None if half is None else round(half,2)} "
              f"| delta={None if half is None else round(half-g,2)}")
        tot_now += g
        if half is not None:
            tot_half += half
    for f in r["refused"]:
        print(f"    {str(f['label']):<7} REFUSED: {f['reason']}")
print(f"\nTOTAL gable ft2 carried at 0.70: {round(tot_now,2)}")
print(f"TOTAL gable ft2 at 1/2 x w x rise: {round(tot_half,2)}")
print(f"DELTA: {round(tot_half-tot_now,2)}")
