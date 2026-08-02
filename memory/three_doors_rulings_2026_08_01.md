# THREE DOORS — RULINGS LEDGER (Howard, 2026-08-01)
NOTHING BUILDS until all ten are ruled AND the Field × Door matrix is ruled.

## BANKED (7)
1. GABLE FACTOR = 0.70 — one sealed constant, all 3 doors, all 3 families. Delta check done: moves neither 261 Haugh nor 3 Degree (both Hover-door; zero blueprint runs exist).
2. LP-PAIR UNAPPLIED RUNS = PENDING, NOT DISCARDED — visibly flagged "not applied yet", never silently prices, never vanishes; dollars only on contractor apply. Live carriers today: EST-910869 (16 runs, siding-kind, applied-state unrecorded), EST-067615 (2), EST-510771 (1), EST-373526 (1), DEMO-LETRICK (1). All gov-bound LP estimates clean.
3. PHOTO DOOR JOINS SHARED REBUILD — existing photo estimates HOLD numbers, manual per-estimate trigger only, human-qty absolute.
4. CONFIDENCE GATE — build. Low-confidence photo reads flag loudly; cannot drive a dollar unseen.
5. DROPPED-FIELD REGISTER, ALL 3 DOORS — Class-B behavior: dropped measured field FAILS THE BUILD on blueprint + photo too.
6. SOURCE PROVIDES IT → ENGINE CONSUMES IT — fill-in boxes ONLY for what the source genuinely cannot see. FIELD × DOOR MATRIX (S-C / S-D / N-S) gates the build; Howard rules the fill-in list off it.
7. ROUND ONCE, AT THE ORDER LAYER — full precision end-to-end (9.583'), one rounding point where qty becomes orderable; composes with whole-units-at-sales-unit rule. NOTE: both AI aggregators currently round(x,1) at intake — dies in unification.

## PENDING RULINGS
- Finding 8 (photo starter eaves fallback) — presented at depth 2026-08-01, awaiting verdict.
- Finding 9 (silent <4ft height substitution) — trade call: (a) substitute + flag loudly vs (b) hold for human height.
- Finding 10 (minors a–d) + 10e window_bottom_width_total_lf false-CONSUMED register entry — trade call: (i) re-register NOT_CONSUMED vs (ii) name a real sill rule.
- Field × Door matrix fill-in-box list — delivered 2026-08-01, awaiting one-pass ruling.

## STANDING CONSTRAINTS
- 261 Haugh + 3 Degree byte-identical except named ruled-fix deltas, per estimate.
- No fourth copy of any math — three aggregation copies collapse to ONE.
- Byte-identical proof reported at END OF EACH BUILD STEP, not one green suite at the end.
- Spanish queued behind all accuracy work.

## BUILD ORDER (once ten ruled)
Ruling 2 pending-flag → aggregator unification (absorbs rulings 1, 3, 6, 7 + findings 6/7/8/10a–c) with ruling-5 registers as acceptance harness → ruling-4 confidence gate (absorbs finding 9).

## NEW DISCOVERY DURING MATRIX BUILD
- BLUEPRINT FOOTPRINT-PERIMETER KEY MISMATCH: blueprint aggregator stores measured perimeter as `_perimeter_lf`; the batten stacked-wall-height machinery reads `footprint_perimeter_ft` (lp_package_routes.py:1255). Blueprint-sourced LP estimates silently lose the measured batten term — S-D cell in the matrix.

## CLOSING RULINGS (all ten ruled, gates cleared)
- F8 starter: blueprint rule extends to photo (perimeter + engine door deduction). FIX-IT.
- F9: (a) substitute story-default + flag loudly via confidence gate.
- F10 a–d: fix-its in unification; (d) pending-flag surfaces BLUEPRINT runs too.
- 10e: option (ii) — wbw feeds FINISH TRIM, vinyl+Ascend only. Register corrects to real consumer.
- FINISH-TRIM FALLBACK SILL WIDTH = 3' (window_count × 3', old ×14 full-opening constant retired for the sill term). Formula = sills + top course; J-channel UNCHANGED at full perimeter. NAMED DELTA: 3 Degree vinyl 59 → ~32 pcs.
- FILL-IN BOXES: four, photo door only — soffit_sqft, drip_edge_lf, total_trim_sqft, frieze presence-toggle. All in trade-spec box. Hover/blueprint zero.
- FOOTPRINT PERIMETER KEY MISMATCH: own fix item — writer's key must equal reader's key, pinned.

