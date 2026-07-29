# STRAIGHT-ON S2 ACCEPTANCE + DEEP VERIFY AUDIT (2026-07-29, 6d8fe50)

## A. DEEP VERIFY SILENT-ZERO AUDIT (report only, nothing wired)
1. OLD finder (_ELEV_RE, hover_vision.py) matches "<Front|Back|Rear|Left|
   Right|Side A..D> Elevation" only. Current Hover format titles drawn
   pages with bare compass tokens (FRONT / FRONT-RIGHT / ...) — missed
   entirely.
2. Run-doc audit: 92 of 92 surviving `done` runs carry ZERO drawing pages
   (per_elevation_siding_from_drawing empty), including every REAL import
   in the window: 261 Haugh 18ac1820 + 3 Degree 7862dd2c / 96217b28 /
   e7a8d661. Run docs TTL 24h — history beyond that is reaped and
   unauditable.
3. Zero-page behavior: run_vision_pass returns ([], {}) — no warning, no
   named state; run completes done. UI: "Verifying with vision…" stage
   then a clean import with NO sanity-check banner. Deep Verify chips
   only attach to vision_elev_delta_* warnings, which require pages —
   so pure SILENCE. An absent verification renders identically to a
   passed one = the silent-zero class. (Also: deep_verify_cache_key is
   minted BEFORE the page render, so run docs carry a key to an empty
   cache.)
4. New locator is used ONLY by the S2 elevation read. Deep Verify still
   runs the old finder. Wiring is Howard's ruling.

## B. STRAIGHT-ON ONLY — SHIPPED + RE-RUN
Oblique pages dropped at page selection (CARDINAL_VIEWS pin). 261 Haugh
re-run (same persisted PDF, 4 pages):
- 63 ⚠ → 9 ⚠. Invented IDs 24 → 2 (W-320/W-329, digit-misreads of the
  W-32x series). Real-opening double-placements 22 → 0 (one region-label
  double remains). Invented facade WR-30: GONE.
- Openings: 37/39 placed (missed W-325, W-326 — only visible obliquely).
- Regions read 23/31; UNREAD: BR-4, BR-5, STC-1..4, WR-5, WR-18.
- STC-1 STILL GETS ZERO of its five openings (D-1→WR-1, D-2→WR-7 etc).
  REGION-BOUNDARY PLACEMENT IS THE REAL WEAKNESS, not the oblique views.
- 18'5" corner still read twice (WR-13 BACK, WR-16 LEFT). Cardinal pages
  actually yielded MORE height callouts than the 8-page run.

## C. HEIGHTS — corner dims cannot reliably carry facade height
3 Degree drawn pages print ONE facade height callout (WR-20 9'6") and 16
corner dims for 50 facades. Failure modes: (1) most facades have no
dimensioned corner; (2) corners disagree on gables/steps (WR-33 14'11"
vs 14'3"); (3) a corner dim is the CORNER TRIM length — on a gable end it
is not the wall's average height; (4) "near_facade" association is itself
a vision judgment. Corner heights work as CROSS-CHECKS + tall-corner
detection (never-average rule), not as the height input. The height input
remains HOVER-SCHEDULE stacked height (sided ÷ footprint perimeter) or
taped heights.

## D. W1 — PARKED by Howard (no build, warn-only rejected).

## E. 3 DEGREE — fresh S1+S2 (run a425e75577844733bb512e9fa4959782)
PDF verified from its own text: "Three Degree Road, PA". 4 pages read.
- Openings 21/35 placed; 14 missed (incl. D-2, D-5, W-101/102, W-211..214,
  W-318..321, W-323, W-330). 10 invented IDs, clean digit-misread pattern:
  W-314/315/316/317 invented on FRONT while real W-318/319/320/321 missed.
- Width callouts: 13 of 37 WR facades (35%) — total 178.7 ft, area from
  extracted dims 2071 ft² vs Hover-printed 4504 ft² (46% coverage).
  THE DRAWN PAGES DO NOT DIMENSION EVERY FACADE — per-facade width cannot
  drive the money formulas alone in this format.
- FORMULA COLUMNS (off extracted dims, heights per method C fallbacks):
  · HARD BATTEN 12" o.c. 10' sticks: 373  | shipped 465
  · HARD BATTEN  8" o.c. 10' sticks: 546  | shipped 465
  · PANELS ceil(area/40 × 1.30):      68  | shipped 155
  · PANELS off Hover-printed 4504:   147  | shipped 155 (delta-report repro)
Raw reports: /app/memory/evidence/s2_report_{run_id}.json + on run docs.
Guard: 2026-07-29 04:11 UTC · 6d8fe50 · CLEAN · 1576 passed.
