# FIELD × DOOR MATRIX — RULING 6 GATE (2026-08-01)
Cells: **S-C** supplied & consumed · **S-D** supplied but DROPPED (ruling-6 violation, register must catch) · **N-S** source genuinely cannot see it (fill-in candidate) · *(ruled)* = deliberate not-consumed, already ruled.

| Field | HOVER | BLUEPRINT | PHOTO | Notes |
|---|---|---|---|---|
| siding_sqft | S-C | S-C | S-C | gable factor unifies to 0.70 (ruled 1) |
| siding_with_openings_sqft | S-C | S-C† | S-C† | † AI doors alias it to siding_sqft (no distinct gross read) |
| soffit_sqft | S-C | **S-D** | N-S | plans print soffit detail; schema has no key. Photo: engine infers eaves×overhang — fill-in legit |
| eaves_lf | S-C | S-C | S-C | blueprint gable-wall correction; photo trusts raw (10a) |
| rakes_lf | S-C | S-C | S-C | |
| starter_lf | S-C | S-C | S-C* | * eaves fallback basis — finding 8, pending |
| outside_corner_count | S-C | S-C | **S-D** | photo detects corners (LP-path machinery); count never lands → finding 7 |
| outside_corner_lf | S-C | S-C | S-C | photo per-wall heights (79j.64) |
| inside_corner_count | S-C | S-C | **S-D** | same as OSC count |
| inside_corner_lf | S-C | S-C | S-C | |
| opening_count | S-C | S-C | S-C | |
| window_count | S-C | S-C | S-C | |
| door_count (total) | S-C | **S-D** | **S-D** | per-type counted, sum never landed → finding 6; caulk + J-blocks short |
| entry/patio/garage_door_count | S-C | S-C | S-C | |
| opening_perimeter_lf | S-C | S-C | S-C | |
| windows (per-opening dims) | S-C | S-C | S-C‡ | ‡ via own builder `_build_vero_openings_from_ai` — consolidates (10b) |
| opening→facade assignments | S-C | **S-D** | S-C | drawings state each window's elevation; blueprint drops the tag (R6 flag fires instead) |
| stories | S-C | S-C | S-C | |
| footprint_perimeter_ft | S-C | **S-D** | **S-D** | blueprint computes it but stores as `_perimeter_lf` — batten machinery reads `footprint_perimeter_ft` (KEY MISMATCH, new find); photo has wall widths, never sums |
| footprint_area_sqft | S-D *(ruled)* | **S-D** | N-S | Hover deliberate (2026-07-28); blueprint plans print it, no key |
| level_frieze_lf | S-C | **S-D** | N-S* | elevations draw frieze; no schema key. * photo: presence detectable, LF ≈ eaves/rakes runs — candidate presence-toggle, not number box |
| sloped_frieze_lf | S-C | **S-D** | N-S* | same |
| drip_edge_lf | S-C | **S-D** | N-S | roof plans print it; photos cannot read it — fill-in legit |
| total_trim_sqft | S-C | **S-D** | N-S | trim schedules print it |
| vent_count | S-C | S-C | S-C | |
| shutter_count | S-C | S-C | S-C | |
| gable geometry (rise/pitch) | (inside measured sqft) | S-C | S-C | 0.70 sealed |
| dormer faces | (inside measured sqft) | S-C | S-C | photo dormers[] carries width_source provenance |
| per-elevation/profile breakdown | S-C | S-C | S-C | facade_breakdown / walls[] / _per_elevation_breakdown |
| per-wall heights | n/a (aggregate) | S-C | S-C* | * <4ft silent substitution — finding 9, pending |
| roof_area_sqft | S-D *(ruled)* | S-D *(ruled analog)* | N-S | out of scope for siding engine |
| united_inches | S-D *(ruled)* | N-S | N-S | per-opening pricing instead |
| window_bottom_width_total_lf | **S-D?** | **S-D?** | **S-D?** | NO consumer exists anywhere — 10e pending: register fiction vs real sill rule |
| overhang_in | N-S | N-S | N-S | contractor spec — existing fill-in box, legit |
| address | S-C | **S-D** (minor) | N-S | plan title blocks print it |
| taped tall corners (_osc_tall_corners_ft) | N-S | N-S | N-S | field-verify input by design — legit human box |

## TALLY
- Ruling-6 violations (S-D to fix by landing, not fill-in): blueprint 10 cells (soffit, frieze×2, drip edge, trim sqft, footprint perim+area, door_count, facade assignments, address) · photo 4 cells (corner counts×2, door_count, footprint perim) · hover 0 (register clean minus 10e).
- Legit fill-in candidates (N-S): photo soffit_sqft, drip_edge_lf, total_trim_sqft; frieze presence-toggle; overhang_in + taped corners (existing, stay).
- Pending Howard: 10e row; finding 8 starter basis; finding 9 substitution behavior.
