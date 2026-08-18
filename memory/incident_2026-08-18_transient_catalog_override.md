# INCIDENT 2026-08-18 — live-invariant pins fired on REAL user activity during the SEND-46 handback runs

## Timeline (all 2026-08-18 UTC, reconstructed from the datastore)
- ~01:02 — SEND-46 handback run 1 starts (register + census committed).
- 01:05:14–01:05:19 — THREE `lp.flag_checklist.close` events land on
  EST-803966 ("3 degree 8-3-26 5 pm", Howard's real estimate, Casile
  company) `by hhunt6677@yahoo.com`: facade_scope,
  porch_ceiling_implied, opening_schedule. **Howard is live on the app.**
- ~01:03 — run 1: `test_no_machine_era_lab_residue_in_casile_catalog`
  FAILS — Casile catalog transiently carries
  `overrides["Window Installation::Window DH/Slider - Pocket Install"]
  = {lab: 200.0}`. Minutes later the override is GONE and the catalog
  doc's `updated_at` still reads 2026-07-03 (neither PUT /catalog nor
  reset ever ran — both stamp updated_at).
- 01:15:06 — EST-803966 `updated_at` stamps (a write during run 3).
- ~01:15 — run 3: `test_no_estimate_carries_cross_family_lines` FAILS —
  EST-803966 (kind lp_smart) now carries FIVE windows-tab lines with NO
  `cross_family_flag` exemption:
  Window DH/Slider - Pocket Install (qty 30, lab 170) ·
  Cap window (Windows) (qty 30, lab 20) · Job Measure Standard Fee
  4 days+ · Disposal Fee (Windows) · Second/Third/Clear Story Fee.
  The catalog-residue pin did NOT re-fire in run 3.

## Root cause
The suite's LIVE-INVARIANT pins scan the SHARED live datastore, and the
owner was actively doing a windows takeoff on EST-803966 while the suite
ran. Both fires share the windows fingerprint (Pocket Install). No test
writes to EST-803966 (repo-wide grep: only a GET in
test_waste_rederives_live) and no test or route writes that catalog
override key. The pins did their jobs: they surfaced real datastore
state, not suite bugs.

## What is NOT explained yet
Which surface put `{lab: 200}` into `catalogs.overrides` transiently
without stamping `updated_at` (no in-repo writer $sets single override
keys). Watch for recurrence; playbook below.

## Open ruling needed (Howard)
EST-803966 is kind `lp_smart` and now carries windows-tab lines. Under
the 2026-08-04 single-family ruling this is a QUOTE-blocking
cross-family state unless exempted. Either:
(a) these are Howard's intentional windows lines → they need the
    `cross_family_flag` exemption (his move, like howard-2026-08-04), or
(b) a flow landed them without his intent → the pinned restore bug has
    a live recurrence path.
NOT touched — no write to a real estimate without authorization.

## Recurrence playbook
1. A live-invariant red during a suite run: FIRST check whether the
   owner is active (tracking events by hhunt6677 in the failure window).
2. Check `updated_at` stamps to separate route writes from raw writes.
3. If the catalog override transient recurs, enable Mongo profiling
   level 2 for the suite window (needs authorization).

## Standing note for the residue pin
`test_no_machine_era_lab_residue_in_casile_catalog` asserts NO lab
overrides at all, but the healing rule allows CONTRACTOR-TYPED ones. If
Howard types a labor override into the catalog UI, the pin fails by
design-mismatch. Flagged for ruling; not changed.
