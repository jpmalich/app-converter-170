# LP MATH VERIFICATION SHEET — 2026-07
**Report only. No code. Every LP-tab line item, one entry each: SKU · formula in plain math · inputs + door · waste/rounding rule · ruling citation · worked example from EST-562488 "3 Degree Rd".**
Worked-example inputs (Hover door, forced board & batten, contractor waste 30%): siding 4,504 ft² · eaves 308.25 LF · rakes 319.42 LF · OSC 26 corners / 175.42 LF · ISC 24 corners / 173.08 LF · opening perimeter 535.08 LF · windows 30, entry 3, patio 1, garage 1 · overhang 12" · measured soffit TOTAL 2,620 ft² · frieze level 406.83 + sloped 276.5 LF.

---

## CONTRACTOR-SPEC CONSTANTS TABLE (every sealed LP constant in one place)
| Constant | Value | Ruling |
|---|---|---|
| Trim/OSC/siding stick length | 16 ft | LP system convention |
| 38 Lap order rate | **11 pcs per square** (PDF 9.17 retired to reference) | sealed 2026-07-19 |
| Shake coverage @ default 7" reveal | 2.33 ft²/pc (4 ft × reveal ÷ 12) | LP PDF formulas (Iter 78ab) |
| Nickel Gap coverage | 9.33 ft²/pc (16 ft × 7" ÷ 12) | LP PDF formulas |
| B&B panel coverage (4'×10') | 40 ft²/pc | RULED (BB rules 2026-07-16) |
| Batten spacing default | **8" o.c.** (was 16" provisional) | **Q9, 2026-07-27** |
| Batten waste | NONE (whole-stick only) | ruled 2026-07-16 (LPZB0884) |
| Soffit panel coverage (16"×16') | 21.3 ft²/pc, × 1.10 cut factor | LP PDF + per-system amendment 2026-07-17 |
| Family waste defaults | lap 10% · B&B/vertical 30% · shake 15% · nickel gap 12% | sealed 2026-07-24; split-path ruling C 2026-07-26; **Q17 2026-07-27: 30% HOLDS** (3 Degree 37.7% = evidence #1) |
| Opening-wrap per-opening constants (photo/blueprint door) | window 14' · entry 18' (21−3 sill) · patio 19' (25−6 sill) · garage 32' (HELD, flagged) | Iter 57ee + door-3-side ruling 2026-07-17 |
| Door-bottom deductions (Hover measured-perimeter door) | garage 16' · entry 3' · SGD 8' | ruled 2026-07-17 |
| Shake belly-band bump | 2 pcs of 540-4" per 100 ft² of shake | LP PDF |
| Starter rip yield | 3 strips per 16' board = 48 LF/board (dedicated-rip option: 16 LF/board) | rip yield RULED FINAL; `starter_rule_divisor` confirmation still OPEN |
| Caulk (B&B) | 1 tube per 23 batten sticks | **Q15, sealed 2026-07-27** |
| Touch-up | 1 kit per 11 SQ per color | **Q15, sealed 2026-07-27** |
| Corner stick math (Hover door) | per-corner whole-stick round-up, min 1 pc/corner | **Q13, 2026-07-27** (pooling retired) |
| Rounding scope | whole-stick rounding is the ENTIRE allowance on stick lines (no % waste); PER-SEGMENT where segment data exists, pooled+flagged where not | C4 2026-07-13 · sealed 2026-07-24 · **Q16 2026-07-27** |
| ISC default product | 540 5/4"×4" (440 4/4"×4" demoted to substitution) | **Q12, 2026-07-27** |
| LP B&B base | NOTHING (no starter, no trim, no J) | **Q11, 2026-07-27** |
| Measured data never drops | soffit total, frieze, drip edge, trim ft², vents, shutters all pass to the engine | **Q10/Q14, 2026-07-27** |

## PRICING MATH (as the quote walks it)
- **Unit material** = the company Price Catalog price for the SKU at the estimate's tier (3 Degree Rd: **Contractor** tier). Supplier-admin cost-preview walks cost → tier margin → sell per line; the contractor quote sees one money surface only.
- **Line total** = qty × unit mat. **sub_mat** = Σ line totals.
- **Tax** = 7% on materials.
- **Labor** = Σ qty × unit lab — v3 zeroing (sealed 2026-07-24): the misc-labor rows ride $0 `lab_src=pending` until the contractor (or a company rate) sets them; Tear-Off/Dumpster join that set (Q1).
- **Base** = sub_mat + tax + labor. **Homeowner sell = Base ÷ (1 − margin)** — 30% margin ⇒ ×1.4286. (3 Degree header: Base 38,082.31 → Sell 54,403.30.)
- No silent waste anywhere: `waste_pct_applied` reports the actual number (sealed 2026-07-19).

---

# LP SMART SIDING
### 1. 38 Series Lap 3/8" × 8" × 16' — PCS
- **Formula**: pieces = ceil( lap ft² ÷ 100 × 11 × (1 + waste) )
- **Inputs**: family-scoped siding ft² (`_per_profile_sqft.lap` or whole-house when lap is the selected family). Doors: Photo (per-wall AI read) · Hover (report ft²) · Blueprint (plan walk).
- **Waste/rounding**: contractor's visible waste % (lap family default 10%), then ceil.
- **Ruling**: book 11 pcs/sq SEALED 2026-07-19 (PDF 9.17 retired); family waste ruling C 2026-07-26.
- **Worked (3 Degree, would-be if lap were selected)**: 4,504 ÷ 100 × 11 × 1.10 = 544.98 → **545 pcs**. (Actual job is B&B → row prints qty 0.)

### 2. Shake — PCS
- **Formula**: pieces = ceil( shake ft² × (1 + waste) ÷ 2.33 ) — coverage = 4 ft × reveal ÷ 12, default reveal 7" (clamped 6.875–9.875").
- **Inputs**: `_per_profile_sqft.shake` (Photo/Blueprint split; Hover only via forced profile).
- **Waste/rounding**: shake family waste 15% (CONTRACTOR-SPEC sealed 2026-07-24), ceil.
- **Ruling**: LP PDF formulas (Iter 78ab); family waste sealed 2026-07-24. **⚠ 7" default reveal is a PDF default, not a Howard ruling — named here, not silent.**
- **Worked (would-be)**: 4,504 × 1.15 ÷ 2.33 = 2,223.1 → **2,224 pcs** (illustrative; no shake on this job).

### 3. Nickel Gap — PCS
- **Formula**: pieces = ceil( ng ft² × (1 + waste) ÷ 9.33 ).
- **Inputs**: `_per_profile_sqft.nickel_gap`. Same doors as Shake.
- **Waste/rounding**: nickel-gap family waste 12% (CONTRACTOR-SPEC), ceil.
- **Ruling**: LP PDF formulas; family waste sealed 2026-07-24.
- **Worked (would-be)**: 4,504 × 1.12 ÷ 9.33 = 540.7 → **541 pcs**.

### 4. 38 Series 4' × 10' Panel (B&B / vertical) — PCS
- **Formula**: panels = ceil( B&B ft² × (1 + waste) ÷ 40 ).
- **Inputs**: `_per_profile_sqft.board_batten` + `vertical` (all three doors; Hover via forced/selected profile).
- **Waste/rounding**: B&B family waste 30% (Q17: HOLDS; 3 Degree effective 37.7% logged as evidence #1), ceil.
- **Ruling**: coverage RULED (BB rules 2026-07-16); waste sealed 2026-07-24 + Q17 2026-07-27.
- **Worked (3 Degree — prints)**: 4,504 × 1.30 ÷ 40 = 146.4 → **147 pcs** (real installed: 155).

### 5. 38 Series 4' × 8' Panel — PCS · 6. 38 Series Vertical Panel — PCS
- **NO DERIVATION — named, not silent.** B&B always lands the 4×10 panel; these two are catalog-only manual rows. No ruling assigns them a formula.

---

# LP SMARTSIDE TRIM
### 7. 190 Series Trim 19/32" × 3" × 16' (battens) — PCS
- **Formula**: batten LF = B&B ft² ÷ (8"/12) + (1 run × wall height per wall, when heights known); pieces = ceil( LF ÷ 16 ).
- **Inputs**: B&B ft²; taped wall heights via the one-tap field / `batten_wall_heights` checklist (`_bb_wall_height_ft`). Hover has no per-wall heights → height term 0, FLAGGED until taped. All three doors.
- **Waste/rounding**: NO waste on battens (ruled 2026-07-16); whole-stick ceil; no doubling at corners/jambs (Q9).
- **Ruling**: Q9 2026-07-27 (8" o.c., height term stays); LPZB0884 2026-07-16.
- **Worked (3 Degree — prints)**: 4,504 ÷ 0.6667 = 6,756 LF ÷ 16 = 422.3 → **423 pcs** (heights untaped, flag stands; real: 465 — tape the walls to close it).

### 8. 440 Series Trim 4/4" × 8" × 16' (fascia + rake + dormer fascia) — PCS
- **Formula**: pieces = ceil( eaves LF ÷ 16 ) + ceil( rake SLOPE LF ÷ 16 ) + ceil( dormer fascia LF ÷ 16 ) — per-segment.
- **Inputs**: eaves LF, rakes LF (all doors), dormer widths (`_ai_dormers`, Photo door only).
- **Waste/rounding**: whole-stick per segment = entire allowance (no % waste); aggregate LF within a segment stays pooled, flagged.
- **Ruling**: one product both run types (amendment 2026-07-11); C4 2026-07-13; 8" width CONTRACTOR-SPEC sealed 2026-07-24; Q16 per-segment + Q4 dormer pooling 2026-07-27.
- **Worked (3 Degree — prints)**: ceil(308.25/16)=20 + ceil(319.42/16)=20 + 0 dormers = **40 pcs** (real: 45; residual = in-segment cut loss, Q16 flag rides the line).

### 9. 540 Series Trim 5/4" × 4" × 16' (opening wrap + frieze + ISC) — PCS
- **Formula**: wrap = ceil( (opening perimeter − door bottoms: garage 16' − entry 3' each − SGD 8' each) ÷ 16 ) on the Hover door; per-opening constants (14/18/19/32) on Photo/Blueprint. Frieze = ceil( level LF ÷ 16 ) + ceil( sloped LF ÷ 16 ). ISC = per-corner: count × max(1, ceil(corner height ÷ 16)). + shake belly-band bump (2 pcs / 100 ft² shake). One consolidated row.
- **Inputs**: opening_perimeter_lf + counts (all doors); level/sloped frieze LF (Hover reads them — consumed per Q10); ISC count + LF (Hover), C3/C4 locators feature-pooled (Photo), corner walk (Blueprint).
- **Waste/rounding**: whole-stick per segment; per-corner min 1 (Q13).
- **Ruling**: measured-perimeter basis + door-3-side 2026-07-17; Q10 (frieze consumed), Q12 (ISC lands this SKU), Q13, Q16 — all 2026-07-27.
- **Worked (3 Degree — prints)**: wrap ceil((535.08−16−9−8)/16)=ceil(502.08/16)=**32** + frieze ceil(406.83/16)=26 + ceil(276.5/16)=18 = **44** + ISC 24 corners × max(1, ceil(7.21/16)) = **24** → **100 pcs** (real 540-4" usage: 142; −42 residual logged, no invented scope).

### 10. 440 4/4"×4" · 440 4/4"×6" · 440 4/4"×10" · 440 4/4"×12" · 540 5/4"×6" · 540 5/4"×8" · 540 5/4"×10" · 540 5/4"×12" — PCS
- **NO DERIVATION (by table design)** — substitution options only: a substitution re-derives from stored geometry with `substituted_from` provenance, never a free reprice. 440 4/4"×4" specifically demoted from ISC default by **Q12 2026-07-27**.

### (non-SKU) LP Starter — field-ripped from siding stock — informational line
- **Formula**: pieces = ceil( starter LF (entry-door widths deducted; sliders sit on starter) ÷ 48 ) — 3 rips per 16' board. Substitution option: dedicated-rip ceil( LF ÷ 16 ).
- **Inputs**: starter_lf (Photo AI read w/ eaves fallback · Hover Level Starter Length · Blueprint raw perimeter). **On LP B&B: starter LF is ZEROED and NOTHING replaces it (Q11 2026-07-27).**
- **Ruling**: rip yield RULED FINAL; C4 slider ruling 2026-07-13. **⚠ `starter_rule_divisor` pending confirmation still OPEN — flag stands on every LP list that prints this line.**
- **Worked (3 Degree — prints)**: B&B → starter **absent** (Q11). Would-be on lap: ceil((654.67 − 3 entry-door widths) ÷ 48) ≈ **14 boards**.

---

# LP SIDING ACCESSORIES
### 11. 540 Series OSC 5/4" × 6" × 16' — PCS
- **Formula**: Hover door — pieces = corner count × max(1, ceil( (corner LF ÷ count) ÷ 16 )); count unavailable → ceil( LF ÷ 16 ) pooled + flag. Photo door — C3 locators, feature-pooled: full sticks per edge, remainders pool, ceil(pool ÷ 16), full sticks at corner BOTTOMS. Blueprint — corner-walk count × whole-stick. + dormer posts: 2 per dormer × max(1, ceil(knee ÷ 16)) (Q4).
- **Inputs**: outside_corner_count + LF (Hover/Blueprint), corner_locations (Photo), `_ai_dormers` (Photo).
- **Waste/rounding**: per-corner whole-stick min 1; no % waste. 6" width CONTRACTOR-SPEC.
- **Ruling**: Q13 2026-07-27 (pooling retired; cut-reuse only with PROVEN tracking); C4 2026-07-13 + placement seal 2026-07-19 (Photo); Q4 2026-07-27 (dormers).
- **Worked (3 Degree — prints)**: 26 corners × max(1, ceil(6.75/16)) = **26 pcs** (real: 19 — ruled conservative; Q13 is the knob).

### 12. 540 Series OSC 5/4" × 4" × 16' — PCS
- **NO DERIVATION** — substitution option for the 6" OSC only (table-limited). Named, not silent.

### 13. Touch up kits — PCS
- **Formula**: kits = max( 1, round( siding SQ ÷ 11 ) ) per color (× N when multi-color; color count is not derived — contractor bumps).
- **Inputs**: siding ft² (all doors).
- **Ruling**: **Q15 sealed 2026-07-27** (flat 1/job retired).
- **Worked (3 Degree — prints)**: 45.04 SQ ÷ 11 = 4.09 → round → **4 kits** (real: 4 — EXACT).

### 14. OSI Quad Max Caulking — Tube
- **Formula**: B&B job — tubes = max( 2, ceil( batten sticks ÷ 23 ) ); non-B&B — 2 tubes/job.
- **Inputs**: B&B ft² → batten stick count (same math as row 7, incl. taped heights).
- **Ruling**: **Q15 sealed 2026-07-27**. ⚠ the non-B&B 2-tube default is the old Iter 57m convention — per-family scaling for lap/shake/NG has NO ruling yet; named row.
- **Worked (3 Degree — prints)**: 423 sticks ÷ 23 = 18.4 → ceil → **19 tubes** (real: 20).

### 15. J blocks — Each
- **Formula**: blocks = max( 4, round( windows ÷ 6 + doors ÷ 2 ) ).
- **Inputs**: window_count, door_count (all doors).
- **Ruling**: **⚠ NO RULING — heuristic proxy.** Named, not silence. (It has landed EXACT on both real checks: 3 Degree 8=8, Casile 9=9.)
- **Worked (3 Degree — prints)**: round(30/6 + 5/2) = round(7.5) = **8** (real: 8 — EXACT).

### 16. Mini Splits — Each
- **Formula**: covers = max( 1, round( entry doors ÷ 2 ) ).
- **Inputs**: entry_door_count.
- **Ruling**: **⚠ NO RULING — heuristic proxy.** (Exact on both real checks.)
- **Worked (3 Degree — prints)**: round(3/2) = **2** (real: 2 — EXACT).

### 17. Trim Coil Aluminum 24"×50' · 18. .019 Coil · 19. PVC Trim Coil · 20. Performance G8 Trim Coil — Roll
- **NO AUTO-ADD — by ruling.** Coil on an LP-native package = cross-domain composition bug (iter97 ruling, 2026-07-12): auto-add RETIRED, rows stay catalog-only as `cross_domain_manual_add`. The composition guard also strips J-channel/finish-trim/coil that leak onto LP lists.

### 21. Flash tape 3 3/4" × 90' — Each
- **NO DERIVATION** — catalog-only manual row (Iter 78e accessory expansion). No ruling assigns a formula. Named.

---

# LP SMARTSIDE SOFFIT
### 22. 38 Series Soffit 16×16 Vented (eaves) — PCS
- **Formula**: basis priority — (1) explicit per-surface breakdown: pieces = ceil( vented ft² × 1.10 ÷ 21.3 ); (2) measured report TOTAL: vented share = total × eaves ÷ (eaves + rakes), then same ÷ 21.3 × 1.10; (3) overhang fallback: ceil( ((overhang ÷ 12) × eaves LF + porch-ceiling ft²) × 1.10 ÷ 21.3 ).
- **Inputs**: `soffit_breakdown` (Hover-LP bridge) → `soffit_sqft` total (Hover report — consumed per Q14a) → overhang (Job-Info/form) + eaves LF + porch entries.
- **Waste/rounding**: 21.3 ft²/pc coverage × 1.10 cut factor, ceil. ⚠ the 1.10 factor is the LP PDF convention (single-bake pinned at Casile closeout) — predates the family-waste seal; named here.
- **Ruling**: measured-basis 2026-07-17 (261 Haugh); **Q14a 2026-07-27** (total governs; proportional split, "verify venting split" note).
- **Worked (3 Degree — prints)**: vented share 2,620 × 308.25 ÷ 627.67 = 1,286.7 ft² × 1.10 ÷ 21.3 = 66.45 → **67 pcs**.

### 23. 38 Series Soffit 16×16 Closed (rakes + ceilings) — PCS
- **Formula**: same basis ladder with the rake share (+ ceilings via the porch-ceiling mechanism, no venting). On the overhang-fallback basis ONLY, the Closed row is REMOVED from LP-native (eaves-only rule — rakes carry 440-8" rake boards); a measured basis (breakdown OR total) keeps it.
- **Inputs**: as row 22, rake side.
- **Ruling**: per-system amendment + refinement 2026-07-17; **Q14a 2026-07-27** (measured total keeps the row).
- **Worked (3 Degree — prints)**: closed share 2,620 × 319.42 ÷ 627.67 = 1,333.3 ft² × 1.10 ÷ 21.3 = 68.85 → **69 pcs**. (Vented 67 + Closed 69 = 136 pcs = the full measured 2,620 ft²; real crew ran 260 pcs of VINYL charter oak ≈ 2,600 ft² — area matches; vinyl substitution row reads 262 per Q14b.)

### 24. 24 inch CTW soffit — PCS · 25. 24 inch VSSFT — PCS
- **NO DERIVATION** — catalog-only manual rows. No ruling assigns them a formula. Named, not silent.

---

# PRESENCE / LABOR ROWS ON THE LP TAB (money-relevant, zero-derive by ruling)
| Row | Rule | Ruling |
|---|---|---|
| Tear-Off (SQ) · Dumpster (Each) | rows EXIST on every door, qty 0 + labor $0 `pending`; readiness panel names them until the contractor sets both | **Q1 2026-07-27** |
| Cap window / entry / patio / garage · clean up/haul away | qty derives from counts (1 per opening; cleanup 1/job); labor $0 `lab_src=pending` (both retired machine generations rebind to $0) | v3 zeroing sealed 2026-07-24 |

# ⚠ UNRULED-MATH REGISTER — ALL 8 RULED 2026-07-28 (post Walk-v2 clearance; pins in `test_register_rulings_2026_07_28.py`)
1. **J blocks** — SEALED AS-IS: max(4, round(W/6 + D/2)) — contractor owns final qty; more-pronounced-flag PARKED, no date.
2. **Mini Splits** — SEALED AS-IS: max(1, round(entry/2)).
3. **LAP UNIFY** — split path CONFORMS to sealed 11 pcs/sq (100/11 coverage); 9.17 retired to reference; equivalence pinned forever. Worked example: 500 ft² @ 10% → 61 pcs on BOTH paths (was 60 via 9.17 on the split path).
4. **SHAKE REVEAL** — contractor field bounded 7"–10", DEFAULT 7" (LP install instructions verbatim, cited in code). **ACCEPTED REDUCTION (Howard, 2026-07-28 — conscious, not a silent walk): the 7" default orders LESS than the retired 6-7/8" worst-case constant — 500 ft²: 252 → 247 pcs.** Accepted because 7" is the max-material end of the LP-legal 7–10" range and the sealed 15% shake waste absorbs it. Interaction with the sealed rates: 44 pcs/sq is the MIN-reveal (6-7/8") instantiation of coverage = 4'×reveal/12 — at the ruled 7" default ~43/sq, at 10" (panel-clamped 9.875) ~31/sq; the sealed 15% waste applies multiplicatively ON TOP regardless.
5. **CAULK family-shaped** — flat 2/job RETIRED everywhere: LP non-B&B 1 tube/SQUARE · vinyl/ascend 1 tube/OPENING · B&B holds sealed 1/23 sticks. Fixture walk: Letrick (lap, 21 SQ) 2 → 21 tubes (+19 × $14.03 = +$266.57), total_sell 13037.21 → 13303.78 (two dollar pins amended). CASILE DOES NOT MOVE — B&B holds at 9 tubes (194÷23), pinned.
6. **SOFFIT 1.10** — RECOGNIZED as the sealed baked-10 soffit convention; citation landed, no change (r6 pin).
7. **TOUCH-UP color count** — reads the estimate's selected Job Info colors; distinct colors multiply the 1-kit-per-11-SQ base on BOTH the package and the tab-line rebuild (parity pinned); unknown at import → 1.
8. **CATALOG-ONLY manual rows** — manual BY DESIGN, named in `lp_conventions.CATALOG_ONLY_MANUAL_BY_DESIGN`; r8 pin asserts none ever grows a silent derivation.

Handback stamps: 2026-07-28 01:06 UTC · ea95b64 · CLEAN (1482) and 01:16 UTC · 6f78d36 · CLEAN (1483).

*Sources: `lp_smartside_formulas.py`, `lp_conventions.py`, `lp_package.py`, `routes/hover.py` (HOVER_MAPPING_SPEC + `_build_lines`), `routes/lp_package_routes.py`, live re-derivation of EST-562488. Every worked example recomputed against the running engine. No source file modified.*
