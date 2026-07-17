# 261 Haugh Drive — Round-Two Derivation (post-fix)
**Date:** 2026-07-17 · **Estimate:** `d78cd3b4-a65c-4238-8d16-7827b131a85c` ("261 Haugh Dr — round two (post-fix)") · fresh materialization per mechanics ruling (3)(b); `02beb855` untouched as the before-artifact.

## Geometry basis (named on panel)
`Hover import — report 4ffc35f4 — pinned (applied) · wrap-only scope 2064 of 2610 ft² (stucco 312, brick 234 excluded) · openings: Hover net · profile: Lap`

## Ruled scope entries (import-time, provenance-logged on the materialization event)
- **Facade scope (ruling 1):** wrap-only **2,064 ft²** of 2,610 measured; excluded: stucco 312, brick 234. Standing rule wired: `facade_scope` on the Hover→engine contract; never silently sums facade types.
- **Openings (ruling 2):** Hover net-of-openings composes AS-IS — no window add-back. Named on the basis line ("openings: Hover net") as the Hover-path convention, distinct from photo/tape gross.
- **Soffit (ruling 3):** the ~83 ft² unlabeled rows (items 19–20) are INSIDE the 463 total — composition fix only. Per-surface entry: eaves 216 / rakes 164 / ceilings 83 (Σ = 463, full measured total composes). Ceilings → closed via the porch-ceiling mechanism, no venting.
- **Waste (fix 4):** contract default **10%**, never silently 0. (`waste_pct` override accepted per estimate.)

## Fix-order dispositions
1. **Coil — GONE from LP surfaces, mechanism traced.** The 6-roll row (Σ opening perimeter 574.33 ÷ 100 = 5.74 → 6) is the legacy **vinyl/ascend** "Siding Accessories" formula. It does not compose on any current LP-routed surface: the LP-native panel guard (iter 97 composition-bug strip) holds, and the `.019 Coil` spec row carries tabs `["vinyl","ascend"]` only — no lp_smart. Where round one saw it: the shared accessories section on the printed/other-tab view of the before-artifact. Sweep result: no other legacy accessory formula (J-channel, house wrap, coil-class) carries an lp_smart tab.
2. **Lap 314 → 248.** The +29 was NOT per-facade ceiling summation — it was the ruled 10% waste already baked in `lap_pieces` (ceil once): ceil(2,610 ÷ 9.17 × 1.10) = 314. The defect was **scope** (all facade types summed). Post-fix: **ceil(2,064 ÷ 9.17 × 1.10) = ceil(247.60) = 248**, house-total scope, whole-piece round-up ONCE.
3. **540 trim 39/37 → 33.** Round-one 39 = legacy per-opening constants (32×14 + 3×21 + 3×25 + 1×32 = 618 ÷ 16). Panel's 37 = Iter 57ee 3-side constants (591 ÷ 16). Ruled measured basis now governs on the Hover path: **574.33 − door bottoms 49 (garage 1×16' + entry 3×3' + SGD 3×8') = 525.33 ÷ 16 = 32.83 → 33**. Per-source convention: photo/blueprint keep the Iter 57ee constants (letrick re-verified unchanged, $11,055.71 to the penny).
4. **Waste honored** (see scope entries) — lap arithmetic above shows the ×1.10 explicitly.
5. **Soffit 463 composes in full, measured basis:** vented = eave 216 ÷ 21.3 × 1.10 = **12 pcs** · closed = (rakes 164 + ceiling 83) = 247 ÷ 21.3 × 1.10 = **13 pcs**. The eaves-only removal rule now yields to measured per-surface data (refinement logged in code); the 463-vs-184 sanity heuristic's expected-math now uses report per-surface areas, not OVERHANG_IN × eaves.

## Full derived list (25 lines, applied-derivation preview)
| Line | Qty | Basis |
|---|---|---|
| 38 Series Lap 3/8"×8"×16' | **248** PCS | ceil(2,064 ÷ 9.17 × 1.10) — wrap-only scope |
| 540 Series Trim 5/4"×4"×16' | **33** PCS | 574.33 − 49 door bottoms = 525.33 ÷ 16 — doors 3-side |
| 540 Series OSC 5/4"×6"×16' | **9** PCS | measured corner LF 140.33 ÷ 16 (20 locations — field verify) |
| 440 Series 4/4"×8"×16' (fascia/rake) | **21** PCS | (eaves 184.17 + rakes 136.58) = 320.8 ÷ 16 — unchanged |
| 440 Series 4/4"×4"×16' (ISC) | 6 PCS | 6 inside-corner locations × whole-stick (see open items) |
| 38 Soffit 16×16 Vented | **12** PCS | measured eave 216 ÷ 21.3 × 1.10 |
| 38 Soffit 16×16 Closed | **13** PCS | measured rakes 164 + ceiling 83 = 247 ÷ 21.3 × 1.10 |
| LP Starter (ripped) | 296 LF | 304.67 − 9' entry widths (sliders sit on starter — ruled) |
| .019 Coil | **—** | GONE (never composes on LP) |
| Gutter section | unchanged | 6" gutter 184 LF · downspout 96 · elbows 16 · end caps 14 · hangers 100 · mitres 20 · clips 16 · sealant 11 |
| Caps | 32 win / 3 entry / 3 patio / 1 garage | per-count, unchanged |
| Sundries | touch-up 1 · caulk 2 · J-blocks 9 · mini-splits 2 · cleanup 1 | unchanged |

**Materials total (contractor sell, applied-lines basis): $15,582.53**

## Score vs check figures
| Item | Check | Derived | |
|---|---|---|---|
| Lap | 248 | 248 | ✅ |
| 540 trim | ~33 | 33 | ✅ |
| Coil | gone | gone | ✅ |
| OSC | 9 | 9 | ✅ |
| 440 fascia/rake | 21 | 21 | ✅ |
| Soffit closed | 12–13 | 13 | ✅ (waste honored) |
| Soffit vented | ~10 | 12 | ⚠️ formula ceil(216 ÷ 21.3 × 1.10) = 12; check figure ~10 reads as no-waste round (216 ÷ 21.3 = 10.1). Waste-on-soffit adjudication yours. |
| Gutter | unchanged | unchanged | ✅ |

## Open items (named, not fixed without ruling)
- **ISC asymmetry:** OSC now rides measured LF (9); ISC still corner-walk whole-stick (6 sticks vs measured 36.92 LF ÷ 16 = 3). Same doctrine would say measured basis governs — awaiting ruling before touching.
- **Soffit vented waste** (above).
- **Import-dialog facade picker:** the standing selectable-scope rule is live at the contract/API level; the one-tap facade picker in the import dialog needs the Hover extraction to emit `facade_breakdown` (schema upgrade) — flagged pending until a future import verifies, blueprint protocol.
- Mapping-contract flags on this estimate: corner_locators OPEN, opening_schedule OPEN (field-verify checklist live on the panel).
