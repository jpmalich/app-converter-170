# SEND-136 — (A) NO PHOTO, NO WALL · (B) NAME THE PLANE — 2026-08-27

Browser check on a front-only rig (a CLONE of the real read on a
disposable estimate): refusal banner **1**, refused wall rows **3**,
stale note **1**, **Apply Measurements DISABLED**. PASS.
32 pins: `tests/test_send136_no_photo_no_wall_and_plane_basis_2026_08_27.py`.
**EST-381546 was not touched.** Nothing is tuned toward 370, 252,
1,243.8 or any dollar total — every arithmetic pin uses invented round
numbers (30 × 10 walls, 20 ft sides).

---

# BLOCK A — NO PHOTO, NO WALL

## 1. EST-381546: WHICH FACES HAD A PHOTO, AND WHAT EACH BECOMES

The read's own evidence fields, straight from the run doc
(`a48df681…`, 1 photo):

| Face | width | source | height source | `_source_photo_indices` | Verdict under the rule |
|---|---|---|---|---|---|
| **front** | 27.0 | `direct_ref` | `direct_single_reading` | **[0]** | **DERIVED** — 27 × 10.5 body + gable rise 6.4 |
| back | 27.0 | `assumed_symmetric` | `assumed_symmetric` | **[]** | **REFUSE** |
| left | 24.0 | `estimated_no_direct_view` | `assumed_symmetric` | **[]** | **REFUSE** |
| right | 24.0 | `estimated_no_direct_view` | `assumed_symmetric` | **[]** | **REFUSE** |

**One photo. One face. Three faces were carried by the front's number.**

Numbers as they stood, and as they stand under the rule (recomputed
through the same aggregator, no tuning):

| Figure | As it stood | Under the rule |
|---|---|---|
| siding_sqft | **1,312.92** (1,071 body + 241.92 gable = two mirrored gables) | **404.46** (283.5 body + 120.96 for the FRONT gable only) |
| gable ft² | 241.92 (front + a copied rear) | **120.96** (front only) |
| eaves_lf | 48.0 — **entirely the left+right widths, i.e. the two faces with no photo** | **REFUSED (None)** |
| rakes_lf | 57.8 | **REFUSED (None)** |
| starter_lf | 102.0 (the whole invented perimeter) | **27.0** — the measured face's own width, basis names it |
| outside_corner_lf | 42.0 | **REFUSED (None)** |
| inside_corner_lf | 0 | **REFUSED (None)** |
| footprint_perimeter_ft | 102.0 | **REFUSED (None)** |
| openings | 4, all `front` | **4 kept** — every one was seen in the photo |

