# SEND-147 — THE WALL-BASE MARK. HUMAN TWO-TAP. NO DETECTOR.

Howard picked **option 2** on 2026-08-28: *"The start line gets its own stored
y. That y is the body bottom when it exists."*

Stamp: see the PRD entry for this send (`scripts/handback_green.sh`).
16 pins in `tests/test_send147_wall_base_2026_08_28.py`, plus 2 SEND-143 pins
and 1 SEND-145 pin updated **BY NAME** and 1 new SEND-143 pin. Live proof on
EST-176308 through the real API and the real browser, then **my own test taps
were removed** — Howard's tap will be the first one on that photo.

---

## 1. THE MARK RECORD (ITEM 1 — WHAT TO REPORT)

`kind: "wall_base"` · `shape: "line"` · **PHASE 1** · exactly **2 points**, and
a wrong count is refused by name:

> *"a wall_base needs exactly 2 point(s) in this photo's natural pixels — the
> LEFT end of the wall base, then the RIGHT end; nothing is padded or truncated
> to fit"*

| field | what it holds |
|---|---|
| `photo_key` | **the photo it belongs to** — it is stored against that ONE photo and is never read for another photo or another face |
| `points` | the two taps, in **this photo's NATURAL PIXELS**, exactly as they landed |
| `wall_base.a` | the **LEFT** end `{x, y}` — always the left, whichever way the taps went |
| `wall_base.b` | the **RIGHT** end `{x, y}` |
| `wall_base.y` | **THE STORED y** — the mean of the two ends. This is the ONE number the body bottom reads |
| `wall_base.tilt_px` | how far the two ends differ in y, **reported not hidden**, so a sloped tap is visible |
| `wall_base.units` | `"natural pixels of this photo"` |
| `status` | lands **PROVISIONAL**, like every mark |
| `basis` | *"WALL BASE — the start line you tapped on THIS photo… it is an ANCHOR, NOT A TRIM RUN: no LF is written for it, it is never priced, and it is never copied to another photo or another face."* |

**NO LF. NO PRICE. NO LENGTH AT ALL.** There is no `span_px`, no `hypot`, no
lineal figure anywhere in the record — a pin bans them from the function. The
rail cell prints **`anchor · no LF`**, not a number. The phase-2 `starter` RUN
is still unbuilt and still refuses.

Live record from the API (my test tap, since removed):

```json
{"kind":"wall_base","shape":"line","status":"provisional",
 "wall_base":{"a":{"x":40.0,"y":330.0},"b":{"x":600.0,"y":336.0},
              "y":333.0,"tilt_px":6.0,
              "units":"natural pixels of this photo"}}
```

## 2. THE GESTURE

The same two-tap as the scale, on that photo only. Tool button **WALL BASE**
(`photo-takeoff-tool-wall_base`), and the hint reads the taps out in order:
*"Tap the LEFT end of the starter / wall base."* → *"Tap the RIGHT end to
finish the start line."* — with *"an ANCHOR for the AI body bottom, never an LF
run"* beside it. A second tap under 8 px is refused (*"tap the OTHER end"*).
The line draws in its own orange, dashed while provisional, labelled
`WALL BASE·y 348px·provisional`. Its two ends are draggable like any vertex,
and a drag re-computes the stored y.

## 3. WHAT IT DOES

**When a wall_base exists on that photo it BEATS the door sill and it BEATS
window-indeterminate.** Basis: *"bottom from wall_base mark on this photo — the
start line YOU tapped (provisional, y=348.0 px, tilt 8.0 px across its two
ends), which beats every opening: an opening sill is not the wall base."*
`ai.anchor` becomes `wall_base_mark` and `ai.anchor_wall_base_y` records the y.

**THE TAP ITSELF MOVES THE BOX** — Howard's test is a tap, not a button press.
Creating, dragging, refusing or deleting a wall_base RE-BASES that photo at
once. **A re-base places NOTHING NEW**: a start line is an anchor, not a
proposal, so tapping one on a photo with no zones leaves that photo empty. A
plain STARTING ZONES press with no start line still overwrites nothing, exactly
as SEND-144 ruled.

**THE SCALE NEVER CHANGES.** A start line says WHERE the wall ends, never HOW
BIG a foot is: px-per-foot still comes from the read's own biggest first-floor
box (LEFT: 17.6 px/ft off `left-w3`). Where no opening carries a typed size the
basis says the WIDTH is still 80% of the frame and INDETERMINATE — *"only the
BOTTOM is evidence here"*.

**When it does not exist, SEND-146 is untouched**: door-to-grade → that door's
sill; window only → INDETERMINATE, no drop, no photo edge; none →
INDETERMINATE. Deleting the line puts a FRESH zone back on the read's own
answer and says so.

**A HUMAN-TOUCHED ZONE STAYS PUT** and the row says why. Three witnesses:
the PATCH route now stamps `human_touched` on every hand edit; a CONFIRMED or
REFUSED zone is a ruling; and — because **Howard tweaked FRONT's edges BEFORE
that stamp existed** — a zone updated long after the machine last wrote it
counts as touched too. `rebased_at` records the machine's own last write so a
re-base never mistakes itself for a hand. Today on EST-176308 that reads:
**AI front body, AI front gable and AI back gable = TOUCHED (they will not
move); AI left body, AI left dormer and AI back body = fresh.**

## 4. THE LEFT TEST, RUN FOR REAL (ITEM 3)

Through the real API, then through the real browser on the LEFT photo:

| step | LEFT body bottom | anchor |
|---|---|---|
| before | **314.0 px** — the `left-w1` DH sill | `window_sill_indeterminate` |
| tap a start line at y=333 | **333.0 px** | `wall_base_mark` |
| delete that line | **back to 314.0 px** | `window_sill_indeterminate` |
| tap again at y=348 (below the mulch line) | **348.0 px** | `wall_base_mark` |

Each move reported `moved: 2` — the body **and the dormer**, because the dormer
stacks on the body top and travels with a body that moves; the dormer's own
UNANCHORED sentence is unchanged. **In the browser** the orange WALL BASE line
drew where I tapped, the yellow body dropped onto it, and the strip of siding
from the sills down to the start line came INSIDE the box — the exact strip
Howard lost. **FRONT and BACK never moved** (no wall_base tapped on their
photos, and their zones are hand-touched anyway). **RIGHT stays refused.**

Then **I deleted both of my test lines**, and the LEFT body went back to
**314.0 px / window_sill_indeterminate**. There is **no wall_base mark on any
photo of EST-176308 right now** — Howard's tap will be the first, and the box
will drop to it.

## 5. ONE SENTENCE THAT WOULD HAVE BECOME A LIE

The Starter trim row said *"no wall BASE is marked on this photo"*. With an
orange WALL BASE line on screen that is false, so with a line present the row
now reads: *"a WALL BASE line IS marked on this photo, and it is an ANCHOR
ONLY — SEND-147 built it to set the AI body bottom and writes NO LF for it. The
starter RUN is not built in this send, so this row stays an em dash rather than
a number nobody ruled on."* **Still an em dash. Still no LF.**

## 6. NOT AUTHORISED, NOT TOUCHED

No AI starter finder (pins ban `find_starter`, `detect_starter`, and there is
no `cv2`/`numpy` anywhere near the anchor) · no corner tick · no eave · no
soffit · no fascia · no quote wiring · no prices · no second finder · no
re-OCR · nothing copied between photos or faces · RIGHT refused ·
EST-886440 untouched.
