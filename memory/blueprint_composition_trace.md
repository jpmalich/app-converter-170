# BLUEPRINT APPLY-TAKEOFF COMPOSITION TRACE (2026-07-14)

Ordered deliverable (1) of the shakedown findings — the code path the
Blueprint Apply-Takeoff actually composes through today, and why the LP
single-source cut (iter97/iter100) did not cover it. Style of record:
`lp_legacy_pricing_trace.json`. Evidence run: `e4afda3a64a54439b02b5c609dda0b69`
(Howard's shakedown upload, 2026-07-14 20:41 UTC, EST-510771 / Letrick).

## A. The contaminated path, line by line

1. **Worker composes RAW legacy lines** — `routes/ai_blueprint.py:1043`
   `lines = _build_lines(measurements)` → `routes/hover.py:1744`.
   `_build_lines` walks `HOVER_MAPPING_SPEC` and emits ALL tabs:
   - `vinyl` tab: J-Channel (hover.py J-channel spec), Finish Trim, Coil,
     "Vinyl 12.5'" outside/inside corner + starter formulas (hover.py:719-760)
   - `ascend` tab: parallel vinyl-era formulas
   - `lp_smart` tab: the LP composition table entries (hover.py:557-742) —
     RAW, without any of the engine's ruled guards.

2. **No engine wrapper** — the ruled LP composition source is
   `lp_package.assemble_lp_package` (lp_package.py:166), which ALSO starts
   from `_build_lines` but then applies, in order:
   - `override_flag(True)` + lp_smart-tab filter
   - **COMPOSITION GUARD** `lp_composition_bugs()` — strips J-channel /
     finish trim / coil (ruled iter97)
   - **PER-SYSTEM TABLE** — removes the rake-driven Closed-soffit row
     (LP soffit is EAVES-ONLY; rakes carry 440 rake boards)
   - **whole-piece rounding at the SKU level, everywhere**
   - C4 conventions (corner locations → per-location stick doctrine, etc.)
   The blueprint worker consumes `_build_lines` OUTPUT DIRECTLY — every one
   of those guards is bypassed. That is the entire defect: not the spec
   table, but raw consumption outside the engine.

3. **Frontend Apply merges all three tabs onto the LP estimate** —
   `BlueprintMeasureButton.jsx::applyResult` (line ~348):
   `SIDING_TABS_FOR_KIND = kind === "siding" ? {vinyl, ascend} : {vinyl, ascend, lp_smart}`.
   EST-510771 is `kind: "lp_smart"` → the vinyl J-Channel 18 pcs, Finish
   Trim 22 pcs, Coil 1.9 rolls AND the raw lp_smart rows all merge into
   `est.lines`. (The iter78z++++ LP-row drop only protects SIDING-kind
   estimates — the inverse direction was never guarded.)

4. **Double waste + fractional pieces** — `applyResult` runs
   `bakeWasteIntoLines(sourceLines, est.waste_pct)` (wasteLogic.js:123)
   with the estimate's default `waste_pct: 20`. The LP lap spec ALREADY
   bakes ×1.10 inside the formula (`lp_formulas.lap_pieces` =
   ceil(sqft ÷ 9.17 × 1.10), hover.py:568). 20% is then applied ON TOP
   → double waste. `bakeWasteIntoLines` rounds to the nearest 0.5 unit
   → the 13.5 / 14.5 PCS fractional orders (whole-stick rounding lives
   in the engine the path never calls).

5. **Legacy-spec convention bugs riding along** (all die with the cut):
   - Closed soffit computed from rakes (raw spec row; engine's per-system
     table removes it — LP is eaves-only)
   - ISC merged into the 440 horizontal-runs formula
     (hover.py:594-604 — `(eaves + rakes) ÷ 16` labelled "Inside corners
     + horizontal runs"; the engine composes ISC per-location per C4)

## B. Why the LP single-source cut didn't cover it

The iter97/iter100 cut governed the DERIVED-PACKAGE SURFACES: the LP
Material List panel, the customer quote composition
(EstimateEditor.jsx:138-176 — package governs, stored lines deduped),
the CSV, freezes. It never governed the APPLY-MERGE INGESTION paths —
`BlueprintMeasureButton.applyResult` and the AI-Measure `onApply` merge
in `JobInfoPanel.jsx:273-336` (same tab-set, same waste-bake) both
pre-date the cut and still write raw `_build_lines` output into
`est.lines`. On LP-native estimates the AI flow never exercises Apply in
practice (the panel derives live from the run), so the gap stayed
invisible until the blueprint shakedown pressed the Apply preview.

Secondary structural gap: `lp_package_routes._load_run` reads
`ai_measure_runs` only — a blueprint takeoff on an LP estimate had NO
route into the engine even if the frontend had wanted one. That is the
missing plumbing the cut has to add, plus: blueprint runs carry a 24-hour
TTL, so an applied blueprint takeoff must archive its run
(`run_archive.archive_run_for_artifact`) or the panel dies next morning
— the "no persistent artifact references a reapable run" pin applies.

## C. Extraction gaps (separate class — blueprint-side C4 analogues)

From the shakedown run's payload (all confirmed in the stored run doc):
- `starter_lf: 108` — the PROMPT ITSELF encodes the wrong convention
  ("≈ eaves_lf", ai_blueprint.py:181) and the aggregator falls back to
  eaves (ai_blueprint.py:480). Convention: perimeter − 3' per entry door
  (key: 168 − 3 = 165).
- Gable `gable_triangle_height_ft: 8.5` — drawing-scaled; NO pitch field
  exists in the extraction schema. 30' gable end at 7/12 → rise = 8.75'.
  (June finding, still unfixed on this path.)
- No chase/appendage schema at all → chase faces (~145.5 ft²: outer
  47.97 + sides 97.56) absent from siding area, AND chimney above-
  roofline edges absent from OSC LF (run: 6 corners × 9.5' = 57 LF;
  key: 8 edges incl. 2 full-height 18.91' + 2 above-roofline).
- Doors: run reads E1 + E2 both `entry 36×80`; the key has 1 entry +
  1 patio slider. Logged against the KNOWN class residual (photo path
  had the same misclass — Phase 3 §4). Class residual, not a new defect.

## D. The cut (ordered deliverable 2) — design of record

One composition source, pinned:
1. `_load_run` considers blueprint runs (latest done across
   `ai_measure_runs` + `ai_blueprint_runs`, fixture fallback preserved)
   → blueprint-applied LP takeoffs derive through `assemble_lp_package`
   + C4 exactly like AI Measure.
2. Frontend Apply on `lp_smart`-kind estimates merges NO composition
   lines from ANY importer (blueprint + AI Measure onApply): only
   `hover_measurements`, openings routing, drawings. The engine-derived
   panel is the material list; est.lines keeps contractor service lines
   only (iter100 model, now enforced at ingestion).
3. Blueprint Apply on an LP estimate archives the run
   (reason `blueprint-apply`) — kills the 24h-TTL dependency.
4. Blueprint preview for lp_smart-kind stops showing raw legacy lines
   (the contaminated table Howard screenshotted) — states that
   composition derives through the LP engine on Apply.
5. Waste: LP lines never pass `bakeWasteIntoLines` on any path (the cut
   removes the only route); engine waste scope stays as ruled (10% area
   lines inside formulas; whole-stick rounding as the sole stick
   allowance). Vinyl-kind estimates keep contractor waste_pct behavior
   unchanged.
6. Mixed-fixture pin extends: blueprint-sourced LP derivation contains
   no cross-domain items, no fractional quantities, soffit eaves-only —
   same assertions the iter97 pins make for the hover/AI path.

## E. ADDENDUM — 3D-layer findings (6)(7)(8), same fork

6. **Pitch 6/12 badged BLUEPRINT (prints say 7/12)** — NOT a regression;
   the June-era fork never received the C2 integer-ladder fix. Two
   compounding causes: (a) the blueprint schema had NO pitch field at
   all — the 3D derives pitch from gable height: 8.5 (itself the
   drawing-scaled under-read) × 24 ÷ 30 = 6.8; (b) the FRONTEND ladder
   `ROOF_PITCHES = [4,6,8,10,12]` (HouseModel3D.jsx:31, pre-C2
   even-only) snapped 6.8 → 6. The photo path's C2 fix
   (`pitch_ratio_observed`, integer 3–14, ai_measure.py:3645) never
   reached either layer. Badge defect: derived pitch wore the green
   "Blueprint" print-authority badge (HouseModel3D.jsx:1650-1660).
   FIX: integer ladder 3–14; printed `roof_pitch` extracted and
   preferred (`pitchSource: "printed"`, green); derived-on-blueprint
   badges AMBER "Derived — verify"; never print-confident for a
   computed value.
7. **All 12 openings on the front wall** — `_aggregate_to_hover_shape`
   hardcoded `"wall": "front"` for every schedule row
   (ai_blueprint.py:668,684 pre-fix; the comment admitted it).
   CONFIRMED RENDER-ONLY: per-wall siding math (`_per_elevation_
   breakdown`) never consumes opening walls; composition uses global
   counts; the "Openings: 12" panel row is the same render payload's
   count — no math contamination. FIX: schema `elevation` per
   window/door row (schedule mark matched to elevation sheets);
   aggregator maps + flags (`placement_source`, `_opening_placement_
   defaulted`); panel shows an amber note when placement was defaulted
   — flagged, never silent.
8. **Chase renders malformed** — the appendage renderer expects
   C3/C4-shaped payloads (corner locators + attributed faces) the
   blueprint path never produces. FIX: blueprint runs render from the
   new STRUCTURED `raw_ai.appendages` payload (printed dims +
   `position_frac` from the elevation); structured payload absent →
   NOTHING rendered (honest absence); the photo-shaped derivation is
   never fed blueprint payloads.
