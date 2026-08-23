# SEND-113 REPORT — OPENINGS: SCHEDULE ROUTE × SYMBOLS ROUTE
2026-08-23 · REPORT ONLY — neither route built; no boundary, count, or deduction logic
changed. Structured per the reframe: THE TWO ROUTES SUPPLY DIFFERENT HALVES — the schedule
gives marks/sizes/counts and cannot give locations; the symbols route gives placement.
Probe: `memory/send113_probe.py` (OCR-store row recovery + placement-text scan, read-only).
Quantities only. Doors and windows separated throughout.

---

# 1. IS A SCHEDULE PRESENT? — YES, BOTH HOUSES, AND IT IS RECOVERABLE AS ROWS (partially)

## BONI (11-page set; sheet index itself recovered from p1's DRAWING SCHEDULE)
- **p6 (FIRST FLOOR PLAN)**: a DOOR SCHEDULE and a WINDOW SCHEDULE, side by side.
- **p7 (SECOND FLOOR PLAN)**: a second DOOR SCHEDULE + WINDOW SCHEDULE (second-floor rows).
- **WINDOW SCHEDULE columns, recovered verbatim from OCR**: `OPENING ID | PRODUCT CODE |
  SIZE | COUNT | LIBRARY NAME`. Rows recover AS ROWS by y-banding: `SH 3-0_5-0 ·
  2'-11½"×4'-11½"`, `SH 3-0_4-0 · 2'-11½"×3'-11½"`, `SH 3-0_5-6 · 2'-11½"×5'-5½"` (p6) —
  BUT the **COUNT cells are NOT in the OCR text on any window row** (tiny digits/graphic
  cells). Marks and sizes recover; window counts do not.
- **DOOR SCHEDULE rows recovered**: `E2 · 3'-0" · Panel Standard (FRONT DOOR)`, `E3 ·
  SLIDING DOOR Right Hand Sliding Glass Door`, `G1 · 16'-0"×8'-0" · GARAGE SONOMA`, `G2 ·
  9'-0"×8'-0" · GARAGE SONOMA` — plus INTERIOR rows mixed into the same table (`2-6 HOLLOW
  CORE`, `Garage to House Door`): exterior/interior separation is a real filtering step,
  not a given. **The schedule prints all FOUR exterior doors, E3 included.**
- Caveats: the OCR store triples text (upright + two rotations), rows band together when
  cells sit close (G1/G2 merged into one band), and hinge-count vs COUNT columns collide.
  Row recovery is real but approximate — MARK+SIZE reliable, COUNT unreliable-to-absent.

## LETRICK (10-page set)
- **p5 (FOUNDATION plan)**: WINDOW SCHEDULE with a fully recovered row INCLUDING ITS
  COUNT: `A · BOWMAN KEMP 4040 · 4'-0"×4'-0" · 1 · BASEMENT EGRESS`.
- **p7 (FIRST FLOOR PLAN)**: DOOR SCHEDULE (rows 2–12 interior hollow-core + `E1 · 3'-0" ·
  Panel-Country (Glass)` + `E2 · 3'-0" · Full Light`) and WINDOW SCHEDULE (`B/C · SH 3-0_5-0
  / SH 2-8_4-0` with sizes; `D · SH 3-0_5-6 (2) · 5'-11½"×5'-5½" · COUNT 3`; `SH 2-4_4-0`).
  Some COUNT digits DO appear in Letrick's OCR (the `1`, the `3`) — legibility varies by
  print, not by principle.

# 2. WHERE COUNTS AND SIZES COME FROM TODAY — every source, graphics-vs-print named

