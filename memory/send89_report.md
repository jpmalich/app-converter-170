# SEND-89 REPORT — CHIMNEY / INTERRUPTED WALL: EDGE vs INTERRUPTING, THE PARTITION, THE DROP
2026-08-21 · report only · NOTHING WIRED (no chase code, no partition code, no corner change)
Probe: `/app/memory/send89_probe.py` (read-only, runs the real propose pipeline per face) · raw output `/app/memory/send89_probe_out.txt`

## ITEM 1 — EDGE vs INTERRUPTING, per face (structural test: does the chimney's stroke chain touch the face's outer boundary at one end?)

| House | Face | Verdict | Evidence |
|---|---|---|---|
| Letrick | LEFT p2 | **EDGE → two surfaces** | chimney twins x=17.43/17.67 ARE the outline's extreme (x_span min); drawn shoulder y=22.28 joins wall line 19.45 |
| Letrick | RIGHT p2 | **EDGE → two surfaces** | chimney twins x=79.77/80.01 are the extreme max; drawn shoulder y=62.40 joins wall line 77.98 |
| Letrick | REAR p1 | **INTERRUPTING → three surfaces** | chimney drawn **FULL HEIGHT** — twin pairs 53.12/53.36 and 57.27/57.52 span plate→floor (riser bottoms 76.80, below the floor box) strictly inside the body [38.13, 80.88]; bounded by wall on both sides |
| Letrick | FRONT p1 | **neither — one surface** | full-height spanners only at the face's own boundary trim (14.01/14.25, 56.20/56.49). Above-roof cap signatures near x≈38–40 read W 0.92–1.63 ft — far under the chase's known ~5.3 ft width; reads as flue/vent ink. Howard's print settles it. |
| Boni | FRONT p1 | none | resolved plain rectangle [16.29, 62.01]; no cap signature, no interior full-height spanner |
| Boni | REAR p1 | none | resolved plain rectangle [36.11, 81.80]; no cap signature |
| Boni | LEFT p2 | n/a | still INDETERMINATE — "all spanning boundaries sit at one corner" (far member x=34.94, its cure a separate ruling) |
| Boni | RIGHT | n/a | no datum pair located |

**NO chase ink exists on any evaluable Boni face.** The pre-height run's "150 ft² chimney chase" was a MODEL claim, never line-work.

**FINDING Howard will want:** the rear elevation draws the chimney **full height down the wall**, not only above the roofline — SEND-87's rear premise ("width × height only above the roofline") is narrower than the ink. The rear is the genuine three-surface case exactly as SEND-89 rules it.

## THE PARTITION — does it sum to the whole face, exactly?

YES — exact BY CONSTRUCTION (the parts share their boundary strokes; no gap and no overlap are possible), and the arithmetic agrees to print rounding:

- **LEFT (two-way):** outline 291.33 ft² = wall rect 270.53 (29.40 × 9.20 ft) + chimney bump 20.80 (2.55 × 8.16 ft). Residue 20.79 — 0.01 rounding.
- **RIGHT (two-way):** outline 291.01 ft² = wall rect 270.12 (29.65 × 9.11 ft) + chimney bump 20.93 (2.59 × 8.07 ft). Residue 20.89 — 0.04 rounding.
- **REAR (three-way, inner-stroke split):** widths 21.43 + 5.50 + 33.22 = **60.15 ft = the face exactly**. At height 9.95 ft: wall-L 213.2 + chimney 54.7 + wall-R 330.6 ≈ outline 598.62 ft².

**THE SIDES MOVE under the ruling (reported explicitly as mandated):** side bodies revert from 31.94 / 32.24 (bump inside the body polygon) to **wall-only 29.4 and 29.65**, and the chimney profile becomes its own surface (20.8 / 20.9 ft² below the plate, plus the above-plate chase that is dropped today — next section).

## THE CHIMNEY FACE'S OWN DIMENSION, per elevation (different numbers, as ruled)

