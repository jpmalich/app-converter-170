# SEND-107 REPORT — REAL-ESTATE WRITE CENSUS · MONEY-WALK REMEDIATION · CHECKLIST-FOLD PLANES
2026-08-22 · QUANTITIES ONLY (Ruling 2). Generated against the clean stamp
`RECORDED: 2026-08-22 21:40 UTC · 3697e35 · CLEAN` (full stamp verbatim in
send105_report.md).

---

## 1. CLASSIFICATION AND BLAST RADIUS (done BEFORE any edit, per mandate)

**(a) stale-defaulted, now correctly refuses: 1 test.**
`test_casile_closeout.py::TestV3MoneyWalk::test_lp_smart_walk_figures` —
asserted sub_mat 23,642.04; read 22,943.35. The 698.69 delta is EXACTLY the
four gutter-accessory rows the retired defaults manufactured (verified to
the cent): Downspout 10 sticks (96 LF = 8 drops × 12 LF, the 9-ft base + 3),
Mitre 20 (out 16 + in 4, corner LF ÷ 9 ft), Pipe Clips 16 (12 LF ÷ 6),
Sealant 11 (42 joints ÷ 4).

**(b) regressions: ZERO — stated explicitly, the list is empty.**
The two other reds in the classification run
(`test_guard_extension_2026_08_11.py::test_profile_annotations_write_lands_in_the_ledger`,
`test_id_migration_never_moves_a_number.py::test_rename_cannot_orphan_a_human_quantity`)
passed standalone AND in the final clean run — named flakes of the known
concurrent-run starvation family, not failures.

**Reach of `_ai_story_count or 1` and the hardcoded 9' (measured):**
- Code sites: 4, all in `routes/hover.py` gutter builders (`lp_package.py`
  carries none). Retired ladder, verbatim: 1. `_ai_avg_wall_height_ft`
  (model hypothesis) 2. `_ai_story_count` × 9 ft 3. bare 9.0 floor — in
  `_downspout_drop_ft`; plus `h = 9.0` in `_gutter_corner_count`. Cascade:
  drop → downspout LF/sticks; corner count → mitres; drop → pipe clips;
  mitres → sealant.
- Tests moved pre-fork (committed cb5551d/f9934de, named there):
  test_gutter_geometry.py, test_gutter_geometry_http.py,
  test_haugh_round_two.py, test_iteration_47_haugh.py,
  test_quote_order_gates.py, Boni anchor manifest. Moved this send: 1
  (the Casile walk, four fields in the pin comment).
- Quantities that moved on the Casile estimate: Downspout 96 LF / 10
  sticks → REFUSED (the 8 DROPS stand — count is height-independent);
  Mitre 20 → REFUSED; Pipe Clips 16 → REFUSED; Sealant 11 tubes → REFUSED.

## 2. P0 — THE SUITE WROTE TO REAL ESTIMATES. FULL CENSUS.

Hardcoded-id estimates touched by tests, and how. A hardcoded id is by
construction a PRE-EXISTING estimate (runtime-created throwaways are never
literals).

**WRITERS (all converted to disposable clones this send — the real
estimates are never written again):**

| test file | real estimate | what it wrote |
|---|---|---|
| test_profile_owns_family.py | **Jon Casile EST-523061** | PUT lines + hover-lp-run rebuild ×3, EVERY RUN (founding-era pins) — the writer that persisted the four Ruling-V refusals at 2026-08-22T20:15:55 |
| test_iteration_48_trade_specs.py | **Jon Casile EST-523061** | PUT panel_size/wrap/fascia/batten ×~10 + lp-package/materialize ×~7, every run (helper-shaped `_put(sess, JON, …)` — invisible to a line scan; the census pin now covers helper calls) |
| test_appendage_dims.py | **Mark Letrick EST-373526**, **doug jones EST-510771** | lp-appendage-dims set/revert ×10 |
| test_elevation_sheets_lbr.py | **Mark Letrick EST-373526** | lp-appendage-dims ×3 + openings-review verbs ×4 |
| test_corner_relocation.py | **Mark Letrick EST-373526** | lp-field-verify relocate/remove/reset ×7 |
| test_default_profile_slice1.py | **Mark Letrick EST-373526** | default-profile ×4 |
| test_flag_checklist.py | **Mark Letrick EST-373526** | default-profile ×3 |
| test_openings_remove.py | **doug jones EST-510771** | openings-review ×3 + teardown $unset |
| test_one_money_surface.py | **Mark Letrick EST-373526** | lp-material-list/freeze (minted a QR share against the real estimate) |
| test_accept_page_3d.py | **Mark Letrick EST-373526** | DIRECT db.estimates.update_one ×6 (accept_token, lp_field_verify) |

