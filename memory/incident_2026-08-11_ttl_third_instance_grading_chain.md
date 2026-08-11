# INCIDENT — TTL EXPIRY, THIRD INSTANCE: EST-886440 GRADING CHAIN REAPED (2026-08-11)

## WHAT HAPPENED (mechanism, verified live — no fix applied)
`ai_blueprint_runs` carries a Mongo TTL index: `created_at_1,
expireAfterSeconds=86400` (24 HOURS). Run docs store `created_at` as a
BSON datetime, so the TTL monitor applies. Every blueprint run dies 24h
after creation UNLESS archived into `fixture_runs` (no TTL) — and
archival fires ONLY on artifact events: quote-send, /m/ freeze, /r/
freeze, hover-lp materialization (run_archive.py, ruled 2026-07-14).

The grading chain (8-6 original, 82bd3a5e, 76203e6a, 840b34e8,
a4cbce91) was DELIBERATELY never applied — rider HELD, no quote sent,
no freeze minted. So no archival trigger ever fired for it. Each run
died silently at its own +24h mark all week; the panel stayed populated
only because new runs kept arriving. After the 8-9 20:10 run
(a4cbce91), Howard stopped rerunning for his card walk — the collection
drained to ZERO at 2026-08-10 ~20:10 UTC (a4cbce91's expiry), which is
exactly when the PENDING panel and the elevation endpoint went empty.
Verified: collection count 0; none of the five run_ids in fixture_runs.

## THE GUARD IS INNOCENT — VERIFIED
- The untouchable guard blocks writes to the ESTIMATE document only.
  Estimate doc `updated_at` = 2026-08-07T20:29 UTC — BEFORE the guard
  existed. Nothing wrote to EST-886440 through any route, guarded or
  not. The guard read-paths (panel, elevations) are unguarded reads.
- The reaper is `mongod`'s own TTL monitor — no app route, no test.

## THE PRICE QUESTION — NO WRITE OCCURRED
Stored lines on EST-886440 carry NO unit prices (stored material total
$0; pricing_mode margin). The VINYL/ASCEND banner totals are COMPUTED
AT RENDER from the live catalog + the CURRENT derivation code. The
document is untouched; the movement ($17,870.21→$18,355.04 vinyl,
$46,151.89→$46,164.61 ascend) is display-time and traces to the ruled
derivation changes landed 8-9/8-10 (accent injection un-gated; rakes
plane-sum governs; porch wall-side geometry), not to any write.

## WHY THE CLASS BIT A THIRD TIME (Haugh hover pins were the second,
incident_2026-07-18): archival is tied to ARTIFACTS. A grading chain
whose whole point is to never become an artifact had NO path into
fixture_runs. One-directional blindness again: the rule protected runs
that MATTER TO CUSTOMERS and was blind to runs that matter to GRADING.
And the reaping is a REMOVAL WITH NO ACCOUNTING — the silent-truncation
class living at the STORAGE layer, outside the seam registry's reach.
The card never said "this run expires in 24h."

## WHAT SURVIVES / WHAT IS GONE
- GONE (unrecoverable from Mongo): the five run documents — reads,
  readbacks, seam ledgers, locator boxes, run stamps.
- SURVIVES: 103 `bpsrc_*` source files on disk + blob store (the
  original PDFs/images, 8-6 through 8-10); page images; the estimate
  document itself (untouched); the walked numbers and per-run findings
  in /app/memory and PRD (the paper survived the database).

## CANDIDATE FIXES (NOT BUILT — Howard rules)
a) UNTOUCHABLE ⇒ UNREAPABLE: any run landing on an untouchable
   estimate auto-archives to fixture_runs on completion (the grading
   chain becomes its own artifact class).
b) Raise/remove the 24h TTL on ai_blueprint_runs (ai_measure_runs
   gets 30d; 24h for blueprint reads is the aggressive outlier).
c) SAYS-SO on the card: a run subject to TTL prints its expiry
   ("this run is reaped at {t} unless applied/archived").
d) Register the TTL reaper as a seam (storage-layer removal census).
