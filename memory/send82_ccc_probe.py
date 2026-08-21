"""SEND-82 probe — RULING CCC joint anatomy (report only, wires nothing).

For every face on both houses:
  A. every chain joint the system CURRENTLY ACCEPTS — its jog stroke,
     own length, the gap it bridges, endpoint shortfalls;
  B. every CANDIDATE projection shoulder: (plate-terminated wall line,
     dropped non-pt spanning stroke) pairs and every horizontal lying
     in the gap region between them;
  C. verdicts under three formalizations of "a spanning member must
     span": literal (allowance = line-weight _COORD_EPS), half-gap
     (own length >= gap/2, i.e. spans more than it misses), and
     box-tol (today's gap_tol end test, the status quo).
Controls: kept boundaries participate only as pair members — CCC
gates joints, it takes nothing from a kept single."""
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
                   mask, fence, _merge_collinear)


EPS = 0.03  # linework_read._COORD_EPS — the module's line-weight


def verdicts(length, gap):
    lit = length >= gap - 2 * EPS
    half = length >= gap / 2.0
    return (f"CCC-literal={'PASS' if lit else 'fail'} "
            f"halfgap={'PASS' if half else 'fail'} "
            f"len/gap={length / gap * 100:.0f}%")


def main():
    for (house, face, segs, band, plate, floor, mask, fence,
         _merge_collinear) in face_ctx():
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
        jog_h = [h for h in horiz
                 if plate[1] < (h["top"] + h["bottom"]) / 2.0 < floor[0]]

        # replicate _lateral_candidates to capture joint anatomy
        singles, tops, bots = [], [], []
        for s in vert:
            reach_top = s["top"] <= plate[1] and s["bottom"] >= plate[0]
            reach_bot = s["bottom"] >= floor[0] and s["top"] <= floor[1]
            span_top = s["top"] <= plate[1]
            span_bot = s["bottom"] >= floor[0]
            if span_top and span_bot:
                x = (s["x0"] + s["x1"]) / 2.0
                singles.append({"x": x, "pt": s["top"] >= plate[0] - gap_tol,
                                "s": s})
            elif reach_top and s["top"] >= plate[0] - gap_tol:
                tops.append(s)
            elif reach_bot:
                bots.append(s)
        printed = False

        def hdr():
            nonlocal printed
            if not printed:
                print(f"\n=== {house} {face} (gap_tol={gap_tol:.2f}, "
                      f"EPS={EPS}) ===")
                printed = True

        # A. accepted fragment-chain joints (today's rule)
        for a in tops:
            xa = (a["x0"] + a["x1"]) / 2.0
            for b in bots:
                xb = (b["x0"] + b["x1"]) / 2.0
                if abs(a["bottom"] - b["top"]) > gap_tol:
                    continue
                lo, hi = min(xa, xb), max(xa, xb)
                if hi - lo <= gap_tol:
                    continue
                jy = (a["bottom"] + b["top"]) / 2.0
                for h in jog_h:
                    hy = (h["top"] + h["bottom"]) / 2.0
                    if abs(hy - jy) > gap_tol:
                        continue
                    h0, h1 = min(h["x0"], h["x1"]), max(h["x0"], h["x1"])
                    if abs(h0 - lo) <= gap_tol and abs(h1 - hi) <= gap_tol:
                        hdr()
                        gap = hi - lo
                        L = h1 - h0
                        print(f"  ACCEPTED-TODAY chain {lo:.2f}<->{hi:.2f}"
                              f" jog y={hy:.2f} x[{h0:.2f},{h1:.2f}] "
                              f"len={L:.2f} gap={gap:.2f} "
                              f"shortfalls={abs(h0 - lo):.2f}/"
                              f"{abs(h1 - hi):.2f} -> {verdicts(L, gap)}")
                        break

        # B. candidate projection shoulders: pt single x non-pt single
        pts = [c for c in singles if c["pt"]]
        drops = [c for c in singles if not c["pt"]]
        if pts and drops:
            for w in pts:
                for p in drops:
                    lo, hi = min(w["x"], p["x"]), max(w["x"], p["x"])
                    if hi - lo <= gap_tol:
                        continue
                    gap = hi - lo
                    region = [h for h in jog_h
                              if min(h["x0"], h["x1"]) >= lo - gap_tol
                              and max(h["x0"], h["x1"]) <= hi + gap_tol]
                    for h in region:
                        h0 = min(h["x0"], h["x1"])
                        h1 = max(h["x0"], h["x1"])
                        L = h1 - h0
                        end_ok = (abs(h0 - lo) <= gap_tol
                                  and abs(h1 - hi) <= gap_tol)
                        hdr()
                        hy = (h["top"] + h["bottom"]) / 2.0
                        # nearest vertical ink to each end at this y
                        def near_ink(xend):
                            best = None
                            for v in vert:
                                if not (min(v["top"], v["bottom"]) - gap_tol
                                        <= hy <= max(v["top"], v["bottom"])
                                        + gap_tol):
                                    continue
                                d = abs((v["x0"] + v["x1"]) / 2.0 - xend)
                                if best is None or d < best:
                                    best = d
                            return best
                        print(f"  SHOULDER-CANDIDATE wall={w['x']:.2f} "
                              f"proj={p['x']:.2f} jog y={hy:.2f} "
                              f"x[{h0:.2f},{h1:.2f}] len={L:.2f} "
                              f"gap={gap:.2f} shortfalls="
                              f"{abs(h0 - lo):.2f}/{abs(h1 - hi):.2f} "
                              f"end-test(gap_tol)="
                              f"{'PASS' if end_ok else 'fail'} "
                              f"nearest-V-ink-at-ends="
                              f"{near_ink(h0)}/{near_ink(h1)} "
                              f"-> {verdicts(L, gap)}")


main()
