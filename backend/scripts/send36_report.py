"""SEND-36 full report (report only, NO BIND):
  1. Letrick p5/p7 horizontal rails vs 54'-0"
  2. x-positions of p5/p7 LEFT/RIGHT winners; garage-item check
  3. MM census re-report (string counts before/after merge) + axis
     cut RE-VERIFICATION on merged Boni p6
  4. LL closure report (both houses' plan pages; Boni p8/p9 probe
     with the precondition set aside)
  5. Chimney search (~2'-7" / ~32'-7") on Letrick
  6. Re-run of BOTH dry runs on the merged substrate
Nothing tuned. EST-886440 untouched."""
import json
import os
import re
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from pymongo import MongoClient

import ocr_geometry as og

BONI = "c54633996e7a49e48432cf66a61efaf7"
LETRICK = "725f8326fd6e48aca8448c22f2454100"
_digits = lambda s: re.sub(r"\D", "", str(s or ""))


def _probe_faces(runs):
    pr = og.positional_rule_probe(runs)
    out = {"envelope": pr["envelope"]["status"],
           "rails": pr["envelope"].get("rails"),
           "hh": [g["raw"] for g in pr["gated_bare_admitted"]]}
    if pr["envelope"]["status"] != "ESTABLISHED":
        out["reason"] = pr["envelope"].get("reason")
        return out
    for side in ("left", "right"):
        s = pr["sides"][side]
        ch = s["chosen"] or {}
        f = {"chosen": ch.get("raw"), "x": (ch.get("loc") or {}).get("x_pct"),
             "contenders": [(c["raw"], c["dist_from_mid_pct"])
                            for c in s["contenders"]][:5]}
        distinct = [c for c in s["contenders"][1:]
                    if _digits(c["raw"]) != _digits(ch.get("raw"))]
        f["distinct_runner_up"] = distinct[0]["raw"] if distinct else None
        f["margin"] = (round(s["contenders"][0]["dist_from_mid_pct"]
                             - distinct[0]["dist_from_mid_pct"], 2)
                       if distinct else None)
        out[side] = f
    return out


