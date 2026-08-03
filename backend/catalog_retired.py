"""RETIRED CATALOG ROWS — soft-delete backup (Howard ruled 2026-08-03).
CONQUEST IS STANDARD ONLY: Architectural Conquest is not a product Howard
sells, so the two priced rows below were PHANTOMS — a tier a future bump
or rename could silently bind to (string-fragility class). Deleted from
every live surface (catalog_seed section list, ITEM_META, PER_TIER_PRICES,
item numbers, catalog_ids register, services backfill list) on 2026-08-03.
Zero estimates referenced them at deletion (swept).

RECOVERY (if Howard is ever proven wrong): re-add each record's name to
the Vinyl Siding section list and restore the entries below verbatim —
same recover-from-trash spirit as the estimate purge.

A pin (tests/test_conquest_phantom_retired_2026_08_03.py) FAILS the suite
if an Architectural Conquest row ever reappears on a live surface.
"""

RETIRED_ROWS = (
    {
        "section": "Vinyl Siding",
        "name": 'Conquest Architectural color Clap 4.5" .040',
        "item_meta": ("SQ", 0),
        "per_tier_prices": {"whole-sale": 113.94, "Contractor": 108.24,
                            "Builder-Dealer": 102.84, "one-opp": 75.71},
        "item_number": "015456",
        "item_id": "itm-b05e5088af",
        "retired": "2026-08-03",
        "ruling": "Conquest is Standard only (Howard, 2026-08-03)",
    },
    {
        "section": "Vinyl Siding",
        "name": 'Conquest Architectural color Dutch lap 4.5" .040',
        "item_meta": ("SQ", 0),
        "per_tier_prices": {"whole-sale": 113.94, "Contractor": 108.24,
                            "Builder-Dealer": 102.84, "one-opp": 75.71},
        "item_number": "015457",
        "item_id": "itm-3bc02d5211",
        "retired": "2026-08-03",
        "ruling": "Conquest is Standard only (Howard, 2026-08-03)",
    },
)
