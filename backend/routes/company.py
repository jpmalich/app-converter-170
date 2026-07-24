"""Per-contractor company GET/PUT."""
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_company_for, get_current_user
from models import CompanyUpdate

router = APIRouter()


@router.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    return await get_company_for(user)


@router.put("/company/labor-rates")
async def set_labor_rate(body: dict, user: dict = Depends(get_current_user)):
    """LABOR IS THE CONTRACTOR'S (ruled 2026-07-24): store a contractor-
    owned labor rate. Future rebuilds bind it (lab_src "company") instead
    of any provisional guess."""
    from lp_costs import sheet_norm
    name = str((body or {}).get("name") or "").strip()
    rate = (body or {}).get("rate")
    if not name or rate is None:
        raise HTTPException(status_code=422, detail="name and rate are required")
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="rate must be a number")
    if rate < 0:
        raise HTTPException(status_code=422, detail="rate must be ≥ 0")
    company = await get_company_for(user)
    key = sheet_norm(name)
    await db.companies.update_one(
        {"id": company["id"]}, {"$set": {f"labor_rates.{key}": rate}})
    doc = await db.companies.find_one({"id": company["id"]}, {"_id": 0, "labor_rates": 1})
    return {"ok": True, "labor_rates": doc.get("labor_rates") or {}}


@router.put("/company")
async def update_company(body: CompanyUpdate, user: dict = Depends(get_current_user)):
    company = await get_company_for(user)
    updates = {}
    if body.name is not None and body.name.strip():
        updates["name"] = body.name.strip()
    if body.logo_url is not None:
        # Empty string clears the logo
        updates["logo_url"] = body.logo_url or None
    if body.quote_footer_enabled is not None:
        updates["quote_footer_enabled"] = bool(body.quote_footer_enabled)
    if updates:
        await db.companies.update_one({"id": company["id"]}, {"$set": updates})
    return await db.companies.find_one({"id": company["id"]}, {"_id": 0})
