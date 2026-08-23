"""SEND-115 probe — READ-ONLY. Stored runs, deep copies; no estimate
written. Reports what Ruling 1 makes each house's siding basis become."""
import copy
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

from routes.ai_blueprint import _aggregate_to_hover_shape  # noqa: E402
from routes.hover import _openings_ded_note  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

HOUSES = {}
for r in db.ai_blueprint_runs.find({"status": "done"}).sort("created_at", -1):
    eid = r.get("estimate_id")
    if eid in HOUSES:
        continue
    est = db.estimates.find_one({"id": eid}, {"customer_name": 1})
    HOUSES[eid] = (str((est or {}).get("customer_name") or eid)[:40], r)

for eid, (name, run) in HOUSES.items():
    raw = copy.deepcopy((run.get("result") or {}).get("raw_ai") or {})
    if not raw:
        continue
    if not raw.get("_ocr_text_by_page") and raw.get("_ocr_text_ref"):
        doc = db.ai_blueprint_ocr.find_one({"run_id": raw["_ocr_text_ref"]},
                                           {"pages": 1}) or {}
        raw["_ocr_text_by_page"] = doc.get("pages")
    m = _aggregate_to_hover_shape(raw)
    d = m.get("_openings_deduction")
    print(f"\n=== {name} ({eid[:8]}) ===")
    print(f"  siding_sqft (gross): {m.get('siding_sqft')}")
    print(f"  siding_with_openings_sqft: {m.get('siding_with_openings_sqft')}")
    if d:
        print(f"  deducted: {d['deducted_sqft']} ft² | net: {d['net_sqft']}"
              f" | complete: {d['complete']} | refused: {len(d['refused'])}")
        print(f"  line note:{_openings_ded_note(m)}")
    else:
        print("  no openings read — nothing deducted, field None")
