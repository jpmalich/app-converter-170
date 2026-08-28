import asyncio, sys
sys.path.insert(0, "/app/backend")
from db import db
from photo_zone_proposals import first_floor_anchor, _run_photo_names, _raw


async def main():
    run = await db.ai_measure_runs.find_one({"estimate_id": "338c6ac8-4e77-4dcd-84df-1cb7327b7ecb",
                                             "status": "done"},
                                            sort=[("created_at", -1)])
    print("run:", run["run_id"], run.get("created_at"))
    names = _run_photo_names(run)
    from routes.photo_takeoff import _photo_natural_size
    from config import UPLOAD_DIR
    from upload_store import rehydrate_to_disk
    photos = {p["index"]: p.get("elevation") for p in _raw(run)["photos"]}
    walls = {str(w.get("label")).lower(): w for w in _raw(run)["walls"]}
    for i, name in enumerate(names):
        elev = str(photos.get(i) or "").lower()
        if elev not in ("front", "back", "left", "right"):
            continue
        dims = _photo_natural_size(name)
        if not dims:
            await rehydrate_to_disk(name, UPLOAD_DIR)
            dims = _photo_natural_size(name)
        w = walls.get(elev) or {}
        h = float(w.get("height_ft") or 0)
        rd = [r.get("eave_ft") for r in (w.get("_per_photo_readings") or [])]
        if w.get("height_ft_source") == "direct_disagreement" and rd:
            h = max(float(x) for x in rd if x)
        a = first_floor_anchor(run, i, dims[0], dims[1], h) if dims else None
        print(f"\n{elev.upper()} photo={name} natural={dims} width_ft={w.get('width_ft')} height_ft_used={h}")
        print("  anchor:", a)
        for o in _raw(run)["openings"]:
            if o.get("bbox_photo_idx") == i:
                bb = o.get("bbox") or {}
                print("   opening", o.get("opening_id"), "width_in", o.get("width_in"),
                      "on_dormer", o.get("on_dormer"),
                      "bbox y", bb.get("y"), "h", bb.get("h"), "w", bb.get("w"))

asyncio.run(main())
