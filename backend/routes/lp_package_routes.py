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
        q_est, {"_id": 0, "id": 1, "lp_pricing_tier": 1, "lp_field_verify": 1,
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


def _amber_items(corner_locations, verify_state):
    """Amber field-verify checklist (approved post-C4): the presence-
    guarantee doctrine surfaced to the user. Unconfirmed (amber) corner
    locations are INCLUDED in stick counts and flagged; a contractor
    ratifies each in the field. Verification is ratification only —
    counts never change here."""
    import re
    items = []
    for i, c in enumerate(corner_locations):
        if str(c.get("tier") or "confirmed") == "confirmed":
            continue
        locator = str(c.get("locator") or "").strip() or f"corner {i + 1}"
        kind = "ISC" if str(c.get("type") or "") == "inside" else "OSC"
        slug = re.sub(r"[^a-z0-9]+", "-", locator.lower()).strip("-")[:60]
        key = f"corner:{kind.lower()}:{slug}"
        st = (verify_state or {}).get(key) or {}
        items.append({
            "key": key, "kind": kind, "locator": locator,
            "walls": c.get("walls") or [],
            "status": st.get("status") or "unverified",
            "verified_at": st.get("at"), "verified_by": st.get("by"),
        })
    return items


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
    pkg["amber_items"] = _amber_items(corner_locations, est.get("lp_field_verify"))
    return redact_external(pkg)


@router.post("/estimates/{est_id}/lp-field-verify")
async def lp_field_verify(est_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Mark an amber item field-verified (or revert). Ratification only —
    stick counts already include ambers (presence guarantee)."""
    key = str((payload or {}).get("key") or "").strip()
    status = (payload or {}).get("status")
    if not key or "." in key or status not in ("verified", "unverified"):
        raise HTTPException(status_code=400, detail="key and status (verified|unverified) required")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0, "id": 1})
    if est is None:
        raise HTTPException(status_code=404, detail="Not found")
    from datetime import datetime, timezone
    if status == "verified":
        entry = {"status": "verified",
                 "at": datetime.now(timezone.utc).isoformat(),
                 "by": user.get("email") or user.get("id")}
        await db.estimates.update_one(
            {"id": est_id}, {"$set": {f"lp_field_verify.{key}": entry}})
        return {"ok": True, "key": key, **entry}
    await db.estimates.update_one(
        {"id": est_id}, {"$unset": {f"lp_field_verify.{key}": ""}})
    return {"ok": True, "key": key, "status": "unverified"}


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


def _pkg_content_hash(pkg: dict) -> str:
    """Canonical content hash for version comparison (frozen vs current)."""
    import hashlib
    import json as _json
    canon = {
        "lines": [[l.get("name"), l.get("qty"), l.get("unit"), l.get("color"),
                   l.get("unit_sell"), l.get("line_sell"), l.get("pricing_status")]
                  for l in pkg.get("lines") or []],
        "total_sell": (pkg.get("summary") or {}).get("pricing", {}).get("total_sell"),
    }
    return hashlib.sha256(_json.dumps(canon, sort_keys=True).encode()).hexdigest()


async def _derive_current(est_id: str, company_id=None):
    est, run = await _load_run(est_id, company_id)
    measurements, corner_locations, wall_heights = _extract(run)
    full_est = await db.estimates.find_one(
        {"id": est_id}, {"_id": 0, "lp_colors": 1, "lp_pricing_tier": 1,
                         "estimate_number": 1, "customer_name": 1,
                         "address": 1, "estimate_date": 1})
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              colors=(full_est or {}).get("lp_colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"))
    pkg = redact_external(pkg)
    pkg["run_id"] = run.get("run_id")
    return pkg, (full_est or {})


@router.post("/estimates/{est_id}/lp-material-list/freeze")
async def lp_material_list_freeze(
    est_id: str, payload: dict | None = None, user: dict = Depends(get_current_user),
):
    """Iter 100 — QR share (ruled, document doctrine): freeze the EXACT
    printed composition (colors + session substitutions) server-side and
    mint a tokenized, contractor-redacted, expiring read-only link. The
    link always resolves to THIS frozen version; the public view banners
    when a newer derivation exists — never a silent live view."""
    import secrets
    from datetime import datetime, timedelta, timezone

    est, run = await _load_run(est_id, user["company_id"], (payload or {}).get("run_id"))
    measurements, corner_locations, wall_heights = _extract(run)
    pkg = assemble_lp_package(measurements, corner_locations, wall_heights,
                              substitutions=(payload or {}).get("substitutions"),
                              colors=(payload or {}).get("colors"))
    cfg = await load_margin_cfg()
    price_package(pkg, cfg, est.get("lp_pricing_tier"))
    pkg = redact_external(pkg)  # frozen snapshot is ALWAYS the redacted view
    pkg["run_id"] = run.get("run_id")
    meta = await db.estimates.find_one(
        {"id": est_id}, {"_id": 0, "estimate_number": 1, "customer_name": 1,
                         "address": 1, "estimate_date": 1})
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(24)
    await db.lp_material_list_snapshots.insert_one({
        "token": token, "estimate_id": est_id, "company_id": user["company_id"],
        "snapshot": pkg, "meta": meta or {},
        "content_hash": _pkg_content_hash(pkg),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=90)).isoformat(),
        "revoked": False,
    })
    return {"token": token, "share_path": f"/m/{token}",
            "expires_at": (now + timedelta(days=90)).isoformat()}


@router.get("/public/lp-material-list/{token}")
async def lp_material_list_public(token: str):
    """Public, read-only, redacted. Frozen version + newer-available flag."""
    from datetime import datetime, timezone

    snap = await db.lp_material_list_snapshots.find_one({"token": token}, {"_id": 0})
    if not snap or snap.get("revoked"):
        raise HTTPException(status_code=404, detail="Link not found or revoked")
    if snap.get("expires_at") and snap["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=410, detail="Link expired")
    newer_available = False
    current = None
    try:
        current, _meta = await _derive_current(snap["estimate_id"])
        newer_available = _pkg_content_hash(current) != snap.get("content_hash")
    except HTTPException:
        current = None
    return {
        "frozen": snap["snapshot"], "meta": snap.get("meta") or {},
        "printed_at": snap.get("created_at"),
        "newer_available": newer_available,
        "current": current if newer_available else None,
    }


@router.post("/public/lp-material-list/{token}/request-update")
async def lp_material_list_request_update(token: str, request: Request):
    """Ruled scope: notifies the estimate's OWNER (the contractor) only,
    with version context attached — no other recipients, no marketing."""
    import asyncio
    from datetime import datetime, timezone

    from config import RESEND_API_KEY, SENDER_EMAIL

    snap = await db.lp_material_list_snapshots.find_one({"token": token}, {"_id": 0})
    if not snap or snap.get("revoked"):
        raise HTTPException(status_code=404, detail="Link not found or revoked")
    now = datetime.now(timezone.utc)
    last = snap.get("last_update_request_at")
    if last and (now - datetime.fromisoformat(last)).total_seconds() < 900:
        return {"ok": True, "throttled": True}
    if not RESEND_API_KEY:
        raise HTTPException(status_code=503, detail="Email is not configured")

    owner = await db.users.find_one(
        {"company_id": snap["company_id"], "role": "owner"},
        {"_id": 0, "email": 1, "name": 1})
    if not owner or not owner.get("email"):
        raise HTTPException(status_code=404, detail="Contractor contact not found")

    newer_available = False
    try:
        current, _m = await _derive_current(snap["estimate_id"])
        newer_available = _pkg_content_hash(current) != snap.get("content_hash")
    except HTTPException:
        pass

    meta = snap.get("meta") or {}
    est_num = meta.get("estimate_number") or "(no number)"
    printed = str(snap.get("created_at") or "")[:10]
    version_line = (
        "The estimate HAS CHANGED since this list was printed — the frozen printout is outdated."
        if newer_available else
        "The frozen printout still matches the current derivation — no drift detected."
    )
    origin = f"{request.url.scheme}://{request.url.netloc}"
    html = f"""<!doctype html>
<html><body style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#09090B;background:#F4F4F5;margin:0;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#FFFFFF;border:1px solid #09090B;padding:32px;">
    <div style="font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#F97316;margin-bottom:8px;">Material List — Update Requested</div>
    <h1 style="font-size:22px;margin:0 0 16px 0;color:#09090B;">Updated list requested for {est_num}</h1>
    <p style="font-size:15px;color:#52525B;line-height:1.6;">
      Someone viewing the printed material list (QR link) asked for the latest version.<br><br>
      <b style="color:#09090B;">Estimate:</b> {est_num} — {meta.get('customer_name') or ''}<br>
      <b style="color:#09090B;">Printed version:</b> {printed}<br>
      <b style="color:#09090B;">Version status:</b> {version_line}
    </p>
    <p style="font-size:14px;color:#52525B;">Open the estimate and print a fresh material list to issue a new frozen link:<br>
      <a href="{origin}/estimate/{snap['estimate_id']}" style="color:#C2410C;">{origin}/estimate/{snap['estimate_id']}</a></p>
  </div>
</body></html>"""
    import resend
    resend.api_key = RESEND_API_KEY
    await asyncio.to_thread(resend.Emails.send, {
        "from": SENDER_EMAIL,
        "to": [owner["email"]],
        "subject": f"Updated material list requested — {est_num}",
        "html": html,
    })
    await db.lp_material_list_snapshots.update_one(
        {"token": token}, {"$set": {"last_update_request_at": now.isoformat()}})
    return {"ok": True, "newer_available": newer_available}


@router.post("/estimates/{est_id}/lp-material-list/revoke")
async def lp_material_list_revoke(
    est_id: str, payload: dict, user: dict = Depends(get_current_user),
):
    token = str(payload.get("token") or "")
    res = await db.lp_material_list_snapshots.update_one(
        {"token": token, "estimate_id": est_id, "company_id": user["company_id"]},
        {"$set": {"revoked": True}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"revoked": True}


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