## BUILD SEQUENCE (Howard, 2026-08-01) — report per step w/ byte-identical proof
1. ✅ DONE (commit 5e38c42, 2026-08-01): ONE aggregation copy — measure_staging.py. Gable 0.70 all doors · shared walk + buckets · door_count lands (photo+blueprint) · ONE paired openings builder · full precision at intake · blueprint sanity recompute rewired (own 0.5 copy retired). SUITE: 1703 passed, 1 skipped (RECORDED 2026-08-01 11:02 UTC · 5e38c42 · CLEAN). BYTE-IDENTICAL: 7/7 ground-truth SHAs unmoved (/app/memory/evidence/step1_before.json = step1_after.json). Ruled test-pin updates: blueprint gable delta 7.5→10.5 (0.70), intake-round pins → full precision. New seals: tests/test_three_doors_step1_2026_08_01.py.
2. NEXT: dropped-field register all 3 doors + land every S-D cell (blueprint 11, photo 5, hover wbw) incl. footprint key fix. Register ships GREEN.
3. Finish trim sills+top course (wbw primary, count×3' fallback), named delta 3 Degree 59→~32.
4. Photo → shared rebuild (HOLD existing, manual trigger) + starter unify + confidence gate (findings 4+9a).
5. Pending-not-discarded flag, photo AND blueprint runs.
6. Four photo fill-in boxes + eaves recompute + opening-basis unify.

## STEP 2 — DONE (commit 857265d, RECORDED 2026-08-01 11:52 UTC · CLEAN, 1712 passed)
- door_field_register.py: BLUEPRINT + PHOTO Class-B registers, shipped GREEN. Enforcement: tests/test_door_registers_2026_08_01.py (unregistered field FAILS, dropped field FAILS, detection-only rider).
- LANDED: blueprint prompt schema + aggregator now capture soffit_sqft, level/sloped_frieze_lf, drip_edge_lf, total_trim_sqft, footprint_area_sqft, address, opening_facade_assignments (R6 strict), wbw (schedule sill sum). FOOTPRINT KEY FIX: blueprint+photo write footprint_perimeter_ft (writer-key==reader-key pinned by test).
- PHOTO lands: outside/inside_corner_count from corner_locations (Q13 min-1-per-corner fires: 35LF/4 corners = 4 pcs not 3), footprint_perimeter_ft (wall-width sum), wbw.
- Hover wbw register entry corrected per 10(e) (fiction on record).
- BYTE-IDENTICAL: NONE moved (step2_after.json == step1_before.json shas).

## STEP 3 — DONE (commit ba03709, RECORDED 2026-08-01 12:10 UTC · CLEAN, 1718 passed)
- FINISH TRIM = sills + top course (vinyl+Ascend): wbw primary → per-window sill sum → count×3' fallback. FINISH_TRIM_SILL_LF_FALLBACK=3.0. J-channel UNCHANGED (full perimeter). Region-split context row renamed "window sills". Registers flipped CONSUMED.
- NAMED DELTAS (only Finish Trim rows moved, both derivation layers, everything else byte-identical): 3 Degree ×3 LP estimates 59→33 (measured wbw); Casile 51→23; 261 Haugh round-two 51→23; Haugh photo-crop 54→20. 3 Degree vinyl EST-979583 stored 59 HOLDS (no stored measurements; updates on re-import/re-derive).
- Seals: tests/test_finish_trim_sills_2026_08_01.py (named delta 59→32 pinned on vinyl-estimate figures; only-finish-trim-moved fence).

## REMAINING: none — build order complete.

## STEP 6 — DONE (RECORDED 2026-08-02 · CLEAN, 1739+2 passed 1 skipped)
- FOUR PHOTO FILL-IN BOXES, photo door ONLY: soffit ft² · drip edge LF · total trim ft² · frieze presence-toggle. ONE copy: measure_staging.fold_photo_fillins — inert unless the blob's _source == "photo"; a box only FILLS A HOLE (never overrides a measured value). Frieze is a toggle: LF derives from the measured runs (level = eaves, sloped = rakes) — no number re-typing.
- Fold points (both call the ONE copy, pinned): rebuild_lp_tab_lines (rederive/hover-lp-run/materialize) + _apply_contractor_waste (LP package path — tab/package parity).
- PUT cannot silent-strip (F2 class): EstimateIn declares the four fields (Optional-None, partial PUTs never clobber, negatives rejected) + useEstimate buildPayload carries them; projections at rederive/_load_run/materialize include them.
- UI: boxes live in the TRADE-SPEC BOX (SettingsRow), gated on est.hover_measurements._source === "photo". UI PASS verified live: render + values on a photo estimate; DO NOT render on hover (EST-853809 checked) — finding-6 re-typing defect impossible by construction. E2E: fill-ins survive PUT → rederive consumes (soffit 18 → 25 pcs on 250 ft² fill-in).
- Minor fix-its confirmed landed + sealed: 10a photo eaves recompute (non-gable walls only, shared eaves_from_walls) · 10c opening basis unified (schedule feeds counts AND ft²).
- BYTE-IDENTICAL: 7/7 SHAs unmoved — /app/memory/evidence/step6_before.json == step6_after.json (261 Haugh both kinds, 3 Degree ×3, Casile). Additive fields verified inert until typed.
- Seals: tests/test_photo_fillins_step6_2026_08_01.py (12 pins incl. photo-door-only, never-overrides, no-second-copy, PUT-strip, engine-consumes).
