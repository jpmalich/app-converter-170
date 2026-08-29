# SEND-146 — ITEM 1 + 3 REPORT, BEFORE A LINE IS WIRED

Stamp, verbatim from `scripts/handback_green.sh`:

```
RECORDED: 2026-08-29 02:34 UTC · 74f20bb · CLEAN
RESULT: 3136 passed, 9 skipped, 7 warnings in 454.45s (0:07:34)
CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none); 8 removal(s) logged (see baseline REMOVAL_LOG)
INGRESS SMOKE: 4 passed in 1.80s
```

11 pins in `tests/test_send146_door_to_grade_2026_08_28.py` · 3 SEND-145 pins
updated BY NAME (the fixture gained the `type` the live rows always carried; the
"lowest box sets the bottom" pin now holds the CORRECTED rule and names the
ignored window; the anchor value now names the KIND of opening).

Run `556b9121…` on EST-176308. Every figure below is read off the finished
run's own opening rows (`memory/send146_probe.py` prints them raw). No second
finder, no re-OCR, no new detector: the rows already carry **`type`**
(`garage_door` · `entry_door` · `patio_door` · `window`) and **`style`**
(`Double Hung` · `2-Lite Slider` · …). The classifier is a read of `type`,
with `style` only ever narrowing a door, never promoting a window.

## THE DEFECT, NAMED IN ONE LINE

SEND-145 took the LOWEST first-floor opening's sill as the wall bottom. On
FRONT that sill is a **garage door at grade** and on BACK a **patio-door
threshold** — both are the wall bottom. On LEFT the lowest opening is a
**Double Hung window**, and a window sill is **mid-wall**: the box started at
the sills and left the starter-to-sill strip of siding outside it.

## ITEM 1 — CLASSIFY, PER FACE (first-floor, non-dormer, typed size)

| face | photo | first-floor openings the read boxed | classification | opening that would be NAMED |
|---|---|---|---|---|
| **FRONT** | 0 · 2400×1800 | `front-gd1` **garage_door** 99″ (sill 0.784) · `front-gd2` **garage_door** 98″ (sill 0.784) · `front-d1` **entry_door** 34″ (sill 0.769) · *(`front-w1` 2-Lite Slider is the peak window — already dropped above the wall band)* | **DOOR-TO-GRADE** | **`front-gd1`** (lowest sill; ties with gd2, gd1 is the left door) |
| **BACK** | 4 · 1428×1071 | `back-d1-patio` **patio_door** 70″ (sill 0.715) · `back-w2-lower-left` **window** 2-Lite Slider 44″ (sill 0.610) · *(`back-w1-gable` dropped above the band)* | **DOOR-TO-GRADE** | **`back-d1-patio`** |
| **LEFT** | 2 · 640×480 | `left-w1` **window** Double Hung 30″ (sill 0.654) · `left-w2` **window** Double Hung 30″ (sill 0.650) · `left-w3` **window** Double Hung 30″ (sill 0.615) · *(`left-dw1`/`left-dw2` are `on_dormer` — excluded outright)* | **WINDOW ONLY** | **none may set the bottom** |
| **RIGHT** | 6 · 2016×1512 | **none** — the read boxed no opening on this photo | **NONE**, and the face is REFUSED anyway | — |

**FRONT and BACK do not move.** Their bottom is already the door's sill, which
is the same pixel the new rule chooses. **LEFT is the only face this send
changes.** RIGHT stays refused — *"no photo measured this wall's width
(assumed_symmetric). Not measured. Not copied from another face."*

Door tokens I would treat as DOOR-TO-GRADE: `garage_door`, `entry_door`,
`patio_door`, `sliding_glass_door`, `slider_door`, `french_door`. **Anything
else — including any `window` row whatever its style, and any `type` I do not
recognise — is NOT a door to grade** (a 2-Lite Slider *window* stays a window;
only `type` promotes). Unknown falls to INDETERMINATE, never to a guess.

## ITEM 3 — THE PREDICTED LEFT BOX (photo 2, 640 × 480 natural px)

Unchanged inputs: plane scale **17.6 px/ft** from `left-w3` (2.5 ft over 44
px — the biggest first-floor box; the DH windows still make an honest RULER,
they just may not make a FLOOR). Read's face: **37.0 ft × 8.4 ft**.

| | today (SEND-145) | after SEND-146 |
|---|---|---|
| bottom y | **314.0 px** — the `left-w1` sill | **INDETERMINATE — not a wall line** |
| top y | 166.2 px | **166.2 px, kept** |
| x span | 5.9 → 657.1, cut at 640 | **unchanged, still cut at the frame** |
| basis | *"BOTTOM anchored to the sill line of 'left-w1'…"* | *"no door-to-grade opening on this photo — bottom is not a wall line"* |

**The one thing the ruling does not fix for me: where the bottom EDGE is
DRAWN.** A rectangle has to have four sides, so "indeterminate" has to land
somewhere on screen, and the two honest choices differ:

- **A — RUN IT TO THE PHOTO EDGE (my recommendation).** Top and width kept, the
  bottom drawn at **y = 480 (the photo edge)**. The starter-to-sill strip
  Howard lost is then INSIDE the box, and the box over-covers by ~166 px ≈ 9 ft
  of lawn, so he **pulls the bottom UP** — the same direction of safety as the
  contested-height rule (take the larger so it can be pulled in). The basis
  names it as a PHOTO EDGE and NOT a wall line, and the box's height is
  therefore **not** the read's 8.4 ft — which the basis also says, out loud.
