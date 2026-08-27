# SEND-132 — ONE EDITOR, TWO STAGES (2026-08-26)

Stamp: `2026-08-26 · CLEAN · 2932 passed, 9 skipped, 7 warnings in 452.93s`
(2919 → 2932 = the 13 new SEND-132 pins.)
Browser pass: `test_reports/iteration_59.json` — **11/11, zero defects.**
Rig: `scripts/send132_ui_rig.py` (build / `--clean`) — a disposable
estimate carrying a CLONE of a real photo read on ONE photo, so both
stages are reproducible without touching a real estimate.

---

## 1. ANNOTATE CAPABILITIES NOW PRESENT IN PhotoTakeoffEditor

| Capability | In the takeoff editor | How |
|---|---|---|
| Siding zone | YES | tool `siding_zone`, tap corners, tap the first to close |
| Non-siding zone, 5 categories (brick · stone · stucco · garage door · other) | YES | tool `non_siding_zone` + the category strip, the annotator's own colours |
| Openings (window / door) | YES | tool `opening`, two taps on opposite corners |
| **Window style** | YES | `photo-takeoff-style-input` per opening mark (free text, as the annotator had it) |
| **Window height + width (typed inches)** | YES | `photo-takeoff-height-in` / `-width-in` per opening |
| Two-tap reference anchor | YES | `photo-takeoff-scale-start` + the ft/in ask |
| Typed tape figure, **tape beats anchor** | YES | `photo-takeoff-tape-*`, and the label states WHICH governs |
| Per-photo elevation label | NO — not moved | the takeoff lane is per PHOTO and does not assign elevations; nothing in phase 1 needs it. Recorded as not moved, not as done. |
| Gables / dormers / profile boxes / exposure calibration | NO — deliberately | not phase-1 mark kinds; exposure/brick-course stays a PRODUCT/INSTALL setting (see below) |

Beyond Annotate, the editor also carries: AI proposals (stage 2),
confirm/refuse/adjust/delete, per-mark provenance and basis, the product
picker with history, live quantities with every refusal named, and Apply.

**Exposure / brick-course inches: CLOSED.** They stay a PRODUCT / INSTALL
setting. They are NOT a second scale — the tape and the anchor measure
the photo. Nothing in `photo_takeoff.py` reads them, and nothing will.

## 2. THE ANNOTATE BUTTON — STILL PRESENT, BY YOUR ORDER

Annotate stays on the grid until **you** verify the import on a real
session. It is unchanged and still opens the old annotator.

**Its doors, counted honestly (three, not two — and one correction to
what I told you when I asked):**
1. **The photo-grid button** — `ai-measure-photo-annotate-{i}`
   (`AIMeasureButton.jsx:3446`).
2. **"Refine on Photo"** — gated behind the Advanced Tools toggle
   (`AIMeasureButton.jsx:4779`); it opens the SAME `PhotoAnnotateModal`
   in guided 7-step mode.
3. **The Refine photo picker** — the second step of door 2, choosing
   which photo to re-open (`AIMeasureButton.jsx:5136`).

**CORRECTION:** I said the Guided Capture Wizard was a separate Annotate
door. It is not. There are exactly three `setAnnotateOpenFor(...)` call
sites and all three are the above; the guided flow belongs to "Refine on
Photo", not to capture. Nothing was removed or retargeted this send.

## 3. STAGE 1 vs STAGE 2 AS THEY RENDER

**The stage is decided PER PHOTO** by whether a completed read actually
carried THAT photo. A read on another photo unlocks nothing.

| | STAGE 1 | STAGE 2 |
|---|---|---|
| Banner | blue, "STAGE 1 — BEFORE AI" | green, "STAGE 2 — AFTER AI" |
| Rail copy | "Marks here are GUIDANCE: the AI reads them, they do not price anything" | "Pull the read's proposals, then confirm, adjust, refuse or delete each one and add what it missed. A confirm here is EVIDENCE." |
| AI proposals button | DISABLED, and the reason is printed: *"no completed AI read carries this photo — Stage 2 is not unlocked here; a read on another photo unlocks nothing on this one"* | enabled |
| Mark badge | GUIDANCE (or GUIDANCE · IMPORTED) | AI PROPOSAL → EVIDENCE once confirmed |
| Stage 1 tools | available | still available — add what the read missed |

**WHAT WRITES QUANTITY.** Only a CONFIRM, and only to the photo lane.
A confirm requires a scale on that photo (no anchor and no tape → a
named refusal, never a 0). Verified in the browser: the Stage 1
guidance confirm wrote 7.03 ft²; the confirm before the scale was
refused by name.

