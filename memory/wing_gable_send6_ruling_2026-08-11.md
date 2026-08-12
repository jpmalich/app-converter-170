# SEND-6 WING GABLE MECHANISM + PITCH PER PLANE — RULING LANDED

**Date**: 2026-08-11 (send-6)
**Ruling**: Howard, verbatim: "AN ORPHAN GABLE END IS NEVER DISTRIBUTED
ONTO AN UNRELATED [wall]. It FLAGS and stays unattributed, loud, on the
card and on the sheet."
**Suite**: 2267 passed / 5 skipped (was 2253; +14 send-6 pins).

## THE MECHANISM (report the finding, then fix the class)

### What we discovered

The Boni case (EST-886440, run 80c10620):
- `_gable_ends_plane_read = 4` — the AI counted four triangular gable
  ends across the elevations.
- `roof_planes` returned three entries: `main` (gable_ends 2),
  `garage/bonus` (gable_ends 2), `porch` (gable_ends 0).
- Sum reconciles: 2 + 2 + 0 = 4.

But Howard walked the drawings and named a **fourth body**: the ENTRY
gable sitting over the front door. It has its own rake, its own soffit,
its own fascia, its own triangular siding area — none of which the
model emitted, because it lumped the entry gable's single end into
`garage/bonus.gable_ends = 2` for lack of a plane to put it on.

### Why it looked right

The read reconciled numerically (4 ends across 3 planes). The
attribution then took `garage/bonus`'s 2 ends and distributed them
across the perpendicular axis (F + B) via the send-3 heuristic — a
seemingly reasonable placement. **The heuristic was papering over a
missing body.**

### The class it exposes

The perpendicular-axis heuristic silently absorbed an orphan. It would
absorb the next one too. **A wrong attribution is worse than a null,
because a null draws a "needs your tape" hatch and a wrong attribution
draws confidently.**

Howard's ruling names the class: an orphan gable end (no plane
identifying its own attachment face) is NEVER distributed onto an
unrelated wall. It flags and stays unattributed, loud, on the card and
on the sheet.

## THE FIX — TWO PARTS, BOTH REQUIRED

### Part 1 — THE READ FIX (extraction-side)

`SYSTEM_PROMPT` and `ROOF_PASS_PROMPT` in `routes/ai_blueprint.py` now
require the model to:

1. **Emit one plane per gable end.** If the elevations show four
   triangular ends, `roof_planes` carries four planes. The entry gable
   becomes its own plane (label `entry` or the verbatim plan label)
   with its own rake, soffit, fascia and area.
2. **Emit `gable_end_faces` on every plane with gable_ends > 0.** A
   list of length equal to `gable_ends`, each entry naming the elevation
   face the triangle points at (front/back/left/right).
3. **Emit `pitch` on every plane.** A plane's own printed pitch, empty
   when unread. **NEVER inherit** the main body pitch — the app flags
   rather than substitutes.
4. **Emit `overhang_in` and `wall_height_ft` per plane.** So the
   garage's printed 9'-11 7/8" siding height rides its own plane, and
   the "FASCIA ONLY NO OVERHANG" annotation rides its own plane.
5. **Self-check block** (S1 / S2 / S3) — the model verifies the
   invariants before returning.

### Part 2 — THE SEAM GUARD (attribution-side)

`gable_attribution.attribute_secondary_gables` was rewritten:

- The perpendicular-axis heuristic is **retired**.
- A wing plane's ends are attributed **only** via its own
  `gable_end_faces` evidence.
- Every unmatched end goes into `orphans[]` — never onto a wall.
- The readback census flag `gable_census_mismatch` names orphan planes
  by count.
- The elevation-sheet renderer surfaces orphans as
  `wall.orphan_gables` + a loud `orphan_note` on EVERY wall the miss
  could belong to. Same shape as every ruling this month: fix the
  instance, then make the class unrepresentable.

## PITCH PER PLANE (addendum to the ruling)

