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
   porch dims, and corner heights are DIM objects. Everything else rides as
   bare numbers on the model's word, no quote, no locator pass:
   roof_planes eave_lf/rake_lf/gable_ends · gutter_runs lf · appendages
   faces_sqft · dormer_face_sqft · gable_triangle_height_ft ·
   avg_wall_height_ft · story_count · windows/doors width_in/height_in
   (checked ONLY when a printed_size string survives) · accent approx_sqft ·
   siding_pct_this_wall · opening elevations.
2. **Door exclusion SIGNAL** (HOLLOW CORE / H DWL CORE / Garage-to-House =
   interior): the seam trusts the model's exterior_evidence label; nothing
   re-reads the product-code column the ruling names. A hollow-core door
   labelled "elevation" sails through.
3. **SH/DH never retyped**: type_hint is never cross-checked against the
   product_code prefix we now carry (SH 3-0_5-0 → type_hint must be
   single_hung — checkable, unchecked).
4. **Profile callouts verbatim** (LAP/SHAKE/B&B, accents): no OCR
   verification that the callout prints on the elevation — a fabricated
   "SHAKE" quote would create accent lines. (Cross-check is a second AI
   opinion, optional — not a guarantee.)
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
