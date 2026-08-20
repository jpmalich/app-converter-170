# SEND-74 — GABLE BASIS LABELLING (2026-08-21)

## The binary, sealed in code
`measure_staging.py` now owns the vocabulary — exactly TWO bases, a
third raises:
- `traced`          → "gable traced from the drawing — [X] ft², no
                       field factor"
- `field_factor_0_70` → "gable not traced — 0.70 field factor applied
                       (safety margin for an approximate gable
                       measurement)"

Every gable quantity carries exactly one (pinned: never both, never
neither — `tests/test_gable_basis_2026_08_21_send74.py`, 10 pins). A
gable REFUSAL is not a quantity and carries no basis. The 0.70 stays
the legal field fudge factor for un-traced gables; a traced gable is
exact. This is why two gables on one house can differ ~40%: traced
left 129.98 ft² vs the same face at 183.75 ft² under 0.70.

## Where the label now shows
1. **The money line** — every siding SQ line whose quantity carries
   derived (0.70) gables appends the field-factor sentence to its
   note. A bound gable ZONE (drawn/confirmed) appends "gable zone
   bound at its drawn area — no field factor" instead. (`routes/
   hover.py` `_build_lines` + `routes/pdf_overlay.py` `_overlay_note`.)
2. **The sheet** — every gable area component (primary + wing) on the
   Blueprint Elevation Sheet carries `gable_basis_label`, rendered
   under the component (`bp-elevation-gable-basis-*`).
3. **The read-back card** — when the planes carry gable ends, the card
   states the field-factor sentence (`bp-rb-gable-basis`). Run-derived
   gables are never traced, so the sentence is always true there.
4. **The overlay editor** — every gable proposal carries
   `gable_basis`/`gable_basis_label` (`pdf-overlay-gable-basis-*`).
   A TRACED proposal's divergence notice now LEADS with the mandated
   sentence and then states the derived figure beside it; a starting
   rectangle's derived figure carries the field-factor basis (the
   rectangle itself is a shape, not a quantity).
5. **The walk detail rows** (`_wall_walk_detail`) carry
   `gable_basis` + `gable_basis_label` per face — the per-surface
   money layer reads the basis from the same row it reads the number.

## Census — who is priced on 0.70 today
3 estimates carry 0.70-based gable quantities, all Letrick copies:
EST-569367, EST-715139, EST-351320 — each left+right at 183.75 ft² =
367.5 ft² under 0.70. Both Letrick gables now TRACE (left 129.98,
right 128.82 under SEND-77's fence) → confirmed traced zones would
carry ~258.8 ft², **−108.7 ft² ≈ −1.09 SQ per estimate (−30%)**. Boni
(EST-713272 etc.) carries no derived gable quantity (gables refuse).

## The recompute-drop question — structural answer
**No gable line can drop silently on recompute.** Tracing lives ONLY
on the proposal layer: the propose path is pinned to carry no
GABLE_FACTOR (SEND-68) and proposals feed no quantity. The only path
that moves a gable's money from 0.70 to traced is a HUMAN confirming a
traced zone — and that write keeps `confirmed_from`, the superseded
value, and now the "no field factor" note on the line. The moment of
choice already states both figures (the traced notice names the
derived 0.70 figure beside the traced one). No silent-drop warning
mechanism is needed because no silent drop path exists; the census
above is the watch list if that ever changes.
