"""SEND-38 report: XX verdicts on both houses, faces as they actually
render, UU indeterminate census, WW exclusion diff, TT on Boni p4 LEFT,
and the p8/p9 question under WW + TT. REPORT ONLY."""
import json
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from pymongo import MongoClient

import ocr_geometry as og

BONI = "c54633996e7a49e48432cf66a61efaf7"
LETRICK = "725f8326fd6e48aca8448c22f2454100"


def main():
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    rep = {}
    stores, runs_docs = {}, {}
    for name, rid in (("boni", BONI), ("letrick", LETRICK)):
        d = db.ai_blueprint_runs.find_one({"run_id": rid})
        runs_docs[name] = d
        stores[name] = d["result"]["raw_ai"]["_ocr_text_by_page"]

    # XX verdicts on the plan sheets
    rep["xx"] = {}
    for name, pages in (("boni", ("4", "6", "7")), ("letrick", ("5", "7"))):
        rep["xx"][name] = {}
        for pg in pages:
            v = og.attribution_verdict(stores[name][pg]["runs"])
            rep["xx"][name][pg] = {
                "status": v["status"], "why": v["why"], "depth": v["depth"],
                "pair": {s: (p or {}).get("raw")
                         for s, p in (v.get("pair") or {}).items()}}

    # Faces as they actually render (model path + gates)
    rep["render"] = {}
    for name in ("boni", "letrick"):
        res = runs_docs[name]["result"]
        m = res.get("measurements") or {}
        walls = (res.get("raw_ai") or {}).get("walls") or []
        rep["render"][name] = {
            "faces": [{k: w.get(k) for k in
                       ("label", "width_ft", "height_ft",
                        "gable_triangle_height_ft")} for w in walls],
            "faces_not_derivable": m.get("_faces_not_derivable"),
            "siding_sqft": m.get("siding_sqft"),
        }

    # UU: indeterminate census across both houses (merged, dim-like)
    rep["uu_indeterminate"] = {}
    for name, store in stores.items():
        total, ind, inds = 0, 0, []
        for pg in store:
            for r in og.merge_positions(store[pg]["runs"]):
                if og.is_dimension_like(r.get("raw")):
                    total += 1
                    if r.get("axis") == og.INDETERMINATE:
                        ind += 1
                        inds.append((pg, r["raw"]))
        rep["uu_indeterminate"][name] = {"dim_strings": total,
                                         "indeterminate": ind,
                                         "list": inds[:15]}

    # WW: what else it excludes on the plan sheets
    rep["ww_excluded"] = {}
    for name, pages in (("boni", ("4", "6", "7", "8", "9")),
                        ("letrick", ("5", "7", "8"))):
        rep["ww_excluded"][name] = {}
        for pg in pages:
            pr = og.positional_rule_probe(stores[name][pg]["runs"])
            if pr["envelope"]["status"] != "ESTABLISHED":
                continue
            ex = {s: [r["raw"] for r in pr["sides"][s]["excluded_off_rail"]]
                  for s in ("left", "right")}
            ch = {s: (pr["sides"][s]["chosen"] or {}).get("raw")
                  for s in ("left", "right")}
            rep["ww_excluded"][name][pg] = {"chosen": ch, "excluded": ex}

    # TT on Boni p4 (LEFT first, as ordered) and the p8/p9 question
    rep["tt_boni_p4"] = og.tt_closure(stores["boni"]["4"]["runs"])
    rep["tt_boni_p8_p9"] = {pg: og.tt_closure(stores["boni"][pg]["runs"])
                            for pg in ("8", "9")}

    out = "/app/memory/send38_report.json"
    with open(out, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(f"[send38] written {out}")


if __name__ == "__main__":
    main()
