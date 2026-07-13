# PHASE 3 REPORT — RE-FILED (v2) — Letrick LP Hand-Takeoff vs Sealed Key (±3%)

**Supersedes:** v1 (rejected for provenance defect — it consumed run ed613872, the 2026-07-11 C3 corner run, not a fresh Phase 3 extraction). v1 retained at `letrick_phase3_hand_takeoff_report.md` for the record.

## (1) Provenance — what the harness consumed
- **Fresh run fired for Phase 3:** run_id `5005d6eb3ddb4d32ae7d51ec6a3fa967`, created **2026-07-13 18:24:58 UTC**, status done, valid. Same cached photo set (rerun path), current-state extraction pipeline. One run in flight; code frozen throughout (no engine/conventions edits).
- **Measurement payload hash:** `cb819d0f92fa2151` (sha256/16 of the run's measurements, sorted keys).
- **Derived package hash:** `53a0bf46e993d719` (sha256/16 of [name, qty, unit] canon).
- **Artifacts:** `/app/memory/letrick_phase3_run_5005d6eb.json` (frozen derived package); prior run artifact retained.
- **Extraction variance note (same photos, 2 days apart):** ed613872 → 5005d6eb: siding 1,832.7 → 1,687.2 sqft (−7.9%), windows 10 → 9, rakes 73.4 → 70.0, starter 168 → 178, OSC locations 7 → 6, ISC 3 → 2. Extraction non-determinism is itself a Layer A finding.

## (2) Two-layer scoring

### LAYER A — measurement input deltas (app extracted geometry vs key geometry)
| Input | Key | App (5005d6eb) | Δ | Verdict |
|---|---|---|---|---|
| Siding area (raw, no window deductions — both) | 2,098.5 sqft | 1,687.2 sqft | **−19.6%** | FAIL |
| — gable component | 367.5 (×0.7 on 525 raw) | 270.0 | −26.5% | FAIL (see lap decomposition) |
| — non-gable (walls + chase) | 1,731.0 (walls 1,585.5 + chase 145.5) | 1,417.2 (not decomposed by run) | −18.1% | FAIL |
| Eaves | 108.0 LF | 108.0 LF | 0% | PASS |
| Rakes | 69.6 LF | 70.0 LF | +0.6% | PASS (was 73.4 on the old run) |
| Start-course | 168 LF perimeter (165 after 3' entry deduction) | 178.0 LF | +6.0% vs perimeter | FAIL |
| Windows | 10 | 9 | −1 | FAIL |
| Doors | 1 entry + 1 patio | 2 entry + 0 patio | classification | FAIL (named in §4) |
| OSC locations | 8 edges (4 house + chimney 2 full-height 18.91' + 2 above-roofline) | 6 (4 house + 2 chimney, 1 amber) | −2 edges | FAIL — the 2 above-roofline chimney edges were not detected |
| ISC locations | 2 (chase junctions) | 2 (1 amber) | 0 | PASS — see §3 |

### LAYER B — conventions graded independent of extraction (app's rules run on THE KEY'S geometry; engine invoked read-only)
| Line | Key | App rules on key geometry | Δ | Layer B verdict |
|---|---|---|---|---|
| 38 Series Lap | 255 | **252** | −1.2% | **PASS** (inside ±3%; residual is rounding order — key rounds to whole squares ×11/sq, app goes direct to boards ceil(sqft÷9.17×1.10); same 10% waste, same effective coverage) |
| 540 OSC | 8 | **9** | +12.5% | **FAIL — conventions divergence.** App grants a whole stick to EVERY ≤16' location (presence guarantee: the 2 above-roofline edges @~8.59' each take a full stick) and pools only over-length tails (2×2.91' → 1); key pools ALL chimney LF: ceil(55÷16)=4. 4+5 vs 4+4. |
| 440 4" ISC | 2 | **2** | 0% | **PASS** |
| 540 Trim | 12 | **12** | 0% | **PASS** (10 windows ×14' + entry 18' + patio 19' = 177 LF ÷16 → 12; engine note reproduces the key's derivation exactly on matched inputs) |
| 440 8" fascia+rake | 12 | **13** | +8.3% | **FAIL — conventions divergence.** 177.6 LF ×1.10 ÷16 = 12.21 → 13; key = splice-and-round-up, no cushion: 177.6÷16 = 11.1 → 12. The 10% waste cushion on trim is the entire flip. |
| Soffit | 108 LF eaves-only | 6 pcs from 108 LF (eaves-only honored) | basis | **PASS** (match-on-basis) |
| Starter | 165 LF → 4 boards | 165 LF → **4 boards** | 0% | **PASS** (rip yield 3 strips/board = 48 LF/board matches key exactly) |

**Conventions score (Layer B on matched geometry): 5 PASS · 2 FAIL (OSC per-location whole-stick doctrine; fascia waste cushion).** Per the scoring rule, only these two lines fail CONVENTIONS; all other line deltas are extraction-class.

### Combined per-line verdicts (fresh run vs key, ±3%)
| Line | Key | App | Δ% | Layer A | Layer B | Failure class |
|---|---|---|---|---|---|---|
| 38 Series Lap | 255 | 203 | **−20.4%** | FAIL | PASS | extraction |
| 540 OSC | 8 | 6 | **−25.0%** | FAIL | FAIL | both |
| 440 4" ISC | 2 | 2 | 0% | PASS | PASS | — (§3) |
| 540 Trim | 12 | 11 | **−8.3%** | FAIL | PASS | extraction |
| 440 8" fascia | 12 | 13 | **+8.3%** | PASS | FAIL | conventions |
| Soffit | 108 LF | 6 pcs (=108 LF) | basis | PASS | PASS | — |
| Starter | 165 LF / 4 bd | 178 LF / 4 bd | +7.9% LF / **0% boards** | FAIL (LF) | PASS (boards) | extraction (+ open sub-question: entry-door 3' deduction on start-course lives in neither layer cleanly — key deducts, app consumes extracted start-course as-is) |
| Composition | NO J-channel / finish trim / coil | none present (22 lines scanned) | — | — | — | **COMPOSITION PASS** |

**Aggregate (recorded, no vote): 3 pass · 4 fail · 1 split (starter).**

## (3) ISC — reconciled-to-residual (per ruling)
Fresh run ISC count = 2, matching the key's 2 chase junctions; one carries amber tier ("chimney chase right side meets back wall", unconfirmed). Scored **reconciled-to-residual**, not FAIL: the amber is the pre-logged drift pair, provenance-limited, surfaced on the line note ("includes 1 unconfirmed (amber) location — field verify"). No stick-count consequence on this run (2 sticks either way).

## (4) 540 Trim door classification — named precisely
- **Which opening:** the BACK-elevation slider (key: patio slider, 25' opening perimeter, 6' sill).
- **Classified as what:** the fresh run's openings schedule reads it as `entry_door 36×80, back elevation` — an entry-door class at entry-door size.
- **3-side vs 4-side applied where:** NO 4-side misapplication anywhere — both key and app apply 3-side head+legs to all doors and 4-side to all windows. The stick delta comes from the door-CLASS wrap length: app derived entry 2×18' (21−3 sill); key has entry 18' + patio 19' (25−6 sill). Engine note: "entry 2×18', patio 0×19'".
- **Additional extraction hit on this line (fresh run):** windows 9 vs key 10 → windows 4-side 9×14'=126 + 36 = 162 LF ÷16 → 11 vs key 177 LF → 12. On matched geometry the conventions produce exactly 12 (Layer B PASS) — the whole −1 stick is extraction (1 missing window + slider class).

## (5) Lap −20.4% — full decomposition
| Component | Key | App (fresh run) | Δ | Where it lives |
|---|---|---|---|---|
| Gables | 367.5 sqft = 525 raw × **0.7** | 270.0 | −97.5 | **Gable factor**: app's 270 ÷ 525 raw ≈ **0.51 ≈ triangle ½**, vs the key's 0.7 convention. If the app's gable basis is ½, this alone is ~105 sqft. (Reported as the identifiable sub-cause; the run does not expose its gable factor explicitly.) |
| Chase faces | 145.53 (outer 47.97 + sides 97.56 = 2.58'×18.91'×2) | not separately extracted; not attributable in the aggregate | up to −145.5 | **Chase face inclusion**: the run detects the chase EDGES (corner inventory) but the wall-area aggregate gives no evidence the chase outer/side faces were added to siding area. |
| Walls incl. stepped segments | 1,585.5 (front 483.8 + back 535.7 + stepped sides ~566.4) | ~1,417.2 minus whatever chase it contains | −168.3 (if zero chase included) | **Stepped-side underread**: avg wall height extracted 8.4' vs the key's staircase courses on the sides; the stepped foundation (documented for this house) under-reads when a wall is measured at a single height. |
| Waste application | ×1.10 | ×1.10 | 0 | identical — eliminated as a cause (Layer B) |
| Board conversion | 23.1 sq × 11/sq → 255 | ceil(sqft ÷ 9.17 × 1.10) → on key area: 252 | −1.2% | rounding order only — inside tolerance |
- Sum check: gables −97.5 + chase −145.5 + stepped-walls −168.3 = −411.3 = exactly the total area gap (2,098.5 − 1,687.2). The three buckets fully account for the delta; the split between "chase omitted" and "stepped underread" cannot be conclusively separated from the run's aggregate — both are flagged.

## Failure-class summary
- **Extraction (dominant):** area −19.6% (gable factor ~½ vs 0.7 + chase faces + stepped sides), 1 missing window, back slider classified entry, 2 above-roofline chimney edges undetected, start-course +6%, plus run-to-run extraction variance (−7.9% area between identical-input runs 2 days apart).
- **Conventions (2, isolated by Layer B):** OSC per-location whole-stick presence guarantee vs key's pooled chimney LF (+1 stick on matched geometry); 10% waste cushion on fascia/rake trim vs splice-and-round-no-cushion (+1 stick on matched geometry).
- **Composition doctrine: clean** — zero J-channel / finish trim / coil on both runs.

**Gate status:** Phase 4 flag-flip NOT executed — awaits Howard's ruling on this re-filed report.
**Approved-in-principle, sequenced after this filing:** field-verify checklist for amber locations (presence-guarantee doctrine surfaced to the user).
