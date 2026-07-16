# Letrick B&B Derivation — Side-by-Side vs Lap List (RULED 2026-07-16)

**Source of authority**: B&B rules ruled by Howard 2026-07-16 (LPZB0884 sheet). The 3-page PDF is **NOT on disk** — the verified extraction lives in `/app/backend/lp_smartside_formulas.py` ("Coverage data verified against LP coverage chart LPZB0884", ingested from Howard's LP_SmartSide_Reference.pdf 2026-02-28).

**Derivation basis**: letrick 7-14-26 7pm photo run — lap field 1,780.5 sq ft (same field, profile substituted). Walls: front/back 50′×8.6′ (eave), left 30′×9.0′ + 8.8′ gable rise, right 30′×8.3′ + 9.3′ gable rise.
**Copy estimate**: `c9203d58-8386-41bb-b030-790c88fd7a7b` — "Dana Letrick — B&B derivation (COPY)" (est # suffix -BB). B&B lines carried at $0 with PENDING notes; original untouched.

## Side-by-side

| | LAP (current list) | B&B (ruled derivation) |
|---|---|---|
| Field | 38 Series Lap 8″ — **227 PCS** @ 9.17 sqft/pc, 10% waste | 38 Series 4′×10′ Panel — **45 PCS** @ 40 sqft nominal, **0% waste (⚑ waste % PENDING)** — at lap's 10% it would be 49 |
| Gables | lap carries its ×0.7 gable convention | **⚑ PENDING** — ×0.7 does NOT auto-carry; left/right gable share derived un-factored |
| Battens | n/a | 190 Series 16′ stock (⚑ SKU/width PENDING): **12″ OC 1,685 LF → 106 pcs · 16″ OC 1,272.4 LF → 80 pcs · 24″ OC 859.8 LF → 54 pcs** (⚑ default spacing PENDING; 16″ provisional on copy) |
| Batten waste | — | NONE per ruling (pieces = ceil(LF ÷ 16)) |
| Seams | — | every 48″ joint covered by scheduled batten — spacing validated ∈ {12,16,24} (divides 48), others raise |
| Starter | lap starter per existing convention | **⚑ PENDING** — B&B starter treatment unruled |
| Nickel Gap | — | reveal **LOCKED 7″** (9.33 sqft/pc), no input field — pinned in test_bb_rules.py |

Batten math per wall (16″ OC example): LF = area ÷ 1.333′ + height → front 331.1 · back 331.1 · left 310.5 (⚑ gable) · right 299.7 (⚑ gable).

## Cross-check findings (flagged, NOT reconciled)
1. **Module batten formula superseded**: old code omitted the "+1 run × wall height" term and applied 10% waste to battens — both corrected to the ruled formula. Old pins updated with RULED comments. Ingest path (hover) computes the +height term as 0 (no per-wall heights there) — noted in line note.
2. **Spacing was a free string with silent fallback** — now validated (must divide 48) and raises on 10/18/32 etc.
3. **`.env` carries LP_AI_FORMULAS_V1 twice** (lines 17 and 24, both truthy) — duplicate key, flagged not touched.
4. Lap 8″ @ 9.17 sqft/pc and soffit conventions in the module match the LPZB0884 extraction; production flag ON so PDF-accurate rates are live (legacy 9.09 only when flag off).

## HELD pending Howard (registry: `BB_HELD_PENDING_HOWARD`)
batten product/width + SKU · default spacing · B&B starter treatment · panel gable factor · panel waste %
