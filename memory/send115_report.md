# SEND-115 REPORT — DART BUG FIXED · RULING 1 SHIPPED (openings deduct, deduction shown) · THIRD PLAN SET READY, AWAITING THE SEAL
2026-08-23 · Order followed as given: dart first, deduction second, third-plan-set
run blocked on the seal, symbols untouched. Quantities only. Probe:
`memory/send115_probe.py` (stored runs, deep copies, READ-ONLY — no estimate written).

# 1. THE DART LIVE BUG — root cause found, fixed, verified end-to-end
- **THE 404s WERE A RESTART WINDOW, NOT THE BUG**: the console list included
  `/api/version` — a route that always exists — 404ing alongside everything
  else. A whole-tree /api 404 is the ingress/restart signature; every path
  serves 200 now (uploads, version, latest-for-estimate). The malformed
  `ai-blue-8a01-…` shapes match console middle-ellipsis of the long run URLs.
- **THE LASTING BREAKAGE WAS A 500 WEARING A REFUSAL'S CLOTHES**: dart's read
  refused every wall height (evidence-or-null working on a foreign drafter —
  no FIRST FLOOR→plate band the height build recognizes). The elevation-sheet
  renderer then crashed on the refusal: `fmt_ftin(None)` TypeError → 500 on
  all four faces → the panel's catch() rendered "NO COMPLETED AI MEASUREMENT
  RUN YET" over a run that was DONE with 11 persisted page images.
- **FIX (one call site)**: `height_label` now mirrors `width_label`'s None
  guard — a refused height PRINTS "—", never crashes, never fabricates.
  Pinned live (4 faces × 200 on the real dart estimate) + structurally.
- **VERIFIED IN THE BROWSER**: EL-1..EL-4 tabs render; front shows width
  62'-0", height —, wall area "not derivable (step untaped)", 23 openings
  (21 windows · 1 entry · 1 garage); page images load; Material Zones
  launcher has its pages. Page persistence was NEVER broken — 11 images on
  disk and served.

# 2. RULING 1 — OPENINGS DEDUCT, AND THE TAKEOFF SHOWS IT
Shipped exactly as ruled: FULL AREA, NO THRESHOLD; the line shows what was
deducted AND what refused; aggregate only until placement exists.
- `siding_with_openings_sqft` now carries the NET (gross − openings) on
  blueprint jobs that read openings — full precision (Ruling 7 holds; the
  guard caught my intake rounding and it was fixed in code). Nothing read →
  the field stays None (the 2026-08-08 no-alias pin survives by scope).
- **THE LINE** (Charter Oak / Ascend / LP lap all carry it): e.g.
  "OPENINGS DEDUCTED 148 ft² — full area, no threshold (gross 2000 −
  openings = 1852 ft²). 4 window marks refused (A, B, C, D) — count cell
  unreadable. DEDUCTION INCOMPLETE. Aggregate only — not attributed per
  face (openings unplaced)". Both refusal classes print: count-unread AND
  size-refused (counted, 0 ft²).
- LP lap PRICES the same net basis the note names; jobs without a deduction
  record (all HOVER) are byte-identical to before, pinned.
- The `openings_unplaced` rail flag now states it in both languages: "The
  opening deduction lands at AGGREGATE — not attributed per face."
- One stale pin updated, NAMED (test_siding_basis_note_2026_08_08): asserted
  "openings NOT deducted" (the 08-08 convention) → asserts "no openings read
  to deduct"; the ruling that made the old value wrong is THIS one.

## WHAT THE TOTALS BECOME (latest stored run per house, bare aggregation —
## live estimates move on their NEXT REDERIVE, where tapes carry the gross)
| house | gross ft² | deducted ft² | net carried | refusals on the line |
|---|---|---|---|---|
| Boni (8-22 2pm) | 200.0 (heights refused — untaped bare run) | 198.5 | **1.5** | G2 size refused |
| Letrick (8-21 9pm) | 1654.6 | 81.6 | **1573.0** | A, B, C sizes refused |
| dart (8-23 7am) | 0.0 (all 8 heights refused) | 165.0 claimed, net floor 0 | **0.0** | 9 window + 3 door sizes refused (marks 1, 2, GARAGE) |
Boni's stored-run gross is height-refusal-limited; on the live estimate the
taped heights carry the gross and the same 198.5 deducts from it. The
deduction never goes below 0 and every missing ft² stays named.

# 3. RULING 2 — THE THIRD PLAN SET (dart): READY, NOT RUN
- Different drafter: CONFIRMED by the read itself — numeric door marks
  ("1", "2", "GARAGE"), no FIRST FLOOR→plate labels the height build
  recognizes, stepped walls. Every house-leaning piece FAILED SAFE: no
  fabricated count, no confident placement — heights refused (8/8), sizes
  refused where unprinted, wall area refused at the step. That is the
  generality condition WORKING, per the ruling.
- **BLOCKED ON THE SEAL**: Howard seals ground truth (face widths, depths,
  heights, opening counts, projections) BEFORE the scored run; predictions
  written first, unrevised. The 7am read predates any seal — the scored run
  will be a FRESH read after the seal lands.

# 4. QUEUED — NOT AUTHORIZED
Symbols placement read (first job: Boni's two side-entry garage doors).
Field sheet photos / tape-from-sheet.

## STAMP (VERBATIM, from memory/handback_green_log.md)
- 2026-08-23 12:41 UTC · 8618c26 · CLEAN · [tests] · 2810 passed, 9 skipped, 7 warnings in 443.92s (0:07:23)
- 2026-08-23 12:41 UTC · 8618c26 · INGRESS-SMOKE-CLEAN · 4 passed in 10.98s
- CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none); 8 removal(s) logged (see baseline REMOVAL_LOG)

**RUNS BEFORE THE STAMP — every red named:**
1. First run `1 failed, 2809 passed` — NOT a flake: the no-second-copy pin
   (Ruling 7) caught my deduction record rounding `siding_sqft` at intake
   while its net feeds an engine key. FIXED IN CODE (full precision in the
   record, rounding only at the note's display); the pin held.
2. Second run `2 failed, 2808 passed` — two LIVE-WINDOW TRANSIENTS, both
   named, both pass standalone and in the stamped rerun:
   (a) demo-reset isolation — Haugh-address disposable `2e78180d` hard-
   deleted asynchronously mid-run (KNOWN family, 3rd recurrence);
   (b) cross-family live pin — a disposable lp_smart estimate carrying a
   `D4 Clapboard` row, created+deleted by a concurrent run (gone from the
   DB before the rerun). Neither touched a real estimate.
Suite deltas: 2797 → 2810 (+13 net new pins: 11 deduction + 4 dart sheet,
minus 2 parametrize consolidation). EST-886440 untouched (its sealed-key
materialize path sets both siding fields directly and carries no deduction
record). 423 on every derived write; purity pin holds.
