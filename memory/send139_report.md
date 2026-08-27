# SEND-139 — GABLES AND DORMERS MOVE INTO PHOTOTAKEOFFEDITOR · THE ANNOTATE DOORS COME OFF — 2026-08-27

**STAMP: `2026-08-27 21:54 UTC · b00f642 · CLEAN · 3030 passed, 9 skipped,
7 warnings in 455.91s`** · census pin GREEN, 0 PENDING_CONVERSION · ingress
smoke 4 passed. **Pre-stamp reds: 3, all of them the guard catching THIS
send's authorised removal** (pins that asserted the retired doors EXIST) —
all three fixed as NAMED PIN UPDATES, no assertion weakened:
`test_send131a` (the takeoff entry point is now THE drawing door, and the
old one is pinned ABSENT), `test_refine_single_annotation_system` (re-cut:
two annotation UIs became one — the rule is completed, not weakened), and
`test_dormer_annotations` (the natural-image-dims round-trip now rides the
surviving Guided Capture merge; its subject is unchanged).

28 pins in `tests/test_send139_gable_dormer_move_2026_08_27.py` · live API
e2e on a throwaway estimate (created and deleted, `memory/send139_e2e.py`)
· **all 7 browser verifications PASS** (`test_reports/iteration_60.json`).
The testing agent's two drawn marks were deleted from EST-373526 afterwards
— no live estimate keeps an agent's gable. **EST-886440 untouched.**

---

## ITEM 1 — WHAT ANNOTATE ACTUALLY DOES (reported before a line was written)

### THE GABLE TOOL (annotator, ruled 2026-07-24)

