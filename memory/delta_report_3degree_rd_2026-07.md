# REAL-JOB DELTA REPORT — EST-562488 "3 Degree Rd" (2026-07)
**Report only. No code was touched. Rules with the pasted Completeness Matrix in ONE sitting.**

## Job identity & provenance
- Estimate: **EST-562488** (`786ff854-9923-4c18-905e-ef6d5d8a1a26`), kind lp_smart, tier Contractor
- Source run: **`hover-dfd4847fcd71-board_batten`** — HOVER door, status done, profile forced **board_batten**, single source (matches the print header)
- Waste field: **30.0%** (B&B family default, sealed 2026-07-24) → `_waste_pct = 0.30`
- Ground truth: contractor's ACTUAL installed list, transcribed xlsx (`material for 3 degree rd.xlsx`), read verbatim
- Standing flags already on this run: `corner_locators` (no per-corner locators on Hover) · `batten_wall_heights` (+height term = 0, PENDING field verify) · `opening_schedule` (counts only)

## Engine inputs as stored (the numbers every formula below actually consumed)
siding_sqft **4504** (Hover net-of-openings, composes AS-IS — ruled 2026-07-17) · eaves **308.25** · rakes **319.42** · OSC **26 loc / 175.42 LF** · ISC **24 loc / 173.08 LF** · opening_perimeter **535.08** · windows **30** · entry **3** · patio **1** · garage **1** · overhang **12"** · stories **>1** · starter_lf **0** (B&B no-starter ruling zeroes it in `_force_profile_measurements`)

**Hover READ these but the engine's 17-key passthrough DROPS them** (`_hover_mapping_contract`):
`soffit_sqft` **2620** · `level_frieze_lf` **406.83** · `sloped_frieze_lf` **276.5** · `drip_edge_lf` **627.67** · `total_trim_sqft` **485** · raw `starter_lf` **654.67** · window bottom widths **89.5 LF** · united inches 2257. Several of these turn out to be exactly the missing money below.