**GUIDANCE NEVER LAUNDERS INTO EVIDENCE.** `origin` survives every
confirm. The confirm records `confirmed_stage`,
`confirmed_after_ai_read` and a `confirmed_basis` that is one of:
- `EVIDENCE — an AI proposal on this photo, checked and confirmed by the contractor`
- `EVIDENCE — confirmed with the AI read on this photo present (origin …)`
- `GUIDANCE-CONFIRMED — no AI read on this photo. It carries quantity; it is NOT evidence that an AI read was checked`
and the quantity payload carries `guidance_confirmed` + its note, so a
reader of the numbers alone cannot mistake one for the other.

**WHERE PRODUCT IS CHANGED.** On the mark, in the rail:
`photo-takeoff-product-select`, offering ONLY body-siding products
already on the job (accessories / soffit / fascia / trim / labour
excluded — verified: "TEST J blocks" was not offered, and a product the
job does not carry is refused 400). The swap:
- is recorded in `product_history` on the mark — **from → to, when, who,
  and the ft² at the moment of the swap** (verified: 7.03 ft²,
  `2026-08-27 01:34`, `hhunt6677@yahoo.com`);
- **does NOT drop the mark to provisional** — it alters the output, not
  the geometry;
- keeps `confirmed_under_product` on the mark, and the quantity's basis
  prints *"… ft² was confirmed under X, now assigned Y — the geometry
  did not change; the output did"*;
- moves the ft² in `siding_by_product`, which also rides the `apply`
  block as `photo_siding_by_product`.
**Geometry still drops the confirmation** (verified: the vertex drag
took 7.03 → 3.52 ft² and returned the mark to provisional). The two
rules do not blur.

## 4. THE IMPORT — ONCE, IDEMPOTENT, CLAIMS INTACT

`import-annotations` brings each photo's existing annotator marks in as
PROVISIONAL: non-siding zones with their category, and tagged windows as
POINT openings carrying **style, typed width and typed height**. Verified
live and in the browser: `2-Lite Slider / 48 / 36` arrived intact on the
mark; a second press imported **0**; the mark count did not move. The
photo's own reference anchor comes across as the photo's scale.

A point opening carries a COUNT and **no ft²**, named — box it here to
give it an area. Nothing is invented from a tap.

## 5. RECTIFICATION — REPORT ONLY

Full report: `memory/send132_rectification_report.md`. In short:
- the ft² math is **scaled orthographic**: one `inches_per_px` applied to
  the whole frame, `ipp²/144 × shoelace(px)`. It assumes one plane, one
  depth, no perspective, isotropy, no lens distortion. **On an oblique
  photo it measures the wall's PROJECTION**, roughly cos θ low (≈13% at
  30°, ≈29% at 45°, ≈50% at 60°) and non-uniformly across the zone;
- **a homography IS establishable — from one boxed opening with a real
  width AND height** (4 correspondences on the wall plane). That is the
  only clean source in frame today. The tape/anchor gives 2 points on a
  line and can never give a plane. Siding/brick courses are a product
  setting, not a measurement of this wall — that door stays closed;
- **front-on vs oblique IS classifiable** from evidence already on the
  photo: a boxed opening's pixel aspect vs its typed aspect; two boxed
  openings' inches-per-pixel disagreeing across depth; converging
  verticals. Where none is present the answer is **UNKNOWN**, and a
  guessed label would be the same defect as an invented ruler;
- an oblique photo should **NAME the plane basis on the figure**
  (`fronto_parallel_assumed` / `oblique_detected` / `unknown`), rectify
  only where a measured rectangle earns it (and report the residual
  against the other known openings), and otherwise **REFUSE the area and
  keep the marks** — plus ask for the one cheap thing that fixes it: one
  window's width and height;
- **NO correction factor was added.** Today's payload carries no
  `plane_basis`, so the fronto-parallel assumption is currently SILENT.
  Naming it is the first thing to fix if you authorise any of this —
  naming costs nothing and is not a correction.

---

## HOWARD'S DESTINATION FLOW (recorded, NOT built this send)
1. Upload photo 1; add the marks on that photo (siding / non-siding /
   openings / style / height / scale).
2. Same for the other 7 photos.
3. The AI runs and draws zones and lines for siding AND accessories on
   those photos.
4. The contractor edits anything the AI got wrong — in the same editor.
5. The material list fills in from the confirmed marks.
6. The quote can be completed.

**Not in this send:** accessory / trim lines (J-channel, finish trim,
corners, starter, soffit, fascia) · filling the material list ·
completing the quote · mixing photo quantities into blueprint/derived
totals. Step 3's zone/line drawing does not exist in the read yet — the
read returns NO zone geometry, and SEND-132 says so plainly rather than
inventing one.

## STANDING, UNCHANGED
Phase 1 kinds only · openings reported, never deducted · photo lane
separate from blueprint/derived totals · photo-generated elevations
hidden · blueprint path PARKED · one photo at a time, session photos
only · PdfOverlayEditor's drawing conventions · EST-886440 PROTECTED,
423 on every derived write · no job names in code.
