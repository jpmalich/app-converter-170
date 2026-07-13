# C4: COMPOSITION CONFORMANCE — PRE-REGISTERED CANDIDATE REPORT (2026-07-13)

**Candidate:** C4 (5 fixes, all from already-ruled conventions). Code changes completed BEFORE the e2e run fired; code frozen during the run.

## Pre-C4 question — answered first
**Do runs extract stepped-wall segments?** NO. Each wall carries ONE consensus `height_ft` (per-photo readings reconcile to a single value; no per-segment/staircase structure exists in the payload). → **Stepped underread logs as extraction residual**, field-verified via ambers. NOT added to C4.
**Chase perception:** YES — walls carry `accent_profiles` with the chase and an `approx_sqft` (this run: 160 ft² vs key 145.5). Perception existed without attribution → fix #2 was viable at the composition layer.

## The five fixes (all shipped)
1. **Gable ×0.7** (`routes/ai_measure.py`): gable area = 0.7 × width × triangle height (ruled angle-cut coverage), replacing true-triangle ÷2.
2. **Appendage attribution** (`routes/ai_measure.py`): accent-profile faces marked chase/chimney/bump/cantilever enter the siding aggregate; exposed as `_ai_appendage_sqft` + `_ai_appendage_faces`.
3. **OSC feature pooling** (`lp_package.py`): pooling scope = the physical FEATURE. Singleton house corners = 1 stick each (≤16'); an appendage's edges pool internally — full sticks per >16' edge + ceil(pooled remainders incl. whole sub-16' edges ÷ 16). Per-location stick-starts within a feature: rejected doctrine, pin updated. Chimney fixture (2×18.91 + 2×8.59) = 4 sticks — pinned (`test_osc_chimney_key_fixture_c4`). Six-ruling splice example (two 18.5' chase corners = 3) still holds — pin preserved.
4. **Waste scope** (`lp_conventions.py`, `lp_package.py`): % waste on AREA-derived lines only (lap ×1.10, soffit ×1.10). Stick-count lines (fascia/rake, corners, wrap trim) get whole-stick rounding as their entire allowance — ×1.10 removed from fascia and the substitution re-derive path.
5. **Starter entry deduction** (`lp_package.py`): start-course − Σ entry-class door widths (schedule widths; 3'/door fallback); sliders sit on starter — no deduction.

## Pass criterion 1 — LAYER B on key geometry: 9/9 within ±3%
| Line | Key | App rules on key geometry | Δ | Verdict |
|---|---|---|---|---|
| 38 Series Lap | 255 | 252 | −1.2% | PASS |
| 540 OSC | 8 | **8** (4 house singletons + chimney feature 4) | 0% | PASS (was 9) |
| 440 4" ISC | 2 | 2 | 0% | PASS |
| 540 Trim | 12 | 12 (177 LF÷16) | 0% | PASS |
| 440 8" fascia | 12 | **12** (177.6÷16, no cushion) | 0% | PASS (was 13) |
| Soffit | 108 LF | 6 pcs from 108 LF | basis | PASS |
| Starter | 165 LF / 4 bd | **165** (168−3' entry) / 4 bd | 0% | PASS |
| Composition absences | no J-channel/finish trim/coil | none derived | — | PASS |
| Boards from area | 255 | 252 | −1.2% | PASS |

## Pass criterion 2 — end-to-end re-run, both layers re-scored
**Run provenance:** run_id `4a009e93eb5348c08cc26bfb935675ce`, created 2026-07-13 19:13:25 UTC, done, valid; measurement hash `79c52e6f6d20c678`; package hash `e26b1c00b4afb7cd`; artifact `/app/memory/letrick_phase3_run_4a009e93.json`. One in flight; fired AFTER all C4 edits.

LAYER A (extraction vs key): area **2,147.6 vs 2,098.5 = +2.3% PASS** (was −19.6%; gable 375.9 vs 367.5; appendage 160 attributed vs 145.5); eaves 108=108; rakes 70.0 vs 69.6 (+0.6%); starter LF net 162 vs 165 (−1.8% PASS); **residuals persist:** windows 9 vs 10, back slider → entry class, chimney above-roofline OSC edges undetected (6 locations vs key's 8-edge inventory; this run also saw a rear bump-out corner — run-to-run inventory variance logged).

E2E per-line (±3%):
| Line | Key | App e2e | Δ% | Verdict | Class |
|---|---|---|---|---|---|
| 38 Series Lap | 255 | **258** | **+1.2%** | **PASS** (was −20.4%) | — |
| 540 OSC | 8 | 6 | −25.0% | FAIL | extraction (edge inventory; Layer B passes) |
| 440 4" ISC | 2 | 2 | 0% | PASS (1 amber — reconciled-to-residual) | — |
| 540 Trim | 12 | 11 | −8.3% | FAIL | extraction (window 9 vs 10 + slider class; Layer B passes) |
| 440 8" fascia | 12 | **12** | **0%** | **PASS** (was +8.3%) | — |
| Soffit | 108 LF | 6 pcs | basis | PASS | — |
| Starter | 165/4 bd | 162/4 bd | −1.8%/0% | **PASS** (both) | — |
| Composition | absences | clean | — | PASS | — |

**E2E aggregate (recorded, no vote): 6 pass · 2 fail — both remaining fails are extraction-class, Layer B clean on both.**

## Pass criterion 3 — red-house regression
Full backend suite: **854 passed, 1 skipped** including red-house fixtures (`test_roof_type_material_math`, tape checks, gable demotion, two-phase pipeline) and all LP pins. Pins superseded by the ruling were updated WITH provenance (iter93 OSC feature pooling; iter94 fascia no-waste; starter 168−6=162 on the Letrick fixture).

## September framing numbers (per the ruling — never blended)
- **Conventions-on-verified-geometry:** 9/9 within ±3% (7 exact, lap −1.2%).
- **End-to-end photos-to-order:** 6/8 within ±3%; the 2 misses are extraction inventory (window count, appendage edges) — amber field-verify flags do the safety work.

**Gate:** Phase 4 flag-flip still NOT executed — awaits Howard's ruling on C4. Amber field-verify checklist ships immediately after that ruling, as approved.
