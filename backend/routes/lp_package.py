"""Iter 79j.93 — LP package preview endpoint (September package assembly, Phase 1)."""
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user
from lp_package import assemble_lp_package

router = APIRouter()


@router.post("/estimates/{est_id}/lp-package/preview")
async def lp_package_preview(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Assemble the LP-native package from an AI Measure run. `run_id`
    optional — falls back to the latest terminal run for this estimate."""
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0, "id": 1},
    )
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")

    q: dict = {"estimate_id": est_id, "status": "done"}
    run_id = (payload or {}).get("run_id")
    if run_id:
        q["run_id"] = run_id
    run = await db.ai_measure_runs.find_one(q, sort=[("created_at", -1)])
    if run is None:
        raise HTTPException(status_code=404, detail="No completed AI Measure run for this estimate")

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

    pkg = assemble_lp_package(measurements, corner_locations, wall_heights)
    pkg["run_id"] = run.get("run_id")
    return pkg
