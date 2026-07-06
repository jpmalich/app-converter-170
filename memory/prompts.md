# Reusable Feature Prompts

Portable, self-contained prompts for reproducing features from this project
in a **different codebase or fresh AI-coding session**. Each entry captures
enough context (what, why, files, gotchas) that an agent starting from zero
can rebuild the feature without needing this repo.

## Conventions

- **One prompt per shipped feature/iteration.** Bug-fix-only iterations
  update the most-relevant existing prompt rather than creating a new one.
- **Version format**: `IterXX.YY` matches the tag used in code comments and
  `PRD.md`. Timestamp is UTC ISO-8601.
- **When an update touches an already-logged feature**, edit the existing
  prompt's `Last updated` date + `Change log` section rather than
  duplicating it. Keep the top of the file (this section) short.
- **Prompts should be portable**: no references to file paths in this repo
  unless the pattern *needs* them (e.g. `/app/backend/routes/`). Use
  placeholder names like `<your-route-file>` when generic.
- **Every prompt ends with a `## Regression guard`** listing the tests or
  manual checks that prove the feature works.

---

## Template

```
### <Feature name>

- **Version**: IterXX.YY
- **Created**: YYYY-MM-DDTHH:MM:SSZ
- **Last updated**: YYYY-MM-DDTHH:MM:SSZ
- **Change log**: (append-only bullets when the prompt is amended)

**Problem it solves**: (1-2 sentences — the failure mode that motivated
this feature)

**Prompt**:
> [paste this into a fresh AI-coding session]
> ...

**Regression guard**:
- Test file(s): ...
- Manual check(s): ...
```

---

# Prompts

### AI Vision — Two-Phase Extraction Pipeline (Map-Reduce)

- **Version**: Iter79j.44
- **Created**: 2026-02-28T14:00:00Z
- **Last updated**: 2026-02-28T14:00:00Z
- **Change log**: initial entry.

**Problem it solves**: A single-call LLM vision pipeline over N photos is
fragile — one hung photo cancels the whole batch, and error strings
propagate as blank toasts (`str(TimeoutError())` = `''`). This turns a
partial-result situation into a total failure with no diagnostic.

