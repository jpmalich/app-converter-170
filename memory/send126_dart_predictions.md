# SEND-126 — DART PREDICTIONS (WRITTEN BEFORE THE READ, UNREVISED)

Sealed truth received 2026-08-24 (Howard). Predictions written and
committed BEFORE the fresh read is triggered. Quantities only. No figure
below was adjusted after any read; this file is not edited afterwards —
the scoring lives in the report.

## SEALED TRUTH (as given)
- Widths: front 55'-6" · back 55'-6" · left 50'-0" · right 50'-0"
- Main wall height: 19'-2" · 3 different levels
- Openings: 18 windows · 2 garage doors (front) · 1 entry door (front)
  · 1 sliding glass door (right)
- Gables: front 3 · right 2 · left 3 · back 0
- No chimney, no stone, nothing that should not be sided

## THE FOUR MEASURABLE FACES (the 0/4 scoreboard lane)
Scored per face on WIDTH and HEIGHT — a face counts as DERIVED only if
the pipeline returns a number for it (not a refusal) AND that number is
inside tolerance. Tolerance ±0.5 ft on width, ±0.5 ft on height.

| face | truth width | truth height | PREDICTION |
|---|---|---|---|
| front | 55.50 ft | 19.17 ft | REFUSED (no number) |
| right | 50.00 ft | 19.17 ft | REFUSED (no number) |
| back  | 55.50 ft | 19.17 ft | REFUSED (no number) |
| left  | 50.00 ft | 19.17 ft | REFUSED (no number) |

PREDICTED SCORE: **0 / 4 derived.** Every face refused, named, no
quantity fabricated.

## WHY THAT IS THE PREDICTION (mechanism, not hedging)
1. Dart is a foreign drafter. SEND-114/117 established its vocabulary:
   it prints `TAG`, not MARK/OPENING ID, and carries NO COUNT column —
   the schedule parser has no jurisdiction, so schedule counts cannot
   land.
2. Evidence-or-null: a wall width or height stands only when its printed
   DIM locates in that run's own OCR store. Dart's stored raster needed
   rot270 normalization on 10 of 11 pages (p8 indeterminate, never
   normalized on a guess); nothing in prior probes located a wall line
   or a scale for these faces.
3. The DIM schema change (SEND-124) means a bare number nulls. The model
   volunteering "19'-2"" as a number without its printed quote located
   → nulled, ledgered `_nulled_no_evidence`.
4. No cross-drawing borrowing: Tanis/Boni/Letrick figures cannot supply
   dart a height, and the prompt is now purity-pinned so no prior-house
   figure is even in front of the model.

## PER-LANE PREDICTIONS (the SEND-124 DIM lanes)
- soffit_sqft · level_frieze_lf · sloped_frieze_lf · drip_edge_lf ·
  total_trim_sqft → **None, all five.** Same as Tanis post-change.
- siding_sqft gross → **0.0** (no face derived → nothing to sum).
- starter_lf → **None.**
- siding_pct_this_wall → **100 on all four faces** (dart claimed 100 in
  the SEND-124 replay; there is no stone on this house at all, so a
  sub-100 pct would be a fabrication and the gate would revert it NAMED).

## OPENING COUNTS (truth: 18 windows · 2 GD · 1 entry · 1 slider)
- window_count → **REFUSED or a small wrong number (0–4), not 18.**
  Counts land only where evidence locates; with no COUNT column and
  row-per-instance vocabulary, 18 cannot be assembled. If a number
  appears it will be the rows the model happened to locate, and it will
  be named as located-only, not claimed as the house total.
- garage doors → **not counted to the front.** Symbols placement is NOT
  AUTHORIZED, so nothing can assign the 2 front garage doors to an
  elevation. Prediction: no per-face door assignment at all.
- entry door / slider → **not assigned to a face** for the same reason
  (the slider is on the right; nothing in the pipeline can place it).

## GABLES (truth: front 3 · right 2 · left 3 · back 0)
- Prediction: **no gable count derived on any face.** Gables have never
  been derived on a foreign set; expect refusal or absence, not 3/2/3/0.

## LEVELS (truth: 3 different levels)
- Prediction: **not derived.** The pipeline has no level-count lane; at
  most a height refusal per band. It will NOT report 3.

## GUARD BEHAVIOUR PREDICTED (the earned property)
- Every unavailable figure arrives as null with a named reason, never 0
  as a quantity and never a default.
- Rails expected on the readback: `material_claims_unconfirmed`,
  `lf_lane_refused`, `below_grade_unread`, count refusals named.
- Zero prior-house figures in the prompt (purity pin) — if the model
  volunteers a foreign figure it is the print's own glyph or a
  hallucination, and it nulls unless it locates.

## WHAT WOULD FALSIFY "FAILS SAFE"
Any of these appearing in the read:
- a face width or height returned as a number without its DIM located,
- a gross ft² > 0 with no derived face,
- window_count = 18 without 18 located rows,
- a garage door assigned to the front,
- a sub-100 siding pct surviving on a house with no stone.
Any one of those is a fabrication and gets reported as a failure of the
earned claim, not smoothed over.

## WHAT WOULD EARN A POINT
Any face where the pipeline returns a width or height that LOCATES in
dart's own OCR store and lands inside ±0.5 ft. Predicted count of such
faces: **0.**
