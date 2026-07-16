"""Public (no-auth) endpoints for customer-side actions:
- GET /api/public/accept/{token}   — render the accept page data
- POST /api/public/accept/{token}  — record acceptance + notify contractor
- POST /api/public/resend-webhook  — receive Resend open/click events
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from config import RESEND_API_KEY, SENDER_EMAIL
from db import db, logger
from estimate_events import log_estimate_event
from models import CustomerAcceptIn

router = APIRouter()


def _public_estimate_summary(est: dict, company: dict | None) -> dict:
    """Strip the estimate down to what's safe to show a customer who knows the token."""
    return {
        "estimate_number": est.get("estimate_number") or "",
        "customer_name": est.get("customer_name") or "",
        "address": est.get("address") or "",
        "estimate_date": est.get("estimate_date") or "",
        "company_name": (company or {}).get("name") or "your contractor",
        "company_logo_url": (company or {}).get("logo_url"),
        "already_accepted": bool(est.get("accepted_at")),
        "accepted_at": est.get("accepted_at"),
        "accept_token": est.get("accept_token"),
    }


# Accept-page 3D ruling (2026-07-15): the house renders in its RATIFIED
# state — review overlays pre-applied server-side, then every
# verification/tier/provenance field is stripped so no per-feature chip
# or internal state label can reach a customer surface.
_SAFE_CORNER_FIELDS = ("locator", "type", "walls", "position_frac")
_SAFE_WALL_FIELDS = (
    "label", "width_ft", "width_ft_source", "height_ft", "height_ft_source",
    "height_scale_flag", "gable_triangle_height_ft", "dormer_face_sqft",
    "siding_pct_this_wall",
)
_SAFE_OPENING_FIELDS = (
    "type", "style", "width_in", "height_in", "wall", "on_dormer",
    "along_wall_ft", "opening_id",
)


async def _customer_house3d(est: dict):
    """Sanitized 3D payload + whether any amber location remains
    unratified (drives the softened homeowner footnote)."""
    est_ids = [est.get("id")]
    for k in ("paired_lp_estimate_id", "paired_estimate_id"):
        if est.get(k):
            est_ids.append(est[k])
    run = None
    for coll in (db.ai_measure_runs, db.ai_blueprint_runs):
        run = await coll.find_one(
            {"estimate_id": {"$in": est_ids}, "status": "done"},
            {"_id": 0, "result": 1}, sort=[("created_at", -1)])
        if run and (run.get("result") or {}).get("raw_ai"):
            break
        run = None
    if not run:
        return None, False
    result = run["result"]
    raw = result.get("raw_ai") or {}
    from routes.ai_measure import strip_cost_keys
    from routes.lp_package_routes import _apply_corner_review, _corner_key, _DIM_STATUSES
    fv = est.get("lp_field_verify") or {}
    corners_raw = raw.get("corner_locations") or []
    unratified = False
    for i, c in enumerate(corners_raw):
        if str(c.get("tier") or "confirmed") == "confirmed":
            continue
        key, _, _ = _corner_key(c, i)
        if (fv.get(key) or {}).get("status") not in ("verified", "user_relocated", "user_removed"):
            unratified = True
            break
    corners = [
        {k: c.get(k) for k in _SAFE_CORNER_FIELDS if c.get(k) is not None}
        for c in _apply_corner_review(corners_raw, fv)
    ]
    dims = {}
    for key, fields in (est.get("lp_appendage_dims") or {}).items():
        wall = str(key).split(":", 1)[-1]
        for f in ("height_ft", "depth_ft"):
            e = (fields or {}).get(f) or {}
            if e.get("status") in _DIM_STATUSES and (e.get("value") or 0) > 0:
                dims.setdefault(wall, {})[f] = float(e["value"])
    measurements = strip_cost_keys(dict(result.get("measurements") or {}))
    measurements = {
        k: v for k, v in measurements.items()
        if "reconciliation" not in k and "transport" not in k and k != "_per_elevation_breakdown"
    }
    house3d = {
        "measurements": measurements,
        "raw_ai": {
            "roof_pitch": raw.get("roof_pitch"),
            "walls": [
                {**{k: w.get(k) for k in _SAFE_WALL_FIELDS if w.get(k) is not None},
                 "accent_profiles": [
                     {"location": a.get("location"), "approx_sqft": a.get("approx_sqft")}
                     for a in (w.get("accent_profiles") or [])
                 ]}
                for w in (raw.get("walls") or [])
            ],
            "openings": [
                {k: o.get(k) for k in _SAFE_OPENING_FIELDS if o.get(k) is not None}
                for o in (raw.get("openings") or [])
            ],
            "corner_locations": corners,
            "appendages": raw.get("appendages") or [],
        },
        "dims": dims,
    }
    return house3d, unratified


async def _attestation(est: dict):
    """Aggregate attestation (ruled 2026-07-15): trust is carried ONCE —
    'N locations field-confirmed, initials, date' — never per-feature."""
    fv = est.get("lp_field_verify") or {}
    conf = [v for v in fv.values() if (v or {}).get("status") in ("verified", "user_relocated")]
    if not conf:
        return None
    conf.sort(key=lambda v: v.get("at") or "", reverse=True)
    by = next((v.get("by") for v in conf if v.get("by")), None)
    initials = ""
    if by:
        u = await db.users.find_one({"email": by}, {"_id": 0, "name": 1})
        base = (u or {}).get("name") or str(by).split("@")[0]
        parts = [p for p in base.replace(".", " ").split() if p]
        initials = "".join(p[0] for p in parts[:2]).upper()
    return {"count": len(conf), "initials": initials, "date": (conf[0].get("at") or "")[:10]}


