# SEND-82 — RULING CCC TESTED. REPORT. NOT WIRED.
Probe: `memory/send82_ccc_probe.py` (re-runnable, read-only). Tested
per the control standard: all 7 dropped strokes, all 8 kept boundaries
as controls, and EVERY joint the system currently accepts.

## The own-length-vs-gap numbers (both houses, every joint)

| joint | len/gap | verdict under CCC |
|---|---|---|
| LETRICK right TRUE SHOULDER (wall 77.98 → chimney 79.77, jog y=64.55 x[78.32,79.37]) | **59%** | the one real shoulder in evidence |
| LETRICK left FRONT-EDGE CHAIN's jog (43.22↔45.30, x[43.41,43.91]) — the wrong-edge bump accepted today | **24%** | dies under any spanning reading |
| LETRICK left tick candidates joining wall 19.45 → back-edge 17.43/17.67 | **1–8%** | never a shoulder |
| legitimate long jogs, both houses (course-line chains 17.02↔43.22, 17.57↔43.22; right 54.24↔78.33; wall-to-chimney course lines) | **100–105%** | pass, all already neutralized by the contradiction rule where they must be |
| kept boundaries (8 controls) | n/a — singles carry no joint | CCC takes nothing from them |

**The separation is real: 59% vs ≤24%, no overlap, on everything both
houses contain.**

## But CCC-as-literal FAILS the one true shoulder — said plainly
"A line that claims to span a gap must actually span it" with only the
module's line-weight allowance (±0.03) demands ≥97% of the gap. The
TRUE shoulder covers 59%: its drawn ink stops 0.34 short of the wall
member and 0.40 short of the chimney member — because both members are
DOUBLE-DRAWN (wall twins 77.64/77.98, separation 0.34; chimney twins
79.77/80.01) and the shoulder terminates at the INNER strokes while
the boundary is the outer line (its left end touches drawn vertical
ink at 78.33 within 0.01). So the literal property rejects the only
legitimate shoulder in either house — exactly the failure Howard asked
to see before shipping.

Zero-parameter alternatives tested and dead:
- "ends touch drawn ink at the jog's y (line-weight)": the true
  shoulder's right end touches nothing within 0.40 — and the left
  TICK touches ink at BOTH ends (0.02/0.01). Admits the tick, can
  reject the shoulder. Worse than nothing.
- today's gap_tol end test: admits the tick (already known).

## THEREFORE: CCC NEEDS A CLEARANCE FIGURE, AND IT GOES TO HOWARD
Any acceptance line between 24% and 59% of the gap separates every
true joint from every false one in both houses — but it is a ratio
cut on a sample of two houses, and per SEND-82's own instruction that
number is Howard's to set, not the code's. Two candidate shapes for
the ruling, stated without preference:
1. **A ratio**: "the shoulder's own ink covers more than half the gap"
   (any figure in (24%, 59%] works on this data; half is the natural
   sentence but is still a chosen figure).
2. **A drawn allowance**: "the shoulder must span the gap between the
   members' INNER twin strokes" — the shortfalls (0.34/0.40) match the
   members' own double-stroke separations, so the allowance would come
   from the drawing (each member's measured twin separation), not from
   a constant. Needs Howard's confirmation that shoulders terminating
   at inner strokes is how these sets are drawn, not a one-house habit.

## What CCC would produce once the figure is ruled (stated, not built)
- RIGHT: bump on the RIGHT edge via the true shoulder — silhouette
  ≈[54.71, 79.77], 6 vertices, ≈31.9 ft (wall 29.65 + 2.28; the outer
  twin 80.01 would give 2.59 = 2'-7" — which twin carries the boundary
  is part of the same ruling).
- LEFT: the wrong-edge front chain (24%) DIES; no CCC shoulder joins
  wall 19.45 to the back-edge chimney strokes (best candidate 8%) —
  so the projection is honestly UNRESOLVABLE on left: wall-only
  [19.45, 42.76] ≈ 29.4 ft, 4 vertices, and the face should SAY the
  projection refused for want of a drawn shoulder (Item 3's bound:
  only the shoulder distinguishes, and only right has one).
- The acceptance is THE SHAPE: left at 32.60 with a front-edge bump is
  registered as a FAILURE state; the honest post-CCC left is narrower
  than the sealed width and says why. That is Item 3's outcome, not a
  regression: an unresolvable projection saying so.
- BONI left: CCC does not reach it (no shoulder involved — its far
  boundary is a full spanning stroke rising into the gable). Its cure
  is a separate ruling.

## Registered (memory/register_send82.md)
1. THE CONTROL-TESTING STANDARD — a proposed property is tested
   against the cases it was NOT invented for; controls killed SEND-81's
   property and CCC-literal here.
2. THE LEFT-32.60 CANCELLATION — two coincidences (wrong edge kept,
   both candidates ≈2'-7") make the number right and the shape wrong.
3. THE STRUCTURAL-IDENTITY BOUND — silhouette geometry alone cannot
   tell a chimney from a course-end line; only the shoulder can, and
   only where one is drawn; sets without one are INDETERMINATE on both
   sides, and the build must let an unresolvable projection say so.
