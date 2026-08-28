# SEND-144 — THE HANDOFF: THE READ'S FINDINGS BECOME STARTING ZONES

Stamp, verbatim from `scripts/handback_green.sh`:

```
RECORDED: 2026-08-28 18:15 UTC · 9c62e6b · CLEAN
RESULT: 3113 passed, 9 skipped, 7 warnings in 469.93s (0:07:49)
CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none)
INGRESS SMOKE: 4 passed in 1.95s
```

Browser: `test_reports/iteration_64.json` (found the entry-point gap) and
`iteration_65.json` (**all 9 acceptance points pass** after the fix).
22 pins in `tests/test_send144_zone_handoff_2026_08_28.py`.

No second finder. No re-OCR. No quote wiring. No price. No material line. No
new mark types. RIGHT was not copied from LEFT. No contested height averaged.
EST-886440 untouched. **The zones are LEFT IN PLACE on EST-176308** for
Howard to open and move.

---

## THE REPORT, BEFORE ANY ZONE WAS DRAWN

The run: `556b9121…` on **EST-176308**, 8 photos, finished 16:51 on
2026-08-28, reference *"Contractor WALL REF bars (front/back 324", left
444") plus corner-anchored lap-course counts; WIN REF 36" bars for opening
sizes"*.

| face | body W × H (the run's own sources) | gable | dormer | openings boxed | zone? |
|---|---|---|---|---|---|
| **FRONT** | 27.0 × 10.9 — width `direct_ref`, height `direct_disagreement`, conf 70 | rise 6.5 ft → 87.8 ft² | none | 4 | **YES** |
| **BACK** | 27.0 × 9.7 — `direct_ref` / `direct_consensus`, conf 80 | rise 7.0 ft → 94.5 ft² | none | 3 (+ 26.2 ft² stone, NO geometry) | **YES** |
| **LEFT** | 37.0 × 8.4 — `direct_ref` / `direct_consensus`, conf 82 | none (rise 0) | 14.1 × 3.5 = 47.6 ft², **UNANCHORED** | 5 | **YES, dormer UNANCHORED** |
| **RIGHT** | **REFUSED** — *"no photo measured this wall's width (assumed_symmetric). Not measured. Not copied from another face."* | claimed 0 | claims 14.9 × 3.8, also UNANCHORED | 0 (its one opening was refused by the read) | **NO ZONE** |

**Where the live run differs from Howard's check table** — the live numbers
governed and nothing was tuned: heights **10.9 / 9.7 / 8.4** (check: 10.4 /
9.1 / 9.85) · gables **87.8 / 94.5** (check: 88 / 95) · left dormer **47.6**
(check: 49) · openings **4 / 3 / 5** and RIGHT refused **match exactly** ·
**both dormers flagged unanchored**, and the right one sits on a REFUSED
face so it gets nothing at all.

**Photo ownership** (the read's own elevation call): FRONT → photo 0 · LEFT →
photo 2 · BACK → photo 4 · RIGHT → photo 6 (refused). The four corner shots
(1, 3, 5, 7) own no plane: **a corner shot is not a fifth wall**.

**Scale**: no photo carried a takeoff scale, so every foot figure on a zone
is `—` until a tape exists on that photo. The WALL REF bars are what the AI
read; they are not a takeoff scale until the contractor's own anchor + typed
tape is on the photo. No course height is guessed.

## WHAT WAS WIRED

`backend/photo_zone_proposals.py` — one module, a READER of a finished run:
no OCR, no photo pass, no height/gable/dormer engine, and a pin fails it on
`pitch`, `prompt`, `anthropic`, `Image.open`, `average` and on any money or
material token.

- **BODY** — a rectangle in the face's own W:H, 80% of the photo's width,
  centred, near the bottom. Basis: *"AI STARTING ZONE — the read measured
  this FRONT face at 27.0 ft × 10.9 ft (width direct_ref, height
  direct_disagreement, confidence 70). the rectangle's SHAPE comes from
  those figures; WHERE IT SITS on this photo is a starting position and NOT
  a measurement — the ft² comes from the shape you confirm after you move
  it. the read's height readings DISAGREE: 10.9 ft vs 9.0 ft — NOT averaged.
  The starting rectangle uses the larger (10.9 ft) so you can pull it down"*.
- **GABLE** — only where the run reports a rise, using that rise, *"NOT
  derived from a pitch"*. The triangle sits in the body's own px-per-ft, so
  the rise reads back at exactly 6.5 ft.
- **DORMER** — only where the run reports one; LEFT's basis carries the
  run's own words: *"UNANCHORED: Dormer on the left slope reports 14.1 ft
  wide but NO reference marker was in frame. Unanchored dormer widths drift
  25-90% — re-shoot the left elevation with a WALL_REF or WIN_REF bar in
  frame before quoting"*. The depth is not typed, so the cheeks still refuse.
- **OPENINGS** — through the EXISTING proposer. The route calls
  `propose_from_read`; the new module cannot build an opening at all (a pin
  forbids the string).
- **REFUSALS** — a refused face and a corner shot answer in the run's own
  words and place nothing. RIGHT's dormer is not parked on a corner shot or
  on LEFT.
- **THE STONE** — the read's 26.2 ft² on BACK carries no geometry, so no
  non-siding zone is proposed: *masks are an INPUT to the read, never an
  output*. The pull says so out loud.
- **PROVISIONAL, KEYED, SAFE TO RE-PULL** — origin `ai_zone_proposal`,
  stage 2, keyed `face:<label>:<part>`; a second press adds nothing and
  **overwrites nothing** (verified live and in the browser: 6 marks before,
  6 after). Provisional zones feed **no quantity** — siding, gable,
  J-channel and rake all stay `—`.
- **CANDIDATE EDGES** — a body zone draws dashed edges labelled *starter
  candidate* (bottom), *corner candidate* (both verticals) and *eave /
  frieze candidate* (top). **No length, no LF, no key written**; a pin fails
  the component on `LF`, `sqft`, `ft²`, `toFixed`. Starter, corners, soffit
  and fascia remain named refusals even with a CONFIRMED body zone.
- **BOTH DOORS** — auto-propose fires at BOTH of the worker's completion
  points the moment a read finishes, and the per-photo **"starting zones"**
  button re-pulls (so a refused face can get zones once it has a photo). A
  **protected estimate gets nothing, not even a provisional zone** (423 at
  the door, and the auto path skips with that reason).

## TWO THINGS FOUND ALONG THE WAY

1. **THE ZONES WERE UNREACHABLE, AND THE FIRST BROWSER RUN CAUGHT IT.** An
   annotated photo is uploaded as a NEW FILE (`ai_<uuid>.jpg`), so the read
   looked at a **different file** from the one attached to the estimate — and
   the zones sat on the read's file while the tiles opened the estimate's.
   **No mapping between the two was guessed.** Instead the preview now
   carries *"The photos this read read — starting zones live here"*: eight
   buttons, each labelled with the **read's own** elevation call, opening the
   takeoff on the exact file the read read. Verified in the browser: STAGE 2,
   six marks on FRONT, seven on LEFT, refusals on RIGHT and on the corner.
2. **A FOURTH UPLOAD DOOR THE SEND-142 MOVE DID NOT NAME.** That annotated
   photo was written to the pod's disk ONLY — no object copy, no Mongo blob —
   so a pod replacement would take the very photo that now carries the
   zones. It now goes to object storage and the Mongo store as well, the
   disk copy stays as a working cache, and **a failed store REFUSES the
   read** rather than reading a photo it cannot keep.

## NOT TOUCHED
Quote wiring · prices · material lines · new mark types (corner tick, wall
base, eave) · blueprint zone work · the hover/photo storage lane split.
