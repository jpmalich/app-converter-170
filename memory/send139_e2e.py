"""SEND-139 live e2e — draws a gable and a dormer through the REAL API on
a scratch estimate, confirms them, applies, then deletes the scratch.
Writes nothing to any existing estimate."""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from pymongo import MongoClient  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com",
                                      "password": os.environ["ADMIN_PASSWORD"]},
           timeout=60)
print("login", r.status_code)

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
est = s.post(f"{API}/estimates", json={"customer_name": "SEND139 SCRATCH",
                                       "lines": []}, timeout=60).json()
eid = est["id"]
print("scratch estimate", eid, est.get("estimate_number"))
PK = "send139-scratch.jpg"
try:
    # scale: 100 px span = 100 ft → 12 in per px, so pixels read as feet
    print("scale", s.put(f"{API}/estimates/{eid}/photo-takeoff/scale", json={
        "photo_key": PK, "anchor": {"p1": {"x": 0, "y": 0},
                                    "p2": {"x": 100, "y": 0},
                                    "inches": 1200}}, timeout=60).status_code)
    g = s.post(f"{API}/estimates/{eid}/photo-takeoff/marks", json={
        "photo_key": PK, "kind": "gable", "shape": "poly",
        "points": [{"x": 0, "y": 8}, {"x": 15, "y": 0}, {"x": 30, "y": 8}],
        "label": "front gable"}, timeout=60)
    print("gable", g.status_code, g.json().get("mark", {}).get("id"))
    gid = g.json()["mark"]["id"]
    d = s.post(f"{API}/estimates/{eid}/photo-takeoff/marks", json={
        "photo_key": PK, "kind": "dormer", "shape": "poly",
        "points": [{"x": 0, "y": 10}, {"x": 6, "y": 10},
                   {"x": 6, "y": 0}, {"x": 0, "y": 0}],
        "label": "left dormer"}, timeout=60)
    did = d.json()["mark"]["id"]
    print("dormer", d.status_code, did)
    bad = s.post(f"{API}/estimates/{eid}/photo-takeoff/marks", json={
        "photo_key": PK, "kind": "gable", "shape": "poly",
        "points": [{"x": 0, "y": 8}, {"x": 15, "y": 0}]}, timeout=60)
    print("2-point gable refused:", bad.status_code, bad.json().get("detail"))

    def rail():
        data = s.get(f"{API}/estimates/{eid}/photo-takeoff",
                     params={"photo_key": PK}, timeout=60).json()
        return data["per_photo"][PK]["quantities"]

    q = rail()
    print("\nBEFORE CONFIRM  gable:", q["gable_sqft"], " dormer face:",
          q["dormer_face_sqft"], " note:", (q["provisional_note"] or "")[:60])
    for mid in (gid, did):
        rr = s.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{mid}",
                     json={"status": "confirmed"}, timeout=60)
        print("confirm", mid[:8], rr.status_code)
    q = rail()
    print("\nAFTER CONFIRM")
    print("  gable_sqft      :", q["gable_sqft"], "(expect 120.0 = 1/2 x 30 x 8)")
    print("  gable rows      :", q["gable_rows"])
    print("  dormer_face_sqft:", q["dormer_face_sqft"], "(expect 60.0)")
    print("  dormer_cheeks   :", q["dormer_cheek_sqft"])
    print("  dormer refusals :", q["dormer_refusals"])
    print("  basis           :", q["gable_basis_note"])
    print("  plane           :", q["plane_basis"])
    s.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{did}",
            json={"depth_ft": 2.0}, timeout=60)
    q = rail()
    print("\nDEPTH TYPED (2.0) — dormer went back to:",
          [m["status"] for m in s.get(f"{API}/estimates/{eid}/photo-takeoff",
                                      params={"photo_key": PK},
                                      timeout=60).json()["marks"]
           if m["id"] == did])
    s.patch(f"{API}/estimates/{eid}/photo-takeoff/marks/{did}",
            json={"status": "confirmed"}, timeout=60)
    q = rail()
    print("  cheeks now      :", q["dormer_cheek_sqft"], "(expect 40.0)")
    ap = s.post(f"{API}/estimates/{eid}/photo-takeoff/apply", timeout=60).json()
    b = ap["photo_takeoff"]
    print("\nAPPLY  gable:", b["photo_gable_sqft"], " dormer face:",
          b["photo_dormer_face_sqft"], " cheeks:", b["photo_dormer_cheek_sqft"])
    print("  basis:", b["photo_gable_basis"][:80])
    doc = db.estimates.find_one({"id": eid}, {"photo_gable_sqft": 1,
                                              "total_sell": 1, "lines": 1})
    print("  stored photo_gable_sqft:", doc.get("photo_gable_sqft"),
          "· lines:", len(doc.get("lines") or []),
          "· total_sell:", doc.get("total_sell"))
finally:
    db.photo_takeoff_marks.delete_many({"estimate_id": eid})
    db.photo_takeoff_scale.delete_many({"estimate_id": eid})
    db.estimates.delete_one({"id": eid})
    print("\nscratch estimate deleted:",
          db.estimates.find_one({"id": eid}) is None)
