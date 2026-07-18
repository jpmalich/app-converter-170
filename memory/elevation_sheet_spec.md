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
   - **Collisions do NOT omit here**: overlapping opening rects render with a
     dashed red outline + "POSITION UNVERIFIED" chip instead. The 2D sheet can
     show conflict honestly where 3D cannot (this is why it's the primary
     verification surface).
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
| Tag | Fields that produce it | Color |
|---|---|---|
| TAPED REF | width_ft_source=direct_ref, WALL_REF-anchored | green solid |
| AI-READ ✓ | direct_consensus / direct_single_reading | green outline |
| AI-READ ⚠ | direct_disagreement / cross_plane / below_typical_range | amber |
| ESTIMATED | estimated_no_direct_view / defaulted / bbox-fallback position | amber dashed |
| PRINTED | blueprint runs: printed dimension callouts | blue |
| USER | user_measured / user override / user_confirmed_from_blueprint | purple |
All chips grayscale-safe (shape + fill pattern differ, not color alone).

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

## 7. Review mock
`/app/frontend/public/mock/letrick_front_elevation_sheet.svg` — Mark Letrick
front wall, run d66794488ef848509446431b355db8e5 (real values): 50'-0" TAPED
REF width, 8'-7" AI-READ✓ eave (23/24-course consensus), lap 4" callout,
100% siding, openings W1 68×61 @5'-6", W2 69×61 @24'-0", D1 38×82 @34'-0",
W3 72×60 @44'-0" — all reconciler-verified positions.