**ATTEMPTED-WRITE PINS (registered, unchanged, reasons asserted by the
census pin):** test_fixture_protection.py (DELETE on the protected red-house
fixture asserting the refusal — the guard's own pin);
test_tape_check_sheet_basis.py (two PUTs asserting 400 validation
rejection — nothing persists).

**READ-ONLY touches (lawful, unchanged):** preview/compare/cost-preview/GET
across ~15 files against Casile, Letrick, doug jones, EST-803966,
EST-853809, EST-630295 and the protected fixtures — these are the
live-invariant pins and stay.

**ADJACENT CLASS, REPORTED NOT CHANGED:** test_lp_master_sheet_binding.py
writes a temporary catalog override to the real Casile COMPANY
(`catalogs.overrides`, restored in-test). Same disease, different
collection — flagged for a ruling, not converted (companies were not in
the mandate).

## 3. WHAT THE SUITE WROTE TO EST-523061, AND RECOVERABILITY

- The four Ruling-V refusals (Downspout/Mitre/Pipe Clips/Sealant, qty
  None) — written by the suite's own in-place rebuild at
  2026-08-22T20:15:55.
- For weeks before: spec churn (panel 4x8↔4x10 etc.) + re-materialization
  + lap seed/zero cycles, each run ending in the restored founding state —
  the standing residue was the refreshed lines and updated_at.
- **RECOVERABLE: YES.** The full pre-Ruling-V line set lives in git —
  `memory/backups/20260731_150000_estimates_pre_item_ids.json` at commit
  f9934de and every earlier commit (Downspout qty 10, Mitre 20, Pipe
  Clips 16, Sealant 11, with notes and prices).
- **NOT RESTORED, per mandate.** The estimate stands as the suite left it;
  Howard rules on his own data.

## 4. INCIDENT (this send, mine, disclosed): the derived run doc

A diagnostic probe cloned Casile and rebuilt the clone. The rebuild door
keyed the derived run doc by hover-run + profile ALONE
(`hover-8f6f9b5e6bb3-board_batten`), so the clone's rebuild HIJACKED the
real estimate's standing run doc (upsert re-pointed estimate_id) and the
probe's cleanup then deleted it — the real Casile Material-List surface
404'd ("No completed AI Measure run").

- ROOT CAUSE FIXED in the door: the derived run id is now PER-ESTIMATE
  (`hover-{run12}-{profile}-{est8}`, routes/hover.py) — a duplicate
  rebuilding from the same hover run can never again steal the source's
  run doc. "No estimate influences another" applies to run identity too.
  Existing stamped docs keep their old ids.
- RESTORED: the run doc is a DERIVED, deterministic artifact (not human
  evidence) — re-derived through the same door on a disposable clone from
  the same inputs (hover run 8f6f9b5e, board_batten, wrap 2064, stucco 312
  + brick 234 excluded) and re-keyed to the stamped id. Verified: preview
  on the real estimate 200, all Casile read pins green. The four refused
  ESTIMATE LINES were NOT touched.
- This same key collision is how EVERY clone rebuild before the fix would
  have silently damaged its source — the class died with the fix, and the
  companions/conversions all run against the fixed door.

## 5. THE INVARIANT PIN (not just the fixture fixes)

`tests/test_real_estate_write_census_2026_08_23_send107.py`:
- **Write census**: fails any test that resolves a hardcoded estimate id
  into a mutating operation — HTTP verbs, POSTs off the read-only register
  (preview/compare/cost-preview/duplicate/login), direct db writes keyed by
  a literal id, AND hardcoded ids passed into mutating-named helpers (the
  iteration-48 shape that the first scan missed). Register members carry
  reasons the pin re-asserts against the code.
- **Anti-default pin**, lexical AND functional: `_ai_story_count` may not
  appear as code in hover.py/lp_package.py; no 9.0 assignment/multiplier in
  the gutter builders; an empty `_verified_wall_heights_ft` MUST yield None
  for drop, mitre, clips and sealant; a verified 9.0 still prices (drop
  12.0) — the VALUE is legal, the DEFAULT is not.
- **Money-walk pairing pin**: any `*MoneyWalk*`/`*money_walk*` module
  without a named `*refusal_companion*` test fails the suite. Second walk
  found on the first scan (`test_segment_partial_derivability_2026_08_14`)
  — its existing all-segments-dead test WAS the companion in behavior and
  was renamed to be discoverable (assertions untouched).

## 6. WHAT WOULD HAVE TO BE TRUE FOR THE 423 GUARD TO COVER EVERY REAL ESTIMATE

Today the guard is an enumerated register (`refuse_untouchable` →
UNTOUCHABLE_ESTIMATE_NUMBERS = {EST-886440}) — it protected the one
estimate someone thought to enumerate, and nothing protected EST-523061.
To cover every real estimate rather than one, "real" must be a property of
the data, not a list: (1) every suite-created estimate is already born
marked (test_artifact / TEST_ name / born-during-run — true today), so the
guard can INVERT — derived writes refuse on any estimate NOT so marked
unless they arrive from an interactive authenticated session; (2) the
fixture side holds only if every test write goes through clones (done this
send) and the census pin keeps it that way (added this send). The inverted
door-level guard is a backend behavior change — it decides which writes
count as "Howard in the app" — and is Howard's to rule, not mine to slip in.

## 7. MONEY-WALK REMEDIATION (executed as ruled)

- **Pin move, four fields**, in the walk itself: WHICH PIN (sub_mat +
  tax/base/sell chain) · ASSERTED 23,642.04 (1,654.94 / 25,296.98 /
  36,138.55) · ASSERTS NOW 22,943.35 (1,606.03 / 24,549.38 / 35,070.55) ·
  RULING V retired the 9-ft base. Old quantities preserved ROW BY ROW in
  the pin comment (the only surviving record of what the default produced).
- **PRICED COMPANION** on a disposable clone with an OBVIOUSLY SYNTHETIC
  verified height — **99 ft, documented at the fixture** — asserting the
  exact scaled quantities the builders produce: Downspout 82 sticks
  (8 × 102 LF = 816 LF), Mitre 1 (round(out/99)=1 + round(in/99)=0),
  Pipe Clips 136 (8 × 17), Sealant 6 (23 joints ÷ 4); height-free rows
  pinned unmoved (Gutter 184 LF, elbows 16, end caps 14, hangers 100).
  NOTE, reported not hidden: the mandate's "keep the original assertions
  unchanged" is arithmetically unreachable — every refused quantity SCALES
  with the height, and the only height reproducing the old numbers is
  exactly 9.0 ft, the retired default itself (not obviously synthetic).
  The blast-radius report raised this; the ruling chose 99 ft + scaled
  assertions + the pin move.
- **REFUSAL COMPANION** on a clone (never the real estimate), asserting
  the machine REASON CODE `RULING_V_NO_VERIFIED_HEIGHT` — a new
  `not_derivable_code` field on every refused row (hover.py), so a
  reworded sentence can never break the pin.

## 8. CHECKLIST-HEIGHT FOLD — PLANES DO NOT MATCH. STAYS DROPPED.

- **What plane the closed batten-checklist heights measure between**: the
  checklist asks "tape the WALL HEIGHTS at the house" for the batten
  count — a batten stick runs the SIDED WALL BAND: bottom of the siding
  course (top of foundation / water table) up to the top of the wall at
  the soffit line. That is the plane the +height term prices.
- **What plane the gutter drop needs**: the downspout runs from the
  GUTTER OUTLET AT THE EAVE down to GRADE — the code models
  drop = eave height + 2 ft kick + 1 ft slack.
- **Whether they match: NO.** The batten tape EXCLUDES the exposed
  foundation band between siding start and grade (and any grade fall), so
  a drop priced from it runs SHORT by exactly that band — the soffit
  problem again in a different material: two figures that both answer to
  "wall height" and span different pairs. THE FOLD STAYS DROPPED,
  registered for this reason. (The uncommitted diff from the previous
  session was dropped without effect: zero tests needed it — verified by
  running all 80 affected tests without it.)
- Named for completeness, not relitigated: the SEALED verified bases
  (taped wall heights, DP-1 FIRST FLOOR → TOP OF PLATE chains) carry a
  version of the same plane question against grade→eave; they stand by
  ruling.

## STANDING RULES HELD
No cross-drawing evidence · no estimate influences another (now including
run identity) · no job names in code · model heights hypothesis-only ·
EST-886440 untouched · 423 on every derived write · purity pin holds ·
quantities only, no dollars in this report.