The ONLY openings source on a blueprint job is the LLM read (`routes/ai_blueprint.py`),
which is asked to read the SCHEDULE and returns `windows[]`/`doors[]` (mark, product code,
printed size, per-sheet COUNT cells, claimed elevation). Two verifiers then run against the
OCR store: the size verifier (unverified `printed_size` → `printed_size_not_located`, and
width/height are NULLED) and the COUNT-CELL LOCATOR (2026-08-11: unverified count cells →
`count_by_page_not_located`, qty NULLED). Assembly (`ai_blueprint.py` ~L4141): a mark with
qty null contributes **1** (`max(1, int(qty or 1))`) — so counts collapse to MARKS when
cells don't verify. `openings[]` (per-opening walls) comes from the LLM's ELEVATION claims
(`placement_source: "elevation"`) — graphics-derived. Downstream consumers: opening_sqft/
counts on the measurement surface, Cap window/door/garage lines (Boni caps read 4/1/1/2 —
marks, not instances), finish-trim sill LF (Boni's 80 LF = `window_bottom_width_total_lf`,
an LLM elevation measurement — graphics-derived), house-level net siding.

## WHICH SOURCE PRODUCED THE 20, AND WHICH PRODUCED THE 4 — THE SAME SOURCE, TWO ERAS
- **THE 20** — run `6a7b7050` (2026-08-11 18:56, EST-886440): the LLM's claimed COUNT
  cells were HONORED: A×9 (p6:2 + p7:7), B×1, **C×9**, D×1 = 20. Sealed truth is 16; the
  C claim was 9 where the latest run claims 5 — **the count column claim itself swung**.