- **Sides — DEPTH:** left 2.55 ft outer-stroke (17.43→wall 19.45; inner-stroke 2.24); right **2.59 ft = 2'-7" dead-on** (80.01→77.98). (Field key: taped depth 31" = 2.58 ft — context only, never drawing evidence.)
- **Rear — W ALONG THE WALL:** inner-stroke 5.50 ft (53.36→57.27); outer-stroke 6.19 ft (53.12→57.52); the drawn cap crown runs 6.23 ft (y=56.30), the inner shoulder line 5.50 ft (y=57.35). **W STAYS UNSEALED until Howard reads it off the print.** (Field key: taped chase width 64" = 5.33 ft — context only.)

## PLATE-versus-CAP split on the side chases

- **LEFT:** ink rises to y=11.64 → **9.02 ft above the drawn plate closure** (y_top 21.18). Cap lines drawn at y=11.64 (W 3.41 ft, cap w/ overhang) and y=12.13 (W 2.75 ft). Below-plate bump: 8.16 ft down to the floor closure.
- **RIGHT:** ink rises to y=51.74/52.00 → **9.16 ft above the drawn plate closure** (y_top 61.32). **No cap horizontal joining the two riser tops was found inside the band+fence** — the cap ink either sits outside the face's datum fence or under an OCR mask box; said plainly, not guessed. Below-plate bump: 8.07 ft.
- **REAR:** chimney tops at the cap y=56.30 → **10.07 ft above the drawn plate closure** (y_top 65.84).

## IS THE CHASE ABOVE THE PLATE BEING SILENTLY DROPPED TODAY? — **YES.**

The wall outline closes at the drawn plate level (`linework_read.py` `closure()` L339-358) and the outline polygon spans y_top→y_bot only. Everything the chimney draws above that line — ~9.0–9.2 ft of rise on each Letrick side, ~10.1 ft on the rear — reaches **no surface, no proposal, no quantity**. The gable trace spans only `wall_corners` (chimney chains are excluded from wall corners by design, L388-394), and nothing else in the pipeline reads above-plate chimney ink. On the REAR the below-roof chimney area is inside the body rectangle (counted as wall, not partitioned); its above-plate rise is dropped like the sides. Roughly: left ~2.55×9.0 ≈ 23 ft², right ~2.59×9.2 ≈ 24 ft² (side profile), rear ~5.5×10.1 ≈ 56 ft² of drawn chase face reaching nothing today.

## ITEM 2 — THE FULL-HEIGHT DISCRIMINATOR, censused

Full-height spanners (plate→floor) across BOTH houses are **only** (a) each face's own boundary/corner-trim strokes at its extremes, and (b) the chimneys. **No window, door, or bay lands in the class** — no opening ink spans the datum interval on any face of either house. The discriminator ("spans the full height → interrupts; anything less → opening, stays a deduction") holds on both houses as drawn. Census per face: Letrick front 14.01/14.25 + 56.20/56.49 (boundary trim); rear 38.13/38.52 + 80.47/80.88 (trim) + 53.12/53.36/57.27/57.52 (chimney); left 17.43/17.67 (chimney) + 19.45/19.83/42.76 (wall+trim); right 54.71/77.64/77.98 (wall+trim/chase ink) + 79.77/80.01 (chimney). Boni front 16.29 + 61.66/62.01; rear 36.11/36.48 + 81.80; left 11.52/12.01 + 34.94.

## ITEM 3 — OUTSIDE CORNERS (report only; NOTHING CHANGED — Ruling G seals that path)

- **How counted today:** `outside_corner_count` / `outside_corner_lf` arrive on the measurement shape from the model read (the prompt contract, `routes/hover.py` L2278-2279); OSC material lines derive per-corner whole-stick round-up (`lp_package.osc_from_corner_locations`, corner heights required — Ruling G: a corner over a wall with no verified height is NOT DERIVABLE). `corner_locations` proper is a PHOTO-measure product; blueprint runs don't build one.
- **Does anything in that path know about projections?** **NO.** Nothing in the corner path reads elevation line-work. Letrick's stored `outside_corner_count = 4` — the plain footprint rectangle; the chase is invisible to it.
- **Corners gained under this ruling:** Letrick's one chase carries **4 corner verticals running its height** (drawn rise, floor closure to cap: (75.27−56.30) × 1.0553 ≈ **20.0 ft each**, ≈ 80 LF of corner material the takeoff has no way to see today). Composition as drawn: 2 convex verticals at the chase's outer face, 2 at the wall junctions (on the sides one junction coincides with the building's back corner). Howard's ruling words say four OUTSIDE corners per interrupting chimney — the count is his to seal; the geometry is reported so he can. **Boni gains zero** from line-work evidence (no chase ink on any evaluable face), and Ruling G blocks corner derivation there regardless (all four face heights refuse).

## THE FOUR OWED QUESTIONS

1. **WALL TWIN QUERY (chimney dead-on, wall short ~0.5 both sides) — anatomy found, no tolerance anywhere.** The chimney's OUTER stroke is drawn CONTINUOUS through the datum interval (17.43 / 80.01 span plate→floor unbroken), so the outline carries the chimney at its outer ink. The wall's outer (corner-board face) stroke is drawn FRAGMENTED at every wall corner and never spans: right L-corner outer stroke x=54.24 spans y 62.31–72.37 — misses the plate box top (62.19) by 0.12 pct and fails reach; R-corner outer ink 78.26/78.33 exists only in pieces (y 61.42–61.75, 64.04–64.60, …); left face mirrors it (18.70, 42.99/43.22 — pieces). So the wall reads its INNER continuous stroke while the chimney reads its OUTER — wall-only lands 0.3–0.6 ft/side under the sealed outer-face figures (29.4 / 29.65 vs 30'), and the chimney depth lands 2'-7" dead-on. It is which stroke the drafter drew continuously, not a tolerance.
2. **DELETION LEDGER — geometry or fact-of-deletion?** **FULL GEOMETRY.** `human_delete` snapshots the entire victim polygon (vertices_pct, scale_ref, page dims, sqft, provenance, tier, basis) — `routes/pdf_overlay.py` L817-824. `propose_rebuild_wipe` snapshots every replaced proposal in full — the propose route's wipe block (verified live on the SEND-91 Boni wipe: 4 polygons with their vertices sit in the ledger row).
3. **MERGE CLASS — is a merged run measured rather than raw ink anywhere?** **No merged-run LENGTH feeds any measurement.** Widths come from stroke POSITIONS (cluster coordinates at line-weight identity); joints are judged on raw ink merged at line-weight only (SEND-84). The single place gap_tol-merged ink lengths enter arithmetic: `closure()` uses them as WEIGHTS for the drawn closure line's mean y (`linework_read.py` L347-349) — a position, not a quantity; named here so it is on the record. (Where this report quotes a cap W from a merged horizontal, it is flagged as the cap's drawn run; the compared W figures are stroke-position readings.)
4. **TOPMOST-LINE ANCHOR — scope.** `_ccc_joint` scans jog lines ascending in y (topmost first) and returns the FIRST qualifying line. For SHOULDER PAIRS (wall × projection; no y_near) the **topmost connecting drawn line carries the jog**. FRAGMENT CHAINS pass `y_near` = their members' own termination y and search only within gap_tol of it — there the anchor is the members' termination, the drawn line only ratifies it. The topmost rule can therefore only ever fire for shoulder pairs (`linework_read.py` L156-175 vs L228-235, L251-252).

## NOTHING WIRED
No chase code, no partition code, no corner change. SEND-90 (XX cross-check) and SEND-91 (Boni re-propose) executed separately per their own authorizations. Standing rules held: no cross-drawing evidence, no estimate influences another, no job names in code, model heights hypothesis-only. EST-886440 untouched. Purity pin holds — CCC still carries UNVALIDATED at n=1 house.
