"""CLASS B — HOVER FIELD-CONSUMPTION REGISTER (sealed 2026-07-28).
Every field the Hover extraction emits is either CONSUMED with its
derivation named, or REGISTERED as deliberately not-consumed with a
reason. A dropped field with no register entry FAILS. A field that stops
being consumed FAILS. A new Hover field FAILS until Howard rules it.
RIDER 2 BINDS: this register changes NO derivation and NO dollar — it is
detection only (test_intake_classes_2026_07_28.py enforces it).
"""

CONSUMED = "consumed"
NOT_CONSUMED = "registered_not_consumed"

# field -> {"status", "consumed_by" | "reason"}
HOVER_FIELD_REGISTER = {
    "siding_sqft": {"status": CONSUMED, "consumed_by": ["panel/lap/shake basis (lp tabs + package)", "Class A conservation ledger"]},
    "siding_with_openings_sqft": {"status": CONSUMED, "consumed_by": ["vinyl/ascend SQ basis", "touch-up + caulk SQ terms"]},
    "soffit_sqft": {"status": CONSUMED, "consumed_by": ["Q14a measured soffit total governs (lp_package._soffit_total_split)", "ceiling-dedup class"]},
    "eaves_lf": {"status": CONSUMED, "consumed_by": ["soffit split + vented run", "fascia LF", "Q2 porch-implied flag"]},
    "rakes_lf": {"status": CONSUMED, "consumed_by": ["soffit split + closed run", "fascia LF"]},
    "starter_lf": {"status": CONSUMED, "consumed_by": ["starter strip lines (vinyl/lp)"]},
    "outside_corner_count": {"status": CONSUMED, "consumed_by": ["Q13 per-corner OSC (both emitters)", "corner correction machinery"]},
    "outside_corner_lf": {"status": CONSUMED, "consumed_by": ["Q13 per-corner height basis — AVERAGE under open flag; taped tall corners per-unit (never-average sealed 2026-07-28)"]},
    "inside_corner_count": {"status": CONSUMED, "consumed_by": ["Q12 ISC 540-4\" per-corner"]},
    "inside_corner_lf": {"status": CONSUMED, "consumed_by": ["Q12 ISC per-corner height basis"]},
    "opening_count": {"status": CONSUMED, "consumed_by": ["opening-driven trim counts", "Class C attribution flag"]},
    "opening_perimeter_lf": {"status": CONSUMED, "consumed_by": ["vinyl J-channel driver (tops/sills/sides preferred, lump fallback)"]},
    "window_count": {"status": CONSUMED, "consumed_by": ["window wrap/trim counts", "J blocks", "caulk-per-opening (register #5)"]},
    "window_bottom_width_total_lf": {"status": CONSUMED, "consumed_by": [
        "FINISH TRIM sill term (vinyl + Ascend) — 10(e) ruled 2026-08-01, landed build step 3: "
        "sills + top course; wbw primary, per-window sum next, window_count × 3' fallback. "
        "The old 'starter deduction at window sills' entry was FICTION (no such consumer ever "
        "existed); the Iter 78f full-window-perimeter term retired with the ruling"]},
    "door_count": {"status": CONSUMED, "consumed_by": ["door trim counts", "J blocks", "caulk-per-opening"]},
    "entry_door_count": {"status": CONSUMED, "consumed_by": ["Cap entry door rows", "mini-splits scaling (register #2)"]},
    "patio_door_count": {"status": CONSUMED, "consumed_by": ["Cap patio door rows"]},
    "garage_door_count": {"status": CONSUMED, "consumed_by": ["Cap garage door rows"]},
    "stories": {"status": CONSUMED, "consumed_by": ["labor/story context on tab lines"]},
    "footprint_perimeter_ft": {"status": CONSUMED, "consumed_by": [
        "HOVER-SCHEDULE stacked-wall-height term = sided facade area / footprint perimeter "
        "(batten_wall_heights flag comparison, sealed 2026-07-28 — measured, not guessed; "
        "Haugh 2064/181 = 11.4 ft wrap-only). Provenance ladder: blueprint/Hover schedule -> "
        "derived area/perimeter (HOVER-SCHEDULE) -> AI vision floor count (SUGGESTS only, "
        "Class C) -> estimated default, flagged"]},
    "footprint_area_sqft": {"status": NOT_CONSUMED, "reason":
        "published on the FOOTPRINT page; perimeter is the batten run term — area held for "
        "plan-view sanity checks, ruled with queue item d (2026-07-28)"},
    "address": {"status": CONSUMED, "consumed_by": ["job info surface (not a derivation input)"]},
    "level_frieze_lf": {"status": CONSUMED, "consumed_by": ["Q10 frieze consumption — per-segment ÷16 (Q16)"]},
    "sloped_frieze_lf": {"status": CONSUMED, "consumed_by": ["Q10 frieze consumption — sloped segments"]},
    "drip_edge_lf": {"status": CONSUMED, "consumed_by": ["drip edge line (Q14 passthrough)"]},
    "total_trim_sqft": {"status": CONSUMED, "consumed_by": ["Q14 passthrough — trim coil context"]},
    "vent_count": {"status": CONSUMED, "consumed_by": ["accessory counts (Q14 passthrough)"]},
    "shutter_count": {"status": CONSUMED, "consumed_by": ["accessory counts (Q14 passthrough)"]},
    "united_inches": {"status": NOT_CONSUMED, "reason": "window-pricing convention not in play — Vero/Mezzo price per-opening from dims (Iter 44); ruled deliberate 2026-07-28"},
    "per_elevation_siding": {"status": NOT_CONSUMED, "reason": "per-elevation split reserved for elevation sheets; siding basis is facade-scoped total — ruled deliberate 2026-07-28"},
    "roof_area_sqft": {"status": NOT_CONSUMED, "reason": "roofing is out of scope for the siding engine — ruled deliberate 2026-07-28"},
    "facade_breakdown": {"status": CONSUMED, "consumed_by": ["Class A/C intake scope (wrap-only default, label-suggested wrap, conservation ledger)"]},
    "opening_facade_assignments": {"status": CONSUMED, "consumed_by": ["Class C opening↔facade attribution (R6 sealed 2026-07-28: read from assignment, never inferred; absent → flag)"]},
    "windows": {"status": CONSUMED, "consumed_by": ["per-opening Vero/Mezzo pricing lists (preferred over lumped perimeter)"]},
}

