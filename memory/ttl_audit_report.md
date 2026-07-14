# System-Wide TTL Audit Report (2026-07-14)

Scoped alongside the chase work (Iter 113 follow-through). Live-inspected against the running
database (`index_information()` on every collection) — not from code alone.

## 1. Mongo TTL indexes (physical deletion by the TTL scanner)

| Collection | TTL | Key | Live docs | September-relevant contents |
|---|---|---|---|---|
| `ai_measure_runs` | **30 days** | `created_at` | 50 | ALL AI Photo Measure run docs, incl. the demo clone `demo-letrick-4a009e93` and the original frozen source `4a009e93eb53…` |
| `ai_blueprint_runs` | **24 hours** | `created_at` | 11 | Blueprint takeoff runs — same-day quoting by design |
| `estimates_trash` | **30 days** | `deleted_at` | 15 | Soft-deleted estimates (Iter 113); restorable ≤30 d via `POST /estimates/trash/{id}/restore` |
| `hover_import_runs` | **24 hours** | `created_at` | 24 | HOVER async-import workers — transient |
| `hover_page_cache` | **1 hour** | `created_at` | 0 | Deep-Verify rendered elevation PNGs — transient |

TTL management: `startup.py::_ensure_ttl` (create → collMod-in-place on conflict → drop+recreate fallback), runs every boot.

## 2. Application-level expiry (docs persist; the ROUTE gates access — no Mongo TTL)

| Collection | Lifetime | Gate | September demo state |
|---|---|---|---|
| `accuracy_report_snapshots` (`/r/` links) | `expires_at` = created + **90 days** | 410 past expiry, 404 revoked (`routes/estimates.py:1221`) | Current demo `/r/` token created 07-14 → expires **2026-10-12** |
| `lp_material_list_snapshots` (`/m/` links) | created + **90 days** | 410/404 same doctrine (`routes/lp_package_routes.py:392`) | Current demo `/m/` token created 07-14 → expires **2026-10-12** |

Expired/revoked docs are never physically reaped (no TTL index) — history and content_hash provenance survive; a re-freeze mints a fresh token.

## 3. No TTL, no expiry (permanent unless explicitly deleted)

`fixture_runs` (frozen Letrick source, archived 2026-07-13 — the Iter-113 TTL defusal), `upload_blobs`
(399 docs: job photos + 3D snapshots — quote PDFs keep their images indefinitely), `ai_measure_sessions`
(74), `estimates`, `catalogs`, `companies`, `users`, `settings`, `price_tiers`, `invitations`,
`lp_legacy_price_archive`, `iss_catalog`, `mezzo_prices`, `vero_prices`, `accuracy` tape histories
(live on estimate docs — no TTL).

## 4. September-relevance findings

1. **Frozen demo chain is TTL-safe by construction.** The original source run `4a009e93` in
   `ai_measure_runs` (created 07-13) would expire ~**08-12 — before September** — but its archived
   copy sits in `fixture_runs` (no TTL, verified present) and demo reset prefers the archive. The
   demo clone `demo-letrick-4a009e93` is re-inserted with a fresh `created_at` on every reset, so
   the demo-morning reset restarts its 30-day clock. No September dependency on any TTL'd doc.
2. **Leave-behind lifetime math (QR):** a QR printed on the demo-morning reset (mid-Sept) is valid
   to ~mid-December. QRs printed TODAY expire **2026-10-12** — past a mid-September demo but dead by
   late October. Runbook already covers this: print final leave-behinds AFTER the demo-morning
   reset (reset also revokes prior demo QRs by design).
3. ⚠️ **Estimates outlive their runs (product gap, NOT a demo risk).** `ai_measure_runs` is 30 days;
   a customer estimate opened after that keeps its stored lines/pricing/quote PDF (all on the
   estimate doc + `upload_blobs`), but the LP Material List panel, 3D view, openings review, and
   `/lp-package/preview` return "No completed AI Measure run". **OPEN DECISION for Howard:** is 30 d
   right, or should runs referenced by estimates with stored lines be archived into `fixture_runs`
   style storage / TTL-extended?
4. **Blueprint runs are 24 h** — any blueprint-based demo material must be generated the same day
   (current demo script is photo-measure based; no exposure).
5. `upload_blobs` grows unbounded (no TTL). Not a September risk; flag for post-demo hygiene.

## 5. Cross-check vs. Iter 113 pins

`tests/test_estimate_delete_guard.py` pins the 30-day trash TTL index and the fixture archive path;
`test_demo_reset.py` pins reset idempotency + public link resolution. This audit adds no code
changes — findings 3–5 are decisions/backlog, not defects.
