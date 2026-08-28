"""SEND-144 REPORT PROBE — READ ONLY. Reads the AI photo-measure run that
ALREADY FINISHED on the live estimate and prints, per face: the measured
width and height, the gable/dormer split, the opening list, the refusal,
and which photo that face belongs to. Writes nothing. Invents nothing —
where the run holds no figure it prints MISSING."""
import asyncio
import json
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    runs = []
    async for r in db.ai_measure_runs.find(
            {"status": "complete"},
            {"_id": 0, "run_id": 1, "estimate_id": 1, "created_at": 1,
             "photo_names": 1, "photo_urls": 1, "result": 1}).sort(
                 "created_at", -1).limit(6):
        runs.append(r)
    print(f"completed runs found: {len(runs)}")
    for r in runs:
        est = await db.estimates.find_one({"id": r.get("estimate_id")},
                                          {"_id": 0, "estimate_number": 1})
        res = r.get("result") or {}
        raw = res.get("raw_ai") or {}
        names = r.get("photo_names") or r.get("photo_urls") or []
        print("\n" + "=" * 72)
        print(f"run {r['run_id']}  est {est and est.get('estimate_number')}  "
              f"{r.get('created_at')}  photos={len(names)}")
        print("  result keys:", sorted(res.keys()))
        print("  raw_ai keys:", sorted(raw.keys()))
        faces = raw.get("faces") or raw.get("walls") or res.get("faces") or []
        print(f"  faces/walls entries: {len(faces)}")
        for f in faces if isinstance(faces, list) else []:
            if isinstance(f, dict):
                print("   ", json.dumps(f)[:700])
        for k in ("gables", "dormers", "openings", "refusals", "photo_faces",
                  "wall_photo_idx", "notes"):
            v = raw.get(k)
            if v is not None:
                s = json.dumps(v)
                print(f"  raw_ai[{k}] ({len(v) if hasattr(v, '__len__') else '?'}): "
                      f"{s[:900]}")
        for k in sorted(res.keys()):
            if k in ("raw_ai",):
                continue
            s = json.dumps(res[k], default=str)
            print(f"  result[{k}]: {s[:500]}")
        for i, n in enumerate(names):
            print(f"    photo[{i}] = {n}")


asyncio.run(main())
