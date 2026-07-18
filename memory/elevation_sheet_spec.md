# Dimensioned 2D Elevation Sheets — SPEC (design + data-mapping phase)
Ruled 2026-07-18 (VISUAL ARCHITECTURE RULING): 2D sheets are the PRIMARY
wall-verification surface. This spec + one mocked sheet (Letrick front wall,
real data) is the review deliverable. Ship timing: first post-September build
unless Howard explicitly moves it.

## 1. Purpose & positioning
One orthographic sheet PER ELEVATION (front/right/back/left), rendered from
EXISTING extraction data — no new AI phase, no new schema. The sheet is a
verification instrument: every number wears its provenance. 3D remains
secondary (tap-wall takeoff, appendage ratification, simple houses).

## 2. Sheet anatomy (top → bottom)
1. **Header strip** — "FRONT ELEVATION" + address + scale note ("NOT A SURVEY —
   AI-measured estimate").
2. **Drawing area** — orthographic wall outline to scale:
   - Wall rectangle: width_ft × height_ft (eave height).
   - Gable triangle when `gable_triangle_height_ft > 0` on THIS wall
     (peak at wall midpoint; no ridge-axis inference — the wall's own field
     decides, sidestepping the 3D ridge-axis failure mode).
   - Roof fascia band + overhang stubs (render-only context, dashed).
   - Grade line below the wall.
   - Openings drawn to scale from `openings[]` (this wall): x from
     `along_wall_ft` (center, wall-local ft from left corner) — bbox X-fraction
     fallback — even-spacing last resort (same cascade as 3D autoSpace); width/
     height from `width_in`/`height_in`; sill from bbox Y (doors sit at grade).
   - **Collisions do NOT omit here** (APPROVED 2026-07-18, chase-render
     precedent): overlapping opening rects render dashed-red with a
     "POSITION UNVERIFIED" chip — presence guaranteed, position labeled,
     render-only, print-surviving, linked to its schedule tag, and
     SOLIDIFIED when the confirm-card ratifies the position.
3. **Dimension lines** (extension lines + ticks, architectural format X'-Y"):
   - Overall wall width (below, outermost chain).
   - Opening-center chain (below, inner chain): left corner → each opening
     center → right corner, from `along_wall_ft`.
   - Eave height (right side); gable peak height when present (right side,
     stacked outside the eave dim).
   - Every dimension carries a SOURCE TAG chip.
4. **Opening schedule labels** — tag bubble above each opening (W1, W2, D1…)
   keyed to a schedule table on the sheet: tag, type, style, size (WxH in),
   position (along_wall_ft + source), sill.
5. **Per-wall data list** — width + source, eave height + source (+ per-photo
   readings note, e.g. "23/24 courses, ±1"), gable triangle, siding %, profile
   callout(s), opening count, AI confidence + reasoning snippet, source photo
   indices.
6. **Title block** (bottom right) — customer, address, sheet code (EL-1..4),
   run_id, model badge, date, scale ratio, source-tag legend.

## 3. Source-tag taxonomy (chip on EVERY dimension)
CORRECTED 2026-07-18 after the rejected first mock: **TAPED is reserved for
contractor tape** — an AI field claiming a taped reference was in frame
(`width_ft_source=direct_ref`) is still an AI READ and never wears the tape's
label. The first mock violated this (AI direct_ref 50'-0" wore TAPED REF while
the sealed tape key says 54'-0") — register-worthy source-naming defect.
| Tag | Fields that produce it | Color |
|---|---|---|
| TAPED | contractor tape: Tape Check values, user_measured, sealed hand-takeoff key | green solid |
| AI-READ ✓ | direct_ref (ref-anchored) / direct_consensus / direct_single_reading | green outline |
| AI-READ ⚠ | direct_disagreement / cross_plane / below_typical_range | amber |
| ESTIMATED | estimated_no_direct_view / defaulted / bbox-fallback position | amber dashed |
| PRINTED | blueprint runs: printed dimension callouts | blue |
| USER | user overrides entered without tape claim | purple |
All chips grayscale-safe (shape + fill pattern differ, not color alone).
**GEOMETRY-BASIS LINE (required from first mock):** the title block names the
source of the sheet's geometry per element class (walls vs openings), e.g.
"GEOMETRY BASIS: sealed hand-takeoff key EST-191890 (tape) · openings: AI run
d6679448". The source-naming rule applies to elevation sheets from their
first mock, not their first ship.

## 4. Data mapping (existing fields only)
- `raw_ai.walls[label]` → width_ft(+source), height_ft(+source, +_height_flag,
  +height_scale_flag), gable_triangle_height_ft, siding_pct_this_wall,
  wall_body_profile_callout, gable_profile_callout, confidence,
  confidence_reasoning, _per_photo_readings, _source_photo_indices.
- `raw_ai.openings[]` (filtered to wall) → type, style, width_in, height_in,
  along_wall_ft (position source: verified when present), bbox (sill Y +
  fallback X), on_dormer (dormer openings get their own inset panel later).
- `raw_ai.openings_schedule` → schedule table rows (size_label, count).
- `raw_ai.corner_locations` (this wall) → corner/appendage witness marks along
  the base line at position_frac, tier-colored (confirmed/unconfirmed/removed).
- Blueprint runs (`_source_kind="blueprint"`): identical sheet; sources map to
  PRINTED; appendages from the structured schema.
- User overrides (`overrides.widths/eaveHeights`, lp_appendage_dims) outrank
  AI values, tagged USER — same cascade as buildHouseJson.

## 5. Rendering & integration
- Pure SVG, computed client-side (same host as the run preview data), sized to
  US-Letter landscape (1056×816 @96dpi), print-first: no interactivity needed
  to be complete; hover/tap can highlight later.
- Scale auto-fit: px_per_ft = floor(drawable_width / wall_width); noted in the
  title block as an architectural ratio approximation.
- Surfaces: new "Sheets" tab in the AI Measure modal (one page per elevation,
  print stylesheet = 4-page packet) + "Elevation Sheets (PDF)" in the report
  actions. Contractor-only; customer surfaces unaffected.
- i18n: EN/ES via existing dictionaries.

## 6. Explicitly out of scope
- No new AI calls, no multi-mass geometry, no photogrammetry (Hover by design).
- No editing on the sheet (verification reads; edits stay in the 3D panel /
  Tape Check flows).

## 7. Review mock (v2 — re-delivered after source-naming rejection)
`/app/frontend/public/mock/letrick_front_elevation_sheet.svg` — Mark Letrick
front wall. WALL GEOMETRY from the tape-validated sealed key EST-191890:
54'-0" width (eaves 2×54), 8'-11½" eave (483.8 sqft ÷ 54', 25 courses) —
tagged TAPED. OPENING positions from AI run d66794488ef8 (along_wall_ft,
reconciler-verified) — tagged AI-READ ✓. The sheet carries the AI run's
DISAGREEING wall read (50'-0" / 8'-7" / 23-24 courses) as an explicit
deviation note — tape governs. Geometry-basis line rendered on the title
block. v1 mock (rejected): AI direct_ref values wearing TAPED REF.

