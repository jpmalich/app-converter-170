# SEND-94 — CHASE PARTITION WIRED · HUMAN 5'-4" MARKED AS HUMAN · REAR STAYS CONTESTED
2026-08-21 · code: `linework_read.py` (chase detection), `routes/pdf_overlay.py` (partition, chase surfaces, human dimensions) · pins: `tests/test_partition_2026_08_21_send94.py` (9) · live responses: `memory/send94_propose_letrick.json` / `..._boni.json`

## RULINGS REGISTERED
- Letrick rear chase SIDING width = **5'-4" (5.3333 ft)** — the 6'-0" is the brick facade, not the sided surface.
- Rear height **stays CONTESTED** (9'-11" vs 9'-1⅛") — never resolved, every rear quantity reported at both.

## ITEM 1 — THE 5'-4" IS A HUMAN DIMENSION, MARKED AS ONE
Stored as DATA, never in code (`human_dimensions` collection, estimate-scoped):
`{face_id: back, kind: chase_width_ft, value_ft: 5.3333, basis: "rear chase width 5'-4\" — supplied by Howard from the prints, not read from this drawing", supplied_by: Howard (SEND-94)}`.
It rides the chase zone's basis verbatim plus "**HUMAN DIMENSION, never presented as derived**; drawn strokes read 5.5 ft (inner) / 6.19 ft (outer) at the carried scale", rides `proposed_from.chase.width_source = "human"` with the full human_dimension record, and survives confirm through the existing confirmed_from law (no laundering). The purity pin is untouched: nothing in code tunes toward 5.33 — the app carries Howard's figure as Howard's figure.

## ITEM 2 — THE SUM HOLDS BY CONSTRUCTION (no tolerance anywhere)
`_chase_partition(face, chase, drawn_ratio)` in integer hundredths of a foot: the chase is the (human-set) value; the walls are the remainder split at the chase's drawn position; the last wall is `face − chase − wall_L`. Pinned exact at BOTH contestants, with the chase fixed and the walls shifting:

| scale | wall-L | chase | wall-R | sum |
|---|---|---|---|---|
| 9'-11" (face 60.15 ft) | 21.50 | **5.33 (human)** | 33.32 | **60.15 exact** |
| 9'-1⅛" (face 55.10 ft) | 19.52 | **5.33 (human)** | 30.25 | **55.10 exact** |

(Howard's own arithmetic point confirmed: 21.43 + 5.33 + 33.22 = 59.98 ≠ 60.15 — mixing the sealed width into scale-derived parts does not close; the remainder construction does, at either scale.)

## ITEM 3 — REAR REPORTED AT BOTH CONTESTANTS
The rear zones carry tier `contested_pick_larger` with both rails named on every basis; the chase basis adds: "this face's scale stays CONTESTED (9'-11 vs 9-1⅛) — wall sections shift with the contestant, the chase width is fixed either way". Above-plate recovery on rear: **54.37 ft² at 9'-11" / ≈49.8 ft² at 9'-1⅛"**. The registered observation stands unchanged: the evidence leans one way and the app may not act on it.

## ITEM 4 — BRICK FACADE: WHAT THE DRAWING SHOWS (non-blocking, reported)
**No brick hatch or material note sits at the chase location on the rear elevation.** The only brick/stone strings on p1 are foundation boilerplate: "USE BRICK FORM" (x=64.1, y=79.5 — below the floor datum, foundation zone, not the chase at x 53–57) and the general note "…LOCATION OF BRICK OR STONE ON FOUNDATION". One flag for Howard's next pass: the FIRST FLOOR PLAN (p7) prints "**STONE FACADE**" at x≈62% — plan-sheet text, cannot be borrowed onto the rear elevation (standing rule), but it is the kind of note that would make the surround EXTERIOR if it belongs to this wall. Until Howard reads it, the partition carries the full wall sections and no brick deduction exists.

## WIRED — AS RULED, LIVE ON BOTH HOUSES (suite green, see stamp)
- **Sides revert to WALL-ONLY**: left body 29.40 ft, right body 29.65 ft (were 31.94/32.24 with the bump inside). **The bump moved to its own surface** — `chase:left` (drawn depth 2.55 ft) and `chase:right` (2.59 ft), zones running from their above-roof ink tops (y=11.64 / 51.74) to the floor closure.
- **Rear is three surfaces**: wall section 1 (38.13→53.36), `chase:back` (53.36→57.27, human 5'-4"), wall section 2 (57.27→80.88), each its own proposal.
- **Partition pin runs on every face, every house, every time**: `partitions` payload per face with `sums_exact` — Letrick left/right (edge, pct-exact: 23.31+2.02=25.33 ✓, 23.27+2.03=25.30 ✓), rear (interrupting, ft-exact by construction ✓). Boni: no chases on any evaluable face → no partition, stated by absence with the zones unchanged.
- **XX CROSS-CHECK CONFIRMED AFTER THE REVERT: still "left 29.4 ft, right 29.65 ft — differ by 0.25 ft"** (silhouettes 31.94/32.24 — 0.30 — still riding uncompared). Boni still SILENT_INDETERMINATE on the p4 tie.
- **The above-plate chase stopped being dropped — ft² RECOVERED PER FACE (the under-read, numbered):**
  | face | recovered ft² |
  |---|---|
  | Letrick left (chase above plate, 2.55 ft × 9.02 ft) | **23.00** |
  | Letrick right (2.59 × 9.16) | **23.72** |
  | Letrick rear (5.33 human × 10.20) | **54.37** at 9'-11" / ≈49.8 at 9'-1⅛" |
  | total newly-carried drawn chase area | **≈101 ft² (± the rear contestant)** |
- Human-zone guard held again live: Letrick's human front zone (1177.13 ft²) untouched through the re-propose wipe; wipes ledgered with full polygons.
- Chase detection is drawn structure only: EDGE = the outline's own shoulder chain to a non-plate-terminated projection member; INTERRUPTING = full-height members strictly inside the body joined by a drawn cap whose ends land ON their tops (an eave/ridge crossing never qualifies — pinned). The full-height discriminator is pinned: window-height ink never becomes a chase.

## STILL-QUEUED REPORTS (delivered here, nothing wired)
- **Boni's chase — drawn vs claimed**: the latest stored model run claims a `chimney_chase` appendage on the LEFT wall, 6.0 × 2.0 ft, height 25 ft, `faces_sqft: 150` (the stored figure; the 200 ft² remembered in the send is not on the latest run doc). The drawn ink gives **nothing**: no chase signature on any evaluable Boni face, and the LEFT face — exactly where the model puts it — is the face line-work refuses ("all spanning boundaries sit at one corner"). **The ratio is: 150 claimed / 0 locatable in ink.** The model's chase remains hypothesis-only; nothing carries it.
- **Fragment-joining on the wall's outer stroke (REPORT ONLY — the merge class stays closed)**: the outer (corner-board) stroke exists in PIECES at every Letrick wall corner, with gaps up to ~4.6 pct (≈3.7 ft at scale) — far beyond line-weight, exactly the class the merge ruling sealed. If those fragments were joined regardless: left face outer-outer 18.70→43.22 would read **30.92 ft** (inner-edge pairing 19.56→42.99: 29.55), right face 54.24→78.33 would read **30.70 ft** (54.44→78.26: 30.36) — against sealed 30'-0" on both. Under current law the walls stay 29.40/29.65 read on the continuous inner stroke. No change made.

## STILL QUEUED (not done)
Chase corners as a visible unpriced note (no corner-count change) · height cards · Ruling V conversion · brick-facade answer from Howard (item 4) · rear W stands sealed at 5'-4" unless Howard's next pass moves it.

Standing rules held: no cross-drawing evidence, no estimate influences another, no job names in code (the 5'-4" lives as estimate data), model heights hypothesis-only. EST-886440 untouched. 423 on every derived write. Purity pin holds — CCC carries UNVALIDATED at n=1 house.
