"""Mezzo (3000 Series) replacement-window catalog endpoint."""
from fastapi import APIRouter, Depends

from catalog_seed import DEFAULT_TIER_NAME
from db import db
from deps import get_company_for, get_current_user
from mezzo_catalog import catalog_for_tier

router = APIRouter()


@router.get("/mezzo/catalog")
async def get_mezzo_catalog(user: dict = Depends(get_current_user)):
    """Return the Mezzo product-type matrix for the contractor's tier."""
    company = await get_company_for(user)
    tier_id = company.get("price_tier_id")
    tier_doc = await db.price_tiers.find_one({"id": tier_id}, {"_id": 0, "name": 1}) if tier_id else None
    tier_name = tier_doc["name"] if tier_doc else DEFAULT_TIER_NAME
    return catalog_for_tier(tier_name)