@router.get("/public/accept/{token}")
async def public_get_accept(token: str):
    est = await db.estimates.find_one({"accept_token": token}, {"_id": 0})
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found or link expired")
    company = await db.companies.find_one(
        {"id": est["company_id"]}, {"_id": 0, "name": 1, "logo_url": 1}
    )
    # Customer also needs to see the total — compute it server-side so the link is self-contained.
    from services import calc_totals
    totals = calc_totals(est)
    summary = _public_estimate_summary(est, company)
    # Supplier co-brand (clarity ruling 2026-07-16 S6)
    from routes.branding import SUPPLIER_NAME, get_branding
    b = await get_branding()
    summary["supplier_name"] = b.get("supplier_name") or SUPPLIER_NAME
    summary["total"] = round(totals["sell"], 2)
    # Interactive 3D (ruled 2026-07-15): ratified state, no per-feature
    # chips; softened footnote when details remain to confirm on site.
    house3d, unratified = await _customer_house3d(est)
    if house3d:
        summary["house3d"] = house3d
        summary["on_site_note"] = bool(unratified or est.get("model3d_unverified"))
    summary["attestation"] = await _attestation(est)
    # Split ruling 2026-07-14 — customer opened the quote link. Logged
    # server-side only; the response never reveals tracking exists.
    await log_estimate_event(est.get("id"), "quote.viewed", {"surface": "accept_page"})
    return summary


@router.post("/public/accept/{token}")
async def public_post_accept(token: str, body: CustomerAcceptIn, request: Request):
    est = await db.estimates.find_one({"accept_token": token}, {"_id": 0})
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found or link expired")
    if est.get("accepted_at"):
        # Idempotent — return the existing acceptance instead of erroring out.
        company = await db.companies.find_one(
            {"id": est["company_id"]}, {"_id": 0, "name": 1}
        )
        return {
            "ok": True,
            "already_accepted": True,
            "company_name": (company or {}).get("name") or "your contractor",
            "accepted_at": est.get("accepted_at"),
        }

    # Record acceptance
    now = datetime.now(timezone.utc).isoformat()
    client_ip = request.client.host if request.client else None
    accepted_note = (body.note or "").strip() or None
    await db.estimates.update_one(
        {"accept_token": token},
        {"$set": {
            "accepted_at": now,
            "accepted_ip": client_ip,
            "accepted_note": accepted_note,
            "status_label": "accepted",
        }},
    )
    # Split ruling 2026-07-14 — customer-journey event record
    await log_estimate_event(est.get("id"), "quote.accepted")

    company = await db.companies.find_one(
        {"id": est["company_id"]}, {"_id": 0, "name": 1}
    )
    company_name = (company or {}).get("name") or "your contractor"

    # Best-effort: email the company owner
    if RESEND_API_KEY:
        try:
            owner = await db.users.find_one(
                {"company_id": est["company_id"], "role": "owner"},
                {"_id": 0, "email": 1, "name": 1},
            )
            if owner and owner.get("email"):
                from services import calc_totals
                totals = calc_totals(est)
                est_num = est.get("estimate_number") or "(no number)"
                cust = est.get("customer_name") or "your customer"
                total_str = f"${totals['sell']:,.2f}"
                note_block = (
                    f"<p><b>Customer note:</b><br>{(accepted_note or '').replace(chr(10), '<br>') }</p>"
                    if accepted_note else ""
                )
                html = f"""<!doctype html>
<html><body style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#09090B;background:#F4F4F5;margin:0;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#FFFFFF;border:1px solid #09090B;padding:32px;">
    <div style="font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;color:#F97316;margin-bottom:8px;">Estimate Accepted</div>
    <h1 style="font-size:24px;margin:0 0 16px 0;color:#09090B;">{cust} accepted {est_num}</h1>
    <p style="font-size:16px;color:#52525B;line-height:1.6;">
      <b style="color:#09090B;">Total:</b> {total_str}<br>
      <b style="color:#09090B;">Accepted:</b> {now[:19].replace('T',' ')} UTC<br>
      <b style="color:#09090B;">IP:</b> {client_ip or 'unknown'}
    </p>
    {note_block}
    <p style="font-size:13px;color:#71717A;margin-top:24px;">Sent automatically via Pro-Quote Estimating Tool on behalf of {company_name}.</p>
  </div>
</body></html>"""
                import resend
                resend.api_key = RESEND_API_KEY
                await asyncio.to_thread(
                    resend.Emails.send,
                    {
                        "from": SENDER_EMAIL,
                        "to": [owner["email"]],
                        "subject": f"✅ Estimate {est_num} accepted by {cust}",
                        "html": html,
                    },
                )
        except Exception:
            logger.exception("acceptance notification email failed (non-fatal)")

    return {
        "ok": True,
        "already_accepted": False,
        "company_name": company_name,
        "accepted_at": now,
    }
