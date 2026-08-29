# SEND-146 — ITEM 1 + 3 REPORT, BEFORE A LINE IS WIRED

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

## THE CLEARING QUESTION — STATED, NOT ACTED ON

A re-pull is keyed `(run_id, face:left:body)` and **never overwrites a zone
that is already there**, so with LEFT's current body zone in place the new
bottom **cannot be seen**. To show it, LEFT's `face:left:body` zone has to be
deleted first. **I have not deleted it and will not without Howard's word.**
FRONT's zones — which he tweaked by hand — are not touched either way.

## NOT TOUCHED

No second finder · no re-OCR · no quote wiring · no price · no new mark type ·
no "snap to start line" button · **no drop-from-sill convention and no typical
sill height** · EST-886440 untouched.
