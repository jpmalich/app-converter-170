# OPTIMISTIC-UI AUDIT (Howard ruled 2026-08-11 send-4)

Ruled ruling (verbatim):
> A WRITE THAT IS REFUSED MUST SAY SO. No optimistic local state
> survives a non-2xx response. Roll it back and surface the refusal in
> words — "this estimate is protected; nothing was saved" — same
> contract as the SurfaceAccessChip: name the state and the way out.

Howard's send-4 also ordered: for every optimistic update, record
**WHAT THE USER SEES WHEN THE SERVER REFUSES.** "Silently reverts" is
nearly as bad as "paints success"; the census must name which
contractors would think a change saved when it did not.

Below: every optimistic UI update (local state mutated BEFORE the
server's response) in the frontend, walked from the automated scan on
2026-08-11. `pattern_local_write` matched `update({`, `setEst(`,
`setLines(`, `setLocal*(`, `setValue(`, `setDraft`, `setBanner(`,
`setPending`; `pattern_api_write` matched `await api.put/post/patch/
delete`. Window: 25 lines look-back per API-write line. 76 API-write
sites scanned; 6 flagged as optimistic (5 paint-over-refusal, 1
paint-and-silently-reverts).

## §1 · CLASS TABLE

Refusal behaviour column is Howard's ask: what does the contractor see?
- **PAINTS SUCCESS**: local state stays changed; toast may or may not
  fire; contractor believes the write landed.
- **SILENTLY REVERTS**: local state may re-fetch or re-render later and
  quietly restore truth — no words on refusal.
- **NAMES THE REFUSAL**: rollback + a persistent surface chip / toast
  that describes what happened and why.

| # | Site | Optimistic field(s) | On non-2xx today | Class | Action |
|---|------|--------------------|--------------------|-------|--------|
| W1 | `BlueprintMeasureButton.jsx:480` (Apply flow) | `lines`, `vero_openings`, `mezzo_openings`, `hover_measurements` | Local state carries applied read; toast says "Apply failed" but merged lines remain visible until page reload. Contractor may re-tap Apply, may edit merged lines, may generate a quote from painted-over-refusal state. | **PAINTS SUCCESS** | route through `writeThrough`; rollback on 423; persistent chip "estimate is protected — apply was refused, nothing was saved" |
| W2 | `SettingsRow.jsx:141` (`updateWastePct`) | `waste_pct` chip + recomputed `lines` | Waste field visually snaps to new %; recomputed line quantities stick. `save()` refusal handled silently (console.warn only). On refusal, waste chip AND line quantities are wrong until refresh. | **PAINTS SUCCESS** | route through helper; rollback both waste_pct AND recomputed lines |
| W3 | `HoverImportButton.jsx:238` | `waste_pct: 0` reset | HOVER import is a POST /estimates/hover-import (typically 200/201). If it 4xx's, waste stays 0 locally, contractor believes waste was reset. | **PAINTS SUCCESS** | route through helper; rollback waste_pct on refusal |
| W4 | `AIMeasureButton.jsx:1047` | `setPendingSessionMeta(null)` | Sets local meta to null BEFORE `await api.delete`. On delete refusal, session appears gone in UI but backend still has it. Any subsequent revive-session guess would key off missing meta. | **PAINTS SUCCESS** (session gone) | route through helper; rollback the meta clear |
| W5 | `ISSEstimateEditor.jsx:255` (in `applyHoverLines`) | `setEst((prev) => ({ ...prev, lines }))` before `await api.put(/estimates/{id})` | ISS applied-lines write. On 423 (protected estimate), local lines stay updated; contractor sees "applied" line set even though the server did not persist. Same class as W1 but on the ISS door. | **PAINTS SUCCESS** | route through helper |
| W6 | `SettingsRow.jsx:99` (`saveSpec`, inside `try` block) | `update({ lines: data.lines })` from the awaited response | Update happens AFTER the await resolves with data. If the await throws, the local update does NOT run. | **RECONCILES** (safe pattern — model for other sites) | no action; keep as-is (this is the target shape) |

## §2 · CLASS-LEVEL PATTERNS

Two distinct classes emerged:

**Class Alpha — "optimism before await."** W1, W2, W3, W4, W5. Local
state mutated before the API call fires. The pattern reads:
```jsx
update({ someField });     // ← optimistic
await api.put(...);        // ← may 423
```
If the API refuses, the local mutation stays. Toast (if any) is a
40-ms flash; the surface itself does not roll back. **This is the class
that made Howard rule from a false state for two turns.**

**Class Beta — "post-response update."** W6. The pattern reads:
```jsx
const { data } = await api.post(...);      // ← wait for the server
if (Array.isArray(data?.lines))            // ← use the answer
  update({ lines: data.lines });
```
This is the shape the helper enforces universally. On refusal (thrown
exception), the `.then` branch never runs, so no optimistic state ever
paints. **Class Beta is the target.**

## §3 · THE HELPER CONTRACT

`writeThrough` (new, ships in the next commit) accepts an optimistic
patch, a rollback (typically the inverse of the patch), a server call,
and a refusal-chip renderer. It runs:

1. Apply the optimistic patch (or none — the caller may opt out of
   optimism for slow-but-safe writes).
2. Fire the API call.
3. On 2xx: keep the patch, optionally reconcile from the response.
4. On non-2xx: **run the rollback**, then render the refusal chip
   naming the STATE and the WAY OUT.
5. On network error: rollback + generic refusal chip; caller decides
   whether to retry.

No component that mutates protected estimate state may bypass this
helper. The detector (see §4) fails the build on any component that
mutates local state within 25 lines above `api.put/post/patch/delete`
without importing `writeThrough`.

## §4 · REGISTRY + DETECTOR

`frontend/src/lib/optimistic_write_registry.js` — every optimistic
write declares itself: `{ id, component_path, fields, rollback,
refuse_chip_testid }`. The detector (pytest) walks every JSX/JS file:
- Finds every "local write in the 25 lines before `api.put/post/patch/
  delete`."
- Fails the build unless the file imports `writeThrough` OR the site
  is registered as UNCONDITIONAL_SAFE (e.g., post-response updates
  wrapping the await's `data`, which are Class Beta by construction).

Same shape as the seam registry / TTL_REAPER_REGISTRY / schema-consumer
detector — all three caught something on first run.

## §5 · THE INVERSE-INSTRUMENT NAMED

Every seam instrument built this month catches something REMOVED
(reaped runs, dropped fields, unlocated sizes, silenced consistency
flags) or INVENTED (hallucinated planes, fabricated dormers,
plane-gables without wall attribution). **The refuse-must-say-so class
is the INVERSE:** the AI/backend didn't remove anything; the FRONTEND
reported a write that never happened.

That is a new class of silent failure. The instrument that catches it
lives on the client (helper + registry + detector) because that is
where the local optimism lives. Backend cannot fix this — a server
that returns 423 is doing its job.

## §6 · ORDER (Howard ruled)

  doc → helper → registry → detector

  - Doc: this file (shipped).
  - Helper: `frontend/src/lib/write_through.js`.
  - Registry: `frontend/src/lib/optimistic_write_registry.js`.
  - Detector: `backend/tests/test_optimistic_write_detector_2026_08_11.py`
    (build fails if any optimistic write is unregistered and does not
    route through the helper).

## §7 · PURITY (permanent)

The audit is EVIDENCE. Never a fallback, never a default. Every
optimistic site named above is anchored by a file path + line number
from the automated scan output — no site is here because someone
guessed. If a site is missed by the scan (e.g., a dynamic dispatch
through an event bus), the detector fails the build the next time it
runs. The refusal chip's copy is derived at runtime from the actual
server response (`err.response.data.detail`), never a canned string.
