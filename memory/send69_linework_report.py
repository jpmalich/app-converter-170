"""SEND-69 — line-work read REPORT (report only, writes nothing).

Per face, both houses: RESOLVED/INDETERMINATE, polygon vertex count,
width in feet at that face's own scale, residual against Howard's
sealed readings (checks, never targets). Run from /app/backend."""
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from pymongo import MongoClient  # noqa: E402

SEALED = {  # checks, never targets (Howard's sealed readings)
    "LETRICK": {"front": 54.0, "rear": 54.0, "left": 30.0, "right": 30.0},
    "BONI": {"front": 58.0, "rear": 58.0,
             "left": 30.0 + 2 / 12.0, "right": 33.0},
}
HOUSES = [
    ("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
    ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332"),
]


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    from linework_read import page_segments, wall_outline_from_segments
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
        print(f"\n=== {house} ===")
        if not ot:
            print("  no persisted OCR on the latest done run — "
                  "line-work NOT ATTEMPTED")
            continue
        pdf = next((f["name"] for f in run.get("source_files") or []
                    if f.get("kind") == "pdf"), None)
        if not pdf or not (UPLOAD_DIR / pdf).exists():
            print("  no single-PDF vector source retained — "
                  "line-work NOT ATTEMPTED")
            continue
        faces = derive_face_heights(ot)
        cache = {}
        for face, r in faces.items():
            spec = _best_ladder_spec(r)
            cand = next((c for c in (r.get("candidates") or [r])
                         if spec and c.get("page") == spec["page"]), r)
            geo = cand.get("datum_geometry") or {}
            band = cand.get("band")
            pg = cand.get("page")
            top_d = geo.get("top_of_plate")
            bot_d = geo.get("first_floor")
            if not (pg and band and top_d and bot_d
                    and top_d.get("b0") is not None
                    and bot_d.get("b0") is not None):
                print(f"  {face:<6} NOT_ATTEMPTED — datum pair not "
                      "located on this drawing")
                continue
            idx = int(pg) - 1
            if idx not in cache:
                cache[idx] = page_segments(str(UPLOAD_DIR / pdf), idx)
            mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
                     u["loc"]["x_pct"] + u["loc"]["w_pct"],
                     u["loc"]["y_pct"] + u["loc"]["h_pct"])
                    for u in (ot.get(pg) or {}).get("runs") or []]
            lw = wall_outline_from_segments(
                cache[idx], (band[0], band[1]),
                (top_d["b0"], top_d["b1"]),
                (bot_d["b0"], bot_d["b1"]), mask)
            if lw["status"] != "RESOLVED":
                print(f"  {face:<6} p{pg} INDETERMINATE — {lw['reason']}")
                continue
            ft = res = ""
            spec_ft = (spec or {}).get("ft")
            sy = (spec or {}).get("scale_y")
            if spec_ft and sy:
                W = ot[pg]["page_w"]
                H = ot[pg]["page_h"]
                fpp = spec_ft / (abs(sy[1] - sy[0]) * H)
                ft = round((lw["x_span"][1] - lw["x_span"][0])
                           / 100.0 * W * fpp, 2)
                sealed = SEALED[house].get(face)
                if sealed:
                    res = f" residual {round(ft - sealed, 2):+} ft vs sealed {sealed}"
            print(f"  {face:<6} p{pg} RESOLVED x {lw['x_span']} "
                  f"vertices={lw['n_vertices']} width_ft={ft}{res}")
            if lw["n_vertices"] > 4:
                print(f"         >4 vertices — steps found (evidence of "
                      "a real read)")


main()
