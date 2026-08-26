# SEND-130 REPORT — WHERE TANIS'S LINE-WORK STOPS, PER FACE
2026-08-26 · Quantities only. Probe: `memory/send130_tanis_linework_probe.py`
(read-only — no run, no estimate, no proposal written).

## 1. THE ANSWER: STEP 2 OF 5, ON ALL THREE CARVED FACES
The read is a five-step chain: **CARVE → DATUM PAIR → SEGMENTS → FENCE →
OUTLINE.**

| face | 1 carve | 2 datum pair | 3 segments | 4 fence | 5 outline |
|---|---|---|---|---|---|
| **front** (p3, band 0–46.2) | **OK** | **FAILED** — none located | **OK — 31,841** | never reached | never reached |
| **right** (p3, band 46.2–88.4) | **OK** | **FAILED** — none located | **OK — 31,841** | never reached | never reached |
| **rear** (p4, band 0–46.2) | **OK** | **FAILED** — none located | **OK — 27,566** | never reached | never reached |
| **left** | **FAILED** — no left elevation located | — | — | — | — |

**It is not a fence. It is not an unresolved outline. It is the DATUM
PAIR — and not one datum of any kind is located in any of the three
bands** (no TOP OF PLATE, no FIRST FLOOR, no TOP OF FOUNDATION). The
refusal string is the honest one the pipeline already prints: "no TOP OF
PLATE datum located."

The left face fails one step EARLIER, at the carve — the same class as all
four of dart's faces.

## 2. IS IT SOMETHING SMALLER? THE TEST THAT SEPARATES THE TWO ANSWERS
"No datum located" could mean the labels are there and the read cannot see
them (small) or they are not there (a limit). Both were tested:

- **Re-rendered and re-OCR'd at x2, x4 and x6** (up to 15,552 × 4,790 px
  per band): **zero datum words at every scale, on every face.** The run
  count does not rise with scale (front 21 → 17 → 15) — there is nothing
  finer to find.
- **The drawing area itself is annotation-free**: of the text runs in each
  band, the ones inside the drawing (x < 90%) are **front 2 · right 39 ·
  rear 8** — and every one of them is the window-schedule table, a sheet
  title, or OCR noise ("CPERATION", "D2.8E -Ns"). **Not one level label.
  Not one dimension string.**
- The source PDF carries **no text layer at all** (0–18 characters per
  page): it is a raster scan in a PDF wrapper, so there is no second
  place to read a label from.

**Verdict: a LIMIT, not something smaller** — but a NARROWER limit than
"line-work does not work on tanis". The outline instrument is READY on
three faces: 31,841 and 27,566 vector segments sit in exactly those
bands, waiting. What is missing is **the RULER** — two labelled
horizontal datums to scale pixels into feet. This drafter's elevations
print neither the labels nor any dimension inside the band.

**What cannot be said from here**: whether the labels were never printed
or are printed in a form no OCR reads. That distinction is registered as
open rather than guessed.

**So the first foreign face that could emit is still not available** — but
the gap is now one named instrument (a scale without labels), not a
mystery. Anything that establishes a face scale without a labelled datum
pair — a graphic scale bar, a printed dimension inside the band, a
plan-derived width tied to that face — unlocks three tanis faces at once,
because steps 1 and 3 already pass.

## 3. REGISTERED THIS SEND (`ocr_geometry.RULINGS_REGISTER["findings"]`, all pinned)
1. **THE MARK BELONGS TO THE FIGURE, NOT THE FACE.** Replace the figure
   with an independently evidenced one and the mark clears, NAMED. The
   shape generalises past attribution: any refusal keyed to a figure must
   be re-asked when the figure changes, and the clearing is always named.
2. **THE WIDTH/HEIGHT ASYMMETRY, STATED RATHER THAN IMPLIED.** An
   unattributed **WIDTH** refuses **BODY AND GABLE**; an unattributed
   **HEIGHT** refuses the **BODY ONLY**. A gable reads a width and a rise
   and never a height — which is exactly why the gable lane leaked
   1,280.53 ft² on dart while all four heights correctly refused. Pinned
   in code as well as in prose: the two scopes are exercised against
   `walk_walls`.
3. **THE LIFT DID NOT ADVANCE GENERALITY, AS PREDICTED.** Corroboration
   needs a second read and neither foreign drafter has a first (dart
   NOT_ATTEMPTED 4/4, tanis NOT_ATTEMPTED 4/4). **Letrick's 1,402.62 ft²
   is the restoration of a house that was already working and must not be
   read as movement on the reads claim.** Pinned with
   `drafters_emitting() == 0`.
4. **THE FRONT OVERREAD IS EXPLAINED, AND TWO INDEPENDENT ROUTES AGREE.**
   A face with no projection has a body span that IS its silhouette, so it
   reads LONG: front +0.73 ft OVER, sides −0.59 and −0.33 UNDER. That is
   the SEND-110 residual shape — over on front/back, under on sides —
   reached from a different instrument (drawn outline vs x-ruler). The
   residual stays REGISTERED AS NAMED with the **fix still DECLINED**; it
   is closer to explained than it was, on two routes.
5. **TANIS LINE-WORK, WHERE IT STOPS PER FACE** — the whole §1/§2 finding,
   with the segment counts, the three re-OCR scales, the annotation counts
   and the open question, in the register rather than in a report only.

## 4. THE CLAIM, UNMOVED
`earned_claim()` = **FAILS_SAFE**. `drafters_emitting()` = **0**. The reads
claim is unearned, for the predicted reason: **neither foreign drafter
emits.** Dart stops at the CARVE on 4 of 4 faces; tanis carves 3 of 4 and
stops at the DATUM PAIR on every one of them.

## 5. STAMP
RECORDED: 2026-08-26 01:19 UTC · e774561 · CLEAN
RESULT: 2891 passed, 9 skipped, 7 warnings in 478.15s (0:07:58)
CENSUS: census pin GREEN — 0 PENDING_CONVERSION · INGRESS SMOKE: 4 passed
(+5 pins over SEND-129's 2886.)

Standing rules held: no proposal used evidence from another drawing, no
estimate influenced another, no job names in operative code, model heights
hypothesis-only for quantities. EST-886440 PROTECTED. 423 on every derived
write. Purity pin holds. Gable placement still noted-not-fixed. Symbols
placement still NOT AUTHORIZED.
