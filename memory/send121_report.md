# SEND-121 REPORT — TANIS, THE FRESH SCORED READ
2026-08-24 · Predictions: `memory/send121_predictions.md` (written first,
unrevised; outcomes appended below its line). Read-only throughout — no code
touched, no estimate written, EST-886440 untouched.

## THE RUN
- **Scored run**: run_id `4670606f7c24438d8affb9f996caa036`, started
  2026-08-24 01:38:40 UTC — 13 seconds after the predictions commit
  (`d74b41c` at 01:38:27). Estimate EST-564805 ("Tanis"), 4 pages, 144 dpi,
  claude-opus-4-5, $0.2255.
- **Build**: post-SEND-117 — rotation-normalize + refusal rails in
  (`f95cc5f`, 2026-08-23 16:05). The only commits since are the CLIENT-side
  cold-start retry and PRD text; no backend pipeline change. THIS IS THE
  CURRENT PIPELINE, NOT A SUPERSEDED ONE.
- **Reproduction**: a second same-build run (`318bb760…`, 11:49:52) is
  byte-identical on every scored figure — heights, widths, carve, rotation,
  schedule, marks, deduction, flags. Sole delta: vent_count 1 → 2 (the one
  figure that moved between runs, named).
- A third run at 00:07:13 PRE-DATES the predictions commit and is NOT the
  scored run; its figures happen to match but it does not count.

## REAL FAILURES — FIRST, SEPARATELY, NAMED
**THREE.**

1. **THE WALKOUT IS SILENTLY MISSED** (predicted by P2, reported as the
   failure it is). Zero occurrences of walkout / below-grade anywhere in the
   read; page 1 is identified "BASEMENT FLOOR LEVEL PLAN" and nothing is
   made of it; stories carried = 1. There is NO STEP PATH even to refuse it.
   The right side's below-grade siding — and its 2 sealed windows and 1
   sealed SGD — is invisible to the geometry layer. The only thing that kept
   a too-short right face from landing is that the right face refused for
   WIDTH first, an unrelated cause. THE WALKOUT RULING'S FIRST EXHIBIT.

2. **WINDOW COUNT 7 vs SEALED 20 — the marks-as-1 floor standing in for
   count evidence.** The schedule has no COUNT column (both pages), so the
   row parser correctly took no jurisdiction — and then the ungoverned
   one-row-one-opening convention carried 7 marks × 1. Six of the seven
   counts are the floor (count cells not located, each named); one (mark 7)
   is a located "1" on p3. The convention that stood correctly on Letrick's
   door rows UNDER-COUNTS TANIS BY 13 WINDOWS. A produced figure, not a
   refusal — it feeds counts (caps etc.), not the deduction (which refused).

