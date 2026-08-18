# INCIDENT 2026-08-18 — transient catalog override observed mid-suite (4th transient-state instance)

## What was observed
During the SEND-46 handback_green run (commit with SEND-46 register),
`tests/test_lp_master_sheet_binding.py::test_no_machine_era_lab_residue_in_casile_catalog`
FAILED: the Casile catalog (`company_id ecfe9396…`) carried
`overrides["Window Installation::Window DH/Slider - Pocket Install"] = {"lab": 200.0}`.
Suite result: 1 failed, 2548 passed.

Within ~3 minutes of the run ending, direct pymongo queries found the
override GONE: one catalog doc, `overrides: {}`.

## What was ruled out (forensics)
- **No route wrote it**: the doc's `updated_at` is `2026-07-03T13:10:05Z`
  — both writers (`PUT /catalog`, `POST /catalog/reset`) stamp
  `updated_at` on every write. The UI (Catalog.jsx) uses PUT. So neither
  the UI nor any HTTP path touched this doc since July 3.
- **No test wrote it**: repo-wide grep — the only direct
  `catalogs.overrides` writer in tests is the neighbor test in the same
  file, and it writes/removes ONLY `Seamless Gutter::Gutter 6"`. No test
  or backend file contains a lab-200 write; "Pocket Install" appears
  nowhere with 200 (seed meta says 170).
- **Not a duplicate doc**: exactly one catalogs doc for the company.
- **Not machine seeding**: `create_company` inserts empty overrides;
  startup migration only unsets legacy `sections`.
- mongod logs empty of catalogs ops; profiling was off (level 0).

## What this means
The mutation was a direct `$set`/`$unset`-style write by an actor outside
the repo's code paths (both operations skip `updated_at`, consistent with
raw driver writes), or a datastore anomaly. This is the FOURTH
transient-datastore incident (after the vanished run 2026-07-17, TTL
expiry 2026-07-18, TTL third instance 2026-08-11).

## Standing note for the pin itself
The pin asserts `labbed == {}` — it polices machine residue but will also
fail on a CONTRACTOR-TYPED override (which the healing rule explicitly
allows: "labor overrides exist only when the contractor typed them").
If Howard types a labor override into the Casile catalog UI, this pin
fails by design-mismatch. NOT changed without a ruling — flagged only.

## Recurrence playbook
1. Check `updated_at` on the doc first — stamped = route wrote it,
   unstamped = raw write.
2. `git status` + repo grep for the exact override key.
3. If it recurs, enable Mongo profiling level 2 for the suite window to
   catch the writer's connection metadata (needs authorization — it is a
   DB-side state change).
