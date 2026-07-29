# REGION-CROP PLACEMENT PASS — PROPOSAL (2026-07-29, report only, nothing built)

THE PROBLEM (from both acceptance runs): opening→region placement is the
read's real weakness. The machine finds the openings (37/39 Haugh) but
misreads WHICH labeled region boundary they sit inside on a crowded page.
STC-1's five openings landed on zero straight-on reads.

## Method — two narrow questions instead of one crowded one
1. **BBOX PASS** (per cardinal page, 1 call): "return the pixel bbox of
   every labeled facade region on this drawing" — labels only, no
   dimensions, no openings. 4 calls/import.
2. **CROP PASS** (per region, 1 call): crop the page render to that
   region's bbox (+10% margin), ask ONLY: "which opening IDs are drawn
   inside this boundary?" One region in frame — no neighbor competition.
3. **SELF-CHECK built in**: Hover's own FACADES table prints the expected
   opening COUNT per region. Crop result ≠ printed count → named ⚠ with
   both numbers. Match → ✓ with the IDs listed.

## Cost per import
- Full: 4 bbox + ~10–15 crop calls (only regions the FACADES table says
  carry openings — Haugh 15 of 31, 3 Degree 17 of 50) ≈ 14–21 extra
  vision calls ≈ $3–7, +2–4 min at current concurrency.
- CHEAPER TRIGGERED VARIANT: crop only regions where the page read's
  placements DISAGREE with the printed count (Haugh: ~8 regions → ~12
  calls ≈ $2–4). Matching regions keep the page-read placements.

## Does it fix STC-1's five on 261 Haugh? — THE TEST
Cannot be promised without running; mechanically it removes the exact
failure (neighbor regions out of frame). Named risk: if Hover DREW those
five openings inside an adjacent region's boundary lines (drawing
ambiguity, not read error), the crop faithfully reports the drawing and
the ⚠ stands — which is still the correct honest outcome. Acceptance
criterion, per Howard: the crop pass puts D-1, the front window, D-2
(garage), the right-side door and right-side window in the block, or it
says plainly it cannot.

## Regions with NO locatable boundary on any straight-on page
A region label can be PRINTED on a cardinal page even when no dimension
callout is — the bbox pass looks for labels, not dimensions, so several
"unread" regions are still locatable. If a label is genuinely absent
from all four cardinal pages (possible for e.g. Haugh STC-2..4):
NAMED ⚠ — "region X: Hover table says N openings, region not locatable
on straight-on pages — resolve by eye." Never silent, never an oblique
fallback (obliques stay dropped by ruling).

## Replace or alongside?
ALONGSIDE, with ownership split: the page read keeps widths, corner
heights, tall corners; the crop pass OWNS opening→region placement
(page-level placements retire — they were the weak read). Checking tool
only: nothing feeds a flag, count, or line (S3 unwired).