3. **THE FABRICATION LEAK — nulled widths survive in the LF lane.** The
   quote guard nulled the model's widths as fabricated/misread: 97'-0"
   front/back, 57'-4" sides. Yet measurements carry **starter_lf 308 =
   2×97 + 2×57 exactly**, **eaves_lf 194 = 2×97 exactly**, and **rakes_lf
   122** — the same 122 nulled at `roof_planes.main.rake_lf` (quote
   57'-4"), carried at the top level. Basis string half-admits it:
   "printed read (no wall widths extracted)". THE GUARD COVERS
   walls / roof_planes / corner_heights / marks — NOT THE TOP-LEVEL LF
   FIELDS (eaves_lf, rakes_lf, starter_lf). Against the seal: wall
   perimeter 371.7 LF vs starter 308 (−63.7); front+back 254.3 vs eaves
   194 (−60.3). Quantities produced from evidence that was dismissed.

## THE SCORING — P1..P9, four verdicts
| P | Predicted (gist) | Happened | Verdict |
|---|---|---|---|
| P1 | 10.09 reads only if a readable TOF→PLATE band exists per face; else refuse, never borrow | 0/4 read; all four REFUSED, none borrowed; model's 9'-1⅛" (−1.0 ft) nulled ×12 | **SAFE FAILURE** |
| P2 | Walkout silently missed at the geometry layer; a real failure if it lands | 0 mentions; no STEP path; miss is upstream of quantities | **CONFIRMED** (real failure 1) |
| P3 | Chase surface created and SIDED (material-on-chase over-count) | No face derived → no chase surface ever created → 0.0 ft² sided total | **NOT SATISFIABLE** |
| P4 | Decisive per-page verdicts; correction before the model looks | 4/4 UPRIGHT: 37.2 / 42.4 / 62.5 / 58.4% — no normalization, no INDETERMINATE | **CONFIRMED** |
| P5 | COUNT column + ink-text → jurisdiction; else no jurisdiction, said so | Schedule found p3+p4; COUNT column FALSE → no jurisdiction, named; sizes 7/7 refused named; mark 3 dropped named | **CONFIRMED** (but see real failure 2 — the convention beneath it) |
| P6 | Counts may land; placement will NOT reproduce 3-front/1-back | Counts did NOT land (2 claims dropped named); 0 doors, 0 placement claimed | **SAFE FAILURE** |
| P7 | Deduction refuses when any face refuses; no zero posing | deduction_refused, faces_refused ×4, net None, 7 marks named | **CONFIRMED** |
| P8 | House-leaning pieces fail safe, never fabricate | Carve refused LEFT named; parser no-jurisdiction; 12 fabricated + 14 misread dims all caught | **CONFIRMED** — exception: the LF lane (real failure 3) |
| P9 | CCC stays UNVALIDATED unless Tanis draws a shoulder | Nothing derived past band_rectangle; no shoulder entered the read | **CONFIRMED** (n=2 stands) |

## THE FOUR THAT MATTER MOST
1. **Do all four faces read 10.09 ft? NO — 0 of 4.** Front / rear / right:
   "no TOP OF PLATE datum located" (front p3 band [0,46.2], right p3
   [46.2,88.4], rear p4 [0,46.2], datum_lines empty). Left: "no left
   elevation drawing located." Residuals: none exist — no value was
   produced. The model volunteered 9'-1⅛" = 9.09 ft on every face and all
   8 corners; sealed is 10'-1⅛" = 10.09; every claim nulled. Had it been
   trusted: −1.0 ft on all four faces.
2. **The four main walls vs ≈3,752 ft²: 0.0 ft² derived.** Gross 0.0, all
   four faces refused for width. No number posed. Trusted, the nulled
   claims (97'-0" front/back, 57'-4" sides, 9.09 height) build ≈2,807 ft²
   — front/back short 30.2 ft EACH, sides short 1.3 ft each, height short
   1.0 ft: a ~25% under-read refused whole.
3. **The four garage doors vs 3 front + 1 back: ZERO carried, ZERO
   placed.** The model claimed TWO (GARAGE1 16'×8', GARAGE2 9'×8', p2
   floor-plan callouts) — under the sealed four even as a claim — and both
   were dropped-not-located, named. No confident wrong placement exists;
   the failure is omission and it is safe.
4. **The stone chimney and the walkout.** Chimney: ABSENT as a chase (no
   chase surface exists on any face); NOTHING was sided (0.0 ft² total), so
   it was not sided-without-a-flag — the class simply never got a subject.
   Named adjacent finding: the model classed the ENTIRE rear body
   "SYNTHETIC STONE AS SPECIFIED" (profile stone; back siding_pct 85) —
   against the seal the rear is SIDED and the CHIMNEY is the stone; the
   claim sits on a refused face; no flag class exists for stone-vs-siding
   disagreement. Walkout: ABSENT ENTIRELY — real failure 1.

## THE DIAGNOSTICS, AS PULLED (observed; ABSENT stated where absent)
- **Heights per face** (`_height_build`, status APPLIED,
  model_heights_demoted true): front REFUSED p3 band [0.0,46.2] datum_lines
  [] · rear REFUSED p4 band [0.0,46.2] datum_lines [] · right REFUSED p3
  band [46.2,88.4] datum_lines [] · left REFUSED "no left elevation drawing
  located". All four reasons named; heights nowhere borrowed.
- **Carved faces**: 3 of 4 — front (p3), right (p3), rear (p4); LEFT NOT
  CARVED. p4's OCR carries REAR ELEVATION / REARELEVATION title strings and
  NO left-side title at all (the sheet prints "REAR ELEVATION / LEFT SIDE
  ELEVATION" per the model's sheet read) — the carve failed at TITLE OCR,
  the step before banding. Overlay proposals exist for front/back/right
  (band_rectangle tier, area None); NONE for left.
- **Rotation verdicts** (`_page_rotation`): p1 UPRIGHT 37.2% (counts
  74/56/69) · p2 UPRIGHT 42.4% (86/49/68) · p3 UPRIGHT 62.5% (55/14/19) ·
  p4 UPRIGHT 58.4%. All ≥33.5 cut — against dart's 9.6/6.0 rotated and
  Boni/Letrick's ~34–52 upright. No page normalized; no INDETERMINATE.
- **Schedule** (`_schedule_tables`): window schedule p3 + p4, identical
  content, **count_column: false on both**. Rows recovered: marks 1, 2, 4,
  5, 6, 7, 8 (7 rows). Count cells: mark 7's "1" LOCATED on p3; marks
  1,2,4,5,6,8 count claims NOT located ("no isolated integer token equal to
  the claimed count '1' in the row-band right of the mark" — each named per
  page). Sizes: ALL 7 printed_size quotes not in OCR (3'-0"×4'-0",
  3'-0"×5'-0", 3'-0"×3'-0" ×2, 3'-0"×5'-0", 2'-0"×3'-0", 3'-0"×4'-0") —
  nulled, marks refused named. NO door schedule rows exist.
- **Dropped marks** (`_marks_dropped_not_located`, 5): windows:3 (quotes
  "3", "3'-0\"×5'-0\"", pages 3+4) · doors:ENTRY (3'×8', p2) ·
  doors:GARAGE1 (16'×8', p2) · doors:GARAGE2 (9'×8', p2) · doors:PATIO
  (6'×8', p2). All rotations_checked.
- **Rail flags — 4, grouped, as they render** (all loud):
  `corner_walk_conflict` (primary 8 out / 4 in vs roof-pass 10 / 6) ·
  `faces_refused` (4: back, front, left, right) · `opening_sizes_refused`
  (7: marks 1, 2, 4, 5, 6, 7, 8) · `deduction_refused` (7 rows, 4 faces).
  No rotation flags (nothing normalized, nothing indeterminate).
- **Deduction state** (`_openings_deduction`): deduction_refused TRUE,
  refusal_class faces_refused, openings_sqft_read 0.0, gross_sqft 0.0,
  faces_refused [back, front, left, right], 7 refused marks each named
  "size refused — contributes 0 ft²". `siding_with_openings_sqft` None —
  the line refuses, no zero poses.
- **The seam ledger caught 26 dims + 5 marks**: 12 quote-fabricated nulled
  (incl. walls.left/right.width_ft 57'-4", walls.back/left.height_ft
  9'-1⅛", 4 corner heights, garage wall height, garage eave 72, main rake
  122, garage overhang 12") · 14 misread nulled (incl. walls.front/back
  .width_ft 97'-0" misread-of "70", front/right heights 9'-1⅛" misread-of
  "118", porch 12' misread-of "20", 4 corner heights, 2 gutter runs) ·
  1 no-evidence (garage rake) · 5 marks dropped · 7 mark sizes nulled ·
  roof_pitch overwritten 6/12→7/12 by the roof pass.
- **What still carried into measurements**: window_count 7 · opening_count
  7 · door/garage/entry/patio counts 0 · opening_sqft 0.0 · siding_sqft 0.0
  · net None · outside corners 8 (80 LF @ the 10.0 model-height hypothesis
  lane; sealed 10.094 → 80.75, −0.9%) · inside 4 (40 LF) · **starter_lf 308
  · eaves_lf 194 · rakes_lf 122 — real failure 3** · overhang 12.0
  (form_default, named) · stories 1 · gable rise 14.3 carried on left/right
  but gable_sqft null (refused — no width) · vent 2 (was 1 in the 01:38
  run — the sole run-to-run delta) · shutters 0.
- **OCR coverage**: p1 15,731 chars · p2 12,519 · p3/p4 elevation sheets
  ~1,529/1,751 at the quote-check pass (13,285/13,478 full-page) — two
  drawings per sheet, thin ink text.
- **Footprint**: closure "closes" with 0 checks (nothing to relate);
  area_table first floor 4,493 + garage 1,060 = 5,553 ft² carried as the
  footprint read; garage side UNVERIFIED (single unopposed naming signal,
  Ruling CC C1 held).

## WHERE THIS STANDS
- **What Tanis proved that Boni and Letrick could not**: on a wholly
  foreign drafter with UPRIGHT pages — no rotation excuse — the evidence
  guard alone dismissed every one of 26 fabricated/misread dimensions
  (widths 30 ft wrong, heights 1 ft wrong) and the read produced 0.0 ft² of
  siding rather than a 25% under-read.
- **What it exposed that nothing had exposed before**: the walkout class
  (a silent geometric miss with no path even to refuse) · the LF-lane
  fabrication leak (starter/eaves/rakes surviving their own nulled
  sources) · the marks-as-1 convention producing a live wrong count
  (7 vs 20) · a two-drawings-per-sheet title carve miss (LEFT on p4) · a
  stone-vs-siding material claim with no flag class.
- **What remains unscored until dart runs**: the same honesty on a
  rotation-normalized drafter — dart's refusals were entangled with
  rotation; its fresh scored read tests whether upright pages convert
  refusals into reads or keep refusing for the second, real causes. TWO
  INDEPENDENT FOREIGN DRAFTERS MAKE A PROPERTY; TANIS ALONE IS AN ANECDOTE.

## OPEN ITEMS — STATUS · WHO OWES THE NEXT MOVE
- Dart scored run — Howard seals, then predictions, then the read. **Top of
  the queue.**
- Symbols placement — NOT AUTHORIZED; first job named (Boni's two
  side-entry garage doors).
- Material-on-chase class — still UNTESTED (Tanis never made a chase);
  adjacent stone-on-body claim class now named. Awaiting ruling.
- The walkout STEP path — first subject now exists (Tanis right side).
  Awaiting ruling.
- The LF-lane leak (starter/eaves/rakes outside the quote guard) — NEW,
  found this send. Awaiting ruling; not fixed, per the no-code order.
- The marks-as-1 convention's jurisdiction bound — the floor now has a
  live wrong figure against a seal. Awaiting ruling.
- The p4 title carve miss (two drawings per sheet, one title OCRs) — NEW.
  Awaiting ruling.
- Catch-all message inventory — still owed.
- rot180 — held, cost stated (SEND-117).
- Openings review card — behind faces deriving.
- CCC — UNVALIDATED at n=2 (Tanis carried no drawn shoulder).

Standing rules held throughout: no cross-drawing borrowing observed, no
estimate influenced another, no job names in code, model heights rode the
hypothesis lane only. EST-886440 untouched. Purity pin holds.
