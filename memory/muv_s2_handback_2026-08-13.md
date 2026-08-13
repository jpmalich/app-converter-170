# MUV S2 HANDBACK — Material Zone Editor (Howard pro-quotes replies 6/7)

Landed 2026-08-13. Backend fully verified (curl round-trip on EST-886440
+ full suite 2356 passed / 4 skipped). Frontend walked by the testing
agent 9/10, the one miss (an aggregate-line testid) fixed.

## THE THREE LAWS — BUILT AND PINNED

### A. REPLACE, never add + superseded stays visible
Confirmed the code already REPLACED (it never added). Fixed the two gaps:
- The app's original number is kept on `superseded_qty` +
  `overlay_superseded=True` and shown side by side in the editor's
  "App vs. your number" panel (e.g. `app 44 → you 9 SQ`).
- `overlay_sqft` carries the drawn ft² for the delta.

### B. A human value is a function of its polygons — pinned BOTH directions
- Delete one of several → the sum RECOMPUTES from what remains.
- Delete the LAST polygon of the material class → the override RETIRES,
  the app's number RETURNS, and the retirement is LEDGERED.
- Tests fail the build if (i) any line keeps `qty_src=human` /
  `overlay_superseded` after its polygons are gone, or (ii) a retirement
  restores anything other than the exact captured baseline.
- DURABILITY: the derived baseline lives on the POLYGON
  (`derived_baseline_qty`), not the line — the estimate editor's
  load/save merge strips unknown line fields, so a baseline on the line
  would be erased by an autosave and retirement would have nothing to
  restore. The polygon collection is never touched by that merge.

### C. Scale read from the sheet, never defaulted
- The hardcoded `3/16" = 1'-0"` constant is DELETED. It was a fact about
  Howard's house baked into code (purity rider).
- Every conversion needs an explicit, evidence-grounded scale: an OCR
  read of the printed dimension (`/measure/ocr-scale`) OR a human
  calibration line traced over a printed dimension. The scale travels
  WITH each polygon, so two zones in two views carry two scales — it is
  PER-VIEW by construction, not per-page.
- No scale for a view → the area is REFUSED: the polygon saves and holds
  its pixel geometry, `sqft` is None, the takeoff line is flagged
  `overlay_scale_unreadable` and NOT converted, and the surface says
  "scale not read on this view — cannot convert." No wrong-scale number
  ever ships.

