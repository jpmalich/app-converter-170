"""PRICE AGE — EVERY PRICE WRITE RECORDS WHO AND WHEN (Howard ruled
2026-07-31). A stale price is the one defect that reaches a homeowner;
RainDrop and House Wrap sat stale with nothing in the app saying so.

RULES:
  · every HUMAN price write on every surface stamps price_changed_at +
    price_changed_by on the finest grain the surface has (per item on the
    tier editors and bulk panel; per doc on ISS/Vero/Mezzo/LP margins)
  · seed re-syncs NEVER stamp (they are not price decisions) and must
    preserve existing stamps
  · a surface that can change a price without stamping FAILS the suite —
    test_price_write_stamps_2026_07_31.py scans every route that writes a
    price collection against this register.
"""
from datetime import datetime, timezone

PRICE_STALE_DEFAULT_DAYS = 90

# Every surface that can change a price. Route-scan test enforces
# membership + stamping. Format: "file::function" → what it is.
PRICE_WRITE_SURFACES = {
    "routes/catalog.py::admin_update_tier":
        "four contractor tier editors (single-cell + row edits)",
    "routes/pricing_admin.py::_apply_changes":
        "bulk pricing panel — quick bump + CSV upload",
    "routes/iss_pricing_admin.py::_apply_changes":
        "ISS CSV flow",
    "routes/vero.py::admin_update_vero_prices":
        "Vero matrix editor",
    "routes/mezzo.py::admin_update_mezzo_prices":
        "Mezzo matrix editor",
    "routes/lp_admin.py::put_lp_margin_tiers":
        "LP margin ladder (35/30/25/20)",
}

# Collections that hold prices. Any routes/*.py write to these is a
# price-write surface and must be registered above.
PRICE_COLLECTIONS = ("price_tiers", "vero_prices", "mezzo_prices",
                     "iss_catalog")


def price_stamp(who: str = "supplier-admin") -> dict:
    return {
        "price_changed_at": datetime.now(timezone.utc).isoformat(),
        "price_changed_by": who,
    }


def stamp_price_change(obj: dict, who: str = "supplier-admin") -> None:
    obj.update(price_stamp(who))
