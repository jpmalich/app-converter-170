# MASTER PRICE CATALOG — TABS 3–6 DIFF REPORTS (2026-07-18, Howard's per-tab go)
Workbook: Pro-quotes Master price Catalog.xls. **REPORT-ONLY — nothing applied.**
Scope of this go: ISS Remodeling / Mezzo / VERO. Tab 4 (ISS Window Replacement,
38×7) had NO go — not diffed, still awaiting per-tab ruling.

## TAB 3 — ISS Remolding Siding price — DIFF vs `iss_catalog` (51 DB docs)
51 priced sheet rows parsed · 45 exact matches on section+name.

### Price changes: **NONE** — every matched price identical to DB.
### Section moves: **6** (same item + identical price, sheet reorganizes sections)
| Item | Price | DB section | Sheet section |
|---|---|---|---|
| R&R gutter | 4.28 | Misc. Labor and Material | MISC. LABOR ONLY |
| R&R downspout | 2.15 | Misc. Labor and Material | MISC. LABOR ONLY |
| Fullback in place of 1/4" insulation | 93.63 | Misc. Labor and Material | MISC. |
| Replace 1x4 lumber | 7.15 | Misc. Labor and Material | MISC. |
| Replace 1x6 lumber | 8.63 | Misc. Labor and Material | MISC. |
| Replace 1x8 lumber | 10.04 | Misc. Labor and Material | MISC. |
### Adds: **NONE** · Removals: **NONE**
RULING NEEDED (cosmetic only): adopt the sheet's section split (MISC. LABOR ONLY /
MISC.) in `iss_catalog`, or keep the current merged "Misc. Labor and Material"?
Prices are unaffected either way.

## TAB 5 — Mezzo Price sheet — DIFF vs `mezzo_prices` (16 DB docs, 4 tiers × 4 products)
Sheet layout: 3000-series **LIST** prices (Base/Option Discount cells = 0). DB tiers
derive from list by a per-tier multiplier — fitted from the data and verified on EVERY
UI bucket of EVERY product:

| Product (sheet) | DB product | Buckets | WS ×0.55 | Contractor ×0.50 | BD ×0.45 | one-opp ×0.45 |
|---|---|---|---|---|---|---|
| 3001 Double-Hung | Mezzo Double Hung | 13 | CONSISTENT | CONSISTENT | CONSISTENT | CONSISTENT |
| 3002 2-Lite Sliding Window | Mezzo 2-Lite Slider | 13 | CONSISTENT | CONSISTENT | CONSISTENT | CONSISTENT |
| 3003 / 3009 3-Lite Sliding Window | Mezzo 3-Lite Slider | 11 | CONSISTENT | CONSISTENT | CONSISTENT | CONSISTENT |
| 3004 Picture Window / Transom | Mezzo Picture | 11 | CONSISTENT | CONSISTENT | CONSISTENT | CONSISTENT |

**VERDICT: zero drift.** Every DB base price on every tier equals sheet-list × the
tier multiplier to the cent. No action required.

## TAB 6 — VERO — DIFF vs `vero_prices` (9 DB docs)
Sheet carries ONE price column = the wholesale COST layer. DB tiers derive by the
established margin divisors (÷0.65 / ÷0.70 / ÷0.75):

| Product | Sheet base 0-101 | WS ×1.5385 (÷0.65) | Contractor ×1.4286 (÷0.70) | BD ×1.3333 (÷0.75) |
|---|---|---|---|---|
| Vero Double Hung | 186.921 | 287.57 CONSISTENT | 267.03 CONSISTENT | 249.23 CONSISTENT |
| Vero 2-Lite Slider | 186.921 | 287.57 CONSISTENT | 267.03 CONSISTENT | 249.23 CONSISTENT |

All 8 adders (Quattro, Elite TG2, TG2 Triple, Head Expander, Grids, Sentry, Nail Fin,
HD Screen) track the SAME ratio on every tier — **zero drift**.

### Flags (report-only, awaiting ruling)
1. **Vero one-opp tier**: no DB docs exist for Vero on the one-opp tier (WS/Contractor/BD
   only). Intentional, or should one-opp be derived too?
2. **Vero Patio Door — net-new sheet data.** DB docs exist but `base_prices` is None.
   Sheet (4792PD 2 Panel, White int/ext): 5068 → 718.19 · 6068 → 780.29 · 8068 → 877.16.
   These read as SELL-side figures (≈ cost ÷ margin already applied?) — need Howard to
   confirm which layer they are before any ingest.

## AWAITING HOWARD'S GO (per-item)
- [ ] ISS: adopt sheet section split (cosmetic) — or keep DB sections?
- [ ] Vero Patio Door: confirm price layer, then ingest?
- [ ] Vero one-opp tier: derive or leave absent?
- [ ] Tab 4 ISS Window Replacement: diff on your go.