**Prompt**:
> Implement a two-phase AI vision pipeline for extracting structured data
> from a batch of user-uploaded photos.
>
> **Phase A — parallel per-photo extraction**:
> - Each photo is dispatched as its own async task via
>   `asyncio.create_task`, wrapped with `asyncio.wait_for(...,
>   timeout=PER_PHOTO_BUDGET)`. Default budget 240s, env-configurable via
>   `<APP>_PER_PHOTO_TIMEOUT`.
> - Inside `_extract_one_photo`, each LLM call has a per-call timeout
>   (default 120s, env `<APP>_PER_CALL_TIMEOUT`). If the first call
>   returns "empty" (no meaningful data), retry ONCE with a nudged prompt
>   ("The previous response was empty; look harder…"). If both attempts
>   are empty, mark the photo `_empty_extraction=True` with a
>   human-readable `_empty_reason`.
> - Batch coordination uses `asyncio.wait(tasks, timeout=PHASE_A_TOTAL)`
>   NOT `asyncio.wait_for(gather(...))`. `wait` does not cancel-all on
>   timeout, so slow photos are cancelled individually while fast ones
>   still return.
> - After timeout, cancel pending tasks but DRAIN with a bounded
>   `asyncio.wait_for(gather(*pending, return_exceptions=True),
>   timeout=5)` — a longer drain waits for cancelled HTTP calls to
>   unwind their synchronous awaits inside `httpx`, defeating the point
>   of the cap.
> - Log per-photo latencies: `logger.info("[phase-A] photo N done in
>   Xms (empty=…)")` for post-hoc diagnosis.
>
> **Phase B — text-only reconciliation**:
> - Feed the ARRAY of Phase A extractions (including empty ones with
>   their `_empty_reason`) to a single reconciler LLM call. The
>   reconciler NEVER sees the raw photos again — text only.
> - The reconciler must produce a unified output that respects
>   provenance: if wall X only came from photo 3, don't hallucinate wall
>   X measurements from other photos.
>
> **Error surfacing**:
> - Any exception in the worker MUST produce a non-empty error string:
>   `friendly = str(e).strip() or type(e).__name__`.
> - Persist `error_kind` (exception class name) alongside `error` on the
>   run document so the frontend can distinguish `TimeoutError` from
>   `AuthenticationError` from `ValueError`.
>
> **Env knobs** (all optional, safe defaults):
> - `<APP>_PER_CALL_TIMEOUT` (default 120)
> - `<APP>_PER_PHOTO_TIMEOUT` (default 240)
> - `<APP>_PHASE_A_TIMEOUT` (default 300)
>
> **Frontend contract**:
> - Persistent inline error banner (NOT a toast) showing
>   `Phase: <stage>`, `Elapsed: Xs`, `Kind: <ErrorClass>`, plus a
>   one-click Retry button. Toasts auto-dismiss and are hidden behind
>   modals — a $-affecting failure needs a durable banner.
> - Track the server stage in a mutable local `let liveStage` inside
>   the polling function — React state closures capture the render-time
>   value and don't update inside the async loop.
> - Before writing the reconciled output into the user's document,
>   check for any `_empty_extraction` or `_orphaned_walls` list and
>   show a `window.confirm` warning ("this takeoff has unmeasured
>   walls: front, back") that the user must acknowledge.

**Regression guard**:
- Test file: `backend/tests/test_phase_a_resilience.py` — drives the
  real pipeline with a monkey-patched slow photo and asserts the
  hanging photo is flagged with `_empty_extraction=True` while the
  fast photo still reaches Phase B intact.
- Test file: `backend/tests/test_two_phase_pipeline.py` — pins the
  reconciler input/output shape.
- Manual: kick a run, kill one photo's LLM call mid-flight, verify
  banner shows the correct phase + kind + doesn't wipe partial results.

---

### AI Vision — Service Health Preflight

- **Version**: Iter79j.45
- **Created**: 2026-02-28T14:00:00Z
- **Last updated**: 2026-02-28T14:00:00Z
- **Change log**: initial entry.

**Problem it solves**: A contractor kicks off a full LLM run only to
discover 5 minutes later that the API key budget is exhausted / the LLM
proxy is down / the provider is refusing requests. All the compute + wait
time is wasted, and the error message is often generic ("Internal server
error"). A cheap preflight ping distinguishes actionable failures
(budget, unauthorised) from ambiguous ones BEFORE the expensive run
dispatches.

**Prompt**:
> Add a `GET /api/<domain>/health` endpoint that fires the smallest
> possible LLM call (typically `max_tokens=1` with a 5s deadline) against
> the same model + provider path the main pipeline uses. Return:
>
> ```
> {
>   "status": "ok" | "budget_exceeded" | "unavailable" | "ambiguous",
>   "detail": "human-readable copy",
>   "checked_at": "ISO-8601",
>   "cached": bool,
>   "latency_ms": int | None  // None when served from cache
> }
> ```
>
> **Server-side cache**: module-level dict with 45s TTL. Never ping more
> than once per 45s per pod.
>
> **Classifier** (pure function `_classify_health_error(err_msg)`):
> - Budget markers → `budget_exceeded`
> - `timeout` / `connection refused` / `DNS` / `unreachable` →
>   `unavailable`
> - `unauthorised` / (`invalid` AND `key`) / `forbidden` →
>   `unavailable`
> - Anything unrecognised → `ambiguous` with the raw error truncated
>   into `detail`
> - **NEVER collapse an unknown error into "budget_exceeded"** — an
>   unknown failure must NOT masquerade as an actionable one.
>
> **Frontend contract**:
> - Client-side 45s cache mirroring the server. Ping on:
>   (1) modal open, (2) before every run dispatch. Never on render.
> - Button state:
>   - `ok` → normal Run button
>   - `budget_exceeded` → red "Budget exhausted — top up first", but
>     CLICKABLE (a broken health check must never lock the product —
>     click forces a re-ping instead)
>   - `unavailable` → red "AI service unavailable — click to re-check"
>   - `ambiguous` → normal Run button STAYS ENABLED + soft amber
>     banner. **A broken health check must NEVER be able to disable the
>     product.**
> - `runMeasure` calls `refreshAiHealth()` first; on `budget_exceeded`
>   or `unavailable` sets a persistent error banner (`Phase: preflight`,
>   `Kind: BudgetExceeded / ServiceUnavailable`) and does NOT dispatch
>   the run.
>
> **Cost note**: with `max_tokens=1` and a 45s cache, cost is negligible
> (~$0.00003 per pod per uncached ping on Claude opus rates). Use the
> SAME model as the worker so the health path exactly mirrors the run
> path — no risk of health passing on a cheap model while the expensive
> model fails.

**Regression guard**:
- Test file: `backend/tests/test_ai_health_ping.py` — 4 pure-function
  classifier tests covering budget_exceeded, unavailable, ambiguous,
  and truncated-detail buckets.
- Manual: call `curl /api/measure/ai-measure/health` twice within 45s
  → 2nd call should have `cached: true, latency_ms: null`.

---

### AI Vision — Event-Driven Auto-Recovery (No Polling While Healthy)

- **Version**: Iter79j.46
- **Created**: 2026-02-28T15:00:00Z
- **Last updated**: 2026-02-28T15:30:00Z
- **Change log**:
  - 2026-02-28T15:30:00Z — Fixed TDZ crash: hoisted the three
    `useEffect` blocks to sit AFTER the `refreshAiHealth` /
    `isHealthRed` declarations they depend on. React function
    components run top-to-bottom on render, so effects that read
    consts declared later throw
    "Cannot access 'X' before initialization".

**Problem it solves**: When a contractor exhausts their LLM budget and
tops up in another tab, the app should detect the recovery without them
having to click anything. But polling `/health` on a timer while the
app is healthy wastes money and adds latency.

**Prompt**:
> Extend the health-preflight feature with event-driven recovery. Only
> ping when SOMETHING useful might have changed:
>
> 1. **Visibility + focus listeners** attach ONLY when the modal is open
>    AND `status` is red (`budget_exceeded` or `unavailable`). Detach the
>    moment status flips green or the modal closes. This catches the
>    "went to billing, topped up, came back" moment for free.
>
> 2. **Red button is CLICKABLE as a re-check escape hatch.** Icon swaps
>    to a refresh symbol; label becomes "…click to re-check". Clicking
>    fires `refreshAiHealth({force: true})` instead of dispatching the
>    run.
>
> 3. **Slow backoff timer** (60s → 2min → 5min → stays 5min) ONLY runs
>    while status is red. Any status change cancels + restarts. **Never
>    polls while green** — a healthy button has nothing to learn from a
>    ping.
>
> **React hoisting gotcha**: Effects reference `refreshAiHealth` and
> derived state like `const isHealthRed = ...`. Because React function
> components execute top-to-bottom on render, these effects MUST be
> declared AFTER the consts they depend on. If you get "Cannot access
> 'X' before initialization", hoist the effects, don't touch the
> consts.
>
> **Never eslint-disable to work around missing deps** — either add the
> deps to the array or use `useRef` for values that shouldn't retrigger
> the effect. In this feature: the backoff timer holds its state in
> `backoffTimerRef` (setTimeout handle) and `backoffStepRef` (schedule
> index), so the effect can safely depend on just `[open, isHealthRed]`.

**Regression guard**:
- Manual: force `budget_exceeded` (e.g. mock the endpoint), open the
  modal → red button appears → alt-tab away → alt-tab back → verify a
  fresh ping was fired (network tab).
- Manual: hover the red button — cursor is pointer, not not-allowed.
  Click it → refresh icon animates, new ping goes out.
- Manual: with modal open and status green, watch network tab for
  60s+ — verify ZERO `/health` requests.

---

### Client Poll Window — Must Exceed Server Worst Case (Prevent Phantom Failures)

- **Version**: Iter79j.48
- **Created**: 2026-02-28T18:00:00Z
- **Last updated**: 2026-02-28T18:00:00Z
- **Change log**: initial entry.

**Problem it solves**: A frontend polling loop with a 5-minute cap
races a server whose legitimate worst case is longer (e.g. two-phase
pipeline: 300s Phase A + 5s drain + 180s Phase B ≈ 485s). The client
gives up first, throws "timed out", the server finishes 30s later and
writes a successful result — but the user sees a phantom failure and
the compute is wasted. Money AND trust burned.

**Prompt**:
> When adding a client-side polling loop for a long-running async
> server job, follow these rules:
>
> 1. **Compute the server's ACTUAL worst case** from all its timeout
>    knobs and stages. Write it down as a comment on the polling loop.
> 2. **Set the client budget to at least 1.25× the server worst case.**
>    In this project: server = 485s → client 200 × 3s = 600s (~1.24×
>    margin plus network jitter absorbed).
> 3. **Grant a bounded grace window** if the server heartbeat is still
>    fresh at the client's normal limit. Track `updated_at` (via a
>    `elapsed_ms` field on the status endpoint) and, if it advanced
>    within the last 30s, extend once by ~+120s. Do NOT extend
>    unconditionally — a stalled heartbeat means the worker died and
>    the grace window would just delay the failure.
> 4. **The client timeout error must NAME the actual budget** and
>    suggest an action: "did not complete within 10 minutes — the
>    server may still be finishing; check the estimate again in a
>    minute". Not "timed out after 5 minutes" when the client budget is
>    now 10.
> 5. **Update ALL poll loops** — main run, resume, rerun. It's easy to
>    fix one and leave the others racing at the old cap.

**Regression guard**:
- Manual: kick a long-running job (e.g. 8-photo AI Measure). Verify
  the client polls until either done or 10 min elapsed. If the server
  is heartbeat-fresh at 10 min, verify the +120s grace triggers with
  the busy stage showing "…(finishing…)".
- Manual: kill the backend mid-run (e.g. `sudo supervisorctl stop
  backend`) → verify the client stops polling within ~30s of stopping
  seeing heartbeat advances, doesn't grace-extend on a dead heartbeat.

---

### Deploy Secrets — Env Var Update Path (Emergent-Specific)

- **Version**: Iter79j.47
- **Created**: 2026-02-28T17:00:00Z
- **Last updated**: 2026-02-28T17:00:00Z
- **Change log**: initial entry.

**Problem it solves**: Documenting the empirically-verified path for
updating a deployed Emergent app's environment variables when the AI
Agent cannot find it and support gives multiple wrong click-paths.

**Prompt** (for team wiki / runbook, not for coding agent):
> **To update env vars on a deployed Emergent app WITHOUT shipping new
> code you can't (env-var-only apply doesn't exist — Save & Redeploy
> always ships preview code too)**:
>
> 1. Home tab → **Manage Deployments** → your app → **Secrets** tab.
> 2. Edit the value. Deployed secrets are shown as "Currently live" or
>    "Updated, not live yet".
> 3. Click **Save and Redeploy**. This ships the new env var AND the
>    current preview code together.
>
> **NOT the path**: clicking the deployed app card on Home, clicking
> "View Task" — both dead-end back to chat.
>
> **Rollback**: previously-deployed versions remain accessible from the
> same panel. Env vars persist across rollbacks but VERIFY after every
> rollback — support's docs explicitly warn about this.
>
> **Backup before Redeploy**: if the GitHub connect UI is broken on
> your account (empty dropdown, no Connect button), zip the preview
> workspace and serve it from `frontend/public/backups/` — the URL is
> `<REACT_APP_BACKEND_URL>/backups/<filename>`. Excludes to skip:
> `node_modules`, `.git`, `__pycache__`, `build`, `venv`, `.emergent`,
> logs, `backend/uploads`.

