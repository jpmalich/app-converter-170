"""SEND-44 owed reports — ALL REPORT-ONLY. No builds, no binds."""
import json, os, re, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient
import ocr_geometry as og

BONI = "c54633996e7a49e48432cf66a61efaf7"
LETRICK = "725f8326fd6e48aca8448c22f2454100"

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
docs, stores, sheets = {}, {}, {}
for name, rid in (("boni", BONI), ("letrick", LETRICK)):
    d = db.ai_blueprint_runs.find_one({"run_id": rid})
    docs[name] = d
    stores[name] = d["result"]["raw_ai"]["_ocr_text_by_page"]
    sheets[name] = {str(s.get("page")): str(s.get("sheet_title") or "")
                    for s in d["result"]["raw_ai"].get("sheets_identified") or []}
rep = {}

# A. TIE AUDIT
rep["tie_audit"] = {"ties": [], "rendered_note":
    "no probe output has ever been bound into derivation (no-bind standing); "
    "rendered values come from the model path (raw_ai.walls) only"}
for name, store in stores.items():
    for pg in sorted(store, key=int):
        pr = og.positional_rule_probe(store[pg]["runs"])
        if pr["envelope"]["status"] != "ESTABLISHED":
            continue
        for side in ("left", "right"):
            s = pr["sides"][side]
            if s.get("tie"):
                rep["tie_audit"]["ties"].append({
                    "house": name, "page": pg, "side": side,
                    "tied": s["tie"],
                    "list_order_would_have_chosen": s["contenders"][0]["raw"]
                    if s["contenders"] else None})

# B. WHICH CHAIN CLOSED on Boni p4 RIGHT at 30'-0"
closes = [e for e in og.tt_closure(stores["boni"]["4"]["runs"])
          if e.get("status") == "CLOSES"]
rep["p4_right_closing_chain"] = closes

# C. HEIGHT PROVENANCE CENSUS
rep["height_census"] = {}
for name, d in docs.items():
    raw = d["result"]["raw_ai"]
    m = d["result"].get("measurements") or {}
    ev = raw.get("_dim_evidence") or {}
    hev = {k: v for k, v in ev.items() if "height" in k.lower()}
    srcs_seen = {}
    entries = []
    for path, e in sorted(hev.items()):
        for s in (e.get("srcs") or [e]):
            if not isinstance(s, dict):
                continue
            key = (str(s.get("from")), str(s.get("page")))
            srcs_seen.setdefault(key, []).append(path)
            entries.append({"path": path, "from": s.get("from"),
                            "page": s.get("page"), "loc": s.get("loc"),
                            "precision": s.get("precision")})
    shared = {f"{k[0]} (p{k[1]})": paths for k, paths in srcs_seen.items()
              if len(paths) > 1}
    rep["height_census"][name] = {
        "walls": [{kk: w.get(kk) for kk in
                   ("label", "width_ft", "height_ft",
                    "gable_triangle_height_ft")}
                  for w in raw.get("walls") or []],
        "avg_wall_height_ft": m.get("_ai_avg_wall_height_ft"),
        "height_evidence": entries,
        "distributed_sources": shared}

# D. ELEVATION READ REPORT
rep["elevation_read"] = {}
for name, store in stores.items():
    rep["elevation_read"][name] = {}
    for pg, title in sheets[name].items():
        if "ELEVATION" not in title.upper():
            continue
        runs = og.merge_positions(store.get(pg, {}).get("runs", []))
        ys = sorted(r["loc"]["y_pct"] for r in runs)
        gaps = [(round(ys[i+1]-ys[i], 1), round(ys[i], 1))
                for i in range(len(ys)-1) if ys[i+1]-ys[i] > 8]
        vdims = [r for r in runs if og.is_dimension_like(r["raw"])
                 and r["axis"] == og.VERTICAL]
        story = sorted({r["raw"] for r in runs if re.search(
            r"FLOOR|CEILING|PLATE|STORY", str(r.get("norm") or ""))})[:8]
        rep["elevation_read"][name][pg] = {
            "title": title, "strings": len(runs),
            "content_y_gaps_gt8pct": gaps,
            "vertical_dim_count": len(vdims),
            "vertical_dim_y_centers": sorted(
                round(r["loc"]["y_pct"], 1) for r in vdims)[:20],
            "story_labels": story}

# E. GRADE READ REPORT
rep["grade_read"] = {}
for name, store in stores.items():
    hits = []
    for pg in sorted(store, key=int):
        for r in store[pg]["runs"]:
            if re.search(r"GRADE|WALKOUT|STEPPED", str(r.get("norm") or "")):
                hits.append({"page": pg, "raw": r["raw"][:40],
                             "loc": r["loc"], "axis": r["axis"]})
    rep["grade_read"][name] = hits

# F. SECOND FOOTPRINT
rep["second_footprint"] = {}
for name, pages in (("boni", ("4", "6", "7")), ("letrick", ("5", "7"))):
    rep["second_footprint"][name] = {}
    for pg in pages:
        runs = og.merge_positions(stores[name][pg]["runs"])
        dims = [r for r in runs if og.is_rail_candidate(r["raw"])]
        xs = sorted(og._cx(r) for r in dims)
        xgaps = [(round(xs[i+1]-xs[i], 1), round(xs[i], 1))
                 for i in range(len(xs)-1) if xs[i+1]-xs[i] > 15]
        rep["second_footprint"][name][pg] = {
            "dim_x_gaps_gt15pct": xgaps,
            "dim_x_span": (round(xs[0], 1), round(xs[-1], 1)) if xs else None}

out = "/app/memory/send44_reports.json"
with open(out, "w") as f:
    json.dump(rep, f, indent=1, default=str)
print("written", out)
