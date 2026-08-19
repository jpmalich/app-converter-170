"""SEND-50 item 1 measurement rig: disposable estimate + cloned Letrick run.
Usage: python send50_item1_rig.py create|cleanup [eid]
"""
import sys
import uuid
import os
import requests
from dotenv import load_dotenv, dotenv_values
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
env = dotenv_values("/app/backend/.env")
API = "https://app-converter-170.preview.emergentagent.com/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com",
                                      "password": env["ADMIN_PASSWORD"]}, timeout=15)
assert r.status_code == 200, r.text

if sys.argv[1] == "create":
    src = db.ai_blueprint_runs.find_one(
        {"estimate_id": "264b6230-5d0f-49ea-b07d-8d33a537f293", "status": "done"},
        sort=[("created_at", -1)])
    assert src, "no source run"
    r = s.post(f"{API}/estimates",
               json={"kind": "lp_smart", "customer_name": "ZZ TEST_send50-item1 TEMP"},
               timeout=15)
    assert r.status_code == 200, r.text
    est = r.json()
    eid = est["id"]
    est["lines"] = [{"tab": "vinyl", "section": "Siding", "unit": "SQ",
                     "qty": 44.0, "raw_qty": 44.0, "qty_src": "derived",
                     "name": "D4 Clapboard"}]
    rr = s.put(f"{API}/estimates/{eid}", json=est, timeout=15)
    assert rr.status_code == 200, rr.text
    db.estimates.update_one({"id": eid}, {"$set": {"kind": "siding"}})
    clone = dict(src)
    clone.pop("_id", None)
    clone["test_artifact"] = True
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send50-{uuid.uuid4().hex[:8]}"
    db.ai_blueprint_runs.insert_one(clone)
    print(eid, clone["run_id"])
elif sys.argv[1] == "cleanup":
    eid = sys.argv[2]
    db.ai_blueprint_runs.delete_many({"estimate_id": eid, "test_artifact": True})
    db.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    db.estimates.delete_many({"id": eid})
    print("cleaned", eid)
