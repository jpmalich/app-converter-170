# LINEAR-EDGES + TWO-KEY LEGEND + HONESTY LAYER — WALK-READY SCOPE
Report only. Prepared 2026-08-13 so this increment can start the
DAY Howard finishes walking MUV — no scope gap, no scoping session.

Howard ruled (pro-quotes reply, 2026-08-13): "SCOPE THE INCREMENT
NOW so it can begin the day I finish walking, and do not let the
gap fill with other work."

**PRECONDITION**: MUV is walked and passes Howard's five-point
bar (open real elevation page → draw/drag polygon over a wall →
sqft changes → material line changes → marked as HIS entry → still
there after rebuild). If any of those five fail on the walk, THIS
document is stale and the increment's shape gets revisited.

## GOAL (one sentence)
The drawing IS the takeoff summary: filled polygons for area
lines, coloured polylines for linear runs, a two-key legend that
names every quantity, and hatched/greyed rendering for any zone
whose evidence was killed by the send-11 tiers.

## SESSION-BY-SESSION SCOPE (~4 sessions total)

### SESSION 1 — Edge model + math + rebuild survival + tests
- **New collection**: `pdf_overlay_edges` — one document per
  polyline. Schema:
    ```
    {
      id: uuid,                       # app-minted
      estimate_id: str,
      page: int,                      # PDF page index (1-based)
      face_id: str,                   # front|back|left|right|dormer:<label>
      edge_class: str,                # fascia|j_channel|inside_corner|outside_corner|starter
      vertices_pct: [[x_pct,y_pct]],  # page-normalised, same shape as _dim_evidence.loc
      qty_src: "human",               # verbatim; hover.py's survive-rebuild shield
      author_id: str,                 # writer's user id
      created_at: datetime,
      updated_at: datetime,
    }
    ```
- **CRUD routes** (mirror the MUV polygon routes exactly):
    - `GET  /api/estimates/{eid}/pdf-overlay-edges`
    - `PUT  /api/estimates/{eid}/pdf-overlay-edges` (upsert one)
    - `DELETE /api/estimates/{eid}/pdf-overlay-edges/{edge_id}`
    - `PUT  /api/estimates/{eid}/pdf-overlay-edges/bulk` (list replace, atomic)
- **`apply_edges_to_takeoff(edges, sheets)`** — deterministic math:
    - **fascia, j_channel, starter**: sum of polyline length in ft,
      converted from `vertices_pct` via each page's calibration
      (default 3/16" = 1'-0"; override rides the sheet's own
      `scale` when present). Writes to the matching lp line's
      `qty` and stamps `qty_src="human"`.
    - **inside_corner, outside_corner**: ONE increment per polyline
      (counts, not runs). A corner is a unit, not a length.
    - Face-level attribution: a polyline "belongs" to the face
      whose polygon it starts inside (if any). If no polygon
      overlaps the polyline's first vertex, the polyline is
      attributed by `face_id` on the record.
- **Rebuild survival pin**: `test_pdf_overlay_edges_survive_rebuild`
  — inserts an edge, forces a rebuild of the takeoff via the
  existing hover.py path, asserts the edge's `qty_src="human"`
  row rides through unchanged (SAME instrument as the polygon
  test in MUV; new pin, same shield).
- **Seam registered**: `pdf_overlay_edge_write` in
  `seam_accounting.SEAM_REGISTRY` — a write with no `edge_class`,
  a bad `face_id`, or vertices outside `[0,1]` is a REPORTED
  removal, never silent.

### SESSION 2 — Editor: polyline tool, tool-switch, LF readout
- **`PdfOverlayEditor.jsx` extended** (the MUV page, not a new
  page):
    - **Tool switch (top-left, two buttons)**: `POLYGON | POLYLINE`.
      Keyboard shortcut: `P` toggles.
    - **Polyline tool**: click sequence of vertices; double-click
      or `Esc` completes; polyline stays OPEN (edges don't have
      to close — a fascia run is a run, not a boundary).
    - **Category dropdown**: primitive-driven. Polygon → material
      class (siding, soffit, accent, ...); polyline → edge class
      (fascia, j_channel, inside_corner, outside_corner, starter).
    - **Live LF readout**: floats beside the polyline while
      drawing, sticks beside the finished polyline. Same
      component pattern as the MUV polygon sqft readout.
    - **Corner mode**: when `edge_class ∈ {inside_corner,
      outside_corner}`, the polyline collapses to a single vertex
      (a corner is a point, not a run). Click-drag disabled;
      click-once places one corner.