- **B — LEAVE THE BOX WHERE IT IS AND ONLY CHANGE THE WORDS.** Top, width AND
  height kept exactly as today (bottom stays at 314 px on the DH sills), with
  the basis saying the bottom is not a wall line. Nothing over-covers and the
  read's 8.4 ft survives — but the picture Howard called WRONG looks identical,
  and the strip is still outside the box until he drags it.

Everything else on LEFT is untouched by this send: the **dormer stays stacked
above the body top** (14.1 ft × 3.5 ft knee wall, still carrying the run's own
UNANCHORED sentence), and the gable/opening zones are not re-shaped.

## THE ANSWER TO (c) — THE `starter candidate` LINE HAS NO STORED y. I STOPPED.

Howard ruled the LEFT bottom should be drawn on the `starter_candidate` line
**already printed on that photo**, and — if that line has no stored y — to
**STOP and say so**, with no fall back to the photo edge and no invented drop.

**IT HAS NO STORED y.** `frontend/src/components/estimate/phototakeoff/CandidateEdges.jsx`
builds it at RENDER time from the body zone's own bottom two corners:

```js
const [tl, tr, br, bl] = p;                       // p = the BODY ZONE's points
{ key: "starter", word: "starter candidate", a: bl, b: br },
```

It is the body zone's own bottom edge with a word on it — *"no length, no LF,
no key written"* in its own header. So anchoring the body bottom to it means
**anchoring the bottom to itself**: circular, exactly as SEND-145's anchor-order
comment warned at rung 1.

**Everything else I checked on that photo, so the answer is not just about one
component** (`memory/send146_probe2.py` prints it):
- **Stored marks on the LEFT photo: 7, and not one is a base line** — 5 AI
  opening rects, the body zone, the dormer. There is no starter mark, no
  wall-base mark, no eave mark: SEND-143 left all three as named refusals and
  SEND-146 was ruled *"no new mark types in this send"*.
- **The run carries no base geometry either**: `raw_ai` has `starter_lf` (a
  house-level LF number, not a pixel), and the words *grade*, *foundation* and
  *ground* appear only in prose. The nearest thing to a start line is LEFT's own
  reading note — *"27-course count at rear-left corner with **visible start
  line** (foundation band excluded)"* — and that is **PROSE about photo 1, a
  corner shot**, not a y on photo 2. Prose is not a position.
- The rail on that photo already says it out loud: *"no wall BASE is marked on
  this photo — a zone outline does not say which of its edges is the base…"*

**So the LEFT box's bottom EDGE is drawn exactly where it was** — Howard's own
ITEM 2 words, *"keep the current box top and width"* — and the basis now
**refuses to call it a wall line**. The picture has not moved; the claim has.
**The bottom will only move when a real start line exists** (the mark-type
send), and that is Howard's ruling to make, not mine.

## WHAT WAS WIRED (ITEMS 1 + 2), AND THE RE-PULLED LEFT BOX

`first_floor_anchor` now classifies before it places, off the row's own
`type` — **no new detector, and `style` never promotes**: a `2-Lite Slider`
*window* stays a window; an unrecognised `type` is NOT a door to grade.

- **DOOR TO GRADE** (`garage_door` · `entry_door` · `patio_door` ·
  `sliding_glass_door` · `slider_door` · `french_door`) → its sill sets the
  bottom, `anchor: first_floor_door_to_grade`, and the basis names it: *"BOTTOM
  anchored to the sill line of 'front-gd1' — a DOOR TO GRADE (garage_door)…"*.
  **A window sitting LOWER than the door no longer takes the bottom** and is
  named on the row: *"A window sill is MID-WALL and set nothing here: …"*.
- **WINDOW ONLY** → `anchor: window_sill_indeterminate`,
  `anchor_bottom_from: None` (nothing is named as the bottom) and
  `anchor_bottom_sill_of` records what it happens to rest on. Basis: *"BOTTOM IS
  INDETERMINATE: no door-to-grade opening on this photo — bottom is not a wall
  line… A WINDOW SILL IS MID-WALL — it does not set the wall bottom. No drop
  from a sill is invented and no typical sill height is used: the box keeps its
  TOP and its WIDTH…"*.
- **NONE** → SEND-145's photo-bottom answer, unchanged and still INDETERMINATE.
- **THE SCALE IS UNTOUCHED**: a window is an honest RULER even when it is not a
  FLOOR — LEFT still scales 17.6 px/ft off `left-w3`.

**(d) EXECUTED EXACTLY AS ORDERED** (`memory/send146_repull_left.py`, which
refuses unless it matches exactly ONE provisional body zone): `face:left:body`
deleted (1 doc), that one zone re-pulled. **Marks on the estimate: 23 before,
23 after.** FRONT (hand-tweaked) not cleared · BACK not cleared · the LEFT
dormer, all openings and the LEFT scale not cleared — the re-pull reported
`already_there: 6` and `proposed: 1`.

The re-pulled LEFT body, live: `x 5.9 → 640.0` (still cut at the 640-px frame),
`y 166.2 → 314.0`, `ppf 17.6`, `anchor: window_sill_indeterminate`,
`bottom_from: None`, `sill_of: left-w1`. Verified in the browser: the box is
where it was and **"BOTTOM IS INDETERMINATE" now prints on the row**.



A re-pull is keyed `(run_id, face:left:body)` and **never overwrites a zone
that is already there**, so with LEFT's current body zone in place the new
bottom **cannot be seen**. To show it, LEFT's `face:left:body` zone has to be
deleted first. **I have not deleted it and will not without Howard's word.**
FRONT's zones — which he tweaked by hand — are not touched either way.

## NOT TOUCHED

No second finder · no re-OCR · no quote wiring · no price · no new mark type ·
no "snap to start line" button · **no drop-from-sill convention and no typical
sill height** · EST-886440 untouched.
