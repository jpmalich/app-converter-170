"""Iter 99 one-off — backfill EST-910869-L (e452a988) whose pair-lp seed
produced 0 lines (source measurements lived on the AI run, not the
estimate doc). Re-seeds via the same path pair-lp now uses. Idempotent:
only fills when the estimate has no lines."""
import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from db import db  # noqa: E402

EST_ID = "e452a988-83b8-4e6e-9537-1223d0ecbf6f"
SRC_ID = "673707d5-9b7e-4d8f-8eaf-63c86820f611"


async def main():
    from routes.catalog import _resolve_catalog_for_company
    from routes.hover import _build_lines

    est = await db.estimates.find_one({"id": EST_ID})
    if not est:
        print("estimate gone"); return
    if est.get("lines"):
        print("already has lines — nothing to do"); return
    run = await db.ai_measure_runs.find_one(
        {"estimate_id": SRC_ID, "status": "done"}, sort=[("created_at", -1)])
    measurements = ((run or {}).get("result") or {}).get("measurements") or None
    if not measurements:
        print("no run measurements"); return
    company = await db.companies.find_one({"id": est["company_id"]}, {"_id": 0})
    catalog = await _resolve_catalog_for_company(company)
    price_idx = {}
    for sec in catalog.get("sections", []):
        for it in sec.get("items", []):
            price_idx[(sec["title"], it["name"])] = {
                "mat": float(it.get("mat") or 0), "lab": float(it.get("lab") or 0),
                "unit": it.get("unit") or "", "ami_part": it.get("ami_part"),
                "pricing_pending": bool(it.get("pricing_pending")),
                "pricing_source": it.get("pricing_source"),
            }
    seeded = []
    for ln in _build_lines(measurements):
        if ln.get("tab") != "lp_smart":
            continue
        try:
            qty = float(ln.get("qty") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        cat_row = price_idx.get((ln.get("section"), ln.get("name")), {})
        doc = {"section": ln.get("section", ""), "name": ln.get("name", ""),
               "unit": ln.get("unit") or cat_row.get("unit", ""), "qty": qty,
               "mat": cat_row.get("mat", 0), "lab": 0,
               "ami_part": cat_row.get("ami_part"), "tab": "lp_smart", "adders": []}
        if not cat_row or cat_row.get("pricing_pending"):
            doc["pricing_pending"] = True
        if cat_row.get("pricing_source"):
            doc["pricing_source"] = cat_row["pricing_source"]
        seeded.append(doc)
    await db.estimates.update_one(
        {"id": EST_ID},
        {"$set": {"lines": seeded,
                  "updated_at": datetime.now(timezone.utc).isoformat()}})
    print(f"backfilled {len(seeded)} lines onto {est.get('estimate_number')}")


if __name__ == "__main__":
    asyncio.run(main())