Howard's addendum: a plane that carries no printed pitch FLAGS rather
than inheriting the house value. Entry at 10/12 vs main at 7/12 is the
live case; a wrong inherited pitch computes a wrong rise on a gable
that is honestly null.

Implementation:
- `roof_planes[i].pitch` propagates through the readback into
  `plane_rows`.
- `blueprint_elevation.build_blueprint_sheet` reads the wing plane's
  own pitch to compute rise = base/2 × pitch/12. Empty pitch → height
  stays null and the sheet says "plane pitch UNREAD — sheet does not
  inherit main body pitch".
- Rail codes `pitch_missing_on_planes` (loud warn) and
  `pitch_varies_by_plane` (info) name the planes.

## GARAGE WALL HEIGHT (Item 3)

The 9'-11 7/8" garage wall is now readable via
`roof_planes[i].wall_height_ft`. The rail surfaces it as
`wall_height_by_plane` (info) — the printed value quoted, additions to
reach the sided height named separately.

## OVERHANG PRECISION (Item 4)

`roof_planes[i].overhang_in` per plane. Rail codes:
- `overhang_by_plane` — info, lists every printed value.
- `overhang_missing_on_planes` — warn, names the specific planes
  without a printed overhang. **No more blanket "not dimensioned
  anywhere" when one plane is missing it.**

## GABLE_CENSUS_MISMATCH — 3-DAY DELAY (P1, partly answered)

The flag was CORRECT for three days. It named the exact contradiction
(planes 4 vs walls 2). Both Howard and prior agent runs let it ride
because the card buried it among 40+ equally-red flags.

**Finding: this is card-readability, not flag-quality.** The instrument
worked; the surface didn't. The verdict-and-triage proposal (P1) must
address:
- Ranking (which flag matters right now)
- A top-level VERDICT (a single-sentence summary of grading state)
- Card grouping that separates "the read reconciles" from "the read
  contradicts itself" from "the read is unread on X"

The fix here is NOT louder flags. The instrument is fine.

## FILES CHANGED

- `backend/routes/ai_blueprint.py`
  - `SYSTEM_PROMPT`: gable_end_faces, pitch, overhang_in,
    wall_height_ft per plane + S1/S2/S3 self-check block.
  - `ROOF_PASS_PROMPT`: same fields.
  - `check_read_consistency`: orphan surfacing in flag vars.
  - `build_blueprint_readback`: per-plane pitch/overhang/wall_height
    on `plane_rows` + new rail codes.
- `backend/gable_attribution.py`
  - Rewritten: evidence-driven attribution via `gable_end_faces`; no
    perpendicular-axis heuristic; orphans[] surfaced with reasons.
- `backend/routes/blueprint_elevation.py`
  - Per-plane pitch → rise. Orphan disclosure per wall
    (`orphan_gables`, `orphan_note`).
- `frontend/src/lib/dictionaries.js`
  - EN + ES for `overhang_by_plane`, `overhang_missing_on_planes`,
    `pitch_missing_on_planes`, `pitch_varies_by_plane`,
    `wall_height_by_plane`.
- `backend/tests/test_gable_attribution_2026_08_11.py`
  - Rewritten for evidence-driven attribution + orphan pins.
- `backend/tests/test_consistency_checker_2026_08_07.py`
  - Case A updated for `gable_end_faces` evidence; Case B carries
    orphan_planes vars.
- `backend/tests/test_blueprint_elevation_phase2_2026_08_11.py`
  - Fixture now emits `gable_end_faces` on all wing planes.
- `backend/tests/test_send6_wing_gable_and_pitch_per_plane_2026_08_11.py`
  - **New** — 11 pins: prompt schema, sheet renderer, rail codes.
- `backend/tests/test_schema_consumer_keys_2026_08_10.py`
  - INTERNAL_KEYS extended for gable_attribution result shape.

## PURITY

Unchanged. Every dimension in this ruling is EVIDENCE for the rulings,
never a constant, default, fallback, or assertion target. Nothing
applies to EST-886440. Integral-J stays ON.
