"""SEND-126 dart scoring dump — READ-ONLY. No estimate written, no run
rewritten. Prints what the fresh read (ff0d596e) returned against the
sealed truth."""
import json
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
RID = "ff0d596e4b604d5eb8001c7fd66c589f"
run = db.ai_blueprint_runs.find_one({"run_id": RID})
res = run.get("result") or {}
m = res.get("measurements") or {}
raw = res.get("raw_ai") or {}

print("== top-level measurement keys ==")
print(sorted(k for k in m if not k.startswith("_ocr")))

print("\n== faces / walls ==")
for key in ("faces", "walls", "wall_faces", "elevations"):
    if m.get(key):
        print(key, json.dumps(m[key], default=str)[:4000])
if raw.get("walls"):
    print("raw walls:", json.dumps(raw["walls"], default=str)[:6000])

print("\n== scalars ==")
for k in ("siding_sqft", "starter_lf", "soffit_sqft", "level_frieze_lf",
          "sloped_frieze_lf", "drip_edge_lf", "total_trim_sqft",
          "window_count", "door_count", "gable_count",
          "siding_pct_this_wall"):
    print(f"  {k}: {m.get(k)!r} (raw {raw.get(k)!r})")

print("\n== refusal / ledger keys present ==")
for k in sorted(m):
    if any(t in k for t in ("refus", "null", "gate", "unread", "not_der",
                            "seam", "claim", "rail", "ledger", "flag")):
        print(f"  {k}: {json.dumps(m[k], default=str)[:1500]}")
