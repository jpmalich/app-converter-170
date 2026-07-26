# X-Axis Placement — Mechanism Report (EST-986945 field-compare, 2026-07-26)

## Ruling context
Howard's follow-up under Part 1: side views do not mirror, dormer centers
disagree with site photos. Ordered: (1) mechanism with evidence FIRST,
(2) fixtures are a re-look event if they change, (3) pin the convention.

## 1. What was actually wrong — and what was NOT

### NOT wrong: the per-view axis convention
The renderer's identity mapping (SVG x = along_wall_ft, drawing-left = 0)
was verified against all four ANNOTATED SITE PHOTOS of EST-986945
(run 7bcc56e2). The extraction datum (prompt iter 79j.40 — left corner as
viewed from OUTSIDE) is each sheet's drawing-left corner, so every sheet
already drew in standard exterior projection:

| view  | photo landmarks proving orientation                | photo positions | sheet positions |
|-------|----------------------------------------------------|-----------------|-----------------|
| front | trash bins photo-left, entry steps photo-right     | G≈7.5 G≈18.2 D≈24.8 | 6.9 / 18.0 / 24.2 ✓ |
| back  | window left, patio door right (fire-pit chairs)    | W≈6.4 P≈19.7    | 7.0 / 20.0 ✓    |
| left  | back-yard chairs photo-LEFT, front trash bins photo-RIGHT → drawing-left = BACK corner | W≈9.0 / 18.4 / 27.2 | 8.9 / 17.6 / 27.0 ✓ |
| right | truck/driveway (front) photo-LEFT → drawing-left = FRONT corner | W≈11.3 / 24.2 | 11.5 / 24.0 ✓ |

The `_PROFILE_SIDE` table was also already mirror-correct (verified per pair).

### WRONG: cross-view horizontal binding of the twin dormer (LEFT + RIGHT views)
One physical dormer box straddles the ridge, so its span from the FRONT
plane must read the same from both sides — i.e. opposite exterior views
MUST mirror: `center_left + center_right = wall width`. The centers were
bound PER VIEW (quad-through-anchor / windows-centered jitter), never
reconciled horizontally (only the vertical LEVEL band was ruled 2026-07-22):

- LEFT sheet: center 17.9' → 19.1' from the front corner
- RIGHT sheet: center 17.5' → 17.5' from the front corner
- Both drew LEFT of wall-center (18.5') — physically impossible for an
  off-center box seen from opposite sides. Right photo supports ≈19'
  from the front corner: the RIGHT view was the outlier.

## 2. Fix (drawing-only; no money surface touches dormer center — verified)
PAIRED-FEATURE MIRROR (horizontal twin reconciliation, exact mirror of the
ruled vertical LEVEL): paired twins (same identity tolerances already
ruled — contractor 1.25' w / 0.5' knee, AI 0.5') bind ONE mirrored center:
`center_here ↔ opp_width − center_opp`, averaged, flagged on the sheet.

### Before → after, per affected view
- EST-986945 LEFT:  dormer center 17.9' → **18.7'** (photo ≈18.8' ✓)
- EST-986945 RIGHT: dormer center 17.5' → **18.3'** (photo ≈19.3', perspective-limited)
- Mirror invariant now holds: 18.7 + 18.3 = 37.0 = wall width ✓

## 3. Fixture re-look gate (before/after payload hash, geometry-only)
- **doug jones — all 4 sheets: geometry HASH-IDENTICAL** (only the new
  orientation-note text was added) — prior field-compare stands.
- **letrick — all 4 sheets: geometry HASH-IDENTICAL** — stands.
- **haugh — all 4 sheets: geometry HASH-IDENTICAL** — stands.
- **red house — CHANGED (RE-LOOK EVENT, flagged loudly):** its twin
  dormers were also unreconciled (left 17.8 / right 20.0 — 0.8' mirror
  disagreement). Now: left 17.8' → **17.4'**, right 20.0' → **19.6'**
  (band shifts ~5" each; NO flip, NO reorientation — prior field-compare
  was against correctly-oriented drawings). Before→after screenshots
  delivered in chat. Howard's eyes re-gate this fixture.

## 4. Convention pinned
`_VIEW_DATUM` (elevation_sheets.py) + `tests/test_view_orientation_pin.py`:
per-view drawing-left corner sealed (front→front-LEFT, back→back-RIGHT,
left→BACK, right→FRONT), profile-side mirror property sealed, 1:1 opening
x-mapping sealed, mirror reconciliation + no-op/non-pair cases sealed.
Every sheet renders an orientation note citing the pin
(`data-testid="elevation-orientation-note"`).
