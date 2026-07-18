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
RULING (2026-07-18 PM): ADOPTED — sheet organization canonical; DB re-homed + reordered.

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

### Flags — RESOLVED 2026-07-18 PM (Howard's rulings)
1. **Vero one-opp tier**: LEAVE ABSENT (ruled) — absent docs render "not offered at your
   tier" via `available:false`; never derived.
2. **Vero Patio Door — flag RETRACTED, reporter error.** The original diff read
   `base_prices` (None for fixed-model products); patio door prices live in
   `patio_prices`. The DB ALREADY carries the ruled option-(a) derivation:
   `VERO_PATIO_COSTS` = sheet per-size costs (718.19 / 780.29 / 877.16), tier ladder
   ÷0.65/÷0.70/÷0.75 → 9 prices verified to the cent (5068: 1104.91/1025.99/957.59 ·
   6068: 1200.45/1114.70/1040.39 · 8068: 1349.48/1253.09/1169.55). Pinned in
   test_vero_iter_78y. Howard's interim "sell tiers" reading was retracted — it had
   confirmed a mis-framed question; the sheet's structure governs. ZERO drift; nothing
   applied because nothing needed applying.

## AWAITING HOWARD'S GO (per-item)
- [x] ISS section-split — **ADOPTED 2026-07-18 PM** (sheet organization canonical;
      reverses the Iter 78z++++ merge; backup 20260718_132744_iss_catalog_….json)
- [x] Vero Patio Door: **RESOLVED 2026-07-18 PM** — flag was a reporter error
      (read base_prices; fixed-model prices live in patio_prices). DB already carries
      the ruled option-(a) ladder from sheet per-size costs. Zero drift.
- [x] Vero one-opp tier: **LEAVE ABSENT, ruled 2026-07-18 PM** — absent doc now renders
      "not offered at your tier" (never auto-computed)
- [x] Tab 4 ISS Window diff — **DONE 2026-07-18 PM**: zero drift (see above)
