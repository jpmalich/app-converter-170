# THREE MISFILED SURFACES → JobInfoPanel — WALK-READY MOVE SCOPE
Report only. Position 1 (second half) of Howard's queue. Delivered
alongside the five P0 chips landed 2026-08-13 (pro-quotes reply 3).
The five chips are P0/build-now; the three moves below are position 1
too, but they are architectural reshapings and I ship the SCOPE
first so the next turn starts inside a known plan rather than a
discovery loop.

## THE THREE MOVES (from baseline burn-down report §2)
Ordered by effort (smallest first — Howard's "the misfile is why
the surface hides" precedent applies to all three):

### MOVE A — Model comparison history → persistent tile-chip
Effort: ~45 min. Smallest move; ship first.
Where it lives now: inside both `BlueprintMeasureButton.jsx` and
`AIMeasureButton.jsx` run dialogs. Only visible when a dialog is
open, which is a per-run mount for a per-estimate concept (the
comparison across runs). Silently vanishes when history < 2.

**Landing plan**:
 - **New component** `RunComparisonChip.jsx` — reads
   `/api/estimates/{eid}/runs/history` (existing endpoint), renders:
    - Count of completed runs on this estimate ("3 blueprint reads,
      2 photo runs").
    - Click → opens the existing model-comparison diff modal
      (already built; we just hoist the trigger).
 - **Mount point** — on the estimate-tile row, next to the existing
   Blueprint / Photo / HOVER chips (JobInfoPanel already has that
   row). A `SurfaceAccessChip` variant with state="Read history —
   1 run so far" when history < 2, "Compare N reads" when ≥2.
 - **Retire** the inline history block from the two run dialogs —
   the trigger is now the tile chip; the diff modal stays where
   it is (its own component; opened by the chip).
 - **Pin**: `test_run_comparison_chip_never_hidden` — assert the
   chip renders on every estimate whose kind supports blueprint or
   photo, even with 0 runs (says "no reads yet"), so it never
   silently vanishes.

### MOVE B — Vinyl profile picker → JobInfoPanel spec area
Effort: ~2 hours. Medium.
Where it lives now: inside `AIMeasureButton.jsx` photo-run dialog.
Chip is already on the tile (send-4). The PICKER itself is only
reachable via that modal.

**Landing plan**:
 - **New JobInfoPanel section** `EstimateProfileSpec` — persistent
   panel that renders per-siding-line profile assignment. Reuses
   the existing `SidingProfileChip` component's dialog / choose /
   swap logic — the component is already estimate-scoped
   (est+catalog+update+save props), just wasn't mounted on the
   panel.
 - Mount point: JobInfoPanel already has a "Spec" section
   (Materials, Waste, Colors); this is a new sibling accordion
   `Siding profile`.
 - **Retire** the run-dialog copy: the picker no longer opens from
   AIMeasureButton; the chip on the tile links to the JobInfoPanel
   accordion instead.
 - **Pin**: `test_profile_picker_reachable_without_open_run` —
   assert JobInfoPanel renders the picker on any estimate with a
   siding takeoff, regardless of run state.

### MOVE C — Accent injection → JobInfoPanel accents panel
Effort: ~2 hours. Medium.
Where it lives now: inside `BlueprintMeasureButton.jsx` blueprint-
run dialog. Injection is per-elevation but per-estimate lives on
the estimate's takeoff, not on one run.

**Landing plan**:
 - **New JobInfoPanel section** `EstimateAccents` — persistent
   panel that lists per-elevation accents (uses
   `PerElevationBreakdownCard`'s existing injection logic).
 - Reuses the existing accent-write endpoint (`PUT
   /api/estimates/{eid}/accents/{elevation}`); the injection UI
   itself is just re-mounted.
 - **Retire** the injection UI from the run dialog.
 - **Pin**: `test_accent_injection_reachable_without_open_run`.

## COMBINED ESTIMATE
~5 hours total (Move A ~45 min + Move B ~2 h + Move C ~2 h). About
one focused session, or two spread across a walk cycle.

## THE WALK BAR (extended P0-chips walk bar)
The five P0 chips have already landed; walking them is a matter of
opening each of the five surfaces in the states that used to hide
them (no carrier row for siding, mid-fetch photo gate, pre-review
openings, empty smart-engine composition, loading gate panel) and
seeing the chip stand in. For the three moves:
 1. Open JobInfoPanel on a photo-source estimate; find "Siding
    profile" accordion; click it; picker opens without a run
    dialog.
 2. Open JobInfoPanel on a blueprint-source estimate; find
    "Estimate accents" accordion; edit a wall accent; save
    without a run dialog.
 3. On any estimate row, see "Compare N reads" chip when N ≥ 2;
    click; the model-comparison diff modal opens directly.

If all three succeed, position 1 (both halves) is walked and MUV
starts.

## READY-TO-START CHECKLIST
- [x] Five P0 chips landed (this session).
- [x] Scope document exists (this file).
- [ ] Move A (Run history chip) — first, ~45 min.
- [ ] Move B (Profile picker relocation) — second, ~2 h.
- [ ] Move C (Accent injection relocation) — third, ~2 h.
- [ ] Handback stamp with all three green.

Next turn: start Move A immediately from this scope, no discovery.
