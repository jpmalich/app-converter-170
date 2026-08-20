"""SEND-77 addendum — gable-trace under the same fence (report only)."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import (page_segments, wall_outline_from_segments,
                               gable_triangle_from_segments)
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
        print(f"=== {house} ===")
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
            gap_tol = max(top_d["b1"] - top_d["b0"],
                          bot_d["b1"] - bot_d["b0"])
            args = ((band[0], band[1]), (top_d["b0"], top_d["b1"]),
                    (bot_d["b0"], bot_d["b1"]), mask)
            lw = wall_outline_from_segments(segs, *args, x_fence=fence)
            if lw["status"] != "RESOLVED" or not lw.get("wall_corners"):
                print(f"  {face}: wall {lw['status']} — no gable trace")
                continue
            fenced = ([s for s in segs
                       if fence[0] - gap_tol <= min(s["x0"], s["x1"])
                       and max(s["x0"], s["x1"]) <= fence[1] + gap_tol]
                      if fence else segs)
            for label, ss in (("UNFENCED", segs), ("FENCED", fenced)):
                g = gable_triangle_from_segments(
                    ss, (band[0], band[1]), (top_d["b0"], top_d["b1"]),
                    lw["wall_corners"], lw["y_top"], mask)
                print(f"  {face} gable [{label}]: {g.get('status')} "
                      f"apex={g.get('apex')} reason={g.get('reason')}")

main()
