import asyncio, json, sys
sys.path.insert(0, "/app/backend")
from db import db
from photo_zone_proposals import _raw, _run_photo_names


async def main():
    run = await db.ai_measure_runs.find_one(
        {"estimate_id": "338c6ac8-4e77-4dcd-84df-1cb7327b7ecb", "status": "done"},
        sort=[("created_at", -1)])
    names = _run_photo_names(run)
    photos = {p["index"]: p.get("elevation") for p in _raw(run)["photos"]}
    print("photos:", photos)
    for o in _raw(run)["openings"]:
        print(json.dumps(o, default=str))

asyncio.run(main())
