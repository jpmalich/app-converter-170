# SEND-45 — HEIGHT BUILD DRAFT (mechanism for review — NOT WIRED)
2026-08-16. Read-only send. No derivation code touched, no tests changed,
no binding. Dry-run artifacts: `send45_height_dryrun.py` (the draft
algorithm, runnable), `send45_height_dryrun.json` (per-face outcomes).

---

## PART 1 — SEND-44 REPORT WALK (most consequential first)

### 1. Height Census — FINDING: every model height descends from a stack-up the sheets do not support
- **Boni**: all four faces carry `height_ft = 20.0`. The census's
  `distributed_sources` shows every height path (corner_heights.0–7, all
  walls.*.height_ft, all segments) descending from exactly TWO strings:
  `9'-11"` (located, ONE bbox per page) and `8'-1 1/2"` (**loc = null —
  NEVER LOCATED on any sheet**). Worse: 9'-11" + 8'-1½" = 18.04 ft ≠ 20.0.
  The model's own cited evidence cannot reconstruct the model's own
  number. And the sheets print `8'-1 1/8"` (ceiling note), not 8'-1½ —
  the unlocated string is a misread of a note, not a dimension.
- **Letrick**: front/back = 9.9 from ONE string (`9'-11 1/8"`, p1) fanned
  across corner_heights.0–3 **including the two corners that live on p2**
  — a cross-face copy performed by the model itself. left/right = null.
- **DESIGN CONSEQUENCE**: model-path heights are DEMOTED to hypothesis.
  Height must be structurally derived per face from that face's own
  elevation drawing, or the face refuses. This is the single most
  important finding: the Standing Prohibition (no cross-face copying) is
  being violated *by the model*, upstream of everything we gate.

### 2. Grade Reads — FINDING: grade lines are label-locatable on some faces only; Boni HAS a walkout
- Letrick prints `APPROX GRADE` on p1 (front band) and TWICE on p2 — one
  per side band (y≈32 left, y≈72 right). Boni prints `GRADE @` once on
  p1 (front band, x≈2.6) and **nothing** on p2 — Boni left/right have no
  locatable grade line at all.
- Boni p1 rear band: `TOP OF WALKOUT FOOTER` ×3 (y≈90) — **a real
  stepped-grade test case exists** (answers the "is there a walkout
  anywhere" question: YES, Boni rear).
- Both sets print `FINAL GRADE TO BE DETERMINED ON SITE` — the plans
  declare their own grades approximate.
- `FINISH GRADE` appears only on p3 (section sheets) — reference planes
  (Ruling KK territory), not face-bound; excluded from face verdicts.
- **DESIGN CONSEQUENCE**: FLAT must be positively established;
  an unlocatable grade line is UNKNOWN and refuses extra area. Verdicts
  carry the plan's own "approximate" disclaimer. STEP needs a walkout
  ruling (see DP-4).

### 3. Elevation Reads — FINDING: the vertical rails exist, face-bindable, on both sets
- Both houses: p1 = "FRONT & REAR ELEVATIONS", p2 = "LEFT & RIGHT
  ELEVATIONS" (printed title blocks). Per-face sub-titles located on the
  sheets: Boni `FRONTELEVATION`/`REARELEVATION`/`LEFTELEVATION`/
  `RIGHTELEVATION`; Letrick prints them token-reversed
  (`ELEVATION FRONT`, `ELEVATION LEFT`, …). Each sub-title sits BELOW its
  drawing → the sheet splits into per-face y-bands structurally (no
  whitespace-gap heuristic needed — the census's "no y-gaps > 8%" is
  irrelevant once titles carve the bands).
- Boni: 17 + 16 vertical dims; Letrick: 5 + 5. Datum labels (`TOP OF
  PLATE`, `FIRST FLOOR`, `SECOND FLOOR`, `TOP OF FOUNDATION`) print at
  the wall corners.
- **DESIGN CONSEQUENCE**: the build reads heights from
  (band, datum lines, vertical rails) — all three are present.

### 4. Tie Audit — FINDING: exactly one tie in the store
- Boni p4 LEFT: `5'-10°` vs `30-2`; list order would have silently
  picked 5'-10. INDETERMINATE is doing its job. Stays blocked on the
  segment-vs-total ruling. Nothing in the height build touches it.

### 5. p4 Closing Chain — FINDING: segment↔total closure is real and exact
- Boni p4 RIGHT vertical high half: 30'-0" = 14'-7 + 10'-11 + 4'-6 =
  360" exactly, residual 0. The chain-closure instrument works and is
  the natural evidence class for the future segment-vs-total ruling.
  (Relevant to heights: the same strict-closure posture is used for
  stacked story rails — see mechanism.)

### 6. Second Footprint — FINDING: no evidence of two footprints on one sheet
- No x-gaps > 15% in the dimension spans of any plan page, either house.
  The "house + detached garage drawn on one sheet" risk has no instance
  in the datastore. Stays a named open (registered in
  `RULINGS_REGISTER`), no build, no design debt.

---

## PART 2 — THE HEIGHT BUILD MECHANISM (draft, for review)

### Provenance chain (per face, no cross-face anything)
1. **Face → band.** A face's sub-title (squashed string containing
   {FACE} + ELEVATION in either token order; never a combined "&" sheet
   title) carves its y-band on its elevation page: band = (previous
   title's y, own title's y). No sub-title → face refuses.
