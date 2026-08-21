# SEND-79 — REPORT (2026-08-21)

## ITEM 1 — MARKER-STRIP FIX. BUILT AS ORDERED, BY CONSTRUCTION.

The rederive no longer carries anything across the merge. Every rebuild
door now RE-RUNS THE OVERLAY LAW over the fresh lines before writing
them (`reapply_overlay_law` in `routes/pdf_overlay.py`, delegating to
`apply_overlay_to_takeoff` — the one law). Doors wired: `/rederive`
(spec-save + manual), `hover-lp-run`, `lp-package/materialize`. A
copied marker was one refactor from being dropped again; the re-run law
cannot lose what it recomputes.

**The invariant is pinned, not the merge**
(`tests/test_overlay_rederive_2026_08_21_send79.py`, 4 pins):
- LIVE: an overlay-bound line keeps `overlay_superseded`,
  `superseded_qty` and the zone math through a FIRST and a SECOND real
  rederive; a zone-less rederive stays derived and invents nothing.
- STRUCTURAL, ON THE CLASS: an AST sweep over ALL of `routes/` — any
  function that calls the shared rebuild and writes lines MUST re-run
  the law. A future door that reintroduces the shortcut fails the pin
  by existing. A second structural pin fails if anyone starts copying
  marker fields by hand in the merge instead.

**The three overlay-bound estimates, before and after a REAL rederive
(run on CLONES via the real door — live estimates untouched, clones
deleted; `memory/send79_item1_report.py`):**

| estimate | line | before | after a real rederive |
|---|---|---|---|
| EST-655664 | Charter Oak Dutch Lap | qty 11.77 · superseded 16.0 · overlay_sqft 1177.13 · 1 zone | **byte-identical — markers intact** |
| EST-569367 | Charter Oak Dutch Lap | qty 25.94 · superseded 15.0 · overlay_sqft 2129.6 · 10 zones | **byte-identical — markers intact** |
| EST-886440 | Charter Oak Dutch Lap | qty 18.74 · superseded 44.0 · overlay_sqft 1873.93 · 4 zones | **the door itself refused 423 (UNTOUCHABLE — protection followed the estimate number onto the clone). A door that cannot open cannot strip; the law re-run covers it if protection is ever lifted.** |

## ITEM 2 — THE MISSED RIGHT-ELEVATION CHIMNEY. HYPOTHESIS CONFIRMED.
Report only — NO fix wired (reason at the end; it needs your ruling).
Probe: `memory/send79_item2_probe.py`.

**1. The chimney strokes EXIST in right's band and ENTERED the
candidate set.** Two verticals (double-stroked outer face) at
x=79.77/80.01, tops rising **~8.3 ft ABOVE the plate box** (to the
cap), bottoms at ground below the floor box. They qualified as
spanning singles. At right's scale the projection beyond the wall line
(77.98) measures **2.28 ft (inner stroke) / 2.59 ft ≈ 2'-7" (outer
stroke)**. A third dropped stroke at 77.64 (a wall-line twin, also
rising past the plate).

**2. The excluding rule, at the exact step:** SEND-71's RAKE-EDGE
SEPARATION — `linework_read.py` L184-186: when any plate-terminated
candidate exists, `cands = plate_terminated` drops every candidate
whose `pt` flag (L104: stroke top terminates at the plate box) is
False. A chimney rises past the plate to its cap, so its `pt` is
False. Dropped at that single line.

**3. Left's capture DEPENDED ENTIRELY on the joint.** Chains are
hardcoded `pt=True` (L130) — left's 2'-7" step survived because the
wall line happened to be FRAGMENTED at the shoulder, forming a jointed
chain that inherited plate termination. Re-run with the jog
horizontals removed: **left drops from RESOLVED [19.45, 45.30] v=6
(32.60 ft) to RESOLVED [19.45, 42.76] v=4 (~29.4 ft) — the step
vanishes.** Left was luck, not capability. Exactly as you wrote.

