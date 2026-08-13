# MATERIAL ZONE LAYER — COST for the PDF-OVERLAY EDITABLE FORM
Report only, requested with the SEND-11 handback. Do not start until
ruled. The ~3-session figure Howard remembers covered the SYNTHETIC
sheet form (2D orthographic drawings the app builds from extraction
fields — `elevation_sheet_spec.md`, ruled 2026-07-18). Drawing on the
ORIGINAL PDF pages with user-adjustable polygons that write back to
the SAME structured takeoff — this is the new cost.

## THE INSTRUMENT (what "position 5" means, verbatim)
Original elevation PDF sheets, in place. User draws / drags polygons
over the printed elevations. Each polygon carries:
  - a MATERIAL CLASS (lap / smart / accent / soffit / trim / ...)
  - a face_id (front | back | left | right | dormer:<label> | ...)
  - vertices in PAGE-NORMALISED coords (x_pct / y_pct — same shape
    as `_dim_evidence.loc` today)
Scale = 3/16" = 1'-0" drives sqft on the polygon; the polygon writes
back to the SAME structured takeoff row the current synthetic sheet
uses (a face_sqft on the material line). `qty_src == "human"` stamps
the edited row so every rebuild path already in `hover.py`
(l.3407 onward — "Human-typed rows always survive verbatim") passes
it through. Simplified synthetic sheets stay as a SECONDARY summary
view — not removed, not primary.

## MINIMUM USEFUL VERSION (Howard: "smallest thing that lets me
correct a wall on the real drawing and see the quantity move")
### MUV scope
 1. Backend
     - `pdf_overlay_polygons` collection with {est_id, page, face_id,
       material_class, vertices_pct[], qty_src, created_at,
       author_id}. TTL: NONE (protected same as takeoff rows).
     - GET/PUT/DELETE routes under `/api/estimates/{eid}/pdf-overlay`
       (list / upsert / delete). One endpoint hitting one collection.
     - `apply_overlay_to_takeoff(polygons, sheets)` — deterministic
       polygon→sqft using 3/16"=1'-0" (the scale ships as a per-page
       calibration override so misprints don't wreck the read;
       fixed 192-per-ft default). Writes to the matching lp row's
       `face_sqft` and stamps `qty_src="human"`.
     - Rebuild guard: on any re-read, the overlay-derived rows survive
       via the existing send-hover `qty_src=="human"` clause. Named
       pin: `test_pdf_overlay_survives_rebuild`.
 2. Frontend
     - New page `PdfOverlayEditor.jsx` (parallel to
       `BlueprintElevationSheet.jsx`, ~800 LoC target). Renders the
       ORIGINAL PDF page (existing `image_payloads[page-1]`
       infrastructure) at fit-to-width, click-to-add polygon,
       drag-vertex, drag-polygon, delete, material-class dropdown.
       No 3D. No syntactic drawing.
     - Reads scale from `sheets_identified[i].scale` when present;
       falls back to 3/16" and shows a "SCALE: 3/16\" = 1'-0\" —
       calibrate?" chip.
     - Writes to the new PUT endpoint on every debounced change.
     - Quantity readout beside the polygon (live sqft) — SO the
       "correct a wall, see the quantity move" is one action.
 3. Tests (all pins added at MUV, none deferred)
     - Backend: overlay CRUD, polygon→sqft math, rebuild-survival,
       schema-consumer keys (add face_id, vertices_pct,
       material_class, page, author_id to INTERNAL_KEYS if any
       consumer reads them bare).
     - Registry: seam entry `pdf_overlay_write` in seam_accounting.
     - Frontend: e2e via testing_agent_v3_fork — add a polygon on
       front elevation, watch the front face's siding sqft increase.

### MUV EXCLUDES (deliberately, so the ship stays inside 3 weeks)
 - No collision detection between polygons (allowed to overlap).
 - No per-vertex snapping / auto-square. Straight-edge polygons
   only in MUV; freeform curves deferred.
 - No dormers as a first-class type — dormer polygons ride under
   `face_id="dormer:<label>"` and take their scale from the same
   page's calibration.
 - No print-time compositing of overlays back onto a PDF export
   (view-only in-app; the takeoff row is the durable artifact).
 - No accent-injection routing — accents draw as polygons, the
   material-class dropdown catches them.

## COST — PDF-OVERLAY EDITABLE FORM

| PHASE | Sessions | What lands |
|---|---|---|
| Data model + endpoints | 1 | pdf_overlay_polygons + CRUD + tests |
| Polygon→sqft + rebuild-survival | 1 | Deterministic math, hover.py `qty_src=="human"` verified in a new pin, seam registered |
| PdfOverlayEditor page | 1.5 | React page rendering the raw PDF page, click-to-add polygon, drag-vertex, material-class dropdown, live sqft readout, debounced PUT |
| Wire the takeoff card + testing_agent_v3_fork | 0.5 | Live "watch the quantity move" round-trip on Boni fixture; regression pins land |
| **TOTAL (MUV)** | **~4 sessions** | Correct-a-wall-see-the-quantity-move works on real PDFs |

For comparison: the ORIGINAL SYNTHETIC sheet estimate was ~3
sessions and covered the drawing PLUS the render — no editing
surface, no round-trip to the takeoff. Adding editing + round-trip
without the synthetic-sheet toil is close to a wash; the PDF as the
canvas actually SAVES the "how do we draw an accurate elevation"
work, because the original drawing IS the canvas.

### Beyond MUV (not in the 4-session figure)
 - Polygon snapping / auto-square / auto-close.
 - Per-polygon material sub-variant (LP vs vinyl within `lap`).
 - PDF export with polygons composited back onto the source pages.
 - Multi-user simultaneous editing (CRDT / OT).
 - Voice-driven polygon commands ("add a lap zone on the front
   above the porch roof").

These stay in the queue; MUV lands the read-defect-answer Howard
ruled at position 5 without dragging the ship past September.

## RISK REGISTER
 - **Scale calibration.** A misprinted or scanned-at-different-scale
   sheet breaks the read. Mitigation: a per-page calibration override
   (drag a known dimension, app back-computes ft-per-pixel — one-off
   per sheet, sticks). MUV ships the chip and default; the
   drag-calibrate ships in "Beyond MUV" if scale disputes surface.
 - **PDF page rasterisation cost.** The existing `image_payloads`
   pipeline already rasterises every page (SEND-8 OCR gate uses
   the same). Reuse — no new cost.
 - **Rebuild survival.** The `qty_src=="human"` guard in hover.py is
   the same instrument that already protects legacy hand-typed
   rows. New surface, existing shield — the test pin is the
   contract, not new code.

## RECOMMENDED CALL
Ship the MUV in 4 sessions — that is the "smallest thing that lets
me correct a wall on the real drawing and see the quantity move".
Two weeks fits, September clears with a margin.

Awaiting the ruling.
