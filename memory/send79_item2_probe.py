"""SEND-79 Item 2 PROBE — the missed right-elevation chimney.
Report only: dumps every spanning candidate per face BEFORE the
plate-termination filter, flags which were dropped by it, and looks
for jog horizontals connecting dropped strokes to the wall line.
Also re-runs LEFT without its jog horizontal to test whether the
captured step depended on the joint."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import (page_segments, _merge_collinear,
                               _lateral_candidates,
                               wall_outline_from_segments)
    from routes.pdf_overlay import _best_ladder_spec
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for house, eid in [("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
                       ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332")]:
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
        print(f"\n===== {house} =====")
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
                continue
            idx = int(pg) - 1
            if idx not in cache:
                cache[idx] = page_segments(str(UPLOAD_DIR / pdf), idx)
            segs = cache[idx]
            mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
                     u["loc"]["x_pct"] + u["loc"]["w_pct"],
                     u["loc"]["y_pct"] + u["loc"]["h_pct"])
                    for u in (ot.get(pg) or {}).get("runs") or []]
            xs = []
            for k in ("top_of_plate", "first_floor", "top_of_foundation"):
                for m in (geo.get(k) or {}).get("markers") or []:
                    xs.extend(m)
            fence = (min(xs), max(xs)) if len(xs) >= 2 else None
            plate = (top_d["b0"], top_d["b1"])
            floor = (bot_d["b0"], bot_d["b1"])
            gap_tol = max(plate[1] - plate[0], floor[1] - floor[0])
            y0, y1 = band
            keep = []
            for s in segs:
                t, b = min(s["top"], s["bottom"]), max(s["top"],
                                                       s["bottom"])
                if t < y0 or b > y1:
                    continue
                if fence is not None:
                    lo, hi = min(s["x0"], s["x1"]), max(s["x0"], s["x1"])
                    if lo < fence[0] - gap_tol or hi > fence[1] + gap_tol:
                        continue
                mx = (s["x0"] + s["x1"]) / 2.0
                my = (t + b) / 2.0
                if any(bx0 <= mx <= bx1 and by0 <= my <= by1
                       for bx0, by0, bx1, by1 in mask):
                    continue
                keep.append({"x0": s["x0"], "x1": s["x1"],
                             "top": t, "bottom": b})
            vert = [s for s in keep
                    if abs(s["x1"] - s["x0"]) < (s["bottom"] - s["top"])]
            horiz = [s for s in keep
                     if abs(s["x1"] - s["x0"]) >= (s["bottom"] - s["top"])]
            vert = _merge_collinear(vert, "v", gap_tol)
            horiz = _merge_collinear(horiz, "h", gap_tol)
            cands = _lateral_candidates(vert, horiz, plate, floor,
                                        gap_tol)
            pt = [c for c in cands if c.get("pt")]
            dropped = [c for c in cands if not c.get("pt")]
            W = ot[pg]["page_w"]
            sy = (spec or {}).get("scale_y")
            fpp = (((spec or {}).get("ft") or 0) / (abs(sy[1] - sy[0])
                   * ot[pg]["page_h"])) if (spec and sy
                                            and (spec or {}).get("ft")
                                            ) else None
            print(f"\n  {face} p{pg} plate_y={plate} floor_y={floor} "
                  f"gap_tol={gap_tol:.2f} fence={fence}")
            for c in cands:
                tag = "KEPT(pt)" if c.get("pt") else (
                    "DROPPED-BY-PT-FILTER" if pt else "kept(no pt set)")
                print(f"    cand x_top={c['x_top']:.2f} "
                      f"x_bot={c['x_bot']:.2f} jog={c['jog_y']} "
                      f"{'CHAIN' if c['jog_y'] is not None else 'single'}"
                      f"  -> {tag}")
            # for dropped singles: their stroke extents + any jog
            # horizontal connecting them toward a kept wall line
            if pt and dropped:
                kept_xs = sorted({round(c["x_top"], 2) for c in pt})
                for c in dropped:
                    v = next((s for s in vert
                              if abs((s["x0"] + s["x1"]) / 2.0
                                     - c["x_top"]) <= gap_tol
                              and s["top"] <= plate[1]
                              and s["bottom"] >= floor[0]), None)
                    if v is None:
                        continue
                    rise = plate[0] - v["top"]
                    print(f"      dropped stroke @x={c['x_top']:.2f}: "
                          f"top={v['top']:.2f} bottom={v['bottom']:.2f} "
                          f"rises {rise:.2f}%-pts ABOVE the plate box"
                          + (f" (~{rise/100*ot[pg]['page_h']*fpp:.1f} ft)"
                             if fpp else ""))
                    for h in horiz:
                        hy = (h["top"] + h["bottom"]) / 2.0
                        if not (plate[1] < hy < floor[0]):
                            continue
                        h0, h1 = min(h["x0"], h["x1"]), max(h["x0"],
                                                            h["x1"])
                        near_c = (abs(h0 - c["x_top"]) <= gap_tol
                                  or abs(h1 - c["x_top"]) <= gap_tol)
                        near_w = any(abs(h0 - x) <= gap_tol
                                     or abs(h1 - x) <= gap_tol
                                     for x in kept_xs)
                        if near_c and near_w:
                            print(f"        JOG horizontal y={hy:.2f} "
                                  f"x[{h0:.2f},{h1:.2f}] joins it to a "
                                  "kept wall line")
            # LEFT-without-the-joint experiment (Letrick only)
            if house == "LETRICK" and face == "left":
                args = ((y0, y1), plate, floor, mask)
                base = wall_outline_from_segments(segs, *args,
                                                  x_fence=fence)
                jogless = [s for s in segs
                           if not (abs(s["x1"] - s["x0"])
                                   >= abs(s["bottom"] - s["top"])
                                   and plate[1]
                                   < (min(s["top"], s["bottom"])
                                      + abs(s["bottom"] - s["top"]) / 2.0
                                      + min(s["top"], s["bottom"])) / 2.0
                                   < floor[0])]
                jogless = [s for s in segs
                           if not (abs(s["x1"] - s["x0"])
                                   >= abs(s["bottom"] - s["top"])
                                   and plate[1] < (s["top"] + s["bottom"])
                                   / 2.0 < floor[0])]
                nolink = wall_outline_from_segments(jogless, *args,
                                                    x_fence=fence)
                print(f"    LEFT with jog horizontals present : "
                      f"{base['status']} span={base.get('x_span')} "
                      f"v={base.get('n_vertices')}")
                print(f"    LEFT with jog horizontals REMOVED : "
                      f"{nolink['status']} span={nolink.get('x_span')} "
                      f"v={nolink.get('n_vertices')}")


main()
