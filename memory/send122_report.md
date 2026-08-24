# SEND-122 REPORT — LF-LANE GUARD · COUNT FLOOR DEAD · THE REFUSAL BEFORE THE READ · PURITY CHECK · STONE-REACH REPORT
2026-08-24 · Items 1–3 BUILT and pinned; items 4–5 REPORT ONLY.
STAMP: `2026-08-24 17:47 UTC · 9392f40 · CLEAN · 2837 passed, 9 skipped`
(+9 SEND-122 pins) · census GREEN 0 PENDING_CONVERSION · ingress 4
passed. Two pre-stamp reds, BOTH the guard catching this send's new
code, both fixed NAMED: the consumer-key census on the internal record's
`lane` key (subscript, census untouched — SEND-116 precedent); the seam
census on 4 new comprehensions (2 INERT classifications, 2 ACCOUNTED
`_count_unread` skips booked upstream). No estimate written; EST-886440
untouched. Quantities only.

## ITEM 5 — PURITY CHECK (done first, as ordered)
**Is the volunteered 9'-1⅛" Letrick's figure, and was Letrick reachable
from the Tanis run?** Three facts, scope stated:
1. **The exact string 9'-1⅛" is NOT reachable from the run.** The
   pipeline reads only its own pages (Ruling AAA); no cross-estimate
   read exists; each run has its own session. The only `9'-1 1/8"` in
   the backend is a tape-parser docstring example (pdf_overlay.py L1170)
   that never enters any model call.
2. **BUT prior-house FIGURES ARE in the prompt** — the derived-value
   worked example in the blueprint prompt ships the literal stackup
   `9'-11 1/8" + 1'-0" + 8'-1 1/8" + 11 1/2"` (routes/ai_blueprint.py
   ~L154). 9'-11 1/8" is Letrick's fan string; 8'-1 1/8" is Boni's
   ceiling note. Every run, every drafter, sees these numbers. The
   volunteered 9'-1⅛" is edit-distance 1 from BOTH. NAMED EXPOSURE —
   whether the example gets neutral figures is Howard's ruling; not
   changed this send.
3. **Tanis's own ink carries the likelier source.** p3 OCR holds a
   VERTICAL token RAW `-1 1/8` (norm 118, ROT270, x 23.6 / y 75.9) —
   the TAIL of a drawn height string beside the front elevation. The
   sealed height is 10'-1⅛"; the drawing evidently prints it and OCR
   dropped the leading feet digits. A model reading those pixels and
   dropping the "10" lands exactly on 9'-1⅛".
**Verdict**: most probable cause is a glyph-level misread of TANIS'S OWN
printed height (its tail is verifiably on the page); the exact Letrick
string was not reachable. NOT CLOSED AS PURE: the prompt example is a
standing prior-figure exposure, named above. The guard nulled the claim
either way — that is why it never mattered to the quantities.

## ITEM 1 — LF-LANE LEAK (P0) — BUILT
**The rule: A COMPUTED TOTAL MAY NOT OUTLIVE ITS NULLED INPUTS.**
- New pass `_null_computed_lf_lanes` runs AFTER the quote guard: the
  computed LF lanes null NAMED when the wall dims their formulas stand
  on died — starter_lf (needs all 4 widths) · eaves_lf (eave-wall
  widths) · rakes_lf (gable-wall widths; the evidenced plane sum still
  governs when planes carry rakes) · outside_corner_lf (per-corner
  heights or wall heights) · inside_corner_lf (wall heights — count ×
  avg would ride the model-height hypothesis, which never feeds a
  quantity). Records ride `_lf_lane_nulled`; the seam ledger books
  `lf_lanes_nulled_inputs_dead`.
- Nulled lanes carry **None into measurements** — no `or 0`
  resurrection, no `4 × avg-height` hypothesis fallback, starter basis
  prints REFUSED naming the cause. Loud rail `lf_lane_refused` EN/ES.
- **Tanis replayed (read-only, stored raw deep-copied)**: all five lanes
  null with the leaked values named — starter 308 · eaves 194 · rakes
  122 · outside corner LF 80 · inside corner LF 40 → all None.
