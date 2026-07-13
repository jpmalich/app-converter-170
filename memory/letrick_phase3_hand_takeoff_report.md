# PHASE 3 REPORT — Letrick LP Hand-Takeoff Acceptance Harness (±3%)

**Date:** 2026-07-13 · **Estimate:** EST-191890 (c864939b) · **Run:** ed613872 (status: done, valid)
**Protocol:** one run in flight, code frozen during the run (no engine/conventions edits made). Per-line verdict against the sealed key ONLY. Aggregate recorded, no vote. Deviations itemized with cause. No reconciliation in either direction.
**Key:** Howard's sealed blind hand-takeoff (entered as ground truth: `/app/backend/letrick_hand_takeoff_key.py`; placeholder backed up first per backup-first rule).
**Run artifact:** `/app/memory/letrick_phase3_run_ed613872.json` (frozen derivation payload).
**Run inputs (app):** siding_sqft 1,832.7 · eaves 108.0 LF · rakes 73.4 LF · perimeter (start-course) 168 LF.
**Key inputs:** raw 2,098.5 sqft (walls+gables 1,953 + chase outer 47.97 + chase sides 97.56) · eaves 108 · rakes 69.6 · starter 165 LF (168 − 3' entry).

## Per-line verdicts

| # | Key line | Key qty | App line | App qty | Δ | Δ% | ±3% verdict |
|---|----------|---------|----------|---------|---|----|-------------|
| 1 | 38 Series Lap 8"×16' | 255 PCS | 38 Series Lap 3/8"×8"×16' | 220 PCS | −35 | **−13.7%** | **FAIL** |
| 2 | 540 OSC 5/4"×6"×16' | 8 PCS | 540 Series OSC 5/4"×6"×16' | 7 PCS | −1 | **−12.5%** | **FAIL** |
| 3 | 440 4/4"×4" ISC | 2 PCS | 440 Series Trim 4/4"×4"×16' | 3 PCS | +1 | **+50.0%** | **FAIL** |
| 4 | 540 Trim 5/4"×4"×16' | 12 PCS | 540 Series Trim 5/4"×4"×16' | 11 PCS | −1 | **−8.3%** | **FAIL** |
| 5 | 440 4/4"×8"×16' fascia+rake | 12 PCS | 440 Series Trim 4/4"×8"×16' | 13 PCS | +1 | **+8.3%** | **FAIL** |
| 6 | LP Soffit (eaves only) | 108 LF | 38 Series Soffit 16×16 Vented | 6 PCS | basis | n/a | **MATCH-ON-BASIS** (eaves-only ✓, 108 LF ✓ both; panelization 6 pcs is convention output: ceil(108 sqft ÷ 21.3 × 1.10) = 6) |
| 7 | Starter rip stock | 165 LF / 4 boards | LP Starter — field-ripped | 168 LF / 4 boards | +3 LF / 0 | **+1.8% / 0%** | **PASS** |
| C | Composition absences: NO J-channel, NO finish trim, NO coil | — | none of the three present in derivation (22 lines scanned; "J blocks" = mounting blocks, not J-channel) | — | — | — | **COMPOSITION PASS** |

**Aggregate (recorded, no vote): 3 pass · 5 fail (of 8 verdicts incl. composition).**

## Deviations itemized with cause

**1. Lap −35 pcs (−13.7%) — cause: AREA INPUT, not conventions math.**
- App run measured siding_sqft = 1,832.7 vs key raw 2,098.5 → input gap −265.8 sqft (−12.7%). The key includes the chase at 145.53 sqft (outer 47.97 + sides 97.56); gap ≈ chase (145.5) + ~120 sqft residual on walls/gables.
- Convention residual is INSIDE tolerance: app formula on the key's area = ceil(2,098.5 ÷ 9.17 × 1.10) = 252 vs key 255 → −1.2%. (The 3-pc difference is rounding order: key rounds to whole squares first, 23.1 sq × 11; app goes direct to boards. Same 10% waste, same effective coverage — 11 pcs/sq ≈ 9.09 vs PDF 9.17 sqft/pc.)
- App note: "ceil(sqft ÷ 9.17 × 1.10) — PDF coverage (LPZB0884)".

**2. OSC −1 stick (−12.5%) — cause: CORNER-LOCATION INVENTORY, incl. chimney edge model.**
- App: 7 OSC locations × whole stick = 7 (64.5 LF; 1 location amber/unconfirmed — field verify).
- Key: 4 house corners @ 1 + chimney 4 sticks from ~55 LF (2 full-height ~18.9' edges + 2 above-roofline edges, splice-and-round-up).
- The disagreement is in the location/edge inventory (7 detected locations vs 4+chimney-4 derivation), not the stick math. The app's amber location and its chimney above-roofline edge handling are the divergence surface.

**3. ISC +1 stick (+50%) — cause: EXTRA AMBER LOCATION.**
- App: 3 ISC locations (note: "includes 2 unconfirmed (amber) — field verify") vs key 2 (chase wall junctions).
- One amber ISC location in the app inventory does not exist in the key.

**4. 540 Trim −1 stick (−8.3%) — cause: DOOR CLASSIFICATION + EXACT-BOUNDARY ROUNDING.**
- App: windows 4-side (10×14') + entry 2×18' + patio 0×19' = 176 LF ÷ 16 = 11.0 exactly → 11.
- Key: 10 windows 4-side + entry 3-side (18') + patio 3-side (19') = 177 LF → 12.
- Two stacked causes: (a) the app classified BOTH doors as entry (caps confirm: "Cap entry door ×2", no patio cap) — key has 1 entry + 1 patio (Δ 1 LF); (b) 176 lands EXACTLY on 11.0 sticks, the key's 177 LF crosses to 12. A 1-LF classification difference flips a stick at the boundary.

**5. Fascia/rake +1 stick (+8.3%) — cause: WASTE CUSHION ON TRIM (flip cause) + rake LF delta (secondary).**
- App: (eaves 108 + rakes 73.4) = 181.4 LF × **1.10** ÷ 16 = 12.47 → 13.
- Key: 177.6 LF splice-and-round-up, **no cushion** → 11.1 → 12.
- Isolation: app's rakes (73.4) WITHOUT waste → 181.4 ÷ 16 = 11.34 → 12 = key. With key's rakes (69.6) WITH waste → 12.21 → 13 ≠ key. The +1 stick is caused by the 10% waste factor applied to fascia/rake trim, not by the rake measurement delta (73.4 vs 69.6, +5.5%, itself a measurement deviation).

**6. Soffit — no deviation.** Both eaves-only (per-system rule honored), both 108 LF at 12" overhang. Key states the LF requirement; the app panelizes (16"×16' vented, 21.3 sqft/pc, +10%) → 6 pcs. Recorded as match-on-basis; panel count is convention output, not a key disagreement.

**7. Starter +3 LF (+1.8%, within ±3%) — note, not a deviation verdict.** App uses full start-course 168 LF; key deducts the 3' entry door (slider sits on starter). Boards identical: ceil(168÷48) = ceil(165÷48) = 4. The rip-yield convention (3 strips/board, 48 LF/board) matches the key exactly.

## Failure-class summary (for the ruling — reported, not reconciled)
- **Dominant class: upstream inputs/inventory** (measured wall area −12.7% incl. chase treatment; corner/ISC location inventory with amber unconfirmeds; entry-vs-patio door classification; rake LF +5.5%). With the key's inputs, the app's conventions reproduce lap within −1.2% and fascia at exactly 12.
- **One pure conventions divergence:** the 10% waste cushion applied to fascia/rake trim vs the key's splice-and-round-up-no-cushion.
- **Composition doctrine holds:** zero J-channel / finish trim / coil lines derived — the LP-native composition absences are honest.

**Gate status:** Phase 4 flag-flip (`PENDING_CONFIRMATIONS["letrick_hand_takeoff"]`) NOT executed — awaits Howard's ruling on this report.
