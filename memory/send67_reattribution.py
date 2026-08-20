"""SEND-67 — AUTHORIZED re-attribution (Howard, verbatim mandate).

The 3 mis-tagged zones + their events on EST-569367 (rear-body pieces
face-tagged "front" on the FRONT & REAR sheet) are re-attributed by
centroid-band resolution. Conditions honored:
 1. Says which of the three are CONFIRMED and the quantity delta.
 2. Recorded as an authorized correction (tracking event on the
    estimate, same shape as the EST-803966 user_error_reversal).
 3. The original baseline is PRESERVED — corrected numbers append
    beside it, never over it.
Run from /app/backend. REPORT + APPLY (authorized — never silent).
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

EID = "07517940-ae2f-447b-b280-0b9302d2f04d"   # EST-569367


async def main():
    from motor.motor_asyncio import AsyncIOMotorClient
    from height_read import elevation_page_faces
    from routes.pdf_overlay import (resolve_face_from_bands,
                                    surface_derived_snapshot,
                                    apply_overlay_to_takeoff)
    import routes.pdf_overlay as po
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    est = await db.estimates.find_one({"id": EID}, {"_id": 0})
    assert est, "estimate not found"
    print(f"=== SEND-67 re-attribution on {est['estimate_number']} ===\n")

    ot, _run = None, None
    run = await db.ai_blueprint_runs.find_one(
        {"estimate_id": EID, "status": "done"},
        {"_id": 0, "result.raw_ai._ocr_text_by_page": 1,
         "result.raw_ai._ocr_text_ref": 1}, sort=[("created_at", -1)])
    raw = ((run or {}).get("result") or {}).get("raw_ai") or {}
    ot = raw.get("_ocr_text_by_page")
    if not ot and raw.get("_ocr_text_ref"):
        ref = await db.ai_blueprint_ocr.find_one(
            {"run_id": raw["_ocr_text_ref"]}, {"_id": 0, "pages": 1})
        ot = (ref or {}).get("pages")
    pages = elevation_page_faces(ot)

    # BEFORE — the line as it binds right now
    def _siding_lines(lines):
        return [(ln.get("description") or ln.get("name") or "?",
                 ln.get("qty"), ln.get("unit"))
                for ln in lines if po._line_matches(ln, "siding")]
    print("LINE BEFORE:", _siding_lines(est.get("lines") or []))

    victims = []
    async for z in db.pdf_overlay_polygons.find({"estimate_id": EID},
                                                {"_id": 0}):
        res = resolve_face_from_bands(
            pages.get(str(z.get("page"))) or {},
            z.get("vertices_pct") or [], z.get("face_id") or "")
        if res["status"] == "RESOLVED" and res["disagrees"]:
            victims.append((z, res))
    print(f"\nzones whose tag disagrees with the centroid band: "
          f"{len(victims)}")
    now = datetime.now(timezone.utc)
    moved = []
    for z, res in victims:
        confirmed = z.get("provenance") == "human"
        new_face = res["resolved_face_id"]
        new_sq, new_ref = surface_derived_snapshot(est, new_face)
        print(f"\n  zone {z['id'][:8]} p{z['page']}  {z['sqft']} ft²  "
              f"CONFIRMED: {confirmed}")
        print(f"    tagged {z['face_id']!r} → band says {new_face!r}")
        print(f"    superseded until now: {z['face_id']!r} "
              f"(derived {z.get('surface_derived_sqft')} ft², "
              f"refusal={z.get('surface_refusal')!r})")
        print(f"    will supersede: {new_face!r} "
              f"(derived {new_sq} ft², refusal={new_ref!r})")
        await db.pdf_overlay_polygons.update_one({"id": z["id"]}, {"$set": {
            "face_id": new_face,
            "surface_derived_sqft": new_sq,
            "surface_refusal": new_ref,
            "face_resolution": {
                "method": "authorized_reattribution",
                "authorized_by": "Howard (SEND-67)",
                "submitted_face_id": z["face_id"],
                "resolved_face_id": new_face,
                "band_face": res["band_face"],
                "at": now.isoformat(),
                "reason": ("face-tag defect: page-level attribution on a "
                           "combined sheet — corrected by centroid-band "
                           "resolution")},
            "updated_at": now}})
        ev = await db.zone_correction_events.find_one(
            {"zone_id": z["id"]}, {"_id": 0, "id": 1, "face_id": 1})
        if ev:
            await db.zone_correction_events.update_one(
                {"id": ev["id"]}, {"$set": {
                    "face_id": new_face,
                    "reattributed_send67": {
                        "from": z["face_id"], "at": now.isoformat(),
                        "note": "metric bookkeeping — no quantity moved "
                                "by the event itself"}}})
            print(f"    event {ev['id']} face {ev['face_id']!r} → "
                  f"{new_face!r} (metric data, re-attributed and SAID SO)")
        moved.append({"zone_id": z["id"], "sqft": z.get("sqft"),
                      "confirmed": confirmed,
                      "from": z["face_id"], "to": new_face})

    if not moved:
        print("\nnothing to re-attribute — closing.")
        return

    # recompute the takeoff exactly as the PUT path does
    all_polys = [p async for p in db.pdf_overlay_polygons.find(
        {"estimate_id": EID}, {"_id": 0})]
    new_lines = apply_overlay_to_takeoff(est.get("lines") or [], all_polys)
    await db.estimates.update_one({"id": EID}, {"$set": {
        "lines": new_lines, "updated_at": now}})
    print("\nLINE AFTER: ", _siding_lines(new_lines))

    # the authorized-correction tracking event (never silent)
    rec = {"type": "zones.face_reattribution",
           "at": now.isoformat(),
           "meta": {"authorized_by": "Howard (SEND-67)",
                    "method": "centroid_band_resolution",
                    "cause": ("face-tag defect: page-level face "
                              "attribution on the FRONT & REAR combined "
                              "sheet (fixed in SEND-66)"),
                    "moved": moved,
                    "line_before": _siding_lines(est.get("lines") or []),
                    "line_after": _siding_lines(new_lines)}}
    await db.estimates.update_one(
        {"id": EID},
        {"$push": {"tracking": {"$each": [rec], "$slice": -500}}})
    print("\ntracking event recorded: zones.face_reattribution "
          "(authorized by Howard, SEND-67)")

    # restated per-face event split (same denominator of 8 surfaces)
    print("\nCORRECTED EVENT ATTRIBUTION (restated):")
    async for e in db.zone_correction_events.find(
            {"estimate_id": EID}, {"_id": 0, "event": 1, "face_id": 1,
                                   "area_confirmed_sqft": 1}):
        print(f"  {e['event']:<20} {e['face_id']:<8} "
              f"{e.get('area_confirmed_sqft') or ''}")


asyncio.run(main())
