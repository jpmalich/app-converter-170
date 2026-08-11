# ELEVATION SHEET MECHANISMS — run 80c10620, EST-886440 (2026-08-11)
Report only. No fixes applied. PURITY: disagreements reported, nothing tuned.

## 1. GARAGE STEP — RENDERER, not model
The model CARRIES the step, fully read:
  front.height_segments = [main body 2-story 34'@20'-0", garage wing
  1-story 24'@10'-6"]  (back wing height null — correctly flagged)
The Phase 1 renderer (routes/blueprint_elevation.py) discards it by
construction:
  - line ~193: `"segments": None` — hands SheetSvg NO segments, ever
  - lines ~147-155: converts the segments to a TEXT note only
    ("STEPPED WALL — drawn as one rectangle at the eave height")
  - lines ~157-158: refuses area on stepped walls → "not derivable"
So the front draws one flat 58'×20' rect at the eave height. The segment
work reached the model and STOPPED at the renderer — a deliberate Phase 1
simplification, disclosed in text, visually wrong. SheetSvg already
renders stepped walls for photo-door sheets (the `segments` contract
exists); Phase 2 maps height_segments → segments.

## 2. FRONT-FACING GABLE — MODEL, read at plane level, never attributed
to a wall. The model's own two representations DISAGREE and nothing flags it:
  - wall level: front.gable_triangle_height_ft = 0 (left/right carry
    11'-4½" each → 2 wall gables)
  - plane level: main plane gable_ends=2 PLUS garage/bonus plane
    gable_ends=2 → _gable_ends_plane_read = 4
Two of the four plane-read gable ends (the garage/bonus plane's — the
wing whose ridge runs perpendicular, ends facing front/back) are
UNATTRIBUTED to any wall. The renderer trusts walls[] only → "Gable
none" on the front sheet. Not dropped by any seam — a cross-
representation contradiction (4 vs 2) with NO census. Candidate
instrument: gable-ends census — sum(plane gable_ends) vs count of wall
gable attributions; disagreement flags loud.

## 3. PORCH — RENDERER (Phase 1 never reads porch at all)
Model carries it: porch plane is_porch=true, 16'-6" × 6'-0", 99 ft²
ceiling, eave 50 LF, quoted evidence (porch.porch_width_ft /
porch_depth_ft in _dim_evidence). blueprint_elevation.py contains zero
porch reads. Phase 2 scope.

## 4. 20-vs-16 WINDOWS — a READ DISAGREEMENT between runs, undetected
because the grading chain was reaped
This run's mark C: qty=9 with count_by_page {"6": 9} — the model claims
a printed COUNT cell of 9 on sheet 6. qty AGREES with its own count
column, so _enforce_count_column had nothing to correct (correctly — no
governance fired). Ground truth (and the a4cbce91 chain): C = 5.
A: count_by_page {6:2, 7:7} = 9 ✓ (matches ground truth), B=1 ✓, D=1 ✓.
So the sheets (20) faithfully render THIS run's model; the takeoff's 16
stands on the PRIOR chain's count column. The disagreement is between
READS of the same printed cell, not between sheet and takeoff logic.
AND THE GATE THAT CATCHES EXACTLY THIS WAS BLIND: run 80c10620 has
stability=None — the determinism compare found no prior run because the
entire chain (a4cbce91 + 4 grading runs) was TTL-reaped. The C 5→9
mismatch would have flagged LOUD. The reaped chain cost a real
detection; the Phase 3 fixes exist so it never can again.

## 5. G2 / window-D null×null — evidence-or-null WORKING AS RULED,
locator false-negative
_seam_ledger.mark_size_quotes_nulled: removed 2 = [windows:D, doors:G2].
The model READ both sizes (its note prints G2 "9'-2\" x 8'-0\"";
D printed_size_not_located "2'-3 1/2\" x 3'-3 1/2\""), but OCR could not
locate those quote strings on the row's sheets (rotations checked) →
the quotes were killed, dims nulled. The sheet draws null×null and says
so. DISAGREEMENT REPORTED, NOT TUNED: Howard reads G2 as 9'-0"×8'-0";
the model's killed quote read 9'-2"×8'-0". G1 (16'-0"×8'-0") located and
carries 192×96 ✓.

## 6. LEFT ELEVATION — openings are MODEL attribution; area is a
RENDERER defect
- Openings: no schedule row carries elevation "left" (A,B front; C back;
  D right). Model attribution — Howard checking the real sheet.
- Area: renderer computes rectangle-only w×h = 39×20 = 780 ft² and
  SILENTLY excludes the gable triangle it prints directly above
  (½ × 39 × 11.375 ≈ 221.8 ft²). Renderer must include the triangle or
  disclose "rectangle only, gable excluded". Phase 2.

## Fix ownership summary
| # | Body | Mechanism | Owner |
|---|---|---|---|
| 1 | garage step flat | segments discarded at renderer | RENDERER (Phase 2) |
| 2 | front gable absent | plane-read, never wall-attributed; 4-vs-2 uncensused | MODEL + new census instrument |
| 3 | porch missing | renderer never reads porch | RENDERER (Phase 2) |
| 4 | 20 vs 16 windows | C count cell read 9 vs prior 5; stability gate blinded by reaped chain | READ DISAGREEMENT — re-read/verify C's printed COUNT cell |
| 5 | G2/D null×null | locator killed real quotes (as ruled) | honest; locator miss noted |
| 6 | left area 780 | gable triangle silently excluded | RENDERER (Phase 2) |
