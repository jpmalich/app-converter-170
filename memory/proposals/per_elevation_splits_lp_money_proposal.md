# PROPOSAL — Per-Elevation Splits → LP Money Derivation
Report-class, for Howard's ruling. Nothing here is wired. 2026-07-26.
Gate pinned meanwhile: tests/test_per_elevation_money_gate.py.

## 0. Facts on the ground (stated plainly, corrected after full trace)
- `_per_elevation_breakdown` (per elevation: body/gable/dormer sqft +
  profile family per surface) and `_per_profile_sqft` (family → total
  ft²) are computed by profile_callouts.breakdown_walls_by_profile in
  ai_measure/ai_blueprint. Contractor accents (+ Add Accent card) edit
  both, then re-map.
- ALREADY-RULED money consumption (NOT touched by this proposal):
  a. /measure/map mapper (routes/hover.py) emits per-profile quote
     lines for the vinyl, ascend AND lp_smart tabs from
     `_per_profile_sqft` — Iter 78z (Campbell, 2026-02-13), Iter 78ab
     LP per-profile coverage, Iter 79j.71 conflict tripwire (amber
     qty-0 lines), compare-profiles ruling 2026-07-16.
  b. lp_package_routes.py default-profile inheritance (ruled slice 1;
     B&B starter OFF ruled+pinned).
  c. lp_package.py shake 540-series trim bump (ruled 2026-07-17).
- THE ACTUAL UNRULED GAP: the LP PACKAGE materialize siding lines
  derive from the headline siding_sqft (plus sealed-key overrides) —
  mixed-family splits reach the estimate-editor lines via (a) but do
  NOT split the LP package's own siding lines per family. That wiring
  is what this proposal maps. Gate pinned meanwhile
  (tests/test_per_elevation_money_gate.py freezes consumption at the
  ruled set above).
- Adjacent overlap that needs the same ruling: the Apply-time
  "Quote gables/dormers as shake" toggles (Iter 51, frontend
  swapSidingToShake) move ft² between SKU lines with FLAT LP math
  (pieces = ceil(sqft / 4), no waste, no reveal coverage) — this
  BYPASSES lp_conventions. The Iter 79j.71 single-owner guard prevents
  double-count vs the breakdown, but the toggle's own math is not
  conventions-grade.

## 1. Proposed mapping — splits → LP PACKAGE siding lines
For an LP estimate whose run carries a per-elevation breakdown, the LP
package materialize step would derive per-FAMILY areas by summing
across elevations:

    family_sqft[f] = Σ over elevations of
        body_sqft   where body_profile   == f
      + gable_sqft  where gable_profile  == f
      + dormer_sqft where dormer_profile == f
      + accent_sqft where accent.profile == f   (contractor overrides)

Then one siding line per family, in place of today's single headline
line:
  - lap / dutch_lap → LP lap SKU at the estimate's selected face;
    pieces via lp_conventions.line_math(area, coverage(reveal, length),
    DEFAULT_WASTE 10%).
  - shake → LP Cedar Shakes SKU; pieces via shake_takeoff(area) —
    sealed 15% waste, reveal-min coverage (44 pcs/sq @ 6-7/8").
  - board_batten / vertical → LP panel SKU via line_math + batten
    flags (batten_takeoff_flags), 10% waste.
  - stone / brick / stucco → NOT siding: excluded from LP lines,
    reported as an excluded-area note on the package (never silently
    dropped).
  - unknown → HARD FLAG line (qty 0, amber) — never priced by guess.

## 2. Conservation rule (the money invariant)
Σ family_sqft across families == siding_sqft the package prices today
(after key-bound/sealed overrides). Any residue (walls without a
profile callout) stays on the DEFAULT family (estimate's selected
profile) — the split may reallocate ft², it may never create or
destroy ft². Pinned by a conservation test before wiring.

## 3. Precedence (consistent with sealed-key doctrine)
1. Sealed hand-takeoff key (letrick_v3-class) — untouched, always wins
   on totals; splits then allocate WITHIN the key-bound total.
2. Contractor accents/overrides (Add Accent, Field Verify) over AI
   callouts.
3. AI per-elevation callouts.
4. Estimate default profile for residue.
Provenance: each family line carries its basis (KEY / CONTRACTOR / AI /
DEFAULT) in `_area_basis`-style notes — same discipline as today.

## 4. What happens to the as-shake toggles under this ruling
They become a thin alias: toggling "quote gables as shake" sets
gable_profile=shake on the breakdown (per elevation) and re-derives via
the SAME conventions path — the flat ceil(sqft/4) swap math retires.
Single owner, no double-count guard needed by construction.

## 5. Waste, by family (from the sealed conventions layer)
- lap/soffit: DEFAULT_WASTE 10% (waste-exclusive coverage, waste on
  top, then whole-piece roundup per line — never averaged).
- shake: SHAKE_WASTE 15% (sealed 2026-07-24 v3 book-check).
- board&batten/vertical: 10% default + batten flags; pending-Howard trim
  carry-over stays pending (never filled from other sources).

## 6. Test plan before any wiring (post-ruling)
- Conservation pin (Σ families == headline, residue-to-default).
- Letrick regression: sealed key totals unchanged; splits allocate
  within 2099.7 only.
- Shake family uses 15%/reveal-min; lap uses 10%/face coverage.
- unknown-family flag line renders, prices nothing.
- As-shake toggle produces byte-identical lines to setting the profile
  on the breakdown (alias equivalence).

## RULING REQUESTED
A. Approve mapping (§1) + conservation rule (§2) + precedence (§3)?
B. Retire the toggles' flat math in favor of the alias (§4)?
C. Family waste table (§5) — confirm B&B at 10% or rule otherwise?
