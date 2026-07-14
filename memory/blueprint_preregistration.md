# PRE-REGISTRATION — Blueprint-path conformance vs sealed Letrick key
**Filed BEFORE the fix ships (2026-07-14). Two-layer protocol per Phase 3.
No reconciling either direction after results; deltas get scored, not
adjusted. Sealed key: `letrick_hand_takeoff_key.py` (EST-191890, ±3%/line;
composition absences are part of the key).**

## Protocol
- LAYER A (extraction): fresh blueprint run (cached-pages rerun of
  Howard's shakedown upload run `e4afda3a64a54439b02b5c609dda0b69`) —
  extracted geometry vs key geometry.
- LAYER B (conventions): the post-cut engine (`assemble_lp_package` via
  the blueprint route) invoked read-only on THE KEY'S geometry.
- Provenance recorded: run_id, measurement payload hash, derived package
  hash, prompt hash (extraction fixes change `_blueprint_prompt_hash` —
  the new hash is part of the record).

## Pre-registered LAYER B expectations (engine on key geometry)
The engine's conventions are UNCHANGED by this work — the two known
Phase 3 Layer B divergences remain OPEN (not ruled here) and are
pre-registered as expected divergences, not surprises:

| Line | Key | Expected engine output on key geometry | Expected verdict |
|---|---|---|---|
| 38 Series Lap | 255 | 252 (ceil(2098.5÷9.17×1.10)) | PASS (−1.2%, rounding-order residual) |
| 540 OSC | 8 | 9 (per-location whole-stick incl. 2 above-roofline edges; pooled tails) | **KNOWN Layer-B divergence — expect FAIL, unchanged from Phase 3** |
| 440 4" ISC | 2 | 2 | PASS |
| 540 Trim | 12 | 12 | PASS |
| 440 8" fascia+rake | 12 | 13 (×1.10 cushion) | **KNOWN Layer-B divergence — expect FAIL, unchanged from Phase 3** |
| Soffit | 108 LF eaves-only | eaves-only basis honored | PASS |
| Starter | 165 LF → 4 boards | 4 boards (48 LF/board rip yield) | PASS |
| **Composition** | NO J-channel / finish trim / coil; no fractional qty; whole-stick everywhere | zero cross-domain lines, integer qtys | **MUST PASS — this is the defect under repair** |

## Pre-registered LAYER A expectations (post-extraction-fix, correct read)
| Input | Key | Pre-fix shakedown (e4afda3a) | Post-fix expectation |
|---|---|---|---|
| Starter basis | 165 (perimeter 168 − 3' entry) | 108 (eaves) | perimeter − 3'/entry rule applied by aggregator: **165 ± schedule-read variance** |
| Gable rise | 8.75' (7/12 on 30' end) | 8.5 (drawing-scaled) | pitch-computed **8.75** when pitch printed; drawing value retained as provenance |
| Chase faces in siding | +145.5 ft² | absent | present, attributed |
| Chimney OSC edges | 8 edges (~55 LF pooled basis) | 6 edges / 57 LF | above-roofline edges present in OSC LF |
| Door classes | 1 entry + 1 patio slider | 2 entry | **pre-registered as KNOWN CLASS RESIDUAL** (Phase 3 §4 analogue) — logged, not promised fixed by schema alone |
| Windows | 10 | 10 | 10 |

Extraction is stochastic (Phase 3 provenance note: −7.9% siding drift on
identical photos) — Layer A scores the fresh run as-is; no cherry-picking
across reruns. ONE post-fix run, declared in advance, is the scored run.

## Waste scope pre-registration
- Area lines: 10% inside the formula (lap), nothing stacked on top.
- Stick lines: whole-stick rounding is the SOLE allowance.
- `est.waste_pct` (20 default) must not touch ANY LP line on any path.
- Double-application (lap ×1.10 × 1.20) must be non-reproducible post-fix.

## What would falsify the fix
- Any J-channel / finish trim / coil line in a blueprint-derived LP
  package; any fractional PCS; any rake-driven soffit row; waste_pct
  echo in LP quantities; a Layer B result differing from THIS table in
  either direction without a ruling.

## ADDENDUM — 3D-layer pre-registration (findings 6/7/8)
| Layer | Key | Post-fix expectation |
|---|---|---|
| Roof pitch | 7/12 printed | `roof_pitch: "7/12"` extracted; 3D expresses **7/12** with GREEN "Printed" badge. If extraction misses the callout: derived value shows AMBER "Derived — verify" — a wrong value may occur (stochastic) but a confident badge on a derived value may NOT. |
| Openings placement | front: 4 windows + entry (per elevation sheets) | openings land on their elevation-sheet walls; any unresolved marks default to front WITH the amber placement note (count flagged). Render-only layer — global counts/sizes unaffected either way. |
| Chase render | chimney chase, rear, extends above roof | rendered from structured `appendages` payload with printed dims, or honestly absent + no malformed box. Amber when position unresolved. |
