"""SEND-84 probe A — MEMBER ANATOMY at every joint (report only).

Ruling CCC(b) says the shoulder terminates at the members' inner twin
strokes. Before wiring, dump the ACTUAL vertical ink around each
member at each joint's y: raw (pre-mask) and kept (post-mask,
post-merge), so the twin structure is read from the drawing and not
from the SEND-82 report's prose (which contains an unreconciled 0.40
shortfall on the chimney side)."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient


def face_ctx():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import page_segments, _merge_collinear
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
                   mask, fence, _merge_collinear)


# joints of interest, from send82's probe output: (house, face,
# window_x0, window_x1, jog_y)
WINDOWS = [
    ("LETRICK", "right", 76.5, 81.5, 64.55),   # true shoulder members
    ("LETRICK", "left", 16.5, 20.5, None),      # tick region (any jog y)
    ("LETRICK", "left", 42.5, 46.5, None),      # 24% wrong-edge jog
]


def main():
    for (house, face, segs, band, plate, floor, mask, fence,
         _merge_collinear) in face_ctx():
        wins = [w for w in WINDOWS if w[0] == house and w[1] == face]
        if not wins:
            continue
        gap_tol = max(plate[1] - plate[0], floor[1] - floor[0])
        y0, y1 = band
        for _, _, wx0, wx1, jy in wins:
            print(f"\n=== {house} {face} window x[{wx0},{wx1}] "
                  f"jog_y={jy} (gap_tol={gap_tol:.2f}, band=[{y0:.2f},"
                  f"{y1:.2f}], plate={plate}, floor={floor}) ===")
            print("-- RAW vertical strokes in window (pre-everything):")
            for s in segs:
                t, b = min(s["top"], s["bottom"]), max(s["top"], s["bottom"])
                if abs(s["x1"] - s["x0"]) >= (b - t):
                    continue
                mx = (s["x0"] + s["x1"]) / 2.0
                if not (wx0 <= mx <= wx1):
                    continue
                inband = t >= y0 and b <= y1
                mxm = (s["x0"] + s["x1"]) / 2.0
                mym = (t + b) / 2.0
                masked = any(bx0 <= mxm <= bx1 and by0 <= mym <= by1
                             for bx0, by0, bx1, by1 in mask)
                covers = (jy is not None
                          and t - gap_tol <= jy <= b + gap_tol)
                print(f"   x={mx:7.3f} y[{t:6.2f},{b:6.2f}] len={b-t:6.2f}"
                      f" inband={inband} masked={masked}"
                      f"{' COVERS-JOG-Y' if covers else ''}")
            # post-pipeline (band+fence+mask, merged) verticals
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
            vert = _merge_collinear(vert, "v", gap_tol)
            print("-- KEPT+MERGED verticals in window:")
            for v in vert:
                x = (v["x0"] + v["x1"]) / 2.0
                if not (wx0 <= x <= wx1):
                    continue
                covers = (jy is not None and
                          v["top"] - gap_tol <= jy <= v["bottom"] + gap_tol)
                print(f"   x={x:7.3f} y[{v['top']:6.2f},"
                      f"{v['bottom']:6.2f}]{' COVERS-JOG-Y' if covers else ''}")
            # horizontals near the jog y, to see the shoulder ink itself
            if jy is not None:
                horiz = [s for s in keep
                         if abs(s["x1"] - s["x0"]) >= (s["bottom"] - s["top"])]
                horiz = _merge_collinear(horiz, "h", gap_tol)
                print("-- KEPT+MERGED horizontals within gap_tol of jog y:")
                for h in horiz:
                    hy = (h["top"] + h["bottom"]) / 2.0
                    if abs(hy - jy) > gap_tol:
                        continue
                    h0 = min(h["x0"], h["x1"])
                    h1 = max(h["x0"], h["x1"])
                    if h1 < wx0 - 2 or h0 > wx1 + 2:
                        continue
                    print(f"   y={hy:6.2f} x[{h0:7.3f},{h1:7.3f}] "
                          f"len={h1-h0:.2f}")


main()
