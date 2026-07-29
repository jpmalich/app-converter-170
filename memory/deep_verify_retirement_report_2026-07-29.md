# DEEP VERIFY RETIREMENT — CARRY-OVER REPORT (2026-07-29, report only)

Howard ruled: RETIRE Deep Verify; the straight-on S2 elevation read
becomes the single verification pass. Before execution, the three
answers he ordered.

## 1. What Deep Verify does that the S2 read does NOT
- **Scale-bar pixel re-derivation.** Deep Verify re-measures a wall's
  area from the drawing's scale bar while explicitly IGNORING the
  printed callouts — an independent measurement that could catch a
  WRONG PRINTED CALLOUT. The S2 read transcribes printed callouts ONLY
  (pixel-derivation is prompt-forbidden). Retiring loses this
  capability — noting plainly: it has produced NOTHING on the current
  format since 24 June, so nothing is lost in practice.
- **On-demand, per-elevation, contractor-triggered** (~$0.40/click chip)
  vs S2's whole-PDF read.
- **3-way reconcile** (deep read vs Phase 2 drawing vs text tables).
- **Phase 2's per_elevation_siding_from_drawing** fed
  elevationBuilder.js (2D elevation preview + email elevations for
  Hover estimates). Empty since 24 June on this format — those surfaces
  already receive nothing from Hover imports and keep working from
  AI-measure/blueprint shapes.

## 2. What breaks when the stage goes
- Backend removals: `/api/estimates/hover-deep-verify` endpoint ·
  `hover_page_cache` collection + TTL index + cache writer ·
  `deep_verify_cache_key` on run docs · `run_vision_pass` /
  `_read_one_elevation` / `_build_warnings` / `deep_verify_elevation` /
  `reconcile_deep_verify` in hover_vision.py. KEPT: `_render_pdf_pages`
  (S2's legacy-format fallback), `MODEL_NAME`, `_json_from_reply`
  (S2 imports them).
- Frontend removals: Deep Verify chip/panel/state in HoverImportButton;
  `vision_elev_delta_*` rows stop arriving (generic warning renderer
  stays — the S2 read's warnings ride the same banner).
- Tests to rewrite/retire: test_hover_vision.py,
  test_hover_import_async.py (stage references), any deep-verify pins.
- NOT affected: Blueprint door (own `_per_elevation_breakdown`, does not
  use run_vision_pass); AI Measure; all money paths (the stage never fed
  money).
- Replacement wiring (same change): S2 straight-on read runs at import,
  results on the run doc, warnings on the import banner, LOUD zero-page
  state ("0 elevation pages found — format not recognized") every time.
  NOTE: S2-at-import ≈ 4 vision calls/import (~1–2 min, ~$1–2) vs Phase
  2's 4-6 — cost-neutral. S3 stays unwired: nothing feeds flags/counts.

## 3. Register + detector — DONE (shipped this session)
- `verification_integrity_register.md` 2026-07-29 entry: SILENT-ZERO-
  VERIFICATION class named, 92-of-92 sighting recorded.
- Detector `tests/test_verification_silent_zero.py` (4 pins): the
  vision-verify stage cannot yield nothing silently (both empty-result
  AND exception branches must emit the loud `vision_zero_pages`
  warning); S2 zero-pages stays a named error; register text pinned.
- ALREADY LIVE (this commit): every import whose vision pass finds
  nothing now shows "DRAWING VERIFICATION DID NOT RUN — 0 elevation
  pages recognized…" on the import banner. The silent-zero is dead
  ahead of the retirement.
