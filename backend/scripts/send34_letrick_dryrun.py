"""SEND-34 — anchor DRY RUN on the SECOND PLAN SET (Letrick).
REPORT ONLY. NO BIND. UNVALIDATED THROUGHOUT. No ground truth is
known here and none is claimed. Nothing is tuned against this set.
Ruling LL (sum closure) is NOT YET BUILT — owed; stated, not faked."""
import json
import os
import re
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from pymongo import MongoClient

import ocr_geometry as og

RUN_ID = "725f8326fd6e48aca8448c22f2454100"
_digits = lambda s: re.sub(r"\D", "", str(s or ""))


def main():
    cli = MongoClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    run = db.ai_blueprint_runs.find_one({"run_id": RUN_ID})
    blob = run["result"]["raw_ai"]["_ocr_text_by_page"]
    sheets = {str(s.get("page")): str(s.get("sheet_title") or "")
              for s in run["result"]["raw_ai"].get("sheets_identified") or []}

    rep = {"run_id": RUN_ID, "estimate": "EST-655664 (letrick 8-16-26 4 pm)",
           "UNVALIDATED": True, "no_bind": True, "no_ground_truth_claimed": True,
           "ruling_ll": "NOT BUILT — owed; no sum-closure report available",
           "pages": {}, "position": None}

    precondition_pages = []
    for pg in sorted(blob, key=int):
        runs = blob[pg]["runs"]
        pr = og.positional_rule_probe(runs)
        env = pr["envelope"]
        dims = [r for r in runs if og.is_dimension_like(r.get("raw"))]
        ax = {"HORIZONTAL": 0, "VERTICAL": 0, "INDETERMINATE": 0}
        for r in dims:
            ax[r.get("axis", "INDETERMINATE")] = ax.get(r.get("axis", "INDETERMINATE"), 0) + 1
        entry = {"sheet_title": sheets.get(pg),
                 "rail_status": env["status"],
                 "rail_reason": env.get("reason"),
                 "rails": env.get("rails"),
                 "axis_counts": ax,
                 "hh_admitted": [
                     {"raw": g["raw"], "src": g.get("src"), "feet": g["feet"],
                      "inches": g["inches"], "chain_mate": g["chain_mate"],
                      "loc": g["loc"]}
                     for g in pr["gated_bare_admitted"]],
                 "ruling_ll": "NOT BUILT — owed"}
        # Room-label precondition: a garage-word run whose center sits
        # INSIDE the established envelope (position alone — the property
        # that separated Boni p1 from p6; nothing widened for Letrick).
        room_labels = []
        if env["status"] == "ESTABLISHED":
            for g in runs:
                if "GARAGE" not in str(g.get("norm") or ""):
                    continue
                l = g["loc"]
                cx, cy = l["x_pct"] + l["w_pct"] / 2, l["y_pct"] + l["h_pct"] / 2
                if env["x_lo"] < cx < env["x_hi"] and env["y_lo"] < cy < env["y_hi"]:
                    side = "right" if cx >= (env["x_lo"] + env["x_hi"]) / 2 else "left"
                    room_labels.append({"raw": g["raw"], "side": side,
                                        "src": g.get("src"), "loc": l})
            entry["room_label_precondition"] = (
                {"met": True, "labels": room_labels} if room_labels
                else {"met": False,
                      "why": "no garage-word run inside the established envelope"})
        else:
            entry["room_label_precondition"] = {
                "met": False,
                "why": f"envelope not established — {env.get('reason')}"}
        if entry["room_label_precondition"]["met"]:
            precondition_pages.append(pg)

        if env["status"] == "ESTABLISHED":
            for side in ("left", "right"):
                s = pr["sides"][side]
                chosen = s["chosen"]
                face = {"anchor_returns": (chosen or {}).get("raw"),
                        "loc": (chosen or {}).get("loc"),
                        "src": None,
                        "contenders": [(c["raw"], c["dist_from_mid_pct"],
                                        c.get("src"))
                                       for c in s["contenders"]][:8],
                        "excluded_interior": [e["raw"]
                                              for e in s["excluded_interior"]][:10]}
                if chosen:
                    for r in runs:
                        if r.get("loc") == chosen.get("loc") and r.get("raw") == chosen.get("raw"):
                            face["src"] = r.get("src")
                            break
                    distinct = None
                    for c in s["contenders"][1:]:
                        if _digits(c["raw"]) != _digits(chosen["raw"]):
                            distinct = c
                            break
                    if distinct:
                        face["distinct_runner_up"] = distinct["raw"]
                        face["margin_pct"] = round(
                            s["contenders"][0]["dist_from_mid_pct"]
                            - distinct["dist_from_mid_pct"], 2)
                    else:
                        face["distinct_runner_up"] = None
                        face["margin_pct"] = None
                        face["note"] = ("sole distinct candidate — wins by "
                                        "default, which proves least")
                else:
                    face["note"] = "no vertical exterior dimension on this side"
                entry[side] = face
        rep["pages"][pg] = entry

    if precondition_pages:
        answers = {pg: {s: rep["pages"][pg].get(s, {}).get("anchor_returns")
                        for s in ("left", "right")}
                   for pg in precondition_pages}
        rep["position"] = {
            "state": "UNVALIDATED — anchor AVAILABLE on this set",
            "precondition_pages": precondition_pages,
            "anchor_answers_on_those_pages": answers,
            "note": "Howard compares against his sealed depths; "
                    "no match/mismatch is claimed here."}
    else:
        rep["position"] = {
            "state": "UNVALIDATED AND UNAVAILABLE on this set",
            "precondition_pages": [],
            "note": "no page met the room-label precondition — a different "
                    "and worse position than unvalidated alone."}

    out = "/app/memory/send34_letrick_dryrun_report.json"
    with open(out, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(f"[send34] report written to {out}")
    print("[send34] position:", rep["position"]["state"])


if __name__ == "__main__":
    main()
