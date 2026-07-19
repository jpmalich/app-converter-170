# RECONCILIATION REPORT — LAP LEDGER GAP (app 227/230 vs key 254/255)
Ordered by ruling 2026-07-19 (item 3 close-out). REPORT ONLY — no convention
change, no code change, no key amendment. Prepared for Howard's unification
ruling, book in hand.

## (a) AREA BASIS — what each ledger starts from, itemized

BOTH LEDGERS ARE GROSS (neither deducts openings; app opening_sqft 204.1 is
informational only — netting is NOT a cause of the gap).

APP ledger base 1889.1 ft² (run d6679448 measurements, AI-frame reads):
- front body  50.0' × 8.6'  = 430.0
- back body   50.0' × 8.6'  = 430.0
- left body   30.0' × 9.0'  = 270.0
- right body  30.0' × 8.3'  = 249.0
- bodies subtotal                  1379.0
- gables (AI triangle composition)  380.1
- chase (AI attribution, C4 rule)   130.0
- TOTAL                            1889.1

KEY ledger base 2092.8 ft² (sealed key EST-191890, taped, pre-item-3):
- front  54' × 8.85' (taped-derived)      = 478.1
- back   54' × 9.92' (28 × 4.25"/12)      = 535.7
- stepped sides (taped segments)          ≈ 566.4
- gables (book convention w × h × 0.7)    = 367.5
- walls_gables subtotal                    1947.3
- chase composed (outer 47.97 + sides 97.56) = 145.53
- TOTAL                                    2092.8

WHY THEY DIFFER (named causes, ft², pre-item-3; Δ = key − app = +203.7):
1. DIMENSION FRAME (tape governs vs AI reads: 54' vs 50' eaves, taped
   heights vs 8.6' avg): eave walls +153.8, side walls +47.4  → +201.2
2. GABLE CONVENTION: book ×0.7 (367.5) vs AI triangles (380.1) → −12.6
3. CHASE ATTRIBUTION: composed 145.53 vs AI 130               → +15.5
   (post-item-3 both carry TAPED faces: 152.39 key vs 152.38 app —
   residual 0.01 = key's 2.5833' vs machinery's 2.583' depth rounding)
Sum: +204.1 ≈ +203.7 (0.4 lives in the key's "~566.4" sides rounding).
POST-ITEM-3 bases: app 1911.5, key 2099.7 (Δ +188.2 — causes 1 and 2 only).

## (b) CONSTANTS — source pedigree

- 9.17 ft²/pc (APP coverage): LP SmartSide reference PDF LPZB0884 (on file:
  /app/memory/LP_SmartSide_Reference_LPZB0884.pdf), product line 38 Series
  Lap 3/8" × 8" × 16': reveal 6-7/8" → coverage 16' × 6.875/12 = 9.1667 →
  9.17. Code: lp_smartside_formulas.py LAP_PROFILES ("PDF data table values
  verified"). Equivalent: 10.905 pcs/sq.
- 1.10 (APP waste): DEFAULT_WASTE = 0.10, adopted as house default under
  "Defaults (Howard, 2026-02-28)" — "Standard PDF waste factor for every LP
  family. Contractor can still bump it manually." Letrick runtime confirms
  waste_pct_applied = 0.10, no manual bump.
- 11 pcs/sq (KEY coverage): Howard's hand-takeoff convention — sealed key
  artifact (TAPED-era, sealed 2026-07), line derivation verbatim: "× 11
  pcs/sq (6-7/8\" reveal)". Equivalent: 9.0909 ft²/pc. vs PDF-exact 10.905
  pcs/sq the book rounds pieces-per-square UP to whole 11 — a ≈0.87%
  ordering cushion. Same 10% waste, same single final round-up: the ONLY
  formula difference between ledgers is 9.17 vs 9.0909 coverage (plus where
  the ceil lands).

## (c) WORKED TOTALS — both formulas on identical bases (formula isolated
from area). APP formula: ceil(base ÷ 9.17 × 1.10). KEY formula:
ceil(base × 1.10 ÷ 100 × 11).

| base (ft²)            | APP formula                    | KEY formula                     | Δ formula |
|-----------------------|--------------------------------|---------------------------------|-----------|
| 1889.1 (app, pre)     | 206.01 ×1.1 = 226.61 → **227** | 20.780 sq ×11 = 228.58 → **229**| +2        |
| 2092.8 (key, pre)     | 228.22 ×1.1 = 251.04 → **252** | 23.021 sq ×11 = 253.23 → **254**| +2        |
| 1911.5 (app, post-i3) | 208.45 ×1.1 = 229.30 → **230** | 21.027 sq ×11 = 231.29 → **232**| +2        |
| 2099.7 (key, post-i3) | 228.97 ×1.1 = 251.87 → **252** | 23.097 sq ×11 = 254.06 → **255**| +3        |

AREA-ONLY deltas (same formula, key base vs app base):
- APP formula: 227 → 252 (+25 pre) · 230 → 252 (+22 post)
- KEY formula: 229 → 254 (+25 pre) · 232 → 255 (+23 post)

DECOMPOSITION OF THE NAMED GAP:
- pre-item-3  227 vs 254 = 27 pcs = 25 (area frame) + 2 (formula)
- post-item-3 230 vs 255 = 25 pcs = 22–23 (area frame) + 2–3 (formula)
The area frame (tape vs AI reads) dominates; the formula difference is
2–3 pcs on any base.

Status: report filed 2026-07-19. Awaiting unification ruling.