## Reproduction check — every printed number rebuilt from the stored run (bit-exact)
| Line | Formula as-computed (inputs shown) | Repro | Printed |
|---|---|---|---|
| 4×10 panels | ceil-pieces(4504 × 1.30 ÷ 40.0 sqft/panel) | **147** | 147 ✓ |
| 440 4"×4" ISC | avg 173.08/24 = 7.21' ≤ 16' → cut-stock pooling ceil(173.08 ÷ 16) | **11** | 11 ✓ |
| 440 4"×8" | ceil((308.25 + 319.42) ÷ 16), whole-stick = entire allowance | **40** | 40 ✓ |
| 540 5/4"×4" | ceil((535.08 − garage 16 − entry 3×3 − SGD 8) ÷ 16) = ceil(502.08/16) | **32** | 32 ✓ |
| 190 battens | ceil(4504 ÷ (16"/12) ÷ 16) = ceil(3378 LF/16), height term **0**, no waste | **212** | 212 ✓ |
| Touch-up kits | constant 1 per color | **1** | 1 ✓ |
| OSI caulk | constant 2 tubes/job | **2** | 2 ✓ |
| J blocks | max(4, round(30/6 + 5/2)) | **8** | 8 ✓ |
| Mini splits | max(1, round(3/2)) | **2** | 2 ✓ |
| 540 OSC 6" | Hover measured-LF basis: ceil(175.42 ÷ 16) | **11** | 11 ✓ |
| Vented soffit | ceil((12"/12) × 308.25 ÷ 21.3 × 1.10) — overhang FALLBACK basis | **16** | 16 ✓ |

**11/11 bit-exact.** The derivation chain is intact; every delta below is a MODEL gap, not a bug. The two exact real-world matches (J-blocks 8=8, mini-splits 2=2) calibrate the claim: the machine is precise about what it models and blind to what it doesn't.

---

# THE DELTAS, CLASSIFIED
Classes: **(a)** formula/convention error · **(b)** MISSING scope (matrix loud-list) · **(c)** scope/input dependency (un-entered input) · **(d)** genuine Hover-data limitation

## D1 · 38 Series 4×10 Panel — 147 app → 155 real (−5.2%)
- As-computed: 4504 × 1.30 ÷ 40 = 146.4 → 147.
- Gap: +8 panels = +320 sqft ⇒ effective real waste **≈ 37.7%** on the Hover net area (or the net-of-openings basis under-states the cut area).
- **CLASS (a) convention calibration** — B&B 30% family default reads ~7 pts light on this job — **with a (d) tail**: Hover facades are net-of-openings and compose AS-IS (ruled); crews cut gross around small openings.
- Smallest miss on the sheet; recommend watching across 2–3 more real lists before touching the sealed default.

## D2 · 440 4/4"×4" ISC — 11 app → NOT USED (real job ran 540 5/4"×4" in its place)
- As-computed: correct per current convention (ISC → 440 4/4"×4", cut-stock pooled).
- **CLASS (a) product-spec/convention error** — the DEFAULT ISC product doesn't match what the crew actually installs. The substitution table already permits 540-series (table-limited swap, full re-derivation) — but a default that's always swapped is the wrong default.
- The 11 sticks' worth of ISC footage migrated into the real 540-4" count (D4).

## D3 · 440 4/4"×8" fascia+rake — 40 app → 45 real (+12.5%)
- As-computed: 627.67 LF ÷ 16 = 39.2 → 40; "whole-stick rounding is the entire allowance" (sealed 2026-07-24) assumes ZERO cut loss across ~628 LF of many separate run segments.
- Gap: +5 sticks = +80 LF ≈ 12.5% — classic per-segment rounding + cut loss on a chopped-up >1-story roofline (26 outside corners!).
- **CLASS (a) convention error (pooled-total rounding vs per-run reality)**, with a possible (b) sliver: Hover read **683 LF of frieze** the engine drops — if any frieze ran 8" board it lands here.

## D4 · 540 5/4"×4" — 32 app → 142 real (−110 sticks, the money hole)
- As-computed: opening perimeter only — 502.08 LF ÷ 16 = 32. **Matrix said this out loud**: LP trim derives from eaves+rakes+opening-perimeter and nothing else.
- Real: 142 × 16' = **2272 LF of installed 4" trim**.
- **CLASS (b) MISSING scope, CONFIRMED — suspect named by matrix.** Inverse reconstruction from surfaces ALREADY ON RECORD for this job:
  | Surface | LF | Status in engine |
  |---|---|---|
  | Opening wrap (modeled) | 502.08 | DERIVED (the 32) |
  | ISC footage (D2 substitution) | 173.08 | derived as 440-4", crew ran it in 540-4" |
  | **Frieze** (level 406.83 + sloped 276.5) | **683.33** | **READ BY HOVER, DROPPED by passthrough — loud** |
  | **B&B base / water table** (raw starter 654.67) | **654.67** | **zeroed by B&B no-starter ruling with NO replacement**: vinyl rule gives J at B&B base, but J is composition-stripped on LP-native → LP B&B base treatment is UNDEFINED. A hole the matrix's family table implied; this job proves the crew trims it |
  | **Total** | **2013.2 LF** → ÷16 = **126 sticks** pooled | real **142** |
- Residual 16 sticks (~11%) ≈ per-surface whole-stick rounding + cut loss (same disease as D3).
- **Hypothesis for ruling**: real 540-4" scope = opening wrap + ISC + frieze + B&B base. Howard/crew to confirm surface-by-surface from the pick ticket.

## D5 · 190 battens — 212 app → 465 real (worst miss, −54%)
- As-computed: 4504 ÷ 1.333' (16" o.c.) = 3378 LF ÷ 16 = 212; height term **0** (Hover has no per-wall heights — the flag is ON this run); no waste (ruled).
- Real: 465 × 16' = **7440 LF** of battens.
- **Named suspect (the PENDING height term): PARTIALLY REFUTED as sole cause.** Even a violently articulated plan (26 OSC + 24 ISC ⇒ ~50 wall planes) at ~19' two-story height adds ~950 LF ≈ +59 sticks → 271. Nowhere near 465.
- Scenario table (what closes the gap):
  | Scenario | LF | Sticks |
  |---|---|---|
  | 16" o.c., no heights (as shipped) | 3378 | 212 |
  | 16" o.c. + height term (~50 walls × 19') | 4328 | 271 |
  | 12" o.c., no heights | 4504 | 282 |
  | 12" o.c. + heights | 5454 | 341 |
  | **8" o.c., no heights** | 6756 | 423 |
  | **8" o.c. + heights** | ~7706 | **~482 ≈ real 465** |
- **CLASS (a) + (c) STACKED**: (a) the 16" o.c. default — explicitly PROVISIONAL, `BB_HELD_PENDING_HOWARD`, still un-ruled — appears wrong by ~2×; real spacing reads **~8" o.c.** (batten on every panel-board seam), AND (c) the un-entered wall-height input (PENDING flag) supplies the remainder. The matrix's FLAGGED-PENDING ×2 on the Hover battens cell is exactly this cell.
- Needs the crew's actual spacing + whether battens double at corners/opening jambs.

## D6 · Touch-up kits — 1 app → 4 real
- As-computed: constant "1 per color — bump if multi-color".
- **CLASS (a) per-job constant wrong** — doesn't scale with job size. This is a 45-SQ job: 4 kits ≈ **1 per ~11 SQ** (or per color × stories). Candidate scaling for ruling, not a fix.

## D7 · OSI Quad Max caulk — 2 app → 20 real (10×)
- As-computed: constant 2 tubes/job (mirrors the vinyl default).
- **CLASS (a) per-job constant wildly wrong for B&B** — battens get edge-caulked. Candidates against this job's real numbers: **1 tube per ~23 batten sticks** (465/20) ≈ 1 per ~370 batten-LF, or ~1 tube per 8 panels (155/20). A lap job would need a different (smaller) rule — caulk wants a **per-family scaling**, same shape as family waste.

## D8 · J blocks 8 = 8 ✓ · Mini splits 2 = 2 ✓
- Both proxies land exact (openings-scaled heuristics). Calibration anchors: door data and engine plumbing are sound; the misses above are scope/convention, not noise.

## D9 · 540 OSC 5/4"×6" — 11 app → 19 real (−42%)
- As-computed: Hover measured-LF basis ceil(175.42 ÷ 16) = 11 — the **maximum-optimism cut yield** (assumes remnants pool freely across all 26 corners).
- Bounds: stick-per-corner = 26 · two-corners-per-stick yield = 13 · real = **19** — squarely between. And 175.42 LF ÷ 26 = **6.75' avg corner height on a >1-story house** is itself suspicious.
- **CLASS (a) convention error (flat ÷16 pooling on the Hover door)** with a **(d) tail** (Hover corner LF may under-read tall corners). Note: the PHOTO door's C4 feature-pooling on locators would already refuse this free pooling — the doors disagree by design; the matrix OSC row shows the split. Ruling wanted: per-corner splice-and-round-up (or capped cut-stock yield) on the Hover door.

## D10 · LP Vented Soffit — 16 pcs app → 260 pcs VINYL charter oak real
- As-computed: overhang FALLBACK — (12"/12) × 308.25 eaves = **308 sqft modeled** → 16 LP pcs.
- The run supplied **no `soffit_breakdown`**, and the passthrough **drops Hover's measured `soffit_sqft` = 2620** on the floor.
- Proof this is the whole story: 2620 ÷ 10 sqft/pc (vinyl charter oak) = **262 ≈ real 260 pcs, exact**. (LP-panel equivalent: `soffit_pieces(2620)` = 136 pcs.)
- Implied average overhang 2620/628 LF ≈ **4.2 ft** → deep porches/porch ceilings folded into Hover's soffit total — **Hover-disease HD-1 + HD-3 in one line**, exactly as the matrix's dedicated rows warned (measured basis exists only via the bridge's `soffit_breakdown`; the report TOTAL is never used; porch ceilings gated on Job-Info entries that are empty here).
- **CLASS (d) Hover-data-path limitation (measured total read but unused) + (b) porch-ceiling MISSING row**, plus a separate **product ruling**: crew ran VINYL soffit on an LP job (cross-family substitution — is vinyl soffit the standing convention under LP siding?).
- Side-finding: the printed list correctly carries no Closed row (eaves-only per-system rule) and no LP Starter (B&B no-starter ruling) — but see D4: the base treatment that replaces starter is undefined.

---

# SCOREBOARD BY CLASS
| Class | Lines | $ direction |
|---|---|---|
| (a) formula/convention | D1 panels · D2 ISC product · D3 fascia rounding · D5 batten spacing · D6 touch-up · D7 caulk · D9 OSC pooling | all UNDER (margin-eating) |
| (b) MISSING scope (matrix loud-list) | D4 frieze + B&B base trim · D10 porch-ceiling/soffit area | massively UNDER |
| (c) un-entered input | D5 batten wall heights (flag was on the run, never closed) | UNDER |
| (d) Hover-data limitation | D9 corner heights · D10 dropped soffit total · D1 net-area tail | UNDER |
| ✓ exact | D8 J-blocks + mini-splits, all 11 repro checks | — |

# RULING QUESTIONS (continue the matrix's Q1–Q8; one-pass session)
9. **B&B batten spacing** — what does the crew actually run (evidence says ~8" o.c., i.e. every panel seam)? Does the height term stay, and do battens double at corners/jambs? (closes D5 + retires `BB_HELD_PENDING_HOWARD`)
10. **540-4" trim scope** — confirm the surface list: opening wrap + ISC + frieze + B&B base/water table? Should the engine consume Hover's frieze LF (it already reads it)? (closes D4)
11. **LP B&B base treatment** — starter ruled OFF, J composition-stripped: what physically goes at the panel base on LP-native, and does it derive from the (currently zeroed) starter LF? (feeds D4)
12. **ISC default product** — is 540 5/4"×4" the crew-spec ISC on LP jobs (440 4/4"×4" demoted to substitution option)? (closes D2)
13. **Hover OSC/ISC stick math** — replace flat ÷16 pooling with per-corner splice-and-round-up or a capped yield? (closes D9)
14. **Soffit basis on the Hover door** — when the report carries a measured soffit total, does it govern over the overhang fallback (with porch ceilings flagged out of it per HD-3)? And is vinyl soffit the standing product under LP siding? (closes D10)
15. **Caulk + touch-up scaling** — adopt per-family/per-size rules (caulk ~1 per 23 batten sticks on B&B; touch-up ~1 per 11 SQ per color)? (closes D6/D7)
16. **Stick-line cut allowance** — keep "whole-stick rounding is the entire allowance," or add a small per-segment rounding rule for chopped rooflines (D3's +12.5%, D4's +11% residual)?
17. **B&B panel waste** — hold 30% and re-measure on the next real list, or lift toward ~35%? (D1)

*Sources: xlsx ground truth (verbatim above) · Mongo estimate `786ff854…` + run `hover-dfd4847fcd71-board_batten` · formulas re-executed from `lp_smartside_formulas.py` / `routes/hover.py` / `routes/lp_package_routes.py` — 11/11 printed quantities reproduced bit-exact before any delta was classified. No source file modified.*
