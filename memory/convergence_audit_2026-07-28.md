# CONVERGENCE AUDIT — 2026-07-28 (report only, nothing built)
Companion to the MONEY-SURFACES MAP (§C below). Class founder: the lap 9.17-vs-11
split (CLOSED by register #3, equivalence pinned). These are its siblings.

---
## A. DUPLICATED QUANTITIES / CONVENTIONS

### A1. ESTIMATE TOTALS — waste application ⚠ DIVERGENT TODAY (DOLLAR)
1. Locations:
   - Frontend `lib/calc.js` `calcTotals` → editor StickyBar/TotalsSummary, Dashboard cards, QUOTE EMAIL (QuoteModal → emailQuote.js `totals.sell`).
   - Backend `services.calc_totals` → public ACCEPT PAGE (routes/public.py:179), accept-confirmation email (public.py:246), CSV export (routes/estimates.py), admin roll-up won/pending dollars (routes/catalog.py:237).
2. Shared emitter? NO — independent formulas. Frontend (fixed 2026-07-24): `wasted = subMat` (waste lives IN qty; wasteAdd display-only). Backend still the PRE-fix formula: `wasted = sub_mat + waste_base × waste_pct` (waste_base = Vinyl Siding section + 2 Ascend SKUs).
3. Pin: `test_profile_owns_family.py:165-170` text-pins the FRONTEND fix only. Nothing stops the backend drifting — it already has.
4. Divergence TODAY: any vinyl/ascend estimate with waste_pct > 0 — the quote email and the Accept page show DIFFERENT sell numbers to the same homeowner (backend re-adds waste on top of the already-baked qty: the exact double-count the 2026-07-24 fix removed from the editor). LP lines are outside waste_base → Casile/LP unaffected.
5. Recommend: UNIFY — retire backend `waste_add` add-on (`wasted = sub_mat`), then one accept-vs-editor fixture pin. Size S.

### A2. WINDOWS — Vero per-opening pricing ⚠ DIVERGENT TODAY (DOLLAR)
1. Frontend calc.js (Iter 44 adders model): per window = base + Σ(adder.qty×mat) + legacy(glass+tempered+premium) fallback. Backend `services._vero_opening_mat`: base + glass + tempered + premium — NO adders term.
2. Independent formulas. 3. No pin. 4. Vero openings priced through adders show those dollars in editor/email but NOT on Accept page/CSV/admin roll-up. (Mezzo backend `_opening_mat` DOES read adders — Vero was left behind.)
5. Recommend: UNIFY backend to the adders model + legacy fallback identical to calc.js; pin. Size S.

### A3. Margin/markup + tax step — 3 copies, agreeing today
services.calc_totals · lib/calc.js · SettingsRow.jsx (display multiplier). Same formula, same "markup" legacy fallback. No pin. Recommend: piggyback one pin on A1's fixture. Size XS.

### A4. OSC/ISC corner-stick math (Q13) — SIX implementations (DOLLAR-capable)
1. hover.py `_osc_lp_pcs` + `_isc_540_pcs` (tab-line spec); lp_package assemble: hover-LF block, corner-walk block, dormer-pool block, C3-locator path (`corner_sticks_for_length`), substitution re-derive.
2. Same formula written independently; 16' as `TRIM_STICK_LEN_FT` in some, literal `16.0` in others.
3. Each path pinned individually (Q13/casile/flag-checklist tests) — NO cross-pin tab-line OSC == package OSC on identical inputs.
4. Divergence-capable TODAY: photo/blueprint estimates with C3 locators — package prices per-locator heights; tab lines price count×avg. A tall-corner house can print a material list ≠ the priced quote.
5. Recommend: equivalence pin on the hover basis (cheap); on the locator basis either UNIFY (tab rebuild consumes assemble's OSC row) or pin the difference as NAMED provenance. Size M.

### A5. LAP piece math — CLOSED by register #3
Both paths pinned identical forever (`test_register_rulings_2026_07_28` r3, parametrized). 9.17 stays reference-only (pinned as reference). Residual: `lap_pieces()` helper still computes via 9.17 — unused for ordering. RETIRE or rename `_reference_`. Size XS.

### A6. Soffit math — 3+ implementations incl. a FRONTEND COPY with its own constants
1. Backend: lp_formulas.soffit_pieces (×1.10 baked), lp_conventions.soffit_takeoff_*, hover spec extracts (note strings hardcode "21.3 × 1.10"). Frontend: `useRecalcSoffitOnOverhang.js` — OWN `LP_SOFFIT_SQFT_PER_PC=21.3`, `LP_WASTE=1.10`, `CHARTER_OAK_SQFT_PER_PC=10.0`; comment admits "must mirror backend".
2. No shared emitter across the wire. 3. No pin on the frontend copy (backend 1.10 now pinned by r6). 4. No value divergence today.
5. Recommend: UNIFY — overhang-edit hook should hit a server recompute (or API-served conventions payload); interim jest pin (wasteLogic.test.mjs precedent). Size M.

### A7. Waste-recompute rounding — frontend 0.5 vs backend whole-piece (cents DOLLAR)
`wasteLogic.js roundUpHalf` (ceil to 0.5) vs backend whole-piece ceil on package/rebuild. Same knob, two rounding conventions → X.5 vs X+1 on the same line. Recommend: UNIFY frontend to whole-piece for PCS units. Size S.

### A8. Porch-ceiling sqft roll-in — deliberate mirror (rebuild_lp_tab_lines vs PorchCeilingsCard.porchCeilingTotalSqft), no pin. ADD pin or accept. XS.

### A9–A10. GOOD (one emitter by construction — cite as the pattern to copy)
Batten sticks: single emitter `board_batten_batten_pieces` feeds spec + caulk + package. Freeze/QR/materialize: all compose through assemble / rebuild_lp_tab_lines verbatim (2026-07-25 ruling); frozen snapshot redacted always.

---
## B. CONSTANTS SWEEP (sealed values defined in >1 place)
| # | Constant | Locations | Pin? | Risk |
|---|---|---|---|---|
| B1 | **11 pcs/sq** | lp_formulas.LAP_PCS_PER_SQUARE=11.0 · lp_conventions.LAP_PCS_PER_SQUARE_16FT['8" Lap']=11 | spec_discrepancies() checks conventions internally; NO cross-module pin | DOLLAR if edited alone |
| B2 | **shake 15%** | SHAKE_WASTE=0.15 · FAMILY_WASTE_DEFAULTS["shake"]=15.0 (same file, two spellings) | none | DOLLAR |
| B3 | **B&B registry vs live** | BB_RULED_FINAL{"default_spacing_in":16} vs DEFAULT_BATTEN_SPACING_IN=8 (Q9 sealed) — the registry value is STALE and CONTRADICTS today | none | harmless (provenance text) → DOLLAR if ever rebound |
| B4 | **16' stick** | TRIM_STICK_LEN_FT · BATTEN_STOCK_LENGTH_FT · SIDING_BOARD_LEN_FT · ~12 literal 16.0s (lp_package, hover) | none | DOLLAR if a length changes |
| B5 | **gable 0.7** | lp_package.GABLE_BOOK_FACTOR · literal 0.7 in ai_measure.py:1954 (C4) | none | DOLLAR via area |
| B6 | **soffit 21.3 / 1.10 / vinyl 10.0** | backend tables + hardcoded note strings + FRONTEND copies (A6) | none | DOLLAR |
| B7 | **family waste defaults** | sealed FAMILY_WASTE_DEFAULTS (10/30/15/12) vs frontend wasteDefaults.js localStorage suggestions (vinyl ~15, LP ~25) that auto-fill est.waste_pct on upload — a THIRD WRITER of the one visible field | none | DOLLAR (can overwrite the sealed pre-fill with 25 on a B&B job) |
| B8 | 44 pcs/sq shake | SHAKE_PCS_PER_SQUARE_MIN_REVEAL=44 vs derived ceil(100/2.29) | NOW PINNED (r4, 2026-07-28) | closed |
| B9 | Tier margins / tier prices | lp_costs.TIERS single source; TIER_PRICES pinned by test_pricing_parity | pinned | GOOD |
| B10 | 6'-8" head anchor | elevation_sheets.py only | single emitter | GOOD (drawing) |
| B11 | tax 7.0 default | models.py only | — | GOOD |

---
## C. MONEY-SURFACES MAP
| Surface | Emitter | Priced? | Exposure |
|---|---|---|---|
| Estimate editor totals (StickyBar/TotalsSummary) | lib/calc.js | YES | A1/A2 reference side |
| Contractor dashboard cards | lib/calc.js | YES | — |
| Quote email (send) | lib/calc.js via QuoteModal | YES | A1: can disagree with Accept page TODAY |
| Public ACCEPT page | services.calc_totals | YES | A1 + A2 live divergence |
| Accept confirmation emails | services.calc_totals | YES | same |
| CSV export | services.calc_totals | YES | same |
| Admin roll-up (won/pending $) | services.calc_totals | YES | same |
| Admin LP cost-preview | lp_costs (tier margin) | YES (admin-only; redact_external guards) | single emitter, GOOD |
| LP Material List panel / freeze / public QR | assemble_lp_package (redacted) | NO (unpriced by ruling 2026-07-23) | A4 qty mismatch vs priced tab lines |
| Printable material list / takeoff PDFs | frontend materialList.js/printTakeoff.js | NO (qty only) | A7 rounding display |
| Group tab lines (the priced quote body) | rebuild_lp_tab_lines → _build_lines spec | YES | A4 vs package panel |
| Elevation sheets / 3D | elevation_sheets.py + frontend renderers | NO | DRAWING class only |

---
## D. RANKED LIST (rule on these — nothing builds until you do)
**CAN CHANGE A DOLLAR:**
1. **A1 totals waste** — LIVE: email vs Accept page disagree on vinyl/ascend jobs with waste>0. Fix S.
2. **A2 Vero adders** — LIVE: adder dollars missing from Accept/CSV/admin. Fix S.
3. **B7 wasteDefaults third-writer** — can silently replace a sealed family waste pre-fill. Fix XS (retire or clamp).
4. **A4 OSC tab-vs-package** — divergence-capable on locator-based jobs (priced quote ≠ printed list). Fix M.
5. **A7 rounding 0.5 vs whole-piece** — cents + provenance smell. Fix S.
6. **B1/B2/B4/B5 duplicate constants** — future contradictions; each a 1-line pin or import. Fix XS each.
7. **A6/B6 frontend soffit copies** — wrong qty on overhang edits the day a backend rate changes. Fix M.

**CAN CHANGE A DRAWING (no dollars):** 6'-8" anchor (single emitter — fine); frontend gableMath.js pitch/scale vs backend C4 0.7 area factor (different quantities, no overlap — fine); elevation-sheet band text.

**HARMLESS:** B3 stale BB_RULED_FINAL registry text (provenance-only — mark superseded); 9.17 reference table (pinned as reference); hardcoded rate strings inside note text (display duplicates); SettingsRow multiplier display.

*Sources: services.py, lib/calc.js, routes/hover.py, lp_package.py, lp_conventions.py, lp_smartside_formulas.py, lp_costs.py, routes/public.py, routes/estimates.py, routes/catalog.py, wasteLogic.js, wasteDefaults.js, useRecalcSoffitOnOverhang.js, materialList.js. Read-only audit; register-#1–#8 wiring (separately ordered) is the only code that moved today.*
