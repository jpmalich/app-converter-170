# BACKLOG — PINNED PRIORITY LIST (Howard ruled 2026-08-13)

**THIS ORDER IS FIXED.** It must not be reordered during plan
restatements or long sessions. If any agent believes an item should
move, they SAY SO AND WHY — they never quietly reorder. This file is
the register; a plan restatement must pull from here, verbatim.

Ruled precedent: send-10 amendment (items 1+2), plus the earlier
evidence-or-null quiet-drop from a truncated send. The rulings
register did not catch the position-5 demotion (send-11 handback plan
sitting at position 4→backlog) because the demotion happened in a
plan summary, not the register. This file closes that gap.

## PINNED ORDER
 1. **Demote-All on shared-source quotes** — `_one_source_one_path_guard`
    demotes EVERY consumer of a shared (page,from) quote. If one must
    survive, mark it UNVERIFIED, never AI-READ. Send-10 alphabetical
    winner is dead. STATUS: **✓ LANDED 2026-08-13 (SEND-11 item 1)**.
 2. **MISREAD tier** — a third tier between FABRICATED and UNVERIFIED.
    A quote absent from the page whose closest OCR run is one
    character-edit away (`_del1`/`_sub1`) is a transcription typo, not
    an invention. Name the real string on the card; kill the value for
    money. STATUS: **✓ LANDED 2026-08-13 (SEND-11 item 2)**.
 3. **OCR-coverage weighting on FABRICATED** — every FABRICATED record
    carries `evidence_strength` (`"strong"` when the page's normalised
    OCR char count > 300, `"weak"` otherwise). Poor coverage + no hit
    is different evidence than dense coverage + no hit — the rail
    badge says so. STATUS: **✓ LANDED 2026-08-13 (SEND-11 item 3)**.
 4. **P0 chips + the three misfiled surfaces onto JobInfoPanel** —
    add `SurfaceAccessChip` to the five existing conditional surfaces
    from the baseline burn-down report; relocate the three misfiled
    dialogs (vinyl profile picker, accent injection, model comparison
    history) out of run dialogs onto `JobInfoPanel`. STATUS: NOT
    STARTED.
 5. **Material Zone Layer** — POSITION 5 IS FIXED. NOT BACKLOG.
    - Original elevation PDF pages are the canvas (not synthetic
      sheets).
    - User-adjustable polygons updating THE SAME structured takeoff
      (never a parallel data model).
    - 3/16" = 1'-0" scale drives dimensions.
    - `qty_src == "human"` survives every rebuild (existing hover.py
      guard is the shield — the test pin is the contract).
    - Simplified synthetic sheets are kept as a secondary summary
      view.
    Cost report: `memory/material_zone_layer_cost_2026-08-13.md` —
    MUV = ~4 sessions. Awaiting the ruling before start.
    STATUS: COSTED, NOT STARTED.
 6. **Verdict-and-Triage card** — ranking, top-level verdict,
    reconcile/contradict/unread grouping on the blueprint card.
    STATUS: NOT STARTED.
 7. **Ledger UI on the Blueprint card** — expose the backend seam
    ledger events on the Blueprint UI card so the removals the ledger
    already records reach the reader. STATUS: NOT STARTED.
 8. **EST-040221 orientation flip** — the eaves landing on 39' walls
    instead of 58' walls. Instrument is live (`eave_rake_orientation`
    fires loud); root cause of the FLIP itself still unattributed.
    STATUS: INSTRUMENT LIVE, ROOT CAUSE NOT ATTRIBUTED.
 9. **Reconciliation (bar c)** — HELD until Howard pulls the invoice
    sets. STATUS: HELD.

## RULES OF ENGAGEMENT
 - The register is verbatim. Restatements pull from here, they do
   not paraphrase.
 - If an item should move, SAY SO AND WHY. Do not move it.
 - "Backlog" is a class of NON-ordered work. Numbered items above are
   NOT backlog — they are the ordered queue. Do not conflate.
 - Every ✓ LANDED entry must name the session (send number + date) so
   the trail is walkable.

## PURITY (do not prompt harder — these are still held)
 - Gable over-count 6 vs 4.
 - Porch 195 vs 99.
 - Corners 12/8 vs 8/4.
 - Nothing applies to EST-886440. Integral-J stays ON.
