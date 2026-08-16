"""SEND-30 backfill + re-probe (Howard sealed 2026-08-16) — REPORT ONLY.

Re-reads the retained Boni rasters with the repaired coverage pipeline
(rotated passes on every page, all runs persisted with src + axis),
archives the old upright-only store on the run doc, persists the new
one, then runs the axis distribution, the rail envelope and the
positional rule probe. THE ANCHOR IS NOT BOUND. Derivation is NOT
re-run. EST-886440 untouched (this run belongs to est 65bcb89d).
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from pymongo import MongoClient

import ocr_geometry as og
import routes.ai_blueprint as bp

RUN_ID = "c54633996e7a49e48432cf66a61efaf7"
UPLOADS = "/app/backend/uploads"


def main():
    cli = MongoClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    run = db.ai_blueprint_runs.find_one({"run_id": RUN_ID})
    assert run, "run not found"
    names = [n for n in (run.get("page_paths") or "").split(",") if n.strip()]
    payloads = []
    for n in names:
        with open(os.path.join(UPLOADS, n.strip()), "rb") as f:
            payloads.append(f.read())
    print(f"[reprobe] {len(payloads)} rasters loaded", flush=True)

    raw = {}
    bp._ocr_locate_evidence({}, payloads, raw)  # coverage-only read
    blob = raw["_ocr_text_by_page"]
    size = bp._bson_len({"by_page": blob})
    print(f"[reprobe] new store bytes={size}", flush=True)

    old_blob = (run.get("result") or {}).get("raw_ai", {}).get("_ocr_text_by_page")
    old_cov = (run.get("result") or {}).get("raw_ai", {}).get("_ocr_page_coverage_chars")
    updates = {
        "result.raw_ai._send30_backfill": {
            "at": datetime.now(timezone.utc).isoformat(),
            "note": "SEND-30 coverage backfill on retained rasters — "
                    "rotated passes on every page, all runs persisted "
                    "with src+axis. Old upright-only store archived. "
                    "No derivation re-run, anchor NOT bound.",
            "old_ocr_text_by_page": old_blob,
            "old_ocr_page_coverage_chars": old_cov,
        },
        "result.raw_ai._ocr_page_coverage_chars":
            raw.get("_ocr_page_coverage_chars"),
    }
    if size <= bp._OCR_ONDOC_MAX_BYTES:
        updates["result.raw_ai._ocr_text_by_page"] = blob
        updates["result.raw_ai._ocr_text_ref"] = {
            "where": "run_doc", "approx_bytes": size,
            "pages": sorted(blob.keys())}
    else:
        db.ai_blueprint_ocr.replace_one(
            {"run_id": RUN_ID},
            {"run_id": RUN_ID, "by_page": blob, "truncated": None},
            upsert=True)
        updates["result.raw_ai._ocr_text_by_page"] = None
        updates["result.raw_ai._ocr_text_ref"] = {
            "where": "ai_blueprint_ocr", "run_id": RUN_ID,
            "approx_bytes": size, "pages": sorted(blob.keys())}
    db.ai_blueprint_runs.update_one({"run_id": RUN_ID}, {"$set": updates})
    print("[reprobe] run doc updated (old store archived)", flush=True)

    # ---- REPORT ----
    rep = {"run_id": RUN_ID, "run_counts": {}, "axis_p6": [], "searches": {}}
    for pg in sorted(blob, key=int):
        runs = blob[pg]["runs"]
        by_src = {}
        for r in runs:
            by_src[r["src"]] = by_src.get(r["src"], 0) + 1
        rep["run_counts"][pg] = {"total": len(runs), **by_src}

    p6 = blob.get("6", {}).get("runs", [])
    for r in p6:
        if og.is_dimension_like(r["raw"]):
            g = og.glyph_count(r["raw"])
            l = r["loc"]
            nr = round((l["w_pct"] / l["h_pct"]) / g, 4) if l["h_pct"] and g else None
            rep["axis_p6"].append({"raw": r["raw"], "src": r["src"],
                                   "loc": l, "glyphs": g, "nr": nr,
                                   "axis": r["axis"]})

    for target, label in (("302", "30'-2"), ("330", "33'-0")):
        hits = []
        for pg in sorted(blob, key=int):
            for r in blob[pg]["runs"]:
                n = r["norm"]
                if target in n and len(n) <= len(target) + 3:
                    hits.append({"page": pg, "raw": r["raw"], "norm": n,
                                 "src": r["src"], "axis": r["axis"],
                                 "loc": r["loc"]})
        rep["searches"][label] = hits

    rep["envelope_p6"] = og.rail_envelope(p6)
    rep["probe_p6"] = og.positional_rule_probe(p6)
    p4 = blob.get("4", {}).get("runs", [])
    rep["envelope_p4"] = og.rail_envelope(p4)
    rep["probe_p4"] = og.positional_rule_probe(p4)

    out = "/app/memory/send30_reprobe_report.json"
    with open(out, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(f"[reprobe] report written to {out}", flush=True)


if __name__ == "__main__":
    main()
