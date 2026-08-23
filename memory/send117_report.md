# SEND-117 REPORT — ROTATION-NORMALIZE (built) · REFUSAL RAILS (built) · UNREACHABILITY PINNED
2026-08-23 · Quantities only. Probes read-only (`memory/send117_dart_probe.py`); no estimate written, no run rewritten, no model call.

# ITEM 1 — ROTATION-NORMALIZE (the report came first, then the wiring)

## 1.1 The upright-share distribution — EVERY page, all three houses (32 pages)
| house | pages | upright share range | dominant pass |
|---|---|---|---|
| dart | p1–p7, p9–p11 (10) | **6.0 – 24.6%** | rot270 on all 10 |
| dart | p8 (framing, n=30) | **33.3%** — IN THE GAP | rot270 by 1 run |
| Boni | all 11 | **33.9 – 52.3%** | upright on all 11 |
| Letrick | all 10 | **33.9 – 47.4%** | upright on 9; p3 rot90 by 4 runs (noise) |

**THE CUT COMES FROM THE OBSERVED GAP — 24.6 → 33.9**, exactly as Ruling UU's
axis band did: ROTATED at share ≤ 25.0 with a dominant rot pass ≥ 1.5×
upright; UPRIGHT at ≥ 33.5; between the bands → INDETERMINATE. And the
arithmetic closes a hole: share ≤ 25% FORCES the winning rot pass ≥ 1.5×
upright, so no low-share page with signal escapes undetected (pinned).

## 1.2 Which pages normalize, per house
- **dart: 10 of 11 rotate CCW 270°** (validated live per page — detection on
  the real pixels reproduces the stored counts; p5: 9.6% → **74.2%** upright
  after rotation, run distribution flips exactly 72/11/14).
- **dart p8: INDETERMINATE (32.3% live)** — NEVER normalized on a guess;
  stands as rendered, read both ways, railed.
- **Boni: 0 of 11. Letrick: 0 of 10.** CONDITION MET — neither house moves;
  grosses byte-identical before/after (200.0 · 1654.62).

## 1.3 Are 90, 180 and 270 all detectable?
- **90 and 270: detectable AND correctable** — the winning pass names the
  correction; the raster transposes losslessly.
- **180: NOT independently detectable with three passes.** There is no
  rot180 pass; an upside-down sheet reads garbage in all three and lands
  INDETERMINATE via the signal floor or the gap — named, unrotated, railed.
  Correction is not derivable from the store; a fourth OCR pass would be a
  build to rule on.

## 1.4 The gap case
INDETERMINATE = no rotation, the page stands as rendered, a LOUD rail names
it, and the deterministic layers read it both ways (the 3-pass store carries
every orientation's text; the frames are compared, disagreement would print).
Dart p8 is the first real member: both readings find no elevation content —
no disagreement to report.

## 1.5 What lands where
- **INGEST (the fix)**: a new `orientation` worker stage BEFORE the model
  sees a sheet — detects per page at full resolution, rotates the payloads,
  REWRITES the persisted page images upright (annotator, model and OCR store
  all see the same sheet), logs verdicts onto the read (`_page_rotation`).
  Cost: 3 OCR passes per page per read (~15–30 s/page), before Claude.
- **THE CARVER CHANGED NOTHING** — zero edits to `face_bands` or any
  consumer. Condition met.

## 1.6 WHAT DART GIVES AFTER NORMALIZATION (deterministic re-read of the stored raster — NOT the scored run)
| layer | after normalization |
|---|---|
| Faces carved | **still none — and rotation was NOT the whole cause for the carve.** Re-OCR of the upright raster recovers 1 of 4 titles, still glyph-dropped (`EFTSIDE ELEVATION·MODERNFARMHOUSE`); p6 recovers zero. The second, independent cause is the FONT — the per-drawing titles print in a decorative display face tesseract cannot read at this raster quality. The carver stays untouched; its refusal stays correct. |
| Heights | **8 of 8 refused faces SURVIVE** — height labels barely OCR even upright (fragments: `PCF DBL.PLATE`, `FLOORTOCL`; one garbled dim string per elevation page). |
| Schedule jurisdiction | **none, correctly** — dart prints `TAG` (not MARK/OPENING ID) and NO COUNT column; the parser has no jurisdiction and row-per-instance stands. Foreign vocabulary, named at SEND-114. |
| Sizes | **12 of 12 refused sizes SURVIVE** (model rows carry no dims; row cells don't OCR at this quality). |

**What normalization buys dart is the FRESH READ**: the model will see
upright sheets for the first time — its vision reads the decorative titles
and the schedule cells that tesseract cannot. That is the scored run, and it
waits for the seal.

# ITEM 2 — THE REFUSAL RAILS (built, grouped, EN + ES)
Aggregation-born refusals now rail: `faces_refused` · `opening_sizes_refused`
· `deduction_refused` · `page_rotation_normalized` · `page_rotation_indeterminate`.
GROUPED — a fully-refused house produces THREE rails, not twenty.

**DART — was 0 flags, now 5 (3 refusal rails):**
- "4 face(s) REFUSED — back, front, left, right. Their height or width could
  not be established from their own elevation drawings; each contributes
  NOTHING until taped or a placement read lands. Silence here would mean
  nothing is wrong — it is not."
- "12 opening mark(s) refused their size — 1, 2, A, B, C, D, G, GARAGE, H,
  I, K, O. Each is counted but contributes 0 ft² to any deduction…"
- "The openings deduction REFUSED — 15 opening row(s) read, but 4 face(s)
  refused (back, front, left, right)…"

**BONI — was 4 flags, now 7 (3 new):** 4 faces refused · 1 size refused (G2)
· deduction refused (7 rows, 4 faces).
**LETRICK — was 0 flags, now 3 (3 new):** 1 face refused (back) · 3 sizes
refused (A, B, C) · deduction refused (7 rows, back).

# ITEM 3 — THE UNREACHABILITY PIN (built)
`test_marks_as_1_collapse_case_stays_unreachable`: under a COUNT column's
jurisdiction, every governed row ends with qty ≥ 1 OR `_count_unread` — if a
governed row ever reaches the floors with a falsy qty, the pin fails and
names the mark. The reasoning now outlives the callers.

# ITEM 4 — SEQUENCING
**ROTATION HAS LANDED.** Howard can seal dart's truth; then predictions,
written first and unrevised; then the fresh scored read (the model's first
look at the sheets upright).

# STILL QUEUED
Symbols placement (not authorized; first job: Boni's two side-entry garage
doors) · field sheet photos · tape-from-sheet · openings review card.

## STAMP (VERBATIM, from memory/handback_green_log.md) — first run, no reds
- 2026-08-23 16:05 UTC · f95cc5f · CLEAN · [tests] · 2825 passed, 9 skipped, 7 warnings in 521.42s (0:08:41)
- 2026-08-23 16:05 UTC · f95cc5f · INGRESS-SMOKE-CLEAN · 4 passed in 1.58s
- CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none); 8 removal(s) logged (see baseline REMOVAL_LOG)

Suite deltas: 2815 → 2825 (+10 pins, `test_rotation_and_rails_2026_08_23_send117.py`).
No flakes, no pre-stamp reds. EST-886440 untouched. 423 on every derived
write; purity pin holds.
