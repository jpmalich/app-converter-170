# BACKLOG — PINNED PRIORITY LIST
Ruled by Howard, updated 2026-08-13 (pro-quotes reply).

**THIS ORDER IS FIXED.** It must not be reordered during plan
restatements or long sessions. If any agent believes an item should
move, they SAY SO AND WHY — they never quietly reorder. This file is
the register; a plan restatement must pull from here, verbatim.

Ruled precedent: (1) evidence-or-null vanishing from a truncated send;
(2) send-10 amendment (items 1+2) reordering; (3) Material Zone Layer
sliding from position 5 to "backlog" in a plan restatement. Each
demotion happened in a PLAN SUMMARY, never in the register itself.
This file is the closed loop.

## CURRENT ORDER (Howard 2026-08-13 pro-quotes reply)
 1. **LEDGER TRUNCATION — fix properly, then the stamp** — the
    `/api/estimates/{eid}/protected-ledger` endpoint returns `total`,
    `showing`, `truncated`, `truncation_notice`, and paginates via
    `?page=`/`?page_size=`; the `.limit()` shape is registered as
    `protected_ledger_paginated` seam. STATUS: **✓ LANDED 2026-08-13**.
    Full suite: **2322 passed, 10 skipped**.
 2. **P0 chips (five) + the three misfiled surfaces onto
    JobInfoPanel** — add `SurfaceAccessChip` to the five existing
    conditional surfaces from the baseline burn-down report;
    relocate the three misfiled dialogs (vinyl profile picker,
    accent injection, model comparison history) out of run dialogs
    onto `JobInfoPanel`. STATUS: NOT STARTED.
 3. **MATERIAL ZONE LAYER — MUV** — **APPROVED AS SCOPED**
    (pro-quotes reply, section 3). ~4 sessions.
    - Original elevation PDF pages are the canvas (not synthetic
      sheets).
    - User-adjustable polygons updating THE SAME structured takeoff.
    - 3/16" = 1'-0" scale drives dimensions.
    - `qty_src == "human"` survives every rebuild.
    - Simplified synthetic sheets are kept as secondary summary view.
    - MUV excludes snapping, PDF export with overlays, multi-user
      editing (correctly, per Howard 2026-08-13).
    Cost report: `memory/material_zone_layer_cost_2026-08-13.md`.
    STATUS: SCOPED + APPROVED, NOT STARTED.
    ADJACENT INCREMENT (COSTED, AWAITING RULING): linear edges +
    two-key legend + honesty layer. ~4 sessions on top of MUV; ~7
    sessions combined. Cost report:
    `memory/material_zone_layer_linear_edges_cost_2026-08-13.md`.
    Howard's decision — ride with MUV or ship immediately after —
    pending.
 4. **VERDICT-AND-TRIAGE CARD** — ranking, top-level verdict,
    reconcile/contradict/unread grouping on the blueprint card.
    STATUS: NOT STARTED.
 5. **LEDGER UI on the Blueprint card** — expose the backend seam
    ledger events on the Blueprint UI card so the removals the
    ledger already records reach the reader. STATUS: NOT STARTED.
 6. **EST-040221 orientation flip** — the eaves landing on 39' walls
    instead of 58' walls. Instrument is live
    (`eave_rake_orientation` fires loud); root cause of the FLIP
    itself still unattributed. STATUS: INSTRUMENT LIVE, ROOT CAUSE
    NOT ATTRIBUTED.
 7. **RECONCILIATION (bar c)** — HELD until Howard pulls the
    invoice sets. STATUS: HELD.

## LANDED, IN ORDER OF SHIP
 - **Demote-All on shared-source quotes** — `_one_source_one_path_guard`
   demotes every consumer of a shared (page,from) quote. LANDED
   2026-08-13 (SEND-11 item 1).
 - **MISREAD tier** — a third tier between FABRICATED and
   UNVERIFIED. Quote absent from the page whose closest OCR run is
   one character-edit away (`_del1`/`_sub1`) is a transcription
   typo, not an invention. LANDED 2026-08-13 (SEND-11 item 2).
 - **OCR-coverage weighting on FABRICATED** — every FABRICATED
   record carries `evidence_strength` (`"strong"` when the page's
   normalised OCR char count > 300, `"weak"` otherwise). LANDED
   2026-08-13 (SEND-11 item 3).
 - **Ledger truncation honesty** — `.limit(200)` replaced with
   paginated response naming `total`, `truncated`,
   `truncation_notice`; seam `protected_ledger_paginated`
   registered. LANDED 2026-08-13 (SEND-11 pro-quotes reply item 1).

## REPORT-ONLY, AWAITING RULINGS (no build)
 - **Detector inversion proposal** —
   `memory/detector_inversion_proposal_2026-08-13.md`. Feasible;
   worth it; ~2.5 sessions to generalise the boundary envelope
   pattern the ledger fix just proved. Awaits ruling.
 - **Material Zone Layer LINEAR-EDGES + legend increment cost** —
   `memory/material_zone_layer_linear_edges_cost_2026-08-13.md`.
   ~4 sessions on top of MUV; recommendation is ride with MUV.
   Awaits ruling.

## RULES OF ENGAGEMENT
 - The register is verbatim. Restatements pull from here, they do
   not paraphrase.
 - If an item should move, SAY SO AND WHY. Do not move it.
 - "Backlog" is a class of NON-ordered work. Numbered items above
   are NOT backlog — they are the ordered queue. Do not conflate.
 - Every ✓ LANDED entry names the session so the trail is walkable.

## PURITY (do not prompt harder — these are still held)
 - Gable over-count 6 vs 4.
 - Porch 195 vs 99.
 - Corners 12/8 vs 8/4.
 - Nothing applies to EST-886440. Integral-J stays ON.