2. **Datum lines.** Within the band, datum labels (`TOP OF PLATE`,
   `SECOND FLOOR`, `FIRST FLOOR`, `TOP OF FOUNDATION`,
   `TOP OF WALKOUT FOOTER`) become horizontal datum LINES. Same-label
   instances whose glyph boxes y-overlap merge into one line (both ends
   of the drawing label the same line); non-overlapping same-label
   instances stay separate lines (two plate lines are real on a 2-story
   face). Exclusions, both parameter-free:
   - prose (contains CEILING/PLAN/JOIST/ELEC),
   - **TITLE-BLOCK FURNITURE**: an identical squashed string whose box
     overlaps a twin on a NON-ELEVATION page is sheet furniture (the
     title-block area table prints "FIRST FLOOR / SECOND FLOOR /
     UNFINISHED BASEMENT" at x≈94 on EVERY page). Set membership, no
     thresholds. Verified: furniture strings recur on 9–11 pages; real
     datum labels never recur off the elevation pages.
3. **Gap binding.** A vertical rail (dimension-like, VERTICAL axis, in
   band) binds to the adjacent datum-line pair whose OPEN interval
   STRICTLY contains its whole glyph box — a box touching a datum line
   is AT the datum, not between the pair. (This positional gate already
   kills Letrick's `19'-11` misread: its box overlaps the plate line.)
   Per gap: one distinct value = BOUND; >1 = CONTESTED; none =
   UNDIMENSIONED. One value per gap is the vertical analog of Ruling JJ.
4. **Height path.** Face height = sum of consecutive BOUND gaps from the
   bottom siding datum (DP-1) to the topmost TOP OF PLATE line. ANY
   contested or undimensioned gap on the path → the face REFUSES with
   the gap named. No averages, no model fallback, no cross-face copy —
   a rail can only enter a face if its box lies inside that face's band
   (the Standing Prohibition becomes structurally unviolable).
5. **Provenance record** persisted per face: band, datum lines (label +
   y), every rail (raw string, inches, gap, bbox, page), and either the
   established chain or the refusal. 423 on every derived write, as
   everywhere.

### Grade verdicts (independent, per face)
- **UNKNOWN** (default): no grade label (`APPROX GRADE`, `GRADE @`,
  `FINISH GRADE`; prose excluded) located in the face's band → verdict
  UNKNOWN, **no grade area added**, loud on the surface. Label scans run
  on UNMERGED runs (position-merge can keep a clipped variant —
  Letrick's `PROXGRADE`).
- **FLAT** (positively established, never by absence): the grade label's
  glyph box overlaps a datum line's box on that face — the grade line IS
  the datum line. Zero extra area, verdict shown with the plan's own
  disclaimer: "plan-approximate (FINAL GRADE TO BE DETERMINED ON SITE)".
- **SLOPE**: grade located at BOTH ends of the face on different lines
  AND a drop rail strictly inside the (grade-high, grade-low) gap →
  extra area = **½ × base × drop**, base = the face's already-read
  width. No two-end read exists in either current dataset → SLOPE fires
  nowhere today (correct: no evidence, no area).
- **STEP**: not built until ruled (DP-4). Walkout evidence surfaces as a
  note: "walkout footer labeled — STEP grade suspected, awaiting
  ruling"; verdict stays UNKNOWN.
- **Gable separation**: grade lives in its own module and writes only
  `grade_extra_sqft` with basis label "grade triangle ½·base·drop". The
  0.70 path keeps `GABLE_CONVENTION_LABEL` and its own field. Pins at
  wiring time: grade module does not reference `GABLE_FACTOR`; neither
  path can write the other's field; a census test asserts the two
  labels never appear on the same line item.

### Exact refusal / verdict language (the rendered surface, per Ruling C)
- `wall height not established from {face} elevation — gap {DATUM_A}@{y} → {DATUM_B}@{y} {CONTESTED: rails 9'-11"(119), 9'-1⅛"(109) | UNDIMENSIONED} — area not derivable`
- `no {face} elevation drawing located — height not established — area not derivable`
- `wall height not established from {face} elevation — no {DATUM} datum located — area not derivable`
- `grade line not located on {face} elevation — verdict UNKNOWN — no grade area added`
- `grade FLAT: grade label on {DATUM} line — no grade area (plan-approximate: FINAL GRADE TO BE DETERMINED ON SITE)`
- `grade SLOPE: ½ × {base} × {drop} = {sqft} sqft (plan-approximate: FINAL GRADE TO BE DETERMINED ON SITE)`
- `walkout footer labeled on {face} elevation — STEP grade suspected — verdict UNKNOWN pending ruling`
- Ruling V stays visible: downspout drop + gutter-corner LF remain
  `PENDING_CONVERSION` off `_ai_avg_wall_height_ft` until converted to
  established per-face heights (conversion is its own send).

---

## PART 3 — WHAT THE FACES RESOLVE TO (computed by the dry run, not guessed)

Option A = FIRST FLOOR → TOP OF PLATE. Option B = TOP OF FOUNDATION →
TOP OF PLATE. (DP-1 picks one.)

| face | A | B | grade | note |
|---|---|---|---|---|
| letrick front | **9'-1⅛" (9.08)** | REFUSED (FF→FND undimensioned) | **FLAT** (label on foundation line) | |
| letrick left | **9'-1⅛"** | REFUSED | **FLAT** | |
| letrick right | **9'-1⅛"** | REFUSED | **FLAT** (both-end rails agree: 109 & 109) | |
| letrick rear | REFUSED — CONTESTED: `9'-11*`(119, x=87) vs `9-1%`(109, x=31) | same | UNKNOWN | real same-gap conflict, both ends named — DP-2 |
| boni front | REFUSED — CONTESTED: `8'-1⅛` vs `29'-1` (overall rail's text sits mid-gap) | same | UNKNOWN (`GRADE @` label present but off-datum → single-end, not classifiable) | DP-3 |
| boni rear | REFUSED — joist band (plate₁→SECOND FLOOR) UNDIMENSIONED | same | UNKNOWN + **walkout note** | DP-4, DP-5 |
| boni left | REFUSED — joist band UNDIMENSIONED | same | UNKNOWN | DP-5 |
| boni right | REFUSED — no FIRST FLOOR datum in band (A); joist band (B) | — | UNKNOWN | DP-5; NB gap FND→plate₁ is BOUND `9'-11⅛` |

Net effect vs today: **Letrick's side-body refusals are CURED
structurally (3 of 4 faces establish 9'-1⅛" from their own drawings)**;
Letrick rear and all Boni faces refuse with NAMED, specific reasons
instead of "wall height not read". Boni's model-path 20.0 is exposed as
unreconstructable. Nothing was tuned to reach any of this; EST-886440
untouched.

## PART 4 — DECISION POINTS (need rulings before wiring)
- **DP-1 — bottom siding datum.** A (FIRST FLOOR→plate: the only pair the
  sheets consistently rail-bind; foundation exposure would ride the grade
  path) vs B (FOUNDATION→plate: closer to what siding covers; but
  FF→FND is undimensioned everywhere, so B refuses everything except
  Boni right's direct 9'-11⅛ rail). Draft recommends **A**, with the
  FF→FND strip named as a visible open, not silently absorbed.
- **DP-2 — same-gap, both-ends conflict** (Letrick rear 119 vs 109).
  Draft: refuse with both strings named. Any tiebreak (value voting
  across faces, glyph-form preference) violates "positions disambiguate,
  values do not" — if a tiebreak is wanted it must be ruled.
- **DP-3 — off-column rails contaminating gaps** (Boni front: the 29'-1
  overall; the garage's 9'-11⅛ vs main's 9'-1⅛ in one gap). These are
  SEGMENT rails (garage wing vs main body) sharing a face. Resolving
  needs segment x-extents on the elevation — a future build. Until then:
  contested → refuse, contestants named.
- **DP-4 — STEP verdict admission.** May `TOP OF WALKOUT FOOTER` datums
  + basement-wall rails (13', 11', 7', 9', …, present on Boni rear)
  establish STEP and its rectangle, absent a literal grade line label?
  Not built until ruled.
- **DP-5 — the undimensioned joist band** (Boni, systematic: SECOND
  FLOOR→first TOP OF PLATE never carries a rail). Options: (i) refuse —
  contractor tapes it (draft default); (ii) rule the band ZERO for
  siding area with the strip labeled (conservative understatement:
  9'-11⅛ + 8'-1⅛ = 18.0 vs model's invented 20.0); (iii) a sealed,
  labeled joist convention like the 0.70 gable. Draft builds (i) only.

## COMPLIANCE
- Standing Prohibition: enforced structurally (band containment).
- EST-886440: untouched. No tuning anywhere; every filter in the draft
  is set-membership or strict geometric containment.
- Nothing wired. Nothing bound. The dry-run script is the mechanism's
  executable specification for review.
