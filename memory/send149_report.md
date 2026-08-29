# SEND-149 — THE EAVE MARK. HUMAN TWO-TAP, SAME PATTERN AS WALL_BASE.

Howard's field check on EST-176308 first: *"Left / Front / Back bottoms sit on
the starter he tapped. Lawn out. Left dormer on the bump-out. Right empty. The
top now gets the same kind of evidence."*

Stamp, verbatim from `scripts/handback_green.sh`:

```
RECORDED: 2026-08-29 17:00 UTC · 3bf7eaa · CLEAN
RESULT: 3175 passed, 9 skipped, 7 warnings in 500.90s (0:08:20)
CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none); 8 removal(s) logged (see baseline REMOVAL_LOG)
INGRESS SMOKE: 4 passed in 2.35s
```

15 pins in `tests/test_send149_eave_mark_2026_08_29.py`, plus **6 pins updated
BY NAME** (SEND-139 point counts, SEND-143 kind set, SEND-147 ×4).

---

## 1. THE MARK RECORD (ITEM 1)

`kind: "eave"` · `shape: "line"` · **PHASE 1** · exactly **2 points**, refused
by name otherwise:

> *"an eave needs exactly 2 point(s) in this photo's natural pixels — the LEFT
> end of the eave / frieze, then the RIGHT end; nothing is padded or truncated
> to fit"* (a one-tap POST returns **400**).

| field | what it holds |
|---|---|
| `photo_key` | **the one photo it belongs to** — never read for another photo or another face |
| `points` | the two taps, in **this photo's NATURAL PIXELS**, exactly as they landed |
| `eave.a` | the **LEFT** end `{x, y}` — always the left, whichever way you tap |
| `eave.b` | the **RIGHT** end `{x, y}` |
| `eave.y` | **THE STORED y** — the mean of the two ends; the ONE number the body top reads |
| `eave.tilt_px` | how far the two ends differ in y — **reported, not hidden** |
| `eave.units` | `"natural pixels of this photo"` |
| `status` | lands **PROVISIONAL** |
| `basis` | *"EAVE — the frieze line you tapped on THIS photo … an ANCHOR, NOT A TRIM RUN: no LF is written for it, it is never priced, and it is never copied to another photo or another face … **It is not a soffit and it is not a fascia — neither of those is built.**"* |

Live record, from a real POST on the BACK photo (removed again by id):

```json
{"kind":"eave","shape":"line","status":"provisional",
 "eave":{"a":{"x":120.0,"y":438.0},"b":{"x":1180.0,"y":446.0},
         "y":442.0,"tilt_px":8.0,
         "units":"natural pixels of this photo"}}
```

**NO LF. NO PRICE. NO LENGTH.** The rail cell prints **`anchor · no LF`**.
The gesture: tool **EAVE** (`photo-takeoff-tool-eave`), hints *"Tap the LEFT
end of the eave / frieze."* → *"Tap the RIGHT end to finish the eave line."*,
a second tap under 8 px refused, drawn in its own purple, labelled
`EAVE·y 442px·provisional`, ends draggable like any vertex.

## 2. WHAT IT DOES

- **THE BODY TOP COMES FROM THE LINE**: *"top from eave mark on this photo —
  the frieze YOU tapped (provisional, y=442.0 px, tilt 8.0 px across its two
  ends)"*, `ai.top_anchor: eave_mark`, `ai.anchor_eave_y` recorded.
- **ONLY THE TWO HIGHEST VERTICES MOVE. NOT ONE x CHANGES. THE BOTTOM DOES NOT
  MOVE.** Proven live on BACK: `y 438.0 → 442.0` top, bottom **765.6
  unchanged**, `x 284.1 → 1195.9` unchanged.
