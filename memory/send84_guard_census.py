"""SEND-84 — guard-case census: every dropped (non-pt spanning) stroke
and every kept boundary on both houses, classified under RULING CCC's
inapplicability guards: JOINED / no jog ink between the members /
endpoint names no reference / member carries 3+ strokes / crossing
only. Kept boundaries are singles — CCC takes nothing from them; they
are listed as controls with before/after identity."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

HOUSES = [
    ("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
    ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332"),
]


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import (page_segments, _merge_collinear,
                               _joint_lines, _ccc_end_ok, _COORD_EPS)
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
            xs = []
            for k in ("top_of_plate", "first_floor", "top_of_foundation"):
                for m in (geo.get(k) or {}).get("markers") or []:
                    xs.extend(m)
            fence = (min(xs), max(xs)) if len(xs) >= 2 else None
            y0, y1 = band
            keep = []
            for s in cache[idx]:
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
            jog_lines = _joint_lines(horiz, plate[1], floor[0])
            vert = _merge_collinear(vert, "v", gap_tol)
            pts, drops = [], []
            for s in vert:
                if (s["top"] <= plate[1] and s["bottom"] >= floor[0]):
                    x = (s["x0"] + s["x1"]) / 2.0
                    if s["top"] >= plate[0] - gap_tol:
                        pts.append(x)
                    else:
                        drops.append(x)
            if not drops and not pts:
                continue
            print(f"\n=== {house} {face} p{pg} ===")
            print(f"  KEPT (plate-terminated) boundaries: "
                  f"{[round(x, 2) for x in pts]} — singles carry no "
                  f"joint; CCC takes nothing from them")
            for p in drops:
                best = "no jog ink between the members"
                joined = None
                for w in pts:
                    lo, hi = sorted((w, p))
                    if hi - lo <= gap_tol:
                        continue
                    for ly, runs in jog_lines:
                        for r0, r1 in runs:
                            if r1 < lo - gap_tol or r0 > hi + gap_tol:
                                continue
                            if r0 < lo - gap_tol or r1 > hi + gap_tol:
                                best = min(best, "crossing only",
                                           key=len) if best.startswith(
                                    "no jog") else best
                                continue
                            if r1 - r0 < _COORD_EPS:
                                continue
                            lok = _ccc_end_ok(r0, lo, 1, ly, vert, True)
                            rok = _ccc_end_ok(r1, hi, -1, ly, vert, True)
                            if lok and rok:
                                joined = (w, ly)
                                break
                            # classify the nearer failure
                            through = [
                                (v["x0"] + v["x1"]) / 2.0 for v in vert
                                if v["top"] <= ly - _COORD_EPS
                                and v["bottom"] >= ly + _COORD_EPS]
                            for end, bnd, inw in ((r0, lo, 1),
                                                  (r1, hi, -1)):
                                if (end - bnd) * inw <= _COORD_EPS:
                                    continue
                                if any(abs(t - end) <= _COORD_EPS
                                       for t in through):
                                    a, b2 = sorted((bnd, end))
                                    if any(a + _COORD_EPS < t
                                           < b2 - _COORD_EPS
                                           for t in through):
                                        best = ("member carries 3+ "
                                                "strokes")
                                else:
                                    if best == ("no jog ink between "
                                                "the members"):
                                        best = ("endpoint names no "
                                                "reference")
                        if joined:
                            break
                    if joined:
                        break
                if joined:
                    print(f"  DROP x={p:.2f}: JOINED to wall "
                          f"{joined[0]:.2f} at drawn joint y="
                          f"{joined[1]:.2f}")
                else:
                    print(f"  DROP x={p:.2f}: REFUSED — {best}")


main()
