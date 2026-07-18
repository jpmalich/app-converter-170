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
   - **Tape/AI deviation box (SPEC-LEVEL, ruled 2026-07-18)**: wherever tape
     and AI disagree on a sheet, an amber deviation box renders stating both
     values, the delta, and "tape governs" — not a one-off of the Letrick
     mock; a standing sheet element.
## 2b. Component color-coding (PALETTE APPROVED 2026-07-18, incl. teal OSC shift)
Classes mirror the existing ExpertFinish component groups. **CHANNEL
SEPARATION (PINNED):** component identity = LINEWORK color; measurement
status = chips/boxes/tags only — neither system ever borrows the other's
channel. Grayscale print legibility: every class also differs by line
weight/pattern, never hue alone.

APPROVED PALETTE (Howard 2026-07-18; status colors stay reserved — amber
deviation #B45309, TAPED/AI-READ✓ green #0D7A3F, PRINTED blue #1D4ED8,
USER purple #7C3AED, C-SPEC ink #111827):
| Class | Hue | Hex | Grayscale channel |
|---|---|---|---|
| Siding field | slate | #475569 | thin solid 1.75px + pale course hatch |
| Opening trim | red | #DC2626 | solid 2.25px |
| Outside corners | teal | #0D9488 | solid 3.5px (heaviest) |
| Inside corners | magenta | #DB2777 | dashed 6-3, 2.25px |
| Fascia / rake | sky | #0EA5E9 | solid 3px |
| Soffit | coffee brown | #6B4423 | dotted, 2.5px |
| Starter | charcoal | #1F2937 | dash-dot, 2.5px |
| Band board (contractor-spec) | plum | #86198F | long-dash 10-4, 2.75px |
APPROVED 2026-07-18: outside corners = TEAL (Howard's "e.g., green" was
illustrative; status-green stays reserved — channel-separation pin applied
correctly). Red opening trim confirmed.

- **Merged legend block**: ONE key, title-block-adjacent — component linework
  samples + source-tag chips, labeled "linework = component · chips = source".
- **Schedule cross-reference** (Hover measurement-key pattern): every schedule
  row carries a color swatch matching its drawn element's class.

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
| CONTRACTOR-SPEC | design-decision features (e.g., band board) — added, not measured; provenance-logged, revertible; excluded from all accuracy comparisons | ink solid |
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


## 8. BAND BOARD (feature ruling 2026-07-18 — conventions now, ships WITH the 2D sheets)
First entry of the Options & Upgrades cluster (not a separate build). No
September scope change.
- **Composition rule:** band board = horizontal trim at a wall's story/gable
  break. LF = sum of widths of the walls it wraps, anchored at the
  gable-break/eave height the geometry already carries. Pieces = whole
  sticks, splice-and-round-up per standing rule. Profile = contractor-
  selected from the 440/540 trim stock (540 5/4×8 and 5/4×12 typical).
  Color per-component per existing architecture. Priced through the engine
  like any trim line.
- **CONTRACTOR-SPEC source tag (RULED NOW, taxonomy addition):** for features
  a human adds by DESIGN DECISION rather than measures or ratifies.
  Provenance-logged (by/at, revertible) like every other verb. NEVER enters
  any accuracy comparison — it isn't a measurement. Chip: ink #111827 solid.
- **Sheet rendering:** contractor-added band board draws on the elevation at
  the anchored break height, in its component color (proposed: plum #86198F,
  long-dash 10-4, 2.75px — pending palette approval with the rest), listed
  in the schedule with the CONTRACTOR-SPEC chip. Deviation machinery does
  NOT apply (nothing to deviate from).
