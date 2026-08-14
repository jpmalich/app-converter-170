# MUV WALK FIXES — Howard walk report 2026-08-13 (S3 stays held)

Six of seven walk-bar points passed on the first walk. This doc reports
the units chain (Defect 1), the fixes for Defects 1–4, and the Defect-5
cost. Backend green deterministically (2358 passed / 4 skipped;
`pytest -p no:randomly`). The 4 failures seen under random ordering are
PRE-EXISTING cross-test shared-state flakiness in the 3D-render/redact
tests, not MUV — they pass in isolation and in deterministic order.

## DEFECT 1 — AREA MATH. UNITS CHAIN REPORTED, FIXED, PINNED.

### The chain as it RAN on the walk (the broken READ path)
1. Polygon vertices captured in page-NORMALISED [0,1] display coords,
   then × the elevation image's naturalWidth/Height → NATURAL raster px.
   (Correct — and note DPI CANCELS here, because the calibration and the
   polygon were both measured in this same natural-px space.)
2. Calibration (old READ path): Claude was asked for the two PIXEL
   endpoints of the "24'-0"" dimension line. Vision models cannot return
   precise arrowhead pixels — it returned a span roughly 3.6× TOO SHORT
   (Howard's "measured the dimension text's bounding box, not the line's
   arrowhead-to-arrowhead span" suspect). real_ft = 24.
3. feet-per-pixel = 24 / (too-short px) → ~3.6× TOO LARGE.
4. area_ft² = area_px × (ft/px)² → (3.6)² ≈ 13× too large.
   → 1,160 ft² read as ~14,923 ft².
5. ÷100 → SQ: 149.24 SQ. (The ÷100 is correct; the whole error is the
   ft-per-pixel in step 3.)

VERDICT: NO DPI double-count in the code (DPI cancels). The root cause is
that AI-returned pixel endpoints are unreliable for area — the square of
a linear error. Howard's second suspect was right.

### The fix — a DETERMINISTIC chain, no vision pixel coords
PRIMARY (Law C) — read the printed scale FRACTION as TEXT and combine
with the page's RECORDED render DPI:
  paper inches per foot  s = 3/16 = 0.1875   (parsed from "3/16\"=1'-0\"")
  feet per paper inch    = 1/s = 5.333
  pixels per paper inch  = DPI (72 × PDF_RENDER_SCALE = 144 for PDF
                           renders; RECORDED on the run as evidence, not
                           assumed; None for scans → REFUSE, user traces)
  feet per pixel         = 1/(s × DPI) = 1/27 = 0.037037
  area_ft²               = area_px × (ft/px)²
No pixel endpoints anywhere; the only model step is reading characters.

FALLBACK — human TRACE: the contractor drags a line over a known printed
dimension and types the feet. The human places the endpoints precisely,
so it is reliable and resolution-independent (works on scans with no DPI).

### The pin (a CHECK, not a target)
`test_printed_scale_pins_howard_rear_wall_to_1160_sqft`: a polygon of the
rear wall's pixel extent (58'×20' at 3/16" & 144 DPI) returns 1,160 ft².
Landing at 1,160 means the chain is right; anything else means it is
still wrong. PASSES.

## DEFECT 2 — FACE FROM PAGE. Never default; refuse when ambiguous.
Discovered: EST-886440's page 1 is titled "FRONT & REAR ELEVATIONS" — a
SINGLE page holds TWO faces. So auto-deriving one face is itself wrong
(that is exactly how the rear zone became "front"). RULE now:
`faceFromTitle` returns a face ONLY when the title names EXACTLY ONE
face; a two-face title ("FRONT & REAR") or none → returns "" and the
editor REFUSES to save until the user picks. The face picker shows its
origin ("from page …" vs "page didn't identify one — pick it"). The
default of "front" is gone.

## DEFECT 3 — PROVENANCE LABEL. Names the path that ACTUALLY ran.
The scale carries a `source` string set by the path that ran: READ sets
`READ · <printed scale text>`; TRACE sets `TRACE · you calibrated N ft`.
The panel shows that string verbatim. It never says "traced" for a READ.

## DEFECT 4 — PRINTED SCALE TEXT. Now reads. (Confirmed live.)
Root cause: the old `/measure/ocr-scale` prompt PRIORITISED the dimension
LINE and only read the scale block as a fallback — so on the rear page it
found the 24' dimension and never reached the printed scale. New endpoint
`/measure/read-page-scale` reads ONLY the printed scale block and parses
the fraction deterministically. Live on EST-886440 page 1 it returned
`3/16" = 1'-0"` → in_per_ft 0.1875, view_title "FRONT ELEVATION", note
"Two elevation views shown: Front and Rear" (which also confirms Defect 2).

## DEFECT 5 — PER-WALL BREAKDOWN DISPLAY. Cost: NEAR-FREE. Shipped.
The app already computes per-wall areas and stores them at
`result.measurements._per_elevation_breakdown` (front wall_body 920 ft²,
etc.). DISPLAYING them needed only a read + a read-only panel — no new
computation, no binding change. So it is shipped: the editor now shows
"App's per-wall siding (read-only, not bound)" with wall/gable/dormer per
face. This is what lets Howard judge each correction against the app's own
pieces. It is DISPLAY ONLY — per-face BINDING is still the structural
1.5–2 session change (and partial-coverage a further ~1 session on top).

## STATE OF EST-886440 FOR THE RE-WALK
It is an IMAGE-SCAN blueprint (.jpg pages), so there is no knowable render
DPI → the READ-printed-scale path reads the fraction but REFUSES to
convert (honest) and directs Howard to TRACE. TRACE gives correct,
1,160-pinned areas on scans. A PDF-sourced blueprint would let READ
convert end-to-end deterministically.
