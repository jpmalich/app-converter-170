# Incident 2026-07-18 — TTL expiry, SECOND instance (Haugh hover pin substrate reaped)

## What happened
`tests/test_haugh_round_two.py` + `test_iteration_47_haugh.py` pinned live derivations to
hover run `4ffc35f4ded14b46bc6eb267469efbfd` (261 Haugh Hover PDF). `hover_import_runs`
carries a **24h Mongo TTL** and was **entirely outside the archival bounds** of
`run_archive.py` (which covered only `ai_measure_runs` + explicit-run_id blueprint lookups).
The run reaped between sessions → `hover-lp-run` returned 404 → pins skipped/failed.
Second instance of the data-aging-out class (first: blueprint fixtures reaped 2026-07-16,
restored with reason `pytest-fixture restore after 24h ai_blueprint_runs TTL loss`).

## Full TTL substrate inventory (LIVE `index_information()` sweep 2026-07-18 — not from memory)
| Collection | TTL | Key | Docs at sweep | Reapable-reference finding |
|---|---|---|---|---|
| `ai_measure_runs` | 30 d | `created_at` | 52 | Covered since 07-14 triggers. NEW gap found: estimate `lp_source_run_id` stamps were never swept — the Haugh estimate's materialized run `hover-4ffc35f4ded1-lap` was quietly reapable. Now archived (`backfill:lp-stamp`). |
| `ai_blueprint_runs` | 24 h | `created_at` | 0 | Explicit-run_id archival existed (THE CUT 07-14); read fallbacks in place. No dangling refs found. |
| `hover_import_runs` | 24 h | `created_at` | 0 → 1 | **ROOT CAUSE — zero archival coverage.** Haugh source run reaped, unrecoverable. Re-ingested (below). |
| `hover_page_cache` | 1 h | `created_at` | 0 | Deep-Verify PNG cache, referenced by `deep_verify_cache_key` inside hover results. RULED CACHE-EXEMPT: transient by design; Deep Verify re-runs on re-upload. An archived hover run's cache key may dangle — acceptable, documented. |
| `estimates_trash` | 30 d | `deleted_at` | 848 | Trash docs ARE the artifact; the 30-day restore window is product intent. Exempt. (Pre-existing product gap: a restored estimate may outlive its runs — ttl_audit finding 3, unchanged.) |

## Fixes shipped (all in this commit)
1. `run_archive.py` — `_RUN_SUBSTRATE_COLLS = (ai_measure_runs, ai_blueprint_runs,
   hover_import_runs)`: `archive_run_for_artifact(run_id=…)` now scans EVERY TTL'd run
   substrate and stamps `substrate` on the archived doc.
2. `run_archive.py::backfill_artifact_referenced_runs` — new sweep leg: every estimate
   `lp_source_run_id` stamp archives its run; hover-materialized stamps ALSO archive the
   SOURCE hover run (prefix match); reaped sources log an explicit unrecoverable warning.
   Runs every boot. Sweep result 2026-07-18: 4 runs ensured; 1 unrecoverable
   (`hover-4ffc35f4ded1-lap` source — pins re-armed via re-ingest instead).
3. `routes/hover.py::hover_lp_run` — NEW TRIGGER: the moment an estimate stamp is minted,
   BOTH the materialized LP run and its source hover run archive
   (`hover-lp-materialize` / `hover-lp-materialize:source`). Read side falls back to
   `fixture_runs` when the live hover doc has reaped.

## Re-arm (ordering per Howard's ruling: fix FIRST, then re-ingest)
- 261 Haugh Hover PDF re-uploaded → new run `7c6194d46b91444990b6910a175b12ff`
  (siding_sqft 2610 — extraction identical to the reaped run; Hover PDFs are text-tabular).
- First `hover-lp-run` call fired the new trigger: VERIFIED both
  `7c6194d46b91…` (substrate `hover_import_runs`) and `hover-7c6194d46b91-lap`
  (substrate `ai_measure_runs`) present in `fixture_runs` — **un-expirable from birth**.
- Pins updated: `test_haugh_round_two.py` + `test_iteration_47_haugh.py` → new run id.
  16/16 + 30/30 related tests PASS.

## Standing rule (unchanged, now structurally enforced)
"No persistent artifact may reference a reapable run." Archival bounds must equal the
LIVE TTL-index inventory — never an enumerated subset from memory. Any future collection
gaining a TTL index MUST be added to `_RUN_SUBSTRATE_COLLS` if runs it holds can be
referenced by estimates, freezes, quotes, or pinned tests.
