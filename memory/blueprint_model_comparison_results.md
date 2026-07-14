# RESULTS — Blueprint validated-model controlled comparison
**Fired 2026-07-15 per pre-registration (blueprint_model_comparison_prereg.md).
All 6 runs declared before firing; all 6 scored; no cherry-picking.
Transport: BOTH arms on direct api.anthropic.com (cutover shipped first, same
transport as the photo pipeline — single-source doctrine). Token costs are
ACTUAL from direct-key usage telemetry, not estimates.**

Run IDs (in firing order, interleaved O/F to smooth time-of-day drift):
| # | Model | run_id | Wall clock | Input tok | Output tok | Cost |
|---|---|---|---|---|---|---|
| 1 | Opus 4.5 | 2a2e8a12… | 24.3 s | 20,195 | 1,181 | $0.1305 |
| 2 | Fable 5 | 144d22fb… | 85.0 s | 53,484 | 5,876 | $0.8286 |
| 3 | Opus 4.5 | a086a6a7… | 24.3 s | 20,195 | 1,218 | $0.1314 |
| 4 | Fable 5 | 9a746229… | 92.0 s | 53,484 | 6,581 | $0.8639 |
| 5 | Opus 4.5 | 9cef31b7… | 48.5 s | 20,195 | 1,240 | $0.1320 |
| 6 | Fable 5 | 67b2d0c3… | 78.8 s | 53,484 | 5,579 | $0.8138 |

Note: Fable's vision tokenizer charges 2.6× the input tokens for the SAME 10
cached pages (53,484 vs 20,195) — model-side image tokenization difference,
not a payload difference. Per-run cost ratio ≈ 6.3× ($0.83 vs $0.13).

## Amendment 2 — anchor integrity
All 6 runs read front/back = 54', left/right = 30', gables on left/right,
7/12 pitch, 8.75' computed rise. **Zero label/geometry contradictions.
No runs voided, no candidate disqualified.**

## Regression bar (must PASS ≥2 of 3 per candidate)
| Line | Opus 4.5 | Fable 5 |
|---|---|---|
| Pitch 7/12 printed | 3/3 PASS | 3/3 PASS |
| Gable rise 8.75 (pitch-computed) | 3/3 PASS | 3/3 PASS |
| Starter raw-perimeter basis (168 LF) | 3/3 PASS | 3/3 PASS |
| **Window count 10** | **0/3 FAIL (11, 11, 11)** | 3/3 PASS (10, 10, 10) |
| Placement attribution (0 defaulted) | 3/3 PASS | 3/3 PASS |
| Structured chase presence | 3/3 PASS | 3/3 PASS |
| Anchor integrity | 3/3 PASS | 3/3 PASS |

⚠ FINDING: the incumbent failed its own previously-PASS window-count line in
3/3 runs — a consistent extra "B" window (reads B×5 splitting across
elevations; schedule says B×4). The prior scored run (367b7397, proxy
transport) read 10. Whether this is transport-related, stochastic drift, or
schedule-splitting behavior is not resolvable from 3 runs.

## Residual lines (Amendment 1: challenger median must land OUTSIDE the incumbent's min-max span, on the improving side)
| Line (key) | Opus runs → median | Fable runs → median | Verdict |
|---|---|---|---|
| Siding area (2098.5) | −2.9%, −2.9%, +0.6% → **−2.9%** | −7.3%, −4.7%, +2.3% → **−4.7%** | **Fable WORSE beyond noise** (4.7% outside Opus's 0.6–2.9% abs-residual span, bad side) |
| Chase faces (145.5 ft²) | +23.7%, +23.7%, +73.2% → **+23.7%** | +16.8%, +55.3%, +40.9% → **+40.9%** | No beat (Fable median inside Opus span) |
| Corner walk OSC (4) | 6, 6, 6 → **6** | 4, 4, 4 → **4** | **Fable IMPROVES beyond noise** (exact key, outside [6,6]) |
| Door classes (1 entry + 1 slider; # misclassed) | 1, 2, 2 → **2** | 1, 1, 1 → **1** | No beat (Fable median = Opus's own min, not outside span) |

Door-class failure modes differ:
- Opus finds the 72" slider 3/3 but hallucinates extra doors in 2/3 runs
  (phantom 60" slider + 48" french on back).
- Fable NEVER finds the slider (3/3): reads it as a second 36×80 entry.

## Pre-registered decision rule applied
- (a) Regression bar: Fable clears 7/7; **Opus fails the window-count line**.
- (b) Fable improves **1 of 4** residual lines beyond noise (needs ≥2). FAIL.
- (c) Fable worsens siding area beyond noise. FAIL.

**Outcome per rule 3/4: challenger does NOT replace incumbent → Opus 4.5
stays**, with residuals logged as blueprint-path stochasticity under amber
handling and edit-and-rerun as the human path.

## Open items for Howard's ruling
1. Incumbent window over-read (11 vs 10, 3/3) is a NEW regression on a
   previously-PASS line, observed only on the direct transport. The strict
   bar says a bar-failing candidate "cannot win" — but incumbent-stays is
   the default state, not a win. Options: accept (amber/echo-check catches
   count deltas), or order a follow-up probe.
2. Cost/clock recorded, not a decision input per pre-registration: Fable is
   6.3× cost, ~3.4× wall clock per run.
3. Model override on the rerun endpoint: pre-registration says "removed or
   clamped after ruling" — awaiting the ruling to clamp.

Raw per-run JSON: /app/memory/bp_comparison_runs/run{1..6}_*.json
