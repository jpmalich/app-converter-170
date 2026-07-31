# PURGE PRE-FLIGHT — ISOLATION PROOF + THE RULED LIST (2026-07-31)
# NOTHING HAS BEEN DELETED. Howard rules the list; then one pass fires.

## RULE 1 — THE AUDIT (a): every cross-estimate read, named
1. **PAIRED-RUN FALLBACK — the ONE real cross-estimate read (by design).**
   `_load_run` (lp_package_routes.py): an LP estimate with NO run of its
   own may read its SIBLING's AI-Measure runs via an EXPLICIT
   `paired_estimate_id` stamp (pair-lp flow — same house, two docs).
   It never scans globally; it fires only through the stamp. CONSEQUENCE:
   deleting one half of a pair can change the other half's LP list.
   HANDLED: the list below never splits a pair — pairs keep or purge
   TOGETHER. Pinned (test_paired_read_requires_explicit_stamp).
2. **Run lookups are estimate-scoped everywhere** — every run query
   filters `estimate_id == the requesting estimate`, including the
   no-TTL fixture_runs archive fallback. No "last import" cache, no
   global latest-run. Pinned.
3. **Create-time state default** — a NEW estimate copies address_state
   from the company's most-recent estimate. COPY-THEN-OWN: deleting the
   source later changes nothing on existing estimates. Not a list read.
4. **Company-shared surfaces** (catalog, tier, standing labor rate,
   branding) — shared across the COMPANY by ruling, not estimate-to-
   estimate; lines snapshot their own mat/lab.
5. **The 261-Haugh-on-3-Degree leak** — fixed and pinned previously
   (test_provenance_hardcode_sweep greps derivation code for hardcoded
   estimate values). Named here as the precedent, class sealed.

## RULE 1 — THE PROOF (b): delete is isolated, demonstrated live
`test_material_list_reads_only_its_own_estimate` (5 pins, all green,
runs inside the guard forever): built two estimates through the real API
(20 SQ house / 31 SQ house), derived both lists, DELETED A →
- B's stored doc: **byte-identical** before/after (string equality on the
  full GET body)
- B's re-derived material list: **identical line-for-line** (canonical
  JSON compare)
- B's quantities provably from B's own squares (31 SQ → 4 wrap rolls,
  never A's 3)
- a fresh LP estimate with no runs + no pair stamp gets NO package —
  refuses to borrow anyone's run
Also: deletion is SOFT (estimates_trash, 30-day TTL) and the 7 protected
fixtures REFUSE deletion at the endpoint regardless of caller.

## RULE 1 — (c): does anything need severing before purge?
The paired fallback is the only dependency and it is not severed — it is
the ruled pair-lp design. The list below is pair-safe, so no purge can
strand a dependent estimate. No other cross-reference exists.

## RULE 2 — THE LIST (25 estimates; Howard rules in one pass)
### KEEP-GROUND-TRUTH (10) — evidence, untouched
| est | name | why |
|---|---|---|
| 786ff854 + 94712a40 | 3 degree rd (pair) | Howard's 155 panels / 465 battens house; carries the HELD RainDrop line |
| 5fc1d3a0 + 6c837ebc | 3 degree rd 7-28-26 8am (pair) | 3 Degree import |
| 34ca0985 + 533e770c | 3 degree vinyl 7-28-26 8am (pair) | 3 Degree import |
| f3e7d728 + 1679183d | 3 degree rd 7-28-26 1pm (pair) | 3 Degree import; f3e7d728 also test-referenced (waste emitter, trade specs, line-write register) |
| d78cd3b4 | 261 Haugh Dr — round two | walked openings, 18'5" corner — PROTECTED |
| 48231310 | 261 haugh — PHOTO cross-validation | PROTECTED, test-referenced |

### KEEP-REFERENCED-BY-A-TEST (7) — load-bearing
| est | name | referenced by |
|---|---|---|
| 8f95c9c2 | Mark Letrick | 20+ test files (chase ratification, elevation sheets, five-key contract…) — PROTECTED |
| db82ec7a | doug jones | elevation-sheet + appendage + provenance tests — PROTECTED |
| 673707d5 + e452a988 | red house (pair) | tape-check basis, collision guard, dormers, seed fixtures — both PROTECTED |
| e2ce35b8 + 40bb13a3 | Jon Casile (pair) | casile closeout, trade specs, profile-owns-family… (40bb13a3 rides as its pair) |
| aac77586 | Letrick Ranch — LP Photo Demo | the demo route's estimate — PROTECTED |

### PURGE (8) — throwaway runs, nothing references them, pairs intact
| est | name | note |
|---|---|---|
| 58bd6ccd | (unnamed) windows draft 7-24 | — |
| ee077937 | (unnamed) lp draft 7-24 | — |
| 37242baf | (unnamed) lp draft 7-26 | — |
| e3c469df | 7-26-26-2pm | wrap-converted this week (receipt + backup exist); only ref is a one-off capture script, not a test |
| 40b8d771 + 59d66e71 | (unnamed) pair 7-27 | 40b8d771 carried the 31.5-SQ $476.44 check row — receipt + backup exist |
| e876e6c0 + 7650bf9a | (unnamed) pair 7-28 | — |

## THE COMPANIES RIDE ALONG (ready, held for the same pass)
Census receipt (endpoint, live): **77 companies · 110 users · 77 catalogs
· 11 resend.dev invitations · 0 estimates inside test companies**.
Keeps: Pro-Quote Estimating Tool, GusGear, Pappans (real) + ZZ Fixture
Test Co (seeded fixture company, ID-fixed, tests re-seed it).

## THE TAGGING GAP — FIXED (no more untagged residue)
- Estimates now tag `test_artifact` at creation when TEST_-named (same
  class as companies, pinned: test_test_named_estimate_is_tagged_at_creation).
- Census + purge now also reach TAGGED estimates (not just name-regex),
  still refusing `fixture_import` and `protected` docs.
- Company tag-on-create + invitation tagging already sealed 2026-07-31.

## AFTER THE PASS (predicted pipeline correction)
25 estimates → **17** (8 purged) · 81 companies → 4 · 114 users → 4 ·
11 invitations → 0. Dashboard pipeline count derives live from the
estimates collection — it corrects itself; receipt will confirm.
