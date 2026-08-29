import asyncio, json, sys
sys.path.insert(0, "/app/backend")
from db import db
from photo_zone_proposals import _raw, _measurements

LEFT_PHOTO = "ai_3112d120856e4ad7aac69a818bca9052.jpg"
EST = "338c6ac8-4e77-4dcd-84df-1cb7327b7ecb"


async def main():
    print("=== every stored mark on the LEFT photo ===")
    async for m in db.photo_takeoff_marks.find({"estimate_id": EST, "photo_key": LEFT_PHOTO}):
        print(" kind=", m.get("kind"), "shape=", m.get("shape"), "origin=", m.get("origin"),
              "label=", m.get("label"), "status=", m.get("status"),
              "ys=", [round(p["y"], 1) for p in (m.get("points") or [])])
    print("\n=== photo_takeoff doc keys (scale etc) ===")
    doc = await db.estimates.find_one({"id": EST}, {"_id": 0, "photo_takeoff": 1})
    print(json.dumps(doc, default=str)[:1200])

    run = await db.ai_measure_runs.find_one({"estimate_id": EST, "status": "done"},
                                            sort=[("created_at", -1)])
    raw = _raw(run)
    print("\n=== raw_ai top-level keys ===")
    print(sorted(raw.keys()))
    blob = json.dumps(raw).lower()
    for tok in ("starter", "wall_base", "grade", "base_line", "baseline", "sill_height",
                "bottom", "foundation", "ground"):
        print(f"  '{tok}' in raw_ai: {tok in blob}")
    left = [w for w in raw.get("walls") or [] if str(w.get("label")).lower() == "left"]
    print("\n=== LEFT wall entry ===")
    print(json.dumps(left, default=str)[:2500])

asyncio.run(main())