**Regression guard**:
- N/A — this is a runbook, not a code feature. Verified in production
  during 2026-02-28 key-rotation incident.

---

### Platform Health Probe + Admin Debug-Log-Tail (Deployment Diagnostics)

- **Version**: Iter79j.49
- **Created**: 2026-02-28T18:15:00Z
- **Last updated**: 2026-02-28T18:15:00Z
- **Change log**: initial entry.

**Problem it solves**: Two production diagnostics gaps discovered
during a live incident: (1) the platform hits `GET /health` (bare, no
`/api` prefix) every 2s as a liveness probe — a 404 makes the pod look
unhealthy and can trigger restarts. (2) The platform log viewer shows
only HTTP access lines; application `logger.info/warning/error` output
is invisible. During an incident we need to grep our own instrumented
log lines (e.g. `[ai-measure phase-A] photo N done in Nms`) but had no
way to reach them without shell access to the container.

**Prompt**:
> Add two diagnostics endpoints to the FastAPI backend.
>
> **1. Bare platform-probe endpoint `GET /health`**:
> - Lives OUTSIDE the `/api` prefix (`@app.get("/health")` on the app
>   object, NOT on the api_router). Do not gate with auth — platform
>   probes are unauthenticated.
> - Returns `{"status": "ok"}` with 200.
> - Do not add work here — must respond in <5ms.
>
> **2. Admin-gated debug-log-tail `GET /api/<domain>/debug-log-tail`**:
> - Attach a ring-buffer `logging.Handler` (deque with `maxlen=2000`)
>   to the ROOT logger BEFORE importing any router modules. Router
>   imports trigger module-level `logger.info` calls (e.g. key-routing
>   summaries) — attaching the handler after these imports means their
>   output never lands in the buffer.
> - Watch out for `logging.basicConfig(level=INFO)` calls in imported
>   modules — `basicConfig` is a no-op if handlers already exist, so
>   priming the root logger first is essential.
> - Endpoint accepts `?grep=<needle>[,<needle>]&lines=<N>` query
>   params. `grep` is case-insensitive substring; multiple terms
>   comma-separated are OR-combined. `lines` capped at buffer capacity.
> - Admin-only: check `user["role"]` against `{"owner", "admin",
>   "supplier_admin"}`. Return 403 otherwise.
> - **Ship for incident diagnostics, remove after resolution.** Add a
>   comment at the top of the endpoint stating this is temporary.
> - Import the ring buffer with a lazy `from server import LOG_RING`
>   inside the endpoint to avoid circular import at module load.
>
> **Response shape**:
> ```
> {
>   "count": <returned line count>,
>   "total_in_buffer": <total records in ring>,
>   "grep": "<echoed query>",
>   "lines": ["<formatted log line>", ...]
> }
> ```
>
> **Formatter**:
> ```
> logging.Formatter(
>   "%(asctime)s %(levelname)s %(name)s: %(message)s",
>   datefmt="%Y-%m-%dT%H:%M:%SZ",
> )
> ```
>
> **Not to do**:
> - Do NOT tail a log FILE (`/var/log/supervisor/backend.err.log`).
>   Log file paths differ between preview and deployed environments;
>   in-memory ring buffer works uniformly.
> - Do NOT store secrets in the buffer. If you log token values
>   anywhere, redact BEFORE logging, not in the endpoint.

