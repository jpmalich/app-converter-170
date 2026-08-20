"""SEND-77 — X-SCOPING CURE dry run (REPORT ONLY, writes nothing).

BEFORE/AFTER on all 8 faces, both houses. The fence = the face's own
datum-line extent: union of marker x-boxes on the governing datum
lines (TOP_OF_PLATE + FIRST_FLOOR [+ TOF when it is the bottom box]).
FENCE CONTAINMENT mirrors BAND CONTAINMENT: a qualifying stroke lies
entirely inside the fence (± the drawing's own line-weight tolerance).
Also reports the actual x-gap between the face's fence edge and the
nearest foreign spanning stroke, against the fence width.
Run from /app/backend."""
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
from pymongo import MongoClient  # noqa: E402

SEALED = {  # checks, never targets (wall + known projections stated)
    "LETRICK": {"front": (54.0, "54' wall"),
                "rear": (54.0, "54' wall (contested scale)"),
                "left": (32.7, "30' wall + 2'-7\" projection"),
                "right": (32.7, "30' wall + 2'-7\" chimney IF read")},
    "BONI": {"front": (None, "no evidence scale"),
             "rear": (None, "no evidence scale"),
             "left": (30.17, "30'-2\""), "right": (33.0, "33'")},
}
HOUSES = [
    ("LETRICK", "264b6230-5d0f-49ea-b07d-8d33a537f293"),
    ("BONI", "65bcb89d-8291-4b84-920c-7b503273f332"),
]


def fence_from_geo(geo):
    xs = []
    for key in ("top_of_plate", "first_floor", "top_of_foundation"):
        for m in (geo.get(key) or {}).get("markers") or []:
            xs.extend(m)
    if len(xs) < 2:
        return None
    return (min(xs), max(xs))


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
            print("  no persisted OCR — NOT ATTEMPTED")
            continue
        pdf = next((f["name"] for f in run.get("source_files") or []
                    if f.get("kind") == "pdf"), None)
        if not pdf or not (UPLOAD_DIR / pdf).exists():
            print("  no vector source — NOT ATTEMPTED")
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
                      "located (before AND after — the fence needs the "
                      "same datums)")
                continue
            idx = int(pg) - 1
            if idx not in cache:
                cache[idx] = page_segments(str(UPLOAD_DIR / pdf), idx)
            segs = cache[idx]
            mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
                     u["loc"]["x_pct"] + u["loc"]["w_pct"],
                     u["loc"]["y_pct"] + u["loc"]["h_pct"])
                    for u in (ot.get(pg) or {}).get("runs") or []]
            args = ((band[0], band[1]), (top_d["b0"], top_d["b1"]),
                    (bot_d["b0"], bot_d["b1"]), mask)
            gap_tol = max(top_d["b1"] - top_d["b0"],
                          bot_d["b1"] - bot_d["b0"])
            before = wall_outline_from_segments(segs, *args)
            fence = fence_from_geo(geo)
            if fence is None:
                print(f"  {face:<6} p{pg} fence: NOT DERIVABLE "
                      "(fewer than 2 datum markers) — cure cannot "
                      "apply; BEFORE stands")
                after = before
            else:
                fenced = [s for s in segs
                          if fence[0] - gap_tol
                          <= min(s["x0"], s["x1"])
                          and max(s["x0"], s["x1"])
                          <= fence[1] + gap_tol]
                after = wall_outline_from_segments(fenced, *args)

            def fmt(lw):
                if lw["status"] != "RESOLVED":
                    return f"{lw['status']} — {lw['reason']}"
                ft = "?"
                spec_ft = (spec or {}).get("ft")
                sy = (spec or {}).get("scale_y")
                if spec_ft and sy:
                    W, H = ot[pg]["page_w"], ot[pg]["page_h"]
                    fpp = spec_ft / (abs(sy[1] - sy[0]) * H)
                    ft = round((lw["x_span"][1] - lw["x_span"][0])
                               / 100.0 * W * fpp, 2)
                sealed, why = SEALED[house].get(face) or (None, "")
                res = (f" residual {round(ft - sealed, 2):+} vs {why}"
                       if sealed and ft != "?" else
                       (f" ({why})" if why else ""))
                return (f"RESOLVED x {lw['x_span']} "
                        f"v={lw['n_vertices']} width_ft={ft}{res}")

            changed = ((before.get("status"), before.get("x_span"),
                        before.get("n_vertices"))
                       != (after.get("status"), after.get("x_span"),
                           after.get("n_vertices")))
            print(f"  {face:<6} p{pg}")
            print(f"    BEFORE: {fmt(before)}")
            print(f"    AFTER : {fmt(after)}"
                  + ("   << CHANGE" if changed else "   (unchanged)"))
            if fence:
                # gap analysis: nearest in-band foreign vertical stroke
                # outside the fence vs the fence width
                y0, y1 = band
                foreign = []
                for s in segs:
                    t, b = min(s["top"], s["bottom"]), max(s["top"],
                                                           s["bottom"])
                    if t < y0 or b > y1:
                        continue
                    if abs(s["x1"] - s["x0"]) >= (b - t):
                        continue  # horizontal
                    if (b - t) < (bot_d["b0"] - top_d["b1"]) * 0.5:
                        continue  # short detail, not a spanning stroke
                    mx = (s["x0"] + s["x1"]) / 2.0
                    if mx < fence[0] - gap_tol or mx > fence[1] + gap_tol:
                        foreign.append(mx)
                W = ot[pg]["page_w"]
                fw = fence[1] - fence[0]
                if foreign:
                    nearest = min(foreign,
                                  key=lambda x: min(abs(x - fence[0]),
                                                    abs(x - fence[1])))
                    gap = min(abs(nearest - fence[0]),
                              abs(nearest - fence[1]))
                    print(f"    fence x [{fence[0]:.1f},{fence[1]:.1f}]%"
                          f" (w={fw:.1f}%) · nearest foreign spanning"
                          f" stroke at {nearest:.1f}% · gap"
                          f" {gap:.1f}% of page"
                          f" ({gap / fw * 100:.0f}% of fence width)")
                else:
                    print(f"    fence x [{fence[0]:.1f},{fence[1]:.1f}]%"
                          f" (w={fw:.1f}%) · no foreign spanning"
                          " strokes in band — fence excludes nothing"
                          " here")


main()
