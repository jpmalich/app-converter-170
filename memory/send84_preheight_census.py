"""SEND-84 report 4 — PRE-HEIGHT-BUILD CENSUS (read-only).

Which estimates carry lines/zones derived under SUPERSEDED rules?
Rule eras are read off each proposal's own disclosure keys:
  • pre-SEND-77: linework disclosure lacks `x_fence` (no x-scoping)
  • pre-SEND-84: lacks `projection_refusals` (pre-RULING CCC)
  • current: carries both.
Also flags lines whose qty rides overlay markers (human zones traced
over proposals of any era). Reports; changes nothing."""
import os
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

eras = {"pre_send77": 0, "pre_send84": 0, "current": 0, "no_linework": 0}
by_est = {}
for p in db.pdf_overlay_polygons.find(
        {"provenance": "proposed"}, {"_id": 0}):
    lw = ((p.get("proposed_from") or {}).get("linework")) or None
    if lw is None:
        era = "no_linework"
    elif "x_fence" not in lw:
        era = "pre_send77"
    elif "projection_refusals" not in lw:
        era = "pre_send84"
    else:
        era = "current"
    eras[era] += 1
    by_est.setdefault(p["estimate_id"], []).append(
        (p.get("face_id"), era, p.get("geometry_tier")))

print("=== proposal era census (all estimates) ===")
for k, v in eras.items():
    print(f"  {k}: {v}")

print("\n=== per estimate ===")
for eid, rows in sorted(by_est.items()):
    est = db.estimates.find_one({"id": eid},
                                {"estimate_number": 1,
                                 "customer_name": 1, "lines": 1})
    if not est:
        print(f"  {eid[:8]} (ESTIMATE GONE) {rows}")
        continue
    num = est.get("estimate_number")
    marked = [ln.get("name") for ln in est.get("lines") or []
              if ln.get("overlay_superseded") or ln.get("overlay_sqft")
              or ln.get("qty_src") == "human"]
    worst = ("pre_send77" if any(r[1] == "pre_send77" for r in rows)
             else "pre_send84" if any(r[1] == "pre_send84" for r in rows)
             else "current")
    flag = (" << CARRIES SUPERSEDED-RULE GEOMETRY"
            if worst != "current" else "")
    print(f"  {num} ({est.get('customer_name')}): "
          f"{len(rows)} proposals, era={worst}{flag}")
    for f, e, gt in rows:
        print(f"      face={f} era={e} tier={gt}")
    if marked:
        print(f"      lines riding overlay/human qty: {marked}")

print("\n=== human zones present (any estimate) ===")
for p in db.pdf_overlay_polygons.find(
        {"provenance": {"$ne": "proposed"}}, {"_id": 0}):
    est = db.estimates.find_one({"id": p["estimate_id"]},
                                {"estimate_number": 1})
    print(f"  {(est or {}).get('estimate_number')} face={p.get('face_id')}"
          f" prov={p.get('provenance')} class={p.get('material_class')}")