## DISCOVERED LIMIT (named on the surface, not hidden)
The real takeoff (EST-886440) has NO per-face lines — siding is ONE
aggregate body line in SQUARES. So a polygon binds by MATERIAL CLASS to
that aggregate line (ft² → SQ ÷100), and `face_id` is carried as
metadata for the future per-face increment. The editor shows a
known-limit banner ("front/back aggregate every segment into one number;
no separate entry-gable face yet") and the impact row shows the zone
count, so a single-face zone replacing the whole-house aggregate is
never silent — Howard sees `app 44 → you 9 SQ · 1 zone`.

## REPORT-ONLY ANSWERS (no build)

### 1. Scale auto per-view region binding (follow-on cost)
S2 achieves per-view scale by the scale travelling with each polygon
(sourced from that view's evidence). FULLY-AUTOMATIC per-view scale
(auto-detect every view region on a page and auto-OCR its printed SCALE
fraction) is NOT a one-field addition: the "anchor-gate region"
machinery Howard remembered is per-PAGE OCR crop bounds, not per-VIEW
scale regions. True auto binding needs: (a) view-region detection per
page, (b) OCR of each region's "SCALE:" text + "AS NOTED" handling, (c)
binding a polygon to the region it sits in. Estimate: ~1 increment. Not
needed for the walk — human trace / whole-page OCR cover it today.

### 2. Face vocabulary — segment + gable faces (cost, report only)
To carry `front:main`, `front:garage`, `gable:entry` etc. through the
whole chain:
- Polygon model: extend `face_id` grammar + validation (trivial).
- AI read: the blueprint worker must EMIT segment/gable faces with
  evidence (the heavy part — new schema fields + prompt + OCR verify).
- Takeoff binding: split the aggregate siding line into per-face rows
  (or a per-face breakdown the aggregate sums from) — touches the
  catalog→line mapper and the useEstimate merge (the sealed
  silent-strip layer), the riskiest part.
- Superseded display + legend: per-face rows each carry their own
  superseded value.
Estimate: ~1.5–2 sessions, and it belongs INSIDE the linear-edges
increment (segments + gable edges are the same geometry problem).
Open decision Howard flagged: is a gable triangle part of its wall's
face or a face of its own? Recommend a face of its own (`gable:<label>`)
— it has its own rake/soffit/fascia and its own triangular area.

### 3. "Merged says merged" (Howard's small ask) — DONE, trivial
Cost was trivial so it shipped with S2: any line fed by >1 polygon
carries `overlay_merged=True` + `overlay_polygon_count`, and the editor
shows the zone count on the impact row.

### 4. Which other human-entry values can outlive their basis? (report only)
Human-entry classes in the ledger are: `tape_check`, `tape_check_score`,
`profile_annotations`, `flag_checklist`, `pdf_overlay_polygon`. Of these:
- `pdf_overlay_polygon` — FIXED here (retires with its last polygon).
- `profile_annotations` — SUSPECT: an accent box sets an authoritative
  per-profile sqft on the material list; if the box is later deleted,
  does the injected accent line retire, or does it outlive the box like
  an orphaned human value? Worth the same question asked of MUV.
- `tape_check` / `tape_check_score` — a tape check is a point-in-time
  reading, not a basis a later value hangs off, so "orphan" is less
  applicable; but a tape_check_score that gates a verdict could outlive
  a deleted/blank tape reading. Worth a look.
- `flag_checklist` — checklist entries are their own basis; low risk.
Recommend a targeted audit of `profile_annotations` first. NOT a sweep.

## ORPHAN AUDIT RESULT — profile_annotations (2026-08-13, read-only)

VERDICT: **profile_annotations does NOT carry the permanent-orphan
defect we just closed on polygons.** It has a lesser, different gap
(run-staleness), described below.

How the accent actually flows (traced in code):
- `PUT /estimates/{id}/profile-annotations` (routes/estimates.py:714)
  ONLY replaces the `profile_annotations` blob + ledgers. It does NOT
  touch `est.lines` and does NOT re-run anything.
- The box `sqft` lands on the materials list ONLY during an AI
  Measure / Blueprint RUN, via `apply_annotations_to_breakdown` /
  `_aggregate_to_hover_shape(raw, annotations)` (routes/ai_measure.py
  ~1504–1755). The run REBUILDS the breakdown from `raw` + the CURRENT
  blob every time ("re-aggregates _per_profile_sqft"; prompt at 1425
  confirms boxes are "counted once downstream, straight from the boxes"
  and the AI is told NOT to double-count).
- `is_accent` exists NOWHERE in the backend except the new
  pdf_overlay.py — there is no persisted human-authority accent line on
  `est.lines` that a rebuild shields. The box-derived accent is a pure
  function of the boxes AT RUN TIME.

So, the two directions:
- Delete a box → the blob shrinks. A SUBSEQUENT run rebuilds without it →
  the accent disappears CLEANLY. No shield preserves it (unlike the
  polygon human-chip line). ✅ No permanent orphan.
- BUT between the box-delete and the next run, `est.lines` still shows
  the PREVIOUS run's accent. That is ordinary RUN-STALENESS (every
  measurement is stale until re-run), NOT an orphan wearing the
  highest-authority chip that nothing downstream questions. The stale
  value is a DERIVED run output, replaced wholesale by the next run.

Risk: MEDIUM-LOW. A contractor who deletes a box expecting the
materials list to drop the accent won't see it change until they re-run,
and could quote stale. This is a UX honesty gap (the app knows the boxes
changed but the takeoff doesn't say "re-run to apply") — not a
data-integrity orphan.

If tightened later (NOT ordered): the smallest honest move is to flag
"profile boxes changed — re-run measure to apply" on the takeoff when the
blob's updated_at is newer than the last run. A heavier option would be
to retire box-derived accent lines immediately on blob PUT. Recommend
the flag.

## PARTIAL-COVERAGE SEMANTICS — named for later (Howard reply, not ordered)
A polygon should replace ONLY the faces it covers; unzoned faces keep
their derived contribution. This needs PER-FACE CONTRIBUTIONS in the
takeoff, which do not exist today (one aggregate siding line). It is
therefore STRUCTURAL, and BIGGER than segment-level faces:
- Segment/gable faces (~1.5–2 sessions) add face GRANULARITY to the
  vocabulary + AI read + one set of per-face rows.
- Partial-coverage adds, on top of that, a CONTRIBUTION MODEL: each
  face's derived ft² must be separately stored so a human zone can
  supersede one face's contribution while the others stay derived and
  the aggregate re-sums (derived faces + human faces). That touches the
  derivation pipeline and the aggregate roll-up, not just the vocabulary.
Estimate: partial-coverage is ~1 additional session ON TOP of
segment/gable, i.e. they are TWO jobs, done in order (faces first, then
contributions). Report only.
