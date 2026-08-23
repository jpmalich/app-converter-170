# SEND-114 REPORT — THE SCHEDULE ROW PARSER (built, wired, pinned)
2026-08-23 · Ruling executed in order: finding registered → parser built → placement
condition honored → scored against the seal. Quantities only. Probe:
`memory/send114_probe.py` (stored runs, deep copies, READ-ONLY — no estimate written).

# 1. THE FINDING — REGISTERED FIRST (pinned)
In `RULINGS_REGISTER["findings"]`, worded as ruled: EVIDENCE-OR-NULL DISCARDED CORRECT
DATA BECAUSE THE VERIFICATION MECHANISM COULD NOT REACH IT — Boni's window COUNT cells
never OCR, the locator had nothing to verify against, and it quarantined claims whose sum
(16) equals the sealed count. Stated explicitly: THIS IS NOT AN ARGUMENT TO WEAKEN THE
POLICY — it is the argument that a schedule ROW needs its own locator. 20 was fabrication
(an unverified claim honored, mark C swung 9→5 between runs); 4 is a floor (marks-as-1).

# 2. THE PARSER — `schedule_read.py`, wired into `_ocr_verify_marks`
- **ROWS, NOT STRINGS**: deterministic text over the existing OCR store (upright pass).
  Tables anchor on WINDOW/DOOR SCHEDULE headers; column strips from the header row; row
  anchors per mark: its MARK token → its unique PRODUCT-CODE token → its unique
  PRINTED-SIZE row (size used as LOCATING TEXT only, never as a value). Ambiguity refuses.
- **The count cell is read BY POSITION** (COUNT column strip × the located row's band).
  One integer → evidence (`_row_count`, seam-accounted). Empty or ambiguous → the mark
  REFUSES, NAMED (`schedule_count_unread`, loud flag): "count cell empty in OCR at the
  located row". **IT NEVER COLLAPSES TO 1** — and when every window mark refused,
  `window_count` is REFUSED (None), never a 0 posing as a survey.
- **JURISDICTION**: the parser governs only where a COUNT column exists; locator-verified
  cells stand untouched; a schedule with no count column lists one opening per row and
  that convention is not overruled. Mark + size are NOT rebuilt (already reliable).
- **DOORS AND WINDOWS SEPARATE THROUGHOUT** — and the E3 class is closed: exterior door
  rows the model missed are recovered from the printed row itself (mark token + exterior
  signal in the row band; HOLLOW CORE rows never; rows with no exterior evidence go to a
  named unclaimed list, never guessed). The one-glyph drift guard now distinguishes a
  DIGIT sibling (E3 vs E2 — legitimate) from a LETTER drift (F2~E2 — skipped).

# 3. PLACEMENT — WHICH I BUILT, AND THE PER-FACE ANSWER (said before building)
**Built: the NAMED UNPLACED BUCKET (option a).** Schedule-derived instances are never
silently assigned a face — a loud `openings_unplaced` flag carries the instance count and
says why ("a schedule gives size and count and is silent on location by design"). The
pre-existing openings list keeps the model's mark-level claims exactly as they were, with
their weak basis already on the record (`placement_source: "elevation"` — option b for
that legacy surface only; the known-wrong G1/G2 "front" is why no new quantity rides it).
**The per-face question, answered before building shaped the build**: on blueprint jobs
`siding_with_openings_sqft` is None BY RULING (2026-08-08) — openings deduct NOTHING from
the billed siding quantity, house-level or per-face. So IT IS TRUE and said here plainly:
**the parser improves the count and the measurement-surface deduction figure without
moving the billed siding quantity — that stays until the symbols route lands placement
AND a deduction ruling exists.** What the counts DO move on the next rederive: window/
door/garage cap counts, the sill-LF fallback path, opening_count/opening_sqft on the
surface, and every refusal is loud on the rail.

# 4. THE SCORE — against the seal (a check, never a target; nothing tuned toward 16, 4, 526)

**BONI** (sealed: 16 windows · 4 exterior doors incl. G1 16'×8', G2 9'×8' · ≈526 ft² gap):
| figure | before (floor era) | parser now | sealed | residual |
|---|---|---|---|---|
| windows | 4 (marks-as-1) | **REFUSED — None, 4 marks named** ("count cell empty in OCR at the located row" ×A/B/C; "row not locatable" ×D) | 16 | the print's count cells are not ink-text; the parser cannot read what is not there and says so per mark |
| exterior doors | 3 (E3 missed 5 of 6 runs) | **4 — E2, G1, G2 + E3 RECOVERED from its printed row** (sliding glass, one row = one door) | 4 | **0** ✓ |
| G1 size | 16'-0"×8'-0" | unchanged (verified) | 16'×8' | 0 ✓ |
| G2 size | refused (print 9'-2" vs OCR 9'-0") | unchanged — refusal stands | 9'×8' | reported, unresolved |
| deduction ft² | 190.5 (marks-as-1 posing) | **148.0** (E2 20.0 + G1 128.0; G2 and E3 sizes refused → 0) | ≈526 | **−378, every missing ft² NAMED** (16 windows refused, 2 door sizes refused) |

A parser that lands short honestly beats one that lands right by fitting — Boni lands
short and every shortfall names its cell.

**LETRICK** (no sealed openings): windows **8 READ from rows** — A=1 (mark anchor, p5),
B=4 (printed-size anchor, p7), D=3 (printed-size anchor, p7) — with C and F REFUSED,
named (their cells are blank at their located rows). Was: 5 marks-as-1. Window deduction
from readable rows 97.6 ft² (was 41.6 windows-portion). Doors: no COUNT column exists on
Letrick's door schedule → no jurisdiction → E1/E2 row-per-instance stand (2).

# 5. TESTING
35 pins green: 10 new (`test_schedule_row_parser_2026_08_23_send114.py` — register pin;
synthetic-table pins: row-cell evidence, empty-cell refusal never 1, ambiguity refusal,
locator-verified cells stand, no-count-column no-jurisdiction, E3 recovery + interior
exclusion + size parse; stored-OCR pins on both houses pinning the exact behavior above;
structural wiring pin incl. EN+ES flag copy) + locator/mark-locator/SEND-111 regression.
Full suite stamp below. No estimate written; EST-886440 untouched; live estimates change
only on their next rederive.

# 6. QUEUED — NOT AUTHORIZED
The symbols placement read. Its first job, named in the ruling: Boni's two side-entry
garage doors that the app puts on the FRONT — a known-wrong placement with a sealed answer.

## STAMP
(appended after the clean run)
