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
