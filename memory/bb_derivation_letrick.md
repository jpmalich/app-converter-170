# Letrick B&B Derivation — FINAL (all five rulings closed 2026-07-16)

**Source PDF archived**: `/app/memory/LP_SmartSide_Reference_LPZB0884.pdf` (the sheet behind `lp_smartside_formulas.py`).
**Copy estimate**: `c9203d58-8386-41bb-b030-790c88fd7a7b` — "Dana Letrick — B&B derivation (COPY)" (#-BB). Original untouched.

## Rulings applied (module `BB_RULED_FINAL`, pinned in test_bb_rules.py — 9 tests)
- Field: 38 Series 4′×10′ Panel, area ÷ 40 × (1+waste) → whole panels
- Battens: 190 Series Trim 19/32″×3″×16′, LF = area ÷ spacing_ft + height/wall, pcs = ceil(LF÷16), no waste; seams covered by divides-48 schedule
- Default spacing 16″ OC, job-editable, 12/16/24 validated
- **NO starter on B&B** — pinned: no starter row is lp_smart-scoped in HOVER_MAPPING_SPEC
- Gable ×0.7 same as lap — carried upstream by the engine's C4 gable-area convention (already inside the 1,780.5 field figure)
- Waste default 10% incl. panels — contractor dial overrides per estimate, provenance-visible

## Catalog check (ruled): BlueLinx cost basis CONFIRMED — nothing pending
- 190 Series Trim 3″×16′: mill $13.76 (EF $20.64) → engine-priced
- 38 Series 4′×10′ Panel: mill $96.56 → engine-priced

## Side-by-side (validated geometry, Contractor tier 30% true margin, mill finish)
| | LAP (current list) | B&B (ruled, FINAL) |
|---|---|---|
| Field | 38 Series Lap 8″ — 227 PCS @ 9.17, 10% waste | 4′×10′ Panel — **49 PCS** (1780.5÷40×1.10) @ **$137.94**/pc sell |
| Battens | — | 190 Series 16′ — **16″ OC: 1,353.8 LF → 85 pcs** @ **$19.66**/pc sell (12″: 113 · 24″: 58, job-editable) |
| Gables | ×0.7 engine convention | same ×0.7, carried upstream — identical field basis |
| Starter | lap starter per convention | **NONE — panels start on the ledge (pinned)** |
| Corners/trim/soffit/fascia | 540/440/soffit rules | **carried unchanged** — profile-independent |
| Pricing | engine | engine (cost ÷ (1−30%)) — zero pending lines |

Per-wall battens @16″: front 331.1 · back 331.1 · left 350.1 · right 341.5 LF (engine per-wall areas incl. 0.7×w×t gables).

---

## PANEL BASIS CHECK (Howard, 2026-07-16) — answered + RE-DERIVED

**(1) Geometry source of the first derivation**: photo extraction run `d66794488ef848509446431b355db8e5` (2026-07-14 23:32), NOT the sealed key. That run read `_per_profile_sqft.lap = 1,780.5` (its own `siding_sqft` = 1,889.1) — a LOW read: −15.2% vs the key's 2,098.5. Known extraction stochasticity: sibling runs read 2,147.6 (+2.3%, C4 report) and 1,954.5 (−6.9%, shakedown scoring).
**(2) Opening deductions**: NONE anywhere on the B&B path — panels from field straight, battens from gross wall areas; ruled convention honored. FLAG (not reconciled): that run's per-profile lap (1,780.5) sits 108.6 sqft below its own siding_sqft (1,889.1) — unexplained internal split within the extraction.
**(3) Field arithmetic, itemized against the sealed key**: walls **1,585.5** + gables@0.7 **367.5** + chase faces **145.5** = **2,098.5** → ÷ 40 × 1.10 = 57.71 → **58 panels** (first derivation's 49 back-solved to the low read, as Howard computed).

## RE-DERIVED — copy now stands on the sealed key
| | LAP (key) | B&B (key basis, FINAL) |
|---|---|---|
| Field | 255 PCS (ceil(2098.5÷9.17×1.10)) | **58 panels** @ $137.94 sell |
| Battens 16″ OC | — | **1,630.0 LF → 102 pcs** @ $19.66 (key field ÷ 1.333′ + heights 8.9+9.9+9.21+9.21 + chase 18.9) · 12″: 135 · 24″: 70 |
| Basis | sealed key 2,098.5 | sealed key 2,098.5 — **same measured house** |
