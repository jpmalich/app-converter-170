# SEED CENSUS — 2026-07-23 (Howard's consolidated ruling, item 3a)
Report only — no tooling built. Scope + sizes for the export tool / seed runner (3b)
and for full production provisioning ahead of the September demo (ruling item 4:
demo platform = PUBLISHED APP).

## A. Per-fixture photo/file census (live-measured, zero missing from both stores)
| Fixture | est-doc | runs (docs) | photo/file refs | payload |
|---|---|---|---|---|
| red house EST-910869 (673707d5) | 4 KB | 23 (2.2 MB) | 62 | 35.3 MB |
| EST-910869-L pair (e452a988) | 6 KB | 0 | 0 (derivation-only) | 0 |
| Letrick EST-373526 (8f95c9c2) | 78 KB | 2 (0.2 MB) | 17 | 25.7 MB |
| doug jones EST-510771 (db82ec7a) | 89 KB | 7 (0.2 MB) | 17 (blueprint pages) | 25.7 MB |
| haugh EST-067615 (48231310) | 2 KB | 3 (0.3 MB) | 33 | 45.4 MB |
| round-two banked (d78cd3b4) | 3 KB | 0 | 0 | 0 |
| DEMO-LETRICK (id rotates on reset) | 7 KB | 2 (0.2 MB) | 8 | 9.8 MB |
| **TOTAL** | ~190 KB | 37 (~3 MB) | **137 unique** | **~142 MB** |
Context: upload_blobs total 323 MB / 724 docs; disk store 1.1 GB (gitignored). The
137 fixture files are the transported subset; the rest is unreferenced residue.

## B. Full prod-provisioning inventory (everything an empty prod DB needs)
1. **Pricing + engine data (~260 KB total)** — export as-is, seed verbatim:
   vero_prices 9 (6 KB) · mezzo_prices 16 (42 KB) · iss_catalog 51 (8 KB, placeholder
   until Howard's ISS Excel lands) · price_tiers 4 (115 KB) · lp_legacy_price_archive
   31 (28 KB) · settings 3 (1 KB: `branding` supplier identity, `lp_margin_tiers`,
   `lp_native_mode` — currently disabled; demo reset reads it).
2. **Accounts**: owner user + company (2 docs) — seed via the registration machinery
   (which auto-creates the per-company catalog doc), password from prod env.
   Supplier admin is token-based (SUPPLIER_ADMIN_TOKEN prod env var — no doc).
3. **Demo estimate**: NOT exported by ID (its id rotates on every demo reset — the
   suite itself rotates it). Seed = its 8 photos (9.8 MB) + archived runs; then
   `POST /demo/reset` reconstructs the estimate idempotently. Pattern already proven.
4. **Fixture docs**: 7 estimates + runs → seed target is `fixture_runs` (no-TTL
   archive) + `ai_measure_sessions` + `lp_openings_review` / `lp_appendage_dims`
   states. Stable IDs preserved verbatim so every pinned test keeps working.
5. **Human rungs — import-stamped transport (PINNED, ruling 3c)**: red house
   `tape_check.walls` (incl. the 33 + 1 cut human course count) + scored history
   (95.2% + Δc −5 under-count record); Letrick chase tape + dormer appendage dims
   (`user_measured`); ratified positions. Transport carries original timestamps +
   an explicit import stamp. Re-entry reserved for disputes. Synthesis never.
6. **Needs NOTHING**: sealed key (code: letrick_hand_takeoff_key.py), extraction
   prompts (code), frozen /m/ + /r/ snapshots (environment-bound — re-minted on the
   production domain AFTER demo reset, per the morning-of checklist ruling).

## C. Two seed scopes for ruling (size drives the mechanics)
- **PROD-MINIMUM (demo-critical): ~45 MB** — DEMO-LETRICK (9.8 MB) + red house
  (35.3 MB, the second demo-grade fixture w/ accuracy record) + pricing/settings
  (260 KB) + accounts. Enough to run the September demo end-to-end on prod.
- **FULL PARITY (every pinned fixture): ~147 MB** — all 137 files + all docs.
  Needed only if the pinned test suite should ALSO run green against prod.
Mechanics implied: fixture JSON docs in-repo (~5 MB — fine); photo bytes exceed
sane repo size at full parity → one-time transported pack (tar of blobs imported
into prod `upload_blobs` by the seed runner; disk rehydrates via the standing
self-heal read path). At PROD-MINIMUM scope an in-repo pack is borderline viable
(45 MB) — ruling preference requested.

## D. Findings surfaced (not acted on — outside the deletion markup)
- 102 of 103 non-revoked `/r/` accuracy snapshots are orphans of HTTP-test-created
  estimates that no longer exist (test artifacts; ~100 docs). The 3 `/m/` links
  belong to keeps (2 × LP pair, 1 × demo). Orphan purge available on ruling.
- `invitations` 153 docs (57 KB) — test residue, not needed in prod seed.
- Test-host hardcoding (~20 test files pin the preview URL) — queued in 3b.
