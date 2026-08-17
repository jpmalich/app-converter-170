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

================================================================
SEND-30 OUTCOMES (2026-08-16, appended — prediction file unrevised)
BUILT (items 1-4, sealed order): rotated passes on EVERY page with all
runs persisted (src + axis tags, boxes mapped to upright); page filter
dead (OCR reads every page, incl. title sheets); glyph-normalized axis
classifier (verified separation FIRST: verticals 0.058-0.087,
horizontals 0.212-0.396, zero overlap on the full p6 set — cuts pinned
inside the gap at 0.12/0.18); 2D rail envelope (interior = inside on
BOTH axes; INDETERMINATE when rails missing/crossing, never a default).
Suite GREEN 2497 passed. Old upright-only store ARCHIVED on the run doc
(_send30_backfill), new store backfilled from the retained rasters.

RE-PROBE RESULTS (run c5463399, REPORT ONLY — ANCHOR NOT BOUND):
  30'-2" — FOUND. Foundation Plan p4, rotated passes only, VERTICAL,
    x=20.33 (left side). It was never absent from the page; it was
    never read. ALSO: raw came back as bare "30-2" (foot AND inch
    marks lost), which the dimension-like filter refuses (bare
    digits-hyphen-digits would swallow dates) — so the positional rule
    on p4-LEFT returned 5'10° instead. NAMED GAP, not tuned away.
  33'-0" — FOUND on p4 (x=78.98), p6 (x=81.9), p7 (x=82.1); VERTICAL,
    rotated passes only, exactly where Howard read it.
  POSITIONAL RULE p6: RIGHT → 33'-0" (x=81.91). Contention: only the
    duplicate reads of the same string from the two rotated passes
    (rot90/rot270 both hit it) — wins by default after dedup, which
    per Howard proves less than it appears. LEFT → "30-0*" (x=28.95);
    whether that is a real 30'-0" or a misread of 30'-2" cannot be
    resolved from OCR alone — OPEN.
  POSITIONAL RULE p4: RIGHT → 33'-0" (x=78.98). LEFT → 5'10° (wrong;
    the true 30'-2" excluded by the bare-form filter gap above).
  AXIS CENSUS p6 (all passes, dim-like): 57 H / 32 V / 1 INDETERMINATE
    (nr=0.130, in the gap band) — rare, not impossible, as ruled.
  ENVELOPE POLLUTION (named): the bottom rail on p4 AND p6 resolved to
    the SCALE note (SCALE:3/16"=1'-0", y=80) below the true bottom
    58'-0" rail (y=70) — y_hi inflated ~10pct. Did not change any
    probe outcome here; needs a ruling (exclude scale-notes vs live
    with it), NOT a silent filter.
  RUN COUNTS/page (total: upright/rot90/rot270): p1 387:147/107/133,
    p2 380:147/100/133, p3 749:290/213/246, p4 323:137/90/96,
    p5 159:69/42/48, p6 465:243/101/121, p7 331:166/81/84,
    p8 339:115/114/110, p9 225:84/67/74, p10 139:69/34/36,
    p11 201:84/56/61. Previously-unread pages 3,4,5,8,10 now covered.
  VARIANCE (item 3): cannot be measured from one run; noted as a
    pending observation for the next fresh reads. NOT claimed.
ANCHOR: STAYS BLOCKED until Howard reads this re-probe.
Full machine report: /app/memory/send30_reprobe_report.json

================================================================
SEND-31 OUTCOMES (2026-08-16, appended — prediction file unrevised)
BUILT: Ruling HH (bare form gated on position: axis V/H + EXTERIOR by
2D envelope + chain-aligned within one box-width + inches <= 11;
no envelope -> nothing admitted) and Ruling II (rail candidate carries
NO alphabetic characters). 12 new pinned tests; suite GREEN 2509.

HH ADMISSIONS across all 11 pages: 4 total — NO FLOOD.
  p4: "30-2" x2 (rot90/rot270 reads of the same string) — THE target;
      chain mate 5'10°.
  p7: "2-8" x2 (upright, HORIZONTAL, chain mates 3'9° / 34-0°) — a
      genuinely mark-stripped small dim on the second floor plan.

II RAIL REPORT (all 11 pages, marked-only):
  p4 bottom rail RECOVERED: 58-0° at y=75 (was SCALE at y=81.65).
  p6 bottom rail: SCALE gone, but "2-11%° × 3-119°" (a size-pair note
    using the '×' GLYPH — not alphabetic) slipped candidacy at y=73.3
    vs the true 58-0° at y=70.2. NAMED RESIDUAL, ~2pct y_hi inflation,
    changed no outcome. Not patched — extending II is a ruling (the
    structural property that excludes it without a catalog would be
    "a rail candidate carries exactly ONE dimension token").
  p7 ESTABLISHED (58'-0° / 24'-0* / 30'-0° / 33'0*), p8, p9 (joist
    plans) ESTABLISHED; p1 ESTABLISHED but it is an ELEVATION — its
    "envelope" is not a footprint and the anchor must not treat it as
    one; p2, p3, p5, p10, p11 INDETERMINATE with named reasons
    (never a default).

PROBE AFTER REPAIRS (report only, anchor NOT bound):
  p4: LEFT -> 30-2 (admitted; 5'10° visible in contention),
      RIGHT -> 33-0*.
  p6: LEFT -> 30-0* (Howard confirms p6 genuinely prints 30'-0";
      the 3'-0" garage step-back is real and printed),
      RIGHT -> 33'-0'.

LEFT-DEPTH CROSS-SHEET (ITEM 3, as ruled): p4 Foundation reads 30'-2",
p6 First Floor reads 30'-0". THE SHEETS DISAGREE BY 2" ON ONE WALL.
REPORTED — not averaged, no sheet preferred, not resolved from OCR.

STANDING: anchor stays BLOCKED; when lifted, first pass is a
REPORT-ONLY DRY RUN and any working-anchor handback says UNVALIDATED
until a second plan set runs. Variance observation pending fresh reads.
Full machine report: /app/memory/send31_reprobe_report.json

================================================================
SEND-32 OUTCOMES (2026-08-16, appended — prediction file unrevised)
BUILT: Ruling JJ (a rail candidate carries EXACTLY ONE dimension
token) and Ruling KK (reference-plane verdict with the contradiction
distinguisher). 10 new pinned tests; suite GREEN 2519.

JJ RE-REPORT: exactly ONE change across 11 pages — p6 bottom rail
recovered to the true 58-0° (y_hi 73.34 -> 70.15; the '×' size pair is
out). NO page moved ESTABLISHED -> INDETERMINATE.

KK DISTINGUISHER (as built and pinned): readings group BY PLANE.
Same-plane disagreement -> CONTRADICTION (still reported as one).
Cross-plane difference -> REFERENCE_PLANES (both correct; the material
names which governs — siding wraps framing). Plane unknown ->
INDETERMINATE ("cannot be told apart"), governing plane unread ->
INDETERMINATE ("the other plane never substitutes"), unruled material
-> INDETERMINATE ("no default"). NO magnitude threshold anywhere.
Left depth verdict: REFERENCE_PLANES — framing 30'-0" (p6) GOVERNS
siding; foundation 30'-2" (p4) visible alongside. UNVALIDATED.

ITEM 3 — WHAT SEPARATES p1 STRUCTURALLY (from the persisted data):
  1. GARAGE ROOM LABEL INSIDE THE ESTABLISHED ENVELOPE: p6 has exactly
     two ('3 CAR GARAGE' x2, both RIGHT half); p1 has ZERO (its 13
     garage-word runs are notes/title-block, all OUTSIDE its rail
     box). ON THIS SET, POSITION ALONE SEPARATES — every garage note
     on p6 (door schedule, blocking note, title block) sits outside
     the envelope; only the room label sits inside. (A glyph-length
     guard I probed with never fired — dropped from consideration,
     not proposed.)
  2. Also observed, reported not prescribed: V/H dim ratio — p1/p2
     elevations 3.3-3.5, plan sheets 0.56-1.25.
  The precondition also excludes p4, p7, p8, p9 (no room label inside
  their envelopes) — the anchor's answer would come from p6 alone,
  with p4/p7 as corroboration via their own probes.

ANCHOR DRY RUN (report only, NO BIND — UNVALIDATED ON EVERY LINE):
  p1 elevation: LEFT 29'-1, RIGHT 13-0* — an elevation's rail box is
    NOT a footprint; the room-label precondition excludes it. UNVALIDATED.
  p4 foundation: LEFT 30-2 (margin 0.08 over 5'10°), RIGHT 33-0*
    (sole candidate). UNVALIDATED.
  p6 first floor: LEFT 30-0*, RIGHT 33'-0' (each sole distinct;
    garage room label RIGHT). UNVALIDATED.
  p7 second floor: LEFT 30'-0°, RIGHT 33'0* (sole candidates). UNVALIDATED.
  p8/p9 joist plans: BOTH faces return 30'-0" variants — RIGHT would
    CROSS-WIRE 30'-0" onto the garage side (the original disease).
    The room-label precondition excludes both sheets structurally. UNVALIDATED.
  p2,p3,p5,p10,p11: INDETERMINATE, named reasons.
  THE PHOTO FINISH (Howard's item): unique to p4 LEFT — 30-2 beats
  its own chain mate 5'10° by 0.08pct of page width. HAD IT GONE THE
  OTHER WAY the left depth would read 5'10" — wrong by ~24 feet, and
  nothing in the rule would have flagged it. Every other plan-sheet
  face wins as SOLE candidate (proves least). The rule as stated has
  no notion of a chain's TOTAL vs its SEGMENTS — 5'10° is a segment
  on the same chain as 30-2. NAMED, not patched: segment-vs-total
  needs a ruling before any bind.
STANDING: NO BIND into derivation. UNVALIDATED until a second plan
set runs. Full machine report: /app/memory/send32_dryrun_report.json

================================================================
SEND-34 OUTCOMES (2026-08-16, appended — prediction file unrevised)
SECOND PLAN SET DRY RUN — Letrick (run 725f8326, 10 pages). REPORT
ONLY, NO BIND, NO GROUND TRUTH CLAIMED, NOTHING TUNED AGAINST THE SET.
Estimate number on record is EST-655664 (send said EST-653665);
customer name matches exactly ("letrick 8-16-26 4 pm").

POSITION: UNVALIDATED AND UNAVAILABLE ON THIS SET.
No page met the room-label precondition. Letrick HAS a garage (notes:
"ON BACK SIDE OF GARAGE" p5, "ADD BLOCKING FOR GARAGE DOOR TRACKS"
p7) but NO GARAGE ROOM LABEL was captured anywhere, any pass. The
send-32 availability question now reads: precondition available on
1 of 2 houses.

RAILS: ESTABLISHED p1,p5,p6,p7,p8,p10; INDETERMINATE p2,p3,p4,p9
(all "fewer than two horizontal dimension rails"). p1 is an elevation
and answers anyway (9-1%* both sides — height dims); the precondition
correctly excludes it, consistent with Boni.

PER-SIDE RETURNS ON PLAN SHEETS (substrate report; the ANCHOR itself
returns NOTHING — no garage side):
  p5 foundation: LEFT 30'-0* (rot270, margin 0.02 over '0-00'),
                 RIGHT 30'-0* (rot270, margin 0.02 over '0-00')
  p7 first floor: LEFT 30'-0" (rot90, margin 0.09 over '0-00'),
                  RIGHT 30'-0" (rot270, margin 0.10 over '0-00')
  p8 joist plan: LEFT returned '0-00' — A WRONG STRING, reported
                 exactly as returned (beat 30'-0" by 0.10);
                 RIGHT 30'-0" (sole distinct)
  p6 foundation-mech: LEFT 12'-6, RIGHT 13'-7* (small local dims —
                 its "envelope" is not a footprint)
  p10 roof plan: LEFT 1'-0, RIGHT 1'-0" (overhang dims — same)

TWO RULES EXPOSED — NAMED AND STOPPED, NOT PATCHED:
  1. HH ADMITS ZERO-FEET FRAGMENTS. '0-00' (feet=0, in=0) passed
     every gate 6 times across p5/p7/p8 — chain mate was 30'-0*, ITS
     OWN TRUE READING: three passes on the same pixels produced
     "30'-0*" (rot270), "0-00" (upright), "0-.00" (rot90) at the
     same location. Candidate rulings for Howard (not built):
     (a) feet=0 dimensions nothing — notation-derived like the
     11-inch bound; (b) a bare form whose box overlaps a fully-marked
     run is the SAME physical string, not a separate dimension —
     positions disambiguate, again.
  2. NO SAME-LOCATION DEDUP ACROSS PASSES. The p8 LEFT flip is the
     send-30 "wins by default after dedup" caveat turned active: a
     degraded pass-read of the same string OUTRAN the true read.
HH admissions listed individually: p1 '19-11' (rot270, mate 19'-11);
p5 '0-00' x3; p7 '0-00' x2; p8 '0-00' x1.
RULING LL: NOT BUILT — owed; no sum-closure report available.
Howard compares his sealed depths; no match or mismatch is claimed.
Full machine report: /app/memory/send34_letrick_dryrun_report.json

================================================================
SEND-36 OUTCOMES (2026-08-16, appended — prediction file unrevised)
BUILT: Ruling MM (position merge is the FIRST operation — parameter-
free same-location test, most-complete reading survives, conflicting
complete readings marked and barred from dimension paths, chain mates
established after merge), Ruling NN (zero total length refused; 0-6
stays real), Ruling LL instrument (aligned-chain sum closure on merged
strings, exact, residuals reported). 12 new pinned tests; suite GREEN
2529. NO BIND anywhere.

ITEM 1 — THIRD CONFIRMATION: Letrick p5 rails read 54'-0" TOP and
54'-0" BOTTOM — the rail path, independent of the depth path, matches
Howard's sealed 54'-0". p7 top rail 54'-0*. NAMED RESIDUAL (JJ's
family, third appearance): p7 bottom rail resolved to a size-pair
note ("2'-11%2\"× 4'-11/\"") because OCR rendered its second foot
mark as PRIME (U+2032), outside the recognized foot-mark glyph set,
so it counted as ONE token. Fix would be glyph normalization (add
prime marks to the foot-mark class so JJ counts two tokens) — a
transcription-noise item, not a rule change; awaiting the ruling.

OWED x-POSITIONS: p5 LEFT x=19.41 vs RIGHT x=90.17; p7 LEFT x=25.48
vs RIGHT x=89.82 — four DISTINCT physical strings; no winner was the
same string selected twice.

OWED GARAGE CHECK: EST-655664 material list and run lines contain NO
garage-derived items. Note-text consumers in code: (1) the garage-
side door signal reads model type_hint text (already ruled
unreliable, CC); (2) a provenance validator for printed notes
(validates, never quantifies); all quantity consumers key on the
structured garage_door_count field, not note text.

MM CENSUS: readings -> strings roughly 2.2-3.1x reduction everywhere
(Boni p6 465->272; Letrick p7 914->408). Conflicted strings: 0-3 per
page, all barred from dimension paths.
AXIS CUTS RE-VERIFIED ON MERGED DATA (as ordered): Boni p6 merged =
72 dim strings, verticals 0.0407-0.1143, horizontals 0.212-0.4328,
ZERO indeterminate. GAP HOLDS but is THINNER than triplicated data
suggested: vertical max 0.1143 sits 0.006 under the 0.12 cut. Stated,
not moved.

LL CLOSURE REPORT (exact, merged): ~100 aligned chains across both
houses' plan pages — 1 CLOSES, rest FAIL. The failures are dominated
by (a) chain totals printing on OUTER RAILS, not on the segment line,
and (b) OCR fraction loss (residuals of ±1in on 1'-11½ vs 2'-0
pairs). RESULT, NOT FAILURE: LL as "aligned line clusters must sum"
does not match how chains print. The closure that matches the sheets
is DD's (segments vs the side total across the footprint), which
exists. LL-as-built stays a reporting instrument; NAMED for a ruling
on its definition before it gates anything.

BONI p8/p9 PROBE (precondition set aside, as owed): p8 L 30'-0*
(x=14.06) / R 30'-0" (x=58.17); p9 L 30'-0° / R 30'-0*. Rails on p8:
33'-11% top AND bottom — the INTERIOR width as both rails. Joist
sheets dimension interior spans; their confident wrong answers are
exactly what the room-label precondition excludes.

ITEM 2 — CHIMNEY: 2'-7" found on Letrick p7 (x=68, y=16.6, axis
INDETERMINATE) and p8 (x=41-51, y=13, VERTICAL, rot passes) — all at
the TOP of the sheet, consistent with the back-wall chimney. NEVER
CHOSEN as a depth (mid-sheet x → smallest distance from mid; the
outermost rule kept it out). NAMED: nothing in the rule KNOWS it is a
chimney — it entered vertical-exterior candidacy on p8 and lost on
position. A projection-vs-face concept does not exist yet.

ITEM 3 — IMMATERIAL ATTRIBUTION (report only, not built):
  - Pair identification WITHOUT attribution: the two per-side winners
    of the positional rule on an established plan page are the pair
    BY CONSTRUCTION (the side split is geometric — envelope mid-line —
    not semantic). Equality tested on parsed feet+inches after merge.
  - Three or more candidates: the rule still returns ONE winner per
    side (outermost); extras are contenders. A side with NO candidate
    means no pair — refusal stands. Unequal winners -> attribution
    MATERIAL -> anchor required or face refuses.
  - Equal but footprint does not close: equality makes attribution
    immaterial, it cannot make an unclosable footprint close — EE
    still blocks; the ruling must never override closure.
  - LETRICK WOULD DERIVE FULLY under this ruling with no anchor:
    LEFT 30'-0" = RIGHT 30'-0" (equal pair, attribution immaterial),
    FRONT 54'-0", BACK 54'-0" from the rails. Four faces named.
    UNVALIDATED as a ruling until Howard adopts it; nothing bound.

DRY RUNS RE-RUN ON MERGED SUBSTRATE (both houses):
  Letrick p8 LEFT now returns 30'-0" — THE CONFIRMED ERROR IS DEAD,
  killed structurally at the merge, not by a value patch. All '0-00'
  HH admissions gone. p5/p7 unchanged and correct. Boni unchanged
  where correct: p4 L 30-2 (the 0.08 photo finish vs 5'10° REMAINS,
  still named, still unpatched), R 33-0*; p6/p7 unchanged. Letrick p1
  RIGHT changed 9-1%* -> 19'-11: the send-34 p1 photo finish was
  itself a same-string artifact that merge resolved (elevation stays
  excluded by precondition regardless).

================================================================
SEND-38 OUTCOMES (2026-08-16, appended — prediction file unrevised)
BUILT: Ruling XX (ADOPTED — attribution_verdict with the explicit
closure pin on every verdict), TT (line-pair sum closure instrument,
reports never gates, fraction loss declared), UU (band = observed gap
on merged data: 0.1143/0.212), VV (Unicode confusable-class mark
normalization), WW (depth candidates must lie on the side's rail
line). 15 new pinned tests; suite GREEN 2544.

NAMED OPEN registered in code (XX_NAMED_OPEN): different depths + no
garage REFUSES today — correct until ruled otherwise. Not designed,
not prototyped. Register note: the anchor is not garage-specific in
MECHANISM ("a labelled interior volume whose outboard wall lands on
one side elevation") — the garage is one reliable instance.

XX VERDICTS (real stores): Letrick p5 IMMATERIAL 30'-0", p7
IMMATERIAL 30'-0" — fires exactly as adopted. Boni p6 MATERIAL
(30-0* vs 33'-0'), p7 MATERIAL — anchor still required; nothing
about XX touched Boni's verdicts on the room-label sheets.

BONI p4 MOVED, AND THE MOVE IS THE FINDING: after MM merge, the
5'-10 string's surviving box lands at the SAME x as 30-2 — the 0.08
photo finish was CROSS-PASS BOX NOISE, NOT SIGNAL. The probe had been
breaking that tie by LIST ORDER — a silent coin flip. FIXED
STRUCTURALLY: an exact positional tie between distinct values is now
named ("tie") with chosen=None; XX reports INDETERMINATE naming the
tie and the missing segment-vs-total ruling. p4 LEFT is now honestly
UNRESOLVED instead of accidentally right.

FACES AS THEY ACTUALLY RENDER (no bind anywhere, model path):
  LETRICK: front 54'x9.9' and back 54'x9.9' derive; left/right WIDTHS
  read 30.0 each; left/right BODY faces refuse on "wall height not
  read" (heights null from the model) — a HEIGHT gate, orthogonal to
  attribution, which XX correctly does not override; both side GABLE
  triangles derive (8.75'). Aggregate siding_sqft 1532.7. So: XX
  resolves Letrick's attribution completely (no anchor needed), and
  the remaining side-face refusal is a different, pre-existing read
  gap — stated, not worked around.
  BONI: unchanged in every rendered value. No bind occurred.

UU CENSUS: INDETERMINATE dim strings after the band reset — Boni
7/289, Letrick 5/259 (~2.4%): rare, not impossible.

WW: on the real plan sheets it excluded nothing that was in
contention (chosen answers all sat on rail lines already); its
structural exclusion of the mid-sheet chimney is pinned in tests.
The Letrick p8 chimney runs class INTERIOR there (inside envelope) —
excluded by the 2D test, visible in excluded_interior.

TT AGAINST BONI p4 (LEFT FIRST, AS ORDERED): TT CANNOT PAIR
30-2 <-> 5'-10 on p4 LEFT — after merge they sit on the SAME line, and
TT's form (inner line sums to next rail out) requires two lines. The
drafting on p4 LEFT does not fit TT's line-adjacency. On p4 RIGHT
(high half) TT found one EXACT closure: 30'-0" = 14'-7 + 10'-11 +
4'-6 (residual 0) — the instrument works where the drafting matches.
Other line pairs FAIL with large residuals because adjacent columns
are frequently unrelated chains — TT's adjacency assumption is the
limit, reported not patched.

p8/p9 QUESTION ANSWERED: NO — the interior-width-as-rails failure
does NOT fail on its own under WW + TT. p8/p9 still answer
confidently (rails ESTABLISHED, candidates on rail lines, TT noise
inconclusive). The room-label precondition remains the only thing
excluding them.
