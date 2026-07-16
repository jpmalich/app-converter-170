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