**EVERY LANE THE GUARD DOES NOT COVER (the ordered inventory — scope
stated, closure NOT claimed; this is what the sweep swept):**
- Quote-guarded (DIM discipline, unchanged): walls width/height (+
  segments), porch w/d, roof_planes eave/rake/overhang/wall_height,
  gutter_runs.lf, corner_heights, eave_overhang_in, fascia_width_in;
  marks (sizes + count cells) via the mark locator.
- NOW input-gated (SEND-122): starter_lf, eaves_lf, rakes_lf,
  outside_corner_lf, inside_corner_lf.
- **STILL OUTSIDE ANY GUARD** (bare model numbers, no quotes, no
  formula gate — reported, not fixed): `soffit_sqft`,
  `level_frieze_lf`, `sloped_frieze_lf`, `drip_edge_lf`,
  `total_trim_sqft` (all schema'd "PRINTED … null if not printed" but
  carried uncited — verifying them needs a schema change to DIM, a
  build awaiting ruling); `vent_unit_count`, `shutter_panel_count`
  (bare counts); `footprint_area_sqft` (derived form WITH srcs — its
  quotes ride the locator, partially covered); corner COUNTS (bare, but
  cross-checked by the corner-walk conflict flag);
  `avg_wall_height_ft` (hypothesis lane, demoted by construction).

## ITEM 2 — MARKS-AS-1 FLOOR (P0) — BUILT
**The rule: A ROW WITH NO COUNT EVIDENCE REFUSES. IT DOES NOT CARRY 1.**
Supersedes the ungoverned one-row-one-opening convention left standing
at SEND-114/116.
- New pass `_refuse_unevidenced_counts` runs after every locator: a
  window/door row whose qty carries no evidence (None/0) becomes
  `_count_unread` + a NAMED entry on `_schedule_count_unread` (reason
  "no count evidence — refused, never 1") — riding the existing loud
  rail, the deduction's named refusals, and window_count's
  refuse-when-all-refused law. Seam ledger: `counts_refused_no_evidence`.
- Every remaining floor site now sits behind a `_count_unread` skip:
  derived openings (both loops), `_ai_openings_schedule`, the garage
  side signal, the sill-width sum, and the cross-read comparators
  (evidence counts only, `or 0`).
- **Tanis replayed**: marks 1, 2, 4, 5, 6, 8 REFUSE NAMED (6 rails);
  mark 7 (the one located count) stands; **window_count 7 → 1**; the
  schedule surface carries only mark 7. Rails 4 → 12 total.
- **RE-READ OF EVERY STANDING "UNREACHABLE" EXCEPTION** (ordered):
  1. SEND-117 item 3 pin (`test_marks_as_1_collapse_case_stays_
     unreachable`) — governed rows: HOLDS UNCHANGED and is now
     strengthened — the ungoverned lane that bypassed it is dead.
  2. SEND-38 "NO_PAIR unreachable geometrically" (gable pairing: a face
     is always its own candidate) — re-read against code: HOLDS, the
     geometric argument is intact.
  3. Color-tier "unreachable-by-accident" (vinyl_color_tiers L86 +
     its pin) — structural byte-identical class: HOLDS.
  4. test_hover_bb_profile_mapping "was unreachable" — historical
     narrative of a fixed bug, not a standing exception.
  5. ai_measure/ai_health "network unreachable" strings — error-copy,
     not exceptions.
  One exception was count-reachability-based and it is the one Tanis
  broke; the rest stand on geometry or structure and survive re-read.

## ITEM 3 — WALKOUT (P1) — THE REFUSAL BEFORE THE READ, BUILT
- New loud rail `below_grade_unread` fires from the sheet inventory
  BEFORE any quantity: any sheet titled BASEMENT / LOWER LEVEL /
  WALKOUT / WALK-OUT names itself — "this read has no below-grade /
  walkout path; any walkout siding is NOT included; flag it by hand
  until a walkout ruling lands." EN + ES.
