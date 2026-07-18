"""Public branding + supplier-admin endpoints."""
import asyncio
import html as html_lib
import uuid
from datetime import datetime, timezone
from urllib.parse import quote as urlquote

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from config import (
    SUPPLIER_NAME,
    SUPPLIER_TAGLINE,
    SIGNUP_CODE,
    UPLOAD_DIR,
    RESEND_API_KEY,
    SENDER_EMAIL,
)
from db import db, logger
from deps import check_admin_token
from models import BrandingUpdate, InviteContractorIn
from services import get_branding

router = APIRouter()


@router.get("/branding")
async def public_branding():
    b = await get_branding()
    from routes.lp_admin import load_lp_native_mode
    return {
        "supplier_name": b.get("supplier_name") or SUPPLIER_NAME,
        "supplier_tagline": b.get("supplier_tagline") or SUPPLIER_TAGLINE,
        "supplier_logo_url": b.get("supplier_logo_url"),
        "default_pricing_mode": b.get("default_pricing_mode") or "margin",
        "lp_native_mode": await load_lp_native_mode(),
    }


@router.get("/admin/fixture-runs/test-artifacts")
async def admin_list_test_artifacts(request: Request):
    """Admin purge view (ruled 2026-07-18) — tagged test debris in the
    no-TTL fixture_runs archive. fixture_runs access stays owned by
    run_archive (fork-boundary discipline)."""
    check_admin_token(request)
    from run_archive import list_test_artifact_runs
    runs = await list_test_artifact_runs()
    return {"count": len(runs), "runs": runs}


@router.delete("/admin/fixture-runs/test-artifacts")
async def admin_purge_test_artifacts(request: Request):
    check_admin_token(request)
    from run_archive import purge_test_artifact_runs
    deleted = await purge_test_artifact_runs()
    logger.info("admin purge: %d test-artifact fixture run(s) deleted", deleted)
    return {"deleted": deleted}


@router.put("/admin/branding")
async def admin_update_branding(body: BrandingUpdate, request: Request):
    check_admin_token(request)
    updates = {}
    if body.supplier_name is not None and body.supplier_name.strip():
        updates["supplier_name"] = body.supplier_name.strip()
    if body.supplier_tagline is not None:
        updates["supplier_tagline"] = body.supplier_tagline.strip()
    if body.supplier_logo_url is not None:
        updates["supplier_logo_url"] = body.supplier_logo_url or None
    if body.default_pricing_mode is not None:
        mode = body.default_pricing_mode.strip().lower()
        if mode not in {"margin", "markup"}:
            raise HTTPException(status_code=400, detail="default_pricing_mode must be 'margin' or 'markup'")
        updates["default_pricing_mode"] = mode
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.update_one({"id": "branding"}, {"$set": updates}, upsert=True)
    return await get_branding()


