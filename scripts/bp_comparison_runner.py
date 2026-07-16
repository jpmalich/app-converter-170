"""Fire the 6 pre-registered blueprint comparison runs (3× Opus 4.5, 3× Fable 5).

Interleaved order O,F,O,F,O,F to smooth time-of-day API drift. Sequential —
one run in flight at a time. Results dumped to /app/memory/bp_comparison_runs/.
"""
import json
import os
import pathlib
import time

import requests

API = "https://app-converter-170.preview.emergentagent.com/api"
PREV_RUN = "e4afda3a64a54439b02b5c609dda0b69"
OUT = pathlib.Path("/app/memory/bp_comparison_runs")
OUT.mkdir(parents=True, exist_ok=True)

ORDER = [
    ("run1_opus", "claude-opus-4-5-20251101"),
    ("run2_fable", "claude-fable-5"),
    ("run3_opus", "claude-opus-4-5-20251101"),
    ("run4_fable", "claude-fable-5"),
    ("run5_opus", "claude-opus-4-5-20251101"),
    ("run6_fable", "claude-fable-5"),
]

s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": os.environ.get("ADMIN_PASSWORD") or __import__("dotenv").dotenv_values("/app/backend/.env").get("ADMIN_PASSWORD")}, timeout=30)
r.raise_for_status()
tok = r.json().get("token") or r.json().get("access_token")
s.headers["Authorization"] = f"Bearer {tok}"

for tag, model in ORDER:
    dest = OUT / f"{tag}.json"
    if dest.exists():
        print(f"{tag}: already done, skipping")
        continue
    print(f"=== {tag} ({model}) firing...", flush=True)
    t0 = time.time()
    r = s.post(f"{API}/measure/ai-blueprint/rerun/{PREV_RUN}", json={"model_key": model}, timeout=60)
    if r.status_code != 200:
        print(f"{tag}: LAUNCH FAILED {r.status_code} {r.text[:300]}")
        break
    run_id = r.json()["run_id"]
    print(f"{tag}: run_id={run_id}", flush=True)
    status = None
    for _ in range(80):
        time.sleep(6)
        st = s.get(f"{API}/measure/ai-blueprint/status/{run_id}", timeout=30).json()
        status = st.get("status")
        if status in ("done", "error"):
            break
    wall = time.time() - t0
    if status != "done":
        print(f"{tag}: FAILED status={status} error={st.get('error')}")
        dest.with_suffix(".error.json").write_text(json.dumps(st, default=str, indent=1))
        continue
    res = st["result"]
    dest.write_text(json.dumps({
        "tag": tag, "model": model, "run_id": run_id,
        "wall_clock_s": round(wall, 1),
        "elapsed_ms": st.get("elapsed_ms"),
        "token_usage": res.get("token_usage"),
        "cost_usd": res.get("cost_usd"),
        "transport": res.get("transport"),
        "measurements": res.get("measurements"),
        "raw_ai": res.get("raw_ai"),
    }, default=str))
    m = res.get("measurements") or {}
    print(f"{tag}: DONE wall={wall:.0f}s cost=${res.get('cost_usd')} transport={res.get('transport')} "
          f"siding={m.get('siding_sqft')} osc={m.get('outside_corner_count')} "
          f"win={m.get('window_count')} entry={m.get('entry_door_count')} patio={m.get('patio_door_count')}", flush=True)

print("ALL DONE")
