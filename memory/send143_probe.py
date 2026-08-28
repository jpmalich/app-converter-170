"""SEND-143 ITEM 2 probe — READ ONLY. Names every photo-takeoff mark that
exists today, per estimate and photo, so the trim report can print REAL
numbers instead of hypotheses. Writes nothing."""
import asyncio
import math
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


async def main():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    n = 0
    async for est in db.estimates.find(
            {"photo_takeoff": {"$exists": True}},
            {"_id": 0, "estimate_number": 1, "photo_takeoff": 1,
             "photo_siding_sqft": 1}):
        pt = est.get("photo_takeoff") or {}
        marks = pt.get("marks") or []
        scales = pt.get("scales") or {}
        if not marks and not scales:
            continue
        n += 1
        print(f"\n=== {est.get('estimate_number')} — {len(marks)} mark(s), "
              f"{len(scales)} scale(s)")
        for key, sc in scales.items():
            print(f"  scale[{key}]: {sc}")
        for m in marks:
            pts = m.get("points") or []
            print(f"  {m.get('kind'):16} {m.get('status'):11} "
                  f"shape={m.get('shape')} pts={len(pts)} "
                  f"origin={m.get('origin')} label={m.get('label')!r} "
                  f"cat={m.get('category')} depth={m.get('depth_ft')}")
            if pts and len(pts) <= 6:
                print(f"      {[(round(p['x'], 1), round(p['y'], 1)) for p in pts]}")
    print(f"\nestimates carrying photo-takeoff state: {n}")

    # every distinct kind ever stored
    kinds = {}
    async for est in db.estimates.find({"photo_takeoff.marks": {"$exists": True}},
                                       {"_id": 0, "photo_takeoff.marks": 1}):
        for m in (est.get("photo_takeoff") or {}).get("marks") or []:
            kinds[m.get("kind")] = kinds.get(m.get("kind"), 0) + 1
    print("kinds stored across all estimates:", kinds)
    _ = math
    cli.close()


asyncio.run(main())
