"""SEND-66 census — REPORT ONLY, applies nothing.

Across every estimate that has zones: how many zones carry a face tag
that DISAGREES with their centroid's elevation band on that page; of
those, how many are CONFIRMED (human/binding); for each confirmed one:
which estimate, which face it currently supersedes, which face it
should, and the quantity difference. Run from /app/backend."""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


async def latest_ocr(db, est_id):
    run = await db.ai_blueprint_runs.find_one(
        {"estimate_id": est_id, "status": "done"},
        {"_id": 0, "result.raw_ai._ocr_text_by_page": 1,
         "result.raw_ai._ocr_text_ref": 1, "run_id": 1},
        sort=[("created_at", -1)])
    raw = ((run or {}).get("result") or {}).get("raw_ai") or {}
    ot = raw.get("_ocr_text_by_page")
    if not ot and raw.get("_ocr_text_ref"):
        ref = await db.ai_blueprint_ocr.find_one(
            {"run_id": raw["_ocr_text_ref"]}, {"_id": 0, "pages": 1})
        ot = (ref or {}).get("pages")
    return ot if isinstance(ot, dict) else None, (run or {}).get("run_id")


async def main():
    from height_read import elevation_page_faces
    from routes.pdf_overlay import (surface_derived_snapshot,
                                    resolve_face_from_bands)
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    total = disagree = confirmed_bad = 0
    rows = []
    for eid in await db.pdf_overlay_polygons.distinct("estimate_id"):
        est = await db.estimates.find_one(
            {"id": eid}, {"_id": 0, "estimate_number": 1,
                          "customer_name": 1, "hover_measurements": 1})
        ot, run_id = await latest_ocr(db, eid)
        pages = elevation_page_faces(ot) if ot else {}
        async for z in db.pdf_overlay_polygons.find({"estimate_id": eid},
                                                    {"_id": 0}):
            total += 1
            res = resolve_face_from_bands(
                pages.get(str(z.get("page"))) or {},
                z.get("vertices_pct") or [], z.get("face_id") or "")
            if res["status"] == "NO_BANDS":
                continue
            if res["status"] == "RESOLVED" and not res["disagrees"]:
                continue
            disagree += 1
            is_confirmed = z.get("provenance") == "human"
            if is_confirmed:
                confirmed_bad += 1
            should = res.get("resolved_face_id")
            cur_sq, cur_ref = z.get("surface_derived_sqft"), z.get(
                "surface_refusal")
            new_sq = new_ref = None
            if should and est:
                new_sq, new_ref = surface_derived_snapshot(est, should)
            rows.append({
                "estimate": (est or {}).get("estimate_number"),
                "estimate_id": eid, "zone": z.get("id"),
                "page": z.get("page"), "provenance": z.get("provenance"),
                "confirmed": is_confirmed,
                "tagged": z.get("face_id"), "band_says": should,
                "band_status": res["status"], "why": res.get("reason"),
                "zone_sqft": z.get("sqft"),
                "supersedes_now_sqft": cur_sq,
                "supersedes_now_refusal": cur_ref,
                "should_supersede_sqft": new_sq,
                "should_supersede_refusal": new_ref,
            })
    print(f"zones examined: {total}")
    print(f"tag disagrees with centroid band (or ambiguous): {disagree}")
    print(f"of those CONFIRMED (binding): {confirmed_bad}")
    for r in rows:
        print("-" * 70)
        for k, v in r.items():
            print(f"  {k}: {v}")


asyncio.run(main())
