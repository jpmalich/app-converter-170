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
    "window_bottom_width_total_lf": {"status": CONSUMED, "consumed_by": ["starter deduction at window sills"]},
    "door_count": {"status": CONSUMED, "consumed_by": ["door trim counts", "J blocks", "caulk-per-opening"]},
    "entry_door_count": {"status": CONSUMED, "consumed_by": ["Cap entry door rows", "mini-splits scaling (register #2)"]},
    "patio_door_count": {"status": CONSUMED, "consumed_by": ["Cap patio door rows"]},
    "garage_door_count": {"status": CONSUMED, "consumed_by": ["Cap garage door rows"]},
    "stories": {"status": CONSUMED, "consumed_by": ["labor/story context on tab lines"]},
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
