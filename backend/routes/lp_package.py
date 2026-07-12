"""Iter 79j.93 — LP package preview endpoint (September package assembly, Phase 1).
Iter 79j.94 — truck-list reconciliation endpoint (pre-±3% acceptance harness)."""
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user
from lp_package import assemble_lp_package
from lp_truck_reconcile import reconcile_letrick_truck

router = APIRouter()


async def _load_run(est_id: str, user: dict, run_id=None):
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0, "id": 1},
    )
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    q: dict = {"estimate_id": est_id, "status": "done"}
    if run_id:
        q["run_id"] = run_id
    run = await db.ai_measure_runs.find_one(q, sort=[("created_at", -1)])
    if run is None:
        raise HTTPException(status_code=404, detail="No completed AI Measure run for this estimate")
    return run


def _extract(run: dict):
    result = run.get("result") or {}
    measurements = result.get("measurements") or {}
    raw_ai = result.get("raw_ai") or {}
    corner_locations = raw_ai.get("corner_locations") or []
    wall_heights = {}
    for w in raw_ai.get("walls") or []:
        lbl = str(w.get("label") or "").strip().lower()
        try:
            h = float(w.get("height_ft") or 0)
        except (TypeError, ValueError):
            h = 0
        if lbl and h > 0:
            wall_heights[lbl] = h
    return measurements, corner_locations, wall_heights


@router.post("/estimates/{est_id}/lp-package/preview")
async def lp_package_preview(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Assemble the LP-native package from an AI Measure run. `run_id`
    optional — falls back to the latest terminal run. `substitutions`
    optional {line_name: new_item} — table-limited, re-derived, provenance-
    carried, never remembered. `colors` optional {"all": X, group: Y} —
    per-component line-level colors (Howard's color architecture)."""
    run = await _load_run(est_id, user, (payload or {}).get("run_id"))
    measurements, corner_locations, wall_heights = _extract(run)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    pkg["run_id"] = run.get("run_id")
    return pkg


@router.post("/estimates/{est_id}/lp-package/truck-reconcile")
async def lp_truck_reconcile_endpoint(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Letrick truck-list acceptance harness — derives each delivered
    line from the conventions layer + validated geometry, deviations
    itemized per line with cause. Runs BEFORE the ±3% acceptance test."""
    run = await _load_run(est_id, user, (payload or {}).get("run_id"))
    measurements, corner_locations, _ = _extract(run)
    raw_ai = (run.get("result") or {}).get("raw_ai") or {}
    window_widths = [float(o.get("width_in") or 0) / 12.0
                     for o in raw_ai.get("openings") or []
                     if str(o.get("type")) == "window" and o.get("width_in")]
    out = reconcile_letrick_truck(measurements, corner_locations, window_widths)
    out["run_id"] = run.get("run_id")
    return out
