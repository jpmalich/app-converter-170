# SEND-63 · ITEM 3 — LINE-WORK READ: DESIGN REPORT ONLY (no code built)

Scope: WALL OUTLINE ONLY. Not gables, not chimneys — they follow once
the read is trusted. Predictions in §6 are written BEFORE any build,
same discipline as the item-4 prediction file.

## 1. Separating building geometry from outlined glyphs
Both source PDFs are vector with ZERO text chars — every letterform is
outlined curves (Letrick p1: 38,637 lines + 3,746 curves). The persisted
OCR store already boxes every string it read, in percent-of-page — the
same coordinate space the vector geometry maps into (PDF pt → page %,
one affine transform from the MediaBox). Masking those boxes removes the
large majority of letterform strokes.
**Is the mask sufficient? NO, and the design does not rely on it.** It
leaves behind: strings OCR failed to read, arrowheads, tick marks,
symbols (⌀, section bubbles), logos, and ALL hatching. The mask is a
cheap first cut; the real separation is structural (§2) — a glyph
fragment can never satisfy the spanning-and-closing property, so
unmasked leftovers are excluded by construction, not by a size
threshold.

## 2. Separating the wall outline from everything else that is a line
THE STRUCTURAL PROPERTY (one property, not a list of exceptions):
**the wall body is the closed region bounded above by the TOP OF PLATE
datum line, below by the FIRST FLOOR (or TOP OF FOUNDATION) datum line,
and laterally by continuous strokes that SPAN the full datum interval.**
- Dimension/extension lines: stubs perpendicular to, or terminating at,
  a datum line — they do not span the interval as part of a closed
  boundary.
- Leaders: open polylines; they close no region.
- Hatching: short strokes interior to the region; not on its boundary.
- Roof / gable lines: above the plate — outside the interval.
- Section marks / grid bubbles: do not span.
The datum lines are the SAME evidence that already derived the height —
the read is anchored to structure that is already proven per face.

## 3. Scope of the search
The face's own TITLE-CARVED BAND on its own page, exactly as the height
read scopes today. Inside Ruling AAA by construction: no other drawing,
no other band, no plan sheet is visible to the read.

## 4. When the outline cannot be resolved
Return **INDETERMINATE** — when no spanning stroke exists at one or both
ends, when the boundary does not close, or when two incompatible closed
boundaries both qualify (ambiguity is indeterminacy, not a choice).
**NEVER a silent fallback to the datum span.** The ladder may still
propose from the datum span, but that zone's basis says "datum marker
span" — a basis of "wall outline (line-work)" may only appear when the
outline actually resolved. A fallback that looks like a read is worse
than a refusal.

## 5. Output shape
A **polygon** (3+ free vertices, which zone binding already accepts):
the region boundary simplified to vertices at direction changes. Steps,
bump-outs, porch returns and chimney notches survive; nothing is reduced
to a bounding rectangle — the entire value of reading real geometry is
the shape.

## 6. Predicted shapes, written down before building (unrevisable)
**LETRICK** (sealed: 54'-0" front/rear, 30'-0" sides; drawn scale
3/16"=1'-0", ARCH C):
- FRONT p1: near-rectangle, ~5–7 ft narrower per side than today's
  datum-span box (i.e., x pulls in from 10.2→60.4% to roughly 14→56%),
  4–8 vertices (porch/garage step possible on the drawn line).
- REAR p1: NOT a single rectangle — Howard zoned it as 3 pieces; the
  drawn wall line should show at least one step/opening. 6–10 vertices.
- LEFT p2 / RIGHT p2: near-rectangles ~30 ft wide at the drawn corners
  (x ≈ 20→43% and ≈ 55→77%), 4–6 vertices.
- All bottoms at the FF/TOF drawn line, tops at the plate line.
**BONI** (sealed: 58'-0" front/rear, 30'-2"/33'-0" sides):
- FRONT and REAR become REACHABLE — the line-work read does not need
  corner labels, so the permanent single-corner limit does not apply to
  it. Predicted: two-story rectangles at the drawn width, checkable
  against 58' only where a face carries its own evidence scale.
- LEFT: two-story rectangle; RIGHT: expected INDETERMINATE risk (its
  FIRST FLOOR datum is not located — the lower boundary anchor is
  missing; if the read cannot close the region it must say so).

## 7. The check against 54'-0" and 30'-0" — a check, never a target
After the read, convert each outline's width at THAT face's own scale
(the height chain, or a BOUND datum gap) and report the delta against
the sealed numbers — exactly the SEND-52 calibration column. No
parameter anywhere in §1–§5 is fit to 54, 30, 58, 30'-2" or 33: the
datum anchors, the spanning property and the closure rule are all
defined without reference to any width. HOW THE DESIGN CAN BE WRONG
(named, so the check has teeth): grabbing an extension line as the
lateral boundary lands ~+10–16 ft (the leader offset reappears);
grabbing the roof/overhang edge lands ~+2–4 ft; missing a step shows as
an area outlier against Howard's confirmed zones. If the deltas land
near zero, the read is confirmed BEFORE it ships; if they scatter, the
markers-vs-lines model is wrong and that outranks shipping.

## Still open (SEND-63 footer)
The vertical-rail span report is HELD pending the line-work decision:
approved → mooted and dropped; rejected → it ships next send (cheap —
the rails' positions are already extracted per face).
