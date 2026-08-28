# SEND-145 — THE ANCHOR WAS WRONG, THE SHAPE WAS FINE

Howard's field run on EST-176308 (2026-08-28), on the zones SEND-144 placed:

> *"Placement uses 80% of photo width, near the BOTTOM OF THE PHOTO. That is a
> photo rule, not a wall rule. A yard or a patio puts the box on the grass. The
> same rule parked the dormer on the first floor."*

Ruled scope, honoured exactly: **opening-box anchor for the body ·
first-floor openings only · BIGGEST opening for scale · LOWEST opening for the
bottom · report the new boxes, then wire them on EST-176308 · RIGHT stays
refused · EST-886440 untouched.** No new mark type. No quote wiring. No price,
no material line. No second finder, no re-OCR — every figure still comes out of
the finished run `556b9121…`.

Stamp, verbatim from `scripts/handback_green.sh`: see `memory/handback_green_log.md`
(this send's line) — quoted in the PRD entry.

12 pins in `tests/test_send145_zone_anchor_2026_08_28.py` ·
browser `test_reports/iteration_66.json` (**7/7 pass**) plus my own four
screenshots on the live photos · probes `memory/send145_probe.py`,
`send145_probe2.py`, `send145_check.py`.

---

## 1. WHAT THE OLD RULE DID, IN PIXELS

`BODY_BOTTOM_FRAC = 0.92` put the bottom edge at 92% of the PHOTO's height and
sized the plane from 80% of the PHOTO's width. On these three photos that is,
measured against the new anchor:

| face | photo (natural px) | old bottom | new bottom (a SILL) | it was low by | old px/ft | new px/ft |
|---|---|---|---|---|---|---|
| **FRONT** | 2400 × 1800 | 1656 | **1411.5** | 244 px ≈ **4.0 ft** | 71.1 | **61.8** |
| **LEFT** | 640 × 480 | 441.6 | **314.0** | 128 px ≈ **7.3 ft** | 13.8 | **17.6** |
| **BACK** | 1428 × 1071 | 985.3 | **766.0** | 219 px ≈ **6.5 ft** | 42.3 | **33.8** |

Four feet of driveway on the front, seven feet of lawn on the left, six and a
half feet of gravel patio on the back. The scale was wrong in BOTH directions
(front/back too big, left too small), because it was a fraction of the frame,
not a measured box on the wall.

## 2. THE ANCHOR ORDER, AS RULED — AND WHAT EXISTS TODAY

Written into `photo_zone_proposals.py` where the code can be read:

1. **the starter-candidate / wall-base MARK on that photo** — no such mark type
   exists (SEND-143 left starter a named refusal), and SEND-144's candidate edge
   is derived FROM the body zone, so anchoring to it would be **circular**.
   `_base_mark_line()` is that door and answers `None` today.
2. **the WALL REF bar** — the read NAMES it in prose (`WALL REF = 324"` is on
   the photo, in the read's words) but writes **no pixel geometry** for it.
   Prose is not a position. `_wall_ref_bar()` answers `None` today.
3. **THE READ'S OWN FIRST-FLOOR OPENING BOXES** — real pixels on the wall, each
   with its own measured width. **BUILT.**
4. **else the photo bottom at 80% width, and the basis SAYS SO**: *"…the box is
   80% of the photo's width sitting at the PHOTO BOTTOM, which is a photo edge
   and NOT a wall line — INDETERMINATE, move it onto the wall you see"*.

## 3. THE RULE THAT WAS BUILT (`first_floor_anchor`)

- **THE LOWEST first-floor box sets the BOTTOM** — its sill line (`y + h`).
  Nothing on a wall sits below the first floor.
- **THE BIGGEST first-floor box sets the PLANE SCALE** — its own measured width
  in inches against its own width in pixels. **ONE named box, never an
  average**: a pin bans `mean(`, `sum(`, `statistics` and `/ len(` from the
  whole module.
- **A DORMER OPENING IS EXCLUDED OUTRIGHT** (`on_dormer`) — it never even
  becomes a candidate.
- **A GABLE-PEAK WINDOW IS DROPPED AND NAMED** — the lowest sill plus the run's
  own wall height describe a band; a box whose sill sits above that band is not
  first floor. The basis prints *"Dropped above the wall band (not first floor):
  front-w1"*.
- **A BOX WITH NO TYPED SIZE IS NEVER USED FOR SCALE** (pinned) — an untyped
  box carries no evidence, so it carries no ruler.
- **THE DORMER STACKS ABOVE THE BODY TOP** — *"placed ABOVE THE BODY TOP, on
  the upper wall of this photo — never at the photo bottom"*. That is the
  sentence that answers Howard's second complaint.
- **A WALL THAT DOES NOT FIT THE FRAME IS CUT AND SAYS SO** — *"the sides run
  past the frame edge … move the sides onto what you can actually see"*. A real
  scale can now overflow the frame; it is reported, never quietly shrunk.
- **NOTHING BECAME A MEASUREMENT.** Every zone is still `provisional`,
  `origin: ai_zone_proposal`, and the basis still says *"WHERE IT SITS on this
  photo is a starting position and NOT a measurement"*.

## 4. THE NEW BOXES ON EST-176308, FACE BY FACE (run `556b9121…`)

**FRONT** — photo `ai_f3c3b84f…jpg`, 2400 × 1800.
3 first-floor boxes (`front-gd1`, `front-gd2`, `front-d1`).
**BOTTOM = `front-gd1`** sill at 1411.5 px (0.784 of the photo) — the garage
door, which reaches the driveway. **SCALE = `front-gd1`**, 8.25 ft over 510 px →
**61.82 px/ft**. Body 27.0 × 10.9 ft → 1669 × 674 px. **`front-w1` DROPPED
above the wall band** — it is the window up in the peak. The gable (rise 6.5 ft,
the run's own figure, *not* derived from a pitch) stacks on the body top.

**LEFT** — photo `ai_3112d120…jpg`, 640 × 480.
3 first-floor boxes (`left-w1/w2/w3`); the **two dormer windows
(`left-dw1`, `left-dw2`) were excluded outright** as `on_dormer` — they are the
very openings that used to drag the placement down.
**BOTTOM = `left-w1`** sill at 314 px (0.654). **SCALE = `left-w3`**, 2.5 ft
over 44 px → **17.6 px/ft** — the lowest box and the biggest box are DIFFERENT
boxes here, which is the point: the two choices are independent (pinned).
The dormer (14.1 ft × 3.5 ft knee wall) now sits above the body top and still
carries the run's own **UNANCHORED** sentence.

**BACK** — photo `ai_5a9d8c20…jpg`, 1428 × 1071.
2 first-floor boxes. **BOTTOM = `back-d1-patio`** sill at 766 px (0.715) — the
patio door threshold, which IS the wall base on this elevation. **SCALE =
`back-d1-patio`**, 5.83 ft over 197 px → **33.77 px/ft**.
**`back-w1-gable` DROPPED above the wall band.** The 26.2 ft² of stone still
gets NO zone — masks are an INPUT to the read, never an output.

**RIGHT — STILL REFUSED, UNCHANGED.** `first_floor_anchor` returns `None` there
and it never gets that far: the face refusal fires first, in the run's own
words — *"no photo measured this wall's width (assumed_symmetric). Not measured.
Not copied from another face."* Pressing STARTING ZONES on the RIGHT photo
places nothing. **A better anchor is not a licence to place a box on a wall
nobody measured.**

## 5. THE PIN I HAD TO CORRECT, NAMED

The pin file arrived asserting the FRONT fixture's bottom came from `w1` (the
small window, sill 0.67) rather than `gd1` (the garage door, sill 0.70). That
contradicted its own fixture comment *and* Howard's own words — **"Lowest
opening for the bottom"** means lowest ON THE WALL, i.e. the largest sill `y`.
The **code was right and the expectation was wrong**; I corrected the
expectation (naming the ruling in the test) rather than the code, and then
**strengthened** the file with a new pin —
`test_the_lowest_box_sets_the_bottom_even_when_another_box_sets_the_scale` —
which drops a small window BELOW the garage door and proves the bottom follows
the window while the scale stays on the garage door. Nothing was relaxed.

## 6. THE BROWSER — LOOKED AT, NOT INFERRED

`test_reports/iteration_66.json` — 7/7 — and four screenshots I took myself on
the live photos through the read-photo buttons:

- **FRONT**: the yellow body bottom (`starter candidate`) runs along the line
  where the two garage doors and the entry door meet the driveway. The
  driveway is BELOW the box. The green gable sits on the body top, over the
  real gable.
- **LEFT**: the body bottom runs along the mulch/siding line; the whole lawn
  that fills the lower third of that photo is OUTSIDE the box. The cyan dormer
  sits above the body top, over the pop-up dormer with its two 2SL windows —
  **not on the first floor**.
- **BACK**: the body bottom runs along the patio-door threshold / wall base;
  the gravel patio, the fire pit and the chairs are all BELOW the box.
- **RIGHT**: STARTING ZONES refuses with the run's own sentence and places
  0 marks.
- **FRONT idempotency**: a second press → still 6 marks, *"this read's starting
  zones are already here; nothing was overwritten"*.

Nothing was confirmed, refused, adjusted, deleted or applied. **The new boxes
are LEFT IN PLACE on EST-176308 for Howard to look at.**

## 7. NOT AUTHORISED, NOT TOUCHED

corner tick · wall base · eave mark types (which would make anchor 1 real) ·
quote wiring · rectify / homography · the blueprint path · the hover/photo
storage split. EST-886440 untouched.
