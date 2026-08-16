"""SEND-31 re-probe (report only) — Rulings HH + II applied to the
persisted store from run c5463399. No DB writes, no derivation, no
anchor bind. The p4/p6 LEFT-depth disagreement is REPORTED, never
resolved."""
import json
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from pymongo import MongoClient

import ocr_geometry as og

RUN_ID = "c54633996e7a49e48432cf66a61efaf7"


def main():
    cli = MongoClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    run = db.ai_blueprint_runs.find_one({"run_id": RUN_ID})
    blob = run["result"]["raw_ai"]["_ocr_text_by_page"]

    rep = {"run_id": RUN_ID, "rails_by_page": {}, "admissions_by_page": {},
           "admissions_total": 0}
    for pg in sorted(blob, key=int):
        runs = blob[pg]["runs"]
        env = og.rail_envelope(runs)
        rep["rails_by_page"][pg] = {
            "status": env["status"], "reason": env.get("reason"),
            "rails": env.get("rails"),
            "bounds": {k: env.get(k) for k in ("x_lo", "x_hi", "y_lo", "y_hi")},
        }
        adm = og.gated_bare_form_admissions(runs)
        rep["admissions_by_page"][pg] = [
            {"raw": a["run"]["raw"], "src": a["run"].get("src"),
             "axis": a["run"].get("axis"), "loc": a["run"]["loc"],
             "feet": a["feet"], "inches": a["inches"],
             "chain_mate": a["chain_mate"]}
            for a in adm["admitted"]]
        rep["admissions_total"] += len(adm["admitted"])

    for pg in ("4", "6"):
        pr = og.positional_rule_probe(blob[pg]["runs"])
        rep[f"probe_p{pg}"] = {
            "envelope_status": pr["envelope"]["status"],
            "rails": pr["envelope"].get("rails"),
            "gated_bare_admitted": pr["gated_bare_admitted"],
            "sides": {s: {"chosen": v["chosen"],
                          "contenders": [(c["raw"], c["dist_from_mid_pct"])
                                         for c in v["contenders"]],
                          "excluded_interior": [e["raw"]
                                                for e in v["excluded_interior"]][:12]}
                      for s, v in pr["sides"].items()},
        }

    left4 = (rep.get("probe_p4", {}).get("sides", {}).get("left", {})
             .get("chosen") or {}).get("raw")
    left6 = (rep.get("probe_p6", {}).get("sides", {}).get("left", {})
             .get("chosen") or {}).get("raw")
    import re as _re
    _digits = lambda s: _re.sub(r"\D", "", str(s or ""))
    rep["left_depth_cross_sheet"] = {
        "p4_foundation": left4, "p6_first_floor": left6,
        "verdict": ("DISAGREE — reported, not resolved; never averaged, "
                    "no sheet preferred" if left4 and left6
                    and _digits(left4) != _digits(left6)
                    else "AGREE"),
    }

    out = "/app/memory/send31_reprobe_report.json"
    with open(out, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(f"[send31] admissions_total={rep['admissions_total']}")
    print(f"[send31] report written to {out}")


if __name__ == "__main__":
    main()