**4. Census — projections dropped by the same rule, both houses, all
8 faces:**
| face | dropped spanning strokes | consequence |
|---|---|---|
| LETRICK right | x=79.77, 80.01 (chimney outer face, 2'-7" at the outer stroke), 77.64 (wall twin) | **the missed chimney — the instance** |
| LETRICK left | x=17.43, 17.67 (double-stroke rising ~8.4 ft above the plate to cap height, descending to ground, **2.24/2.55 ft ≈ 2'-7" beyond the wall corner 19.45**), 19.83 (corner twin) | **see the complication below** |
| BONI left | x=34.94 (rises 3.13%-pts above the plate into the shake-gable region) | **this drop is WHY Boni left refuses "one corner" — the far boundary itself is being discarded** |
| LETRICK front/rear, BONI front/rear | none — no plate-terminated candidates exist on those faces, the filter is inert (eave faces, SEND-71's designed case) | — |

So the class is real: 7 dropped strokes across 3 faces; on 2 faces the
drop changes the outcome (right's chimney missing; Boni left refusing
entirely), and on 1 face the same-class strokes remain dropped while a
fragment-luck chain preserved the step.

**5. THE COMPLICATION THAT STOPS ME FROM WIRING YOUR FIX SHAPE
WITHOUT A RULING.** The structural cure you named — a stroke that
departs the wall line and returns to it is silhouette regardless of
where its far end goes — admits right's chimney (a drawn shoulder
horizontal at y=64.55 joins wall 77.98 to chimney 79.77 → right
becomes ~[54.71, 79.77], 6 vertices, ~31.9–32.2 ft, matching your
prediction's first branch). **But the SAME structural property holds
on LEFT for the dropped strokes at 17.43/17.67**: they rise cap-high,
reach ground, and the drawn cladding course lines END on them (x runs
17.67→~42.7). Geometry agrees: a back-wall chimney shows at the BACK
edge of BOTH side views — low-x on left, high-x on right, and both
measure ≈2'-7". If the cure admits right's chimney, it admits left's
back edge too, and **LEFT MOVES from 32.60 (your sealed figure) to
~35+ ft** — a currently-resolved face changing. Note also left's
CURRENT +2'-7" step sits at the FRONT edge (the 43.22→45.30 chain,
2.62 ft) — so the drawings show left with a 2'-7" feature at EACH
edge, and the read has been keeping the front one (by fragment luck)
while dropping the back one (by the pt rule). Which of the three
readings of left is the house — 29.4 (no steps), 32.60 (front step
only, today's number), or ~35 (both) — **your prints settle it, and
per the standing discipline I stopped rather than move a resolved
face.** Nothing was tuned toward 32.6 or any sealed figure; these are
the strokes as drawn.

## ITEM 3 — THE LEFT/RIGHT WIDTH CROSS-CHECK. BUILDABLE: YES.
Not built (as ordered). From what Ruling XX already produces:
- `attribution_verdict(runs)` (ocr_geometry.py L623) returns
  IMMATERIAL/MATERIAL/NO_PAIR/INDETERMINATE plus the parsed depth pair
  — everything the check needs on the depth side. The line-work side
  (per-face width_ft) is already computed in propose.
- The check: where XX says IMMATERIAL (equal side depths) and both
  side elevations RESOLVE via line-work, their widths should agree;
  disagreement → FLAG, NEVER RESOLVE. It would have flagged left
  32.60 vs right 29.65 without anyone opening prints.
- Three wiring facts to know before building: (1) `attribution_verdict`
  is NOT currently wired into the live pipeline — only
  `scripts/send38_report.py` calls it; the live check must locate the
  floor-plan page (the envelope probe's ESTABLISHED status already
  identifies it). (2) A true single-sided projection is a LEGITIMATE
  disagreement — the flag is still correct (a flag, not a verdict).
  (3) Where XX is INDETERMINATE (Boni's positional tie — the open
  segment-vs-total ruling), the check stays silent: no pair, no claim.
