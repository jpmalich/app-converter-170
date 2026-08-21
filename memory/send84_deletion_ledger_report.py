"""SEND-84 report 1 — DELETION LEDGER: EST-713272's nine human zones.
Read-only. Scans every persistent source for traces of the deleted
human-set zones and states, per zone, what is recoverable. Restores
NOTHING."""
import os, json
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

EID = "65bcb89d-8291-4b84-920c-7b503273f332"  # EST-713272 (Boni)
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

print("=== current zones on the estimate ===")
cur = list(db.pdf_overlay_polygons.find({"estimate_id": EID}, {"_id": 0}))
print(f"  pdf_overlay_polygons now: {len(cur)}")
for p in cur:
    print(f"    {p.get('id')[:8]} face={p.get('face_id')} "
          f"prov={p.get('provenance')} class={p.get('material_class')}")

print("\n=== zone_correction_events for the estimate ===")
evs = list(db.zone_correction_events.find({"estimate_id": EID},
                                          {"_id": 0}))
print(f"  events: {len(evs)}")
for e in evs:
    keys = sorted(e.keys())
    print(f"    event={e.get('event')} zone={str(e.get('zone_id'))[:8]} "
          f"face={e.get('face_id')} at={e.get('at') or e.get('created_at')}")
    vp = e.get("vertices_pct") or (e.get("doc") or {}).get("vertices_pct")
    print(f"      carries_vertices={bool(vp)} fields={keys}")

print("\n=== protected_estimate_ledger mentions ===")
led = list(db.protected_estimate_ledger.find(
    {"estimate_id": EID}, {"_id": 0}))
print(f"  entries: {len(led)}")
for l in led[:20]:
    print(f"    {l.get('kind')} {l.get('actor_email')} "
          f"{l.get('at')} meta={json.dumps(l.get('meta') or {})[:160]}")

print("\n=== estimate lines carrying overlay markers ===")
est = db.estimates.find_one({"id": EID})
for ln in est.get("lines") or []:
    marks = {k: ln.get(k) for k in
             ("overlay_sqft", "overlay_superseded", "superseded_qty",
              "qty_src", "overlay_zone_ids")
             if ln.get(k) is not None}
    if marks:
        print(f"    line '{ln.get('name')}' tab={ln.get('tab')} "
              f"qty={ln.get('qty')} marks={marks}")

print("\n=== ai_measure / blueprint runs (zones embedded?) ===")
for coll in ("ai_measure_runs", "ai_blueprint_runs", "fixture_runs",
             "ai_measure_sessions"):
    n = db[coll].count_documents({"estimate_id": EID})
    hits = 0
    for d in db[coll].find({"estimate_id": EID}):
        if "vertices_pct" in str(d.get("result") or "")[:200000]:
            hits += 1
    print(f"  {coll}: {n} docs, {hits} carrying vertices_pct in result")

print("\n=== estimates_trash / upload_blobs ===")
print(f"  estimates_trash for est: "
      f"{db.estimates_trash.count_documents({'id': EID})}")
snap = est.get("hover_measurements") or {}
zk = [k for k in snap if "zone" in k.lower() or "overlay" in k.lower()]
print(f"  hover_measurements keys mentioning zone/overlay: {zk}")
hist = [k for k in est.keys() if "hist" in k.lower() or "snap" in k.lower()
        or "backup" in k.lower()]
print(f"  estimate doc history-ish keys: {hist}")
