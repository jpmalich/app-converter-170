# BACKLOG — PINNED PRIORITY LIST
Ruled by Howard. Updated 2026-08-13 (pro-quotes reply 2).

**THIS ORDER IS FIXED.** It must not be reordered during plan
restatements or long sessions. If any agent believes an item should
move, they SAY SO AND WHY — they never quietly reorder. This file is
the register; a plan restatement must pull from here, verbatim.

Ruled precedent: (1) evidence-or-null vanishing from a truncated
send; (2) send-10 amendment (items 1+2) reordering; (3) Material
Zone Layer sliding from position 5 to "backlog" in a plan
restatement; (4) linear edges being placed WITH MUV in a
recommendation Howard overrode ("I have never used an editable
overlay ... four sessions of linear-edge work built on top of it
is wasted" if the interaction model is wrong). Every demotion or
combination happened in a PLAN SUMMARY, never in the register
itself. This file is the closed loop.

## CURRENT ORDER (Howard 2026-08-13 pro-quotes reply 2)
 1. **P0 chips (five) + the three misfiled surfaces onto
    JobInfoPanel** — add `SurfaceAccessChip` to the five existing
    conditional surfaces from the baseline burn-down report;
    relocate the three misfiled dialogs (vinyl profile picker,
    accent injection, model comparison history) out of run
    dialogs onto `JobInfoPanel`. STATUS: NOT STARTED.
 2. **MATERIAL ZONE LAYER — MUV. Then Howard walks it.** — ~4
    sessions. Original elevation PDF pages as canvas;
    user-adjustable polygons updating the SAME structured takeoff;
    3/16" = 1'-0" scale; `qty_src == "human"` survives every
    rebuild; simplified synthetic sheets kept as secondary summary
    view. MUV excludes snapping / PDF export / multi-user
    (correct per Howard).
    Cost report: `memory/material_zone_layer_cost_2026-08-13.md`.
    STATUS: SCOPED + APPROVED, NOT STARTED.
    **THE 5-POINT WALK BAR** (Howard's words): "I open a real
    elevation page. I draw or drag a polygon over a wall. The
    square footage changes. The material line changes with it.
    It is marked as MY entry, not the app's. It is still there
    after a rebuild." If all five are true, MUV passes and the
    increment starts.
 3. **LINEAR EDGES + TWO-KEY LEGEND + HONESTY LAYER** — scoped
    NOW so it starts the DAY the MUV walk ends. ~4 sessions.
    Scope document: `memory/linear_edges_walk_ready_scope_2026-08-13.md`.
    Session-by-session plan is walk-ready; no scoping gap.
    STATUS: SCOPED, WAITING FOR MUV WALK TO END.
 4. **ENVELOPE[T] PROTOTYPE on the ledger endpoint** — Howard
    ruled prototype-only, after MUV. Not the ~2.5-session refactor
    yet; prove `Envelope[T]` on the ledger endpoint we just
    fixed, verify the contract holds against a real path, report,
    and Howard rules on the rest. Feasibility report:
    `memory/detector_inversion_proposal_2026-08-13.md`.
    STATUS: NOT STARTED (comes after MUV).
 5. **VERDICT-AND-TRIAGE CARD** — ranking, top-level verdict,
    reconcile/contradict/unread grouping on the blueprint card.
    STATUS: NOT STARTED.
 6. **LEDGER UI on the Blueprint card** — expose the backend
    seam ledger events on the Blueprint UI card so the removals
    the ledger already records reach the reader. STATUS: NOT
    STARTED.
 7. **EST-040221 orientation flip** — the eaves landing on 39'
    walls instead of 58' walls. Instrument is live
    (`eave_rake_orientation` fires loud); root cause of the FLIP
    itself still unattributed. STATUS: INSTRUMENT LIVE, ROOT
    CAUSE NOT ATTRIBUTED.
 8. **RECONCILIATION (bar c)** — HELD until Howard pulls the
    invoice sets. STATUS: HELD.

## LANDED, IN ORDER OF SHIP
 - **Demote-All on shared-source quotes** — `_one_source_one_path_guard`
   demotes every consumer of a shared (page,from) quote.
   LANDED 2026-08-13 (SEND-11 item 1).
 - **MISREAD tier** — a third tier between FABRICATED and
   UNVERIFIED. LANDED 2026-08-13 (SEND-11 item 2).
 - **OCR-coverage weighting on FABRICATED** — `evidence_strength`
   `"strong"`/`"weak"` on every FABRICATED record. LANDED
   2026-08-13 (SEND-11 item 3).
 - **Ledger truncation honesty** — `.limit(200)` replaced with
   paginated response naming `total`, `truncated`,
   `truncation_notice`; seam `protected_ledger_paginated`
   registered. LANDED 2026-08-13 (SEND-11 pro-quotes reply item 1).
 - **Five new skips retired** — the five HTTP pins in
   `test_send11b_...` that skipped because the fixture hardcoded
   `127.0.0.1:8001` + `Passw0rd!` are now wired to the shared
   `api_base.BASE_URL` + `creds_for_tests.TEST_PASSWORD`; every
   pin RUNS in the same env that runs `test_guard_extension` to
   green. Diagnosis:
   `memory/five_new_skips_diagnosis_2026-08-13.md`. LANDED
   2026-08-13 (SEND-11 pro-quotes reply 2, "either it runs or
   it does not count").

## REPORT ONLY, AWAITING RULINGS (no build)
 - **Linear-edges + two-key legend + honesty layer — session-by-
   session walk-ready scope**:
   `memory/linear_edges_walk_ready_scope_2026-08-13.md`. Starts
   the day the MUV walk ends.

## RULES OF ENGAGEMENT
 - The register is verbatim. Restatements pull from here, they
   do not paraphrase.
 - If an item should move, SAY SO AND WHY. Do not move it.
 - "Backlog" is a class of NON-ordered work. Numbered items above
   are NOT backlog — they are the ordered queue. Do not conflate.
 - Every ✓ LANDED entry names the session so the trail is walkable.
 - Recommendations that Howard overrides get RECORDED with the
   override reason, so the demotion never happens again the same
   way (see the linear-edges precedent: recommendation was "ride
   with MUV", override was "walk it first — early looks always
   find what tests do not").

## PURITY (do not prompt harder — these are still held)
 - Gable over-count 6 vs 4.
 - Porch 195 vs 99.
 - Corners 12/8 vs 8/4.
 - Nothing applies to EST-886440. Integral-J stays ON.
