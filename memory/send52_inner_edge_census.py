"""SEND-52 item 3A — READ-ONLY inner-edge calibration. REPORT ONLY.

Measurement definition change (stated reason, not a tuned subtraction):
a label's INNER edge sits nearer where its leader anchors than its outer
edge does. Inner span = right edge of the LEFTMOST marker box → left edge
of the RIGHTMOST marker box. Same same-corner guard (overlapping extreme
boxes = single-ended = INDETERMINATE). Nothing here ships; nothing tunes
toward any sealed figure.
"""
import os
import re
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
from height_read import derive_face_heights  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

HOUSES = [
    ("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293",
     {"front": 54.0, "rear": 54.0, "left": 30.0, "right": 30.0}),
    ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332",
     {"front": 58.0, "rear": 58.0, "left": 30.0 + 2 / 12.0, "right": 33.0}),
]


def load_ot(eid):
    run = db.ai_blueprint_runs.find_one(
        {"estimate_id": eid, "status": "done"},
        {"result.raw_ai._ocr_text_by_page": 1, "run_id": 1},
        sort=[("created_at", -1)])
    raw = ((run or {}).get("result") or {}).get("raw_ai") or {}
    return raw.get("_ocr_text_by_page"), (run or {}).get("run_id")


def inner_span(markers):
    if not markers or len(markers) < 2:
        return None
    left = min(markers, key=lambda m: m[0])
    right = max(markers, key=lambda m: m[1])
    if left[1] > right[0]:
        return None
    return [round(left[1], 2), round(right[0], 2)]  # inner edges


def outer_span(markers):
    if not markers or len(markers) < 2:
        return None
    left = min(markers, key=lambda m: m[0])
    right = max(markers, key=lambda m: m[1])
    if left[1] > right[0]:
        return None
    return [round(left[0], 2), round(right[1], 2)]


def calib(r, ot):
    geo = r.get("datum_geometry") or {}
    page = ot.get(r.get("page")) or {}
    pw, ph = page.get("page_w"), page.get("page_h")
    if not pw or not ph:
        return None, "page px unknown"
    if r.get("status") == "DERIVED" and r.get("span_y"):
        dy = abs(r["span_y"][1] - r["span_y"][0])
        ft_per_px = r["ft"] / (dy / 100.0 * ph)
        return ft_per_px * pw / 100.0, f"height read {r['ft']} ft"
    best = None
    for g in r.get("gaps") or []:
        if g["status"] == "BOUND" and g.get("value_in"):
            best = g if (best is None or g["value_in"] > best["value_in"]) else best
    if best:
        m0 = re.search(r"@([\d.]+)", best["from"])
        m1 = re.search(r"@([\d.]+)", best["to"])
        if m0 and m1:
            dy = abs(float(m1.group(1)) - float(m0.group(1)))
            if dy > 0:
                ft_per_px = (best["value_in"] / 12.0) / (dy / 100.0 * ph)
                return (ft_per_px * pw / 100.0,
                        f"BOUND gap = {best['value_in']}\"")
    return None, "no evidence scale on this face"


def rows(r):
    return r.get("candidates") or [r]


for name, eid, truth in HOUSES:
    ot, run_id = load_ot(eid)
    if not ot:
        print(f"\n=== {name}: no persisted OCR ===")
        continue
    faces = derive_face_heights(ot)
    print(f"\n{'=' * 70}\n{name} (run {run_id}) — INNER-EDGE spans\n{'=' * 70}")
    for face in ("front", "rear", "left", "right"):
        r = faces.get(face) or {}
        for cand in rows(r):
            geo = cand.get("datum_geometry") or {}
            if not geo:
                print(f"\n-- {face.upper()}: no datum geometry")
                continue
            print(f"\n-- {face.upper()}  p{cand.get('page')}  status={cand.get('status')}")
            fppx, basis = calib(cand, ot)
            gt = truth[face]
            for key, label in (("first_floor", "FF"), ("top_of_plate", "TP")):
                d = geo.get(key)
                if not d:
                    print(f"   {label}: NOT LOCATED")
                    continue
                o, i = outer_span(d["markers"]), inner_span(d["markers"])
                if not i:
                    print(f"   {label}: INDETERMINATE (single-ended)")
                    continue
                line = (f"   {label}: outer {o[0]:.1f}→{o[1]:.1f} ({o[1]-o[0]:.1f}%)"
                        f"  inner {i[0]:.1f}→{i[1]:.1f} ({i[1]-i[0]:.1f}%)")
                if fppx:
                    wo = (o[1] - o[0]) * fppx
                    wi = (i[1] - i[0]) * fppx
                    line += (f"  → outer {wo:.2f} ft (res {wo-gt:+.2f})"
                             f"  INNER {wi:.2f} ft (res {wi-gt:+.2f})"
                             f"  [sealed {gt:.2f}]")
                else:
                    line += f"  → no scale ({basis})"
                print(line)
            if fppx:
                print(f"   scale basis: {basis}")
