"""SEND-129 re-check — READ-ONLY. After the overwrite sweep and with the
corroboration lift live, replay all four houses: what each lane reads, what
the second read says per face, and whether anything moved. No write."""
import copy
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

import attribution_lift
import linework_corroboration
from config import UPLOAD_DIR
from foreign_drafter_scoreboard import earned_claim, unattributed_lanes
from routes.ai_blueprint import _aggregate_to_hover_shape

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
RUNS = {"boni": "5df22e6d", "letrick": "725f8326",
        "tanis": "072e8c36", "dart": "ff0d596e"}
LANES = ("siding_sqft", "starter_lf", "footprint_perimeter_ft", "eaves_lf",
         "rakes_lf", "outside_corner_lf", "inside_corner_lf")


def _ocr(run):
    raw = ((run.get("result") or {}).get("raw_ai") or {})
    ot = raw.get("_ocr_text_by_page")
    if not ot and raw.get("_ocr_text_ref"):
        ot = (db.ai_blueprint_ocr.find_one({"run_id": raw["_ocr_text_ref"]},
                                           {"pages": 1}) or {}).get("pages")
    return ot if isinstance(ot, dict) else None


def _pdf(run):
    for f in (run.get("source_files") or []):
        if isinstance(f, dict) and f.get("kind") == "pdf":
            p = os.path.join(str(UPLOAD_DIR), str(f.get("name")))
            if os.path.exists(p):
                return p
    return None


for house, pref in RUNS.items():
    run = db.ai_blueprint_runs.find_one({"run_id": {"$regex": "^" + pref}})
    raw = copy.deepcopy((run.get("result") or {}).get("raw_ai") or {})
    ot = _ocr(run)
    if ot:
        raw["_ocr_text_by_page"] = ot
    pdf = _pdf(run)
    print("=" * 72)
    print(f"{house.upper()} · run {run['run_id'][:8]}")
    if ot and pdf:
        amb = {str(r.get("quote"))
               for r in (raw.get("_dim_shared_source") or [])
               if isinstance(r, dict)}
        corr = linework_corroboration.read_face_widths(ot, pdf, amb)
        if corr:
            raw["_linework_corroboration"] = corr
        widths = {str(w.get("label")): w.get("width_ft")
                  for w in (raw.get("walls") or []) if isinstance(w, dict)}
        for face, read in sorted(corr.items()):
            v = attribution_lift.evaluate(widths.get(face), read)
            print(f"  {face:<6} printed={widths.get(face)} "
                  f"drawn={read.get('wall_only_ft')} "
                  f"Δ={v['delta_ft']} ({v['delta_pct']}%) "
                  f"lifted={v['lifted']} :: {str(v['statement'])[:88]}")
    else:
        print("  no OCR store or no retained PDF — no second read")
    m = _aggregate_to_hover_shape(raw)
    print("  LANES: " + " | ".join(f"{k}={m.get(k)}" for k in LANES))
    if raw.get("_dim_unattributed"):
        print("  still unattributed: "
              + ", ".join(sorted({d["path"] for d in raw["_dim_unattributed"]})))

print("=" * 72)
print("earned_claim():", earned_claim(), "| leaking lanes:",
      unattributed_lanes())
