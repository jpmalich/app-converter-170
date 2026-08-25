# SEND-126 REPORT — DART SEALED, PREDICTIONS SEALED FIRST, SCORED READ RUN
2026-08-24 · Quantities only. Predictions committed BEFORE the read at
`63aa1f3` (`memory/send126_dart_predictions.md`, unrevised — that file was
not edited after the read). Scored read: run `ff0d596e`, rerun of
`eb87852f` on the 11 cached pages. No estimate written (dart's estimate
`updated_at` still 2026-08-24T00:05, 59 lines untouched), no run
rewritten, no line priced.

## 0. HEADLINE
**SCORE: 0 / 4 faces derived — as predicted.**
**BUT THE MECHANISM WAS NOT THE PREDICTED ONE, AND TWO OF MY OWN
PRE-REGISTERED FALSIFIERS FIRED.** Reported below without softening.

## 1. THE FOUR FACES, SCORED (tolerance ±0.5 ft)

| face | truth W | read W | ΔW | truth H | read H | derived? |
|---|---|---|---|---|---|---|
| front | 55.50 | **58.0** | +2.50 | 19.17 | refused | NO |
| back  | 55.50 | refused | — | 19.17 | refused | NO |
| left  | 50.00 | **56.0** | +6.00 | 19.17 | refused | NO |
| right | 50.00 | **56.0** | +6.00 | 19.17 | refused | NO |