- **Tanis fires it**: p1 "BASEMENT FLOOR LEVEL PLAN".
- **WHAT EVIDENCE A WALKOUT LEAVES, AND WHAT TANIS CARRIES (ordered
  report)**: searched the full persisted OCR store (all 4 pages, all
  three passes) for GRADE · WALKOUT · WALK-OUT · LOWER LEVEL · T.O.F ·
  TOP OF FOUNDATION · FOOTING · EGRESS · AREAWAY · RETAINING:
  **ZERO hits on every term except BASEMENT ×4, all on p1, all
  title-block.** No grade line labels, no lower-floor datum text on
  the elevations (p3/p4 ink text is thin — 1.5–1.7k chars at the
  quote pass), no foundation-step notes.
  **THE HONEST ANSWER, AS PREDICTED POSSIBLE: on Tanis, beyond the
  basement sheet NAME, walkouts leave nothing machine-readable —
  WALKOUTS NEED A HUMAN FLAG.** The rail built here is exactly the
  refusal that evidence supports; a finer walkout read has nothing on
  this drafter to stand on.

## ITEM 4 — STONE-BODY MISCLASSIFICATION — REACH REPORT (nothing built, as ordered)
Where a material claim can reach a quantity:
- The claim: `walls[].wall_body_profile_callout` — model text, NEVER
  OCR-verified (no quote discipline on callout strings).
- The reach: `profile_callouts.classify_profile(callout)` →
  `per_profile_sqft[family] += face ft²` → `_per_profile_sqft` →
  LP package profile lines (lp_package.py L327/L680/L1086: board-batten
  vs lap vs shake SKUs price from this split) and the per-elevation
  breakdown surface.
- Verified live: `classify_profile("SYNTHETIC STONE AS SPECIFIED") =
  "stone"` — had Tanis's rear derived, its ENTIRE body ft² would have
  routed to the stone family and OUT of every siding profile line,
  with zero flag. The sealed truth: the rear is SIDED; only the
  CHIMNEY is stone.
- The only gate that stopped it on Tanis: the rear face refused for
  width — an unrelated cause.
- **No flag class exists for material claims.** A claim-vs-callout
  cross-check (e.g., a stone body claim on a face whose elevation
  carries siding callout ink, or any whole-face material claim moving
  >X ft² between families) would be the guard's shape — NOT BUILT,
  awaiting ruling.

## WHAT THE FIXES CHANGE (stored-raw replay, read-only; live estimates
move only on their next read)
- Tanis: starter 308→None · eaves 194→None · rakes 122→None · corner
  LF 80/40→None · window_count 7→1 (6 marks refused named) · flags
  4→12 (6 count refusals + lf_lane_refused ×1 naming all 5 lanes +
  below_grade_unread + the original 4).
- Boni/Letrick/dart: no stored figures move (their LF lanes stand on
  live widths where derived; refused where already refused); the
  Letrick door row-per-instance counts survive ONLY if their rows carry
  located/parsed evidence — anything conventional now refuses on the
  next read, per the ruling.

## OPEN ITEMS AFTER THIS SEND
- Dart scored run — Howard seals ground truth (widths, depths, heights,
  opening counts, projections) → predictions first → fresh read. TOP OF
  QUEUE.
- Printed-only bare fields (soffit/friezes/drip-edge/total-trim) —
  outside any guard; schema-to-DIM build awaiting ruling.
- Material-misclassification flag class — reach reported above,
  awaiting ruling.
- Prompt worked-example prior-figures (9'-11 1/8" / 8'-1 1/8") — named
  exposure, awaiting ruling.
- Symbols placement — NOT AUTHORIZED.
- Catch-all message inventory — still owed.
- rot180 — held. CCC — unvalidated at n=2.

Standing rules held: no cross-drawing borrowing, no estimate influenced
another, no job names in code (the LP ground-truth key file and rulings
register carry historical names as DATA/registry, unchanged), model
heights hypothesis-only. EST-886440 untouched. Purity pin holds.
