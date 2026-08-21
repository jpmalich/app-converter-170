"""SEND-81 probe — the OUTERMOST-BOUNDARY property against all 7
dropped strokes (report only, wires nothing). For each dropped
non-plate-terminated spanning stroke: does drawn geometry lie beyond
it in its direction (within the face's band + fence, outside the
line-weight tolerance)? Names what lies beyond."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient


def face_ctx():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import page_segments, _merge_collinear, \
        _lateral_candidates
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
            mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
                     u["loc"]["x_pct"] + u["loc"]["w_pct"],
                     u["loc"]["y_pct"] + u["loc"]["h_pct"])
                    for u in (ot.get(pg) or {}).get("runs") or []]
            xs = []
            for k in ("top_of_plate", "first_floor", "top_of_foundation"):
                for m in (geo.get(k) or {}).get("markers") or []:
                    xs.extend(m)
            fence = (min(xs), max(xs)) if len(xs) >= 2 else None
            yield (house, face, cache[idx], band,
                   (top_d["b0"], top_d["b1"]), (bot_d["b0"], bot_d["b1"]),
                   mask, fence, _merge_collinear, _lateral_candidates)


def main():
    for (house, face, segs, band, plate, floor, mask, fence,
         _merge_collinear, _lateral_candidates) in face_ctx():
        gap_tol = max(plate[1] - plate[0], floor[1] - floor[0])
        y0, y1 = band
        keep = []
        for s in segs:
            t, b = min(s["top"], s["bottom"]), max(s["top"], s["bottom"])
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
        cands = _lateral_candidates(vert, horiz, plate, floor, gap_tol)
        pt = [c for c in cands if c.get("pt")]
        dropped = [c for c in cands if not c.get("pt")]
        if not (pt and dropped):
            continue
        allk = vert + horiz
        # ink that lies WITHIN the datum interval the boundary claims
        # to bound (strictly between the two datum label boxes) — a
        # dimension tick above the plate or below the floor is not
        # wall-region geometry.
        iv0, iv1 = plate[1], floor[0]

        def in_interval(s):
            return min(s["top"], s["bottom"]) < iv1 \
                and max(s["top"], s["bottom"]) > iv0

        allk_iv = [s for s in allk if in_interval(s)]
        print(f"\n=== {house} {face} (gap_tol={gap_tol:.2f}, "
              f"fence={fence}, interval=({iv0:.2f},{iv1:.2f})) ===")
        for c in dropped + [dict(c, kept=True) for c in pt]:
            x = c["x_top"]
            tag = "KEPT-pt" if c.get("kept") else "dropped"
            for label, pool in (("literal", allk),
                                ("interval-only", allk_iv)):
                beyond_l = [s for s in pool
                            if min(s["x0"], s["x1"]) < x - gap_tol]
                beyond_r = [s for s in pool
                            if max(s["x0"], s["x1"]) > x + gap_tol]
                outer = (not beyond_l) or (not beyond_r)
                print(f"  {tag} @x={x:.2f} [{label}]: "
                      f"outermost-left={not beyond_l} "
                      f"outermost-right={not beyond_r} -> "
                      f"{'OUTERMOST' if outer else 'INTERIOR'}")
                if label == "interval-only" and not outer:
                    for nm, lst, key in (
                            ("beyond-left", beyond_l,
                             lambda s: min(s["x0"], s["x1"])),
                            ("beyond-right", beyond_r,
                             lambda s: max(s["x0"], s["x1"]))):
                        for s in sorted(lst,
                                        key=lambda s: abs(key(s) - x))[:3]:
                            kind = ("V" if abs(s["x1"] - s["x0"])
                                    < (s["bottom"] - s["top"]) else "H")
                            print(f"      {nm} ({len(lst)}): {kind} "
                                  f"x[{min(s['x0'], s['x1']):.2f},"
                                  f"{max(s['x0'], s['x1']):.2f}] "
                                  f"y[{s['top']:.2f},{s['bottom']:.2f}]")


main()
