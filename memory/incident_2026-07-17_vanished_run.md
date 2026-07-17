# Incident 2026-07-17 — "Vanished" Haugh photo run (b7a26956, est 48231310)

## What actually happened (nothing was deleted)
- Run doc NEVER left the DB. Timeline (UTC):
  - 12:57 run created; Phase A 8/8 done (anthropic_direct); reconcile in flight.
  - ~16:47 platform pod restart (post-batch checkpoint) killed the reconcile task.
  - 16:48:19 startup sweep DID fire → AUTO-RESUMED reconcile-only (attempt 1/1 cap).
  - Direct-B attempt timed out at 300s (non-streaming + extended thinking = silent
    read → httpx APITimeoutError) → fell back to proxy at 16:53:19.
  - Proxy call was a SYNC litellm.completion() inside async send_message —
    it BLOCKED THE ENTIRE EVENT LOOP ~15 min (documented proxy hang mode #4),
    then returned 502 at 17:08:21 → run flipped to ReconciliationRetryError.
  - UI looked "vanished" because every API route was frozen while the loop
    was blocked; the run banner had nothing to poll.

## Root causes fixed (all pinned in tests/test_worker_lifecycle_class5.py)
1. **Event-loop freeze**: `_send_message_nonblocking` wrapper — ALL 6
   LlmChat.send_message call sites now run on a worker thread; a proxy hang
   can never freeze the app again. Pin: `test_proxy_llm_calls_are_nonblocking`.
2. **Direct-B timeout**: `_reconcile_extractions_direct` now STREAMS
   (`client.messages.stream` + `get_final_message`). The successful direct
   run took 327s — over the old 300s silent-read ceiling every time.
   Pin: `test_direct_phase_b_streams`.
3. **Hollow-done honesty**: reconcile-only worker treated `_parse_error`
   (proxy returned prose) as success → run "done" with 0 walls/0 sqft.
   Now flips to error, Phase A intact. Pin:
   `test_reconcile_only_hollow_result_never_passes_as_done`.
4. **In-flight gap (user ruling)**: `/ai-measure/in-flight` now counts
   status=error runs with persisted raw_per_photo (<24 h) as
   `kind: "awaiting_retry"`; restart_safe=false while any exist. Pins:
   `test_in_flight_counts_awaiting_retry_runs`, `test_in_flight_ignores_stale_error_runs`.
5. **Key routing**: class-5 resume + reconcile-only endpoint now pass
   phase="B" to `_pick_llm_api_key`. Pin: `test_class5_resume_and_retry_use_phase_b_key_routing`.
6. **Test collateral kill (agent's own mistake)**: `test_startup_sweep_recovers_orphans`
   ran the GLOBAL sweep against the shared DB and class-5-flipped a LIVE
   mid-retry run. Now runs against an isolated throwaway DB (dropped after).

## Final state
- Run b7a26956: **done via anthropic_direct**, 327,693 ms, parse clean.
  4 walls, 15 corner locations, siding 1,991.2 ft², eaves 100 / rakes 110.
  CAVEAT: stop_reason=max_tokens (32k output ceiling hit; JSON parsed fully,
  but tail fields may have been clipped — bump
  AI_MEASURE_RECONCILE_DIRECT_MAX_TOKENS if anything reads short).
- Session repointed to the reconciled result; estimate 48231310 resumes normally.

## Standing lessons
- NEVER run the global sweep (or any global mutator) against the shared DB
  from tests.
- Before any deliberate restart: GET /api/measure/ai-measure/in-flight —
  restart_safe must be true (now includes awaiting_retry runs).
- Proxy transport trace for the record: litellm logs show provider=openai
  because the Emergent proxy exposes an OpenAI-compatible endpoint; the
  502s/hangs are the proxy gateway, not api.anthropic.com. Direct-B goes
  through AsyncAnthropic (httpx) and never touches litellm.
