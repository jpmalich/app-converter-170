# RULING FF — GARAGE ANCHOR DESIGN REPORT (report only, NOT built)
Howard sealed 2026-08-14 send-25. This is a DESIGN, not a build. Nothing in
the derivation is wired to it. It answers the corrected question and states
what it would do on the one house with confirmed ground truth (EST-713272
run 6) before anyone authorizes the build.

The defect it targets: face attribution cross-wires — a LEFT dimension is
read onto RIGHT (and vice-versa), so the wrong depth prices the wrong side.
DD (Ruling EE) now REFUSES a face that cannot be closed; the anchor is what
would let a refused face DERIVE again by binding a depth to the correct side
with evidence instead of a coin-flip.

--------------------------------------------------------------------------
## 1. SPLIT THE QUESTION IN TWO (Howard's instruction)
They have different evidence and different failure modes and MUST be able to
fail independently:

  Q1  WHICH DEPTH belongs to the garage block?   (a dimension)
  Q2  WHICH SIDE ELEVATION shows the garage's outboard wall?  (a face)

- Answering Q2 without Q1 gives a side with no dimension.
- Answering Q1 without Q2 gives a dimension with no face.
Both are required; the anchor returns a RESULT only when BOTH resolve and
AGREE. Either one UNVERIFIED ⇒ the whole anchor is UNVERIFIED (no default).

--------------------------------------------------------------------------
## 2. CANDIDATE SIGNALS — assessed, with the choice named

### A. PLAN-SIDE — garage label bbox along the footprint's WIDTH axis
Read the garage LABEL's box (now persisted by Ruling GG) and ask: does it sit
in the left half or the right half of the footprint's WIDTH extent?
- Requires: (i) locating the footprint extent on the floor-plan sheet, and
  (ii) knowing which drawn axis is WIDTH and which is DEPTH.
- STRENGTH: independent of the elevation sheets; uses the label we already
  have a box for.
- WEAKNESS: needs the footprint extent, which the OCR substrate does not give
  directly — it gives text boxes, not the building outline. Usable as a
  SECONDARY/corroborating signal, not the primary.
- USE: yes, as the plan-side half of a CONFLICT check against B — never alone.

### B. ELEVATION-SIDE — the side-elevation title block  ← PRIMARY
The side-elevation sheet whose TITLE BLOCK reads "LEFT ELEVATION" or "RIGHT
ELEVATION" and which DEPICTS GARAGE FEATURES.
- Why it beats the label path: the title block is PRINTED TEXT, not a model
  inference. The crossed dimension came from inferring a face; a printed
  "RIGHT ELEVATION" string is read, not inferred. This is the whole reason it
  is the primary.
- "Depicts garage features" must be GROUNDED, never eyeballed. Acceptable
  grounding, in priority order:
    1. a printed "GARAGE" annotation whose box sits on that sheet (GG box),
    2. a garage door on that elevation (door row with elevation == that face),
    3. a distinct LOWER wall height on that sheet (garage wing sides lower
       than the 2-story body) — corroborating only, never sole grounding.
- USE: PRIMARY for Q2. The face is whatever the title block says, gated on at
  least one grounded garage feature on that same sheet.

### C. DEPTH BINDING — depth string nearest the garage block's outboard edge
For Q1: among the persisted plan-sheet strings, the depth dimension nearest
the garage block's OUTBOARD edge. This is exactly what the per-string boxes
(Ruling GG) were persisted for.
- Requires the outboard edge location, which follows from Q2 (the outboard
  side is the side named by the title block) + the footprint extent.
- USE: PRIMARY for Q1, but ONLY after Q2 has named the outboard side.

### ORIENTATION — DERIVE IT, DO NOT ASSUME IT
Front-at-the-bottom is a CONVENTION, not a guarantee; a wrong orientation
assumption fails silently and looks exactly like a correct one. The anchor
does NOT need FRONT-vs-BACK — it needs WIDTH-axis vs DEPTH-axis, which is a
smaller and more reliable problem:
- The WIDTH axis is the one the FRONT/BACK overall widths run along
  (front width == back width, a DD closure input). The DEPTH axis is
  perpendicular. Establish the axis from the printed overall-dimension
  strings and their boxes (which pair of parallel strings are the equal
  front/back widths). If the axis cannot be established from the sheet, the
  result is UNVERIFIED — never a default orientation.

