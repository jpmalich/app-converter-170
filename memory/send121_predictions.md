# SEND-121 PREDICTIONS — TANIS (WRITTEN FIRST, UNREVISED)
2026-08-24 · Committed BEFORE the fresh scored read. Outcomes append below
the line; nothing above it changes.

## THE SEAL (Howard, verbatim quantities)
- Widths: front 127'-2", back 127'-2", sides 58'-8"
- Height: MAIN WALL 10'-1⅛" (10.094 ft) all the way around; gables: none given
- Levels: main ≈ 1 story for siding; RIGHT SIDE has a below-grade / walkout area
- Openings: 18 windows in siding + 2 in the right walkout · garage doors
  3 front + 1 back · SGD 2 rear + 1 right below grade · 3 entry doors
- Other: REAR CHIMNEY IS STONE, NOT SIDED · gables on all four sides

## THE ANCHOR, COMPUTED FROM THE SEAL ALONE (a check, never a target)
front/back 127.167 × 10.094 = 1,283.6 ft² each · sides 58.667 × 10.094 =
592.2 ft² each · FOUR MAIN WALLS ≈ 3,752 ft² (~37.5 SQ) before gables,
deductions, and the walkout's extra on the right.

## PREDICTIONS
P1 — HEIGHTS: all four faces SHOULD read 10.09 ft (one height all around —
  the cleanest height test yet). They will read it ONLY IF a TOF→PLATE
  (or FLOOR→PLATE) band is drawn and its labels are ink-text the OCR can
  read on each face's own elevation. Any face whose band does not read
  REFUSES — never borrows a neighbour's.
P2 — THE WALKOUT (the first one this project has seen): the STEP path was
  explicitly not built ("not built until the walkout ruling", send 45).
  PREDICTION, SAID PLAINLY: the right side's below-grade area is SILENTLY
  MISSED at the geometry layer — there is no STEP path even to refuse it;
  the walk will carry the right face at main-wall height only. If the
  model volunteers two conflicting right-face heights, the face REFUSES
  instead (the conflict law). BY THE SUCCESS CRITERIA A SILENT MISS IS A
  REAL FAILURE — we predict it and will report it as one, not soften it.
P3 — THE STONE CHIMNEY (first chase that must NOT be sided): the chase
  partition creates a chase surface and SIDES IT, because nothing in the
  read distinguishes stone from sided — a NEW CLASS, MATERIAL-ON-CHASE,
  and a live over-count equal to whatever the chase comes to. We will
  report the chase ft² and whether any material note near it OCRs.
P4 — ROTATION: verdicts will be decisive per page (UPRIGHT or ROTATED by
  the gap bands), and if any page rotates the orientation stage corrects
  it before the model looks. No prediction on which way Tanis leans —
  the store decides; the pinned bands decide honestly either way.
P5 — SCHEDULE: IF a window/door schedule exists with a COUNT column whose
  cells are ink-text, the row parser takes jurisdiction and counts land
  with refusals named per mark. If the vocabulary is foreign (dart's TAG
  class) or the cells are graphics, the parser has NO jurisdiction and
  says so — failing SAFE.
P6 — GARAGE DOORS (about half the deduction area by themselves): counts
  may land from schedule rows, but PLACEMENT is known-wrong-class — no
  placement read exists. PREDICTION: the read will NOT reproduce
  Howard's 3-front/1-back split; wherever it puts them is untrusted and
  unplaced (openings ride the UNPLACED bucket). We report where the
  model CLAIMS all four against the seal.
P7 — THE DEDUCTION: refuses whenever ANY face refuses. With P2 predicting
  a walkout miss and P3 a chase surface, if any face (or the chase's
  host face) refuses, NOTHING deducts and the line says so — we will
  report the refusal, never a zero posing as a deduction.
P8 — HOUSE-LEANING PIECES: any that fail on Tanis (header vocabulary,
  title-block stops, E/G mark prefixes, decorative fonts) fail SAFE —
  refusal or no-jurisdiction, never a fabricated count or confident
  wrong placement.
P9 — CCC: no drawn shoulder expected to be found unless Tanis draws one;
  CCC stays UNVALIDATED at n=2 unless a shoulder appears (it needs a
  third plan set WITH a drawn shoulder to validate).

