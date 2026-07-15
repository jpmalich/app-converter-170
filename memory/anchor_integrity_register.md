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
