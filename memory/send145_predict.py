"""SEND-145 ITEM 2 PREDICTION — READ ONLY, RUN BEFORE ANY PRODUCTION CODE
CHANGED. Prints exactly what FRONT / LEFT / BACK would propose under the new
anchor Howard ruled: FIRST-FLOOR opening boxes only (no gable-peak window, no
dormer opening) · the LOWEST first-floor box sets the body BOTTOM · the
BIGGEST first-floor box sets the plane SCALE · sides = the run's width at
that scale, centred on the first-floor boxes. Writes nothing."""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

RUN = "556b9121f209470f9983b9065d1eab32"
FACES = {0: ("front", 2400, 1800, 27.0, 10.9, 6.5, None),
         2: ("left", 640, 480, 37.0, 8.4, 0.0, (14.1, 3.5)),
         4: ("back", 1428, 1071, 27.0, 9.7, 7.0, None)}
HOWARD = {0: {"body": (0.151, 0.407, 0.841, 0.776), "gable": (0.165, 0.184, 0.834, 0.412)},
          2: {"body": (0.093, 0.398, 0.941, 0.678), "dormer": (0.349, 0.256, 0.668, 0.359)},
          4: {"body": (0.192, 0.388, 0.827, 0.736), "gable": (0.206, 0.204, 0.810, 0.392)}}


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    run = await db.ai_measure_runs.find_one({"run_id": RUN})
    ops = run["result"]["raw_ai"]["openings"]
    for idx, (face, W, H, wft, hft, rise, dormer) in FACES.items():
        cands = [o for o in ops
                 if o.get("bbox_photo_idx") == idx and o.get("bbox")
                 and o.get("width_in") and not o.get("on_dormer")]
        if not cands:
            print(f"\n{face.upper()}: no first-floor box with a typed size — "
                  "photo-bottom fallback, said out loud")
            continue
        low = max(cands, key=lambda o: o["bbox"]["y"] + o["bbox"]["h"])
        bottom = low["bbox"]["y"] + low["bbox"]["h"]
        seed = (low["bbox"]["w"] * W) / (float(low["width_in"]) / 12.0)
        band_top = bottom - hft * seed / H
        first = [o for o in cands
                 if (o["bbox"]["y"] + o["bbox"]["h"]) >= band_top]
        big = max(first, key=lambda o: o["bbox"]["w"])
        ppf = (big["bbox"]["w"] * W) / (float(big["width_in"]) / 12.0)
        dropped = [o["opening_id"] for o in cands if o not in first]
        cx = (min(o["bbox"]["x"] for o in first)
              + max(o["bbox"]["x"] + o["bbox"]["w"] for o in first)) / 2.0
        bw = wft * ppf / W
        top = bottom - hft * ppf / H
        hb = HOWARD[idx]["body"]
        print(f"\n{face.upper()} — bottom from '{low['opening_id']}' · scale from "
              f"'{big['opening_id']}' ({float(big['width_in'])/12:.2f} ft, "
              f"{big['bbox']['w']*W:.0f} px) = {ppf:.1f} px/ft"
              + (f" · dropped above the wall band: {dropped}" if dropped else ""))
        print(f"  BODY  x {cx-bw/2:.3f}–{cx+bw/2:.3f}  y {top:.3f}–{bottom:.3f}"
              f"   | Howard x {hb[0]:.3f}–{hb[2]:.3f} y {hb[1]:.3f}–{hb[3]:.3f}"
              f"   | worst edge {max(abs(hb[0]-(cx-bw/2)), abs(hb[2]-(cx+bw/2)), abs(hb[1]-top), abs(hb[3]-bottom)):.3f}")
        if rise:
            g = top - rise * ppf / H
            hg = HOWARD[idx]["gable"]
            print(f"  GABLE y {g:.3f}–{top:.3f}   | Howard y {hg[1]:.3f}–{hg[3]:.3f}"
                  f"   | top miss {abs(hg[1]-g):.3f}")
        if dormer:
            dw, dk = dormer
            dt = top - dk * ppf / H
            hd = HOWARD[idx]["dormer"]
            print(f"  DORMER x {cx-dw*ppf/W/2:.3f}–{cx+dw*ppf/W/2:.3f} y {dt:.3f}–{top:.3f}"
                  f"   | Howard x {hd[0]:.3f}–{hd[2]:.3f} y {hd[1]:.3f}–{hd[3]:.3f}")


asyncio.run(main())
