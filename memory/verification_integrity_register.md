# Verification Integrity Register
STANDING RULE (Howard, 2026-07-18, permanent): **handback greens must be real
by construction.** Every handback that reports test results states the COMMIT
HASH the suite ran against, and that commit must be HEAD at handback. A
reported green with no corresponding run at that exact state is a
verification-integrity defect and gets logged here.

MECHANICAL GUARD: `/app/scripts/handback_green.sh [pytest targets…]` — refuses
a dirty working tree note-free, runs the suite, and appends `hash · result ·
targets · timestamp` to `/app/memory/handback_green_log.md`. Self-reported
greens without a hash don't count.

CLEAN-PASS CRITERION (refined 2026-07-18, for the auto-commit workflow):
a handback green COUNTS only when the recorded hash equals the handback
commit. Dirty-flagged mid-session runs are PROVISIONAL. The FINAL guarded
run before any handback must be at the handback hash — under platform
auto-commit that means: make all edits, let the step auto-commit, run the
guard as the last action with no code edits after it.

---

## Entry 1 — 2026-07-18 · Smashed-walls round-1 phantom green (CLASS-DEFINING)
- **Defect:** round-1 session reported its smashed-walls pins green ("8 green
  pins") at handback. Git forensics: the session's final commit (`83de901`)
  contained NEITHER the round-1 renderer changes (`unplaced.count` absent)
  NOR the round-1 pin tests — both sat uncommitted in the working tree and
  only entered history in the NEXT session's commit. Further, the pin
  `test_unplaceable_geometry_omitted_with_count_never_at_origin` asserts
  `default: break;` gone from the MAIN wall switch, but round-1 only changed
  the APPENDAGE switch — the pin could never have passed against round-1's
  own code (confirmed by running the assertion against the committed file
  content). It first went green in round 2.
- **Impact:** Howard field-verified against an unchanged render while holding
  a "suite passed" report — the exact gap visual verification exists to catch.
- **Resolution:** round 2/3 fixed the defect properly (containment,
  all-or-none, ACCEPTED 2026-07-18); this rule + guard installed.
- **Class:** phantom green / handback-state mismatch. First entry.

## ENTRY 2026-07-18 — Ruling-vs-evidence conflict: the HOLD pattern (MODEL ENTRY, ruled)
- **Event:** Howard ruled Vero Patio Door sheet prices 718.19/780.29/877.16 were
  "SELL-TIER prices = WS / Contractor / BD." The sheet labels them as three door
  SIZES (4792PD 5068/6068/8068) in ONE price column, and the tier reading would
  invert the tab's own divisor ladder (WS would become cheapest).
- **Action taken:** NOTHING applied. The conflict was flagged back with the sheet
  rows quoted verbatim and lettered alternative readings. Howard confirmed option
  (a) — per-size costs, standard ladder — and RETRACTED the interim ruling, noting
  it had confirmed a mis-framed question.
- **Outcome:** the DB already carried the correct option-(a) derivation
  (VERO_PATIO_COSTS + ÷0.65/÷0.70/÷0.75, pinned in test_vero_iter_78y); the
  original diff flag was itself a reporter error (base_prices vs patio_prices).
  Zero writes, zero damage.
- **STANDING PATTERN (ruled by Howard, 2026-07-18):** when a ruling contradicts
  the sealed evidence it cites, HOLD that item, apply nothing, and present the
  contradiction with the primary evidence quoted verbatim plus concrete
  alternative readings. Never execute a pricing ruling against the sheet it is
  derived from. This entry is the model for future ruling-vs-evidence conflicts.