# ── PUBLISHED-FIELD REGISTER (Howard, 2026-07-28 — "five confirmed
# dropped fields is not a queue item any more"): every figure the Hover
# REPORT PUBLISHES maps to a schema key. This is the detector that would
# have caught soffit area, frieze LF, outside-corner length, opening
# perimeter, and the FOOTPRINT page in one pass instead of one-at-a-time
# across a day. A published figure with no schema key FAILS. ─────────────
HOVER_PUBLISHED_FIELDS = {
    "Siding table (area / openings / net)": "siding_sqft",
    "Siding waste table (+openings adder)": "siding_with_openings_sqft",
    "Facade material breakdown rows": "facade_breakdown",
    "Soffit area (dropped-field #1, caught 2026-07)": "soffit_sqft",
    "Level frieze board length (dropped-field #2)": "level_frieze_lf",
    "Sloped frieze board length (dropped-field #2)": "sloped_frieze_lf",
    "Outside corner count": "outside_corner_count",
    "Outside corner length (dropped-field #3)": "outside_corner_lf",
    "Inside corner count": "inside_corner_count",
    "Inside corner length": "inside_corner_lf",
    "Opening perimeter (dropped-field #4)": "opening_perimeter_lf",
    "Opening count": "opening_count",
    "Window schedule (per-opening dims)": "windows",
    "Opening→facade assignments": "opening_facade_assignments",
    "Eaves fascia length": "eaves_lf",
    "Rakes fascia length": "rakes_lf",
    "Starter length": "starter_lf",
    "FOOTPRINT — Number of Stories (carried since intake)": "stories",
    "FOOTPRINT — Footprint Perimeter (dropped-field #5, caught 2026-07-28)": "footprint_perimeter_ft",
    "FOOTPRINT — Footprint Area (dropped-field #6, caught 2026-07-28)": "footprint_area_sqft",
    "Roof area (waived: out of scope)": "roof_area_sqft",
    "United inches (waived: per-opening pricing)": "united_inches",
    "Drip edge / perimeter length": "drip_edge_lf",
    "Trim total area": "total_trim_sqft",
    "Vents / shutters accessory counts": "vent_count",
    "Property address": "address",
}
