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
