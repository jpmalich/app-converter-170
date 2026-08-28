import asyncio, sys
sys.path.insert(0, "/app/backend")
from db import db


async def main():
    est = await db.estimates.find_one({"estimate_number": "EST-176308"}, {"_id": 0, "id": 1})
    if not est:
        est = await db.estimates.find_one({"id": "EST-176308"}, {"_id": 0, "id": 1})
    print("estimate:", est)
    eid = est["id"]
    async for m in db.photo_takeoff_marks.find({"estimate_id": eid, "origin": "ai_zone_proposal"}):
        ai = m.get("ai") or {}
        ys = [p["y"] for p in m["points"]]
        xs = [p["x"] for p in m["points"]]
        print("---", m["photo_key"], m["kind"], ai.get("ref_id"))
        print("   anchor:", ai.get("anchor"), "bottom_from:", ai.get("anchor_bottom_from"),
              "scale_from:", ai.get("anchor_scale_from"), "ppf:", ai.get("px_per_ft"))
        print("   x:", round(min(xs)), round(max(xs)), " y:", round(min(ys)), round(max(ys)),
              "status:", m["status"])
        print("   basis:", (m.get("basis") or "")[:400])

asyncio.run(main())
