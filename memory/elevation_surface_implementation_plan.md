# Elevation Surface — Implementation Plan (PLAN ONLY, no build; ships post-September)
Per Howard 2026-07-18: mock v3 PASSED, spec complete incl. §9 (SIDING HEIGHT)
+ §2b (approved palette) + §8 (band board) + key-hygiene chip inheritance.

## Phase 0 — Data selectors (pure functions, no UI)
`/app/frontend/src/lib/elevationSheet.js`
- `buildSheetModel(runResult, estimate, wallId)` → one wall's sheet model:
  outline (width, siding height, gable triangle), openings (x from
  along_wall_ft cascade, sizes, sills, schedule tags), dimensions with
  source-tag classification (TAPED / TAPED-DERIVED / AI-READ ✓ / AI-READ ⚠ /
  ESTIMATED / PRINTED / USER / CONTRACTOR-SPEC), per-wall data list, collision
  detection (reuses the autoSpace overlap math — but 2D renders POSITION
  UNVERIFIED dashed-red instead of omitting), band-board entries from
  estimate.contractor_spec_features (post-O&U cluster), blueprint plate-height
  clarifier when `_source_kind === "blueprint"`.
- Unit-testable with pinned fixtures (Letrick front = golden fixture: 54'-0"
  TAPED, 8'-10¼" TAPED-DERIVED, 4 openings AI-READ ✓, deviation vs AI read).
- SIDING HEIGHT naming everywhere; never "eave height" on sheet surfaces.

## Phase 1 — SVG sheet component
`ElevationSheet.jsx` (pure SVG, ~viewBox 1056×816, print-first):
regions = header / drawing (component-class linework per approved palette) /
dimension chains / deviation boxes (STATUS channel) / wall-data / opening
schedule (class swatches) / title block + merged legend (component key +
source chips). Channel-separation pin enforced by construction: linework
colors come ONLY from the component-class map; chips ONLY from the source map.
data-testids per element class.

## Phase 2 — Surfaces
- AI Measure modal: new "Sheets" tab (per-elevation pager FRONT/RIGHT/BACK/
  LEFT), contractor-only.
- Print/PDF: print stylesheet → 4-page packet; "Elevation Sheets (PDF)" in
  report actions (reuse the existing report-share pattern).
- 3D stays secondary per the visual-architecture ruling; fit gate untouched.

## Phase 3 — Band board (first Options & Upgrades entry, ships with surface)
- Add flow: contractor picks wall(s) + break height (anchored to the
  geometry's story/gable break) + 440/540 profile + color → CONTRACTOR-SPEC
  provenance log (by/at, revertible).
- Derivation: LF = Σ wrapped wall widths; sticks = splice-and-round-up;
  priced through the engine as a trim line.
- Sheet render: plum long-dash line at break height + schedule row with
  C-SPEC chip; excluded from accuracy comparisons by construction.

## Phase 4 — i18n + tests
- EN/ES dictionary keys for all sheet labels.
- Pin suite `test_elevation_sheet.py`: channel separation, TAPED vs
  TAPED-DERIVED vs AI-READ classification, POSITION-UNVERIFIED collision
  render (presence guaranteed, never omitted), SIDING-HEIGHT naming,
  deviation-box "tape governs" wording, band-board C-SPEC exclusion from
  accuracy comparisons, golden Letrick fixture snapshot.
- testing_agent E2E: open estimate → Sheets tab → verify per-wall render +
  print CSS.

## Order & estimates
Phase 0 (selectors + fixtures) → 1 (component) → 2 (surfaces) → 3 (band
board) → 4 (i18n/tests). Each phase independently testable. No backend
schema changes required until Phase 3 (contractor_spec_features on estimate).
