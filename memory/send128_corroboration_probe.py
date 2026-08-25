"""SEND-128 corroboration probe — READ-ONLY. For every face of all four
houses: is a LINE-WORK width available, what is it, and by how much does
it differ from the model's figure? Nothing is written: no proposal, no
run, no estimate. Uses the same building blocks propose_zones uses
(height_read.derive_face_heights + linework_read.wall_outline_from_segments),
so the figures are the pipeline's own, not a re-implementation.
"""
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

from height_read import derive_face_heights
from linework_read import page_segments, wall_outline_from_segments

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/backend/uploads")

RUNS = {"boni": "5df22e6d", "letrick": "725f8326",
        "tanis": "072e8c36", "dart": "ff0d596e"}
FACE_KEY = {"front": "front", "rear": "back", "left": "left",
            "right": "right"}


def _ocr(run):
    raw = ((run.get("result") or {}).get("raw_ai") or {})
    ot = raw.get("_ocr_text_by_page")
    if not ot and raw.get("_ocr_text_ref"):
        ref = db.ai_blueprint_ocr.find_one({"run_id": raw["_ocr_text_ref"]},
                                           {"pages": 1})
        ot = (ref or {}).get("pages")
    return ot if isinstance(ot, dict) else None


def _pdf(run):
    for f in (run.get("source_files") or []):
        if isinstance(f, dict) and f.get("kind") == "pdf":
            p = os.path.join(UPLOAD_DIR, str(f.get("name")))
            if os.path.exists(p):
                return p
    return None


def _linework(pdf, ot, cand, seg_cache):
    geo = cand.get("datum_geometry") or {}
    band = cand.get("band") or [0.0, 100.0]
    top_d, bot_d = geo.get("top_of_plate"), geo.get("first_floor")
    if not (top_d and bot_d and top_d.get("b0") is not None
            and bot_d.get("b0") is not None):
        return {"status": "NOT_ATTEMPTED",
                "reason": "datum pair not located on this drawing"}, None
    page = str(cand.get("page"))
    idx = int(page) - 1
    if idx not in seg_cache:
        seg_cache[idx] = page_segments(pdf, idx)
    pgd = (ot.get(page) or {})
    mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
             u["loc"]["x_pct"] + u["loc"]["w_pct"],
             u["loc"]["y_pct"] + u["loc"]["h_pct"])
            for u in (pgd.get("runs") or [])]
    fence_xs = []
    for dkey in ("top_of_plate", "first_floor", "top_of_foundation"):
        for mk in (geo.get(dkey) or {}).get("markers") or []:
            fence_xs.extend(mk)
    x_fence = (min(fence_xs), max(fence_xs)) if len(fence_xs) >= 2 else None
    lw = wall_outline_from_segments(
        seg_cache[idx], (band[0], band[1]),
        (top_d["b0"], top_d["b1"]), (bot_d["b0"], bot_d["b1"]),
        mask, x_fence=x_fence)
    # the face's own vertical scale: the datum span in feet over its
    # drawn pixel height, carried across to the horizontal by page ratio
    ft = cand.get("feet")
    if ft is None and cand.get("inches"):
        ft = float(cand["inches"]) / 12.0
    if ft is None:
        vals = [g.get("value_in") for g in (cand.get("gaps") or [])
                if g.get("from") == "TOP_OF_PLATE" and g.get("value_in")]
        if vals:
            ft = max(vals) / 12.0
    sy = (top_d["y"], bot_d["y"])
    fppx = None
    if ft and pgd.get("page_w") and pgd.get("page_h") and abs(sy[1] - sy[0]) > 0:
        fppx = (float(ft) / (abs(sy[1] - sy[0]) / 100.0 * pgd["page_h"])
                * pgd["page_w"] / 100.0)
    return lw, fppx


for house, pref in RUNS.items():
    run = db.ai_blueprint_runs.find_one({"run_id": {"$regex": "^" + pref}})
    est_id = run.get("estimate_id")
    if not _ocr(run):
        for alt in db.ai_blueprint_runs.find(
                {"estimate_id": est_id, "status": "done"}).sort("created_at", -1):
            if _ocr(alt):
                run = alt
                print(f"  (latest OCR-bearing run for this estimate: "
                      f"{alt['run_id'][:8]})")
                break
    ot, pdf = _ocr(run), _pdf(run)
    raw = (run.get("result") or {}).get("raw_ai") or {}
    model = {str(w.get("label")): w.get("width_ft")
             for w in (raw.get("walls") or []) if isinstance(w, dict)}
    ua = {str(w.get("label")) for w in (raw.get("walls") or [])
          if isinstance(w, dict) and w.get("_width_unattributed")}
    print("=" * 72)
    print(f"{house.upper()} · run {run['run_id'][:8]} · ocr {bool(ot)} · "
          f"pdf {bool(pdf)}")
    if not (ot and pdf):
        print("  no OCR store or no retained vector PDF — line-work "
              "NOT_ATTEMPTED on every face")
        continue
    faces = derive_face_heights(ot)
    seg_cache = {}
    for face, res in faces.items():
        key = FACE_KEY.get(face, face)
        mv = model.get(key)
        cands = res.get("candidates") or ([res] if res.get("band") else [])
        if not cands:
            print(f"  {key:<6} model={mv} | line-work NOT_ATTEMPTED "
                  f"({str(res.get('refusal'))[:70]})")
            continue
        for c in cands:
            lw, fppx = _linework(pdf, ot, c, seg_cache)
            st = lw.get("status")
            if st != "RESOLVED" or not fppx:
                print(f"  {key:<6} p{c.get('page')} model={mv} | "
                      f"line-work {st}"
                      f"{'' if fppx else ' (no face scale)'}: "
                      f"{str(lw.get('reason'))[:70]}")
                continue
            sil = round((lw["x_span"][1] - lw["x_span"][0]) * fppx, 2)
            wc = lw.get("wall_corners") or lw.get("body_x_span")
            wall = round((wc[1] - wc[0]) * fppx, 2) if wc else None
            d = (round(abs(float(mv) - wall), 2)
                 if (wall is not None and mv) else None)
            print(f"  {key:<6} p{c.get('page')} model={mv} | wall-only="
                  f"{wall} silhouette={sil} | Δ={d} ft"
                  f"{' | face width UNATTRIBUTED' if key in ua else ''}")
