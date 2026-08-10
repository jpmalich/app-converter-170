# AUDIT: WHICH RULINGS STILL LIVE ONLY IN THE PROMPT (Howard ordered 2026-08-09)

"A RULE IN THE PROMPT IS A REQUEST. A RULE AT THE SEAM IS A GUARANTEE."
Classification: SEAM (wrong behaviour unrepresentable) · CHECKED (violation
detected and flagged loud — reported, not prevented) · PROMPT-ONLY (a request;
nothing catches a violation).

## SEAM (guarantees)
- Evidence-or-null: bare numbers on DIM fields nulled by construction
- Count column governs: qty rewritten from printed cells; unread → 0 (2026-08-09)
- Marks face the locator: fabricated rows dropped, fabricated size quotes killed (2026-08-09)
- Interior-door drop: exterior_evidence "none" rows removed + accounted
  (BUT see PROMPT-ONLY #2 — the label itself is unverified)
- THE CUT (lp_smart rows), eaves = plane-sum override, gable rise pitch-computed
- Junk loc boxes die; a box never rescues a missing quote; OCR location-never-value
- One aggregation copy (measure_staging); waste chip idempotent

## CHECKED (flags, not guarantees)
- window/door_size_parse_mismatch (printed_size re-parse vs carried numbers)
- mark_size_conflict · count_cell_conflict · count_column_absent
- corner invariant (out − in = 4) · averaged-corner-LF basis smell · corner_taller_than_wall
- porch_run_vs_width · porch_dims_vs_area · run_exceeds_facade
- footprint_missing · footprint_is_total_finished · wall_segment(s)_undimensioned/mismatch
- soffit_finish / overhang read-or-flag · box_model · gable_census_mismatch · gable_blind
- OCR quote misses on DIM evidence (all rotations) · determinism gate (stability only)

## PROMPT-ONLY (the list Howard asked for — longer than we thought)
1. **BARE-NUMBER FAMILIES EXEMPT FROM EVIDENCE-OR-NULL** — the biggest hole.
   Only _EVIDENCE_SCALARS (overhang, fascia), wall width/height + segments,
   porch dims, corner heights, and (closed 2026-08-09) roof-plane
   eave_lf/rake_lf + gutter-run lf are DIM objects. Everything else rides
   as bare numbers on the model's word, no quote, no locator pass:
   appendages faces_sqft · dormer_face_sqft · gable_triangle_height_ft ·
   avg_wall_height_ft · story_count · windows/doors width_in/height_in
   (checked ONLY when a printed_size string survives) · accent approx_sqft ·
   siding_pct_this_wall · opening elevations · top-level eaves/rakes/starter ·
   corner COUNTS · vent_count/shutter_count.
2. **Door exclusion SIGNAL** — HALF-CLOSED (2026-08-09): the machine now
   OCRs the product-code column and drops HOLLOW CORE / H DWL CORE /
   Garage-to-House rows regardless of the model's label
   (interior_signal_dropped). RESIDUE: a row whose schedule line OCR
   cannot join still rides the model's exterior_evidence label.
3. **SH/DH never retyped**: type_hint is never cross-checked against the
   product_code prefix we now carry (SH 3-0_5-0 → type_hint must be
   single_hung — checkable, unchecked).
4. **Profile callouts verbatim** (LAP/SHAKE/B&B, accents): the CALLOUT
   CENSUS (2026-08-09) covers the OMISSION direction (a printed family
   the read missed flags loud; accent leg FIXED 2026-08-09 send 7 —
   was reading a dead key). The FABRICATION direction stays open: a
   fabricated "SHAKE" quote still creates accent lines — NAMED GAP,
   see below.
5. **Gutter-run inventory discipline** ("one entry per continuous run, never
   re-list a segment, [] when unresolved"): only the width-vs-facade check
   exists; double-listed or invented runs are invisible (runs carry no
   evidence quotes — see #1).
6. **Corner-walk membership** (chase edges not double-counted, garage wing
   included): only the ±4 invariant is checked; WHICH corners made the list
   is unverifiable from the output.
7. **Elevation assignment of openings** (mark ↔ elevation sheet): never
   verified; drives per-elevation splits silently.
8. **4-digit shorthand parse conventions** (3050→36×60, 3068 door): enforced
   only via printed_size re-parse when a quote survives; code-only rows
   trust the model's arithmetic.
9. **sheets_identified page typing** (schedule/elevation/roof): unverified;
   only schedule_pages now get an implicit check via the mark locator.
10. **"Rely on printed dims, never measure pixels"**: unverifiable by nature —
    the determinism gate + locator are the only indirect witnesses.

## Candidate next seams (NOT built — Howard's call)
a. Extend DIM/evidence form to roof_planes + gutter_runs (quotes + locator
   on eave/rake figures) — closes the largest bare-number family.
b. Product-code column as the door-exclusion seam: OCR the code cell for the
   ruled interior markers; a "HOLLOW CORE" row carried as exterior is dropped
   + flagged regardless of the model's label.
c. type_hint ↔ product_code prefix consistency check (SH/DH) — cheap flag.
d. OCR-verify profile/accent callout quotes on their elevation sheets (same
   machinery as the mark locator).

## KNOWN UNINSTRUMENTED GAPS (named, not ordered)
1. GEOMETRIC OMISSION (Howard named it 2026-08-09 send 4): roof planes
   and gutter runs carry evidence for their VALUES (DIM-or-null,
   2026-08-09), but nothing detects a plane or a run that simply NEVER
   GOT READ. They carry no printed marks, so the schedule omission
   instrument cannot reach them — omission there means a geometric
   eave-line census (a different instrument). The two lines that moved
   most all week live here.
2. CALLOUT FABRICATION (Howard named it 2026-08-09 send 7): the callout
   census catches a printed family the read MISSED; nothing catches a
   family the read INVENTED — a fabricated "SHAKE" quote still creates
   accent lines. The same fabrication-vs-omission asymmetry closed on
   the schedule side, still open on callouts. Logged so it is not
   rediscovered in three weeks.
