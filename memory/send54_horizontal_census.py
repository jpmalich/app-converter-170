"""SEND-54 — READ-ONLY horizontal-rail census. REPORT ONLY, DO NOT BUILD.

Question: does each elevation print its OWN horizontal width dimension?
Uses only that face's title-carved band (inside Ruling AAA). Where a face
carries BOTH a horizontal dim and a determinate datum span, the leader
offset becomes derivable from that face alone: measured span − dim value
at that face's own scale.
"""
import os
import re
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
from height_read import derive_face_heights, elevation_page_faces  # noqa: E402
from ocr_geometry import (normalize_marks, is_dimension_like, axis_class,  # noqa: E402
                          glyph_count, merge_positions, _member_inches)

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


def horizontal_rails(runs, y0, y1):
    out = []
    for r in runs:
        if not is_dimension_like(normalize_marks(r["raw"])):
            continue
        if axis_class(r["loc"], glyph_count(r["raw"])) != "HORIZONTAL":
            continue
        cy = r["loc"]["y_pct"] + r["loc"]["h_pct"] / 2
        if y0 <= cy <= y1:
            out.append(r)
    return out


def face_scale(r, ot):
    """ft per x-percent from THIS face's own evidence (height read or a
    BOUND datum gap) — same bases as the earlier censuses."""
    page = ot.get(r.get("page")) or {}
    pw, ph = page.get("page_w"), page.get("page_h")
    if not pw or not ph:
        return None, "page px unknown"
    if r.get("status") == "DERIVED" and r.get("span_y"):
        dy = abs(r["span_y"][1] - r["span_y"][0])
        return (r["ft"] / (dy / 100.0 * ph)) * pw / 100.0, \
            f"height read {r['ft']} ft"
    best = None
    for g in r.get("gaps") or []:
        if g["status"] == "BOUND" and g.get("value_in"):
            best = g if (best is None or g["value_in"] > best["value_in"]) else best
    if best:
        m0 = re.search(r"@([\d.]+)", best["from"])
        m1 = re.search(r"@([\d.]+)", best["to"])
        if m0 and m1 and abs(float(m1.group(1)) - float(m0.group(1))) > 0:
            dy = abs(float(m1.group(1)) - float(m0.group(1)))
            return ((best["value_in"] / 12.0) / (dy / 100.0 * ph)) * pw / 100.0, \
                f"BOUND gap {best['value_in']}\""
    return None, "no evidence scale on this face"


for name, eid, truth in HOUSES:
    ot, run_id = load_ot(eid)
    if not ot:
        print(f"\n=== {name}: no persisted OCR ===")
        continue
    faces = derive_face_heights(ot)
    pages = elevation_page_faces(ot)
    print(f"\n{'=' * 72}\n{name} (run {run_id}) — HORIZONTAL rails per face band\n{'=' * 72}")
    for face in ("front", "rear", "left", "right"):
        r = faces.get(face) or {}
        cands = r.get("candidates") or [r]
        for cand in cands:
            pg = cand.get("page")
            if not pg:
                print(f"\n-- {face.upper()}: no evaluated band")
                continue
            band = cand.get("band")
            y0, y1 = band
            runs = merge_positions(ot[pg].get("runs") or [])
            hz = horizontal_rails(runs, y0, y1)
            print(f"\n-- {face.upper()}  p{pg}  band y {y0}→{y1}  "
                  f"status={cand.get('status')}")
            fppx, basis = face_scale(cand, ot)
            geo = cand.get("datum_geometry") or {}
            spans = {k: d["span_x"] for k, d in geo.items() if d.get("span_x")}
            if not hz:
                print("   HORIZONTAL dims in band: NONE")
            for h in hz:
                loc = h["loc"]
                inches = _member_inches(h["raw"])
                ft = inches / 12.0 if inches is not None else None
                box = (f"x {loc['x_pct']:.1f}→{loc['x_pct']+loc['w_pct']:.1f} "
                       f"y {loc['y_pct']:.1f}→{loc['y_pct']+loc['h_pct']:.1f}")
                line = f"   HZ: {h['raw']!r} = {ft if ft is None else round(ft,2)} ft  [{box}]"
                gt = truth[face]
                if ft is not None:
                    line += ("  ← reads as OVERALL WIDTH" if abs(ft - gt) < 0.51
                             else "")
                print(line)
            det = ", ".join(f"{k}:{v[0]:.1f}→{v[1]:.1f}" for k, v in spans.items()) or "NONE"
            print(f"   determinate datum span(s): {det}")
            both = bool(hz) and bool(spans)
            print(f"   carries BOTH horizontal dim AND determinate span: "
                  f"{'YES' if both else 'no'}")
            if both and fppx:
                for h in hz:
                    inches = _member_inches(h["raw"])
                    if inches is None:
                        continue
                    ft = inches / 12.0
                    for k, v in spans.items():
                        span_ft = (v[1] - v[0]) * fppx
                        print(f"   leader-offset candidate ({k} vs "
                              f"{h['raw']!r}): span {span_ft:.2f} ft − dim "
                              f"{ft:.2f} ft = {span_ft - ft:+.2f} ft  "
                              f"(scale: {basis})")
