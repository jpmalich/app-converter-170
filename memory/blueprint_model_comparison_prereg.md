# PRE-REGISTRATION — Blueprint validated-model controlled comparison
**Status: DRAFT — win criteria await Howard's approval. NO comparison runs
fired until approved. Filed 2026-07-14.**

## Candidates
- **Incumbent:** `claude-opus-4-5-20251101` (inherited default, tagged
  `inherited-default — validated-model decision pending` on every run)
- **Challenger:** `claude-fable-5` (the validated photo-pipeline engine,
  `_VALIDATED_MODEL_KEYS` on the photo side)

## Protocol (standing controlled-comparison protocol)
- Same Letrick prints (cached pages of Howard's upload `e4afda3a…`), same
  fixed prompt (post-shakedown hash), same composition engine downstream.
- N runs per candidate: **3 each** (extraction is stochastic — a single run
  per candidate cannot separate model quality from run variance; 3 exposes
  spread without burning budget). All 6 declared before firing; all 6 scored;
  no cherry-picking.
- Two-layer scoring vs the sealed key + validated blueprint geometry
  (footprint 30×54, 9'-1⅛" plates, 7/12, sheet-7 schedule, 6+2 corners,
  chase dims). Layer B is model-independent (engine on key geometry — already
  7/7) and is NOT re-scored; this comparison is Layer A only.
- **Anchor-integrity check:** wall labels/widths vs known geometry
  (front/back 54', left/right 30'); a run that mislabels anchors is scored
  DISQUALIFIED for that run (counts against the candidate's consistency).
- Cost (token spend) and wall-clock recorded per run.
- **Per-line verdict, aggregate no vote** — a candidate wins lines, not
  averages.

## Incumbent baseline to beat or hold (from scored run 367b7397)
| Line | Key | Incumbent baseline |
|---|---|---|
| Siding area | 2098.5 | −6.9% |
| Chase faces | 145.5 ft² | +23.7% |
| House corner walk (OSC) | 4 | 6 (over-read +2) |
| Door classes | 1 entry + 1 slider | 3 entry + 1 slider |
| Pitch / gable / starter basis / windows / placement mechanism | — | PASS (held fixes, must not regress) |

## Proposed win criteria (FOR APPROVAL)
1. **Regression bar (hard):** every already-PASS line (pitch 7/12 printed,
   gable 8.75, starter raw-perimeter basis, window count 10, placement
   attribution, structured chase presence, anchor integrity) must PASS in
   ≥2 of 3 runs per candidate. A candidate failing the bar cannot win
   regardless of residual improvement.
2. **Residual improvement (the contest):** per residual line, a candidate
   "improves" it if its MEDIAN of 3 runs is closer to key by more than the
   incumbent's own run-to-run spread on that line (i.e., improvement must
   exceed noise). Lines: siding area, chase magnitude, corner walk count,
   door classes (scored as # of misclassed doors).
3. **Decision rule:** challenger replaces incumbent only if it (a) clears
   the regression bar, (b) improves ≥2 of the 4 residual lines per rule 2,
   and (c) worsens none of the 4 beyond noise. Ties → incumbent stays
   (churn has cost). Cost/wall-clock recorded and reported but NOT a
   decision input unless Howard rules otherwise.
4. **Neither-improves outcome (pre-declared):** incumbent stays; residuals
   log as blueprint-path stochasticity with amber handling, photo-side
   doctrine (edit-and-rerun as the human path).

## Mechanics note (implementation, pending approval)
The blueprint pipeline currently hardcodes `MODEL_NAME` (ai_blueprint.py:73).
The comparison needs a per-run model override on the rerun endpoint —
internal/admin-only, never a user-facing dropdown (model-dropdown policy
ruling stands). Ships with the comparison, removed or clamped after ruling.
