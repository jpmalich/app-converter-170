# POST-SEPTEMBER PROPOSAL — BLUEPRINT VERIFICATION READ-BACK (sized 2026-08-06, REPORT ONLY, nothing built)
Howard's order: after a blueprint import, the app produces a VERIFICATION SHEET showing WHERE it placed what it read — trust-through-visible-honesty applied to the blueprint door. Every Boni geometry miss (dropped garage gable, phantom rear porch, missing garage corners) would have been visible at a glance.

## CONFIRMATIONS (both hold)
1. **The EL-1..EL-4 elevation engine CAN be pointed at the blueprint door.** Mechanics: `routes/elevation_sheets.py` reads `ai_measure_runs.result.raw_ai` — walls[] (label/width/height/gable_triangle_height_ft) is the SAME schema shape `ai_blueprint_runs.result.raw_ai` emits, and blueprint openings already carry the `elevation` tag + schedule dims. What it takes: a `source=blueprint` run-selector on the sheet endpoint; skip the photo-only binders (dormer photo-chains, chase position ladders); openings bind by elevation tag and fall to the EXISTING even-spacing + "POSITION UNVERIFIED" dashed-red chip state (blueprint reads carry no along_wall_ft — that render state was built for exactly this). The tape/sealed-key ladder is estimate-keyed and rides unchanged.
2. **Schematic read-back IS the cheaper path — confirmed.** Pixel-annotating the uploaded PDF requires per-page coordinate returns from the model (unreliable on dense sheets), scale registration per blueprint format, and breaks on every new format. The schematic renders the app's OWN understanding — which is the thing being verified — format-agnostic, print-native, and the flags are first-class. Est. 3-4× cheaper than PDF annotation and strictly more honest.

## MVP CUT — "BLUEPRINT READ-BACK CARD" (would have caught all three Boni misses; build FIRST)
No elevation engine needed at all — a schematic data panel on the blueprint modal + print:
1. **ROOF PLANE CENSUS TABLE**: one row per plane (label · eave_lf · rake_lf · gable_ends · porch ft²), plane-sum totals vs wall-derived shown side by side. LOUD flags: `rake_lf = 0` on a non-porch plane ("GABLE-BLIND PLANE — verify the elevation"); "NO GARAGE PLANE" banner when garage doors/area-table evidence exists without a garage entry (fed by the existing `_roof_pass_needed` predicate — already written and pinned). → catches the dropped garage gable.
2. **CORNER LEDGER**: outside/inside counts + the invariant check (out − in = 4) displayed pass/fail; corner LF with basis chip ("per-corner summed" vs "count × avg — AVERAGED, verify"). → catches 9-vs-11.
3. **PORCH TAG**: porch plane present/absent + ceiling ft² + corroboration chip ("printed area table 99 ft²" vs "ASSUMED"). A ceiling without a plane, or a plane without printed corroboration, flags. → catches the phantom 150.
4. **HONESTY FLAG RAIL**: every ASSUMED/defaulted/low-confidence read inline (pitch source, overhang default, `_roof_pass` accepted-merge provenance — already stamped on the run doc).
SIZE: **S — one session.** ~1 backend endpoint (~150 lines: read `ai_blueprint_runs.raw_ai`, compute flags — most predicates already exist), one React panel (~250 lines, shadcn tables + chips, print-safe), pins (~150 lines, pure flag-rule tests). No schema change, no new AI phase.

## PHASE 2 — ELEVATION ENGINE FED BY THE BLUEPRINT READ
Per-elevation EL sheets (front/right/back/left) drawn from the blueprint walls + schedule openings placed on their tagged elevation, source chips reading "blueprint run <id>". SIZE: **M — 1-2 sessions.** Cost drivers: run-source switch + photo-binder skips (small), opening binder for schedule marks (small), regression pins that photo-door sheets stay byte-identical (the real work).

## PHASE 3 (optional) — PER-CORNER HEIGHTS ON THE SHEETS
Schema slot `corner_heights[]` (the walk already reads per-corner heights, it just sums them) + corner ticks on the EL sheets with each corner's own height chip. SIZE: **S.**

## BUILD ORDER WHEN AUTHORIZED: MVP card → Phase 2 sheets → Phase 3 corners. DEMO-LOCKED UNTIL HOWARD AUTHORIZES POST-SEPTEMBER.