**Regression guard**:
- Manual: `curl <base>/health` → 200 `{"status":"ok"}`, no auth
  needed, sub-5ms.
- Manual: after backend restart, `curl -b <admin cookie>
  <base>/api/measure/ai-measure/debug-log-tail?grep=key-routing` →
  returns at least the startup key-routing log line, confirming
  the ring buffer captured module-import-time logging.
- Manual: `curl -b <non-admin cookie>` → 403.

---

### AI Vision — Payload Shrink + Concurrency Cap (Proxy Serialization Workaround)

- **Version**: Iter79j.50
- **Created**: 2026-02-28T19:45:00Z
- **Last updated**: 2026-02-28T19:45:00Z
- **Change log**: initial entry.

**Problem it solves**: The upstream LLM proxy (LiteLLM behind
`emergentintegrations.LlmChat`) serializes concurrent large-payload
`send_message` calls even though small-payload calls parallelize fine.
Empirically observed: 3 parallel calls with `max_tokens=4000` +
3000×4000 JPEG take 185s wall clock (ratio 3.0 = serial); 3 parallel
calls with tiny payloads take 4.89s wall clock (ratio 1.00 = truly
parallel). Also: `asyncio.wait_for(chat.send_message(), timeout=N)`
does NOT cancel in-flight calls — they run to natural completion,
making all client-side timeouts decorative. `t.cancel()` on a running
task has no effect either.

