# Single House Model — Mechanism Report (rides the handback, 2026-07-26)

## Ruling
ONE RECONCILED VERTICAL MODEL per estimate; the per-view patch era ends.
Follow-up rulings: pair dims bind PER-DIMENSION WORST CASE (never
averaged — P3 precedent; W × KNEE feeds siding area), TAPED on either
twin supersedes both; per-wall grade datums stand (named on-sheet, with
the implied grade slope printed when front/back ridge figures differ).

## Howard's findings, named in terms of the retired per-view derivations

1. **FRONT unlevel profiles** — profiles carried each face's OWN knee
   (left quad 3.4' / right quad 3.8'). Bases had been pair-leveled but
   tops = base + own knee → roof edges at 14.2' vs 14.6' — NOT level.
   Retired: per-face profile dims. Now both project the ONE SOLID
   (knee 3.8') → level by construction (pinned).
2. **BACK two-size profiles** — the same two knees rendered one paired
   box at two sizes on the back sheet. Retired: same per-face dims.
   One dormer = one size on every view (pinned; two-size impossible).
3. **LEFT floating face** — the face-on band drew in blank whitespace
   above the fascia: the per-view renderer NEVER DREW the roof plane
   the dormer sits on. Retired: plane-less dormer rendering. Now the
   face-on slope renders as a real plane (eave→ridge) and the band
   SEATS on it (pinned testid `elevation-roof-plane`).
4. **RIGHT floating profile** — same seating absence on the right
   sheet, compounded by the clamp (below): the band hung crushed and
   detached over the fascia. Retired with 3 and 5.
5. **RIGHT ridge-jam** — `_clamp_band_to_roof` CRUSHED the TAPED band
   (photo-chain 10.8'–14.6' → drawn 10.4'–14.2') to fit the ridge
   ESTIMATE (eave + gable-rise read = 14.2'). Retired: THE CLAMP. The
   ridge now RE-DERIVES UPWARD to the taped band top (14.2' → 14.6',
   rise read kept as the flagged comparison); roofline bounds remain
   flag-only and never relocate geometry (pinned).

## Before → after (EST-986945)
- ONE SOLID: 15.1' W × 3.8' KNEE (worst case — width Δ 12", knee Δ 4¾",
  both quad reads printed on-sheet) on all four sheets.
- Band 10.8'–14.6' LEVEL on every view; centers mirrored 18.7' / 18.3'
  (sum = 37.0' = wall width).
- Right ridge 14.2' → 14.6' RE-DERIVED; left 14.5' → 14.6'.
- Front/back sheets: ridge figures differ → implied-grade-slope note
  prints; every sheet names its datum ("heights above this wall's
  grade") beside the orientation note.

## Annotation layout (ruled with this package)
Pure `frontend/src/lib/annotationLayout.js` — fixed panels never move,
callouts stack below whatever they overlap, long callouts abbreviate
(full text stays in the payload/schedule). Node-executed no-overlap pin:
`tests/test_annotation_layout_pin.py`.

## Fixture gate (payload geometry, `view` text excluded)
- **letrick / doug jones / haugh — HASH-IDENTICAL** (all 12 sheets).
- **red house — drawn geometry numbers IDENTICAL** (bands 10.34–15.34,
  centers 17.4/19.6, dims 15.0×5.0 both faces; its twins agree, worst
  case = no-op). Only provenance wording changed (basis/tags now cite
  ONE SOLID / PAIRED-RECONCILED LEVEL). Declared per the re-look rule;
  no drawn geometry moved, so prior field-compares stand at the number
  level.
- EST-986945 — changed as ruled (dormer, profiles, roofline).

## Money surfaces
Dormer quads remain "visible everywhere, NEVER auto-injected" (sealed
landing rule) — no quote line consumes the drawn solid; the on-sheet
governing solid is what a manual landing reads. Conservation intact.

## Pins added/amended
- `tests/test_single_house_model.py` (8): worst-case dims + both-reads
  flag, stronger-rung governs, one-size-every-view, level profiles,
  flag-only bounds, clamp-retired + ridge-re-derive source, seating,
  grade datum.
- `tests/test_annotation_layout_pin.py` (4): node-executed no-overlap.
- Amended (declared): `test_dormer_crossview_consistency.py` (clamp →
  flag-only), `test_dormers_p5.py` (pair-governed tape tag).
