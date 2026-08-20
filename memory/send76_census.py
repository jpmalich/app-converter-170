"""SEND-76 census — human-set lines with overlay markers stripped.
REPORT ONLY. Touches nothing. Run: python3 /app/memory/send76_census.py"""
import os, sys, json
sys.path.insert(0, "/app/backend")
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from routes.pdf_overlay import apply_overlay_to_takeoff, _line_matches

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

MARKERS = ("overlay_superseded", "superseded_qty", "overlay_sqft",
           "overlay_polygon_count", "overlay_replaced_surfaces")

rows = []
for est in db.estimates.find({}, {"_id": 0, "id": 1, "estimate_number": 1,
                                  "customer_name": 1, "lines": 1,
                                  "deleted_at": 1, "kind": 1}):
    lines = est.get("lines") or []
    human = [l for l in lines if (l.get("qty_src") or "") == "human"]
    if not human:
        continue
    polys = list(db.pdf_overlay_polygons.find(
        {"estimate_id": est["id"]}, {"_id": 0}))
    binding = [p for p in polys
               if (p.get("provenance") or "human") != "proposed"
               and not p.get("binding_suspended")]
    computed = apply_overlay_to_takeoff(lines, polys)
    comp_by_id = {}
    for i, l in enumerate(lines):
        comp_by_id[i] = computed[i]
    ever_zones = bool(polys) or db.zone_correction_events.count_documents(
        {"estimate_id": est["id"]}) > 0
    for i, l in enumerate(lines):
        if (l.get("qty_src") or "") != "human":
            continue
        has_markers = any(l.get(k) is not None for k in MARKERS)
        cls_bound = any(_line_matches(l, p.get("material_class") or "")
                        for p in binding)
        comp = comp_by_id[i]
        computed_qty = comp.get("qty")
        computed_known = (comp.get("overlay_superseded") is True
                          or l.get("derived_qty") is not None)
        if not comp.get("overlay_superseded") and l.get("derived_qty") is not None:
            computed_qty = l.get("derived_qty")
        stored = l.get("qty")
        delta = (stored - computed_qty) if (computed_known and
                 isinstance(computed_qty, (int, float)) and
                 isinstance(stored, (int, float))) else None
        rate = float(l.get("mat") or 0) + float(l.get("lab") or 0)
        rows.append({
            "estimate_id": est["id"],
            "estimate": est.get("estimate_number") or "",
            "customer": est.get("customer_name") or "",
            "tab": l.get("tab"), "section": l.get("section"),
            "name": l.get("name"), "unit": l.get("unit"),
            "stored_qty": stored,
            "markers_present": has_markers,
            "class_bound_by_zones_now": cls_bound,
            "zones_ever_existed": ever_zones,
            "computed_qty": computed_qty if computed_known else None,
            "computed_known": computed_known,
            "delta_qty": round(delta, 2) if delta is not None else None,
            "delta_dollars": round(delta * rate, 2) if delta is not None else None,
        })

stripped = [r for r in rows if not r["markers_present"] and r["zones_ever_existed"]]
never = [r for r in rows if not r["markers_present"] and not r["zones_ever_existed"]]
modern = [r for r in rows if r["markers_present"]]

def show(title, rs):
    print(f"\n=== {title} ({len(rs)} lines, "
          f"{len(set(r['estimate_id'] for r in rs))} estimates) ===")
    for r in sorted(rs, key=lambda x: -(abs(x["delta_dollars"] or 0))):
        print(json.dumps(r, default=str))

show("HUMAN LINES, MARKERS ABSENT, ZONES EXISTED (stripped-or-superset)", stripped)
show("HUMAN LINES, MARKERS NEVER EXISTED (no zones ever on estimate)", never)
show("HUMAN LINES WITH MARKERS INTACT (modern, has record)", modern)
print("\nTOTAL human-set lines:", len(rows),
      "on", len(set(r["estimate_id"] for r in rows)), "estimates")
