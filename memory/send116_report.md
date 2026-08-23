# SEND-116 REPORT — DEDUCTION ARITHMETIC (reported, then fixed) · FACE-CARVING CAUSE (report only) · ALL-REFUSED SURFACE SWEEP
2026-08-23 · Quantities only. Read-only probes over stored runs; no estimate written.

# ITEM 1 — THE DEDUCTION ARITHMETIC (REPORTED FIRST, THEN FIXED)

## 1.1 Per house: which faces derived, which refused, share of gross
| house (latest run) | front | back | left | right | gross ft² | derived-face share |
|---|---|---|---|---|---|---|
| dart | width 62 read, height REFUSED | width 62, height REFUSED | REFUSED (gable rise 13 read) | REFUSED (gable rise 13 read) | **0.0** | **0%** |
| Boni 8-22 | REFUSED (two conflicting heights 8'-1"/29'-1") | REFUSED (SECOND_FLOOR→TOP_OF_PLATE gap undimensioned) | REFUSED | REFUSED | **200.0 = 100% chimney chase, 0% wall face** | **0%** |
| Letrick 8-21 | 490.3 | **REFUSED** (gap undimensioned) | 272.4 + 183.8 gable | 272.4 + 183.8 gable | 1654.6 | wall faces 1402.6 (84.8%) + chase 252 (15.2%) |
| Boni 8-6 (older, fuller run) | derived | **REFUSED** | derived | derived | 3981.1 | 3/4 faces |

**LETRICK IS NOT SOUND.** Its back face refuses, and its 81.6 ft² of read
openings include marks that may sit on that back. The older Boni run shows the
rule bites beyond Boni/dart: one refused face on an otherwise-full 3981 ft²
gross refuses the deduction there too.

## 1.2 "Deduct only from faces that derived" — computable?
**NO — not without placement.** Every schedule opening rides the UNPLACED
bucket; its face is unknown, so membership in the derived-face subset is
unknowable. Your read was tested and it held: THE DEDUCTION REFUSES WHENEVER
ANY FACE REFUSES, naming both the openings and the faces. A partial gross
minus a whole-house deduction is a different quantity wearing the same label.

## 1.3 EVERY FLOOR AND CLAMP IN THE DEDUCTION PATH (the full inventory)
1. `max(1, int(qty or 1))` — window rows into the bucket (ai_blueprint).
   FLOOR AT 1. It implements the no-count-column row-per-instance convention
   (legitimate); its collapse case (qty=0 without `_count_unread`) is
   currently unreachable. NAMED, LEFT STANDING.
2. The same floor on door rows. NAMED, LEFT STANDING.
3. The same floor a third time in `expanded_windows`. NAMED, LEFT STANDING.
4. `bucket_openings`: `max(0, int(count or 0))` skips non-positive counts;
   `float(width_in or 0)` — a refused size contributes 0 ft² SILENTLY inside
   the bucket (named on the line since SEND-115). NAMED, LEFT STANDING.
5. `max(siding_sqft − opening_sqft, 0.0)` — **THE FLOOR THAT HID DART.
   REMOVED.** No floor remains anywhere in the deduction.
6. The line extract `(siding_with_openings_sqft or siding_sqft)` — a FALSY
   COLLAPSE: a net of 0 fell silently back to gross (dart's 0.0 rode it).
   Now unreachable for a true 0 — refusal fires first; the None-fallback IS
   the designed refusal path. NAMED.
7. `lp_package`: `_net if _net is not None else gross` — None-collapse by
   design (refusal → gross basis). NAMED.

## 1.4 THE FIX (after the report, as ordered)
**AN OPENING MAY ONLY DEDUCT FROM A GROSS THAT INCLUDES THE FACE IT SITS ON —
without placement, that means EVERY face.**
- Any face on `faces_not_derivable` → the deduction REFUSES:
  `siding_with_openings_sqft` stays None (lines price the partial gross,
  itself loudly flagged), and the line reads e.g.:
  *"OPENINGS DEDUCTION REFUSED — 81.6 ft² of openings read, but face(s) back
  refused and an opening may only deduct from a gross that includes its face;
  no placement exists to scope the deduction (openings unplaced); nothing
  deducted. 3 window marks refused (A, B, C) — size refused — contributes 0 ft²"*
- All faces derived but openings ≥ gross → REFUSES as a read inconsistency
  ("reads disagree; nothing deducted") — never a floor.
- All faces derived and net > 0 → deduction applies exactly as SEND-115
  (full precision, refusals named, aggregate-only statement).
- What each house carries now: dart REFUSED (165 ft² read, 4 faces named) ·
  Boni REFUSED (198.5 ft², 4 faces) · Letrick REFUSED (81.6 ft², back named).
  The deduction returns house-by-house as faces derive (tapes) or placement
  lands.

# ITEM 2 — THE FACE-CARVING CAUSE ON DART (REPORT ONLY, NOTHING FIXED)

## The three candidates, each answered from the store and the page images
- **(a) grid layout breaks y-band carving — NO.** Each elevation sheet
  carries TWO drawings stacked VERTICALLY in drawing space (A-3: FRONT above
  LEFT SIDE; A-4: REAR above RIGHT SIDE) with a window schedule beside them —
  exactly the stacking y-band carving expects.
- **(b) compass vocabulary — NO.** The titles are `FRONT ELEVATION - MODERN
  FARMHOUSE`, `LEFT SIDE ELEVATION - MODERN FARMHOUSE`, `REAR …`, `RIGHT
  SIDE …`. The one-face + ELEVATION matcher WOULD match every one of them
  (the "· MODERN FARMHOUSE" suffix is harmless; no compass words anywhere).
- **(c) no per-drawing titles — NO.** All four exist on the sheets.

## THE ACTUAL CAUSE — none of the three: THE SHEETS ARE ROTATED 90° IN THE RASTER
Dart's elevation pages rasterize sideways — every string runs vertically.
- **The upright-share signal** (runs by OCR pass): dart p5 = 11 upright /
  32 rot90 / 72 rot270 (9.6% upright); p6 = 8 / 38 / 87 (6.0%). Contrast
  Letrick p1 = 104/79/92 (37.8% upright), p2 = 108/73/89; Boni p1 =
  147/107/133, p2 = 147/100/133 (~38%).
- **What the OCR recovered of the four titles: ONE**, glyph-dropped —
  `EFTSIDE ELEVATION·MODERNFARMHOUSE` (rot270, x 85.0, y 58.7, 1.1×11.9) —
  the L lost, and the title sits BESIDE its drawing in raster space, not
  below. Page 5 also carries bare `ELEVATION` (rot90, x 46.7, y 39.0) — a
  fragment with no face word. Page 6 recovered ZERO face-title strings.
- **What the carver matched, step by step** (`face_bands`): `ELEVATIONS`
  (sheet title) — excluded by design, correctly; `ELEVATION` bare — no face
  word, skipped; `EFTSIDE…` — "LEFT" not present (glyph drop), skipped.
  Zero titles → zero bands → zero faces → "no evaluated elevation drawing
  for this face" on every face and both height cards. **The refusal itself
  was correct behaviour over what the store contains.**
- **Fix shape (NOT built — a build to be ruled on):** rotation detection
  (the upright-share collapse above is the parameter-light signal) +
  raster normalization before OCR. The carver needs NO change once the
  raster is upright — dart's layout is the layout it already expects.
- Also from the sheets: dart's window schedule prints `TAG` (not
  `OPENING ID`/`MARK`) with NOMINAL/FRAME SIZE columns and NO COUNT column,
  rotated like everything else — the schedule parser had no jurisdiction
  and failed safe.

# ITEM 3 — THE ALL-REFUSED SURFACE SWEEP (dart is the fixture — the first real fully-refused run)
| surface | result with the fully-refused run |
|---|---|
| Elevation sheets | **CRASHED — fixed SEND-115**, pinned (4×200, height "—") |
| Read-back card | renders (latest-for-estimate 200; readback builds) |
| Walk rows (`_build_lines`) | renders — 89 lines, 19 zero-qty, no crash |
| LP package assembly | renders — 24 lines, no crash |
| Field sheet (endpoint) | 200 |
| Gates | 200 (quote modal is client-side over gates + lines; the estimate page rendered in the browser with EL tabs + zones launcher) |
| PDF overlay list | 200 |
| Frozen material list (public) | NOT EXERCISABLE — dart has no frozen list; nothing to render (a fact, not a gap) |

**NAMED GAP (reported, not fixed — needs authorization):** THE RAIL IS SILENT
on aggregation-born refusals. Dart's read-back carries 0 consistency flags
while 8 faces and 12 opening sizes refuse; the refused DEDUCTION likewise has
no rail flag — the takeoff line note is the only surface naming it. The crash
class is registered: the first fully-refusing house broke the display, and
as refusal becomes the honest default the refusal paths need the exercising
the derived ones got — this sweep is that exercise's first pass.

# ITEM 4 — REGISTERED
The face-carving failure is registered as a NAMED FINDING on the third plan
set (rotated raster — a foreign sheet orientation Boni and Letrick never
exercised), not as a defect in the carver.

# QUEUED
Howard's sealed dart truth → predictions first → fresh scored read.
Symbols placement — STILL NOT AUTHORIZED.

## STAMP (VERBATIM, from memory/handback_green_log.md)
- 2026-08-23 14:36 UTC · 1a664f8 · CLEAN · [tests] · 2815 passed, 9 skipped, 7 warnings in 476.91s (0:07:56)
- 2026-08-23 14:36 UTC · 1a664f8 · INGRESS-SMOKE-CLEAN · 4 passed in 1.80s
- CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none); 8 removal(s) logged (see baseline REMOVAL_LOG)

**One pre-stamp red, named, not a flake:** the consumer-key census caught the
aggregator reading the deduction record's bare child keys via `.get`
(`deduction_refused`, `deducted_sqft`) — fixed in code (the net lands from
the local at build time; no dict reads), the census pin held untouched.
Suite deltas: 2810 → 2815 (+5 pins, `test_deduction_face_rule_2026_08_23_send116.py`).
EST-886440 untouched (sealed-key path carries no deduction record). 423 on
every derived write; purity pin holds.
