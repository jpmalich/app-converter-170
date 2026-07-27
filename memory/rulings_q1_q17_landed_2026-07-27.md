# RULINGS Q1–Q17 — LANDED + ACCEPTANCE RE-DERIVE (2026-07-27)
**All seventeen rulings from the money-layer sitting are CODE. Suite: 1444 passed, 0 failed. Derivation purity PINNED by test.**

## Acceptance — 3 Degree Rd re-derived under the new rules (the proof of the sitting)
Engine re-derivation from the estimate's stored `hover_measurements` through the same
contract → force-profile → assemble chain the endpoint runs (board_batten, waste 30%).

| Line | BEFORE (printed) | AFTER (new rules) | REAL | Verdict |
|---|---|---|---|---|
| 38 Series 4×10 Panel | 147 | **147** (Q17: 30% HOLDS) | 155 | −5.2% — logged as waste evidence #1; lift only on two-job confirmation |
| 440 4/4"×4" ISC | 11 | **row RETIRED** (Q12) | not used | **MATCH** — 540-4" is the ISC default now |
| 440 4/4"×8" fascia | 40 | **40** (Q16 per-segment; same here) | 45 | −11% residual = segment-level cut loss; Q16 flag rides the line |
| 540 5/4"×4" | 32 | **100** = wrap 32 + frieze 44 (Q10) + ISC 24 (Q12/Q13) | 142 | gap −110 → **−42**; with Q11 ruling (B&B base = NOTHING) the base-LF hypothesis is ruled OUT — remaining 42 sticks logged as open evidence |
| 190 battens | 212 | **423** (Q9: 8" o.c.) | 465 | gap −253 → **−42**; the `batten_wall_heights` flag still stands on Hover (height term = 0) — closing it closes the gap |
| Touch-up kits | 1 | **4** (Q15: 1/11 SQ/color) | 4 | **EXACT** |
| OSI caulk | 2 | **19** (Q15: 1/23 batten sticks) | 20 | −1 tube |
| J blocks / Mini splits | 8 / 2 | **8 / 2** | 8 / 2 | **EXACT** (unchanged calibration anchors) |
| 540 OSC 6" | 11 | **26** (Q13: per-corner min 1) | 19 | +7 — ruled conservative; cut-reuse only with PROVEN tracking |
| LP soffit | 16 pcs (308 sqft) | **vented 67 + closed 69 = 136 pcs = 2620 sqft** (Q14a: measured total governs; Closed row survives on measured basis) | 260 vinyl pcs ≈ 2600 sqft | **AREA MATCHES**; vinyl substitution row reads **262 ≈ 260** (Q14b: vinyl pulls via the vinyl list) |
| Tear-Off / Dumpster | absent | **rows present, qty 0, PENDING + readiness items** (Q1) | crew-set | as ruled |
| Porch ceilings | silent | **`porch_ceiling_implied` flag FIRES** (Q2: 4.2' implied vs 12" stated; flag-only) | — | as ruled |

**Materials modeled: the two biggest misses (soffit −244 pcs-equivalent, trim −110) collapse to −42/−42 residuals, both tied to named open flags — no invented scope anywhere.**

## Named deltas (fixtures + live estimates that moved)
- **Jon Casile (unprinted quote) — full before→after walk** (pinned in `test_casile_closeout.py`):
  battens 97→194 (Q9) +$1,907.02 · OSC 9→20 (Q13) +$2,988.59 · 540-4" 33→62 (Q10+Q12) +$994.70 ·
  440-4"×4" 3→0 (Q12, merged) · soffit V 11→14 + C 8→11 (Q14) +$477.99 · caulk 2→9 + touch-up 1→2 (Q15) +$159.17 ·
  Tear-Off/Dumpster rows appear qty-0 pending (Q1).
  **sub_mat 20,025.74 → 26,468.61; walk sell 30,610.77 → 40,459.16** (margin math unchanged).
- **261 Haugh pins**: 540-4" 33→62 (wrap 33 + frieze 23 + ISC 6) · OSC 9→20 per-corner.
- **Letrick (photo door)**: ISC re-SKU 440→540 reprices 2 sticks → total_sell 12,901.52 → **13,037.21** (+135.69).

## Where each ruling lives
Q1 `hover.py` spec presence rows + `lp_conventions.MISC_LABOR_ROWS` + readiness `qty_pending` items ·
Q2 `_hover_mapping_contract` flag ·
Q3 width-conditional coil divisor (≤10" → 100 LF/roll; >10" → 50) — catalog row NAME kept for key stability, note carries the rule ·
Q4 `fascia_rake_takeoff(dormer_fascia_lf)` + dormer-corner OSC pooling; non-priced dormer SKUs retired ·
Q5 photo door pairs `mezzo_openings` with its vero rows ·
Q6 `stories` set on photo (`_ai_story_count`) + blueprint (`story_count`) ·
Q7 `vent_count`/`shutter_count` wired on photo + blueprint ·
Q8 `color_tier` estimate field + selector (SettingsRow) + `_apply_color_tier` re-landing ·
Q9 `DEFAULT_BATTEN_SPACING_IN = 8` (BB_HELD closed) ·
Q10 frieze consumed (passthrough + spec + assemble; measured data never drops: soffit/frieze/drip/trim/vents/shutters all pass through) ·
Q11 pinned: LP B&B base = nothing (no starter, no trim, no J) ·
Q12 `ISC_TRIM_ITEM = 540 5/4"×4"`, merged row, one color group ·
Q13 per-corner whole-stick round-up min 1 (Hover OSC + ISC; pooled only when count missing, flagged) ·
Q14 `_soffit_total_split` proportional basis governs; Closed row survives measured basis; vinyl row pulls the total ·
Q15 caulk 1/23 batten sticks (B&B), touch-up 1/11 SQ/color ·
Q16 per-segment rounding where segments exist, pooled-flagged otherwise ·
Q17 30% holds — evidence register entry #1: 3 Degree Rd effective 37.7%.

## Derivation purity — PINNED
`test_derivation_purity_pin` (in `test_rulings_2026_07_27.py`): derivation modules import no DB layer;
same inputs → identical outputs; inputs never mutated. Real-job lists enter ONLY as ruling evidence.