- **THE 4** — every post-locator run (5 runs, 08-14→08-16, EST-713272): the SAME claimed
  cells could not be located in the OCR (Boni's window COUNT cells never OCR — §1), all
  were quarantined, and every mark fell back to the marks-as-1 assembly → window_count 4.
- So: **both figures came from one source — the LLM's schedule COUNT-cell read.** Honored
  it swings (20, with C mis-read 9 vs 5); quarantined it collapses to marks (4). That
  source's unverifiability on this print is the whole instability. Notably, the LATEST
  run's quarantined claims sum to **16 — exactly the sealed count** — evidence the schedule
  route carries the right answer and the verification gap, not the read, is what discards it.

# 3. WHAT EACH ROUTE GIVES INDEPENDENTLY — and the score

## Route A — THE SCHEDULE (marks, sizes, counts; NO locations — confirmed: no elevation
column exists in either house's schedule)

**BONI** (sealed: 16 windows · 4 exterior doors incl. G1 16'×8', G2 9'×8' · gross-to-net
gap ≈ 526 ft² — A CHECK, NEVER A TARGET; nothing below was tuned):
| figure | schedule route (latest claims) | pipeline carries today | sealed | verdict |
|---|---|---|---|---|
| windows | **16** (A×9, B×1, C×5, D×1) | 4 (marks) | 16 | claims EXACT; carried −12 |
| exterior doors | 3 (E2, G1, G2) — E3 missed; the 08-15 run read 4 | 3 | 4 | schedule PRINTS 4 (E3 sliding recovered in OCR); read misses it in 5 of 6 runs |
| G1 | 16'-0"×8'-0" | ✓ | 16'×8' | exact |
| G2 | 9'-2"×8'-0" printed (9'-0"×8'-0" in the OCR row) | size nulled (unverified) | 9'×8' | two-inch print/seal disagreement REPORTED, not resolved |
| deduction ft² | **453.3** = windows 232.0 (A 132.0 + B 11.7 + C 80.7 + D 7.5) + doors 221.3 (E2 20.0 + G1 128.0 + G2 73.3); **+48.0 if E3 (6'×8', the 08-15 run's 4th-door area) = 501.3** | **190.5** (one instance per mark; G2+D at 0 — sizes nulled) | ≈526 gap | schedule route lands −4.7% of the gap; today's carried figure is −64% |

**LETRICK** (no sealed openings figures): schedule route: windows 5 marks / **10 claimed
instances** (A×1, B×4, C×1, D×3, F×1) with printed sizes on all 5 marks (4 of 5 unverified
→ nulled today); doors E1×1, E2×1 (both 3'-0"). Instance-honored deduction ≈ **231.8 ft²**
(A 16.0 + B 58.7 + C 10.4 + D 97.6 + F 9.1 + doors 40.0) vs pipeline **81.6** today.

## Route B — THE SYMBOLS (placement; not built — what exists is a CLAIM, not a read)
- Today's ONLY placement is the LLM's `elevation` field per MARK: Boni A/B/C "front", D
  "left"; doors E2/G1/G2 "front". A mark-level wall claim cannot place 16 instances (A's 9
  windows do not all sit on one face) — **per-face deduction is impossible from today's
  data**, exactly as the reframe predicted.
- The print gives the symbols route real anchors: elevation canvases with recovered labels
  and positions — Boni p1 FRONT (9.5, 45.4) / REAR (34.3, 91.6), p2 LEFT (15.1, 47.0) /
  RIGHT (45.0, 87.8); Letrick the same split (p1 front/rear, p2 left/right). Window/door
  symbols on those canvases are DRAWN, not texted (no G1/G2/16'-0" text on any elevation
  page) — placement must come from geometry, the thing the linework layer already parses.

## THE TWO SIDE-ENTRY GARAGE DOORS — what each route says
- **Schedule**: G1 16'-0"×8'-0" and G2 9'-0/2"×8'-0" EXIST, one each — and it says NOTHING
  about where. Correct behavior for a schedule; the known-wrong "front" did not come from it.
- **Symbols/claims**: the LLM claims `elevation: "front"` for both, `exterior_evidence:
  "elevation"` — the KNOWN-WRONG placement, confirmed against the prints long ago,
  reproduced in every stored run. The floor plan (p6) carries the counter-evidence in text:
  `3 CAR GARAGE` at (66.2, 44.0) with the garage-door notes on the plan wall — a plan-side
  anchor a real symbols read could use; the front elevation canvas carries no garage-door
  text at all. **Standing evidence the placement problem is real: today's placement source
  is a graphics-derived claim, and it is wrong on the one case with ground truth.**

## WHERE THE ROUTES DISAGREE (reported, not resolved — standing rule)
1. Boni window count: schedule claims 16; today's carried figure 4; the 08-11 claim 20.
2. Boni door count: schedule prints 4 exterior; the read returns 3 in 5 of 6 runs.
3. G2 size: 9'-2" (run claim) vs 9'-0" (OCR row) vs 9' (sealed).
4. Placement: schedule silent (by design) vs LLM claim "front" (known-wrong for G1/G2).

# 4. WHAT A BUILD WOULD COST (stated, not assumed — no build authorized)
- **Schedule-for-size-and-count**: the schedule rows recover from the EXISTING OCR store
  (§1) — a deterministic row-parser (y-banding + column split, doors/windows separated,
  interior rows filtered) is ~150–250 lines plus pins, zero new API cost, stable across
  runs by construction. Its hard edge: window COUNT cells that never OCR (Boni) — those
  rows would carry counts only where a cell is legible, refusing otherwise (evidence-or-null).
- **Symbols-for-placement**: a per-elevation opening-rectangle read over the existing
  vector layer, bounded by the four recovered elevation canvases. Larger (~300+ lines),
  and the SEND-111 noise floor applies to any area it measures (~4%); its value is
  placement and the count cross-check, not sizes.
- **The disagreement signal** (schedule count ≠ symbols count per face) costs nothing
  extra once both halves exist — it is the acceptance test.

# NOTHING BUILT
Both routes remain unbuilt; every figure above is read from stored runs, the OCR store,
and the prints' own text. (Separately, the parallel exposed-field sweep authorized in
SEND-113's preamble landed: `viz` — the last derivation-born field riding neither the
merge nor the save whitelist — now rides both, and a structural pin
(`test_exposed_field_carry_2026_08_23_send113.py`) scans `useEstimate.js` so ANY
exposed-class field missing from either half turns a pin red instead of stripping
silently. The refusal trio stays law-owned, not carry-dependent.)

## STAMP
(appended after the clean run)