**How the contractor draws it.** THREE TAPS, in order: **LEFT EAVE →
PEAK → RIGHT EAVE**, on the photo itself. The prompt changes with each
tap ("Tap the LEFT EAVE point of the gable." → "Tap the PEAK (ridge)
point." → "Tap the RIGHT EAVE point to finish the triangle."). Any vertex
can then be **dragged** to refine it; two fingers cancels a drag. Multiple
gables per photo.

**What is typed.** Nothing is typed for the AREA. Two optional controls
shape the triangle:
- **Symmetric gable** (checkbox) — mirrors the peak to the base midpoint.
- **Pitch** — a preset (4·5·6·7·8·9·10·12 /12) or a typed custom value.
  Selecting a pitch MOVES THE PEAK (`rise = base/2 × pitch/12`); dragging
  the peak re-derives the pitch. The pitch is scale-free and is never a
  quantity.

**What number it writes.** `gableNetArea` in `lib/gableMath.js`:
- base = the eave-point span in pixels;
- rise = the **PERPENDICULAR** distance from the peak to the eave line
  (the eave line may tilt a touch — the perpendicular keeps it honest);
- **`grossAreaFt = (baseFt × riseFt) / 2`** — the TRUE TRIANGLE;
- minus every **NO-SIDING mask whose CENTROID sits inside the triangle**
  (vents, decorative panels, stone accents), clamped at ≥ 0 → `netAreaFt`.
- A cross-elevation ridge check warns (never blocks) when the largest
  implied rise disagrees by more than 1.0 ft between elevations.

**HOWARD'S QUESTION, ANSWERED PLAINLY: ANNOTATE DOES *NOT* MULTIPLY BY
0.70. IT NEVER DID.** The drawn gable has always been `½ × base × rise`.
The 0.70 factor lived on the DERIVED side (`measure_staging.walk_walls`
and friends), and SEND-137 retired it there. **So there was nothing to
convert on the way in — the tool being ported already obeys the ruling,
and a pin now holds `0.7` out of both the editor and the math module.**

**When a field is missing.** No WALL REF and no WIN REF on the photo →
no inches-per-pixel → `gableDims` returns pixels only, `grossAreaFt` is
`undefined`, the row reads **"dims pending scale ref"** and an amber
warning says the triangle still saves. A degenerate triangle (the two
eave taps on top of each other, or the peak on the eave line) simply
yields nothing — **but the annotator never NAMED that refusal.**

### THE DORMER TOOL (annotator, ruled 2026-07-25 — "a mirror of the gable")

**How it is drawn.** FOUR TAPS round the vertical face: **bottom-left →
bottom-right → top-right → top-left**, prompts stepping the same way,
vertices draggable, multiple dormers per photo, drawn with a dashed stroke
so it reads apart from a gable triangle.

**What is typed.** **DEPTH (ft)** — one field, ruled 2026-07-26: *typed,
never photo-derived*, because depth is measured on the roof and cannot be
seen in a photograph of the face.

**What number it writes.** `dormerNetArea`: width and height each
**AVERAGE the two opposing edges** (a touch of tilt averages out
honestly); face area = width × height, minus masks whose centroid sits
inside the quad, clamped ≥ 0. Cheeks = **2 × face height × depth**.

**When the depth is missing.** The annotator **SUBSTITUTES A 1.5 ft
DEFAULT** and labels it "(default depth)". That is a fabricated number
wearing a small label.

---

## THE TWO DEVIATIONS FROM A LITERAL PORT — NAMED, NOT SMUGGLED

Everything else came across unchanged. Two things could not:

1. **THE 1.5 ft DEFAULT DEPTH DOES NOT COME ACROSS.** In the new editor an
   untyped depth **REFUSES THE CHEEKS BY NAME** — *"cheeks REFUSED — depth
   is measured on the roof, never read off the photo. No default depth."*
   The face area still stands (it was drawn); only the cheeks refuse. This
   is the same rule that refuses a gable with no rise: **missing evidence
   does not become a number.** A pin holds the 1.5 out.
2. **EVERY REFUSAL IS NOW NAMED.** Where the annotator quietly produced
   nothing (no scale, no width, no rise, wrong point count), the editor
   says which mark refused and why, in the rail and on the record — and
   the ft² is `None`, **never 0**.

One tightening worth stating: **only CONFIRMED masks subtract.** A
provisional mark carries no quantity anywhere in this editor, so it may
not silently reduce one either.

---

## ITEM 2 — THE TOOLS, MOVED

**The gesture is the annotator's gesture, word for word** — a pin asserts
each prompt string appears in BOTH files, so it cannot drift.
**The fields are the annotator's fields** — symmetric · pitch preset ·
custom pitch · dormer depth, with pitch still moving the peak by
`rise = base/2 × pitch/12`.
**The math module is the annotator's own** (`lib/gableMath.js`, imported,
not copied) so there is no second implementation to disagree with.

**THE QUANTITY RULE.** `_gable_figure` in `routes/photo_takeoff.py`:

| condition | result |
|---|---|
| 3 points, width > 0, rise > 0, scale present | **½ × width × rise**, less confirmed masks inside |
| point count ≠ 3 | REFUSED: "a gable is a triangle: LEFT EAVE, PEAK, RIGHT EAVE" |
| the two eave taps coincide | REFUSED: **NO WIDTH** |
| the peak sits on the eave line | REFUSED: **NO RISE** — "never a 0 and never a factor on an unmeasured triangle" |
| no scale on this photo | REFUSED: "width and rise have no feet, so there is no area" |
| pitch outside 3/12–18/12 | measured anyway, with a **warning, never a block** |

**GUIDANCE UNTIL CONFIRMED · QUANTITY, NEVER MONEY.** A gable lands
`provisional` like every other mark and contributes nothing until it is
confirmed; the rail shows an em dash, not a 0. Apply writes
`photo_gable_sqft`, `photo_dormer_face_sqft`, `photo_dormer_cheek_sqft`
under the photo lane's own keys — a pin scans the whole route for
`total_sell`, `unit_price`, `mat`, `lab`, `margin` and finds none, and the
live run wrote **0 priced lines and no total_sell**.

**A FACE WITH NO PHOTO STILL GETS NO GABLE.** A mark is geometry on ONE
photo; nothing is mirrored or copied, and the basis line on the figure
itself says so: *"A face with no photo gets no gable: nothing here is
copied from another face."* The AI read proposes no gable and says why —
it returns a rise NUMBER, not a triangle, so nothing is placed at a
guessed spot.

