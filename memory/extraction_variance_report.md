# EXTRACTION VARIANCE REPORT — fresh red-house run vs fixture run (same house)
Report only, no code. 2026-07-24.
FRESH: run 92e4d20a… on EST-644081 (created 20:04 UTC) — dormer ft² 0, dormer
windows on wall planes (phantom W1×W2 collision), left 55 / right 45.
FIXTURE: run c2002212… — 2 shed dormers (left 15 ft, right 15 ft) with faces,
knees, on_dormer windows (3), left 75.

## 1. Prompt-path: IDENTICAL — ruled out
Both runs carry the same `prompt_hash cbcb392fc94104fa`, same model choice
(claude-fable-5), same photo_count (8), same exposure anchor (3.75"), same
Deep Dormer Scan setting (False on both). Whatever diverged, it was NOT the
prompt or model path. (Footnote: the fresh run has a
`reconcile_only_retry_at 20:22` — a Phase-B-only retry 18 min after launch;
same prompt hash, so a re-reconcile of the same Phase A evidence.)

## 2. Photo-set differences: LARGE — the evidence
Same 8-angle protocol, materially different capture + annotation quality:
  a. LEFT-WALL REFERENCE, WRONG PLANE (the smoking gun for the low score):
     fresh photo 3 (LEFT) carries a 180" wall ref; Phase A itself reported
     "The ref banner appears to lie over the roof monitor plane, not the
     main wall plane" and set `eave_scale_cross_plane = true`. The fixture's
     left photo carried a 444" FULL-WALL ref (the dormer width was later
     read against that same 444" anchor). Fresh left ended
     `direct_single_reading @55` vs fixture `@75`.
  b. WINDOW-STYLE PINS: the fixture set had contractor yellow pins on
     photos 1/3/5 — photo 3 (LEFT) alone had 5 pinned windows, which forces
     per-window enumeration exactly where the dormer windows live. The
     fresh set had ZERO pins anywhere.
  c. RIGHT ELEVATION NEVER SQUARE-ON (fresh): the photo tagged RIGHT was
     read by Phase A as front-right ("elevated camera angle… oblique") —
     the fresh run has TWO front-right reads and no usable right
     elevation; right wall fell to `assumed_symmetric @45`. (The fixture
     set was also weakest on the right — @50 — its 8th photo carried no
     elevation tag at all.)

## 3. The dormer miss is a CLASSIFICATION flip, not blindness
Phase A per-photo outputs, fresh run: `dormers_observed_count = 0` on ALL 8
photos — but the model SAW the structure. Its own Phase B note:
  "the raised structure above the main roof (photos 1, 2, 3, 5, 6, 7) is
   consistently described as a raised half-story / roof monitor with its
   own eave walls and elevated corner posts, not a dormer; its ~4.5 ft
   pop-up wall and windows are carried on the wall planes instead."
The fixture run saw the SAME structure and called it a dormer in 4 of 8
photos (front-left, left, rear-left, + one front frame) → Phase B
reconciled 2 shed dormers and upgraded roof_type to gable-shed-dormer.
The taxonomy flip is all-or-nothing and it cascades: no dormers → dormer
ft² 0 on every wall → dormer windows projected onto the wall planes → two
projected windows overlap → the phantom W1×W2 collision the sheets flagged.

## 4. Does low confidence correlate with the miss? YES — and it worked
The two walls that lost their dormers are exactly the two that self-scored
LOW (left 55: cross-plane ref; right 45: no square-on frame). Phase B
excluded the cross-plane and foreshortened frames from eave math by name.
The confidence system did its job — the run TOLD us it was weak precisely
where it was wrong.

## 5. Verdict: (c) BOTH — weighted toward (a)
(a) PHOTO-COVERAGE/ANNOTATION SENSITIVITY — dominant, zero code. The
    fixture succeeded with: full-wall main-plane refs, window pins on the
    dormer wall, and dormer-visible oblique frames. A capture-guidance
    sentence covers all three:
      "Draw the WALL REF across the MAIN wall plane, full span where
       possible (never across a dormer/pop-up face); shoot each elevation
       square-on; pin the windows — especially any window sitting up in
       the roof."
(b) GENUINE EXTRACTION INSTABILITY — real, smaller, post-Sept
    prompt-hardening item: the dormer definition lets the model park the
    SAME structure under "roof monitor / raised half-story" and silently
    zero the dormer schedule. Two-line hardening when it opens:
      1. Taxonomy rule: any raised roof structure with its own windows +
         knee walls is emitted in dormer_details (a monitor/half-story
         flag is fine) — never dropped to zero.
      2. Phase B tripwire: per-photo text mentions a raised roof
         structure while dormers_observed totals 0 → named LOW warning on
         the affected walls instead of silently carrying the windows onto
         the wall planes (today the collision guard is what catches it,
         downstream and anonymously).
RECOMMENDATION: ship the capture-guidance sentence as UI copy whenever
Howard wants (text-only); log the taxonomy hardening as the post-Sept
prompt item. Nothing builds this month.