Without this workaround, 8-photo AI Measure runs take 400-500s
**per photo** (~8min/photo) when the proxy is serializing, blowing past
any client polling window.

**Prompt**:
> When a vision-heavy pipeline dispatches N concurrent
> `emergentintegrations.LlmChat` calls, apply both of these before
> the dispatch:
>
> **1. Aggressive per-photo shrink**:
> - Add a helper `_shrink_for_phase_a(raw_bytes, max_dim=1600,
>   jpeg_q=80)` that PIL-resizes each photo to a max long-edge of
>   1600px and re-encodes JPEG q80. Contractor phone photos are
>   typically 3000-4500px and 3-5 MB — this yields ~10-50 KB per
>   photo (100-300× reduction).
> - Wrap in try/except and fall back to any existing looser compressor
>   (`_compress_for_claude` with 5.5 MB cap) so a broken image doesn't
>   kill the run.
> - Log per-photo before/after: `logger.info("[phase-A] photo N shrunk
>   3000x4000 → 1200x1600 (4200000 → 47000 bytes, 0.011x)")`. This is
>   essential diagnostic evidence — proves the shrink actually ran and
>   quantifies the reduction.
> - Env-configurable: `<APP>_PHASE_A_MAX_DIM` (default 1600),
>   `<APP>_PHASE_A_JPEG_Q` (default 80).
>
> **2. Concurrency semaphore**:
> - Cap concurrent LLM calls with `asyncio.Semaphore(N)` inside the
>   per-photo coroutine, NOT around `asyncio.create_task`. The
>   semaphore must be entered AFTER task creation so:
>   - `asyncio.wait` sees each task as immediately scheduled.
>   - Each task's per-photo timer starts only when the semaphore
>     grants entry, not while waiting in the queue (otherwise queue
>     time counts against the timeout budget).
> - Default N=2 matches the empirically-observed proxy concurrency
>   sweet spot. Env-configurable: `<APP>_PHASE_A_CONCURRENCY`.
> - Note: this is a WORKAROUND for a proxy-side bug. File a support
>   ticket with the reproduction script (see the "empirical evidence"
>   section below). When the proxy is fixed, raise N back to `len(photos)`.
>
> **Empirical evidence** (paste in the support ticket):
> ```python
> # Small calls: wall clock 4.89s, ratio 1.00 (parallel)
> tasks = [chat.with_params(max_tokens=5).send_message(text_only) ...]
> # Large calls: wall clock 185s, ratio 3.0 (serial)
> tasks = [chat.with_params(max_tokens=4000).send_message(big_image) ...]
> # asyncio.wait(tasks, timeout=2) returned at 185.21s (should be 2s)
> # t.cancel() on pending tasks had zero effect — they ran to completion
> ```