@router.post("/admin/upload-logo")
async def admin_upload_logo(request: Request, file: UploadFile = File(...)):
    check_admin_token(request)
    ext = (file.filename or "").split(".")[-1].lower() or "png"
    if ext not in {"jpg", "jpeg", "png", "webp", "svg"}:
        ext = "png"
    name = f"supplier-logo-{uuid.uuid4().hex[:8]}.{ext}"
    dest = UPLOAD_DIR / name
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo too large (>5MB)")
    with open(dest, "wb") as f:
        f.write(content)
    url = f"/api/uploads/{name}"
    await db.settings.update_one(
        {"id": "branding"},
        {"$set": {"supplier_logo_url": url, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"url": url}


@router.get("/admin/signup-code")
async def admin_get_signup_code(request: Request):
    check_admin_token(request)
    return {"signup_code": SIGNUP_CODE}


def _build_invite_html(*, supplier_name: str, supplier_tagline: str, supplier_logo_url: str | None,
                       app_url: str, signup_code: str, recipient_email: str,
                       recipient_name: str | None, personal_note: str | None) -> str:
    """Email-safe HTML for the contractor invitation. Inline styles only — no <style> block."""
    safe_name = html_lib.escape(recipient_name) if recipient_name else "there"
    safe_supplier = html_lib.escape(supplier_name or "Alside Supply")
    safe_tagline = html_lib.escape(supplier_tagline or "")
    safe_code = html_lib.escape(signup_code)
    safe_app = html_lib.escape(app_url.rstrip("/"))
    note_block = ""
    if personal_note:
        # Render as a soft pull-quote so it stands out without breaking branding.
        note_block = (
            f'<tr><td style="padding:14px 28px 0;">'
            f'<div style="border-left:3px solid #F97316;padding:8px 14px;background:#FAFAFA;'
            f'color:#3F3F46;font-size:14px;line-height:1.55;white-space:pre-wrap;">'
            f'{html_lib.escape(personal_note)}</div></td></tr>'
        )
    if supplier_logo_url:
        absolute = supplier_logo_url if supplier_logo_url.startswith("http") else f"{safe_app}{supplier_logo_url}"
        logo_block = (
            f'<img src="{html_lib.escape(absolute)}" alt="{safe_supplier}" '
            f'width="56" height="56" style="display:block;background:#09090B;object-fit:contain;" />'
        )
    else:
        logo_block = (
            f'<div style="width:56px;height:56px;background:#09090B;color:#F97316;'
            f'font-family:Georgia,serif;font-size:30px;font-weight:bold;'
            f'text-align:center;line-height:56px;">{safe_supplier[:1] or "A"}</div>'
        )
    register_url = (
        f"{safe_app}/login?mode=register"
        f"&email={urlquote(recipient_email, safe='')}"
        f"&code={urlquote(signup_code, safe='')}"
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;background:#F4F4F5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#09090B;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#F4F4F5;padding:32px 12px;">
  <tr><td align="center">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;background:#FFFFFF;border:1px solid #E4E4E7;">
      <tr><td style="padding:24px 28px;background:#09090B;color:#FFFFFF;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td>{logo_block}</td>
            <td style="padding-left:14px;vertical-align:middle;">
              <div style="font-size:18px;font-weight:bold;letter-spacing:0.5px;">{safe_supplier}</div>
              <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#A1A1AA;margin-top:4px;">Quoting Tool · Invitation</div>
            </td>
          </tr>
        </table>
      </td></tr>
      <tr><td style="padding:28px 28px 8px;">
        <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#A1A1AA;font-weight:bold;">You're invited</div>
        <h1 style="margin:8px 0 0;font-size:24px;line-height:1.2;color:#09090B;">
          Hey {safe_name}, jump on the new {safe_supplier} quoting tool
        </h1>
        <p style="margin:14px 0 0;font-size:15px;line-height:1.6;color:#3F3F46;">
          We built a fast siding &amp; windows quoting tool with your tier pricing already loaded.
          Upload a HOVER PDF and your line items auto-populate. Send a branded quote with one click.
          Click below to set up your account — your access code is pre-filled.
        </p>
      </td></tr>
      {note_block}
      <tr><td align="center" style="padding:24px 28px 8px;">
        <a href="{register_url}" style="display:inline-block;background:#F97316;color:#FFFFFF;
           text-decoration:none;font-weight:bold;letter-spacing:1px;text-transform:uppercase;
           font-size:13px;padding:14px 28px;">Create your account</a>
      </td></tr>
      <tr><td style="padding:8px 28px 24px;">
        <div style="text-align:center;font-size:12px;color:#71717A;">
          Or use this access code on the signup page:
        </div>
        <div style="text-align:center;margin-top:10px;">
          <span style="display:inline-block;background:#09090B;color:#F97316;
            font-family:Menlo,Consolas,monospace;font-size:18px;letter-spacing:4px;
            padding:10px 22px;font-weight:bold;">{safe_code}</span>
        </div>
      </td></tr>
      <tr><td style="padding:18px 28px 24px;border-top:1px solid #E4E4E7;background:#FAFAFA;">
        <div style="font-size:12px;color:#71717A;line-height:1.6;">
          {safe_tagline}
        </div>
        <div style="margin-top:6px;font-size:11px;color:#A1A1AA;">
          If you weren't expecting this, you can ignore the email — nothing will be created.
        </div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


@router.post("/admin/invite-contractor")
async def admin_invite_contractor(body: InviteContractorIn, request: Request):
    check_admin_token(request)
    if not RESEND_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Add RESEND_API_KEY to enable invitations.",
        )
    recipient = body.email.lower().strip()
    # Guard rail: don't email someone who already has an account.
    existing = await db.users.find_one({"email": recipient}, {"_id": 0, "email": 1})
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"{recipient} already has an account on this platform.",
        )
    app_url = (body.app_url or "").strip()
    if not app_url:
        raise HTTPException(status_code=400, detail="app_url is required (frontend origin).")
    # Build branded HTML
    b = await get_branding()
    supplier_name = b.get("supplier_name") or SUPPLIER_NAME
    supplier_tagline = b.get("supplier_tagline") or SUPPLIER_TAGLINE
    supplier_logo_url = b.get("supplier_logo_url")
    register_url = (
        f"{app_url.rstrip('/')}/login?mode=register"
        f"&email={urlquote(recipient, safe='')}"
        f"&code={urlquote(SIGNUP_CODE, safe='')}"
    )
    html_body = _build_invite_html(
        supplier_name=supplier_name,
        supplier_tagline=supplier_tagline,
        supplier_logo_url=supplier_logo_url,
        app_url=app_url,
        signup_code=SIGNUP_CODE,
        recipient_email=recipient,
        recipient_name=body.name,
        personal_note=body.personal_note,
    )
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        params = {
            "from": SENDER_EMAIL,
            "to": [recipient],
            "subject": f"You're invited to the {supplier_name} quoting tool",
            "html": html_body,
            "tags": [{"name": "kind", "value": "contractor_invite"}],
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
    except Exception as e:
        logger.exception("invite send failed")
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")

    record = {
        "id": str(uuid.uuid4()),
        "email": recipient,
        "name": body.name or "",
        "signup_code": SIGNUP_CODE,
        "register_url": register_url,
        "resend_id": (result or {}).get("id"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.invitations.insert_one(record)
    record.pop("_id", None)
    return {"status": "sent", "invitation": record}


@router.get("/admin/invitations")
async def admin_list_invitations(request: Request):
    check_admin_token(request)
    items = await db.invitations.find({}, {"_id": 0}).sort("sent_at", -1).limit(50).to_list(50)
    # Annotate whether each invited email has since registered.
    emails = [i["email"] for i in items]
    if emails:
        registered = {
            u["email"]
            async for u in db.users.find({"email": {"$in": emails}}, {"_id": 0, "email": 1})
        }
        for it in items:
            it["registered"] = it["email"] in registered
    return items
