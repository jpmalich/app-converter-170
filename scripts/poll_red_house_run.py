#!/usr/bin/env python3
"""Poll Mongo for the newest Red-House confirmation run and dump a full
gate-report the moment it completes (or errors).

Usage: python3 /app/scripts/poll_red_house_run.py
Writes: /tmp/red_house_gate_report.json  (also tails to stdout)
"""
import os, json, time, sys
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
client = MongoClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

RED_HOUSE_EID = "673707d5-9b7e-4d8f-8eaf-63c86820f611"
POLL_S = 10
MAX_WAIT_S = 45 * 60  # 45 min guardrail
started = time.time()
start_wall = datetime.now(timezone.utc)

print(f"[poll] watching estimate_id={RED_HOUSE_EID} since {start_wall.isoformat()}", flush=True)

# baseline: newest run for this estimate BEFORE we start watching
baseline = db.ai_measure_runs.find_one(
    {"estimate_id": RED_HOUSE_EID},
    sort=[("created_at", -1)],
)
baseline_id = baseline.get("run_id") if baseline else None
baseline_created = baseline.get("created_at") if baseline else None
print(f"[poll] baseline run_id={baseline_id} created_at={baseline_created}", flush=True)

new_run = None
while time.time() - started < MAX_WAIT_S:
    q = {"estimate_id": RED_HOUSE_EID}
    if baseline_created:
        q["created_at"] = {"$gt": baseline_created}
    cand = db.ai_measure_runs.find_one(q, sort=[("created_at", -1)])
    if cand:
        rid = cand.get("run_id")
        status = cand.get("status")
        print(f"[poll] {datetime.now().strftime('%H:%M:%S')} run_id={rid} status={status}", flush=True)
        if status in ("done", "error", "failed"):
            new_run = cand
            break
    time.sleep(POLL_S)

if not new_run:
    print("[poll] TIMEOUT — no new run detected inside the 45-min window", flush=True)
    sys.exit(1)

# ---------- Build gate report ----------
raw_ai = new_run.get("raw_ai") or {}
walls = raw_ai.get("walls") or []
opns = raw_ai.get("openings") or []
dorms = raw_ai.get("dormers") or []

dormer_report = []
for i, d in enumerate(dorms):
    dormer_report.append({
        "idx": i,
        "face": d.get("face"),
        "width_ft": d.get("width_ft"),
        "width_source": d.get("width_source"),
        "source_photo_indices": d.get("_source_photo_indices"),
        "taped_baseline_ft": 15.0,
        "delta_ft": (round(d.get("width_ft") - 15.0, 2) if isinstance(d.get("width_ft"), (int, float)) else None),
        "within_1ft": (isinstance(d.get("width_ft"), (int, float)) and abs(d.get("width_ft") - 15.0) <= 1.0),
    })

created = new_run.get("created_at")
completed = new_run.get("completed_at") or new_run.get("finished_at")
wall_clock_s = None
if created and completed:
    try:
        wall_clock_s = (completed - created).total_seconds()
    except Exception:
        wall_clock_s = None

report = {
    "run_id": new_run.get("run_id"),
    "estimate_id": new_run.get("estimate_id"),
    "status": new_run.get("status"),
    "created_at": str(created),
    "completed_at": str(completed),
    "wall_clock_seconds": wall_clock_s,
    "wall_clock_minutes": (round(wall_clock_s/60, 2) if wall_clock_s else None),
    "_transport": new_run.get("_transport"),
    "_phase_a_transport": new_run.get("_phase_a_transport"),
    "_phase_b_transport": new_run.get("_phase_b_transport"),
    "_phase_a_ms": new_run.get("_phase_a_ms"),
    "_phase_b_ms": new_run.get("_phase_b_ms"),
    "_reconciliation_error": new_run.get("_reconciliation_error"),
    "scale_refs": {
        "_scale_refs_used": raw_ai.get("_scale_refs_used"),
        "_scale_refs_cited": raw_ai.get("_scale_refs_cited"),
        "_reconcile_notes": (raw_ai.get("_reconcile_notes") or "")[:800],
    },
    "extraction_counts": {
        "walls": len(walls),
        "openings": len(opns),
        "dormers": len(dorms),
        "_empty_photos": raw_ai.get("_empty_photos") or [],
        "_orphaned_walls": raw_ai.get("_orphaned_walls") or [],
    },
    "dormers": dormer_report,
    "gate_verdict": {
        "both_dormers_within_1ft": (
            len(dormer_report) >= 2 and all(d["within_1ft"] for d in dormer_report[:2])
        ),
        "scale_refs_used": bool(raw_ai.get("_scale_refs_used")),
        "phase_b_direct": (new_run.get("_phase_b_transport") == "anthropic_direct"),
        "no_empty_photos": len(raw_ai.get("_empty_photos") or []) == 0,
        "no_orphaned_walls": len(raw_ai.get("_orphaned_walls") or []) == 0,
        "wall_clock_under_5min": (wall_clock_s is not None and wall_clock_s < 300),
        "status_done": (new_run.get("status") == "done"),
    },
}
report["gate_verdict"]["ALL_PASS"] = all(report["gate_verdict"].values())

out_path = "/tmp/red_house_gate_report.json"
with open(out_path, "w") as f:
    json.dump(report, f, indent=2, default=str)

print("=" * 70, flush=True)
print("GATE REPORT", flush=True)
print("=" * 70, flush=True)
print(json.dumps(report, indent=2, default=str), flush=True)
print(f"\n[poll] report written to {out_path}", flush=True)