**DORMER DEPTH IS A QUANTITY INPUT, NOT A GUIDANCE CLAIM.** Changing it on
a CONFIRMED dormer returns the mark to PROVISIONAL — a confirmation cannot
outlive the figure it was given for, exactly as a geometry change already
did.

**"PULL IN WHAT I ALREADY DREW" NOW CARRIES GABLES AND DORMERS**, with
their symmetric flag, their pitch and their typed depth, as PROVISIONAL.
A depth the contractor never typed arrives as **nothing**, not as 1.5.

### THE LIVE API RUN (throwaway estimate, then deleted)
```
gable 30.0 ft × 8.0 ft rise, pitch 6.4/12   →  120.0 ft²   (½ × 30 × 8)
                                    0.70 × 30 × 8 = 168.0  →  NOT WHAT IT SAYS
2-point gable                       →  400, refused by name
provisional gable                   →  rail: None (em dash), not 0
dormer 6.0 × 10.0                   →  face 60.0 ft², cheeks REFUSED by name
depth 2.0 typed                     →  mark demoted to provisional
re-confirmed                        →  cheeks 40.0 ft² (2 × 10 × 2)
apply                               →  photo lane keys written · 0 lines · total_sell None
```

---

## ITEM 3 — THEN THE DOORS CAME OFF (and only the doors)

**REMOVED** from `AIMeasureButton.jsx`:
- the photo tile's **Annotate / Edit annotations** button;
- **Refine on Photo** (under Advanced Tools);
- the **Refine on Photo photo picker**;
- **the annotator's mount and import on this screen**, plus the state that
  served them (`annotateOpenFor`, `annotateGuided`, `refineOpen`).

**KEPT**, verified live: PhotoTakeoffEditor (the ONE drawing door, 8 tiles)
· **pull in what I already drew** · the **Guided Capture Wizard** (its own
mount, not an Annotate door) · Advanced Tools for the debug view · the
annotator as an **import source only**. A pin fails if the annotator's
name reappears anywhere in `AIMeasureButton.jsx` outside a comment.

### THE FIVE BROWSER VERIFICATIONS HOWARD ASKED FOR
1. **Gable and dormer can be drawn in Photo Takeoff** — 3 taps and 4 taps,
   on real photos of EST-373526. PASS.
2. **The quantity is ½ × w × rise, or refused** — panel read
   `14.0 ft × 5.1 ft rise · ½ × w × rise = 35.4 ft²`; the rail read an
   **em dash while provisional** and **35.44 ft²** after the confirm. The
   retired factor would have printed 49.98. The basis line printed
   verbatim. Dormer: face 29.3 ft², **cheeks em dash + named refusal**,
   depth 2 typed → demoted to provisional → re-confirmed → **18.75 ft²**.
   PASS.
3. **The Annotate doors are gone** — `ai-measure-photo-annotate-*` count
   **0** across all 8 tiles (iteration 59 still saw 8), `ai-measure-refine-btn`
   **0** before and after expanding Advanced, `refine-photo-picker` **0**,
   `photo-annotate-modal` never appears. PASS.
4. **Pull-in still works on old marks** — "Nothing new to pull in" on a
   virgin photo, no error, no 500. PASS.
5. **Guided Capture still opens** — the calibration gate that hands off to
   the wizard opens and closes. PASS.

---

## NOT AUTHORISED, NOT TOUCHED
Phase 2 trim · rectify · split storage · rederive sweep · quote wiring.
No estimate influenced another; no job name entered code; no face borrowed
another face's evidence.

## REGISTERED, NOT BUILT (the reviewer's note, for Howard's ruling)
`PhotoTakeoffEditor.jsx` is now ~800 lines and `AIMeasureButton.jsx` ~5,200
(it LOST 180 lines this send). A rail split is overdue; it is a refactor,
it was not authorised, and it was not attempted.