- **THE HEIGHT BECOMES THE SPAN BETWEEN TWO LINES HE TAPPED**, and the basis
  prints both figures: *"this box's HEIGHT is the span between two lines you
  tapped: N ft at this photo's scale, NOT the read's M ft claim. Both figures
  are printed and neither is averaged."* The read's own claim stays recorded in
  `ai.claimed_height_ft`.
- **A HAND-MOVED BODY FOLLOWS THE EAVE ON ITS TOP**, same ruling as SEND-148
  for the bottom: the zone is not cleared, his sides and his bottom stay, and
  the sentence is appended to his own basis. **A CONFIRMED body drops back to
  PROVISIONAL** — *"the top moved to the eave line you tapped — re-confirm the
  new figure"*.
- **NO EAVE MARK → THE TOP STAYS EXACTLY AS IT IS** (`top_anchor:
  read_height_claim`), and deleting the line puts a fresh top back where the
  read's claim had it.
- **AN EAVE TAPPED AT OR BELOW THE BOTTOM IS REFUSED IN WORDS**: *"it cannot be
  a top: the TOP was NOT moved and nothing was guessed — re-tap the frieze
  above the start line."*

## 3. WHAT IT DOES NOT DO

- **NO AI EAVE FINDER** — pins ban `find_eave`, `detect_eave`, `eave_finder`,
  `frieze_finder`, and there is no `cv2`/`numpy` anywhere near the anchor.
- **NO SOFFIT, FASCIA, CORNER TICK OR J-CHANNEL** in this send. The soffit and
  fascia rows stop lying instead: with an eave line present they read *"an EAVE
  line IS marked on this photo, and it is an ANCHOR ONLY … A frieze line is not
  a soffit and it is not a fascia: neither run is built in this send, so this
  row stays an em dash rather than a number nobody ruled on."*
- **THE GABLE AND THE DORMER ARE NOT RESHAPED.** An eave tap re-bases with
  `scope="body"`, and every other zone is refused by name: *"'AI back gable'
  was not moved: an eave line only sets the BODY top in this send — the gable
  and the dormer stay exactly where they are."*
- **A CROSSED DORMER IS REPORTED, NEVER AUTO-FIXED**: *"THE NEW BODY TOP
  CROSSES '<dormer>': the eave line you tapped sits at y=… and that dormer
  reaches down to y=…, so the two overlap on this photo. NOTHING was auto-fixed
  and the dormer was not moved — this is reported for you to settle."*
- **NOTHING IS COPIED** between photos or faces. **RIGHT stays refused.**
- **NO DELETE-BY-KIND, EVER AGAIN.** My test line's id was recorded when it was
  created and only that id was deleted — `delete by id fbdc9aa7 → 200`.

## 4. HIS OWN TAPS, UNTOUCHED (state right now)

Three `wall_base` lines he tapped at 16:48–16:49 UTC are on the estimate and
**I did not touch one of them**:

| photo | line | y | tilt | the body that sits on it |
|---|---|---|---|---|
| FRONT `ai_f3c3b84f…` | wall_base | **1389.427** | 15.4 px | AI front body `y 739.3 → 1389.4`, bottom `wall_base_mark` |
| LEFT `ai_3112d120…` | wall_base | **325.289** | 1.4 px | AI left body `y 177.4 → 325.3`, bottom `wall_base_mark` |
| BACK `ai_5a9d8c20…` | wall_base | **765.553** | 6.1 px | AI back body `y 438.0 → 765.6`, bottom `wall_base_mark` |

**All three bottoms are on lines he tapped.** No `eave` mark exists on any
photo right now — mine was removed by id after the test. **RIGHT still has no
zone at all.**

## 5. THE TEST STILL TO RUN — HIS TAPS (ITEM 2 AND 3)

Tap the **EAVE** tool on FRONT, LEFT and BACK. Then I report, per face,
whether the body **TOP** moved to his line and whether the **BOTTOM** stayed
put. **I did not tap for him** — the one tap I made was on BACK, to prove the
record, and it was deleted by id.
