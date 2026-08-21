"""SEND-84 — RULING CCC move-check (all eight faces, both houses).

BEFORE = HEAD's linework_read (old gap_tol joint law), AFTER = the
wired RULING CCC. Fence applied via x_fence exactly as the live
propose does. Three numbers per resolving face: silhouette width,
implied wall width (wall_corners), sealed plan depth (checks, never
targets). Plus: fixed-point verdicts and the guard-case census of the
dropped strokes and kept boundaries."""
import os, sys
import importlib.util
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

spec_old = importlib.util.spec_from_file_location(
    "linework_old", "/tmp/linework_old_send84.py")
linework_old = importlib.util.module_from_spec(spec_old)
spec_old.loader.exec_module(linework_old)

SEALED = {  # checks, never targets
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


def main():
    from height_read import derive_face_heights
    from config import UPLOAD_DIR
    import linework_read as lw_new
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
        print(f"\n===== {house} =====")
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
            band, pg = cand.get("band"), cand.get("page")
            top_d, bot_d = geo.get("top_of_plate"), geo.get("first_floor")
            if not (pg and band and top_d and bot_d
                    and top_d.get("b0") is not None
                    and bot_d.get("b0") is not None):
                print(f"  {face:<6} NOT_ATTEMPTED — datum pair not located")
                continue
            idx = int(pg) - 1
            if idx not in cache:
                cache[idx] = lw_new.page_segments(
                    str(UPLOAD_DIR / pdf), idx)
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
            args = ((band[0], band[1]), (top_d["b0"], top_d["b1"]),
                    (bot_d["b0"], bot_d["b1"]), mask)
            before = linework_old.wall_outline_from_segments(
                segs, *args, x_fence=fence)
            after = lw_new.wall_outline_from_segments(
                segs, *args, x_fence=fence)

            def three(lw):
                if lw["status"] != "RESOLVED":
                    return f"{lw['status']} — {lw['reason']}"
                sil = wall = "?"
                if spec.get("ft") and spec.get("scale_y"):
                    W, H = ot[pg]["page_w"], ot[pg]["page_h"]
                    sy = spec["scale_y"]
                    fpp = spec["ft"] / (abs(sy[1] - sy[0]) * H)
                    sil = round((lw["x_span"][1] - lw["x_span"][0])
                                / 100.0 * W * fpp, 2)
                    wc = lw.get("wall_corners")
                    if wc:
                        wall = round((wc[1] - wc[0]) / 100.0 * W * fpp, 2)
                sealed, why = SEALED[house].get(face) or (None, "")
                pe = []
                vp = lw["vertices_pct"]
                if len(vp) > 4:
                    for i in range(len(vp) - 1):
                        if (abs(vp[i][1] - vp[i + 1][1]) < 1e-9
                                and abs(vp[i][0] - vp[i + 1][0]) > 1e-9
                                and 0 < i < len(vp) - 1):
                            side = ("RIGHT" if max(vp[i][0], vp[i+1][0])
                                    >= max(q[0] for q in vp) - 1e-9
                                    else "LEFT")
                            if vp[i][1] not in (vp[0][1],):
                                pe.append(side)
                return (f"x{lw['x_span']} v={lw['n_vertices']} "
                        f"SIL={sil} WALL={wall} SEALED={sealed} ({why}) "
                        f"proj_edge={sorted(set(pe)) or 'none'} "
                        f"refusals={lw.get('projection_refusals')}")

            print(f"  {face:<6} p{pg}")
            print(f"    BEFORE {three(before)}")
            print(f"    AFTER  {three(after)}")
            if after["status"] == "RESOLVED":
                print(f"    AFTER vertices: {after['vertices_pct']}")


main()