**Regression guard**:
- Manual: kick an 8-photo run with the semaphore active. Watch the
  backend log — the `photo N start` lines should batch (2 at a time,
  not 8 at once). Total wall clock should be roughly
  ceil(N/concurrency) × per-photo-latency.
- Manual: `curl /api/measure/ai-measure/debug-log-tail?grep=shrunk` —
  should return N `photo M shrunk WxH → wxh` lines confirming every
  photo was downscaled.
- Follow-up: once Emergent fixes the proxy serialization bug, raise
  `AI_MEASURE_PHASE_A_CONCURRENCY` back to a value ≥ N-photos and
  confirm wall clock drops to ~1× per-photo latency.


---

# Support Datapoint — 2026-07-06 03:33 UTC — Emergent LiteLLM proxy: instant Phase B 502 (not slow, not timeout)

**Estimate**: `673707d5-9b7e-4d8f-8eaf-63c86820f611`
**Target Run**: `22af2eb2ad784c7bbd662222e16001ab` — 8 photos, Phase A extractions intact, model `claude-fable-5`.
**Endpoint invoked**: `POST /api/measure/ai-measure/reconcile-only/{run_id}` (text-only Phase B, no image payload).
**Observed behavior**: proxy hard-rejected the reconcile request with `litellm.BadGatewayError: BadGatewayError: OpenAIException - Error code: 502` — response arrived within seconds, not the ~900s hang seen in Iter 79j.50/51.

