"""SEND-79 Item 1 REPORT — the three overlay-bound estimates through a
rederive, BEFORE and AFTER, markers shown. Runs on CLONES so no live
estimate is written (EST-886440 is PROTECTED and stays that way).
Clones are deleted afterwards."""
import os, sys, uuid, json
sys.path.insert(0, "/app/backend")
import requests
from dotenv import dotenv_values
from pymongo import MongoClient
from creds_for_tests import TEST_PASSWORD

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
API = _FE["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(_ENV["MONGO_URL"])[_ENV["DB_NAME"]]

s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com",
                                      "password": TEST_PASSWORD})
assert r.status_code == 200, r.text

MARKERS = ("overlay_superseded", "superseded_qty", "overlay_sqft",
           "overlay_polygon_count")


def bound_lines(lines):
    return [l for l in lines if l.get("overlay_superseded")
            or (l.get("qty_src") == "human"
                and l.get("unit") == "SQ")]


def show(tag, lines):
    for l in bound_lines(lines):
        print(f"    [{tag}] {l.get('tab')}/{l.get('name')}: "
              f"qty={l.get('qty')} qty_src={l.get('qty_src')} "
              f"superseded_qty={l.get('superseded_qty')} "
              f"overlay_superseded={l.get('overlay_superseded')} "
              f"overlay_sqft={l.get('overlay_sqft')} "
              f"zones={l.get('overlay_polygon_count')}")


for est in db.estimates.find(
        {"lines": {"$elemMatch": {"overlay_superseded": True}}},
        {"_id": 0}):
    num = est.get("estimate_number")
    print(f"\n=== {num} ({est.get('customer_name')}) ===")
    print("  BEFORE (stored, untouched):")
    show("before", est.get("lines") or [])
    if not est.get("hover_measurements"):
        print("  no stored measurements — the rederive door refuses "
              "(409) by design; markers cannot be stripped by a door "
              "that cannot open. NOT CLONED.")
        continue
    cid = str(uuid.uuid4())
    clone = dict(est)
    clone["id"] = cid
    clone["customer_name"] = f"SEND79-CLONE-{num}"
    clone.pop("protected", None)
    db.estimates.insert_one(clone)
    npoly = 0
    for p in db.pdf_overlay_polygons.find({"estimate_id": est["id"]},
                                          {"_id": 0}):
        p = dict(p)
        p["estimate_id"] = cid
        p["id"] = f"send79c-{uuid.uuid4().hex[:8]}"
        db.pdf_overlay_polygons.insert_one(p)
        npoly += 1
    try:
        r = s.post(f"{API}/estimates/{cid}/rederive",
                   json={"trigger": "send79-item1-report"})
        if r.status_code != 200:
            print(f"  rederive refused: {r.status_code} {r.text[:200]}")
            continue
        print(f"  AFTER a REAL rederive on the clone ({npoly} zones "
              "copied):")
        show("after", r.json()["lines"])
        after = {(l.get("tab"), l.get("name")): l
                 for l in r.json()["lines"]}
        ok = True
        for l in bound_lines(est.get("lines") or []):
            a = after.get((l.get("tab"), l.get("name")))
            if a is None:
                print(f"    !! line {l.get('name')} missing after")
                ok = False
                continue
            for k in MARKERS:
                if l.get(k) != a.get(k):
                    print(f"    Δ {l.get('name')}.{k}: "
                          f"{l.get(k)} → {a.get(k)}")
            if not a.get("overlay_superseded"):
                ok = False
        print("  MARKERS INTACT THROUGH THE REBUILD:" ,
              "YES" if ok else "NO — DEFECT")
    finally:
        db.pdf_overlay_polygons.delete_many({"estimate_id": cid})
        db.estimates.delete_many({"id": cid})
print("\nclones removed; live estimates untouched.")
