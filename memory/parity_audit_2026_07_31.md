# PARITY AUDIT — ONE MECHANIC, THREE FAMILIES (2026-07-31, report only)

## THE LIVE CASE — ANSWERED
**NO — a vinyl user CANNOT set fascia width.** The control is inside the
`est.kind === "lp_smart"` block (SettingsRow.jsx:250). The vinyl/Ascend `.019
Coil` divisor reads `_fascia_width_in` (hover.py:1331-1333: ≤10" → 100 LF/roll,
>10" → 50 LF/roll). On a siding-kind estimate the value is unreachable in the UI
AND has no fold path even via raw API — the only two places that fold
`est.fascia_width_in` → `_fascia_width_in` are `rebuild_lp_tab_lines`
(hover.py:2769) and `_apply_contractor_waste` (lp_package_routes.py:330), both
reachable only through LP-gated endpoints (hover-lp-run 400s on kind!=lp_smart at
hover.py:2972; materialize at lp_package_routes.py:636). Vinyl coil coverage is
permanently the 8" default. **F2 is fixed for exactly one family.**

## THE ASSUMPTION — CORRECTED
The app today is NOT one-mechanic-three-families. The single structural cause of
most divergence: **vinyl and Ascend have no server rebuild path.** Every spec
fold, catalog bind, human-qty guard, whole-unit reseal, flag-checklist
consumption and family-zeroing lives inside `rebuild_lp_tab_lines` /
`_apply_contractor_waste` — both LP-gated. Vinyl/Ascend derive once at import
(worker has no estimate context beyond overhang) and are then frozen except for
one client-side hook. Step 2 (re-derive for vinyl AND Ascend) is the keystone
that closes most ABSENT cells below.

## THE PARITY TABLE
Kinds: Vinyl + Ascend live on `kind="siding"` (tabs vinyl/ascend); LP on
`kind="lp_smart"` (tabsConfig.js).

| Mechanic | Vinyl | Ascend | LP SmartSide | Evidence |
|---|---|---|---|---|
| Intake composition (facade default at import) | PRESENT | PRESENT | PRESENT | shared worker `_compose_facade_default_into`, hover.py:3110 |
| Rebuild path (server re-derive) | **ABSENT** | **ABSENT** | PRESENT | hover-lp-run kind gate hover.py:2972; materialize gate lp_package_routes.py:636 |
| Waste application — field-driven, at apply | PRESENT | **DEFECT D2** | PRESENT | one emitter wasteLogic.js:87 + backend mirror hover.py:2711; Ascend "RainDrop" misses BOTH classifiers (wasteLogic.js:60, hover.py:2704) |
| Waste application — on stored estimates (recompute) | PRESENT (waste-% field + Recompute button) | PRESENT (same, minus D2 row) | PRESENT (+ rebuild) | wasteLogic.js:120,149 |
| Length-cut opt-out (`waste_included`) | PRESENT (OSC/ISC/starter/finish/J/soffit-J all flagged) | PRESENT (OSC/starter/finish/J; ISC retired by ruling) | PRESENT (440/540/190/OSC/soffit; 38-lap conditional) | register census appended below |
| Whole-unit rounding — at apply | PRESENT | PRESENT | PRESENT | bakeWasteIntoLines rounds every fractional line, wasteLogic.js:99-115 |
| Whole-unit rounding — stored-estimate repair | **ABSENT** | **ABSENT** | PRESENT | `_bake_tab_waste` only reachable via LP rebuild; the 26 fractional lines / 11 estimates stay frozen until step 2 |
| Spec: overhang_in | PRESENT* | PRESENT* | PRESENT | import param hover.py:3105 + client hook; LP also server fold hover.py:2756. *hook defects D4/D5 |
| Spec: porch_ceilings | PRESENT* | PRESENT* | PRESENT | hook (all kinds) + LP server fold hover.py:2750 |
| Spec: fascia_width_in | **ABSENT = DEFECT D1** | **ABSENT = DEFECT D1** | PRESENT | consumer exists for vinyl/ascend (.019 coil hover.py:1331) but field unreachable |
| Spec: batten_spacing_in | no consumer | **NEEDS RULING R2** (Ascend B&B 12" SKU exists, no batten derivation) | PRESENT | hover.py:2767 |
| Spec: panel_size | DIFFERENT-BY-NATURE (rule it, R4) | DIFFERENT-BY-NATURE (R4) | PRESENT | 38-Series-only SKU concept |
| Spec: wrap_trim_width_in | DIFFERENT-BY-NATURE (R4 — vinyl wraps with coil) | same | PRESENT | 540-Series-only |
| Spec: shake_reveal_in | **NEEDS RULING R3** (vinyl shake rows exist in catalog, no emitter) | no shake SKU | PRESENT | catalog_seed.py:159 "Pelican Bay Shake Starter" |
| Spec: color_tier | PRESENT | DIFFERENT-BY-RULING (named: Howard 2026-07-28, no tiers) | DIFFERENT-BY-RULING (same) | SettingsRow.jsx:202 |
| Spec: lp_soffit_type | DIFFERENT-BY-NATURE (single Charter Oak row) | same | PRESENT | two-SKU LP soffit split |
| Trade-spec box visibility | overhang+porch+tier only | overhang+porch only | full | SettingsRow.jsx:250 `kind==="lp_smart"` gate — carries D1 |
| SKU price binding | PRESENT (string-keyed) | PRESENT (string-keyed) | PRESENT (string-keyed) | editor catalog merge useEstimate.js:92-118; LP rebuild bind hover.py:2857-2877 — shared fragility, the parked ID-binding task |
| Human-qty survival — re-import/apply | **ABSENT = DEFECT D3** | **ABSENT = DEFECT D3** | PRESENT | merge overwrites qty with no qty_src check HoverImportButton.jsx:404-413; LP rebuild preserves hover.py:2848-2853 |
| Human-qty survival — client recalc hook | **DEFECT D4** | **DEFECT D4** | **DEFECT D4** | useRecalcSoffitOnOverhang.js:135-141 overwrites qty with no qty_src check |
| Flag tier registry | PRESENT | PRESENT | PRESENT | gates.py GATE_TIERS/tier_for — unassigned flag fails the suite, family-agnostic |
| Quote gate (email/PDF/freeze block) | PRESENT | PRESENT | PRESENT | evaluate_gates kind-agnostic; assert_quote_gate on email.py:29,119 |
| Order gate (release enforcement) | **ABSENT = DEFECT D6** | **ABSENT = DEFECT D6** | PRESENT | order items sourced from lp_package_preview → needs an LP run → vinyl/ascend order gate evaluates EMPTY; order-release passes trivially |
| Flag checklist (corner correction, ceiling dedup, taped heights) | **DEFECT D7** — closable, consumed nowhere | same | PRESENT | endpoint not kind-gated (lp_package_routes.py:1429) but all consumers are LP paths |
| Detectors: Hover field-consumption register (Class B) | PRESENT | PRESENT | PRESENT | hover_field_register.py — field-level, shared pipeline |
| Detectors: import sanity checks + silent-zero verification | PRESENT | PRESENT | PRESENT | hover.py:3124-3179, shared worker |
| Detectors: suite acceptance table | PRESENT (added on demand) | PRESENT (added on demand) | PRESENT | test_acceptance_four_column_2026_07_28.py — step 1's end-to-end test adds the family axis permanently |

## NEW DEFECTS FOUND BY THIS AUDIT (named)
- **D1 — Fascia width unreachable on vinyl/Ascend** while governing their .019
  coil divisor. The live case. F2 fixed for one family.
- **D2 — Ascend RainDrop gets NO field waste.** Catalog/register row is
  `RainDrop` (hover.py:1216, catalog_seed.py:409); both classifiers match only
  `"house wrap"`/`"raindrop house wrap"`. Vinyl's House Wrap wastes; Ascend's
  does not. Same class as the six, seventh instance.
- **D3 — Re-import clobbers human-typed quantities on vinyl/Ascend.** The apply
  merge writes `qty: ln.qty` unconditionally on existing rows; only the
  zero-family path checks `qty_src`. Violates the sealed
  human-overrides-are-absolute doctrine. (LP is shielded only because the server
  rebuild supersedes the merge.)
- **D4 — Overhang/porch recalc hook overwrites qty with no `qty_src` check** —
  all three families (useRecalcSoffitOnOverhang.js:135-141).
- **D5 — Second waste emitter in the hook.** `LP_WASTE = 1.10` hard-coded into
  LP soffit recalc (line 41,72) while Charter Oak recalc applies none — both
  diverge from the sealed one-emitter/field-only rule and neither maintains
  `raw_qty`.
- **D6 — Order gate is empty for vinyl/Ascend** — release never blocks.
- **D7 — Corner-count correction (walked counts) has no vinyl/Ascend consumer**
  though OSC/ISC counts drive vinyl corner rows.

## RULINGS REQUESTED
- R1: Fascia width joins the trade-spec box on siding-kind (fix rides step 2's
  vinyl/Ascend rebuild so the fold path exists)?
- R2: Batten spacing for Ascend B&B 12" — consumer, or ruled LP-only by name?
- R3: Vinyl shake rows (Pelican Bay) — blind-by-design or emitter owed?
- R4: panel_size / wrap_trim_width / lp_soffit_type — ratify as
  DIFFERENT-BY-NATURE by name so the register carries the ruling.
- R5: Order gate on siding-kind — what should block release?
- R6: D3/D4/D5 fix direction — assume sealed doctrine governs (human qty always
  survives; one waste emitter) unless overruled.

## FAMILY-COVERAGE PLEDGE
Every handback from here states its family coverage — Vinyl · Ascend · LP — and
names the reason when a change touches fewer than three.

## APPENDIX — waste_included census (register, 58 entries)
- Vinyl YES: OSC, ISC, Starter, Finish Trim, 3/4" J-Channel
- Ascend YES: 5.5" OSC MATTE, Starter, Finish Trim, J-Channel
- Shared vinyl+ascend YES: 3/4" Soffit J-Channel (Charter Oak)
- LP YES: 440 Trim, 540 Trim, 190 Trim, 540 OSC, Soffit Vented, Soffit Closed;
  38 Lap = conditional (callable)
- Correctly unflagged (area/count/passthrough): siding SQ rows, House Wrap /
  RainDrop / Fan Fold (area goods — field waste), coil rolls, nails, caulk,
  vents, shutters, gutter LF family, caps, tear-off, dumpster
