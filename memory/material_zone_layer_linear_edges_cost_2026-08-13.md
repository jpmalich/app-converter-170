# MATERIAL ZONE LAYER — LINEAR-EDGES + LEGEND INCREMENT COST
Report only, requested with the SEND-11 handback. No build.

Howard's ruling (2026-08-13): "MUV as scoped looks like FILLED
REGIONS ONLY. My original ask had two halves and the second one is
the part a BDM sees. Cost this separately, report only, do not build."

## THE INCREMENT (Howard's words)
### (a) Coloured LINEAR EDGES
Fascia, J-channel, inside corners, outside corners, starter. These
are RUNS, not areas — an edge drawn along a boundary that produces
**linear feet**, not square feet. Same drawing surface as the MUV
polygons (the original elevation PDF page), but the primitive is a
POLYLINE with a category, not a POLYGON with a material class.

### (b) THE TWO-KEY LEGEND
- Filled swatches for area lines (siding, soffit, accent, ...).
- Edge swatches for linear lines (fascia, J, corners, starter).
- Quantity beside every swatch:
   - Siding 3,986 ft².
   - Starter 194 LF.
   - Outside corners 6.
- The drawing BECOMES the takeoff summary, not a picture next to
  one.

### (c) HONESTY LAYER — rides BOTH halves
A null or flagged zone renders HATCHED OR GREYED with "NEEDS YOUR
TAPE" on the wall it belongs to. Never silently omitted. Never
silently drawn as known.

## SCOPE — what has to land for the increment

### Backend
 - `pdf_overlay_edges` collection (parallel to `pdf_overlay_polygons`):
   `{est_id, page, face_id, edge_class, vertices_pct[], qty_src,
     created_at, author_id}`. `edge_class ∈ {fascia, j_channel,
     inside_corner, outside_corner, starter}`.
 - GET/PUT/DELETE routes under `/api/estimates/{eid}/pdf-overlay-edges`
   (same shape as the MUV polygon endpoints).
 - `apply_edges_to_takeoff(edges, sheets)` — polyline length in
   ft at 3/16" = 1'-0" (or per-page calibration), writes to the
   matching lp line's `qty` and stamps `qty_src="human"`.
 - Outside/inside corner counts increment by 1 per polyline (not
   by length) — corners are units, not runs.
 - Extend the existing `pdf_overlay_write` seam entry to cover
   edges (or add `pdf_overlay_edge_write` — a second seam name
   costs one registry line and keeps polygon-vs-edge separated in
   the ledger).
 - Honesty payload: every face's takeoff row exposes a
   `render_status` field: `known | needs_tape | flagged`. Existing
   `_dim_unverified` / `_dim_fabricated` / `_dim_misread` collapse
   into this at the takeoff level. Wall-level status computed once,
   consumed by both filled + edge renderers.

### Frontend
 - Extend `PdfOverlayEditor.jsx` (the MUV page):
   - New tool switch: `POLYGON | POLYLINE`.
   - Polyline tool: click sequence of vertices, double-click / Esc
     to close (or leave open — an edge does not have to close).
   - Category dropdown driven by primitive: material-class for
     polygons, edge-class for polylines.
   - Live LF readout beside the polyline (mirrors the sqft readout
     on polygons).
 - New `LegendPanel.jsx` — pinned right side of the editor and the
   BlueprintCard. Two columns:
   - Left: filled swatches + area quantities.
   - Right: edge swatches + LF/count quantities.
   - Every row links back to its polygons/polylines (click a legend
     row, editor highlights the primitives).
 - Hatched / greyed rendering for `render_status ∈ {needs_tape,
   flagged}`. One shared React component (`HonestyOverlay.jsx`)
   consumed by BOTH filled polygons AND polylines, driven by the
   wall's render_status. "NEEDS YOUR TAPE" label pinned to the
   wall the flag belongs to.

### Tests (all pins added at MUV, none deferred)
 - Backend: edges CRUD + polyline→LF math + corner-count
   increment + rebuild survival + `pdf_overlay_edge_write` seam.
 - Registry: `pdf_overlay_edge_write` in `seam_accounting`.
 - Schema-consumer: `edge_class`, `render_status` added to
   `INTERNAL_KEYS` (or the schema, if we want them prompted).
 - Frontend: e2e via `testing_agent_v3_fork` — draw a fascia edge
   on front elevation, watch fascia LF appear in the legend; flag
   a wall's height, watch it render hatched with NEEDS YOUR TAPE.

### Deliberate EXCLUSIONS from this increment
 - No snapping (polylines are hand-drawn straight, same as MUV
   polygons).
 - No end-cap or miter counting inside a polyline (a polyline is
   ONE run; if a wall has two independent fascia runs, draw two
   polylines). End caps ride on inside_corner + outside_corner
   counts.
 - No auto-derivation of edges from the polygon boundary. If the
   user wants a fascia along the top of a siding polygon, they
   draw it. Auto-derivation is powerful and interesting and it is
   NOT what makes this a MUV.

## COST — LINEAR-EDGES + LEGEND INCREMENT

| PHASE | Sessions | What lands |
|---|---|---|
| `pdf_overlay_edges` + polyline→LF + corner counts + tests | 1 | Edge model, CRUD, math, seam registered |
| Polyline tool + tool-switch UI + LF readout in PdfOverlayEditor | 1 | User can draw an edge and see its LF |
| LegendPanel two-key layout + click-to-highlight + quantity binding | 1 | The drawing IS the takeoff summary |
| Honesty layer (`render_status`, hatched rendering, "NEEDS YOUR TAPE" label, shared component) + e2e regression | 1 | A null zone can never render as known |
| **TOTAL (increment)** | **~4 sessions** | Two-key legend + linear edges + honesty layer |

## HOW IT COMPARES TO THE MUV BASELINE
 - MUV (already costed at ~4 sessions): filled polygons + polygon→sqft
   + rebuild survival + PdfOverlayEditor.
 - Increment (this report, ~4 sessions): edges + two-key legend +
   honesty layer.
 - **Combined (MUV + increment)**: ~7 sessions (~1 saved by reusing
   PdfOverlayEditor and the `pdf_overlay_*` write pattern; the
   remaining 7 is not 4+4 because half of PdfOverlayEditor is shared).
 - **Timing**: 7 sessions fits inside September if I start now.
   Two weeks + a couple days.

## THE DECISION HOWARD ASKED FOR
Ride with MUV (~7 sessions total): a BDM sees the two-key legend
on day one, the drawing IS the takeoff summary, the honesty layer
prevents a silent-nulled wall from looking correct on the sheet.
This is what the ask actually is — the second half is the part a
BDM sees.

Follow immediately after MUV (~4 sessions each, back-to-back):
delivers MUV first as a demonstrable "quantity moves" round-trip,
then the summary/legend layer as a follow-up ship. Faster to a
first-signal build; slower to the full "drawing IS the takeoff"
outcome.

## RECOMMENDATION
Ride with MUV. The increment is the second half of one instrument,
not a separate feature. A BDM meeting where the polygon moves the
sqft but there is no legend and no edges is a demo of half a
promise; the whole promise fits inside September.

Awaiting the ruling.
