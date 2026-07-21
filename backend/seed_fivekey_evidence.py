"""Seed the ZZ FIVE-KEY CONTRACT EVIDENCE estimate + run (one window,
one entry door, one patio door, one garage door, one vent on FRONT).
Idempotent: re-running replaces the same fixed ids."""
import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

EST_ID = "zz-fivekey-evidence-0001"
RUN_ID = "zzfivekeyrun0001"


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    owner = await db.users.find_one({"email": "hhunt6677@yahoo.com"}, {"company_id": 1})
    now = datetime.now(timezone.utc).isoformat()
    est = {
        "id": EST_ID,
        "company_id": owner["company_id"],
        "customer_name": "ZZ FIVE-KEY CONTRACT EVIDENCE",
        "address": "evidence fixture — five-key schedule ruling 2026-07-20",
        "estimate_number": "ZZ-FIVEKEY",
        "created_at": now,
    }
    openings = [
        {"opening_id": "front-w1", "type": "window", "style": "Double Hung",
         "wall": "front", "width_in": 36, "height_in": 60, "along_wall_ft": 6.0,
         "bbox": {"x": 0.08, "y": 0.40, "w": 0.05, "h": 0.35}},
        {"opening_id": "front-d1", "type": "entry_door", "style": "",
         "wall": "front", "width_in": 36, "height_in": 80, "along_wall_ft": 16.0,
         "bbox": {"x": 0.25, "y": 0.50, "w": 0.05, "h": 0.40}},
        {"opening_id": "front-p1", "type": "patio_door", "style": "2-Lite Slider",
         "wall": "front", "width_in": 72, "height_in": 80, "along_wall_ft": 26.0,
         "bbox": {"x": 0.40, "y": 0.50, "w": 0.10, "h": 0.40}},
        {"opening_id": "front-g1", "type": "garage_door", "style": "",
         "wall": "front", "width_in": 192, "height_in": 84, "along_wall_ft": 42.0,
         "bbox": {"x": 0.58, "y": 0.48, "w": 0.26, "h": 0.42}},
        {"opening_id": "front-v1", "type": "vent", "style": "",
         "wall": "front", "width_in": 14, "height_in": 10, "along_wall_ft": 55.0,
         "bbox": {"x": 0.92, "y": 0.55, "w": 0.02, "h": 0.05}},
    ]
    run = {
        "run_id": RUN_ID,
        "estimate_id": EST_ID,
        "status": "done",
        "created_at": datetime.now(timezone.utc),
        "completed_at": now,
        "model_name": "seeded-evidence (no AI call)",
        "result": {
            "model": "seeded-evidence (no AI call)",
            "raw_ai": {
                "story_count": 1,
                "walls": [{
                    "label": "front", "width_ft": 60.0, "height_ft": 9.0,
                    "width_ft_source": "direct_ref", "height_ft_source": "direct_ref",
                    "gable_triangle_height_ft": 0, "siding_pct_this_wall": 80,
                    "wall_body_profile_callout": "lap 4\"",
                    "confidence": 90,
                    "confidence_reasoning": "seeded evidence fixture — synthetic",
                    "_source_photo_indices": [0],
                }],
                "openings": openings,
            },
            "measurements": {"_ai_openings_schedule": []},
        },
    }
    await db.estimates.replace_one({"id": EST_ID}, est, upsert=True)
    await db.ai_measure_runs.replace_one({"run_id": RUN_ID}, run, upsert=True)
    n = await db.estimates.count_documents({})
    print(f"seeded estimate {EST_ID} + run {RUN_ID} · estimates total now {n}")

asyncio.run(main())
