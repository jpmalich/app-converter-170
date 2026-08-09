# SCOPE: MARKED-UP TAKEOFF ELEVATIONS — BLUEPRINT DOOR (Howard ordered scoping 2026-08-09 send 5; BUILD GATED behind card walk + flag census/gate truthfulness)

RULING SUMMARY: Approach (A) — render a SYNTHETIC elevation from the
blueprint model, never paint the architectural sheet. Honesty carries onto
the drawing (null/flagged walls hatch "NEEDS YOUR TAPE"). Legend carries
AREA swatches (filled regions) and LINEAR swatches (coloured edges), each
with its quantity — the drawing IS the takeoff summary. Zone model built
as a FIRST-CLASS layer (reusable for deferred (B); (B)'s only unique piece
is pixel-space segmentation). Do not start until mark-merge is closed
(closed 2026-08-09: detection seam + suspicion-revoked leniency + row
identity prompt rule — but note the model-side merge still OCCURS; the
seam flags it loud and kills copied dims. A drawing built while
mark_merge_suspected fires should hatch the affected openings).

## Q1 — CAN THE PHOTO DOOR'S EL RENDERER TAKE BLUEPRINT GEOMETRY? YES.
Mechanism (read from the code): the renderer is TWO layers.
- Backend `GET /api/estimates/{id}/elevation-sheet/{which}`
  (routes/elevation_sheets.py, ~1,900 lines) builds a JSON SHEET CONTRACT:
  wall frame (width/height or stepped segments), roofline binding, gable
  bands, dormer solids, chases, openings bound at x-positions, and a
  BASIS/honesty tag on every figure (the geometry-source ladder: sealed
  key > tape check > AI run, every rung labeled).
- Frontend `SheetSvg` (pages/ElevationSheet.jsx, ~1,100 lines) draws pure
  SVG from that contract. It knows NOTHING about photos — every region's
  pixels are known by construction, which is exactly why it can be
  coloured.
THE COUPLING IS ONE QUERY: the endpoint hard-binds to `ai_measure_runs`
(photo door) and 404s otherwise. What reuse takes: a BLUEPRINT CONTRACT
BUILDER — same output shape, sourced from ai_blueprint_runs raw (walls +
wall_segments + gable_triangle_height_ft + pitch + schedules). The
photo-only ladder rungs (sealed keys, tape checks, course counts) simply
don't apply on the blueprint door yet — the AI-run rung of the ladder
already exists and is labeled, so the contract stays honest without them.
SheetSvg itself needs ZERO changes for Phase 1, additions (zone colouring)
for Phase 2.

## Q2 — WHAT THE ZONE MODEL NEEDS THAT THE BLUEPRINT READ DOESN'T PRODUCE
1. OPENING PLACEMENT — as expected, the big one, in two halves:
   a. Wall ATTRIBUTION exists (windows/doors carry `elevation`) but it is
      in the PROMPT-ONLY unverified family (audit 2026-08-09) — nothing
      checks a mark landed on the right wall.
   b. X-POSITIONS do not exist at all (photo raw carries along_wall_ft;
      blueprint raw has nothing). Phase 1 answer: schematic even spacing
      within the attributed wall, LABELED "schedule-attributed, position
      schematic" — never claimed as placed. True placement would need a
      floor-plan coordinate pass (a later read, not scoped here).
2. PER-EDGE CORNER ASSIGNMENT — corner COUNTS are global; which wall
   edges are outside vs inside on a stepped facade needs deriving from
   wall_segments adjacency (derivable; a wing with no segments hatches).
3. SOFFIT/FASCIA GEOMETRY per wall — plane eave/rake figures are now
   evidenced (2026-08-09) but not attributed per wall edge; the zone
   model maps them via the eave-bearing-wall rule already in the
   aggregator.
4. LINE BINDING — zones must bind to est.lines rows (name/section map)
   so each swatch carries the LIVE quantity (Siding 3,986 ft² · Starter
   194 LF · Outside corners 6), and updates when the takeoff does.

## Q3 — SCOPE AND COST
- Phase 1 — blueprint sheet contract (~1 session): contract builder +
  `/estimates/{id}/blueprint-elevation/{which}` reusing SheetSvg
  unchanged; hatched "NEEDS YOUR TAPE" walls for null/derived heights
  (Boni back garage wing is the acceptance case); schematic openings,
  labeled.
- Phase 2 — MATERIAL ZONE MODEL + coloured legend (~1.5 sessions):
  backend material_zones.py (first-class, renderer-independent): zones =
  filled regions (siding body, gable accent, soffit) + edges (fascia,
  J-channel, corners, starter), each {line_binding, qty, basis,
  flagged}; SheetSvg overlay layer + two-key legend with quantities;
  flagged/null zones hatch on the wall they belong to.
- Phase 3 — the instrument (~0.5 session): 4-elevation card on the
  blueprint door + print view; a wrong model draws a wrong house (the
  orientation flip, the 4-gables-on-2-walls, the null wing — all visible
  in one second).
- TOTAL ≈ 3 sessions. Reused for (B): zone model, legend, colours,
  quantity binding, honesty rendering, summary layout. (B)-unique:
  pixel-space segmentation of the architectural drawing only.

## BUILD GATE (Howard's standing order)
Queue: card walk (a4cbce91) → FLAG CENSUS (e) → GATE TRUTHFULNESS (g) →
then this. Bar (c) HELD until Monday's invoices.
