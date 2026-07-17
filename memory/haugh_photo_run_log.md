# 261 Haugh Dr — Photo run log (est 48231310-3872-4d4e-b657-35ade10c1cb8)

Only ONE photo run doc exists on this estimate. The "refined run" is
b7a26956's third reconcile attempt — the run doc's result was overwritten
in place on each retry. Attempt history:

| # | When (UTC) | Transport | Outcome |
|---|-----------|-----------|---------|
| 1 | 07-17 ~16:48 (auto-resume) | direct (non-streaming) → APITimeoutError @300s → proxy | proxy hung 15 min blocking loop → 502 → error |
| 2 | 07-17 17:16 | direct (non-streaming) → APITimeoutError @300s → proxy | proxy 53s, reply had NO JSON → hollow "done" (0 walls) — honesty defect, since fixed+pinned |
| 3 | 07-17 17:25→17:31 | **anthropic_direct, STREAMED** | **DONE — canonical** |

## CANONICAL RUN
- run_id: `b7a269564c654f998ab63d8b829199d4` (attempt 3)
- transport: `anthropic_direct` (streamed), latency 327,693 ms
- model: claude-fable-5 · usage: input 27,394 / output 32,000 (ceiling) / thinking 0
- REF STATE: per-photo WALL REF bars 273"–360" on-plane (8/8 photos) +
  per-photo WIN REF window anchors (30"–110"). Reconciler's own
  `reference_used` (verbatim): "Per-photo WALL REF bars (273"–360")
  on-plane, cross-checked by WIN REF window anchors (photo 2's 48" and
  photo 4's 73" both corroborated)". `scale_confidence: medium`.
- max_tokens STATUS: stop_reason=max_tokens at the 32,000 ceiling;
  `_extraction_partial: true`, `_json_repaired: "truncation"` — the JSON
  salvage recovered a complete parse (4 walls, 15 corner locations,
  38-row openings schedule, dormer). Ceiling RAISED to 48,000 via
  `AI_MEASURE_RECONCILE_DIRECT_MAX_TOKENS` in backend/.env (2026-07-17
  ruling) before the next complex-house run. No re-run for this alone.

## Comparison partner
- Hover run `hover-4ffc35f4ded14b46bc6eb267469efbfd` (261 Haugh report,
  net values, wrap-only scope: Siding 2,064 of 2,610 total facades;
  stucco 312 + brick 234 excluded per wrap-default ruling).