Gable convention note: one gable = **0.70 × width × rise** (the trade
allowance, ≈1.4× the geometric ½·w·h). Howard's "370" is the geometric
reading of the same front (283.5 + 86.4); the pipeline's own convention
gives 404.46. **A separate, real finding:** the browser's live
`recomputeFromWalls` uses the GEOMETRIC ½·w·h while the backend uses the
0.70 allowance — the panel and the stored figure disagree by ~40% of the
gable on every gabled house. **Named, not touched** (the gable convention
is not in this send's authority).

**A refusal is None, never 0.** `None` is this project's established
refusal marker and the LP package reader already honours it; a 0 would
read as "measured and none".

## 2. WHICH CODE PATH PERFORMED THE MIRROR

Three links, named, not defended:

1. **The prompt asked for it.** `routes/ai_measure.py` instructs the
   model to return all four walls and to fill the unseen ones as
   symmetric placeholders — hence `width_ft_source:
   "assumed_symmetric"` and `"estimated_no_direct_view"` with
   `_source_photo_indices: []`. The model told the truth about what it
   had done; nothing downstream acted on it.
2. **`_aggregate_to_hover_shape(raw, annotations)`** — the single funnel
   every photo door passes through (AI Photo Measure, Apply
   Measurements, Restore preview, the shared `/measure/map`). It walked
   **all four walls** into `siding_sqft`, and derived `starter_lf` from
   the sum of all four widths, `eaves_lf` from
   `staging.eaves_from_walls(all four)`, and corners from
   `_corner_lf_from_walls(all four)`. **This is the function that turned
   a symmetry placeholder into money.**
3. **`recomputeFromWalls(walls)`** in `AIMeasureButton.jsx` — a SECOND
   money surface that re-totalled the same four walls in the browser, so
   a backend-only fix would have been undone on screen.
4. **The corner stick builders** in `routes/hover.py` floored at
   `max(1, ceil(lf / 12.5))`, so a refused corner lane still emitted one
   stick. (The LP corner builder already honoured refusals — SEND-129.)

## 3. WHAT APPLY MEASUREMENTS WRITES ON A FRONT-ONLY JOB NOW

Run through the real mapper (`routes/hover._build_lines`) on that same
read, before vs after: **44 priced lines → 28.**

GONE (every one of them derived from a face no photo showed):
- Trim 440 4/4 × 8 (rake/fascia sticks), Soffit panel + trim,
  **Gutters 5" K-style (74 LF)**, gutter end caps / inside + outside
  mitres / hangers / downspout elbows,
- **Outside corners: 4 sticks → none** (the corner lane is refused),
- Inside corner + finish-trim sticks off the refused faces.

CHANGED (per-face, front only):
- siding coverage lines fall with the ft² (1,312.92 → 404.46),
- **starter 9 → 3 sticks** (27 LF, the measured face),
- **J-channel 15 → 6** (front openings only),
- house wrap / nails / caulk follow the measured ft².

KEPT (they were never face-derived): window/door labour and disposal
fees, debris haul-away.

**Front only. Three faces refused. Accessories from refused faces gone.**

## 4. A FOUR-PHOTO JOB STILL PRICES FOUR WALLS

Pinned (`test_a_four_photo_job_still_prices_four_walls`): four walls,
each with its own `_source_photo_indices`, all `direct_ref` →
`_faces_refused == []`, all four faces DERIVED, siding 1,252 ft²
(1,000 body + two measured gables at the 0.70 convention), and
`eaves_lf`, `rakes_lf`, `outside_corner_lf`, `starter_lf`,
`footprint_perimeter_ft` all present and positive
(footprint 100 ft). **The rule costs an honest job nothing.**

## 5. THE RULE, AS BUILT
- One gate, at the one funnel: `_face_photo_evidence(wall)` → refuse if
  `_source_photo_indices` is present and EMPTY, or if a width/height
  source is a mirror / symmetry assumption / no-direct-view estimate.
- A refused face contributes **no ft², no gable, no dormer, no starter,
  no eave, no corner, no opening, no line**. Its claim is kept on the
  record (`_refused` + `_refusal` on the wall, `claimed_*` in
  `_faces_refused`) so the gap is NAMED, never erased.
- **Gables follow the face** — the mirrored rear gable is gone (pinned).
- **Openings on a refused face are refused**; an opening with no wall
  label is KEPT (it was seen in a photo — the label is missing, the
  evidence is not).
- House-level runs are refused whenever ANY face is refused, because the
  read computed them over the mirrored faces and they cannot be pulled
  apart afterwards.
- **Every restore is a door.** A run stored BEFORE this rule is
  re-gated ON READ: its mirrored faces are stamped REFUSED and the
  payload is marked `_face_rule_stale`, which **disables Apply
  Measurements** with the reason printed. Read-only; nothing is written
  back.
- **NOT A GUESS IN THE OTHER DIRECTION**: a refused face's row shows the
  refusal and **no editable width box** (pinned). A missing photo stays
  missing until a photo arrives or Howard draws that face himself in the
  editor.
- **PhotoTakeoffEditor** needs no gate: every mark lives on the photo it
  was drawn on and no code copies a mark between photos. **HOVER**
  numbers come from Hover's own report; the door is source-locked
  (SEND-135). Both stay under the same rule by construction.

---

# BLOCK B

## ITEM 1 + 2 — NAME THE PLANE, AND THE CLASSIFIER
`plane_basis` now rides every photo-takeoff quantity payload and is
printed in the editor rail beside the figures
(`photo-takeoff-plane-basis`). **Three values, no fourth** (pinned):
`SQUARE-ON` · `OBLIQUE` · `UNKNOWN`. The surface falls back to UNKNOWN,
never to square-on. **The silent fronto-parallel assumption is over.**

The classifier (`_plane_basis`) uses only marks already on the photo:
1. **a boxed opening's pixel aspect vs its typed aspect** — within 8% →
   SQUARE-ON, naming what earned it; compressed → OBLIQUE with the
   angle it gives (a box at half its aspect indicates ≈60°); stretched →
   OBLIQUE **with the angle withheld**, because a turned wall and a
   tilted camera both explain it and the evidence cannot separate them;
2. **two boxed openings' inches-per-pixel across depth** — >15% apart →
   OBLIQUE ("the scale falls off across this frame"); within 8% →
   supports SQUARE-ON;
3. **converging verticals — NOT TESTED, and it says so**: phase 1
   traces no vertical lines, so the test cannot run. A test that cannot
   run is declared, not silently passed.

**WHAT IT SAYS ON EVERY PHOTO IN HAND.** Marks exist on two photos
(both on the SEND-132 rig) and the AI reads carry boxed openings on one
more:
- rig photo `ai_c7b431…` (4 AI-proposed openings with typed sizes) →
  **SQUARE-ON**;
- rig photo `347130b5…` (3 marks, no typed opening sizes) →
  **UNKNOWN**;
- **EST-381546's front photo** — running the classifier over that read's
  4 boxed openings (all with typed widths and heights) → **SQUARE-ON**,
  no angle. *That is the first photo in the system that earns a verdict,
  and it earns the good one.*
- Every other photo in hand → **UNKNOWN**: no boxed opening carries both
  a typed width and height, so nothing can be tested. **That is the
  correct starting state.**

## ITEM 3 — RECTIFY: NOT BUILT
No homography, no rectification, no warp, no correction factor (pinned:
those tokens may not appear, and the only trigonometry in the module
lives inside the classifier and reports an ANGLE — it never scales a
figure). The 13% / 29% under-read stays on the record, and the typed
window width and height keep being collected against the day it is
authorised. When it is: residual against the other known openings is
required; one boxed opening with nothing to test against refuses; no
factor from an unmeasured angle.

## ITEM 4 — NAMED GAPS FROM THE CONSOLIDATION (registered, not built)
- **GABLES AND DORMERS were not moved into PhotoTakeoffEditor.** They
  live only in Annotate, and Annotate is being retired. **Named gap.**
- **THREE Annotate doors, not two**: the grid button
  (`AIMeasureButton.jsx:3446`), **Refine on Photo** behind Advanced
  Tools (`:4779`), and the Refine photo picker (`:5136`). The Guided
  Capture Wizard is **NOT** a separate Annotate door. **All three come
  off together after Howard verifies the import — not before.**

## ITEM 5 — STAGE 2 HAS NO WALL PROPOSALS (recorded)
The current AI read produces **openings and marks, not wall polygons**.
The contractor still draws every siding and non-siding zone himself.
**Propose-and-correct on photos is currently CORRECT-ONLY for openings
and ADD-ONLY for walls.** No wall proposal is invented to fill the gap;
the Stage 2 pull states the absence in words every time it runs.

---

## NOT AUTHORISED, NOT TOUCHED
Rectify-from-a-window · splitting hover/photo storage · Annotate
retirement · the import test as a build · phase 2 trim · quote /
material-list wiring · any door audit beyond the mirror path above.
