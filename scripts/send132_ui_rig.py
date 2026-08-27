"""SEND-132 UI RIG — a DISPOSABLE estimate that reproduces both stages.

Stage 2 photo: carries a CLONE of a real completed photo read.
Stage 1 photo: a real uploaded photo the cloned read never carried.
Two body-siding product lines so the per-zone picker has real options.
Pre-AI annotations on the Stage 1 photo so the import can be exercised.

Run:  python3 scripts/send132_ui_rig.py            # create + print ids
      python3 scripts/send132_ui_rig.py --clean    # delete every artifact
"""
import os
import sys
import uuid

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")
from api_base import API  # noqa: E402

SRC_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"
TAG = "ZZ TEST_send132 UI RIG"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def clean():
    n = 0
    for e in db.estimates.find({"customer_name": TAG}, {"id": 1}):
        eid = e["id"]
        db.photo_takeoff_marks.delete_many({"estimate_id": eid})
        db.photo_takeoff_scale.delete_many({"estimate_id": eid})
        db.ai_measure_sessions.delete_many({"estimate_id": eid})
        db.ai_measure_runs.delete_many({"estimate_id": eid})
        db.estimates.delete_one({"id": eid})
        n += 1
    print(f"cleaned {n} rig estimate(s)")


def build():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": "hhunt6677@yahoo.com",
                     "password": os.environ["ADMIN_PASSWORD"]}, timeout=20)
    r.raise_for_status()
    src = db.ai_measure_runs.find_one({"estimate_id": SRC_EST, "status": "done"},
                                      sort=[("created_at", -1)])
    names = [n for n in str(src.get("photo_paths") or "").split(",") if n]
    read_photo = names[0]
    from config import UPLOAD_DIR
    unread = None
    for other in db.ai_measure_sessions.find({}):
        for cand in (other.get("photo_urls") or []):
            if cand not in names and (UPLOAD_DIR / cand).exists():
                unread = cand
                break
        if unread:
            break
    est = s.post(f"{API}/estimates",
                 json={"kind": "lp_smart", "customer_name": TAG},
                 timeout=20).json()
    eid = est["id"]
    est["lines"] = [
        {"tab": "lp_smart", "section": "LP Smart Siding",
         "name": 'TEST 38 Series Lap 3/8" x 8" x 16\'', "unit": "PCS", "qty": 100.0},
        {"tab": "lp_smart", "section": "LP Smart Siding",
         "name": "TEST Board & Batten Panel", "unit": "PCS", "qty": 20.0},
        {"tab": "lp_smart", "section": "LP Siding Accessories",
         "name": "TEST J blocks", "unit": "Each", "qty": 4.0},
    ]
    s.put(f"{API}/estimates/{eid}", json=est, timeout=20).raise_for_status()
    photos = [read_photo] + ([unread] if unread else [])
    ann = {}
    if unread:
        ann[unread] = {
            "elevation": "left",
            "zones": [{"id": "z-1", "kind": "rect", "category": "stone",
                       "points": [{"x": 200, "y": 400}, {"x": 700, "y": 400},
                                  {"x": 700, "y": 900}, {"x": 200, "y": 900}]}],
            "windows": [{"id": "w-1", "x": 1100, "y": 600,
                         "style": "2-Lite Slider", "width_in": 48,
                         "height_in": 36}],
        }
    s.put(f"{API}/measure/sessions/{eid}",
          json={"estimate_id": eid, "photo_urls": photos,
                "photo_annotations": ann}, timeout=20).raise_for_status()
    clone = dict(src)
    clone.pop("_id", None)
    clone["estimate_id"] = eid
    clone["run_id"] = f"TEST_send132ui-{uuid.uuid4().hex[:8]}"
    clone["photo_paths"] = read_photo          # ONLY photo 1 carries the read
    clone["test_artifact"] = True
    db.ai_measure_runs.insert_one(clone)
    print("estimate_id :", eid)
    print("stage2_photo:", read_photo)
    print("stage1_photo:", unread)
    print("run_id      :", clone["run_id"])
    print("url         : /estimate/" + eid)


if __name__ == "__main__":
    clean() if "--clean" in sys.argv else build()
