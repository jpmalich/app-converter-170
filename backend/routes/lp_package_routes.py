"""Iter 79j.93 — LP package preview endpoint (September package assembly, Phase 1).
Iter 79j.94 — truck-list reconciliation endpoint (pre-±3% acceptance harness).
Iter 79j.96 — confidential cost layer + tiered sell pricing. Contractor-facing
preview is ALWAYS redacted (sell only); the unredacted cost view exists only
behind the supplier-admin token."""
from fastapi import APIRouter, Depends, HTTPException, Request

from db import db
from deps import check_admin_token, get_current_user
from lp_costs import price_package, redact_external
from lp_package import assemble_lp_package
from lp_truck_reconcile import reconcile_letrick_truck
from routes.lp_admin import load_margin_cfg

router = APIRouter()


async def _load_run(est_id: str, company_id=None, run_id=None):
    """company_id=None is the supplier-admin path (token-checked upstream).
    Falls back to the PAIRED estimate's runs — a paired LP estimate's AI
    Measure run lives on its siding source (pair-lp flow)."""
    q_est: dict = {"id": est_id}
    if company_id is not None:
        q_est["company_id"] = company_id
    est = await db.estimates.find_one(
        q_est, {"_id": 0, "id": 1, "lp_pricing_tier": 1,
                "paired_lp_estimate_id": 1, "paired_estimate_id": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    q: dict = {"estimate_id": est_id, "status": "done"}
    if run_id:
        q["run_id"] = run_id
    run = await db.ai_measure_runs.find_one(q, sort=[("created_at", -1)])
    paired_id = est.get("paired_lp_estimate_id") or est.get("paired_estimate_id")
    if run is None and paired_id and not run_id:
        paired_q: dict = {"id": paired_id}
        if company_id is not None:
            paired_q["company_id"] = company_id
        paired = await db.estimates.find_one(paired_q, {"_id": 0, "id": 1})
        if paired:
            run = await db.ai_measure_runs.find_one(
                {"estimate_id": paired["id"], "status": "done"},
                sort=[("created_at", -1)])
    if run is None:
        raise HTTPException(status_code=404, detail="No completed AI Measure run for this estimate")
    return est, run


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


@router.get("/lp-package/colors")
async def lp_package_colors(user: dict = Depends(get_current_user)):
    """ExpertFinish palette + component groups for the Material List
    color selector. Names are the backend source of truth; swatch hexes
    are frontend visualization approximations."""
    from lp_colors import (ALL_COLORS, COMPONENT_GROUPS, EXPERTFINISH_CORE_16,
                           NATURALS_COLLECTION, PRIMED)
    return {
        "groups": list(COMPONENT_GROUPS),
        "colors": ALL_COLORS,
        "collections": {"core": EXPERTFINISH_CORE_16,
                        "naturals": NATURALS_COLLECTION, "primed": PRIMED},
    }


@router.post("/estimates/{est_id}/lp-package/preview")
async def lp_package_preview(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Assemble the LP-native package from an AI Measure run. `run_id`
    optional — falls back to the latest terminal run. `substitutions`
    optional {line_name: new_item} — table-limited, re-derived, provenance-
    carried, never remembered. `colors` optional {"all": X, group: Y} —
    per-component line-level colors (Howard's color architecture).
    PRICING: sell prices at the estimate's admin-assigned tier (default
    Tier B/25%) — the payload can NEVER set a tier or margin here; the
    tier picker is admin-side only. Response is ALWAYS redacted:
    cost / margin / tier never leave the server on this surface."""
    est, run = await _load_run(est_id, user["company_id"], (payload or {}).get("run_id"))
    measurements, corner_locations, wall_heights = _extract(run)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"))
    pkg["run_id"] = run.get("run_id")
    return redact_external(pkg)


@router.post("/admin/estimates/{est_id}/lp-package/cost-preview")
async def lp_package_cost_preview(est_id: str, request: Request, payload: dict | None = None):
    """SUPPLIER-ADMIN ONLY (X-Admin-Token): the unredacted package with
    the confidential cost layer — dealer cost, margin, tier resolution.
    This payload must never be proxied to a contractor surface."""
    check_admin_token(request)
    est, run = await _load_run(est_id, None, (payload or {}).get("run_id"))
    measurements, corner_locations, wall_heights = _extract(run)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, (payload or {}).get("tier") or est.get("lp_pricing_tier"))
    pkg["run_id"] = run.get("run_id")
    return pkg


@router.post("/estimates/{est_id}/lp-package/truck-reconcile")
async def lp_truck_reconcile_endpoint(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Letrick truck-list acceptance harness — derives each delivered
    line from the conventions layer + validated geometry, deviations
    itemized per line with cause. Runs BEFORE the ±3% acceptance test."""
    _est, run = await _load_run(est_id, user["company_id"], (payload or {}).get("run_id"))
    measurements, corner_locations, _ = _extract(run)
    raw_ai = (run.get("result") or {}).get("raw_ai") or {}
    window_widths = [float(o.get("width_in") or 0) / 12.0
                     for o in raw_ai.get("openings") or []
                     if str(o.get("type")) == "window" and o.get("width_in")]
    out = reconcile_letrick_truck(measurements, corner_locations, window_widths)
    out["run_id"] = run.get("run_id")
    return out