- **Heights: 4 of 4 REFUSED**, each named ("no {face} elevation drawing
  located — height not established — area not derivable"); seam ledger
  `height_build: front/rear/left/right REFUSED`. Prediction exact.
- **Widths: prediction WRONG on mechanism.** I predicted refusal on all
  four. Three widths came back as NUMBERS, every one outside tolerance:
  - front 58.0 from a located glyph `58'-4"` (p4, precision
    "approximate"),
  - left 56.0 AND right 56.0 from **one single located glyph** `56'-0"`
    (p4, the identical box x 8.59 / y 19.53 serves both faces).
- **This is the read failure named precisely: LOCATED BUT
  MIS-ASSIGNED.** The glyphs are really on the print. Evidence-or-null
  asks "does this figure exist in this run's own OCR?" — it cannot ask
  "does it belong to THIS line?". One glyph became two different faces'
  widths, and both are 6 ft over truth.
- The fabrication lane did work where the quote did not exist:
  `dims_nulled_quote_fabricated` removed 9 (incl. back width 58.0 and
  both 38'-0" segment widths); `dims_misread` removed 12 (the whole
  garage-wing set + corner heights 4–7); `lf_lanes_nulled_inputs_dead`
  removed starter_lf=228 and eaves_lf=116.

## 2. FALSIFIERS THAT FIRED (from my own pre-registered list)

**(1) "a gross ft² > 0 with no derived face" — FIRED.**
`siding_sqft = 1280.53` with **wall_body_derivable false on all four
faces**. Every square foot is gable:
- left gable 640.27 ft² and right gable 640.27 ft², each built as
  width 56.0 × rise 16.33 × the **0.70 field-factor convention**
  (`gable_basis: field_factor_0_70`, basis labelled), rise from the
  7/12 pitch (`_gable_pitch_provenance`: scaled 16.3 / computed 16.33).
- The width used is the mis-assigned 56.0 (truth 50.0), so the gable
  quantity is built on a figure that is 12% over on a face whose body
  the same run refuses.
- Truth says **left 3 gables, right 2, front 3, back 0**. The read
  treats each side as ONE 56-ft-wide gable and finds **none on the
  front**. So the placement is wrong as well as the size.
- Named, disclosed, not hidden — but it is a priced quantity, and it is
  a quantity the body lane refused to produce. **The gable lane is where
  mis-assignment turns into money**: it needs no height, so no height
  refusal stops it.

**(2) "a quantity riding an unverified footprint" — FIRED (starter).**
`starter_lf = 170.0` = `footprint_perimeter_ft` 170.0 (basis string:
"perimeter 170 LF — engine deducts entry-door widths per convention").
The sealed widths imply ~211 LF if the outline were a simple rectangle
(2 × (55.5 + 50)); the house has 3 levels so the true outline is not
that rectangle, and no claim is made here about the exact figure — the
point is that 170 LF was emitted while the model's own starter quote
(228) was nulled as evidence-free. `footprint_area_sqft` 3248.

**NOT fired (guards held):** no face height without a located DIM; no
sub-100 pct (100 on all four, and the front STONE callout — truth says
there is NO stone on this house — was routed to the material card with
`sqft_at_stake: null`, changing no quantity); window_count did NOT
become 18.

## 3. COUNTS (truth: 18 windows · 2 garage front · 1 entry front · 1 slider right)
- `window_count = 2` (marks J and K — the only two that located).
  **14 counts refused by name** (`counts_refused_no_evidence`: windows
  A,B,C,D,E,F,G,H,I,L,M,N,O + doors GARAGE), each "no count evidence —
  refused, never 1". 14 mark-size quotes nulled, 14 count cells nulled.
- `garage_door_count 0` · `entry_door_count 0` · `patio_door_count 0`.
  `marks_dropped_not_located`: doors FRONT ENTRY, PATIO SLIDER.
- Garage side: **REFUSED** with a CONFLICT verdict (doors say front,
  naming says back+front, no elevation labels) — the refusal rail did
  its job; truth is front, so the refusal was correct to withhold.
- Prediction on counts: correct (small wrong number, not 18; no door
  assigned to a face; nothing placed).

## 4. GABLES · LEVELS · HEIGHT HYPOTHESIS
- Gables truth 3/0/3/2 (front/back/left/right) vs read 0/0/1/1 →
  **not derived**; prediction "no gable count derived" holds in spirit,
  but the read did emit gable AREA (see falsifier 1).
- Levels truth **3**; read `stories = "2"`. Not derived, as predicted.
- Wall-height hypothesis 18.5 ft (`9'-2" + 9'-4"` plate quotes, both
  located as approximate) vs truth 19.17 ft → **0.67 ft low**.
  Hypothesis-only, never used for area (the four heights stayed
  refused). Recorded because it is the closest the read got to a real
  figure on this house.

## 5. THE FIVE DIM LANES (SEND-124)
`soffit_sqft` None · `level_frieze_lf` None · `sloped_frieze_lf` None ·
`drip_edge_lf` None · `total_trim_sqft` None — all five in
`_dim_unread`. Prediction exact; still zero, nothing previously
invisible appeared.

## 6. ROTATION NOTE (no claim)
Every page read **UPRIGHT** this run except p8 (33.3%, INDETERMINATE,
never normalized on a guess). The SEND-117 probe found rot270 on 10 of
11 pages — that probe ran on a DIFFERENT stored upload for this
estimate. Recorded as an observation about which raster was read, not as
a rotation finding.

## 7. SCOREBOARD AFTER THIS SEND
`foreign_drafter_scoreboard`: tanis 0/4 · **dart 0/4, sealed True**.
`earned_claim()` still computes **"fails safe on unfamiliar sets"** —
and SEND-126 shows that claim is itself only PARTLY true:
- it holds on the **height lane**, the **body-area lane**, the **count
  lane**, the **material-pct lane** and the **garage-side lane**;
- it does **not** hold on the **gable-area lane** or the
  **starter/perimeter lane**, where quantities were emitted on a
  mis-assigned width and an unverified outline.

## 8. WHAT NEEDS A RULING (nothing built this send)
1. **Gable-area gate**: should a gable quantity be refused when the same
   face's body is not derivable, or when the width it uses is not
   uniquely located to that face? (This is the 1280.53 ft².)
2. **One-glyph-two-faces**: should a width whose located box is shared
   with another face be refused as ambiguous? (This is the 56'-0".)
3. **Starter/perimeter**: should starter_lf be refused when the
   footprint outline is not verified face-by-face? (This is the 170 LF.)
These are read/attribution questions, which is where Howard said the
next phase points. Not built without authorization.

Standing rules held: no cross-drawing borrowing, no estimate influenced
another, no job names in operative code (registries are data), model
heights hypothesis-only, predictions unrevised. EST-886440 untouched.
Purity pin holds — dart's sealed figures and its distinctive drawn
glyphs joined `fixture_figures.py` in this same send, per the in-step
rule.

## 9. STAMP
RECORDED: 2026-08-25 02:01 UTC · a531df9 · CLEAN
RESULT: 2858 passed, 9 skipped, 7 warnings in 429.54s (0:07:09)
CENSUS: census pin GREEN — 0 PENDING_CONVERSION · INGRESS SMOKE: 4 passed
