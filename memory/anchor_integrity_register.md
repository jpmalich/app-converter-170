# Anchor-Integrity Register
Wall-level extraction errors and documented stochasticity, per run.
Opened 2026-07-15 (Howard's order, letrick 7-14-26 7pm findings).

## Entry 1 — Chase wall misassignment (photo run d6679448, letrick 7-14-26 7pm)
- **Class: wall-level LABEL error** — coarser than fractional drift.
  Locators placed the chase ISC pair on "right wall"; ground truth is the
  back wall. The 3D drew the wrong-wall data honestly — no render change
  owed; it drew what it was given.
- **Coverage check (ordered)**: does "not present" + field-verify fully
  cover correction of a mislocated chase? **NO — reported honestly.**
  - Field-verify is ratification-only (verified/unverified); it cannot
    RELOCATE a chase to another wall.
  - The "not present" verb covers openings-schedule rows (windows/doors),
    not chase/corner locators.
  - A contractor facing a mislocated chase today can: leave it amber/
    unverified (presence guarantee keeps the sticks), or edit-and-rerun.
    There is NO in-card relocation path. Flagged to Howard as a coverage
    gap; awaiting ruling on whether a "wrong wall" correction verb is
    wanted on amber locators.

## Entry 2 — Documented extraction stochasticity (same run — amber/confirm-card handling, NO engine action per ruling)
| Line | Run read | Key | Delta |
|---|---|---|---|
| Lap boards | 227 | 255 | −28 |
| OSC | 7 | 8 | −1 |
| Trim | 11 | 12 | −1 |
| Fascia | 11 | 12 | −1 |
| Windows | 9 | 10 | −1 |
| Patio door | read as entry | 1 patio | misclass |

## Entry 3 — Starter "fractional boards" report: TRACED, NOT A VIOLATION
- Reported: $123.96 ÷ $38.99 ≈ 3.18 boards on 154 LF.
- Trace: engine prices starter by `pieces_added = ceil(153.833 ÷ 48) = 4`
  whole boards; line_sell = $30.99 (Contractor-30 board sell) × 4 =
  $123.96 exactly. The ÷ $38.99 read used the Whole-sale-35 board price.
- Real defect was DISPLAY: a per-board unit price rendered beside an LF
  qty invites exactly this misread. Fixed: rip lines now show
  "$/board × N whole boards" in the unit column. Whole-piece pin test
  added (line_sell == unit_sell × pieces_added, integer boards).

## Entry 4 — Blueprint window over-read (comparison runs, 2026-07-15)
- See blueprint_model_comparison_results.md evidence memo: schedule-qty
  cross-attribution duplicate (B×4 kept + spotted B×1), 3/3 on direct
  transport. Disposition: stochasticity → confirm-openings ratification
  card now serves the blueprint path.

## DEFECT CLASS: intra-run self-disagreement (registered 2026-07-16, NO FIX — mechanism named per Howard)
- **Instance**: run d66794488ef848509446431b355db8e5 (letrick photo): siding_sqft 1,889.1 vs _per_profile_sqft.lap 1,780.5 (−108.6).
- **Mechanism (named, verified by exact decomposition)**: two gable conventions inside one result. Headline path (`apply_roof_type_material_math`, C4 ruling) prices gables at ×0.7 (0.7·w·t = 380.1). Per-profile path (`profile_callouts.breakdown_walls_by_profile`) computes gables at the TRUE triangle (0.5·w·t = 271.5). Bodies (1,379) + chase (130) match exactly in both. Δ = 0.2·(30·8.8 + 30·9.3) = 108.6 ✓.
- **Class distinction**: this is NOT key-vs-run extraction variance — the extraction disagrees with itself; any consumer binding to _per_profile_sqft inherits the un-C4'd gable basis (the B&B first-derivation did).
- **Fix status**: HELD — mechanism first per ruling; reconciliation is a separate diff for Howard's review (which path's convention governs per-profile splits).

## STANDING RULE: geometry-source naming (Howard, 2026-07-16)
- Every derivation, copy, and comparison surface states its geometry basis VISIBLY: "tape-validated key" vs "extraction run + run_id".
- Where a tape-validated basis exists it is the DEFAULT source; extraction runs are the labeled fallback.
- PIN: no derivation silently binds to latest-run. Compare-profiles toggle ships under this rule — "one geometry" = one NAMED geometry.
