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
