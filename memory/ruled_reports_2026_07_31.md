# RULED REPORTS — 2026-07-31 (report only; rulings R1–R6 received)

## 1. R2 REVERSE CHECK — ASCEND BATTEN LINES: CLEAN
- The only batten emitter is `190 Series Trim` registered `tabs=["lp_smart"]` (HOVER_MAPPING_SPEC census).
- Ascend B&B maps to the SQ panel row only: `_PROFILE_SKU_MAP[("board_batten","ascend")] → 'Ascend Composite B&B 12"'` (hover.py:2046). No separate strip anywhere — frontend included (grep: no ascend batten line site).
- REGISTERED: batten_spacing_in = LP-only, DIFFERENT-BY-NATURE. Reason: Ascend Composite B&B is a panel with the batten look integrated; no separate batten strip exists on an Ascend job. Ruled by Howard 2026-07-31.
- REGISTERED: shake_reveal_in = LP-only, DIFFERENT-BY-NATURE. Reason: vinyl shake (Pelican Bay 9") has ONE fixed exposure; no reveal choice exists. Ruled by Howard 2026-07-31.
- RATIFIED (R4): panel_size, wrap_trim_width_in, lp_soffit_type = LP SmartSide product concepts, DIFFERENT-BY-NATURE. Reasons: panel_size picks between 38-Series 4×10/4×8 sheet SKUs (vinyl/Ascend siding is SQ-coverage, not sheet-picked); wrap_trim_width picks the 540-Series board width (vinyl wraps openings with coil, not boards); lp_soffit_type steers the two-SKU LP soffit split (vinyl soffit is a single Charter Oak row). Ruled by Howard 2026-07-31.

## 2. SALES-UNIT AUDIT (app unit vs real sales unit) — 220 catalog items
Method: full ITEM_META census. Rows where app unit == plausible sales unit are
not listed (all `each/Each/PCS/PR/Box/Tube` accessory rows, SQ siding rows sold
1 SQ/carton, ROLL coil rows, JOB/SQ service rows).

| Item | App unit | Real sales unit | Verdict |
|---|---|---|---|
| Pelican Bay Shakes 9" | SQ | **1/2 SQ** (13 pcs per half square) | **FLAG — RULED (R3)**: derive qty in half squares, round UP whole; fix rides step 2 |
| 2" Nails 30 lbs | JOB | 30-lb BOX | **FLAG** — a "job" of nails is not placeable; rule the boxes-per-job rate |
| House Wrap | SQ | ROLL (9'/10' × 100'+ ≈ 10 SQ/roll) | **FLAG-VERIFY** — priced per SQ, ordered per roll; rule roll size or keep SQ deliberately |
| RainDrop | SQ | ROLL | **FLAG-VERIFY** — same as House Wrap |
| 3/8" Fan Fold | SQ | BUNDLE/CARTON (~2 SQ) | **FLAG-VERIFY** |
| Downspout 6" | LF | 10' STICK | **FLAG-VERIFY** — LF fine for seamless gutter; downspouts come in sticks |
| Gutter 6" | LF | LF (seamless) | OK if seamless — confirm |
| Caulking (per color) | Each | Tube | cosmetic — LP row says "Tube"; align naming |
| Soffit & fascia Charter Oak (PCS) | PCS | PCS or carton | **VERIFY** with your yard |
| Hangars with Screws | Each | Each or box | **VERIFY** |
| Shake (LP, PCS) | PCS | PCS/bundle | **VERIFY** |
All other rows: app unit matches the sales unit as best determinable.
NOTE: whole-unit rounding is only correct where the LINE's unit is the SALES
unit — every FLAG above is a row where rounding to the app unit can still
produce an unplaceable order.

## 3. DETECTOR AUDIT — LAYER vs SURFACE (why one-emitter missed D5)
D5 root cause, exact: test_one_waste_emitter scans source for the signatures
`(1 + …)`, `= 1 + max`, `(wastePct / 100` within a ±3-line "waste" window.
useRecalcSoffitOnOverhang.js ships `const LP_WASTE = 1.10` and multiplies by the
PRE-FOLDED constant — no signature matches. The window keyword hit ("LP_WASTE")
but the pattern did not. The mirror test executes `_bake_tab_waste` only. The
detector tests the LAYER (source text + one function), never the SURFACE (the
qty that reaches the line/print).

Classification of the sealed-rule detectors:
| Detector | Class | Can pass while rule is violated in production? |
|---|---|---|
| test_one_waste_emitter (signature scan + bake-fn units) | LAYER (text+function) | **YES — proven (D5)**: constant-folding evades the regex; hook surface never executed |
| test_one_money_emitter (same machinery) | LAYER | **YES — same evasion class** (pre-multiplied constants, derived rates) |
| whole-units pin (in one_waste_emitter) | LAYER (bake fns only) | **YES — you named it**: never tests the list that prints |
| spec-field pins (trade_specs / iteration_48) | LAYER (one layer each) | **YES — proven (3-layer silent strip)** |
| test_profile_pick_rederive_is_the_last_write | LAYER (string-asserts JSX source) | **YES** — passes if the asserted strings exist but behavior broke another way |
| printed-list pins (strings in materialList.js) | LAYER (text) | **YES** — asserts source strings, not the rendered number |
| test_pricing_parity | LAYER (locks data structures) | partially — catches edits to the structures only |
| test_ceil_epsilon_seal | LAYER (math helpers) | narrow but honest for its scope |
| test_dimensioned_sku_register | REGISTER (completeness) | NO for registration gaps — the productive class (found 7) |
| hover_field_register / intake classes | REGISTER | NO for field drops — fails on unconsumed/new fields |
| test_line_write_paths_register | REGISTER | honest — names W4/W6 as UNCOVERED rather than pretending |
| test_verification_silent_zero | SURFACE | NO — asserts the warning actually lands on the import result |
| test_acceptance_four_column | SURFACE | NO within covered rows — family axis was the gap, now mandated |
| test_*_http end-to-end tests | SURFACE | NO within covered flows |
VERDICT: three detector species. TEXT/SIGNATURE pins and single-FUNCTION pins
are LAYER — all four of this week's misses were in that species. REGISTER
detectors and HTTP/SURFACE tests have been the productive ones. Step 1's
end-to-end journey test is the SURFACE species and the one-emitter rule gains a
SURFACE assertion (golden estimate per family: printed qty == field formula) so
a rogue emitter is caught by its OUTPUT, not its spelling.

## 4. NAME-KEYED CLASSIFIER CENSUS (the D2/ghost-guard string class)
Sites where a MECHANIC keys on a product NAME rather than a family/flag:
1. `isCutProneItem` (wasteLogic.js:21-64) + backend mirror `_cut_prone_line`
   (hover.py:2680-2708) — exact-name matches for House Wrap / RainDrop / Fan
   Fold + a 2-SKU Ascend name set. **CAUSE OF D2.** Fix direction: rows should
   carry a `waste_class` flag from the spec (like `_waste_included`), not be
   re-classified by name at two sites.
2. `steerLpSoffit` (wasteLogic.js:178-179) — exact VENTED/CLOSED SKU names.
3. `useRecalcSoffitOnOverhang` (lines 24-36, 63) — five exact names + name-keyed
   catalog lookup.
4. Quote-gate detectors (gates.py:91-124) — `fam_markers` + `_SIDING_MARKERS`
   name substrings decide family conflict / no-siding.
5. Labor binding — `sheet_norm(name)` → company rates / catalog labor sheet
   (hover.py:2930) + `MISC_LABOR_ROWS` name set.
6. Line identity itself — `(tab, section, name)` string keys in the editor
   catalog merge, apply merge, rebuild inheritance, and catalog bind. THE MASTER
   INSTANCE — this is what the parked ID-binding task retires.
7. `_PROFILE_SKU_MAP` (hover.py:2037) — profile→name register (acceptable as a
   register, but renames break it; step 1's rename-collision guard covers it).
8. Colour-chip and print groupings key on coil row names (materialList).
Every one of these breaks silently on a rename ruling. The rename-collision
guard (step 1) protects the register names; ID binding (parked step 5) retires
the class.
