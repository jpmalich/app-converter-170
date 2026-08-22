"""SEND-110 probe v2 — x-ruler trace at the RESOLVED outline's own
boundaries (silhouette corners + wall corners), full cluster window,
twin identification, rule-A / rule-B theoretical widths. READ-ONLY."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

HOUSES = [("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
          ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332")]
SEALED = {"LETRICK": {"front": 54.0, "rear": 54.0,
                      "left": 30.0, "right": 30.0}}
FPPX = {("LETRICK", "front"): {"9.08": 1.28794},
        ("LETRICK", "rear"): {"9'-11": 1.40662, "9'-1 1/8": 1.28990},
        ("LETRICK", "left"): {"9.08": 1.26111},
        ("LETRICK", "right"): {"9.08": 1.27439}}
EPS = 0.05


def clusters_of(strokes):
    items = sorted(strokes, key=lambda s: (s["x0"] + s["x1"]) / 2.0)
    out = []
    for s in items:
        x = (s["x0"] + s["x1"]) / 2.0
        if out and x - out[-1]["xs"][-1] <= EPS:
            out[-1]["xs"].append(x)
            out[-1]["frags"].append((s["top"], s["bottom"]))
        else:
            out.append({"xs": [x], "frags": [(s["top"], s["bottom"])]})
    for c in out:
        c["x"] = sum(c["xs"]) / len(c["xs"])
        ivs = sorted(c["frags"])
        merged = [list(ivs[0])]
        for a, b in ivs[1:]:
            if a <= merged[-1][1] + EPS:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        c["n"] = len(merged)
        c["y0"] = min(a for a, b in merged)
        c["y1"] = max(b for a, b in merged)
        c["cov"] = sum(b - a for a, b in merged)
        c["gaps"] = [round(merged[i + 1][0] - merged[i][1], 2)
                     for i in range(len(merged) - 1)]
        del c["xs"], c["frags"]
    return out


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import (page_segments, _merge_collinear,
                               wall_outline_from_segments)
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
        if not ot or not pdf:
            continue
        faces = derive_face_heights(ot)
        cache = {}
        for face in ("front", "rear", "left", "right"):
            r = faces.get(face) or {}
            spec = _best_ladder_spec(r)
            if not spec:
                continue
            pg = spec["page"]
            cand = next((c for c in (r.get("candidates") or [r])
                         if c.get("page") == pg), r)
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
            print(f"\n==== {house} {face} p{pg} lw={lw.get('status')} "
                  f"x_span={lw.get('x_span')} "
                  f"wall_corners={lw.get('wall_corners')} ====")
            if lw.get("status") != "RESOLVED":
                print(f"  reason={lw.get('reason')}")
                continue
            keep = []
            for s in cache[idx]:
                t, b = (min(s["top"], s["bottom"]),
                        max(s["top"], s["bottom"]))
                if t < band[0] or b > band[1]:
                    continue
                if x_fence is not None:
                    lo, hi = min(s["x0"], s["x1"]), max(s["x0"], s["x1"])
                    if (lo < x_fence[0] - gap_tol
                            or hi > x_fence[1] + gap_tol):
                        continue
                mx, my = (s["x0"] + s["x1"]) / 2.0, (t + b) / 2.0
                if any(b0 <= mx <= b1 and c0 <= my <= c1
                       for b0, c0, b1, c1 in mask):
                    continue
                keep.append({"x0": s["x0"], "x1": s["x1"],
                             "top": t, "bottom": b})
            raw_v = [s for s in keep
                     if abs(s["x1"] - s["x0"]) < (s["bottom"] - s["top"])]
            vert_m = _merge_collinear(raw_v, "v", gap_tol)
            band_v = [s for s in raw_v
                      if s["bottom"] >= plate[0] and s["top"] <= floor[1]]
            cl = clusters_of(band_v)
            fpp = FPPX.get((house, face)) or {}
            fpp0 = list(fpp.values())[0] if fpp else None
            bounds = []
            xs = lw["x_span"]
            wc = lw.get("wall_corners")
            bounds.append(("SIL-L", xs[0], -1))
            bounds.append(("SIL-R", xs[1], 1))
            if wc:
                if abs(wc[0] - xs[0]) > EPS:
                    bounds.append(("WALL-L", wc[0], -1))
                if abs(wc[1] - xs[1]) > EPS:
                    bounds.append(("WALL-R", wc[1], 1))
            for name, cx, sgn in bounds:
                near = [c for c in cl
                        if -0.8 <= (c["x"] - cx) * sgn <= 2.5]
                near.sort(key=lambda c: (c["x"] - cx) * sgn)
                print(f"  [{name}] x={cx:.3f} (outboard = {'+x' if sgn>0 else '-x'}):")
                for c in near[:12]:
                    d = (c["x"] - cx) * sgn
                    cont = c["n"] == 1
                    reach = (c["y0"] <= plate[1] and c["y1"] >= floor[0])
                    ptl = c["y0"] >= plate[0] - gap_tol
                    ftd = f" {d*fpp0:+.3f}ft" if fpp0 else ""
                    print(f"    x={c['x']:.3f} Δ={d:+.3f}%{ftd} "
                          f"frags={c['n']} y[{c['y0']:.2f},{c['y1']:.2f}] "
                          f"cov={c['cov']:.2f}% cont={cont} "
                          f"reach_both={reach} pt={ptl} "
                          f"gaps={c['gaps'][:4]}")
                # merged twin states in the same window
                for v in sorted(
                        (v for v in vert_m
                         if -0.8 <= (((v["x0"] + v["x1"]) / 2.0) - cx)
                         * sgn <= 1.0),
                        key=lambda v: ((v["x0"] + v["x1"]) / 2 - cx) * sgn):
                    x = (v["x0"] + v["x1"]) / 2.0
                    spans = (v["top"] <= plate[1]
                             and v["bottom"] >= floor[0])
                    ptl = v["top"] >= plate[0] - gap_tol
                    print(f"    MERGED x={x:.3f} Δ={(x-cx)*sgn:+.3f}% "
                          f"y[{v['top']:.2f},{v['bottom']:.2f}] "
                          f"spans={spans} pt={ptl}")
            # rule widths on the WALL ruler (wall corners where present)
            wl, wr = (wc if wc else xs)
            in_cl = [c for c in cl]
            ruleA_l = min(c["x"] for c in in_cl)
            ruleA_r = max(c["x"] for c in in_cl)
            rb = [c for c in in_cl
                  if c["y0"] <= plate[1] and c["y1"] >= floor[0]]
            ruleB_l = min((c["x"] for c in rb), default=None)
            ruleB_r = max((c["x"] for c in rb), default=None)
            sealed = SEALED.get(house, {}).get(face)
            for lbl, f_ in (fpp or {"(no scale)": None}).items():
                if f_ is None:
                    print(f"  RULES: no evidence scale — widths in %: "
                          f"current={wr-wl:.2f} "
                          f"ruleA={ruleA_r-ruleA_l:.2f} "
                          f"ruleB={(ruleB_r-ruleB_l) if rb else None}")
                    continue
                print(f"  RULES @{lbl}: current={(wr-wl)*f_:.2f}ft "
                      f"ruleA={(ruleA_r-ruleA_l)*f_:.2f}ft "
                      + (f"ruleB={(ruleB_r-ruleB_l)*f_:.2f}ft "
                         f"(L {ruleB_l:.3f} R {ruleB_r:.3f})"
                         if rb else "ruleB=None")
                      + f" sealed={sealed}")
                if rb:
                    print(f"    ruleB moves: L "
                          f"{(wl-ruleB_l)*f_:+.3f}ft outboard, R "
                          f"{(ruleB_r-wr)*f_:+.3f}ft outboard "
                          f"(vs current wall ruler)")


main()
