"""SEND-110 probe — per-face scale query + x-ruler fragmentation trace.
READ-ONLY. Nothing wired, nothing written to any estimate."""
import os, sys, json
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

HOUSES = [("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
          ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332")]
SEALED = {"LETRICK": {"front": 54.0, "rear": 54.0,
                      "left": 30.0, "right": 30.0}}
REAR_CANDIDATES = {"LETRICK": [("9'-11\"", 9.9167), ("9'-1 1/8\"", 9.0938)]}
EPS = 0.05  # _COORD_EPS


def clusters_of(strokes):
    """Cluster raw vertical strokes into drawn lines (x within EPS)."""
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
        c["n_frags"] = len(merged)
        c["y_min"] = min(a for a, b in merged)
        c["y_max"] = max(b for a, b in merged)
        c["covered"] = sum(b - a for a, b in merged)
        c["gaps"] = [round(merged[i + 1][0] - merged[i][1], 2)
                     for i in range(len(merged) - 1)]
        del c["xs"], c["frags"]
    return out


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import (page_segments, _merge_collinear,
                               _joint_lines, _lateral_candidates,
                               wall_outline_from_segments)
    from routes.pdf_overlay import _best_ladder_spec
    import pdfplumber
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
        # real tapes on the live estimate (affect live scale seating)
        tapes = list(db.pdf_overlay_tapes.find({"estimate_id": eid})) \
            if "pdf_overlay_tapes" in db.list_collection_names() else []
        print(f"\n######## {house} pdf={pdf} run={run.get('_id')} "
              f"live_tapes={len(tapes)} ########")
        # ---- PAGE BOXES (pdf points + ocr raster dims) ----
        with pdfplumber.open(str(UPLOAD_DIR / pdf)) as pp:
            for i, pg in enumerate(pp.pages[:4], start=1):
                o = ot.get(str(i)) or {}
                print(f"  PAGEBOX p{i}: pdf {pg.width:.2f}x{pg.height:.2f} pt"
                      f" = {pg.width/72:.3f}x{pg.height/72:.3f} in"
                      f" | ocr raster {o.get('page_w')}x{o.get('page_h')} px")
        faces = derive_face_heights(ot)
        cache = {}
        for face in ("front", "rear", "left", "right"):
            r = faces.get(face) or {}
            spec = _best_ladder_spec(r)
            if not spec:
                print(f"\n==== {house} {face}: no ladder spec ====")
                continue
            pg = spec["page"]
            W, H = ot[pg]["page_w"], ot[pg]["page_h"]
            sy = spec.get("scale_y")
            ft = spec.get("ft")
            dy = abs(sy[1] - sy[0]) * 100.0 if sy else None
            print(f"\n==== {house} {face} p{pg} tier={spec.get('tier')} "
                  f"ft={ft} contested={spec.get('contested_rails')} ====")
            # ---- A. SCALE QUERY ----
            cands_ft = [(str(ft), ft)] if ft else []
            if face == "rear" and house in REAR_CANDIDATES:
                cands_ft = REAR_CANDIDATES[house]
            if dy:
                print(f"  SCALE drawn_gap dy={dy:.3f} y-% "
                      f"(scale_y={[round(v*100,3) for v in sy]})")
                for label, f_ in cands_ft:
                    fppy = f_ / dy
                    fppx = f_ / (dy / 100.0 * H) * W / 100.0
                    print(f"    candidate {label}={f_} ft: "
                          f"fpp_y={fppy:.5f} ft/y-%  "
                          f"fpp_x={fppx:.5f} ft/x-%")
                if not cands_ft:
                    print("    no real gap ft on this face — quotient "
                          "not derivable (drawn gap % reported above)")
            else:
                print("  SCALE: no scale_y on this face")
            # ---- B. X-RULER TRACE ----
            cand = next((c for c in (r.get("candidates") or [r])
                         if c.get("page") == pg), r)
            geo = cand.get("datum_geometry") or {}
            band = cand.get("band") or [0.0, 100.0]
            top_d, bot_d = geo.get("top_of_plate"), geo.get("first_floor")
            if not (top_d and bot_d and top_d.get("b0") is not None
                    and bot_d.get("b0") is not None):
                print("  TRACE: datum pair not located — no linework")
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
            print(f"  LINEWORK status={lw.get('status')} "
                  f"reason={lw.get('reason')} x_span={lw.get('x_span')} "
                  f"wall_corners={lw.get('wall_corners')} "
                  f"body={lw.get('body_x_span')} fence={x_fence}")
            # pre-merge kept raw verticals (module's own filters)
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
            horiz_raw = [s for s in keep
                         if abs(s["x1"] - s["x0"])
                         >= (s["bottom"] - s["top"])]
            vert_m = _merge_collinear(raw_v, "v", gap_tol)
            jogs = _joint_lines(horiz_raw, plate[1], floor[0])
            cands = _lateral_candidates(vert_m, jogs, plate, floor,
                                        gap_tol)
            pt_c = [c for c in cands if c.get("pt")] or cands
            if not pt_c:
                print("  TRACE: no candidates")
                continue
            cur_l = min(min(c["x_top"], c["x_bot"]) for c in pt_c)
            cur_r = max(max(c["x_top"], c["x_bot"]) for c in pt_c)
            fppx_map = {lbl: f_ / (dy / 100.0 * H) * W / 100.0
                        for lbl, f_ in cands_ft} if dy else {}
            fppx0 = list(fppx_map.values())[0] if fppx_map else None
            print(f"  CURRENT boundaries: L={cur_l:.3f} R={cur_r:.3f}"
                  + (f"  width={(cur_r-cur_l)*fppx0:.2f} ft" if fppx0
                     else ""))
            # datum-interval fragments: raw verticals with ink inside
            # [plate_top, floor_bottom]
            band_v = [s for s in raw_v
                      if s["bottom"] >= plate[0] and s["top"] <= floor[1]]
            cl = clusters_of(band_v)
            di = floor[1] - plate[0]
            for side, cx, sgn in (("L", cur_l, -1), ("R", cur_r, 1)):
                near = [c for c in cl
                        if (c["x"] - cx) * sgn >= -1.0]
                near.sort(key=lambda c: (c["x"] - cx) * sgn)
                show = near[:6]
                print(f"  {side}-BOUNDARY x={cx:.3f} — clusters from "
                      f"1%% inboard OUTWARD (datum interval "
                      f"{plate[0]:.2f}..{floor[1]:.2f} = {di:.2f}%):")
                for c in show:
                    d = (c["x"] - cx) * sgn
                    spans = (c["y_min"] <= plate[1]
                             and c["y_max"] >= floor[0]
                             and c["n_frags"] == 1)
                    covers = (c["y_min"] <= plate[1]
                              and c["y_max"] >= floor[0])
                    ptl = c["y_min"] >= plate[0] - gap_tol
                    ftd = f" ({d*fppx0:+.3f} ft)" if fppx0 else ""
                    print(f"    x={c['x']:.3f} Δ={d:+.3f}%{ftd} "
                          f"frags={c['n_frags']} "
                          f"y[{c['y_min']:.2f},{c['y_max']:.2f}] "
                          f"covered={c['covered']:.2f}% "
                          f"({c['covered']/di*100:.0f}% of interval) "
                          f"continuous={spans} reaches_both={covers} "
                          f"plate_term={ptl} gaps={c['gaps'][:4]}")
                # post-merge state of the same neighbourhood
                nearm = [v for v in vert_m
                         if (((v["x0"] + v["x1"]) / 2.0) - cx) * sgn
                         >= -1.0 and abs(((v["x0"] + v["x1"]) / 2.0)
                                         - cx) <= 1.5]
                for v in sorted(nearm, key=lambda v: (v["x0"] - cx) * sgn):
                    x = (v["x0"] + v["x1"]) / 2.0
                    spans = v["top"] <= plate[1] and v["bottom"] >= floor[0]
                    ptl = v["top"] >= plate[0] - gap_tol
                    print(f"    POST-MERGE x={x:.3f} Δ={(x-cx)*sgn:+.3f}% "
                          f"y[{v['top']:.2f},{v['bottom']:.2f}] "
                          f"spans={spans} plate_term={ptl}")
            # theoretical rule: outermost collinear cluster per side
            # (any ink inside the datum interval, inside fence), outer
            # edge, NO JOINING required
            if cl:
                th_l = min(cl, key=lambda c: c["x"])
                th_r = max(cl, key=lambda c: c["x"])
                print(f"  THEORETICAL (outermost collinear fragment, no "
                      f"joining): L={th_l['x']:.3f} "
                      f"(frags={th_l['n_frags']} "
                      f"covered={th_l['covered']:.2f}%) "
                      f"R={th_r['x']:.3f} (frags={th_r['n_frags']} "
                      f"covered={th_r['covered']:.2f}%)")
                for lbl, fx in fppx_map.items():
                    wth = (th_r["x"] - th_l["x"]) * fx
                    wcur = (cur_r - cur_l) * fx
                    sealed = SEALED.get(house, {}).get(face)
                    print(f"    @{lbl}: theoretical={wth:.2f} ft  "
                          f"current={wcur:.2f} ft  sealed={sealed}  "
                          f"moves_L={abs(th_l['x']-cur_l) > EPS} "
                          f"moves_R={abs(th_r['x']-cur_r) > EPS}")


main()