--------------------------------------------------------------------------
## 3. REQUIRED UNVERIFIED PATHS (Ruling FF: "an anchor that always answers
is a coin flip with better manners"). Each returns UNVERIFIED with a NAMED
reason — never a guess:

  U1  no garage label found                 → Q2 unverified: "no garage label"
  U2  label found but no depth string binds  → Q1 unverified: "no depth bound
                                               to the garage block"
  U3  plan orientation cannot be derived     → both unverified: "width/depth
                                               axis not established"
  U4  GARAGE HAS HOUSE ON BOTH SIDES         → NO OUTBOARD WALL EXISTS. This
      is Howard's "almost always" exception. The design must DETECT it, not
      answer anyway: when the garage block's left AND right neighbours are
      both interior (house continues on both sides on the plan / no outboard
      elevation names the garage), return NO_OUTBOARD_WALL, distinct from
      UNVERIFIED. A side-entry garage (Boni) has exactly one outboard side;
      a front-entry garage tucked between wings has none.

--------------------------------------------------------------------------
## 4. CONFLICT HANDLING (Ruling CC applies unchanged)
Signals A and B disagreeing ⇒ CONFLICT: both sides REFUSE. No majority, no
winner, no "prefer the stronger signal." Name which signal said what
(e.g. "plan label → left half; title block → RIGHT ELEVATION"). The garage
side stays refused until the conflict is resolved by evidence, exactly as
garage_side_verdict already does for the CC signals today.

--------------------------------------------------------------------------
## 5. WHERE CLOSURE SITS IN THE SEQUENCE
The anchor ASSIGNS; footprint_closure (DD) CHECKS; where they disagree the
face REFUSES. Sequence:

  read → GG OCR substrate persisted
       → anchor: Q2 (title block) then Q1 (depth binding) → (face, depth)
       → write that depth onto the assigned side's wall record
       → footprint_closure runs on the assembled walls (unchanged)
       → if closure fails for that side, EE refuses it (as it does now)

So the anchor never overrides DD. A wrong assignment that breaks closure is
caught by the check that is already wired, and the face goes NOT DERIVABLE
with the failing relation named — the anchor cannot smuggle a bad depth past
DD.

--------------------------------------------------------------------------
## 6. WHAT THE ANCHOR WOULD PRODUCE ON EST-713272 RUN 6 — signal by signal
Confirmed ground truth (Howard): RIGHT side-entry garage; RIGHT = 33'-0",
LEFT = 30'-2". A design that cannot say what it would do on the one house
with ground truth is not ready to build.

  Q2 (face):
   - Signal B (title block): if run 6's side-elevation sheets carry printed
     "RIGHT ELEVATION" + a grounded garage feature (garage door / GARAGE
     annotation / lower wall height on that sheet) → Q2 = RIGHT.
   - Signal A (plan label half): garage label in the RIGHT half of the width
     axis → RIGHT. Corroborates B → no conflict → Q2 = RIGHT (VERIFIED-side).
   - IF run 6's OCR did NOT capture a "RIGHT/LEFT ELEVATION" title box (the
     read that produced the crossed dimension may not have persisted the
     title strings — GG did not exist then) → Q2 = UNVERIFIED "no title box".
     HONEST STATE: on the frozen run 6 the anchor MOST LIKELY returns
     UNVERIFIED for Q2, because run 6 predates GG and the title/label boxes
     it needs were discarded. It would resolve to RIGHT only on a FRESH read
     that persists the substrate.

  Q1 (depth):
   - With Q2 = RIGHT, the depth string nearest the RIGHT outboard edge is the
     30'-2" + garage-return that sums to the RIGHT depth. Whether the anchor
     reaches RIGHT = 33'-0" depends on which depth strings run 6 persisted;
     pre-GG it did not, so Q1 = UNVERIFIED "no depth bound" on the frozen run.

  CLOSURE cross-check:
   - Today (post-EE, pre-anchor) the frozen run: RIGHT has segment depth
     30+9=39 with LEFT unread → DD refuses RIGHT ("footprint does not close:
     right depth 39 present but opposing left depth not read"). The anchor,
     once built and fed a FRESH read, would bind LEFT = 30'-2" and RIGHT =
     33'-0" so both depths are present and close within tolerance — turning
     the refusal into a DERIVED pair. On the FROZEN run it cannot, and it
     correctly says so (UNVERIFIED), rather than manufacturing the answer.

CONCLUSION for the build decision: the anchor's PRIMARY signal (title-block
face) and its depth binding BOTH depend on the GG substrate that only exists
from send-25 forward. On a fresh EST-713272 read it would return RIGHT /
33'-0" and LEFT / 30'-2" and close; on the frozen run 6 it honestly returns
UNVERIFIED. That is the correct behaviour — it does not pretend to know what
its inputs never captured.