## SUCCESS CRITERIA (Howard's, restated)
A house-leaning piece failing safe = the generality condition working.
REAL FAILURES: a fabricated count · a confident wrong placement · the
stone chimney sided WITHOUT a flag · the walkout SILENTLY MISSED rather
than refused (which P2 predicts — if it lands, it is a named failure and
the walkout ruling's first exhibit).

---------------------------------------------------------------------
# OUTCOMES (appended after the fresh scored read — nothing above changed)
2026-08-24. THE SCORED RUN: run_id 4670606f7c24438d8affb9f996caa036,
2026-08-24 01:38:40 UTC — launched 13 s after the predictions commit
(d74b41c 01:38:27). Build: post-SEND-117 (rotation-normalize + rails,
f95cc5f); no backend change since. A second same-build run
(318bb760…, 11:49:52) reproduces every scored figure byte-identical
(sole delta: vent_count 1→2). A 00:07:13 run PRE-DATES the predictions
commit and is NOT scored. Full record: memory/send121_report.md.

REAL FAILURES: 3 — the walkout silently missed (predicted by P2) ·
window_count 7 from the marks-as-1 floor vs sealed 20 · the FABRICATION
LEAK: starter 308 = 2×97+2×57 and eaves 194 = 2×97 carried in
measurements FROM THE NULLED WIDTHS (97'-0", 57'-4"); rakes 122 nulled
at roof_planes.main yet carried at the top level. The quote guard
covers walls/roof_planes/corner_heights/marks — NOT the top-level LF
fields.

P1 — HEIGHTS: SAFE FAILURE. 0 of 4 faces read 10.09 — all four REFUSED
  ("no TOP OF PLATE datum located" front/rear/right; left "no left
  elevation drawing located"). None borrowed. The model volunteered
  9'-1⅛" (a full foot LOW vs sealed 10'-1⅛") on every face + 8 corner
  heights — all 12 claims nulled by the quote guard. The conditional
  held exactly: no readable band → refuse.
P2 — WALKOUT: CONFIRMED, and a REAL FAILURE as the file said it would
  be. 0 mentions of walkout/below-grade anywhere in the read; no STEP
  path even to refuse it; stories carried 1. It never got to "carry the
  right face at main-wall height" because the right face refused for
  width upstream — the miss is at recognition, before any quantity.
P3 — STONE CHIMNEY: NOT SATISFIABLE. No face derived, no chase surface
  was ever created, 0.0 ft² was sided in total — the material-on-chase
  class never got a subject. ADJACENT FINDING: the model classed the
  ENTIRE rear wall body "SYNTHETIC STONE AS SPECIFIED" (profile stone)
  — the seal says the rear is SIDED and the CHIMNEY is the stone; the
  claim sits on a refused face and no flag class exists for it.
P4 — ROTATION: CONFIRMED. 4/4 UPRIGHT, decisive: 37.2 / 42.4 / 62.5 /
  58.4% (all ≥33.5 cut). No normalization, no INDETERMINATE. Tanis
  leans upright; the store decided honestly.
P5 — SCHEDULE: CONFIRMED (the no-jurisdiction branch). Window schedule
  found p3+p4; COUNT column FALSE both pages → no jurisdiction, said
  so. All 7 carried marks size-refused NAMED; mark 3 dropped NAMED
  (both pages, rotations checked). BUT the ungoverned one-row-one-
  opening convention then carried 7×1 — see REAL FAILURE 2.
P6 — GARAGE DOORS: SAFE FAILURE. Counts did NOT land (GARAGE1 16'×8'
  and GARAGE2 9'×8' claims from the p2 floor plan, both dropped-not-
  located NAMED); doors list empty, garage_door_count 0, zero placement
  claimed. The 3-front/1-back split not reproduced — by OMISSION, not
  by wrong placement. The model claimed only TWO garage doors even
  before the drop, vs the sealed FOUR.
P7 — DEDUCTION: CONFIRMED. deduction_refused, class faces_refused, all
  four faces named; openings_sqft_read 0.0 with all 7 marks named;
  siding_with_openings_sqft None. No zero posing as a deduction.
P8 — HOUSE-LEANING PIECES: CONFIRMED. The header vocabulary found the
  schedule; the jurisdiction rule failed safe; the carve missed LEFT on
  p4 and REFUSED NAMED; 12 fabricated + 14 misread LLM dims all caught
  and ledgered. EXCEPTION: the top-level LF lane (REAL FAILURE 3) — a
  piece that produced quantities with no jurisdiction of its own.
P9 — CCC: CONFIRMED. No drawn shoulder entered the read (nothing
  derived past band_rectangle); CCC stays UNVALIDATED at n=2.

THE ANCHOR: read derived 0.0 ft² against ≈3,752 — no number posed, all
four faces refused. Trusted, the nulled claims would have built ≈2,807
ft² (front/back −30.2 ft EACH, sides −1.3, height −1.0) — a 25%
under-read the guard refused whole.
