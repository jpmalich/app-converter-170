# MATERIAL-LIST COMPLETENESS MATRIX — 2026-07
**Report only. Nothing builds until Howard rules on this document.**

## How this matrix was built (per your correction)
Rows are seeded from the **Price Catalog** (`catalog_seed.py → SECTION_LAYOUT`, every group tab, every line item) **PLUS the standard-job kickoff checklist** (siding families · starter/J-at-base · OSC/ISC · all trim · soffit vented/closed · fascia · porch ceilings · gutter chain · caps · tear-off · accessories). Only THEN were the four derivation files audited to fill cells:
`lp_package.py` · `routes/lp_package_routes.py` · `routes/hover.py` (owner of the shared `HOVER_MAPPING_SPEC` + `_build_lines`) · `routes/ai_blueprint.py` (+ `routes/ai_measure.py`, which reuses `_build_lines`).
**A catalog row no door derives = MISSING, loudly** — even if today it is "manual by design."

### Cell legend
- **DERIVED** — auto-derives on that door; formula + ruling citation in the cell.
- **FLAGGED-PENDING** — derives or lists but carries an unresolved flag / pending ruling / $0-pending price or labor.
- **MISSING** — the door produces nothing for this row. Contractor must remember it by hand.

### What each intake door can see (measurement keys it emits)
| Door | Emits | Does NOT emit |
|---|---|---|
| **PHOTO** (AI Measure) | siding_sqft (per-wall gross × siding% + gables w×h×0.7 [book factor sealed 2026-07-19] + dormers + appendages), eaves_lf, rakes_lf, starter_lf (AI read; fallback = eaves_lf), OSC/ISC LF **+ C3 per-corner locators**, opening counts + `_ai_openings_schedule` + perimeter, `_per_profile_sqft` multi-family split, `_ai_dormers` | measured soffit area, porch-ceiling area, overhang (Job-Info field), vent_count, shutter_count, `stories`, `windows[]` for Vero/Mezzo rows |
| **HOVER** (PDF import) | siding_sqft + "+ Openings <20ft² +10%", **soffit_sqft (total)** (+ per-surface eaves/rakes/ceilings breakdown ONLY via the Hover→LP bridge `soffit_breakdown`), eaves/rakes/starter LF, corner **counts + LF (no locators)**, opening_perimeter_lf, per-window dims `windows[]`, shutter_count, vent_count, stories, frieze/drip-edge, `_hover_source=True` | per-corner locators, per-profile family split, porch-ceiling area, overhang (defaults 12"), dormer geometry |
| **BLUEPRINT** (AI Blueprint) | siding_sqft, eaves_lf (eave walls only), rakes_lf (computed from gable geometry), starter_lf = **full raw perimeter** (basis recorded; entry-door deduction downstream), corner **counts from perimeter walk** × avg wall height, openings + expanded `windows[]` → Vero/Mezzo rows, overhang_in (**form input**, default 12), per-profile callouts, appendage faces | measured soffit area, porch-ceiling area, shutter_count, vent_count, `stories` (has story_count only), dormer knee/fascia geometry (pitch/overhang NOT READ) |

---

## ⚠ HOVER-DISEASE RISK ROWS (dedicated, per your order)

### HD-1 · SOFFIT (vented vs closed)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| LP `38 Series Soffit 16x16 Vented` (eaves) | **DERIVED (fallback basis)** — ceil((overhang÷12) × eaves_LF + porch_ceiling_sqft) ÷ 21.3 × 1.10 (PDF 16" panel). Overhang is the contractor's Job-Info field, NOT read from photos → **FLAGGED-PENDING when overhang unverified** | **DERIVED (measured basis when bridge supplies it)** — `_soffit_vented_sqft` ÷ 21.3 × 1.10 (per-surface basis governs, ruled 2026-07-17, 261 Haugh). Plain Hover import w/o breakdown → overhang-fallback with **default 12" overhang (silent)** → FLAG | **DERIVED (fallback basis)** — same overhang formula; overhang_in is a typed form input (default 12) → **FLAGGED-PENDING when left at default** |
| LP `38 Series Soffit 16x16 Closed` (rakes + ceilings) | **FLAGGED-PENDING** — on LP-native package w/o measured basis the Closed row is **REMOVED** ("LP soffit panels eaves only; rakes carry 440 4/4×8 rake boards" — per-system amendment; refined 2026-07-17: measured basis reinstates it) | **DERIVED (measured basis)** — `_soffit_closed_sqft` (rakes + ceilings via porch-ceiling mechanism) ÷ 21.3 × 1.10. W/o bridge breakdown: overhang × rakes fallback | Same removal rule as PHOTO — **FLAGGED-PENDING** |
| LP `24" CTW soffit` | **MISSING** | **MISSING** | **MISSING** |
| LP `24" VSSFT` | **MISSING** | **MISSING** | **MISSING** |
| Vinyl/Ascend `Soffit & fascia Charter Oak Standard Color` | **DERIVED** — ceil(((overhang÷12) × (eaves+rakes) + porch_ceiling_sqft) ÷ 10 sqft/pc) (Iter 45 piece formula). Standard color default; Architectural variant never auto-selected | **DERIVED** — same; overhang defaults 12" (Hover PDF has no overhang) → soft FLAG | **DERIVED** — same; overhang from form input |
| `Soffit & fascia Charter Oak Architectural` / `Greenbriar` / `2T` | **MISSING** (color/product swap is manual) | **MISSING** | **MISSING** |

### HD-2 · J-CHANNEL
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| Vinyl `3/4" J-Channel Standard color` | **DERIVED** — ceil((window+patio+garage perimeter + rakes) ÷ 12.5) (Iter 78: eaves moved to Finish Trim to kill the double count; garage doors INCLUDED). Multi-region jobs: pooled row suppressed → context-split lines (window/door + rake/gable, each stating bordering region color — ruled 2026-07-18) | **DERIVED** — same; perimeter best-signal-first: per-window dims from `windows[]` → lumped opening_perimeter_lf minus entry/garage allowances → count-based fallback | **DERIVED** — same, per-window dims from blueprint schedule |
| Vinyl `3/4" J-Channel Architectural color` | **MISSING** (derivation always lands the Standard row; color swap manual) | **MISSING** | **MISSING** |
| Vinyl `1/2" J-Channel (2 per Sq)` | **MISSING** | **MISSING** | **MISSING** |
| Ascend `Ascend - J-Channel` | **DERIVED** — same J formula | **DERIVED** | **DERIVED** |
| `3/4" Soffit J-Channel (Charter Oak) Standard` | **DERIVED** — ceil((eaves + 2×rakes) ÷ 12.5) — soffit J runs 2 passes per rake (wall side + fascia return) | **DERIVED** | **DERIVED** |
| Soffit J Architectural / `1/2" J-Channel White` | **MISSING** | **MISSING** | **MISSING** |
| **J on the LP tab** | **DERIVED-BY-EXCLUSION** — composition guard STRIPS J-channel/finish-trim/coil from the LP-native package (`lp_composition_bugs`, iter97 cross-domain ruling): J on LP = composition bug, listed in `composition_guard_removed` | same | same |
| **J at B&B base** | see FAMILY DIMENSION table below — B&B base gets J, no starter (ruled) | | |

### HD-3 · PORCH CEILINGS
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| `Porch Ceiling → Charter Oak Soffit White` | **MISSING from the door** — no AI porch-ceiling read. Populates ONLY from contractor-typed Job-Info porch entries (W×L), porch sqft ÷ 10 sqft/pc via the editor recalc hook | **MISSING from the door** — Hover PDF carries NO porch-ceiling area (the disease). Job-Info entries are the only path | **MISSING from the door** — blueprint prompt does not extract porch ceilings |
| Porch ceilings → soffit roll-in | **DERIVED once Job-Info entries exist** — porch sqft feeds the Vented soffit derivation server-side on every rebuild (ruled 2026-07-24, Casile set-back); on measured-soffit Hover basis, ceilings compose as **Closed** (porch-ceiling mechanism, no venting — 2026-07-17) | same | same |
| `Wrap porch beam` | **MISSING** | **MISSING** | **MISSING** |
> **Net risk**: a contractor on ANY door who skips Job-Info porch entries quotes **zero porch ceiling material** with no flag. Recommend a ruling on whether an empty porch-ceilings list should raise a visible flag when photos/blueprints show a porch.

---

## FAMILY DIMENSION — rows whose rule differs by siding family

### Starter vs J-at-base (per-family rule, not blended)
| Family | Rule (all doors, once family + base LF known) | Door caveats |
|---|---|---|
| **Lap / Dutch lap / clap body (vinyl)** | HAS starter: ceil(starter_lf ÷ 12.5) (12'6" stick — ruled 2026-07-18, closes the ÷10-vs-÷12.5 question). Multi-region: clap-body starter takes the whole door deduction | starter_lf: PHOTO = AI read (fallback eaves); HOVER = measured Level Starter Length; BLUEPRINT = raw full perimeter, entry-door widths deducted downstream (sliders sit on starter — C4 2026-07-13) |
| **Shake (vinyl)** | HAS its own starter: `Pelican Bay Shake Starter` #65516000 — own product, NEVER priced from clap Starter (ruled 2026-07-18). Region split: shake base + gable-break LF ÷ 12.5 — **12'6" stick assumed, FLAGGED for ruling** | Region base-LF requires the per-profile breakdown → PHOTO/BLUEPRINT only. HOVER: no family split → **FLAGGED amber "verify by hand"** when shake declared without region LF |
| **B&B / vertical** | **NO starter — base gets J-channel** (ruled): B&B base LF ÷ 12.5, line carries the B&B region's product color | Same breakdown dependency; HOVER can't supply B&B base LF → amber "verify by hand" line |
| **LP (all families)** | `LP Starter — field-ripped from siding stock`: non-SKU informational line ALWAYS present; pieces = ceil(starter LF ÷ 48) (3 rips per 16' board — rip yield RULED FINAL); entry-door widths deducted; thin-waste-margin annotation when siding cushion < 0.5 pc; substitution option "dedicated-rip" (ceil(LF ÷ 16)) | **FLAGGED-PENDING on every door**: `starter_rule_divisor` pending confirmation still open (code ÷12.5 vs file-comment ÷10; Letrick delivered 20 — Howard to rule) |
| **Ascend** | `Ascend - Starter`: ceil(starter_lf ÷ 12.5) | all three doors |

### Battens (B&B only)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| LP `190 Series Trim 19/32" x 3" x 16'` | **FLAGGED-PENDING** — pcs = ceil((wall area ÷ spacing_ft + 1 run × wall height) ÷ 16), no waste on battens (ruled 2026-07-16, LPZB0884); **16" o.c. provisional; batten SKU + default spacing HELD PENDING HOWARD (BB_HELD_PENDING_HOWARD)** | **FLAGGED-PENDING ×2** — same formula but Hover carries no per-wall heights → +height term = 0, flagged "PENDING field verify" | **FLAGGED-PENDING** — same as photo |

### Family waste (per-family defaults — sealed 2026-07-24; split path ruling C 2026-07-26)
| Family | Default waste | Applied |
|---|---|---|
| Lap | 10% | the ONE visible estimate waste field governs the selected family + single-family jobs; every other family line defaults to ITS family waste — never another family's |
| B&B / vertical | 30% | same |
| Shake | 15% (CONTRACTOR-SPEC, sealed 2026-07-24) | same |
| Nickel gap | 12% (CONTRACTOR-SPEC) | same |
| — | No silent waste anywhere (sealed 2026-07-19): `waste_pct_applied` reports the actual number; missing → 0, never a hidden constant. Sealed stick-count rows (OSC/ISC/fascia/540 wrap/battens): whole-stick rounding IS the entire allowance — no % waste (ruled 2026-07-24) | |

### Headline siding lines (per family per door)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| Vinyl profile SKUs (27 rows; default lands `Charter Oak Std Dutch Lap 4.5"`) | **DERIVED** — sqft ÷ 100 SQ; multi-family houses emit ONE line per family via `_per_profile_sqft` (Iter 78z P1.2) w/ per-elevation composition note | **DERIVED** — sqft ÷ 100 from "SIDING WASTE TOTALS +Openings<20ft² +10%" row (small-opening adder baked); **no family split** — single default SKU only | **DERIVED** — like PHOTO (profile callouts read from plan) |
| Ascend Lap 7" / `Ascend B&B 12" (add 30% Waste)` | **DERIVED** — default Lap line; B&B family maps via profile split | **DERIVED** (default Lap only) | **DERIVED** |
| LP `38 Series Lap 3/8"×8"×16'` | **DERIVED** — book 11 pcs/sq SEALED 2026-07-19 (PDF 9.17 retired to reference): ceil(sqft ÷ 100 × 11 × (1+waste)); area-basis key-bound notes; chase-face ratification swap (item-3, 2026-07-19) | **DERIVED** — same book formula, Hover sqft basis | **DERIVED** — same |
| LP `Shake` | **DERIVED** — sqft ÷ coverage(7" default reveal), family waste 15% | **DERIVED only via forced-profile** (compare-profiles / materialize with profile choice); no split from PDF | **DERIVED** (callout-driven) |
| LP `Nickel Gap` | **DERIVED** — sqft ÷ NICKEL_GAP coverage, waste 12% | same caveat as Shake | **DERIVED** |
| LP B&B → `38 Series 4'×10' Panel` | **DERIVED** — sqft ÷ BB panel coverage, waste 30% | same caveat | **DERIVED** |
| LP `38 Series 4'×8' Panel` / `38 Series Vertical Panel` | **MISSING** — no derivation targets these SKUs (B&B always lands the 4×10) | **MISSING** | **MISSING** |
| `Pelican Bay Shakes 9"` (vinyl shake SKU) | **DERIVED** via profile split (shake family → vinyl tab map) | **MISSING** (no split) | **DERIVED** |
| `UNCLASSIFIED SIDING PROFILE` guard | **FLAGGED** — unknown family = qty 0 hard-amber, never priced by guess (ruled 2026-07-26 A); conservation: Σ family ft² == priced siding ft², residue → default family (ruling A 2026-07-26) | n/a (no split) | **FLAGGED** — same |

---

## OSC / ISC
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| LP `540 Series OSC 5/4"×6"×16'` (Howard's default width) | **DERIVED** — C3 locators → feature-pooled sticks (C4 ruled 2026-07-13: full sticks per edge, ALL remainders pool, ceil(pool÷16)); placement sealed 2026-07-19 (full sticks at corner BOTTOMS, splices upper only); amber locations included per presence guarantee → FLAG "field verify" | **DERIVED** — measured corner LF governs (ruled 2026-07-17): ceil(LF ÷ 16), whole-piece once; standing flag: "Hover has counts/LF, no per-corner locators — walk the corners" | **DERIVED** — corner-walk basis: count × whole-stick(height) or per-feature pooled LF (`_ai_osc_features`); (out−in) must equal 4 tripwire in prompt |
| LP `540 Series OSC 5/4"×4"×16'` | substitution option only (table-limited, re-derives from stored geometry — never a reprice) | same | same |
| LP ISC `440 Series Trim 4/4"×4"×16'` | **DERIVED** — locator feature-pooling, same C4 math | **DERIVED** — measured-LF pooling = cut-stock yield (2×~6' per stick) **with validity caveat (ruled 2026-07-17): only while corner heights ≤ 16'; taller → splice-and-round-up per corner** | **DERIVED** — count × whole-stick |
| Vinyl `Outside corners Standard color` | **DERIVED** — ceil(OSC LF ÷ 12.5) | **DERIVED** | **DERIVED** |
| Vinyl `Outside corners Architectural` / `Inside Corners (Siding) Architectural` | **MISSING** (Standard always lands; color swap manual) | **MISSING** | **MISSING** |
| Vinyl `Inside Corners (Siding) Standard color` | **DERIVED** — ceil(ISC LF ÷ 12.5) | **DERIVED** | **DERIVED** |
| Ascend `5.5" Outside Corner - MATTE` / `Inside Corners` | **DERIVED** — LF ÷ 12.5 | **DERIVED** | **DERIVED** |
| Ascend `3.5" Outside Corner - MATTE` | **MISSING** (5.5" always lands) | **MISSING** | **MISSING** |
| **Dormer OSC LF** (flagged non-priced) | **FLAGGED-PENDING** — listed as LF: dormers × 2 posts × knee height (`_ai_dormers`, ruled 2026-07-23); **NON-PRICED, pricing pending your ruling** | **MISSING** — Hover carries no dormer geometry | **MISSING** — blueprint dormer knee not read |

## TRIM (remaining)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| LP fascia+rake `440 Series Trim 4/4"×8"×16'` | **DERIVED** — (eaves + rake **slope** LF, never plan-view) ÷ 16 whole-stick = entire allowance (sealed 2026-07-24; 8" width CONTRACTOR-SPEC, Letrick precedent); always present on LP-native (ruled) | **DERIVED** — same | **DERIVED** — same (rakes computed from gable geometry) |
| LP wrap `540 Series Trim 5/4"×4"×16'` | **DERIVED** — per-opening constants (Iter 57ee + door-3-side ruling): windows 4-side ×14' + entry ×18' (21−3 sill) + patio ×19' (25−6 sill) + garage ×32' (HELD — flagged for confirmation, never silently cut) ÷ 16, + shake belly-band bump (LP PDF) | **DERIVED** — MEASURED opening perimeter governs (ruled 2026-07-17): (perim − door bottoms: garage 16' + entry 3' + SGD 8') ÷ 16 | **DERIVED** — per-opening constants (per-source convention ruled 2026-07-17: measured-perimeter basis is HOVER-path only) |
| LP `440 4/4"×6/10/12` · `540 5/4"×6/8/10/12` | substitution options only — no direct derivation (**MISSING as auto-rows**, by table design) | same | same |
| Vinyl `Finish Trim Standard color` | **DERIVED** — ceil((eaves + FULL window perimeter) ÷ 12.5) (Iter 78f: full perimeter, not sill; rakes excluded — soffit-J owns the 2-pass rake rule); region split → eave-run + window-perimeter context lines | **DERIVED** | **DERIVED** |
| Vinyl `Finish Trim Architectural` | **MISSING** (color swap manual) | **MISSING** | **MISSING** |
| Ascend `5.5" Trim (16')` | **MISSING** | **MISSING** | **MISSING** |
| `ASCEND Finish Trim` | **DERIVED** — same finish-trim formula | **DERIVED** | **DERIVED** |
| **Dormer fascia (eave) LF** (flagged non-priced) | **FLAGGED-PENDING** — listed as LF: Σ dormer width per face (ruled 2026-07-23); **NON-PRICED, pending ruling**; dormer rake LF / dormer soffit intentionally OFF the list (pitch/overhang NOT READ) | **MISSING** | **MISSING** |

## FASCIA / FRIEZE (vinyl chain)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| `Fascia/rake or frieze up to 8" coverage` | **DERIVED** — eaves LF + rakes LF | **DERIVED** (Hover also reads level/sloped frieze LF but the mapping uses eaves+rakes) | **DERIVED** |
| `.019 Coil (1 per 50' fascia)` | **DERIVED with a NAME/FORMULA MISMATCH** — extract = (eaves+rakes) ÷ **100** "per Howard", but the catalog row name says **"1 per 50'"**. One of them is wrong on its face — **needs a ruling** (also applies to the PVC/G8 fascia-coil rows, which are MISSING entirely) | same | same |
| `PVC Trim Coil (1 per 50' fascia)` / `Performance G8 (1 per 50' fascia)` | **MISSING** — only the .019 row auto-fills | **MISSING** | **MISSING** |
| `Cap porch band` | **MISSING** | **MISSING** | **MISSING** |

## GUTTER CHAIN (all 3 siding tabs)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| `Gutter 6"` | **DERIVED** — eaves LF (gutters run eaves, not rakes) | **DERIVED** | **DERIVED** |
| `Downspout 6"` | **DERIVED** — story-aware (Iter 78z P1.4): spouts = max(2, ceil(eaves÷25)); drop = avg wall height + 3' (kick+slack) | **DERIVED** | **DERIVED** |
| `elbow` | **DERIVED** — 2 per downspout (top turn + bottom kick-out) | **DERIVED** | **DERIVED** |
| `End Cap` | **DERIVED** — 2 per run; runs = max(2, ceil(eaves÷30)) (tightened Iter 78, LETRICK) | **DERIVED** | **DERIVED** |
| `Mitre` | **DERIVED** — roof-type aware: gable → inside-corner mitres only (gutter doesn't wrap); hip → every outside+inside corner; corner counts backed out of corner LF ÷ wall height | **DERIVED** (gable detection via `_ai_gable_sqft`/per-elevation — Hover import may lack these → gable check can silently read "hip"; soft FLAG) | **DERIVED** |
| `Hangars with Screws` | **DERIVED** — 1 per 2' gutter + 1 per run (run count synced to End-Cap estimate, Iter 78i) | **DERIVED** | **DERIVED** |
| `Pipe Clips` | **DERIVED** — 1 per 6' of drop, min 2/spout | **DERIVED** | **DERIVED** |
| `Gutter Sealant` | **DERIVED** — 1 tube per 4 joint points (mitres+caps+outlets) | **DERIVED** | **DERIVED** |
| `Gutter Guard (USA Shurflo)` | **MISSING** | **MISSING** | **MISSING** |
| ISS `Gutter` / `Downspout` (mirrored, Iter 57w) | **DERIVED** — eaves LF / story-aware drop | **DERIVED** | **DERIVED** |

## CAPS + THE FIVE CONTRACTOR-LABOR ROWS (current pending states shown)
All five carry the **v3 labor zeroing (sealed 2026-07-24)**: labor = $0, `lab_src="pending"` until the contractor fills the row or a company/catalog rate binds (`lab_src="company"`); a per-estimate edit wins forever (`lab_src="human"`). Both retired machine-default generations (25/75/75/100/150 and 98/107/100/138/334) rebind to $0 on rebuild. The quote surfaces one aggregated always-visible **"LABOR PENDING — contractor sets labor"** item naming every pending row.
| Row (qty derivation) | PHOTO | HOVER | BLUEPRINT | Labor state |
|---|---|---|---|---|
| `Cap window` — 1 per window | **DERIVED** | **DERIVED** | **DERIVED** | **FLAGGED-PENDING ($0, lab_src pending)** |
| `Cap entry door` — 1 per entry door | **DERIVED** | **DERIVED** | **DERIVED** | **FLAGGED-PENDING** |
| `Cap patio door` — 1 per SGD/patio | **DERIVED** | **DERIVED** | **DERIVED** | **FLAGGED-PENDING** |
| `Cap single garage door` — 1 per garage | **DERIVED** | **DERIVED** | **DERIVED** | **FLAGGED-PENDING** |
| `clean up/ haul away job debris` — 1/job when siding > 0 | **DERIVED** | **DERIVED** | **DERIVED** | **FLAGGED-PENDING** |
| Other Misc rows (`R&R gutter`, `R&R downspout`, `Cap windows with wide crown`, `Capping general`, `Cap window headers only`, `Build out w/furring`, `R&R Gable louvers`, `Fascia Return`, `Bird box`, `Flashing`, `Cap tops of bird boxes`, `Dormer upcharge`, `R&R Utilities`, `Cut out 4x4 + insulate`) | **MISSING** ×14 | **MISSING** | **MISSING** | — |
> `Dormer upcharge` deserves a callout: PHOTO **knows the dormer count** (`_ai_dormers`) yet the upcharge row never auto-fills. Cheap win if you rule it.

## TEAR-OFF / CLEAN UP
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| `Tear-Off` | **MISSING — LOUD.** No door derives the headline tear-off quantity even though every door knows siding SQ. A re-side job can leave the yard with $0 tear-off | **MISSING** | **MISSING** |
| `Wood shake tear off (requires a dumpster)` | **MISSING** | **MISSING** | **MISSING** |
| `clean up/ haul away job debris` | **DERIVED** — 1/job when siding present (labor pending, see above) | **DERIVED** | **DERIVED** |
| `Dumpster` | **MISSING** | **MISSING** | **MISSING** |

## ACCESSORIES (vinyl / ascend / LP)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| `House Wrap` (vinyl) | **DERIVED** — siding SQ (matches +10% small-opening basis on Hover) | **DERIVED** | **DERIVED** |
| `RainDrop` (ascend) | **DERIVED** — same SQ | **DERIVED** | **DERIVED** |
| `3/8" Fan Fold` | **MISSING** | **MISSING** | **MISSING** |
| `2" Nails 30 lbs` | **DERIVED** — 1 box per 15 SQ | **DERIVED** | **DERIVED** |
| `1 1/4" Trim Nails` | **DERIVED** — 1 box/job | **DERIVED** | **DERIVED** |
| `Caulking (per color)` | **DERIVED** — flat 2 tubes/job | **DERIVED** | **DERIVED** |
| `.019 Coil` (Siding Accessories) | **DERIVED** — opening-perimeter LF ÷ 100 LF/roll (Iter 79b rule) | **DERIVED** | **DERIVED** |
| `PVC Trim Coil (1 per 5 Sq)` / `Performance G8 (1 per 5 Sq)` | **MISSING** — only .019 auto-fills | **MISSING** | **MISSING** |
| `J-blocks Split/Light/UL/Jumbo` (vinyl, 4 rows) | **MISSING** ×4 | **MISSING** | **MISSING** |
| `Dryer Vents 4"` | **MISSING** | **MISSING** | **MISSING** |
| `Gable vents (round,octagon)` | **MISSING** — photo counts openings but `vent_count` never lands in measurements | **DERIVED** — HOVER Accessories → Vents Qty | **MISSING** |
| `Shutters (louvered…) standard sizes` | **MISSING** | **DERIVED** — shutter qty ÷ 2 (priced per PAIR, round up) | **MISSING** |
| `Flash tape 3 3/4"×90'` (vinyl + LP) | **MISSING** | **MISSING** | **MISSING** |
| LP `Touch up kits` | **DERIVED** — 1 per color (bump if multi-color) | **DERIVED** | **DERIVED** |
| LP `OSI Quad Max Caulking` | **DERIVED** — 2 tubes/job | **DERIVED** | **DERIVED** |
| LP `J blocks` | **DERIVED** — max(4, windows÷6 + doors÷2) proxy | **DERIVED** | **DERIVED** |
| LP `Mini Splits` | **DERIVED** — max(1, entry doors÷2) proxy | **DERIVED** | **DERIVED** |
| LP coils (`Trim Coil Alum 24"×50'`, `.019`, `PVC`, `G8`) | **DERIVED-BY-EXCLUSION** — auto-add RETIRED (iter97 composition ruling): coil on LP-native = cross-domain bug; rows stay catalog-only as flagged `cross_domain_manual_add` | same | same |

## WINDOWS DOOR (Vero / Mezzo / installation)
| Row | PHOTO | HOVER | BLUEPRINT |
|---|---|---|---|
| Vero + Mezzo per-opening rows (W×H → UI bucket) | **MISSING** — photo builds `_ai_openings_schedule` with dims but never calls `_build_window_openings`; no Vero/Mezzo rows spawn | **DERIVED** — every W-N opening → paired Vero+Mezzo rows (shared UUID); cross-kind estimate auto-pairing (Iter 41) | **DERIVED** — expanded blueprint windows → same builder |
| `Window DH/Slider - Pocket Install` | **MISSING** (no windows rows) | **DERIVED** — 1 per window (default method) | **DERIVED** |
| `Vinyl Sliding Glass Door (5'&6')` install | **MISSING** | **DERIVED** — 1 per patio door | **DERIVED** |
| `Cap window (Windows)` | **MISSING** | **DERIVED** — 1 per window | **DERIVED** |
| `Job Measure Standard Fee` / `Disposal Fee (Windows)` | **MISSING** | **DERIVED** — 1/job when any window/SGD | **DERIVED** |
| `Second/Third/Clear Story Fee` | **MISSING** — photo sets `_ai_story_count`, mapping reads `stories` → never fires | **DERIVED** — stories ≠ "1" → 1 fee | **MISSING** — blueprint sets `story_count`, not `stories` |
| `Windows - .019 Coil` | **MISSING** | **DERIVED** — Σ window perimeters ÷ 100/roll | **DERIVED** |
| `Windows - PVC/G8 Coil`, `Windows - Caulking`, Ext/Int trim-work rows, `Window Misc.` remainder, `Vero Window Quote`, Full-Fin/Large-Window/Field-Mull/Lead-Safe/Mullion rows | **MISSING** | **MISSING** | **MISSING** |

## STANDING PACKAGE-WIDE FLAGS (attach to every LP-native list)
- `expertfinish_availability_matrix` — LOOKUP pending: color-by-product-line matrix not ingested; combinations unverified.
- `bluelinx_sku_upload` — Howard's BlueLinx SKU sheet pending; BlueLinx names only until then.
- `starter_rule_divisor` — ÷12.5 vs ÷10 discrepancy, Howard to rule.
- Color architecture: per-line colors, availability flagged while unverified; substitution table-limited (no free-text SKUs), full re-derivation from stored geometry with `substituted_from` provenance.
- Escalations panel: unpriced money-surface rows, `pricing_status=pending` package lines, and the aggregated LABOR PENDING item are all surfaced per estimate (`lp_package_routes.py`).

---

# THE LOUD LIST — catalog rows NO door derives (MISSING ×3)
**Money-relevant first:**
1. **`Tear-Off`** (and `Wood shake tear off`, `Dumpster`) — headline demo labor/material, $0 on every door.
2. **Porch Ceiling rows** (`Charter Oak Soffit White`, `Wrap porch beam`) — Job-Info-entry-gated with **no flag when the list is empty** (Hover-disease #3).
3. **`3/8" Fan Fold`** — underlayment alternative, never fills.
4. **PVC / Performance G8 coils** (siding + fascia + windows variants) — only .019 ever auto-fills; fascia-coil rows also carry the **"1 per 50'" name vs ÷100 formula mismatch**.
5. **`1/2" J-Channel`** (both catalog variants).
6. **Vinyl J-blocks (4 rows) + `Dryer Vents 4"`** (LP-side proxies exist; vinyl side dark).
7. **`Gable vents`/`Shutters` on PHOTO + BLUEPRINT** (Hover-only today; photo counts vents as openings but drops them).
8. **`Dormer upcharge`** — PHOTO knows dormer count; row never fills.
9. **`Gutter Guard`**, **`Cap porch band`**, **`Flash tape`**, **Ascend `3.5" OSC`**, **Ascend `5.5" Trim`**, **LP `4'×8' Panel` / `Vertical Panel`**, **LP `24" CTW` / `24" VSSFT` soffit**, 14 Misc. Labor rows, windows-tab trim-work/misc remainder.
10. **Architectural-color variants everywhere** — derivations always land Standard color; the Architectural rows never fill (color swap is manual, uncounted).
11. **Vero/Mezzo window rows on PHOTO** — the schedule has dims; the builder is never called.
12. **`Second/Third Story Fee` on PHOTO + BLUEPRINT** — key-name mismatch (`stories` vs `_ai_story_count`/`story_count`).

# QUESTIONS QUEUED FOR YOUR RULING (no builds until you say so)
1. Tear-Off + Dumpster: derive from siding SQ (e.g., tear-off SQ = siding SQ; dumpster 1/job)? Which door(s)?
2. Empty porch-ceilings list: flag when the job plausibly has a porch, or leave silent?
3. Fascia-coil "1 per 50'" name vs ÷100 formula — which governs?
4. Dormer fascia LF + dormer OSC LF pricing (currently flagged non-priced).
5. Photo → Vero/Mezzo window rows: wire `_build_window_openings` to the openings schedule?
6. `stories` key alignment so the story fee fires on photo/blueprint?
7. Vent/shutter reads on photo/blueprint (photo already sees vents as openings)?
8. Architectural-color landing: keep Standard-always + manual swap, or add a per-estimate color-tier choice that re-lands derivations?

*Sources audited: `catalog_seed.py` (SECTION_LAYOUT, ITEM_META), `lp_conventions.py` (MISC_LABOR_ROWS, PENDING_CONFIRMATIONS, LP SKU tables, FAMILY_WASTE_DEFAULTS), `lp_smartside_formulas.py`, `lp_package.py`, `routes/lp_package_routes.py`, `routes/hover.py` (HOVER_MAPPING_SPEC, `_build_lines`, region-split, gutter/J/finish-trim helpers, `rebuild_lp_tab_lines`), `routes/ai_measure.py`, `routes/ai_blueprint.py`. No source code was modified.*
