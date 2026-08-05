# BONI HOUSE (EST-190197) — BLUEPRINT DOOR vs INSTALLED — DELTA REPORT
2026-08-05 · report only, no code · demo-locked · findings await Howard's ruling one at a time
Run: ai_blueprint_runs 15f7dd03 · 11 sheets · scale confidence high · walls read: front 58', back 58', left 39' (gable 11.5'), right 39' (gable 11.5') · pitch 7/12 · overhang 12" (correct, untouched)

## FINDING 1 — EAVES 116 vs ~167: MECHANISM TRACED
WHERE 116 COMES FROM (two reinforcing steps, same blind spot):
1. The extraction SCHEMA (ai_blueprint.py line 188) defines eaves_lf as "sum of widths of EAVE walls only ... for a typical gable-roof house = the two non-gable wall widths". The model followed it exactly: gables sit left/right, so eaves = front 58 + back 58 = 116. The schema hard-models ONE roof over ONE four-wall rectangle.
2. The Iter-57w defensive override then RECOMPUTES eaves from the same walls[] (measure_staging.eaves_from_walls: sum of non-gable wall widths) = 58+58 = 116 again. Defence and read share the blind spot.
WHAT GOT DROPPED: sheet 11 is identified as "ROOF PLAN / useful_for: roof" but is consumed ONLY for pitch + roof type. No pipeline stage sums eave runs per ROOF PLANE. The garage (3-car, projecting — footprint_area 2351 ft² vs 58×39=2262 ft², ~89 ft² of projection the rectangle can't hold) and the covered porch each carry their own eave fascia; appendages[] (the only schema slot for attachments) came back EMPTY and is wall-face-only anyway — it has no roof/eave slot. Planes counted: main roof's two eave sides (front 58 + back 58). Planes dropped: garage roof eave run(s) + porch roof eave (together ≈ 51 LF).
CONFIRMED MECHANISM FOR THE FIX (no code yet): eaves must be summed across ALL roof planes — main + garage + porch — read from the roof plan + elevations, not derived from the four-wall rectangle. The defensive override must also become plane-aware or step aside when a plane-summed read exists.

### THE CASCADE AT EAVES = 167 (one input, formulas untouched)
| Line       | Formula (as shipped)                          | App @116 | @167 lands | Installed | Verdict |
|------------|-----------------------------------------------|----------|------------|-----------|---------|
| Gutter LF  | eaves                                         | 116      | **167**    | 167       | EXACT |
| Elbows     | ceil(eaves/25) downspouts × 2                 | 10       | **14**     | 14        | EXACT |
| End caps   | 2 × max(2, ceil(eaves/30)) runs               | 8        | **12**     | 12        | EXACT |
| Hangers    | ceil(eaves/2) + runs                          | 62       | **90**     | 75        | overshoots +15 — see calibration note |
| Soffit pcs | (overhang×(eaves+rakes) + porch_ceiling)/10   | 20       | **25**     | 40        | remainder is the PORCH CEILING term (currently 0) — see note |
| Soffit-J   | ceil((eaves+rakes)/12.5)                      | 16       | **20**     | 35        | cascade moves it; residual ~187 LF — see note |
Elbows and end caps landing EXACT at 167 independently corroborate 7 downspouts / 6 runs — the formulas are right, the INPUT was short. Also moved by the same fix (installed values not provided — worth pulling): Downspout sticks 11→15 · Pipe clips 20→28 · Gutter sealant 4→5 · Fascia LF 198→249 · Soffit-side .019 coil 2→3 · Finish trim 15→19 (its eave term).
NOTES INSIDE THE CASCADE (surfacing, per "anything else off"):
- HANGERS: at true eaves the 2.0-ft spacing formula lands 90 vs installed 75. Installed math is almost exactly 167/2.2. Question for ruling: is the crew's spacing 2.2 ft (or 2.0 ft without the +1/run bonus)? Small, but it's a formula constant, not an eave problem.
- SOFFIT: the miss is NOT overhang (12" is right). Fixing eaves lands 25 of 40; the remaining ~150 ft² is the PORCH CEILING — the formula already carries a porch_ceiling term and it is 0 because the same dropped porch that hid the eave also hid its ceiling. One structure, two consequences. A ~150 ft² porch ceiling lands soffit at ~40.
- SOFFIT-J: eaves fix lands 20 of 35. The ~187 LF residual smells like the porch ceiling's perimeter channel and/or a second eave-side pass — needs the porch geometry off sheet 11 before proposing numbers. Flagged, not guessed.

## FINDING 2 — INTEGRAL-J WINDOWS: ONE FACT, TWO LINES (+ TWO TO RULE)
App J-channel = ceil((windows 337.2 + patio 22 + garage 64 + rake pass 82)/12.5) = 41. App caulk = 22 windows + 5 doors = 27.
- CAULK: drop the 22 integral-J windows → 5; if garage doors are also uncaulked (integral trim) → 3. Installed 4 sits exactly in that band. LANDS.
- J-CHANNEL: drop the full 337 LF window term → (22+64+82)/12.5 = **14** vs installed 30. The deduction is real but OVERSHOOTS the landing by ~200 LF: the installed job bought MORE total J (30+35 = 65 pcs ≈ 812 LF) than the app computed WITH windows (41+16 = 57 pcs ≈ 712 LF). Reading: the crew's extra J lives on the runs Finding 1 dropped (porch ceiling channels, true-eave runs) — the window deduction and the eave/porch additions move in opposite directions and roughly balance the J books. So: Finding 2 is correct AND masked by Finding 1 in this SKU. Both must land together before the J line matches installed.
- SAME FACT, POSSIBLY TWO MORE LINES (for ruling, not assumed): (a) window-wrap .019 coil (5 rolls) carries the same 337 LF window term — new-construction integral-J windows are typically not wrapped → would drop to ~2 rolls (doors only). (b) "Cap window 22 Each" — capping wraps existing frames; a new-build with integral-J windows likely installs 0. If the installed list shows no window coil/caps, both belong to this finding.
PROPOSED REPRESENTATION (build nothing until ruled): a per-job window-type input on the estimate spec row — "Windows carry integral J-channel: yes / no" (default no; blueprint door may PRE-SUGGEST yes when the window schedule says vinyl new-construction, contractor confirms). When yes, the ONE flag: (1) removes window perimeter from the wall-J term, (2) removes windows from caulk-per-opening, and — if Howard rules them in — (3) removes the window term from window-wrap coil and (4) zeroes Cap window. Alternative shapes if preferred: per-window-schedule flag (mixed jobs), or a company-level default with per-job override. The flag must print its own provenance note on every line it touches.

## FULL APP-vs-INSTALLED TABLE
| Line                          | App        | Installed | Δ        | Classification |
|-------------------------------|------------|-----------|----------|----------------|
| Dutch Lap siding              | 41.1 SQ    | not given | —        | eaves-independent; no finding |
| Starter                       | 16 PCS     | 16        | 0        | CORRECT (do not touch) |
| Inside corners                | 3 PCS      | 3         | 0        | CORRECT (do not touch) |
| Outside corners               | 9 PCS      | not given | —        | verify against installed |
| Finish trim                   | 15 PCS     | not given | (→19)    | eaves-cascade (eave term) |
| 3/4" J-Channel (wall)         | 41 PCS     | 30        | −11      | integral-J (lands 14) + eaves/porch J masking (+~16) — both findings meet on this SKU |
| .019 coil (window wrap)       | 5 ROLL     | not given | —        | integral-J question (c) — rule it |
| House wrap                    | 4.57 ROLL  | not given | —        | eaves-independent |
| Nails (2" / trim)             | 3 + 1 BOX  | not given | —        | standard |
| Soffit & fascia panels        | 20 PCS     | 40        | +20      | eaves-cascade (→25) + porch ceiling (~150 ft² → ~40) |
| Soffit J-Channel              | 16 PCS     | 35        | +19      | eaves-cascade (→20) + porch/2nd-pass residual (flagged) |
| Fascia/rake LF                | 198 LF     | not given | (→249)   | eaves-cascade |
| Soffit-side .019 coil         | 2 ROLL     | not given | (→3)     | eaves-cascade |
| Caulking                      | 27 EA      | 4         | −23      | integral-J (lands 5; 3 if garage doors excluded) |
| Gutter 6"                     | 116 LF     | 167       | +51      | EAVES ROOT CAUSE |
| Downspout sticks              | 11         | not given | (→15)    | eaves-cascade |
| Elbows                        | 10         | 14        | +4       | eaves-cascade — lands 14 EXACT |
| End caps                      | 8          | 12        | +4       | eaves-cascade — lands 12 EXACT |
| Hangers                       | 62         | 75        | +13      | eaves-cascade — lands 90; spacing constant 2.0 vs 2.2 to rule |
| Mitres                        | 2          | not given | —        | gable rule applied; verify |
| Pipe clips                    | 20         | not given | (→28)    | eaves-cascade |
| Gutter sealant                | 4          | not given | (→5)     | eaves-cascade |
| Cap window                    | 22 EA      | not given | —        | integral-J question (d) — new-build likely 0; rule it |
| Cap entry/patio/garage        | 2/1/2      | not given | —        | verify against installed |
| Clean up / haul away          | 1 JOB      | —         | —        | standard |

## WHAT WAS RIGHT (untouched, per the order)
Starter 16=16 · inside corners 3=3 · footprint perimeter 194 · window schedule read (22 windows, sheets 6–7) · multi-use color split (separate siding-coil/soffit-coil, siding-J/soffit-J per use) · overhang 12" · pitch 7/12 · gable/hip call.

## RULING QUEUE (nothing builds until each is ruled)
1. Eaves = sum across ALL roof planes (main+garage+porch), roof-plan-aware; defensive override becomes plane-aware. Cascade proof above.
2. Porch ceiling ft² captured from the same dropped porch (soffit + its perimeter J).
3. Integral-J window flag — representation choice (per-job toggle / schedule flag / company default) and which of the 4 lines it touches (J, caulk ruled; coil, caps proposed).
4. Hanger spacing constant 2.0 (+1/run) vs installed 2.2.