--------------------------------------------------------------------------
## 7. BUILD DEPENDENCIES (for Howard's go/no-go)
- GG substrate persisted (DONE this send) — required by A, B, C.
- Title-block string capture: GG persists page OCR only for pages that carry
  model quotes today. Binding B reliably needs the side-elevation TITLE boxes
  even on pages with no dimension quote → a small extension to OCR the
  elevation/floor-plan sheets for title + GARAGE strings would be part of the
  FF build (named here, NOT built).
- Axis derivation from the front/back overall-width string pair.
Face disambiguation proper (the wiring that writes the anchored depth onto
the wall record) stays BLOCKED pending Howard's approval of this report.

--------------------------------------------------------------------------
# SEND-27 OUTCOMES — appended below the prediction (prediction UNREVISED)
Observed on the fresh EST-713272 read, run c54633996e7a49e48432cf66a61efaf7
(READ-ONLY ledger + OCR probe; confirmed live through the diagnostics
endpoint, HTTP 200).

FF INPUTS — the send-25 prediction said the anchor's inputs only exist from
GG forward and would be UNVERIFIED on the frozen pre-GG run 6. This is a
FRESH read WITH GG, and the inputs are now OBSERVED PRESENT:
  - garage label: PRESENT — "3 CAR GARAGE" on page 6 at x≈66% (RIGHT half of
    the width axis), plus stray "GARAGE" tokens. (Signal A plan-side → RIGHT.)
  - LEFT/RIGHT elevation title blocks: PRESENT — "LEFTELEVATION" and
    "RIGHTELEVATION" on page 2 (OCR concatenates the words). (Signal B, the
    primary, is available and is printed text as predicted.)
  - depth string nearest the garage block: PRESENT — feet-inch strings
    "33-11", "33-5" on page 6 near the garage label; "9'-5" on page 9.
    (Signal C substrate exists.)
  GG persistence: 871 runs across pages 1,2,6,7,9,11; stored on the run doc;
  no truncation; no int-key coercions.

CONSEQUENCE FOR THE BLOCK: the FF inputs are now CONFIRMED PRESENT in the
persisted OCR (the condition Howard set for lifting the anchor-build block).
The build is NOT started in this send — SEND-27 is accuracy only and the
mandate scoped the anchor as still blocked pending this confirmation. This
entry records the confirmation; it does not authorize the build.

WHAT THE PREDICTION GOT RIGHT / WRONG:
  - RIGHT: prediction said a fresh read would reach RIGHT via title block +
    plan-half, and it is borne out — garage label sits in the RIGHT half and
    a "RIGHTELEVATION" title exists. NOT YET TESTED end-to-end (anchor unbuilt).
  - The prediction's "frozen run 6 → UNVERIFIED" is not contradicted: this is
    a different, fresh run that DID persist the substrate.

