"""Vero Series API: contractor-facing catalog + admin pricing matrix.

  GET  /api/vero/catalog          → contractor reads (tier-aware)
  GET  /api/admin/vero/prices     → admin reads the full 4-tier × 6-product matrix
  PUT  /api/admin/vero/prices     → admin upserts one (tier, product_type) doc
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import vero_prices
from catalog_seed import DEFAULT_TIER_NAME
from db import db
from deps import check_admin_token, get_company_for, get_current_user
from vero_catalog import (
    VERO_PRODUCT_TYPES,
    VERO_TIER_NAMES,
    catalog_for_tier_async,
    validate_product_type,
    validate_tier,
)

router = APIRouter()


@router.get("/vero/catalog")
async def get_vero_catalog(user: dict = Depends(get_current_user)):
    """Tier-aware Vero catalog — picks the user's company tier and returns
    the full per-product matrix (buckets, sister colors, glass packages,
    optional premium options) for the W×H window panel."""
    company = await get_company_for(user)
    tier_id = company.get("price_tier_id")
    tier_doc = await db.price_tiers.find_one({"id": tier_id}, {"_id": 0, "name": 1}) if tier_id else None
    tier_name = tier_doc["name"] if tier_doc else DEFAULT_TIER_NAME
    return await catalog_for_tier_async(tier_name, vero_prices)


# ─────────────────── Admin Pricing Matrix ───────────────────

class VeroPriceUpdate(BaseModel):
    tier: str
    product_type: str
    payload: Dict[str, Any]


@router.get("/admin/vero/prices")
async def admin_get_vero_prices(request: Request):
    """Return the full 4-tier × 6-product matrix + structural metadata for
    the Pricing Admin UI."""
    check_admin_token(request)
    rows = await vero_prices.list_all_prices()
    by_key = {(r["tier"], r["product_type"]): r for r in rows}
    data: Dict[str, Dict[str, dict]] = {}
    for tier in VERO_TIER_NAMES:
        data[tier] = {}
        for pt in VERO_PRODUCT_TYPES.keys():
            doc = by_key.get((tier, pt))
            data[tier][pt] = (doc or {}) if doc else {
                "sizing": VERO_PRODUCT_TYPES[pt]["sizing"],
                "_sister_colors": [],
                "_buckets": [],
                "_models": [],
                "base_prices": {},
                "patio_prices": {},
                "adder_prices": {},
            }
    products_meta: Dict[str, dict] = {
        pt: {**meta} for pt, meta in VERO_PRODUCT_TYPES.items()
    }
    return {
        "tiers": VERO_TIER_NAMES,
        "products": list(VERO_PRODUCT_TYPES.keys()),
        "products_meta": products_meta,
        "data": data,
    }


@router.put("/admin/vero/prices")
async def admin_update_vero_prices(body: VeroPriceUpdate, request: Request):
    """Upsert one (tier, product_type) doc."""
    check_admin_token(request)
    err = validate_tier(body.tier) or validate_product_type(body.product_type)
    if err:
        raise HTTPException(status_code=400, detail=err)
    saved = await vero_prices.save_prices(body.tier, body.product_type, body.payload)
    from price_age import price_stamp
    await db.vero_prices.update_one(
        {"tier": body.tier, "product_type": body.product_type},
        {"$set": price_stamp()})
    return saved
