"""SEND-137 probe 2 — READ ONLY. For every estimate carrying a gable
figure with no walk detail, recover the walls from the source run and
name which convention the stored figure was computed at."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
cols = db.list_collection_names()
print("run collections:", [c for c in cols if "run" in c or "measure" in c])

for est in db.estimates.find({}, {"estimate_number": 1, "hover_measurements": 1}):
    m = est.get("hover_measurements") or {}
    if not isinstance(m, dict):
        continue
    g = m.get("_ai_gable_sqft")
    if not g:
        continue
    rid = m.get("_run_id")
    walls = None
    for cname in ("ai_measure_runs", "ai_blueprint_runs", "blueprint_runs"):
        if cname not in cols:
            continue
        run = db[cname].find_one({"run_id": rid}) if rid else None
        if run:
            walls = (((run.get("result") or {}).get("raw_ai") or (run.get("result") or {}).get("raw") or {}) or {}).get("walls")
            if walls:
                print(f"\n{est.get('estimate_number')}  run={cname}:{rid} "
                      f"carried_gable={g} siding={m.get('siding_sqft')}")
                s = 0.0
                for w in walls:
                    rise = float(w.get("gable_triangle_height_ft") or 0)
                    wd = float(w.get("width_ft") or 0)
                    if rise > 0 and wd > 0:
                        s += wd * rise
                        print(f"    {w.get('label')}: w={wd} rise={rise} "
                              f"| half={round(0.5*wd*rise,2)} "
                              f"| f070={round(0.70*wd*rise,2)}")
                if s:
                    print(f"    SUM w*rise={round(s,2)}  implied factor from "
                          f"carried figure = {round(float(g)/s,4)}")
            break
    if walls is None:
        print(f"\n{est.get('estimate_number')}  carried_gable={g} "
              f"run={rid} — NO RUN WALLS RECOVERABLE")