EE ON THIS RUN (the SEND-27 finding): RIGHT refused via footprint_closure
("footprint does not close: right depth 39 present but opposing left depth
not read — right cannot be closed"); LEFT is a genuine width-not-read (no
width at all — NOT an EE refusal); BACK segment height not read. EE fired
correctly in the backend; the rendered surface was the defect (fixed).

================================================================
SEND-29 OUTCOMES (2026-08-16, appended — prediction file unrevised)
Run probed: run_id c54633996e7a49e48432cf66a61efaf7 (latest done,
est 65bcb89d), 11 pages, persisted OCR pages {1,2,6,7,9,11}.

CHECK-FIRST — UPRIGHT-ONLY FILTER: CONFIRMED, three layers deep
(routes/ai_blueprint.py):
  L1 PAGE FILTER (~line 1802-1813): OCR runs ONLY on pages carrying
     an inexact model quote ("wanted"). Pages 3,4,5,8,10 never read.
     Page 4 is the FOUNDATION PLAN — never OCR'd at all.
  L2 PERSISTENCE FILTER (line 1852-1863): _ocr_text_by_page keeps
     ONLY the upright pass runs. Rotated (norm,raw,bbox) discarded
     after locate use — never persisted.
  L3 TRIGGER FILTER (line 1951-1953): rotated passes run only when
     the upright pass left quote-misses on that page. This run:
     pages 1 and 2 only.
CONSEQUENCE: every rotated (depth) dimension is systematically
absent from the persisted OCR unless the upright engine happens to
read the vertical glyph stack (it did for 14'-2", 3'-10", title
block; it did NOT for 33'-0" or 30'-2").

ITEM 1 — AXIS CLASS (p6, ratio w/h; ≥1.5 H, ≤0.667 V, else IND):
  21 dimension-like runs → 7 HORIZONTAL, 4 VERTICAL, 10 INDETERMINATE.
  Key strings: 33-11½ (45.87,20.01,1.92x0.93) HORIZONTAL;
  33-5½ (45.77,68.68,1.71x1.0) HORIZONTAL; 58-0 top (55.54,18.15,
  1.31x0.93) INDETERMINATE(1.41); 58-0 bottom (55.49,70.15,1.46x1.2)
  INDETERMINATE(1.22). VERTICAL survivors: 3'-10 (54.28), 3'-1
  (45.82), 3'-0 (59.53), 14'-2 (61.54).
  AXIS FILTER ALONE KILLS BOTH WRONG ANCHOR CANDIDATES (both class
  HORIZONTAL). Short strings at this DPI ride near ratio 1 —
  INDETERMINATE is real and populated.

ITEM 2 — INTERIOR/EXTERIOR: NO footprint outline is established
anywhere in the pipeline today. footprint_checks.py (DD/EE) is
arithmetic-only — no geometry, no outline, no inside/outside test
exists. When it cannot be established the answer must be
INDETERMINATE, never default-to-exterior. (33-11½ sits at y=20.01
between the two 58-0 rails at y=18.15 and y=70.15 — an outline
test would class it INTERIOR; no such test runs.)

ITEM 3 — POSITIONAL RULE APPLIED ON p6: garage label '3 CAR GARAGE'
at (66.18,44.02) → right half. Outermost VERTICAL dim on that side
in the persisted store: 14'-2" at x=61.54 — THE WRONG ANSWER.
Nearly returned: 3'-0" at x=59.53. It cannot return 33'-0" because
33'-0" WAS NEVER CAPTURED (L2/L3 filters). The rule is sound; the
substrate is missing its target.

ITEM 4 — 30'-2": ABSENT from the persisted OCR on every persisted
page; no one-edit misread neighbour exists either. Worse: the
FOUNDATION PLAN (p4) — one of the two sheets that records it — was
NEVER OCR'd (L1 page filter). The anchor cannot bind what was never
captured. Root causes ranked: L1 (foundation plan unread) + L2/L3
(rotated runs never persisted) ahead of resolution.

ANCHOR: STAYS BLOCKED. No build performed in SEND-29.
