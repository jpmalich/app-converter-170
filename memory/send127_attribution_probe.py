"""SEND-127 attribution replay — READ-ONLY. For each fixture house's
stored blueprint run: which located dims are UNATTRIBUTED (one located
quote claimed by two or more DIFFERENT named features for the same leaf),
and what quantities they feed TODAY. No run rewritten, no estimate
touched, no model call."""
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

HOUSES = {
    "boni": None, "letrick": None, "tanis": None, "dart": None,
}


def _feature(path):
    parts = str(path).split(".")
    return ".".join(parts[:-1]), parts[-1]


def unattributed(raw):
    """A path is UNATTRIBUTED when its located quote is claimed by 2+
    DIFFERENT named features for the SAME leaf field."""
    out = {}
    for rec in (raw.get("_dim_shared_source") or []):
        groups = {}
        for p in rec.get("consumers") or []:
            feat, leaf = _feature(p)
            groups.setdefault(leaf, set()).add(feat)
        for leaf, feats in groups.items():
            if len(feats) < 2:
                continue
            for f in feats:
                out[f"{f}.{leaf}"] = {
                    "quote": rec.get("quote"), "page": rec.get("page"),
                    "competitors": sorted(feats),
                    "conflicting": rec.get("conflicting")}
    return out


for est in db.estimates.find(
        {}, {"id": 1, "customer_name": 1, "estimate_number": 1}):
    nm = str(est.get("customer_name") or "").lower()
    for h in HOUSES:
        if h in nm and HOUSES[h] is None:
            run = db.ai_blueprint_runs.find_one(
                {"estimate_id": est["id"], "status": "done"},
                sort=[("created_at", -1)])
            if run:
                HOUSES[h] = (est, run)

for h, pair in HOUSES.items():
    print("=" * 70)
    if not pair:
        print(f"{h.upper()}: no stored done blueprint run found")
        continue
    est, run = pair
    res = run.get("result") or {}
    raw = res.get("raw_ai") or {}
    m = res.get("measurements") or {}
    ua = unattributed(raw)
    print(f"{h.upper()} · est {est.get('estimate_number')} · run "
          f"{run.get('run_id')[:8]} · {run.get('created_at')}")
    walls = [w for w in (raw.get("walls") or []) if isinstance(w, dict)]
    print("  widths:", {str(w.get("label")): w.get("width_ft") for w in walls})
    print("  heights:", {str(w.get("label")): w.get("height_ft") for w in walls})
    w_ua = {p: v for p, v in ua.items() if p.endswith("width_ft")}
    h_ua = {p: v for p, v in ua.items() if p.endswith("height_ft")}
    print(f"  UNATTRIBUTED widths ({len(w_ua)}):")
    for p, v in sorted(w_ua.items()):
        print(f"    {p} ← {v['quote']!r} p{v['page']} "
              f"competitors={v['competitors']} conflicting={v['conflicting']}")
    print(f"  UNATTRIBUTED heights ({len(h_ua)}):")
    for p, v in sorted(h_ua.items()):
        print(f"    {p} ← {v['quote']!r} p{v['page']} "
              f"competitors={v['competitors']} conflicting={v['conflicting']}")
    print("  QUANTITIES TODAY:")
    print("    siding_sqft:", m.get("siding_sqft"),
          "| starter_lf:", m.get("starter_lf"),
          "| perimeter:", m.get("footprint_perimeter_ft"),
          "| eaves_lf:", m.get("eaves_lf"), "| rakes_lf:", m.get("rakes_lf"),
          "| osc_lf:", m.get("outside_corner_lf"),
          "| isc_lf:", m.get("inside_corner_lf"))
    for d in (m.get("_wall_walk_detail") or []):
        print(f"    {d.get('label')}: body={d.get('body_sqft')} "
              f"gable={d.get('gable_sqft')} width={d.get('width_ft')} "
              f"body_refusal={bool(d.get('body_refusal'))}")
    # AT STAKE under the split: any width-derived quantity on an
    # unattributed face.
    ua_faces = {p.split(".")[1] for p in w_ua if p.startswith("walls.")}
    at_stake_gable = 0.0
    at_stake_body = 0.0
    for d in (m.get("_wall_walk_detail") or []):
        if str(d.get("label") or "").lower() in ua_faces:
            at_stake_gable += float(d.get("gable_sqft") or 0)
            at_stake_body += float(d.get("body_sqft") or 0)
    print(f"  AT STAKE on unattributed faces {sorted(ua_faces)}: "
          f"body {at_stake_body:.1f} ft² · gable {at_stake_gable:.1f} ft²")
