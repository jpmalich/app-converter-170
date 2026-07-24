# HOVER-NATIVE ELEVATION SHEETS — SIZING REPORT
Report only (no build). Rung authorized SMALL–MEDIUM, DEFERRED behind budget
discipline — Howard calls the timing. Grounded in the live codebase and Jon's
actual run (2.1 MB Hover PDF, 30,366-char text layer, run 8f6f9b5e…).

## 1. What the sheet renderer needs (the as-built input contract)
`routes/elevation_sheets.py` (read-only, zero writes) binds EL-1..EL-4 from:
  • per wall: width basis + height basis (stepped walls keep per-segment
    courses×exposure lines — no interpolation), roofline (eave, gable rise,
    ridge derivation), every value with tag + named-source basis string;
  • openings: CLOSED five-key contract {windows, doors, patio_doors, vents,
    garage_doors}, each with w×h, position, AI tag / ratify state, collision-
    guard registration;
  • accents: chimney chase (dims ladder), dormers (photo-chain v-pos,
    paired-feature reconciliation), shutters.
Sources today — a two-rung ladder:
  Rung 0 · TAPED — sealed tape key (`LETRICK_TAPE_WALLS`, constants).
  Rung 1 · PHOTO-AI — `ai_measure_runs` extraction (AI-READ ✓/⚠, ESTIMATED).
HARD LIMIT: the binder requires an `ai_measure_runs` doc. Hover-sourced
estimates (Jon) have NO sheet path at all today — that is the gap this rung
closes.

## 2. What the Hover PDF actually contains (per-wall geometry inventory)
A. TEXT LAYER — deterministic, ALREADY parsed by the importer:
   • totals: facade/siding areas (with the openings-adder waterfall), corners
     qty + LF, eaves/rakes/starter/frieze/drip-edge LF, trim, roof area;
   • `per_elevation_siding`: front/back/left/right net siding ft² (table);
   • Doors & Windows SCHEDULE: per-opening ID (W-101, D-1, SGD-1, OHD-1) with
     width×height in inches — the pipeline already extracts `windows[]` WxH
     and the pinned door-classification rules. Openings MEASUREMENTS need no
     vision at all.
   NOT in the text layer (or not associable from it): which wall an opening
   sits on, wall-segment widths/heights per elevation, opening x/y placement,
   stepped-wall breaks, gable-vs-hip per face.
B. ELEVATION DRAWING PAGES — 4–6 pages, ALREADY located and rendered:
   `hover_vision._render_pdf_pages` finds them by on-page text and renders
   144-DPI PNGs (Phase 2 sends each to Claude Vision for the area
   cross-check; Phase 3 Deep Verify reuses the same renders, Mongo cache TTL
   1 h). These pages carry exactly what the sheets are missing: wall-segment
   dimension callouts (lengths, eave/ridge heights) and every scheduled
   opening DRAWN IN POSITION on its wall, to scale.
C. NOT in the PDF anywhere: numeric opening positions (drawn, not tabulated),
   interior return depths, per-wall material transition lines (partial).

## 3. The geometry-source ladder (proposed contract)
Per-element resolution order — every value keeps a named source; divergence
between rungs FLAGS, never averages (paired-feature reconciliation precedent):
  1. TAPED — sealed tape key (unchanged, always wins where it exists).
  2. HOVER-SCHEDULE — text-layer openings WxH. Deterministic parse of a
     measured document: the strongest untaped rung. Never overwritten by a
     vision read.
  3. HOVER-DIM — wall dimension callouts read OFF the drawing pages. Hover
     measured them, but they arrive through a vision read → tagged
     HOVER-READ ✓/⚠ (mirroring the `_AI_TAGS` states), never presented as
     TAPED. Vision also PLACES scheduled openings (wall assignment +
     horizontal center + sill fraction) — placement only, dims stay rung-2.
  4. PHOTO-AI — existing `ai_measure_runs` chain (unchanged fallback).
  5. ESTIMATED — labeled, last resort.
Basis strings name the page: "HOVER dim callout · front elevation p.6 ·
HOVER-READ ✓". Cross-rung tripwire: per-wall vision totals must reconcile to
the text `per_elevation_siding` within tolerance, else the wall drops to ⚠.

## 4. What it takes — three slices (fits the authorized S–M envelope)
S1 · SUBSTRATE PERSISTENCE (SMALL)
   Keep the elevation-page PNGs past the 1 h TTL once an estimate
   materializes from the run (or persist the source PDF as an upload blob).
   Same asset class as the post-September split-class signed-URL work — do
   them together to avoid touching upload security twice. Check Jon's PDF in
   as a fixture for pins.
S2 · WALL-GEOMETRY EXTRACTION (MEDIUM — the only new AI surface)
   One vision call per elevation page (reuses the Phase-2 render batch and
   its 6-page cap → zero extra rendering, +4–6 Opus vision calls per import)
   returning a STRICT JSON wall contract:
     walls: [{width_ft, height_eave_ft, gable_rise_ft|null, stepped: [...]}]
     openings_placed: [{schedule_id, wall_index, cx_frac, sill_frac}]
     roofline: gable|hip per face
   Fixture-driven exact-JSON pins + disagreement-state pins (WG- composite
   skip rule already pinned carries over).
S3 · BINDER INTEGRATION (MEDIUM)
   `elevation_sheets.py` learns run-source polymorphism (`ai_measure_runs` |
   `hover_import_runs`), resolves through the ladder, composes the new basis
   strings; collision guard, five-key contract, and read-only stance
   unchanged. Result: Jon-class (Hover-sourced) estimates get live EL-1..4.
Out of scope for this rung: P6 massing families, layer visibility toggles,
compare-toggle overlay (each stays its own backlog item).

## 5. Cost, risks, verdict
  • Spend: +4–6 Claude vision calls per Hover import (bounded by the existing
    page cap); no new rendering cost.
  • Risks: callout mis-association on busy drawings (mitigated by the rung-2
    tripwire against the text table); stepped walls read as single spans
    (mitigated: stepped contract + ⚠ when segment sums disagree with the
    callout total); TTL expiry before S1 lands means re-upload for old runs.
  • September protection: new writes are confined to run docs; the sheet
    route stays read-only; no sealed-key edits.
VERDICT: S1 small · S2 medium · S3 medium — inside the authorized
SMALL–MEDIUM scope. S2 is the risk center; S1 is prerequisite plumbing worth
pairing with the post-Sept upload-security item. No build until Howard calls
timing.
