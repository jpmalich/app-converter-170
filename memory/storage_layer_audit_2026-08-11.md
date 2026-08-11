# STORAGE-LAYER AUDIT — 2026-08-11 (report only, zero code changes)

Ordered after TTL incident #3 (EST-886440 grading chain reaped). Scope:
every mechanism that removes or expires data WITHOUT code executing, plus
automated code-side removals the AST seam detector cannot see. Method:
live-DB index walk (all 22 collections), cron/systemd/supervisor walk,
logrotate walk, full-codebase grep (delete_many / delete_one / drop /
unlink / $unset / TTL), platform cron inspection.

## TIER A — mongod's TTL monitor (no code executes; the exact incident class)
None of these five appear in seam_accounting.SEAM_REGISTRY. The AST
detector is structurally blind to all of them.

| # | Collection.index | Window | Status |
|---|---|---|---|
| A1 | ai_blueprint_runs.created_at_1 | 30 days (raised today, was 24h) | Reaper UNLEDGERED. Archive fires only on artifact events (quote-send/freeze/materialize) — unapplied runs still die, just 30× later. Fixes #2/#3/#4 pending (Phase 3). |
| A2 | ai_measure_runs.created_at_1 | 30 days | Same class as A1: archive-on-artifact only; an unapplied photo run under evaluation dies at +30d. UNLEDGERED. |
| A3 | hover_import_runs.created_at_1 | 24 HOURS | SAME ANTI-PATTERN AS THE INCIDENT, shortest window in the DB. Archive fires only on hover-lp-materialize. A hover run being evaluated but never materialized is reaped inside a day. UNLEDGERED. |
| A4 | estimates_trash.deleted_at_1 | 30 days | Ruled soft-delete retention (2026-07-23, receipted). Intentional — but the reaper itself is UNLEDGERED like the rest. |
| A5 | hover_page_cache.created_at_1 | 1 HOUR — ORPHANED | Code retired the collection 2026-07-29; startup no longer creates this index; the LIVE DB still carries it (count=0 today). Any future write to that name dies within the hour with zero code trace. A trap, not a policy. |

Verified NO TTL on: estimates, fixture_runs, upload_blobs, users,
companies, catalogs, sessions, price_tiers, mezzo/vero prices, snapshots
(estimates no-TTL is pinned in test_estimate_delete_guard.py).
No capped collections anywhere (capped = silent oldest-doc eviction).

## TIER B — process/pod lifecycle (no code decides)
- B1: In-memory asyncio workers die on every restart (failure class 5).
  ai_measure_runs gets a boot sweep (sweep_orphaned_runs: resume or flip
  to class-5 error). ai_blueprint_runs HAS NO SWEEP — a dead blueprint
  worker leaves a status='running' doc polling grey until the TTL (A1)
  destroys the evidence of the failure.
- B2: /app is a PVC — uploads/ (1.4 GB) survive restarts; upload_blobs
  (1,949 docs) self-heals disk misses. No lifecycle policy on either. OK.
- B3: NamedTemporaryFile in routes/hover.py — self-cleaned in finally. OK.

## TIER C — code that removes data on EVERY BOOT (no human act)
- C1: startup.py vero_prices.delete_many(obsolete products + tiers) —
  force-reseed follows; any admin price edit to an obsolete doc is
  destroyed silently each boot. By design (Iter 78y) but unledgered.
- C2: startup.py legacy-catalog migration: $unset sections; delete of
  catalog id="default". Dormant (legacy shapes gone). One-way.
- C3: run_archive.backfill_artifact_referenced_runs — ADDS data. Safe.

## TIER D — route/script deletes (human-triggered; for completeness)
- D1 estimate soft-delete → estimates_trash (then A4 reaps at 30d).
- D2 branding-admin test-company purge (companies/users/sessions/
  catalogs/estimates/invitations cascade).
- D3 catalog.py company-delete cascade (estimates + users + catalogs).
- D4 demo reset cascade (old demo estimate's runs + snapshots).
- D5 run_archive.purge_test_artifact_runs (tagged docs only; tag is
  creation-time-only, pinned).
- D6 deletion_handback.py / purge_protect_handback.py — one-shot
  receipted scripts, not scheduled; safe unless re-run by hand.

## TIER E — platform / infra
- E1: Emergent webhook-cron (every minute, watch_crons.sh) — dispatches
  webhooks only; no app-data deletion found in the scripts.
- E2: logrotate (nginx/apt/dpkg) + supervisor log rotation — logs only.
- E3: MongoDB internals (WiredTiger cache eviction, oplog) — never
  user-visible document removal.

## FINDINGS RANKED
1. A3 hover_import_runs @24h — the incident anti-pattern, live today,
   shortest fuse. Phase 3's archive-on-view + ledger should cover it.
2. A5 hover_page_cache orphaned 1h TTL — a trap; nothing writes there
   today, but the index outlived its code. Candidate for explicit drop.
3. B1 no blueprint dead-worker sweep — restart kills a run AND the TTL
   later destroys the proof.
4. A1/A2/A4 reapers unledgered — Phase 3 fix #4 should register the
   WHOLE Tier A class, not one index.
5. C1 boot-time vero purge — ruled, but a silent per-boot delete_many.
