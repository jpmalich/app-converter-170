"""SEND-89 probe — EDGE vs INTERRUPTING per face, the partition, W on
above-roof chases, plate-vs-cap split, silent-drop check, wall twin
anatomy, full-height qualifiers. Read-only. Nothing wired."""
import os, sys, json
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

HOUSES = [("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
          ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332")]


def shoelace(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import (page_segments, _merge_collinear,
                               _joint_lines, _lateral_candidates,
                               wall_outline_from_segments, _COORD_EPS)
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
        pdf = next((f["name"] for f in run.get("source_files") or []
                    if f.get("kind") == "pdf"), None)
        if not ot or not pdf or not (UPLOAD_DIR / pdf).exists():
            print(f"== {house}: no OCR or PDF ==")
            continue
        faces = derive_face_heights(ot)
        cache = {}
        for face in ("front", "rear", "left", "right"):
            r = faces.get(face) or {}
            spec = _best_ladder_spec(r)
            if not spec:
                print(f"\n==== {house} {face}: no ladder spec ====")
                continue
            cand = next((c for c in (r.get("candidates") or [r])
                         if c.get("page") == spec["page"]), r)
            geo = cand.get("datum_geometry") or {}
            band = cand.get("band") or [0.0, 100.0]
            top_d, bot_d = geo.get("top_of_plate"), geo.get("first_floor")
            if not (top_d and bot_d and top_d.get("b0") is not None
                    and bot_d.get("b0") is not None):
                print(f"\n==== {house} {face}: datum pair not located ====")
                continue
            plate = (top_d["b0"], top_d["b1"])
            floor = (bot_d["b0"], bot_d["b1"])
            gap_tol = max(plate[1] - plate[0], floor[1] - floor[0])
            pg = spec["page"]
            idx = int(pg) - 1
            if idx not in cache:
                cache[idx] = page_segments(str(UPLOAD_DIR / pdf), idx)
            mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
                     u["loc"]["x_pct"] + u["loc"]["w_pct"],
                     u["loc"]["y_pct"] + u["loc"]["h_pct"])
                    for u in (ot.get(pg) or {}).get("runs") or []]
            fence_xs = []
            for dk in ("top_of_plate", "first_floor", "top_of_foundation"):
                for m in (geo.get(dk) or {}).get("markers") or []:
                    fence_xs.extend(m)
            x_fence = ((min(fence_xs), max(fence_xs))
                       if len(fence_xs) >= 2 else None)
            lw = wall_outline_from_segments(
                cache[idx], (band[0], band[1]), plate, floor, mask,
                x_fence=x_fence)
            # ft-per-pct scales from this face's OWN chain
            fpp_x = fpp_y = None
            if spec.get("ft") and spec.get("scale_y"):
                W, H = ot[pg]["page_w"], ot[pg]["page_h"]
                sy = spec["scale_y"]
                dy = abs(sy[1] - sy[0]) * 100.0        # y pct
                fpp_y = spec["ft"] / dy
                fpp_x = spec["ft"] / (abs(sy[1] - sy[0]) * H) * W / 100.0
            print(f"\n==== {house} {face} p{pg} status={lw.get('status')} "
                  f"reason={lw.get('reason')} ====")
            print(f"  fpp_x={fpp_x and round(fpp_x,4)} "
                  f"fpp_y={fpp_y and round(fpp_y,4)} plate={plate} "
                  f"floor={floor} gap_tol={round(gap_tol,3)}")

            # rebuild the module's own kept/merged sets (same filters)
            keep = []
            for s in cache[idx]:
                t, b = min(s["top"], s["bottom"]), max(s["top"],
                                                       s["bottom"])
                if t < band[0] or b > band[1]:
                    continue
                if x_fence is not None:
                    lo, hi = min(s["x0"], s["x1"]), max(s["x0"], s["x1"])
                    if lo < x_fence[0] - gap_tol or hi > x_fence[1] + gap_tol:
                        continue
                mx, my = (s["x0"] + s["x1"]) / 2.0, (t + b) / 2.0
                if any(bx0 <= mx <= bx1 and by0 <= my <= by1
                       for bx0, by0, bx1, by1 in mask):
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
            jog_lines = _joint_lines(
                [s for s in keep
                 if abs(s["x1"] - s["x0"]) >= (s["bottom"] - s["top"])],
                plate[1], floor[0])
            cands = _lateral_candidates(vert, jog_lines, plate, floor,
                                        gap_tol)
            singles = [c for c in cands if c["jog_y"] is None]
            chains = [c for c in cands if c["jog_y"] is not None]
            print("  FULL-HEIGHT SPANNERS (singles spanning plate->floor):")
            for c in sorted(singles, key=lambda c: c["x_top"]):
                w = ""
                if fpp_x:
                    w = ""
                print(f"    x={c['x_top']:.2f} pt={c['pt']}")
            for c in chains:
                print(f"  CHAIN x_top={c['x_top']:.2f} "
                      f"x_bot={c['x_bot']:.2f} jog_y={c['jog_y']:.2f}")

            # ABOVE-PLATE CAP FINDER: horizontal whose BOTH ends meet
            # the TOPS of two distinct verticals (line-weight joint),
            # both descending below the cap — the drawn chase signature.
            risers = [v for v in vert if v["top"] < plate[0] - gap_tol]
            caps = []
            for h in horiz:
                hy = (h["top"] + h["bottom"]) / 2.0
                if hy >= plate[0]:
                    continue
                h0, h1 = min(h["x0"], h["x1"]), max(h["x0"], h["x1"])
                lm = [v for v in risers
                      if abs(v["x0"] - h0) <= gap_tol
                      and abs(v["top"] - hy) <= gap_tol
                      and v["bottom"] > hy + gap_tol]
                rm = [v for v in risers
                      if abs(v["x0"] - h1) <= gap_tol
                      and abs(v["top"] - hy) <= gap_tol
                      and v["bottom"] > hy + gap_tol]
                if lm and rm and h1 - h0 > _COORD_EPS:
                    caps.append((hy, h0, h1,
                                 max(v["bottom"] for v in lm),
                                 max(v["bottom"] for v in rm)))
            print("  CAPS (horizontal joining two riser tops, above plate):")
            for hy, h0, h1, lb, rb in sorted(caps):
                wft = f" W={(h1 - h0) * fpp_x:.2f}ft" if fpp_x else ""
                hft = (f" cap_to_plate={(plate[0] - hy) * fpp_y:.2f}ft"
                       if fpp_y else "")
                print(f"    cap y={hy:.2f} x[{h0:.2f},{h1:.2f}]"
                      f"{wft}{hft} riser_bottoms=({lb:.2f},{rb:.2f})")

            if lw.get("status") != "RESOLVED":
                continue
            # outline partition arithmetic
            v = [(p[0] * 100, p[1] * 100) for p in lw["vertices_pct"]]
            xs = [p[0] for p in v]
            sil_ft = (max(xs) - min(xs)) * fpp_x if fpp_x else None
            wc = lw.get("wall_corners")
            wall_ft = (wc[1] - wc[0]) * fpp_x if (wc and fpp_x) else None
            print(f"  OUTLINE x_span={lw['x_span']} wall_corners={wc} "
                  f"y_top={lw['y_top']} y_bot={lw['y_bot']} "
                  f"SIL={sil_ft and round(sil_ft,2)}ft "
                  f"WALL={wall_ft and round(wall_ft,2)}ft")
            if fpp_x and fpp_y:
                ft_pts = [(x * fpp_x, y * fpp_y) for x, y in v]
                a_out = shoelace(ft_pts)
                a_wall = ((wc[1] - wc[0]) * fpp_x
                          * (lw["y_bot"] - lw["y_top"]) * fpp_y
                          if wc else None)
                print(f"  AREA outline={a_out:.2f} ft2 "
                      f"wall_rect={a_wall and round(a_wall,2)} ft2 "
                      f"residue(outline-wall)="
                      f"{a_wall and round(a_out - a_wall,2)} ft2")
                # per-chain bump rectangles (below-jog chimney profile)
                for c in chains:
                    lo, hi = sorted((c["x_top"], c["x_bot"]))
                    bw = (hi - lo) * fpp_x
                    bh = (lw["y_bot"] - c["jog_y"]) * fpp_y
                    print(f"  BUMP chain x[{lo:.2f},{hi:.2f}] "
                          f"depth={bw:.2f}ft below-jog h={bh:.2f}ft "
                          f"area={bw*bh:.2f} ft2")
            # WALL TWIN anatomy: vertical clusters within 1.0 pct of
            # each wall corner — pt status + spans
            if wc:
                for side, cx in (("L", wc[0]), ("R", wc[1])):
                    near = [c for c in singles
                            if abs(c["x_top"] - cx) <= 1.0]
                    nearv = [w2 for w2 in vert
                             if abs(w2["x0"] - cx) <= 1.0]
                    print(f"  TWINS near wall corner {side} x={cx}: ")
                    for w2 in sorted(nearv, key=lambda w2: w2["x0"]):
                        spans = (w2["top"] <= plate[1]
                                 and w2["bottom"] >= floor[0])
                        pt = w2["top"] >= plate[0] - gap_tol
                        d = (w2["x0"] - cx) * fpp_x if fpp_x else 0
                        print(f"    x={w2['x0']:.2f} ({d:+.2f}ft) "
                              f"y[{w2['top']:.2f},{w2['bottom']:.2f}] "
                              f"spans={spans} plate_term={pt}")
            # ABOVE-PLATE chimney ink near each chain's projection x
            for c in chains:
                px = c["x_bot"] if c["x_top"] != c["x_bot"] else None
                if px is None:
                    continue
                up = [w2 for w2 in vert if abs(w2["x0"] - px) <= 0.5
                      and w2["top"] < plate[0] - gap_tol]
                for w2 in up:
                    hft = (plate[0] - w2["top"]) * fpp_y if fpp_y else 0
                    print(f"  ABOVE-PLATE ink at proj x={w2['x0']:.2f}: "
                          f"rises to y={w2['top']:.2f} "
                          f"({hft:.2f}ft above plate)")


main()
