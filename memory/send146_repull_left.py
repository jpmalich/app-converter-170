"""SEND-146 (d) — Howard's order, 2026-08-28: clear ONLY `face:left:body` on
EST-176308 and re-pull that one zone. FRONT (hand-tweaked), BACK, the LEFT
dormer, every opening and the LEFT scale are NOT touched."""
import asyncio
import sys

sys.path.insert(0, "/app/backend")

from db import db
from photo_zone_proposals import propose_zones_for_photo

EST = "338c6ac8-4e77-4dcd-84df-1cb7327b7ecb"
LEFT_PHOTO = "ai_3112d120856e4ad7aac69a818bca9052.jpg"


async def main():
    est = await db.estimates.find_one({"id": EST}, {"_id": 0, "company_id": 1})
    run = await db.ai_measure_runs.find_one({"estimate_id": EST, "status": "done"},
                                            sort=[("created_at", -1)])
    before = await db.photo_takeoff_marks.count_documents({"estimate_id": EST})
    q = {"estimate_id": EST, "photo_key": LEFT_PHOTO,
         "ai.ref_id": "face:left:body", "origin": "ai_zone_proposal"}
    doomed = [m async for m in db.photo_takeoff_marks.find(q)]
    print("about to delete:", [(m["label"], m["ai"]["ref_id"]) for m in doomed])
    assert all(m["kind"] == "siding_zone" and m["status"] == "provisional"
               for m in doomed), "refusing: not a provisional body zone"
    assert len(doomed) == 1, f"refusing: {len(doomed)} matches, expected 1"
    r = await db.photo_takeoff_marks.delete_many(q)
    print("deleted:", r.deleted_count)

    from config import UPLOAD_DIR
    from routes.photo_takeoff import _photo_natural_size
    from upload_store import rehydrate_to_disk

    async def natural_size(key):
        dims = _photo_natural_size(key)
        if dims:
            return dims
        if await rehydrate_to_disk(key, UPLOAD_DIR):
            return _photo_natural_size(key)
        return None

    row = await propose_zones_for_photo(db, run, EST, est["company_id"],
                                        LEFT_PHOTO, "hhunt6677@yahoo.com",
                                        natural_size)
    for m in row.pop("marks", []):
        ys = [p["y"] for p in m["points"]]
        xs = [p["x"] for p in m["points"]]
        print(f"\nPLACED {m['label']} ({m['ai']['ref_id']})")
        print("  x", round(min(xs), 1), "->", round(max(xs), 1),
              " y", round(min(ys), 1), "->", round(max(ys), 1))
        print("  anchor:", m["ai"]["anchor"], "| bottom_from:",
              m["ai"]["anchor_bottom_from"], "| sill_of:",
              m["ai"].get("anchor_bottom_sill_of"), "| ppf:", m["ai"]["px_per_ft"])
        print("  basis:", m["basis"])
    print("\nrow:", row)
    after = await db.photo_takeoff_marks.count_documents({"estimate_id": EST})
    print("marks on this estimate before/after:", before, after)

asyncio.run(main())
