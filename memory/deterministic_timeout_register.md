# DETERMINISTIC-TIMEOUT REGISTER — Phase B reconcile
Named class (ruled 2026-07-17): ceilings that sit BELOW the real duration of a
complex-house reconcile are not safety nets — they are deterministic kill
switches. Every entry here was a 100%-reproducible failure, not flakiness.

## Variants observed
| # | Ceiling | Value | Mechanism | Killed | Fix |
|---|---------|-------|-----------|--------|-----|
| 1 | httpx read timeout, non-streaming `messages.create` | 300s of SILENCE | extended-thinking phase emits no bytes; read timer fires before first byte | b7a26956 attempts 1+2 (direct → APITimeoutError @300s → proxy junk) | STREAM (`client.messages.stream`) — bytes flow through the thinking phase, read timeout becomes per-chunk (2026-07-17) |
| 2 | `asyncio.wait_for` around the SYNC proxy call | 180s (couldn't fire) | sync `litellm.completion()` blocks the event loop; wait_for can't preempt a blocked loop — 15-min hang, whole API frozen | b7a26956 attempt 1's fallback + every route in the process | worker-thread wrapper `_send_message_nonblocking` (2026-07-17); proxy then RETIRED entirely |
| 3 | outer `asyncio.wait_for` in `_reconcile_extractions_direct` | 360s (= read+60), error text falsely said "180s" | canonical reconcile took 327s at 32k output; the 48k ceiling runs longer → 360s outer ceiling fires on every complex re-run | runs 1170d3f5, 3921e482, ddff780b (3/3, each at exactly 360,023 ms, marked hollow-"done") | unified `PHASE_B_CEILING_S` (env `AI_MEASURE_RECONCILE_CEILING`, default 900s), all paths; honest label (2026-07-17) |
| 4 | CLIENT retry-poll budget (`retryReconcileOnly`, AIMeasureButton.jsx) | 240s (80 × 3s) | client abandons the poll ("retry timed out") while the server is still legitimately reconciling — a sub-policy budget hiding outside the backend | would have failed the UI on every 327s+ retry even after variants 1–3 were fixed (caught in the 2026-07-17 status-parity consumer trace, before it fired in production) | raised to 960s (320 × 3s) ≥ server ceiling; pinned `test_client_retry_poll_budget_matches_ceiling` (2026-07-17) |

## Standing policy (pinned)
- ONE streaming client (`_reconcile_extractions_direct`), ONE ceiling
  (`PHASE_B_CEILING_S`), EVERY path through it. All four invocation paths —
  initial run, interactive re-run, auto-resume, retry button — funnel through
  `_reconcile_extractions`; there is no other Phase B outer wrapper (verified
  by inventory below).
- EVERY timeout/budget in the pipeline — server-side ceilings AND client-side
  poll budgets — audits against the empirical floor (327s complex-house
  reconcile at 32k; longer at 48k). No layer may carry a budget below it.
  Pins: `test_phase_b_single_ceiling_policy`,
  `test_client_retry_poll_budget_matches_ceiling`.
- No reconcile path may carry a ceiling below the empirically observed
  complex-house duration (327s at 32k; ceiling default 900s ≥ 2× observed
  with 48k headroom). Pin: `test_phase_b_single_ceiling_policy`.
- Timeout error text must state the ACTUAL configured value (variant 3 lied
  "180s" while firing at 360s). Pin: stale literal banned from source.

## Full Phase B ceiling inventory (2026-07-17 trace, all invocation paths)
| Wrapper | Value | Applies to |
|---|---|---|
| `PHASE_B_CEILING_S` outer wait_for (direct, streamed) | 900s default, env-tunable | initial / re-run / auto-resume / retry — all |
| httpx client Timeout on AsyncAnthropic | total=PHASE_B_CEILING_S, read=300s PER-CHUNK (streaming), connect=10s, write=60s | same |
| `_send_message_nonblocking` (proxy) | PHASE_B_CEILING_S | EMERGENCY-ONLY (proxy retired; AI_MEASURE_PROXY_EMERGENCY=1) |
(Other wait_fors in the file — per-photo 120s, wave drain 5s, salvage 120s,
health ping 5s — are Phase A / health scaffolding, not reconcile ceilings.)

## Adjacent pin from the same incident
Empty/pending measurement states render EMPTY, never 0 LF
(`ai-measure-lf-pending` panel state; `?? ""` not `|| 0`). Zeros presented as
readings on a failed run is hollow-done adjacent.
