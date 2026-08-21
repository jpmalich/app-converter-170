"""SEND-87 probe — ABOVE-ROOF CHASE ANATOMY, all faces, both houses.
Read-only. For each face: verticals inside the fence whose ink rises
ABOVE the plate box (candidates for a chimney rising past the roof),
the horizontals up there (cap / ridge / roof lines), and the face's
own ft-per-pct scale so W reads in feet. Nothing wired."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

HOUSES = [("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
          ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332")]


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import page_segments, _merge_collinear
    from routes.pdf_overlay import _best_ladder_spec
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for house, eid in HOUSES:
        run = db.ai_blueprint_runs.find_one(
            {"estimate_id": eid, "status": "done"},
            sort=[("created_at", -1)])
        raw = ((run or {}).get("result") or {}).get("raw_ai") or {}
        ot = raw.get("_ocr_text_by_page")
        if not ot and raw.get("_ocr_text_ref"):
            ref = db.ai_blueprint_ocr.find_one(
                {"run_id": raw["_ocr_text_ref"]}, {"pages": 1})
            ot = (ref or {}).get("pages")
        if not ot:
            continue
        pdf = next((f["name"] for f in run.get("source_files") or []
                    if f.get("kind") == "pdf"), None)
        if not pdf or not (UPLOAD_DIR / pdf).exists():
            continue
        faces = derive_face_heights(ot)
        cache = {}
        for face, r in faces.items():
            spec = _best_ladder_spec(r)
            cand = next((c for c in (r.get("candidates") or [r])
                         if spec and c.get("page") == spec["page"]), r)
            geo = cand.get("datum_geometry") or {}
            band, pg = cand.get("band"), cand.get("page")
            top_d, bot_d = geo.get("top_of_plate"), geo.get("first_floor")
            if not (pg and band and top_d and bot_d
                    and top_d.get("b0") is not None
                    and bot_d.get("b0") is not None):
                print(f"\n== {house} {face}: datum pair not located ==")
                continue
            plate = (top_d["b0"], top_d["b1"])
            floor = (bot_d["b0"], bot_d["b1"])
            gap_tol = max(plate[1] - plate[0], floor[1] - floor[0])
            idx = int(pg) - 1
            if idx not in cache:
                cache[idx] = page_segments(str(UPLOAD_DIR / pdf), idx)
            xs = []
            for k in ("top_of_plate", "first_floor", "top_of_foundation"):
                for m in (geo.get(k) or {}).get("markers") or []:
                    xs.extend(m)
            fence = (min(xs), max(xs)) if len(xs) >= 2 else None
            fpp = None
            if spec.get("ft") and spec.get("scale_y"):
                W, H = ot[pg]["page_w"], ot[pg]["page_h"]
                sy = spec["scale_y"]
                fpp = spec["ft"] / (abs(sy[1] - sy[0]) * H) * W / 100.0
            y0, y1 = band
            keep = []
            for s in cache[idx]:
                t, b = min(s["top"], s["bottom"]), max(s["top"],
                                                       s["bottom"])
                if t < y0 or b > y1:
                    continue
                if fence is not None:
                    lo = min(s["x0"], s["x1"])
                    hi = max(s["x0"], s["x1"])
                    if lo < fence[0] - gap_tol or hi > fence[1] + gap_tol:
                        continue
                keep.append({"x0": s["x0"], "x1": s["x1"],
                             "top": t, "bottom": b})
            vert = _merge_collinear(
                [s for s in keep
                 if abs(s["x1"] - s["x0"]) < (s["bottom"] - s["top"])],
                "v", gap_tol)
            horiz = _merge_collinear(
                [s for s in keep
                 if abs(s["x1"] - s["x0"]) >= (s["bottom"] - s["top"])],
                "h", gap_tol)
            # verticals whose ink rises above the plate box top
            risers = [v for v in vert
                      if v["top"] < plate[0] - gap_tol
                      and (v["bottom"] - v["top"]) > gap_tol]
            print(f"\n== {house} {face} p{pg} band=[{y0:.1f},{y1:.1f}] "
                  f"plate={plate} fence={fence} "
                  f"ft/pct={fpp and round(fpp, 4)} ==")
            for v in sorted(risers, key=lambda v: v["x0"]):
                print(f"  RISER x={v['x0']:.2f} "
                      f"y[{v['top']:.2f},{v['bottom']:.2f}]")
            # horizontals above the plate: caps / ridge / roof lines
            ups = [h for h in horiz
                   if (h["top"] + h["bottom"]) / 2.0 < plate[0]]
            for h in sorted(ups, key=lambda h: h["top"])[:18]:
                h0 = min(h["x0"], h["x1"])
                h1 = max(h["x0"], h["x1"])
                w = (f" W={(h1 - h0) * fpp:.2f}ft" if fpp else "")
                print(f"  H y={(h['top'] + h['bottom']) / 2:.2f} "
                      f"x[{h0:.2f},{h1:.2f}] len={h1 - h0:.2f}{w}")


main()