- **Debounced PUT to the new edge endpoint on every change**;
  same debounce interval as MUV polygons (200ms).
- **e2e via testing_agent_v3_fork**: draw a fascia edge on the
  front elevation; watch the fascia LF row change; refresh; edge
  survives; row still shows the new LF.

### SESSION 3 — LegendPanel: two-key, click-to-highlight
- **New component `LegendPanel.jsx`** — pinned right side of the
  editor and the BlueprintReadBackCard. Two columns:
    - **Left**: filled swatches + area quantities (from
      `pdf_overlay_polygons` + existing extraction sqft).
      Format: `Siding 3,986 ft²`.
    - **Right**: edge swatches + LF/count quantities (from
      `pdf_overlay_edges` + existing extraction LF/counts).
      Format: `Starter 194 LF`, `Outside corners 6`.
- **Every legend row is clickable**: click → editor highlights
  every polygon/polyline of that class (dashes their strokes,
  fades the rest). Second click clears the filter.
- **Quantity binding**: the legend reads the SAME takeoff row the
  lp line consumes — the drawing and the takeoff are one number,
  not two views. When Howard corrects a wall, the legend moves,
  the lp line moves, and no third path exists to disagree.
- **Print view**: `LegendPanel.jsx` composes onto the print stylesheet
  the same way the existing sheet renderers do; when Howard prints
  the sheet, the legend prints with it. The drawing on paper IS the
  takeoff summary.

### SESSION 4 — Honesty layer + full regression walk
- **`render_status` field** on every face row: `known |
  needs_tape | flagged`.
    - `known` — evidence is intact.
    - `needs_tape` — width or height on this face is null on raw
      (send-9 unverified, send-10 shared-source demoted, send-11
      misread, send-11 fabricated).
    - `flagged` — a consistency check fires loud on this face
      (opposing walls disagree, openings exceed wall width,
      eave/rake orientation, gable-mismatch).
- **`HonestyOverlay.jsx`** — one shared React component consumed
  by BOTH filled polygons AND polylines. Renders as:
    - `known` → normal stroke and fill.
    - `needs_tape` → diagonal hatch (SVG pattern), muted colour,
      pinned label "NEEDS YOUR TAPE".
    - `flagged` → red dashed stroke, hatched fill, pinned label
      naming the flag code (send-9 vocabulary already in EN + ES).
- **`test_render_status_never_lies_pin`** — for every send-9/-10/-11
  fixture already in the suite, assert `render_status` reaches the
  card and matches the tier that killed the value. NO fixture in
  which `render_status="known"` while `_dim_unverified` /
  `_dim_fabricated` / `_dim_misread` names the same path — a
  silent-known rendering of a killed dim IS the class we killed.
- **testing_agent_v3_fork full walk**: MUV polygon flow + this
  increment's linear-edges + legend + honesty layer, on the Boni
  fixture. Every send-11 tier surfaces in the legend and the
  drawing.

## THE 5-POINT WALK BAR (extended from MUV)
When Howard walks the increment, the bar is the same as MUV plus
three additions:
1-5. Same as MUV.
6. He draws a fascia polyline on the front elevation; the fascia
   LF row in the legend changes to match.
7. He places two outside_corner marks on the plan; the "Outside
   corners" count moves from 4 to 6.
8. A wall whose height is null (send-11 misread or fabricated)
   renders hatched with NEEDS YOUR TAPE on the drawing, never
   silently as known.

If any of 6-8 fail, the increment does not pass and gets more
scope, not a green stamp.

## READY-TO-START CHECKLIST
- [x] Scope document exists (this file).
- [ ] MUV is walked and passed by Howard.
- [ ] `pdf_overlay_polygons` collection + `PdfOverlayEditor.jsx`
      already in the tree (they land with MUV).
- [ ] Howard rules on THIS document if he wants the scope
      trimmed, extended, or resequenced.

The day the MUV walk ends: start session 1 of this document. No
scoping session. No planning gap.
