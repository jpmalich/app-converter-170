# WINDOW MARK B — INVESTIGATION REPORT (2026-08-08, investigate only — ruled)

## The ruling this ran under
"28x64 IS CORRECT. DO NOT CHANGE THE CONVERTER. The suspect number is
the 28x48 — a different mark, a misread of the schedule table, or a
genuine inconsistency on the plans. Find out which. REPORT THE
DISAGREEMENT. Change nothing."

**Nothing was changed.** The converter was verified, not touched.

## Converter verification (all correct, width-first convention)
| input | parse |
|---|---|
| SH 2-4_5-4 | 28 × 64 |
| SH 2-4_3-4 | 28 × 40 |
| 3-0_5-0 | 36 × 60 |
| 3-0_5-6 | 36 × 66 |
| SH 3-0_4-0 | 36 × 48 |

## What the stored Boni reads actually hold for mark B
| run | date | mark B transcription | carried size |
|---|---|---|---|
| e633ca8d | 8-7 16:01 (pre-discipline) | notes: "SH 2-4_5-4 (B)... B=28x64 approximated to standard 38x60" | 38 × 60 (snapped — behavior since banned) |
| db686693 | 8-7 19:51 | printed_size "2'-4\" x 3'-4\"" | 28 × 40 |
| a6e723af | 8-8 10:47 | printed_size "SH 2-4_3-4" (right + left elevations) | 28 × 40 |

## The finding — THREE sources, THREE answers
1. **The 8-7 morning read** transcribed the schedule cell for B as
   **SH 2-4_5-4 → 28×64**. This is where the 28×64 Howard graded came
   from. (That same read then snapped it to 38×60 — the catalog-snap
   behavior killed by the printed-dims-SACRED ruling.)
2. **The two newest reads independently agree** on **SH 2-4_3-4 → 28×40**
   for mark B. Two reads agreeing is STABILITY, not correctness.
3. **Howard reports the plan prints 28×48** beside mark B.

No stored read holds 28×48 for mark B. `5-4` vs `3-4` is a one-glyph
vision disagreement on a scan — exactly the class the determinism gate
exists to surface, and this read pair would have flagged it.

## What it needs
A human eye on the schedule cell for mark B (sheets 6–7 per the 8-7
notes) — or a tape on the opening. The reads disagree across runs; the
window_size_parse_mismatch checker is clean on each run individually
because each run's parse matches its own transcription. The instability
is BETWEEN runs, which only the two-read gate (now built) can catch.

## PURITY
None of 28×48 / 28×64 / 28×40 was made a constant, default, or test
target. The converter's pins use synthetic strings.

---

# RESOLUTION + PROVENANCE CORRECTION (Howard read sheet 6, 2026-08-08)

## PROVENANCE CORRECTION (owned)
This report's line "Howard reports the plan prints 28×48" was WRONG
ATTRIBUTION. The 28×48 came off the app's own 4:06 PM read-back card
(run e633ca8d era) — an app-generated number attributed to a human.
It was never three sources disagreeing; it was THREE APP READS
disagreeing with no human anywhere in it. RULED: never attribute a
number to Howard that came out of the app. A figure whose origin cannot
be named has no source.

## MARK B RESOLVED FROM THE PRINTED SHEET (Howard's transcription)
Sheet 6 window schedule:
  A · SH 3-0_5-0 · SIZE 2'-11 1/2" x 4'-11 1/2" · count 2 · egress yes
  B · SH 3-0_4-0 · SIZE 2'-11 1/2" x 3'-11 1/2" · count 1 · egress NO
  C · SH 3-0_5-6 · SIZE 2'-11 1/2" x 5'-5 1/2" · count 5 · egress yes
All Pella Encompass Single Hung. ALL THREE APP READS WERE WRONG on B
(2-4_5-4 / 2-4_3-4 / 28x48 — none printed). Every read also missed the
width glyph: all three marks are 3-0 wide. The converter was never the
problem; the transcription was.

## NEW RULING: THE SIZE COLUMN GOVERNS
The schedule prints the real dimension BESIDE the code — every unit
half an inch under nominal (35.5×59.5, 35.5×47.5, 35.5×65.5). The
product code is a FAMILY LABEL, not a dimension. Read the SIZE column;
use the code only to identify the unit. (Printed-dims-sacred was being
violated by converting a label.)

## SHEET 7 ANSWERED (agent vision transcription of the RETAINED page
image bp_05f61f9d... — this is an AI read of a scan, named as such,
not tape):
  Sheet title: SECOND FLOOR PLAN. It carries its OWN schedules.
  WINDOW SCHEDULE: A · SH 3-0_5-0 · 2'-11 1/2" x 4'-11 1/2" · count 7
                   D · SH 2-4_3-6 · 2'-3 1/4" x 3'-5 1/2" · count 1
  DOOR SCHEDULE: marks 5–15, ALL "H DWL CORE" (hollow core) interior.
  → Two-sheet schedule total: 8 (first) + 8 (second) = 16 units.
  → A mark D EXISTS that no app read ever carried; D is the only 2-4
    family on the job — consistent with the reads' 2-4 glyph confusion
    on B, reported as observation only.
  → App reads reported 21–28 total: still ABOVE the 16 the schedules
    hold. DISAGREEMENT REPORTED — needs Howard's eye on sheet 7 to
    confirm my transcription before the count is treated as resolved.

## PURITY
SH 3-0_4-0 · 35.5×47.5 · 35.5×59.5 · 35.5×65.5 · 192×96 · 108×96 ·
counts 2/1/5 · sheet-7 rows — evidence for rulings, never constants,
defaults, or assertion targets.