def main():
    cli = MongoClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    rep = {"UNVALIDATED": True, "no_bind": True}

    stores = {}
    for name, rid in (("boni", BONI), ("letrick", LETRICK)):
        run = db.ai_blueprint_runs.find_one({"run_id": rid})
        stores[name] = run["result"]["raw_ai"]["_ocr_text_by_page"]

    # ---- 1. Letrick p5/p7 horizontal rails ----
    rep["item1_rails"] = {}
    for pg in ("5", "7"):
        env = og.rail_envelope(stores["letrick"][pg]["runs"])
        rep["item1_rails"][pg] = {"status": env["status"],
                                  "rails": env.get("rails")}

    # ---- 2a. x-positions of winners ----
    rep["item2_xpos"] = {}
    for pg in ("5", "7"):
        f = _probe_faces(stores["letrick"][pg]["runs"])
        rep["item2_xpos"][pg] = {s: {"chosen": f[s]["chosen"], "x": f[s]["x"]}
                                 for s in ("left", "right") if s in f}

    # ---- 2b. garage-derived items on the Letrick estimate ----
    est = db.estimates.find_one({"estimate_number": "EST-655664"})
    gar_lines = []
    for ln in (est or {}).get("lines") or []:
        txt = json.dumps(ln, default=str).lower()
        if "garage" in txt:
            gar_lines.append({k: ln.get(k) for k in
                              ("name", "description", "qty", "quantity",
                               "label", "unit") if k in ln})
    run_l = db.ai_blueprint_runs.find_one({"run_id": LETRICK})
    res_lines = []
    for ln in (run_l.get("result") or {}).get("lines") or []:
        txt = json.dumps(ln, default=str).lower()
        if "garage" in txt:
            res_lines.append(ln)
    rep["item2_garage_items"] = {"estimate_lines_matching": gar_lines,
                                 "run_result_lines_matching": res_lines[:5]}

    # ---- 3. MM census + axis re-verify on merged Boni p6 ----
    rep["mm_census"] = {}
    for name, store in stores.items():
        rep["mm_census"][name] = {}
        for pg in sorted(store, key=int):
            runs = store[pg]["runs"]
            merged = og.merge_positions(runs)
            conf = sum(1 for m in merged if m.get("merge_conflict"))
            rep["mm_census"][name][pg] = {
                "readings": len(runs), "strings": len(merged),
                "conflicted": conf}
    p6m = og.merge_positions(stores["boni"]["6"]["runs"])
    dims = [r for r in p6m if og.is_dimension_like(r.get("raw"))]
    nrs = []
    for r in dims:
        l, g = r["loc"], og.glyph_count(r["raw"])
        if l["h_pct"] and g:
            nrs.append((round((l["w_pct"] / l["h_pct"]) / g, 4),
                        r["axis"], r["raw"]))
    v = sorted(n for n, a, _ in nrs if a == og.VERTICAL)
    h = sorted(n for n, a, _ in nrs if a == og.HORIZONTAL)
    ind = [(n, raw) for n, a, raw in nrs if a == og.INDETERMINATE]
    rep["axis_reverify_boni_p6_merged"] = {
        "strings": len(dims),
        "vertical": {"n": len(v), "min": v[0] if v else None,
                     "max": v[-1] if v else None},
        "horizontal": {"n": len(h), "min": h[0] if h else None,
                       "max": h[-1] if h else None},
        "indeterminate": ind,
        "gap_holds": bool(v and h and v[-1] < og.AXIS_VERTICAL_MAX
                          < og.AXIS_HORIZONTAL_MIN < h[0]),
    }

    # ---- 4. LL closure (plan pages both houses; Boni p8/p9 probe) ----
    rep["ll_closure"] = {}
    for name, pages in (("boni", ("4", "6", "7", "8", "9")),
                        ("letrick", ("5", "7", "8"))):
        rep["ll_closure"][name] = {}
        for pg in pages:
            cc = og.chain_sum_closure(stores[name][pg]["runs"])
            rep["ll_closure"][name][pg] = {
                "chains": len(cc),
                "closes": sum(1 for c in cc if c["status"] == "CLOSES"),
                "fails": sum(1 for c in cc if c["status"] == "FAILS"),
                "unparseable": sum(1 for c in cc if c["status"] == "UNPARSEABLE"),
                "failing": [{"axis": c["axis"],
                             "members": [m["raw"] for m in c["members"]],
                             "residual_in": c.get("residual_in")}
                            for c in cc if c["status"] == "FAILS"][:6]}
    rep["boni_p8_p9_probe_precondition_set_aside"] = {
        pg: _probe_faces(stores["boni"][pg]["runs"]) for pg in ("8", "9")}

    # ---- 5. chimney search on Letrick ----
    hits = []
    for pg in sorted(stores["letrick"], key=int):
        for r in stores["letrick"][pg]["runs"]:
            d = _digits(r["raw"])
            if d in ("27", "327") and og.is_dimension_like(r["raw"]):
                hits.append({"page": pg, "raw": r["raw"], "src": r["src"],
                             "axis": r["axis"], "loc": r["loc"]})
    rep["item5_chimney_hits"] = hits

    # ---- 6. dry-run re-runs on merged substrate ----
    rep["dryrun_merged"] = {}
    for name, pages in (("boni", ("1", "4", "6", "7", "8", "9")),
                        ("letrick", ("1", "5", "6", "7", "8", "10"))):
        rep["dryrun_merged"][name] = {
            pg: _probe_faces(stores[name][pg]["runs"]) for pg in pages}

    out = "/app/memory/send36_report.json"
    with open(out, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(f"[send36] report written to {out}")


if __name__ == "__main__":
    main()
