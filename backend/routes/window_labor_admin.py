"""Contractor Window Quotes labor divergence — mechanism + admin preview
(approved 2026-07-15, GATE not companion).

Doctrine:
  • Side-by-side ISS vs Contractor labor with per-item deltas, admin
    boundary (X-Admin-Token), Quick Bump preview-before-apply pattern
    applied to labor.
  • NO diverged rate reaches any contractor-visible surface until the
    diff is reviewed and APPROVED. `approved_contractor_window_labor()`
    is the only sanctioned consumer and returns {} until then.
  • Divergence VALUES are HELD pending Howard's rate ruling (direction,
    structure, magnitude) — the draft starts empty; approve on an empty
    draft is a 400.
  • Any draft edit re-opens the gate (status back to draft).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from catalog_seed import ITEM_META, SECTION_LAYOUT, SECTION_PRODUCT_LINES, WINDOW_ADDERS
from db import db

router = APIRouter()

DOC_ID = "window_labor_divergence"


def _iss_labor_rows():
    """Labor-carrying rows on the windows tab — the shared (ISS) rates
    contractor Window Quotes currently mirror."""
    rows, seen = [], set()
    for title, _ascend, item_names in SECTION_LAYOUT:
        if "windows" not in SECTION_PRODUCT_LINES.get(title, []):
            continue
        for n in item_names:
            unit, lab = ITEM_META.get(n, ("Each", 0))
            if float(lab or 0) > 0 and n not in seen:
                seen.add(n)
                rows.append({"name": n, "section": title, "unit": unit,
                             "kind": "item", "iss_lab": round(float(lab), 2)})
        for a in WINDOW_ADDERS.get(title, []):
            if float(a.get("lab") or 0) > 0:
                key = f"{title} :: {a['name']}"
                if key not in seen:
                    seen.add(key)
                    rows.append({"name": key, "section": title, "unit": a.get("unit"),
                                 "kind": "adder", "iss_lab": round(float(a["lab"]), 2)})
    return rows


async def _load_doc():
    return (await db.admin_settings.find_one({"id": DOC_ID}, {"_id": 0})
            or {"id": DOC_ID, "proposed": {}, "status": "draft"})


async def approved_contractor_window_labor() -> dict:
    """The gate's only sanctioned consumer (future contractor-windows
    catalog serving — NEVER ISS surfaces). Empty until approved."""
    doc = await db.admin_settings.find_one({"id": DOC_ID}, {"_id": 0})
    if not doc or doc.get("status") != "approved":
        return {}
    return doc.get("proposed") or {}


@router.get("/admin/window-labor/compare")
async def window_labor_compare(request: Request):
    from deps import check_admin_token
    check_admin_token(request)
    doc = await _load_doc()
    proposed = doc.get("proposed") or {}
    rows = []
    for r in _iss_labor_rows():
        p = proposed.get(r["name"])
        row = {**r, "proposed_lab": p}
        if isinstance(p, (int, float)):
            row["delta_usd"] = round(p - r["iss_lab"], 2)
            row["delta_pct"] = round((p - r["iss_lab"]) / r["iss_lab"] * 100, 1) if r["iss_lab"] else None
        rows.append(row)
    return {
        "rows": rows,
        "status": doc.get("status", "draft"),
        "approved_at": doc.get("approved_at"),
        "updated_at": doc.get("updated_at"),
        "values_held": not proposed,
    }


@router.put("/admin/window-labor/draft")
async def window_labor_draft(payload: dict, request: Request):
    from deps import check_admin_token
    check_admin_token(request)
    changes = (payload or {}).get("proposed")
    if not isinstance(changes, dict) or not changes:
        raise HTTPException(status_code=400, detail="proposed (dict of item → rate or null) required")
    valid = {r["name"] for r in _iss_labor_rows()}
    doc = await _load_doc()
    proposed = dict(doc.get("proposed") or {})
    for name, v in changes.items():
        if name not in valid:
            raise HTTPException(status_code=400, detail=f"unknown windows labor item: {name}")
        if v is None:
            proposed.pop(name, None)
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"rate for {name} must be a number")
        if not (0.0 <= v <= 10000.0):
            raise HTTPException(status_code=400, detail=f"rate for {name} must be within 0..10000")
        proposed[name] = round(v, 2)
    now = datetime.now(timezone.utc).isoformat()
    # any edit re-opens the gate
    await db.admin_settings.update_one(
        {"id": DOC_ID},
        {"$set": {"proposed": proposed, "status": "draft", "updated_at": now},
         "$unset": {"approved_at": ""}},
        upsert=True)
    return {"ok": True, "count": len(proposed), "status": "draft"}


@router.post("/admin/window-labor/approve")
async def window_labor_approve(request: Request):
    from deps import check_admin_token
    check_admin_token(request)
    doc = await _load_doc()
    if not (doc.get("proposed") or {}):
        raise HTTPException(
            status_code=400,
            detail="Nothing to approve — divergence values are held pending the rate ruling; enter draft rates first")
    now = datetime.now(timezone.utc).isoformat()
    await db.admin_settings.update_one(
        {"id": DOC_ID},
        {"$set": {"status": "approved", "approved_at": now}},
        upsert=True)
    return {"ok": True, "status": "approved", "approved_at": now,
            "count": len(doc.get("proposed") or {})}
