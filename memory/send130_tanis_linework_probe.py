"""SEND-130 tanis line-work diagnostic — READ-ONLY. Where does the read
stop, per face? Five steps: CARVE → DATUM PAIR → SEGMENTS → FENCE →
OUTLINE. Nothing is written; no run, no estimate, no proposal.

Step 2 is also probed a second way: the carved band is re-rendered at a
higher scale and re-OCR'd, to separate "this drafter prints no datum
labels" from "the labels are printed but the page-scale OCR cannot read
them". Those are different findings.
"""
import os
import re
import sys

sys.path.insert(0, "/app/backend")
import numpy as np
import pypdfium2 as pdfium
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

from height_read import derive_face_heights
from linework_read import page_segments
from routes.ai_blueprint import _ocr_runs

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
DATUM_WORDS = ("PLATE", "FLOOR", "FOUNDATION", "GRADE", "SUBFLOOR",
               "CEILING", "TRUSS", "BEARING", "SLAB", "FINISH", "TOPOF",
               "T.O.", "FIRST", "SECOND", "WALKOUT")
RUN_PREFIX = "072e8c36"


def _band_ocr(pdf, page_idx, y0, y1, scale):
    page = pdfium.PdfDocument(pdf)[page_idx]
    bmp = page.render(scale=scale)
    img = bmp.to_pil()
    W, H = img.size
    crop = img.crop((0, int(H * y0 / 100.0), W, int(H * y1 / 100.0)))
    arr = np.asarray(crop.convert("RGB"))
    runs = _ocr_runs(arr)
    hits = [raw for _n, raw, _b in runs
            if any(w in re.sub(r"[^A-Z.]", "", raw.upper())
                   for w in DATUM_WORDS)]
    return len(runs), hits, crop.size


run = db.ai_blueprint_runs.find_one({"run_id": {"$regex": "^" + RUN_PREFIX}})
raw = (run.get("result") or {}).get("raw_ai") or {}
ot = raw.get("_ocr_text_by_page")
if not ot and raw.get("_ocr_text_ref"):
    ot = (db.ai_blueprint_ocr.find_one({"run_id": raw["_ocr_text_ref"]},
                                       {"pages": 1}) or {}).get("pages")
pdf = next("/app/backend/uploads/" + f["name"]
           for f in (run.get("source_files") or []) if f.get("kind") == "pdf")

faces = derive_face_heights(ot)
for face, res in faces.items():
    band = res.get("band")
    page = res.get("page")
    print("=" * 68)
    print(f"FACE {face.upper()}")
    print(f"  step 1 CARVE .......... {'OK' if band else 'FAILED'} "
          f"(page {page}, band {band})")
    if not band:
        print(f"  stops here: {res.get('refusal')}")
        continue
    cands = res.get("candidates") or [res]
    geo = (cands[0].get("datum_geometry") or {}) if cands else {}
    located = {k: bool(v) for k, v in geo.items()}
    print(f"  step 2 DATUM PAIR ..... "
          f"{'OK' if located.get('top_of_plate') and located.get('first_floor') else 'FAILED'} "
          f"(located: {located or 'none'})")
    segs = len(page_segments(pdf, int(page) - 1))
    print(f"  step 3 SEGMENTS ....... {'OK' if segs else 'FAILED'} "
          f"({segs} vector segments on p{page})")
    print(f"  step 4 FENCE .......... NOT REACHED (needs the datum extent)")
    print(f"  step 5 OUTLINE ........ NOT REACHED")
    print(f"  stops at step 2: {res.get('refusal')}")
    for scale in (2, 4, 6):
        n, hits, size = _band_ocr(pdf, int(page) - 1, band[0], band[1], scale)
        print(f"    re-OCR scale x{scale} ({size[0]}x{size[1]} px): "
              f"{n} runs in band, datum-word hits: {hits[:8] or 'NONE'}")
