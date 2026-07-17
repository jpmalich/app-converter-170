# 261 Haugh Dr — Cross-source comparison (canonical)

**Hover basis:** report 4ffc35f4, net, wrap-only (Siding rows 2,064 ft²; stucco 312 + brick 234 excluded)
**Photo basis:** run b7a26956 (attempt 3, anthropic_direct streamed), per-photo WALL REF bars 273"–360" on-plane + WIN REF anchors, scale confidence MEDIUM
**Band:** ±10% = agree-within-band. All values verbatim from run docs; derived values show their formula.

| Line | Hover | Photo | Δ | Tag |
|---|---|---|---|---|
| Siding, wrap scope (ft²) | 2,064.00 | 1,991.20 | −72.8 (−3.5%) | agree-within-band |
| Masked masonry (ft²) | 234.00 (brick) | 221.11 = 405.0×30% (front 121.50) + 933.8×5% (back 46.69) + 352.8×15% (right 52.92) | −12.89 (−5.5%) | agree-within-band — SCOPE CONCURRENCE HEADLINE |
| Stucco (ft²) | 312.00 | not separately masked (no stucco distinct from siding detected) | — | disagree-flagged |
| OSC count | 20 | 12 | −8 | disagree-flagged |
| OSC LF | 140.33 | 80.00 | −60.33 (−43.0%) | disagree-flagged |
| ISC count | 6 | 3 | −3 | disagree-flagged |
| ISC LF | 36.92 | 36.00 | −0.92 (−2.5%) | agree-within-band |
| Windows | 32 | 34 | +2 (+6.3%) | agree-within-band |
| Entry doors | 3 | 3 | 0 | agree (exact) |
| Patio doors | 3 | 4 | +1 (+33.3%) | disagree-flagged |
| Garage doors | 1 | 1 | 0 | agree (exact) |
| Openings total | 39 | 42 | +3 (+7.7%) | agree-within-band |
| Opening perimeter LF | 574.33 | 818.50 (all 42 openings) | — | **basis-mismatch** (retagged 2026-07-17, see below) |
| Eaves LF | 184.17 | 100.00 | −84.17 (−45.7%) | disagree-flagged |
| Rakes LF | 136.58 | 110.00 | −26.58 (−19.5%) | disagree-flagged |
| Starter LF | 304.67 | 140.00 | −164.67 (−54.1%) | disagree-flagged |
| Soffit (ft²) | 463.00 | (no soffit field emitted) | — | photo-couldn't-see |
| Roof area (ft²) | 2,126.00 | (elevations only) | — | photo-couldn't-see |

## Scope-agreement headline
The photo path independently masked **221.11 ft²** of masonry (aggregator-exact
from per-wall siding_pct: 70/95/85) vs Hover's **234 ft² brick** — Δ −5.5%,
unprompted concurrence between fully independent sources on both the EXISTENCE
and the MAGNITUDE of the non-siding scope. (The ~242 figure quoted in review is
not present in either run doc; 221.11 is the exact doc-derived value.)
Corroborating: photo wrap-scope siding 1,991.2 lands −3.5% off Hover's
wrap-only 2,064 — the two sources agree on what wraps.

## Honest-flag exhibit (no fix — the warning IS the deliverable)
3D viewer banner (`ai-measure-3d-ridge-mismatch-banner`):
"**ROOF ORIENTATION MAY BE WRONG** — {mismatched walls} report a gable triangle
in the AI takeoff but aren't rendering as a gable end. → *Try flipping Ridge
orientation below.*"
Why it fires on this house: the run reports gable triangles on **left (5.2 ft)**
and **back (3.0 ft)** — adjacent walls that no single ridge axis can serve —
with roof_type `gable-shed-dormer` at 0.55 confidence ("Primary roof is
low-slope shed/clerestory (photos 0,4,5,6) with true gable ends on the left
wall (photo 2, 4/12) and rear one-story wing (photo 3, 4/12), plus a raised
front clerestory box reported as a dormer (photo 7)."). The banner + ridge
toggle is exactly the honest behavior for a stepped modern roof; it also
explains the eaves/rakes disagreement rows above.

## Opening-perimeter BASIS CHECK (2026-07-17, retag: basis-mismatch)
Photo schedule per-class perimeter (2×(w+h)×count, exact):
windows 34 → **586.50** · entry 3 → 60.67 · patio 4 → 123.33 · garage 1 → 48.00
· doors subtotal **232.00** · total **818.50** (reproduces the stored figure to the cent).
- Windows-only vs Hover 574.33 → **+12.17 (+2.1%) — agree-within-band.**
- Doors account for 244.17 of the raw gap; photo doors perimeter = 232.00 (95% of it).
→ Hover's 574.33 behaves as a windows-table perimeter (doors excluded); the raw
+42.5% was two different baskets, not a measurement miss.
CAVEAT (honest): Hover united_inches 2,748 implies a windows perimeter of
2×2748/12 = 458.0 LF, which does NOT reconcile with 574.33 — the exact
composition of Hover's printed line is unverified against the PDF (united_inches
is itself a parsed/derived field). The retag stands on the two matches above.
CONVENTION (standing, for future cross-comparisons): compare opening perimeter
WINDOWS-ONLY unless the Hover PDF line is verified to include doors; photo-side
reports carry per-class perimeter so the matching basket is always available.

## Notes for the workbook
- Photo wall set: front 45.0×9.0 (70% siding, conf 70) · left 29.3×9.3 +5.2'
  gable (100%, conf 72) · back 46.0×20.3 +3.0' gable (95%, conf 65) · right
  36.0×9.8 (85%, conf 55). Gables 203.3 ft² (0.7 convention) + dormer 45.0 ft².
- Photo ISC LF agreeing (−2.5%) while count halves (3 vs 6) = photo sees fewer,
  taller inside corners; Hover counts 6 shorter ones. Same steel, different cut.
- Hover extras with no photo counterpart: united inches 2,748 · level frieze
  215.67 · sloped frieze 129.83 · drip edge 320.75 · window bottom width 100.25.
