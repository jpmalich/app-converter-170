"""ISS Siding REST endpoint.

  GET /api/iss/catalog → contractor-facing single-tier line book.

The catalog is loaded from the `iss_catalog` MongoDB collection so the
supplier admin can update prices via /api/admin/iss/*. The hardcoded
ISS_SECTIONS in iss_catalog.py only acts as the first-boot seed.
"""
from fastapi import APIRouter, Depends

from iss_catalog import load_iss_catalog
from deps import get_current_user
from db import db

router = APIRouter(prefix="/iss", tags=["iss"])


@router.get("/catalog")
async def iss_catalog(user: dict = Depends(get_current_user)):
    return await load_iss_catalog(db)