**Why this matters**:
- Prior 79j.50 failure was a Phase B **hang → 502 after 901s** (long-tail latency, consistent with a proxy backend that eventually gave up).
- This datapoint is a Phase B **instant 502** (fast rejection). The proxy is *actively refusing* text-only reconciliation on a stable estimate whose 8-for-8 Phase A extractions are already persisted.
- Combined with 79j.50/51's evidence, the LiteLLM proxy now exhibits **at least three distinct failure modes** on the same Universal Key routing anthropic/claude-fable-5:
    1. Silent serialization → long-tail hang → eventual 502 (79j.44/45).
    2. Payload-driven 502 after ~900s hang (79j.50/51).
    3. **Instant 502 hard-rejection on text-only Phase B (79j.52 → this datapoint).**
- Support has already confirmed in writing that **no documented concurrency, payload-queueing, or cancellation behavior exists** for the Universal Key path (see PRD.md → "Standing Justification for Post-Validation Direct-API Rewrite"). This datapoint is the third failure mode to attach to that thread.

**What we did NOT do**:
- Retry the reconcile after the 502.
- Fire any further reconcile attempts.
- Change the model or the proxy routing.
- (Per user gate: no further calls until sort fix + read-only Resume land — both landed in 79j.53.)

**What we DID do (79j.53)**:
- Status-aware sort on `latest-for-estimate` so failed retries never bury successful reconciliations.
- Session-autosave guard (both debounced + close-time) that refuses to persist a `_reconciliation_error` preview.
- Historic-error banner framing on Resume — "Prior reconciliation failed", "Restored from a previous session — no fresh call was made", origin badge, elapsed suppressed. Contractors will no longer misread a resumed failed session as a fresh instant-502.
- One-shot direct DB repoint of the estimate's session back to Run 3.

**Action item for support ticket**: append this timestamp + error string as evidence #3 alongside the 79j.50 901s hang + 79j.51 reconcile 502. All three occurred on the same key/model/route with no code change on our side — the proxy's behavior is unstable, not our payload.

---

# Meta

**Convention going forward**: after every feature/build the main agent
appends a new entry OR updates an existing one (via the `Change log`
section). Prompts are pinned to iteration numbers matching the code
comments so a grep of the codebase (`grep -rn "Iter79j.49" backend/`)
reveals every touch site.

**Backfill status**: entries below Iter79j.44 are NOT included. Older
features (WCAG AA pass, theme system, customer-contact fields, soft
validation, auto-populate on Create, two-phase pipeline base build,
etc.) are documented in `PRD.md` but not yet turned into portable
prompts. Backfill on request.
