"""SEND-145 ITEM 1 PROBE — READ ONLY.

Per face on EST-176308: WHERE SEND-144's starting box sat (recomputed
deterministically, exactly as it was placed), WHERE HOWARD DRAGGED IT TO
(the marks as they stand now), the miss per edge, and an inventory of every
piece of PIXEL EVIDENCE that already exists on that same photo and could
have anchored the box. Guesses nothing, writes nothing.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from PIL import Image  # noqa: E402

from config import UPLOAD_DIR  # noqa: E402
from photo_zone_proposals import (build_zone_marks, face_for_photo,  # noqa: E402
                                  _run_photo_names)
from upload_store import rehydrate_to_disk  # noqa: E402

EST = "338c6ac8-4e77-4dcd-84df-1cb7327b7ecb"      # EST-176308
RUN = "556b9121f209470f9983b9065d1eab32"


def box(pts):
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


async def natural(name):
    p = UPLOAD_DIR / name
    if not p.exists():
        p = await rehydrate_to_disk(name, UPLOAD_DIR) or p
    return Image.open(p).size if p.exists() else (0, 0)


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    run = await db.ai_measure_runs.find_one({"run_id": RUN})
    names = _run_photo_names(run)
    marks = [m async for m in db.photo_takeoff_marks.find({"estimate_id": EST})]
    raw = (run.get("result") or {}).get("raw_ai") or {}

    for idx, photo in enumerate(names):
        who = face_for_photo(run, photo)
        face = who.get("face")
        on_photo = [m for m in marks if m.get("photo_key") == photo]
        if not face or (who.get("refusal") and not on_photo):
            print(f"\n=== photo[{idx}] {face or '?'} — {('REFUSED: ' + who['refusal'][:80]) if who.get('refusal') else 'no face'}"
                  f" — marks on it: {len(on_photo)}")
            continue
        nat_w, nat_h = await natural(photo)
        print(f"\n=== photo[{idx}] {face.upper()} ({nat_w}x{nat_h}) — "
              f"{len(on_photo)} mark(s) on it")
        proposed = {}
        if not who.get("refusal"):
            for m in build_zone_marks(run, face, who["wall"], photo, nat_w,
                                      nat_h, EST, "co", None):
                proposed[m["ai"]["ref_id"].split(":")[-1]] = m
        for part, pm in proposed.items():
            x0, y0, x1, y1 = box(pm["points"])
            print(f"  SEND-144 {part:6}: x {x0/nat_w:.3f}–{x1/nat_w:.3f}  "
                  f"y {y0/nat_h:.3f}–{y1/nat_h:.3f}  (fractions of the photo)")
            cur = next((m for m in on_photo
                        if (m.get("ai") or {}).get("ref_id") == pm["ai"]["ref_id"]), None)
            if not cur:
                print(f"    → no mark with ref {pm['ai']['ref_id']} on this photo now")
                continue
            cx0, cy0, cx1, cy1 = box(cur["points"])
            print(f"  HOWARD   {part:6}: x {cx0/nat_w:.3f}–{cx1/nat_w:.3f}  "
                  f"y {cy0/nat_h:.3f}–{cy1/nat_h:.3f}   status={cur['status']}")
            print(f"    MISS: left {(cx0-x0)/nat_w:+.3f}  right {(cx1-x1)/nat_w:+.3f}  "
                  f"top {(cy0-y0)/nat_h:+.3f}  bottom {(cy1-y1)/nat_h:+.3f} "
                  "(+ = he moved it right/down)")
        # EVIDENCE ALREADY ON THIS PHOTO
        ops = [m for m in on_photo if m.get("kind") == "opening"
               and len(m.get("points") or []) >= 3]
        if ops:
            xs0 = min(box(m["points"])[0] for m in ops)
            xs1 = max(box(m["points"])[2] for m in ops)
            ys0 = min(box(m["points"])[1] for m in ops)
            ys1 = max(box(m["points"])[3] for m in ops)
            print(f"  EVIDENCE — {len(ops)} boxed opening(s) from the read: "
                  f"x {xs0/nat_w:.3f}–{xs1/nat_w:.3f}  y {ys0/nat_h:.3f}–{ys1/nat_h:.3f}")
        else:
            print("  EVIDENCE — no boxed opening on this photo")
        human = [m for m in on_photo if m.get("origin") in
                 ("contractor_stage1", "contractor_stage2", "imported_annotation")]
        for m in human:
            x0, y0, x1, y1 = box(m["points"]) if m.get("points") else (0, 0, 0, 0)
            print(f"  EVIDENCE — human {m['kind']}/{m.get('label')} "
                  f"({m['status']}, {m['origin']}): x {x0/nat_w:.3f}–{x1/nat_w:.3f} "
                  f"y {y0/nat_h:.3f}–{y1/nat_h:.3f}")
        p = next((q for q in (raw.get("photos") or []) if q.get("index") == idx), {})
        keys = [k for k in p.keys() if k not in ("index",)]
        print(f"  the read's own per-photo fields: {keys}")
        for k in keys:
            v = p[k]
            if isinstance(v, (int, float, str)) and str(v)[:60]:
                print(f"      {k} = {str(v)[:90]}")
    print("\nreference the read used:", (raw.get("scale") or {}).get("reference_used")
          or raw.get("reference_used"))


asyncio.run(main())
