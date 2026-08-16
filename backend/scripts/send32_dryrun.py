"""SEND-32 items 1-4 (report only): JJ rail re-report with status
changes, Item-3 structural separation probe (p1 vs plan sheets), the
anchor DRY RUN across all pages with contention margins — UNVALIDATED
on every line — and KK applied to the left depth. NO BIND. No DB
writes. EST-886440 untouched."""
import json
import os
import re
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from pymongo import MongoClient

import ocr_geometry as og

RUN_ID = "c54633996e7a49e48432cf66a61efaf7"
_digits = lambda s: re.sub(r"\D", "", str(s or ""))


def main():
    cli = MongoClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    run = db.ai_blueprint_runs.find_one({"run_id": RUN_ID})
    blob = run["result"]["raw_ai"]["_ocr_text_by_page"]
    sheets = {str(s.get("page")): str(s.get("sheet_title") or "")
              for s in run["result"]["raw_ai"].get("sheets_identified") or []}

    prev = json.load(open("/app/memory/send31_reprobe_report.json"))
    rep = {"run_id": RUN_ID, "unvalidated": True,
           "rails_after_jj": {}, "rail_status_changes": {},
           "item3_structural": {}, "dry_run": {}, "kk_left_depth": None}

    # ---- 1. JJ rail re-report + changes ----
    for pg in sorted(blob, key=int):
        env = og.rail_envelope(blob[pg]["runs"])
        rep["rails_after_jj"][pg] = {
            "status": env["status"], "reason": env.get("reason"),
            "rails": env.get("rails"),
            "bounds": {k: env.get(k) for k in ("x_lo", "x_hi", "y_lo", "y_hi")}}
        old = prev["rails_by_page"].get(pg, {})
        if (old.get("status") != env["status"]
                or old.get("rails") != env.get("rails")):
            rep["rail_status_changes"][pg] = {
                "before": {"status": old.get("status"), "rails": old.get("rails")},
                "after": {"status": env["status"], "rails": env.get("rails")}}

    # ---- 2. Item 3: structural separation in the persisted data ----
    for pg in sorted(blob, key=int):
        runs = blob[pg]["runs"]
        garage = [r for r in runs if "GARAGE" in str(r.get("norm") or "")]
        dims = [r for r in runs if og.is_dimension_like(r.get("raw"))]
        v = [r for r in dims if r.get("axis") == og.VERTICAL]
        hz = [r for r in dims if r.get("axis") == og.HORIZONTAL]
        env = rep["rails_after_jj"][pg]
        # A garage ROOM label: a garage-containing run that is itself a
        # short label (not a sentence-note) sitting inside the envelope.
        room_labels = []
        if env["status"] == "ESTABLISHED":
            b = env["bounds"]
            for g in garage:
                l = g["loc"]
                cx, cy = l["x_pct"] + l["w_pct"] / 2, l["y_pct"] + l["h_pct"] / 2
                if (b["x_lo"] < cx < b["x_hi"] and b["y_lo"] < cy < b["y_hi"]
                        and og.glyph_count(g["raw"]) <= 12):
                    room_labels.append(g["raw"])
        rep["item3_structural"][pg] = {
            "sheet_title": sheets.get(pg), "garage_runs": len(garage),
            "garage_room_labels_inside_envelope": room_labels,
            "dim_like": len(dims), "vertical": len(v), "horizontal": len(hz),
            "v_to_h": round(len(v) / len(hz), 2) if hz else None,
            "envelope": env["status"]}

    # ---- 3. Anchor DRY RUN, report only, all pages ----
    for pg in sorted(blob, key=int):
        pr = og.positional_rule_probe(blob[pg]["runs"])
        entry = {"UNVALIDATED": True, "sheet_title": sheets.get(pg),
                 "envelope": pr["envelope"]["status"]}
        if pr["envelope"]["status"] != "ESTABLISHED":
            entry["result"] = "INDETERMINATE"
            entry["reason"] = pr.get("reason") or pr["envelope"].get("reason")
            rep["dry_run"][pg] = entry
            continue
        entry["garage_label_sides"] = {}
        for l in pr["labels"]:
            entry["garage_label_sides"].setdefault(l["side"], []).append(l["raw"])
        entry["gated_bare_admitted"] = [g["raw"] for g in pr["gated_bare_admitted"]]
        for side in ("left", "right"):
            s = pr["sides"][side]
            chosen = s["chosen"]
            face = {"chosen": (chosen or {}).get("raw"),
                    "chosen_loc": (chosen or {}).get("loc"),
                    "contenders": s["contenders"][:6]}
            if chosen and len(s["contenders"]) > 1:
                cd = s["contenders"][0][1] if isinstance(s["contenders"][0], (list, tuple)) else s["contenders"][0]["dist_from_mid_pct"]
                distinct = None
                for c in s["contenders"][1:]:
                    craw = c[0] if isinstance(c, (list, tuple)) else c["raw"]
                    cdist = c[1] if isinstance(c, (list, tuple)) else c["dist_from_mid_pct"]
                    if _digits(craw) != _digits(face["chosen"]):
                        distinct = (craw, cdist)
                        break
                if distinct:
                    face["distinct_runner_up"] = distinct[0]
                    face["margin_pct"] = round(cd - distinct[1], 2)
                    face["had_it_gone_the_other_way"] = distinct[0]
                else:
                    face["distinct_runner_up"] = None
                    face["margin_pct"] = None
                    face["note"] = "sole distinct candidate — wins by default, which proves least"
            elif chosen:
                face["distinct_runner_up"] = None
                face["margin_pct"] = None
                face["note"] = "sole candidate — wins by default, which proves least"
            entry[side] = face
        rep["dry_run"][pg] = entry

    # ---- 4. KK on the left depth ----
    readings = []
    for pg in ("4", "6"):
        d = rep["dry_run"].get(pg, {})
        chosen = (d.get("left") or {}).get("chosen")
        if chosen:
            readings.append({"value": chosen, "page": int(pg),
                             "plane": og.plane_for_sheet_title(sheets.get(pg))})
    rep["kk_left_depth"] = og.reference_plane_verdict(readings, material="siding")

    out = "/app/memory/send32_dryrun_report.json"
    with open(out, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(f"[send32] report written to {out}")


if __name__ == "__main__":
    main()
