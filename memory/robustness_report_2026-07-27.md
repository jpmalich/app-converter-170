# Robustness Report — AI Measure pipeline (report only, no build) — 2026-07-27

## (a) The two timed-out runs — both completed server-side; both persist and surface

**Run 7bcc56e2 (EST-986945 "7-26-26-2pm", 8 photos, 18:16 UTC).** Completed
server-side IN-SESSION: 18:16:19 → 18:25:44 (9m25s; Phase B reconcile call
230s). The UI wait exceeded patience but the worker never died. Result
persisted; surfaces on reload via `latest-for-estimate` (verified 200,
status=done) — every sheet/quote built today reads this run.

**Run d8ea786a (EST-179127 "test 7-26-26-7pm", 8 photos, 23:41 UTC).**
Completed server-side, NOT in-session. Timeline: phase A finished 7/8
photos clean + 1 salvage-retry (checkpointed to `raw_per_photo`), entered
`reconciling`, then the WORKER DIED — `asyncio.create_task` workers are
process-bound and do not survive pod hibernation/hot-reload (named in-code).
Death detection requires a status poll or a process start; nobody polled
overnight, so the run stranded until the pod woke at 04:33:13, when the
startup sweep found it, dispatched the reconcile-only auto-resume
(attempt 1, checkpointed extractions reused — no photo re-calls), and it
completed 04:37:54. Wall clock 4h56m; actual compute ~14 min. Result full
(`_pipeline: two_phase_reconcile_only_retry`); persists + surfaces on
reload (verified 200, status=done, resume-banner path).

Same-day context: two more runs died as `worker_died` and flipped to ERROR
instead of resuming (bde315fe 00:25, 800c331b 10:59) — by policy,
auto-resume requires phase-A checkpoints; these died without any, so they
surfaced as errors for manual re-run (which Howard did: fae641d4 at 11:06,
done). Historical precedent: b7a26956 (7-17) = the identical
die-then-resume-at-next-boot pattern (16,433s wall). This class has now
occurred 2× — it is systemic, not incidental.

## (b) Phase B duration telemetry — before vs after the split machinery

Source: persisted per-run telemetry (`raw_per_photo[]._latency_ms`,
`raw_ai._reconciliation_latency_ms`, created→completed). Done runs, 8 photos.

| era | n | Phase B (reconcile call) | per-photo max (Phase A) | total wall (clean) |
|---|---|---|---|---|
| PRE-split (single-shot Phase A, 7-07) | 2 | 122s / 143s | 300s (timeout cap hit, both) | 447s / 506s |
| POST-split (4 waves × concurrency 2) | 52 | med 252s (90–587) | med 96s (14–250) | med 661s (140–1378) |
| POST, 7-07→7-14 | 38 | med 226s | — | — |
| POST, last 3 days (7-24→7-26) | 11 | med 271s (206–340) | — | med 800s |

Honest reading:
- The split bought RELIABILITY, not speed: per-photo 300s timeout caps are
  gone (median max 96s), failures isolate per wave with salvage retry, and
  phase-A checkpoints enable reconcile-only resume. Totals did NOT improve
  (median ~11 min; last-3-days ~13 min).
- Phase B has GROWN ~20% (226s → 271s median) and is now the single
  longest, un-checkpointable call — it carries all 8 extraction payloads +
  contractor quads/gables + pin-gap hints + audits. It is also where
  d8ea786a died: Phase B is now the pipeline's exposure window.
- Per photo count: the fleet is effectively all-8-photo (52/52 telemetered
  done runs); no 2/4/6-photo variance data exists. TELEMETRY GAP, named:
  no per-stage wall-clock timestamps are persisted (phase A wall is
  estimable from wave latencies only).

## (c) True async pattern — sized, NO BUILD

What already exists: background worker + status polling + resume banner
(`latest-for-estimate`) + heartbeat idle detection on poll + startup sweep
+ phase-A per-photo checkpoints + reconcile-only auto-resume (cap 1).
The architecture is already async; its failure classes are:
  F1 — workers are process-bound (die on hot-reload/hibernation);
  F2 — death detection is passive (poll or boot; overnight = stranded);
  F3 — Phase B is a 4–6 min monolithic call, no mid-call checkpoint;
  F4 — no-checkpoint deaths flip to error and need a human re-run.

Sized rungs (each independently shippable; none built):
- **R1 — active watchdog (S, ~0.5 day):** in-process 60s sweep task (same
  logic as the poll-path detector) so a dead worker is claimed within
  minutes while ANY process lives, instead of waiting for the next boot.
  Kills the 4h51m stranding class where the process survived. Pins: sweep
  claims are atomic (existing race guard), fixture runs untouched.
- **R2 — supervisor-managed worker loop (M, ~1.5–2 days):** move execution
  out of uvicorn into a small supervisor-run worker process consuming a
  Mongo-leased job queue (state machine already exists on the run doc);
  hot-reload/uvicorn restarts stop killing workers; leases + idempotent
  stage checkpoints give exactly-once resume; raise the resume cap with
  backoff. Pins: lease atomicity, no double-execution, byte-identical
  results for single-attempt runs.
- **R3 — perceived latency (S–M, ~1 day):** honest ETA chip from fleet
  telemetry ("Phase B running — median 4½ min"), SSE progress channel
  replacing poll loops, and phase-A concurrency 2→4 trial (the 7-10 22:0x
  cluster completed in 140–250s total, proving throughput headroom exists;
  a pre-registered timed trial would confirm proxy limits before ruling).
- **Boundary named:** preview-pod HIBERNATION kills any in-pod worker
  regardless of pattern (R1/R2 included). Only the deployed environment
  (always-on) or an external queue removes F1 entirely. A live demo on
  preview inherits this; a live demo on deploy does not.

No code changed for this report. Standing queue unchanged: B (drag-adjust)
after four-photo acceptance → model ledger → money-surfaces map.
