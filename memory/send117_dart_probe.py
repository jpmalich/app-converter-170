"""SEND-117 dart probe — READ-ONLY. Rotates COPIES of dart's stored page
images per the detector, re-OCRs, rebuilds a store, and reports what the
deterministic layers give: faces carved, heights, schedule jurisdiction,
refusal survival. NO run rewritten, NO estimate touched, NO model call.
NOT a scored run — Howard's seal and predictions come first."""
import copy
import io
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

import ocr_geometry  # noqa: E402
import page_rotation  # noqa: E402
from routes.ai_blueprint import (_aggregate_to_hover_shape, _map_rot_box,
                                 _ocr_runs)  # noqa: E402
from height_read import face_bands  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
EID = "7caeff94-7167-4ca6-8a03-4808e9dd57a9"
run = db.ai_blueprint_runs.find_one({"estimate_id": EID, "status": "done"})
names = [s for s in run["page_paths"].split(",") if s.strip()]
raw = copy.deepcopy((run.get("result") or {}).get("raw_ai") or {})
if not raw.get("_ocr_text_by_page") and raw.get("_ocr_text_ref"):
    raw["_ocr_text_by_page"] = (db.ai_blueprint_ocr.find_one(
        {"run_id": raw["_ocr_text_ref"]}, {"pages": 1}) or {}).get("pages")

store = {}
rot_report = []
for i, name in enumerate(names):
    pg = str(i + 1)
    img = Image.open(f"/app/backend/uploads/{name}").convert("RGB")
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=88)
    v = page_rotation.detect_image_bytes(buf.getvalue(), _ocr_runs)
    rot_report.append((pg, v["verdict"], v.get("rotation_ccw"),
                       v["upright_share"]))
    if v["verdict"] == "ROTATED":
        img = Image.open(io.BytesIO(page_rotation.rotate_image_bytes(
            buf.getvalue(), v["rotation_ccw"])))
    arr = np.array(img.convert("RGB"))
    w, h = img.size
    pw, ph = max(w, 1), max(h, 1)

    def _doc(r, src, rect):
        loc = {"x_pct": round(rect[0] / pw * 100, 2),
               "y_pct": round(rect[1] / ph * 100, 2),
               "w_pct": round(max(rect[2] - rect[0], 1) / pw * 100, 2),
               "h_pct": round(max(rect[3] - rect[1], 1) / ph * 100, 2)}
        return {"norm": r[0], "raw": r[1], "loc": loc, "src": src,
                "axis": ocr_geometry.axis_class(
                    loc, ocr_geometry.glyph_count(r[1]))}

    runs = [_doc(r, "upright", r[2]) for r in _ocr_runs(arr)]
    for k, src in ((1, "rot90"), (3, "rot270")):
        runs.extend(_doc(r, src, _map_rot_box(r[2], k, w, h))
                    for r in _ocr_runs(np.rot90(arr, k)))
    store[pg] = {"page_w": int(w), "page_h": int(h), "runs": runs}

print("== detection (per page) ==")
for t in rot_report:
    print("  p%s: %s rot=%s share=%s" % t)

print("\n== face bands (the carve, carver untouched) ==")
for pg in sorted(store, key=int):
    b = face_bands(store[pg]["runs"])
    if b:
        print(f"  p{pg}: {b}")

raw2 = copy.deepcopy(raw)
raw2["_ocr_text_by_page"] = store
raw2.pop("_schedule_count_unread", None)
m = _aggregate_to_hover_shape(raw2)
print("\n== aggregation after normalization ==")
print("  gross:", m.get("siding_sqft"),
      "| field:", m.get("siding_with_openings_sqft"))
for wl in raw2.get("walls") or []:
    print(f"  {wl.get('label')}: w={wl.get('width_ft')} h={wl.get('height_ft')}"
          f" src={str(wl.get('height_ft_source'))[:52]}")
fnd = m.get("_faces_not_derivable") or []
print("  faces still refused:", len(fnd),
      sorted({str(f.get('elevation') or f.get('label')) for f in fnd
              if isinstance(f, dict)}))
su = raw2.get("_schedule_count_unread") or []
print("  schedule jurisdiction rows unread:", len(su), su[:6])
rec = raw2.get("_schedule_rows_recovered") or []
print("  rows recovered:", len(rec))
d = m.get("_openings_deduction") or {}
sizes = [r for r in (d.get("refused") or []) if "size" in str(r.get("why"))]
print("  sizes still refused:", len(sizes),
      sorted(r.get("mark") for r in sizes))
print("  deduction record keys:", sorted(d.keys()))
