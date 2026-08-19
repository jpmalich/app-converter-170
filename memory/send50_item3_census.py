"""SEND-50 item 3 — READ-ONLY census: datum x-spans vs current proposal
width, with the ft calibration column. No writes anywhere.

Scale bases (evidence only, no invention):
  - DERIVED face: the height read's own scale (ft over the datum-pair y gap)
  - refusing face: the largest BOUND gap between two datum lines (a
    dimensioned rail bound to that pair) — else INDETERMINATE
"""
import os
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
        {"result.raw_ai._ocr_text_by_page": 1,
         "result.raw_ai._ocr_text_ref": 1, "run_id": 1},
        sort=[("created_at", -1)])
    raw = ((run or {}).get("result") or {}).get("raw_ai") or {}
    ot = raw.get("_ocr_text_by_page")
    if not ot and raw.get("_ocr_text_ref"):
        ref = db.ai_blueprint_ocr.find_one(
            {"run_id": raw["_ocr_text_ref"]}, {"pages": 1})
        ot = (ref or {}).get("pages")
    return ot, (run or {}).get("run_id")


def face_rows(r):
    """One row (or candidate rows) per face result."""
    if "candidates" in r:
        return r["candidates"]
    return [r] if r.get("datum_geometry") is not None or r.get("page") else []


def calib(r, ot):
    """(ft_per_pct_x, basis) or (None, reason)."""
    geo = r.get("datum_geometry") or {}
    page = ot.get(r.get("page")) or {}
    pw, ph = page.get("page_w"), page.get("page_h")
    if not pw or not ph:
        return None, "page px unknown"
    if r.get("status") == "DERIVED" and r.get("span_y"):
        dy = abs(r["span_y"][1] - r["span_y"][0])
        if dy <= 0:
            return None, "zero y-span"
        ft_per_px = r["ft"] / (dy / 100.0 * ph)
        return ft_per_px * pw / 100.0, f"height read {r['ft']} ft over datum pair"
    best = None
    for g in r.get("gaps") or []:
        if g["status"] == "BOUND" and g.get("value_in"):
            best = g if (best is None or g["value_in"] > best["value_in"]) else best
    if best:
        ys = {}
        for key in ("top_of_plate", "first_floor"):
            if key in geo:
                ys[key.upper()] = geo[key]["y"]
        import re
        m0 = re.search(r"@([\d.]+)", best["from"])
        m1 = re.search(r"@([\d.]+)", best["to"])
        if m0 and m1:
            dy = abs(float(m1.group(1)) - float(m0.group(1)))
            if dy > 0:
                ft_per_px = (best["value_in"] / 12.0) / (dy / 100.0 * ph)
                return (ft_per_px * pw / 100.0,
                        f"BOUND gap {best['from']}→{best['to']} = {best['value_in']}\"")
    return None, "no derived height and no BOUND datum gap on this face"


def show(name, eid, truth):
    ot, run_id = load_ot(eid)
    if not ot:
        print(f"\n=== {name}: no persisted OCR ===")
        return
    faces = derive_face_heights(ot)
    print(f"\n{'=' * 74}\n{name} (run {run_id})\n{'=' * 74}")
    for face in ("front", "rear", "left", "right"):
        r = faces.get(face) or {}
        for cand in face_rows(r) or [r]:
            geo = cand.get("datum_geometry") or {}
            page = ot.get(cand.get("page")) or {}
            pw = page.get("page_w")
            print(f"\n-- {face.upper()}  p{cand.get('page')}  "
                  f"status={cand.get('status') or r.get('status')}")
            for key, label in (("first_floor", "FIRST FLOOR"),
                               ("top_of_plate", "TOP OF PLATE")):
                d = geo.get(key)
                if not d:
                    print(f"   {label}: NOT LOCATED")
                    continue
                marks = " ".join(f"[{m[0]:.1f}..{m[1]:.1f}]" for m in d["markers"])
                span = d["span_x"]
                s = (f"span {span[0]:.1f}→{span[1]:.1f} ({span[1]-span[0]:.1f}%)"
                     if span else "INDETERMINATE (single marker)")
                print(f"   {label}: y={d['y']}  markers({len(d['markers'])}): {marks}  → {s}")
            # current proposal box (today: DERIVED faces only, x 2..98%)
            if cand.get("status") == "DERIVED" and cand.get("span_y"):
                sy = cand["span_y"]
                print(f"   CURRENT PROPOSAL: x=2.0→98.0 (96.0%)  "
                      f"y={sy[0]}→{sy[1]}")
            else:
                print("   CURRENT PROPOSAL: NONE (face not DERIVED)")
            fppx, basis = calib(cand, ot)
            gt = truth.get(face)
            if fppx is None:
                print(f"   CALIBRATION: INDETERMINATE — {basis}")
                continue
            print(f"   scale basis: {basis}")
            for key, label in (("first_floor", "FF"), ("top_of_plate", "TP")):
                d = geo.get(key)
                if d and d["span_x"]:
                    w = (d["span_x"][1] - d["span_x"][0]) * fppx
                    print(f"   IMPLIED WIDTH ({label} span): {w:.2f} ft   "
                          f"(sealed: {gt:.2f} ft, offset {w - gt:+.2f} ft)")
            cur_w = 96.0 * fppx
            print(f"   IMPLIED WIDTH (current proposal 96%): {cur_w:.2f} ft   "
                  f"(sealed: {gt:.2f} ft, offset {cur_w - gt:+.2f} ft)")


for name, eid, truth in HOUSES:
    show(name, eid, truth)
