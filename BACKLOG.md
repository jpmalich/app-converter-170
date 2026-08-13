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

## CURRENT ORDER (Howard 2026-08-13 pro-quotes reply 4)
 1. **P0 chips (five) + tombstone inversion + skip-reason lint
    pin + the three misfiled surface moves** — ✓ LANDED
    2026-08-13:
    - **Five P0 chips ✓ LANDED** (pro-quotes reply 3).
    - **Tombstone inversion ✓ LANDED**
      (`test_material_overrides_are_structurally_impossible`).
    - **Skip-reason-class lint pin ✓ LANDED** (registry +
      AST-walking census; every skip in the suite carries a
      registered class tag).
    - **Three misfiled surface moves ✓ COMPLETE**:
        - Move A (Run comparison history → tile-chip) ✓ LANDED
          this session — `RunComparisonChip.jsx` on JobInfoPanel
          Blueprint tile.
        - Move B (Vinyl profile picker → JobInfoPanel spec area)
          already accomplished 2026-08-09 (SidingProfileChip
          mounts at estimate scope in EstimateEditor.jsx:479 with
          its own picker dialog); chip copy updated this session
          to name the true way out.
        - Move C (Accent injection → JobInfoPanel accents panel)
          already accomplished 2026-08-09
          (PerElevationBreakdownCard mounts at estimate scope in
          EstimateEditor.jsx:485 when hover_measurements exist);
          chip copy updated this session to name the true way out.
    STATUS: **✓ COMPLETE**.
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
    Scope document: `memory/linear_edges_walk_ready_scope_2026-08-13.md`
    (AMENDED 2026-08-13 pro-quotes reply 3: `render_status` beside
    every legend quantity moves INTO S3; S4 is now on-drawing
    hatching only. A legend with bare numbers is refused.).
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
 - **Position 1 COMPLETE (send-11 pro-quotes reply 4)** — five
   P0 chips, tombstone inversion into positive shape assertion,
   skip-reason-class lint pin (registry + AST census), Move A
   (RunComparisonChip.jsx on JobInfoPanel Blueprint tile). Moves B
   and C already accomplished 2026-08-09 (chip copy updated to
   name the correct way out). LANDED 2026-08-13.
 - **Five P0 chips (position 1 half-1)** — `SidingProfileChip`,
   `PhotoFillinGateBanner`, `OpeningsReviewCard`,
   `CompositionTrace`, `FinalJobSurface` each render a
   `SurfaceAccessChip` in the branch that used to `return null`
   silently. LANDED 2026-08-13 (SEND-11 pro-quotes reply 3).
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
 - **Baseline five skips named** —
   `memory/baseline_five_skips_named_2026-08-13.md`. One
   tombstone (iter-6 obsolete pin) + four cadence-gated ingress
   smoke tests. Recommendations report-only: invert the
   tombstone into an assertion, and add a `skip-reason-class` pin
   requiring every `pytest.skip` reason to name its class.
 - **Three misfiled-surface moves scope** —
   `memory/three_misfiled_surfaces_move_scope_2026-08-13.md`.
   Position 1 second-half; walk-ready.
 - **Linear-edges + two-key legend + honesty layer —
   session-by-session walk-ready scope** (AMENDED per
   pro-quotes reply 3):
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
