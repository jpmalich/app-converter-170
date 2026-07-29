# STC-1 REGION-CROP PROBE — 261 HAUGH (2026-07-29, ~$0.75, 6 calls, 21s)

Method as ruled: Hover's printed count given AS A CONSTRAINT ("the table
says 5 — which 5?"), table wins on disagreement, never invent to reach a
count. bbox pass on all 4 cardinal pages, crop (+10% margin) where found.

## RESULTS
- STC-1 located: FRONT (bbox 656–892 × 580–720 px — label vicinity, small)
  and BACK (tiny sliver, crop blank). NOT printed on RIGHT (right-side
  masonry is labeled STC-2 there) or LEFT.
- FRONT crop returned: W-209, W-210 inside STC-1. uncertain: []. Invented:
  NOTHING — the constrained prompt held; the model returned 2 and said
  "the region appears to continue beyond this crop" instead of reaching 5.
- Union: 2 of 5. DISAGREES — table's count kept.

## HONEST READING (probe artifacts named)
1. The bbox pass boxed the LABEL VICINITY (236×140 px), not the full
   outlined region — the crop's own note says the region continues
   beyond. A boundary-box refinement (ask for the full outlined wall
   area / crop the label's whole wall band) is untested — one more ~$1
   probe would answer whether the front three land.
2. STRUCTURAL: STC-1 is not printed on the RIGHT view at all — the
   right-side masonry there is STC-2. So Howard's five (front entry,
   front window, garage, right door, right window) CANNOT all sit inside
   one drawn STC-1 boundary on any straight-on page: the printed table's
   "5" is a whole-region count that the drawn views fragment across
   STC-1/STC-2 labels. This is evidence toward "the drawings cannot
   settle placement in this format" — but not conclusive until the
   boundary-box refinement is tried on the front three.
3. Cost/time for one region: 6 vision calls (4 bbox + 2 crops), 21s,
   ≈ $0.60–1.00.

Raw log: /tmp/probe_stc1.log (script: /app/memory/evidence/probe_stc1.py)
STOPPED per ruling — nothing else built off this one-region result.

## SECOND PROBE — FRONT BOUNDARY-BOX REFINEMENT (2 calls, 11s, ≈$0.30)
- Boundary trace found STC-1 on FRONT but reports it as "a small wall
  section BETWEEN the door D-1 and the large D-2 area" — 87×36 px of a
  1684×1191 page, boundary_fully_traced=false, "no distinct hatched or
  colored area."
- Crop of that section + margin: openings visible with size callouts
  (2'9", 3') but NO printed ID tags inside; opening_ids_inside=[],
  nothing invented, nothing uncertain.
- VERDICT: DRAWING-CONTENT problem, not boundary detection. Hover's FRONT
  drawing gives STC-1 a tiny footprint and draws D-1/D-2 OUTSIDE its
  outline (consistent with the page reads that placed D-1 on WR-1 and
  D-2 on WR-7). The printed table's "STC-1: 5" is not reflected in the
  drawn region's boundary. Combined with the RIGHT-view structural
  finding (that masonry is labeled STC-2): the drawings cannot settle
  opening-to-region placement in this format.
- TARGET CONTESTED (named, unresolved): Hover's table = 5 STC + 2 BR = 7
  non-wrap openings; Howard walked 5; Howard has ruled Hover's "brick" is
  also block. The drawing cannot arbitrate this; disagreement stands.
- STANDING RULE EXECUTED: ID-as-constraint now rides EVERY S2 read (the
  printed ID universe is in the prompt; "an honest omission beats a
  guessed tag"), pinned by test_id_constraint_rides_every_read.
