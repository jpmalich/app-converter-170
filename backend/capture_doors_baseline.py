"""3-DOORS BUILD — byte-identical baseline capture (Howard's standing constraint).
Derives, for every ground-truth estimate, the FULL engine output off its stored
measurements / governing run: _build_lines + rebuild_lp_tab_lines. Run BEFORE and
AFTER each build step; diff the JSON byte-for-byte. Any move must be a named
ruled fix."""
import asyncio, os, sys, json, hashlib
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# estimate_number -> label
GROUND_TRUTH = {
    "EST-523061": "casile_lp",
    "EST-562488": "3degree_lp",
    "EST-109465": "3degree_lp_8am",
    "EST-630295": "3degree_lp_1pm",
    "EST-979583": "3degree_vinyl",
}
HAUGH_CUSTOMER = "261 Haugh Dr — round t"


async def main(outfile):
    from motor.motor_asyncio import AsyncIOMotorClient
    from routes.hover import _build_lines, rebuild_lp_tab_lines
    db_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = db_client[os.environ["DB_NAME"]]
    out = {}
    ests = await db.estimates.find({}, {"_id": 0}).to_list(300)
    for e in ests:
        num = e.get("estimate_number") or ""
        label = GROUND_TRUTH.get(num)
        if not label and "261 haugh" in str(e.get("customer_name") or "").lower():
            label = f"haugh_{(e.get('kind') or 'siding')}_{(num or e['id'][:6])}"
        if not label:
            continue
        meas = e.get("hover_measurements") or None
        if not meas and e.get("lp_source_run_id"):
            gov = await db.ai_measure_runs.find_one({"run_id": e["lp_source_run_id"]}) \
                or await db.run_archive.find_one({"run_id": e["lp_source_run_id"]})
            if gov:
                meas = ((gov.get("result") or {}).get("measurements")) or None
        if not meas:
            run = await db.ai_measure_runs.find_one(
                {"estimate_id": e["id"], "status": "done"}, sort=[("created_at", -1)])
            if run:
                meas = ((run.get("result") or {}).get("measurements")) or None
        entry = {"estimate_number": num, "kind": e.get("kind"),
                 "stored_lines_sha": hashlib.sha256(
                     json.dumps(e.get("lines") or [], sort_keys=True, default=str).encode()
                 ).hexdigest()[:16]}
        if meas:
            bl = _build_lines(dict(meas))
            entry["build_lines"] = bl
            entry["build_lines_sha"] = hashlib.sha256(
                json.dumps(bl, sort_keys=True, default=str).encode()).hexdigest()[:16]
            try:
                tab_lines, _scoped = await rebuild_lp_tab_lines(
                    est_id=e["id"], company_id=e["company_id"],
                    base_measurements=dict(meas), est=e,
                    profile=e.get("default_siding_profile") if e.get("kind") == "lp_smart" else None,
                    waste_field=float(e.get("waste_pct") or 0))
                entry["rebuild_lines"] = tab_lines
                entry["rebuild_sha"] = hashlib.sha256(
                    json.dumps(tab_lines, sort_keys=True, default=str).encode()).hexdigest()[:16]
            except Exception as ex:
                entry["rebuild_error"] = f"{type(ex).__name__}: {ex}"
        else:
            entry["note"] = "no stored measurements and no done run"
        out[label] = entry
    with open(outfile, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True, default=str)
    for k, v in sorted(out.items()):
        print(f"{k:28} bl_sha={v.get('build_lines_sha','-'):16} rebuild_sha={v.get('rebuild_sha','-'):16} {v.get('rebuild_error','') or v.get('note','')}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "/app/memory/evidence/doors_baseline.json"))
