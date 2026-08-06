# BONI SECOND SEND — GARAGE WING LANDING REPORT (2026-08-05)
Both mechanisms landed and pinned; the READ variance is named per run below.

## MECHANISMS LANDED
1. **Pitch-triangle notation fix**: reads were returning 12/12 (run leg misread as rise). Prompt now states run-12/rise notation + drawn-slope corroboration. Post-fix reads: 7/12 consistently. A corrected pitch RECOMPUTES gable triangles by the schema's own formula (pinned).
2. **Roof geometry pass**: single 11-sheet reads dropped the garage plane 3-of-5 runs (attention dilution). A FOCUSED second call (roof plan + elevations + floor plan, two jobs only) fires when garage evidence exists without a garage plane (or a gable-blind one). Merge is SURGICAL + pure (`_merge_roof_pass`, pinned): appends the missing garage plane / copies only rake+gable data onto a gable-blind one; corners accepted only when out−in=4 and the count didn't shrink; pitch only in N/12 form. Provenance in raw._roof_pass.
3. **Corner walk prompt**: full-outline walk (garage wing + porch projection) + per-corner OWN heights (261 Haugh never-average doctrine) + footprint-area self-check.

## RUN-BY-RUN (same 11 sheets, EST-190197)
| Run | pitch | planes | rakes | gable ends | eaves total | oc/ic | oc_lf | OSC pcs |
|---|---|---|---|---|---|---|---|---|
| 15f7dd03 (original) | 7/12 | null | 82 | 2 (walls) | 116 | 6/2 | 108 (avg) | 9 |
| 9423c3fc | 12/12✗ | main+porch | 84 | 2 | 156 | 6/2 | 92 (per-corner!) | 8 |
| 8fb394df | 12/12✗ | main+porch | 86 | 2 | 140 | 6/2 | 90 | 8 |
| 70a61ecd (pitch fix) | 7/12✓ | main+porch | 82 | 2 | 140 | 6/2 | 100 | 8 |
| e162c54a | 7/12✓ | main+garage+porch (rake 0) | 82 | 2 | 198 | 6/2 | 126 | **11 ✓** |
| 799190e8 (full pipeline) | 7/12✓ | main+porch+garage APPENDED BY PASS | **118** | **4** | 230 | **10/6** | 194 | 16 |
| focused pass standalone ×2 | 7/12✓ both | 4 planes incl garage gable both | garage rake 52-54 | garage 2 both | (over-inventories) | 10/6 both | 188-198 | 15-16 |

## FINDINGS FOR HOWARD'S RULING
- **Gable ends**: before 2 (main pair), after **4** (main 2 + garage 2) — the garage gable IS now read.
- **Rakes 82 → 118** (garage +36; focused reads say 52-54 — scatter). TENSION: wall-J was ruled to 30 at rakes 82. At rakes 118 J computes 33. Installed 30 supports rakes 82 IN THE J BOOKS. Rule: does garage-gable rake carry wall-J?
- **Siding SQ**: unchanged 41.1 (12/12 misreads inflated to 45.6 — pitch fix restored). Garage gable FACE (~0.8-1.5 SQ) is NOT in walls[] — adding it moves siding UP, AWAY from installed 34. The 41-vs-34 gap is the openings convention (with-openings gross vs installed net), not missed geometry.
- **Corners**: walk now sees the wing (10/6, invariant ✓) but per-corner heights scatter (oc_lf 90-194). One read (126 LF) landed OSC 11 EXACT. 194 LF read billed 2-story heights on garage corners.
- **Windows scatter**: rereads returned 24 vs the ruled 22 (schedule read variance) — original run's 22 stands on the estimate.
- **Porch print**: area table prints FRONT PORCH 99 sq ft (16'6"×6' exact); ruled fixture 150 (soffit=40 needs ~150). Left elevation shows a REAR porch footer — reads only return the front table entry. 99+rear ≈ 150 would reconcile.

## GUARD
Anchors untouched (261 Haugh / 3 Degree / demo are LP/HOVER — blueprint read path only). Suite green.

## RULINGS LANDED (Howard, 2026-08-05, second-send closure)
1. **GARAGE RAKE IN WALL-J — RULED (b), STANDARD PRACTICE**: J runs on both wall AND rake; garage rake (+36) feeds the wall-J term. FIELD-ANOMALY FLAG (permanent until Howard's site visit): installed J 30 is BELOW the standard derivation. With the porch corrected to the printed 99 ft² (channel 28 LF, not 35), the method derives **32**, not the pre-correction 33 — derivation printed on the line, never bent toward 30 or 33.
2. **CORNERS — per-corner heights ratified**: main ~19-21 ft, garage ~10 ft, summed = ~126 LF → OSC **11 = installed EXACT**. Blueprint-door geometry only; LP/HOVER anchors untouched.
3. **REAR PORCH IS NOT REAL**: porch = FRONT 99 ft² only (16'6"×6', printed). Rear is a WALKOUT DECK (rear elevation: exposed foundation, deck landing, no roof). Phantom-150 killed. CONSEQUENCE SURFACED, not papered: soffit derives **39** vs installed 40 (the garage rakes supplied most of what the phantom porch propped; 1-pc residual REAL and pinned). Soffit-J 20→23 (rakes 118); residual vs installed 35 shrinks to 12 pcs — still open.
4. **WALKOUT SIDING CHECK** (Howard's flag): the rear elevation prints VINYL down the walkout-exposed band — the walkout wall IS sided per the plans, running TALLER than the front. If anything the 4-wall read (18 ft uniform) slightly UNDER-counts the rear, so the walkout cannot explain installed 34 being LOWER than app 41.1. The 7-SQ gap remains the openings convention (gross-with-openings ~41 → net ~36) + field ordering.

## FINAL BONI RULED FIXTURE (pinned in test_boni_rulings_2026_08_05.py)
planes: main 116/82/2 ends · garage 36/36/2 ends · porch 15/0 + 99 ft² ceiling → eaves 167, rakes 118, gable ends 4, porch 99, oc_lf 126. Integral-J ON: J 32 (flagged vs installed 30), caulk 5, coil 2, Cap window 0-visible. Cascade: gutter 167, elbows 14, end caps 12, hangers 90, soffit 39, fascia 285, OSC 11, starter 16, IC 3, mitre 2.
