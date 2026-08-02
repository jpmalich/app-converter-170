"""DROPPED-FIELD REGISTERS — BLUEPRINT + PHOTO DOORS (Howard ruled 2026-08-01,
ruling 5: same alarm, same behavior as Hover's Class B on ALL THREE doors).
Every field a door's aggregator emits is either CONSUMED with its derivation
named, or REGISTERED deliberately-not-consumed with a reason. A dropped
measured field FAILS THE BUILD. A new field FAILS until Howard rules it.
Detection only — changes NO derivation and NO dollar
(test_door_registers_2026_08_01.py enforces it).

Field × Door matrix of record: /app/memory/three_doors_field_matrix_2026_08_01.md
"""
from hover_field_register import CONSUMED, NOT_CONSUMED

# ── Shared engine keys (both AI doors stage through measure_staging;
#    consumers identical to Hover's register) ────────────────────────────
_SHARED = {
    "siding_sqft": {"status": CONSUMED, "consumed_by": ["panel/lap/shake basis (lp tabs + package)", "vinyl/ascend SQ basis"]},
    "siding_with_openings_sqft": {"status": CONSUMED, "consumed_by": ["vinyl/ascend SQ basis", "touch-up + caulk SQ terms"]},
    "opening_sqft": {"status": NOT_CONSUMED, "reason": "informational surface; SQ basis nets openings upstream"},
    "eaves_lf": {"status": CONSUMED, "consumed_by": ["soffit split + vented run", "fascia LF"]},
    "rakes_lf": {"status": CONSUMED, "consumed_by": ["soffit split + closed run", "fascia LF"]},
    "starter_lf": {"status": CONSUMED, "consumed_by": ["starter strip lines (vinyl/lp)"]},
    "outside_corner_lf": {"status": CONSUMED, "consumed_by": ["Q13 per-corner height basis / pooled fallback"]},
    "inside_corner_lf": {"status": CONSUMED, "consumed_by": ["Q12 ISC per-corner height basis"]},
    "outside_corner_count": {"status": CONSUMED, "consumed_by": ["Q13 per-corner OSC (both emitters)"]},
    "inside_corner_count": {"status": CONSUMED, "consumed_by": ["Q12 ISC 540-4\" per-corner"]},
    "opening_count": {"status": CONSUMED, "consumed_by": ["opening-driven trim counts"]},
    "opening_perimeter_lf": {"status": CONSUMED, "consumed_by": ["vinyl J-channel driver"]},
    "window_count": {"status": CONSUMED, "consumed_by": ["window wrap/trim counts", "J blocks", "caulk-per-opening"]},
    "door_count": {"status": CONSUMED, "consumed_by": [
        "caulk-per-opening + J blocks — LANDED build step 1 (finding 6 ruled 2026-08-01: "
        "the sum was counted per-type but never rolled up on either AI door)"]},
    "entry_door_count": {"status": CONSUMED, "consumed_by": ["Cap entry door rows", "starter door deduction"]},
    "patio_door_count": {"status": CONSUMED, "consumed_by": ["Cap patio door rows"]},
    "garage_door_count": {"status": CONSUMED, "consumed_by": ["Cap garage door rows"]},
    "footprint_perimeter_ft": {"status": CONSUMED, "consumed_by": [
        "batten stacked-wall-height term — KEY FIX landed build step 2 (named item, ruled "
        "2026-08-01): blueprint wrote _perimeter_lf while the reader reads footprint_perimeter_ft; "
        "writer-key == reader-key is pinned by test"]},
    "window_bottom_width_total_lf": {"status": CONSUMED, "consumed_by": [
        "FINISH TRIM sill term (vinyl+Ascend) — 10(e) ruled, landed build step 3 "
        "(wbw primary, count × 3' fallback)"]},
    "vent_count": {"status": CONSUMED, "consumed_by": ["vent accessory rows"]},
    "shutter_count": {"status": CONSUMED, "consumed_by": ["shutter accessory rows"]},
}

# ── BLUEPRINT door — printed figures land (step 2) ──────────────────────
BLUEPRINT_FIELD_REGISTER = {
    **_SHARED,
    "soffit_sqft": {"status": CONSUMED, "consumed_by": ["Q14a measured soffit total governs (lp_package._soffit_total_split)"]},
    "level_frieze_lf": {"status": CONSUMED, "consumed_by": ["Q10 frieze consumption — per-segment ÷16"]},
    "sloped_frieze_lf": {"status": CONSUMED, "consumed_by": ["Q10 frieze consumption — sloped segments"]},
    "drip_edge_lf": {"status": CONSUMED, "consumed_by": ["drip edge line (roof-edge passthrough)"]},
    "total_trim_sqft": {"status": CONSUMED, "consumed_by": ["trim-area context passthrough"]},
    "footprint_area_sqft": {"status": NOT_CONSUMED, "reason":
        "mirrors Hover's ruled entry — perimeter is the batten term; area held for plan-view sanity"},
    "address": {"status": CONSUMED, "consumed_by": ["job info surface (not a derivation input)"]},
    "opening_facade_assignments": {"status": CONSUMED, "consumed_by": ["Class C attribution (R6: read from explicit assignment, never inferred)"]},
    "windows": {"status": CONSUMED, "consumed_by": ["ONE paired openings builder (dims mode)", "wbw sill sum"]},
    "stories": {"status": CONSUMED, "consumed_by": ["labor/story context on tab lines"]},
}

# ── PHOTO door — detected figures land (step 2) ─────────────────────────
# (stories lands worker-side on the photo door; dormers[] ride the raw
# result — the register scopes to AGGREGATOR-emitted engine keys.)
PHOTO_FIELD_REGISTER = {
    **_SHARED,
    # Photo genuinely-cannot-see cells (N-S on the matrix): the four
    # ruled fill-in boxes LANDED build step 6 (soffit_sqft, drip_edge_lf,
    # total_trim_sqft, frieze presence-toggle — measure_staging.
    # fold_photo_fillins). They are NOT register entries here because the
    # photo AGGREGATOR never emits them — the trade-spec box supplies
    # them, human-typed, and the fold only ever fills a hole.
}
