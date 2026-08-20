# SEND-71 — REPORT (2026-08-20)

## 1 · THE STRADDLE — report first, then the flag. Path: HOWARD REDRAWS.

**The money, before anything changed:**
- Zone `33e4b47a` (EST-713272, p2, 95.8 ft², qty_src human, legacy —
  predates provenance fields) is BINDING in the overlay law.
- **Which surface it supersedes: none individually.** It is a legacy
  whole-class zone (no per-surface snapshot); it participates in the
  9-zone siding group totaling 3,291.26 ft². Its captured derived
  baseline was 22.0 SQ. EST-713272 carries NO walk detail (rebuild
  test), so no per-face derived/refused status exists to supersede.
- **The stored siding line does not obey the zones at all right now:**
  it is human-set at 18.0 SQ with the overlay markers stripped by a
  later line edit. On the stored line, the zone stopping binding moves
  **0.00 SQ** → per the mandate: said so, proceeded.
- Latent condition, named: if ANY recompute runs on this estimate
  (any zone save/delete), the overlay law would rebind the class to
  32.91 SQ with the straddler / 31.95 SQ without (−0.96 SQ). That jump
  from 18.0 exists with or without this cleanup and belongs to the
  estimate's history of hand-set lines, not to this ruling.
- **What each half would carry once split at the band boundary (app
  arithmetic, REPORT ONLY):** LEFT band 1.63 ft² · RIGHT band 94.18 ft².
  The zone is a right-face shape with one vertex poking ~1% into the
  LEFT band — redrawing the shape is very likely the real fix, exactly
  what the ambiguity message predicts.

**Path taken: PREFERRED (flag only).** The zone now carries
`binding_suspended` (code FACE_AMBIGUOUS, ruling SEND-71) — it no
longer binds on any recompute path, the editor shows "NOT BINDING —
…redraw as two zones, one per face", and the app drew NOTHING. The two
new zones will be Howard's, with human provenance earned. Provenance
is not laundered in either direction. A `zones.face_ambiguous_flag`
tracking event is on the estimate.

**Register:** this is the ONLY genuine straddle in 52 zones and it
predates the SEND-66 write gate. One-off cleanup, NOT a class — pinned
(`test_straddle_2026_08_19_send71.py`) that no splitting feature exists.

## 2 · RESIDUALS AGAINST WALL + KNOWN PROJECTIONS (pre-rake-fix restated)
- LETRICK front 54.71 vs 54' wall → **+0.71** (no known projections).
- LETRICK left 35.15 vs 30' wall + 2.7' projection + ~2.45' rake grab →
  restated exactly as ordered: 30.0 + 2.7 + 2.45 = 35.15. ✓
- LETRICK rear 60.15 at the contested 9'-11" scale (see item 4).

## 3 · RAKE-EDGE SEPARATION — property, fix, re-report
**The structural property (reported before the fix):** on the gable-end
drawing, the WALL LINE terminates AT its plate — its top end lies
inside the TOP OF PLATE label's own box (19.45 → top 21.32; 42.76 →
top 21.61; box 20.57–22.10). The rake/corner-board edges continue far
above it into the roof (tops ≈11.6–11.9, ~9% above the box). On EAVE
faces no stroke terminates at the plate at all — the corner trim runs
up to the eave (front's corners top out ~9% above the box) and is the
only drawn lateral boundary.
**The fix:** where plate-terminated spanning strokes exist, the outline
is chosen among them (the drawn wall line wins over roof-borne edges);
where none exist, the spanning set stands. A preference for stronger
evidence — set membership against the datum's own box, no size
threshold, nothing tuned toward 30.

**All four faces re-reported, both houses (post-fix):**
| house | face | status | width | vs sealed |
|---|---|---|---|---|
| LETRICK | front | RESOLVED, 4 v | 54.71 ft | 54' → **+0.71** |
| LETRICK | rear | RESOLVED, 4 v | 60.15 ft @9'-11" | see item 4 |
| LETRICK | left | RESOLVED, 6 v | 32.60 ft | 30' + 2'-7" proj = 32.7 → **−0.1** |
| LETRICK | right | INDETERMINATE — "top boundary not closed at the plate level". A second drawing shares this band's y-range at x 14.8–25; the closure test catches it instead of inventing a box. Structural cure would be x-scoping by the face's own datum-line extent — a NEW mechanism, reported here and NOT built without an order. |
| BONI | front | RESOLVED, 4 v | x-extent 45.72% | no evidence scale on this face — shape real, number waits for a scale |
| BONI | rear | RESOLVED, 4 v | x-extent 45.69% | same; the two extents agree with each other |
| BONI | left | INDETERMINATE — only the left corner's twin wall lines are drawn/spanning ("one corner") |
| BONI | right | NOT_ATTEMPTED — no FIRST FLOOR datum located (the lower anchor is missing) |

The ~2.4 ft rake grab on Letrick left is GONE (35.15 → 32.60), and the
2.7 ft step (6 vertices) survives — the projection, not the rake.

## 4 · CONTESTED-SCALE WIDTHS AT BOTH CONTESTANTS (LETRICK rear)
Contestants on the rear drawing: 9'-11" (119 in) and 9'-1" (109 in).
- at 9'-11" → **60.15 ft** (residual +6.15 vs 54')
- at 9'-1"  → **55.10 ft** (residual +1.10 vs 54')
The rear geometry matches front's (both read ≈42.7% of page width);
the residual difference is the CONTESTED SCALE, not the outline.
Reported at both, tuned toward neither.

## 5 · GABLE LINE-WORK — the drawn triangle
Built `gable_triangle_from_segments`: base = the drawn wall corners at
the plate-level closure (`wall_corners` from the wall read — the
chimney chain is silhouette, never a rake-bearing corner); sides = the
drawn rakes (diagonals whose line passes within a joint of a corner and
rises inward — true endpoint pairing read from the PDF's `pts`, since
the bbox loses the slope sign); apex = their drawn intersection, which
both drawn rake ends must reach within a joint. Refusals are named.
- **LETRICK left gable: TRACED. 129.98 ft²** at that face's own scale —
  vs 131.25 ft² pure half-base×rise and 183.75 ft² under the 0.70
  derived convention (which carries waste). The drawn triangle and the
  pure triangle agree within 1%; nothing was tuned toward either.
- LETRICK right gable: starting rectangle stands (wall outline refused
  on that drawing — the gable read only extends a trusted wall read).
- BONI: no wall read is trusted on the gable-bearing faces (left one
  corner, right no FF datum) → no trace attempted.
Proposals carry tier `gable_outline` (traced) vs `gable_rectangle`
(starting shape), each with its own basis and notice; the traced notice
states both figures plainly instead of the OVERSTATE warning.

Standing rules held: no cross-drawing evidence, no estimate influences
another, no job names in code, model heights hypothesis only.
EST-886440 untouched (423 on derived writes). Purity pin holds —
nothing tunes toward 54, 30, 58, 30'-2", 33, or 2'-7".
