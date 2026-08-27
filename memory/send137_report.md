# SEND-137 — THE GABLE RULING: MEASURE THE TRIANGLE · 0.70 RETIRED — 2026-08-27

**STAMP: `2026-08-27 19:34 UTC · e1046d0 · CLEAN · 2991 passed, 9 skipped,
7 warnings in 487.46s`** · census pin GREEN, 0 PENDING_CONVERSION · ingress
smoke 4 passed.

**PRE-STAMP REDS, NAMED, NEVER STAMPED OVER (10 on the first run):** eight
were the guard catching THIS send's change — stale 0.70 expectations in old
pins — and all eight were fixed as **NAMED PIN UPDATES** (listed at the
bottom), zero assertions weakened. Two were the known live-window transient
family (`test_demo_reset` isolation: a concurrent test's `TEST_GATE` price
tier and one extra estimate inside the reset window); both pass standalone
and in the stamped run.

**LIVE E2E, READ-ONLY, ON REAL BLUEPRINT ESTIMATES** (`/api/estimates/{id}/
blueprint-elevation/left`, nothing written): EST-530671 left gable now
returns **131.2 ft²** and EST-349048 left gable **222.3 ft²**, each stamped
`gable_basis: "measured_triangle"` with the sentence *"gable measured — ½ ×
width × rise = … from this face's own width and rise, no field factor"* —
the same ½ figures the table below predicts, from the live surface.

Howard's ruling, executed. `½ × width × rise` is the gable wall wherever
that face's own width and rise exist. `0.70 × width × rise` is retired —
not a fallback, not a waste factor, not a default, not a "close enough".
**An untraced gable has no area: it refuses by name.**

Pins: 15 in `tests/test_send137_gable_ruling_2026_08_27.py` + 3 NAMED pin
updates (send74 basis file, send23 Ruling-Y, three-doors step 1).
Probes (read-only, wrote nothing): `memory/send137_probe.py`,
`memory/send137_probe2.py`. **EST-886440 was not touched.** Nothing is
tuned toward 8.4, 370, 172.8, 367.5, 621.1 or any dollar total — every
arithmetic pin uses invented round numbers (30 × 10 walls, rise 8, 40 ft
fronts).

---

## ITEM 1 — EVERY LIVE GABLE FIGURE COMPUTED WITH 0.70

Read straight out of Mongo, with the source run's own walls recovered so
the factor each figure was computed at is **measured, not assumed**
(`carried ÷ Σ(width × rise)`).

| Estimate | source | faces | w × rise | carried gable ft² | implied factor | ½ × w × rise | becomes |
|---|---|---|---|---|---|---|---|
| **EST-349048** | blueprint | left + right | 39.0 × 11.4 each | **621.1** | **0.6985** | 444.6 | **444.6** |
| EST-190197 / EST-886440 / EST-111561 / EST-040221 / EST-713272 | blueprint | (same read family; run walls not recoverable on those five docs) | — | **621.1** each | 0.70 by construction (same aggregator, same figure) | 443.6 | **443.6** |
| **EST-530671** | blueprint | left + right | 30.0 × 8.75 each | **367.5** (basis stamped `field_factor_0_70`) | **0.7000** | 262.5 | **262.5** |
| EST-655664 / EST-569367 / EST-715139 / EST-351320 | blueprint | left + right | 30.0 × 8.75 each | **367.5** each | **0.7000** | 262.5 | **262.5** |
| **EST-381546** | photo | front + back | 27.0 × 6.4 each | **172.8** | **0.5000** | 172.8 | **86.4** — front only |
| EST-687512 | blueprint | left | — | — | — | — | already **REFUSED** (width not read) |
| EST-012540 | blueprint | left + right | — | — | — | — | already **REFUSED** ×2 |
| EST-564805 | blueprint | left + right | — | — | — | — | already **REFUSED** ×2 |

**Totals across the walk-detail rows in hand: 1,653.75 ft² carried at
0.70 → 1,050.00 ft² at ½ (−603.75 ft², −36.5%).**

Three things this table says plainly:

1. **The blueprint lane wrote 0.70.** Eleven estimates carry it; one
   (EST-530671) still carries the literal basis string
   `field_factor_0_70` on its walk rows, which is how a stored figure
   from before the ruling can be recognised at all.
2. **EST-381546 wrote ½ — from the PANEL.** Its implied factor is
   **0.5000 exactly**, and its stored `siding_sqft` 1243.8 = 1071 body +
   **172.8** gable. The backend's own aggregator would have written
   241.92 on that same read. **The panel's number was saved into the
   estimate.** That is the ~40% disagreement, live, in one document — and
   it is the reason this was never "two conventions to choose between":
   both numbers were already in the same database, under the same key.
3. **EST-381546 does not become 172.8.** Under SEND-136 its back face has
   no photo and is refused, so only the front gable survives: **86.4 ft²**
   (½ × 27 × 6.4). The estimate is already marked `_face_rule_stale` and
   Apply Measurements is disabled until it is re-derived — nothing was
   written to it in this send.
4. **The three already-refusing houses do not change.** A refusal was
   never a factor question.

Live estimates move on their **next rederive**. Nothing was rewritten
under anyone's feet, and EST-886440 (protected) was read only.

---

## ITEM 2 — THE FUNCTIONS THAT DISAGREED. NAMED, NOT DEFENDED.

**The two Howard named:**

1. **`measure_staging.walk_walls`** — the one shared aggregation funnel
   every door passes through (photo, blueprint, hover, restore, the
   shared mapper). It computed `GABLE_FACTOR (0.70) × g_width × rise`
   and stamped the basis `field_factor_0_70` on the row, the money line,
   the elevation sheet and the read-back card. **This is the function
   that put 0.70 into the database.**
2. **`recomputeFromWalls` in `AIMeasureButton.jsx`** — the live preview
   panel, a second money surface. It computed `0.5 * width * gableH`, and
   whatever it computed got SAVED (EST-381546 is the receipt).

**Same disease, three more copies, found while wiring — reported, not
hidden:**

3. **`profile_callouts.breakdown_walls_by_profile`** — `0.7 * width *
   gable_h`, a THIRD copy. It feeds the per-profile split and the LP
   profile lines; its own docstring claimed it was kept at 0.7
   *precisely so the split would not disagree with the headline* — the
   two were locked together at the wrong number.
4. **`routes/blueprint_elevation.py`** (primary + wing gable) — the
   arithmetic was **already `0.5 × width × rise`** while the label it
   printed said *"gable not traced — 0.70 field factor applied"*. **The
   sheet's number and the sheet's own sentence disagreed.**
5. **`PhotoMeasureButton.jsx`** — the manual tape card, `gw × gh × 0.7`,
   inherited from the old HTML tool ("half-tri plus bonus up to the
   peak"). A contractor's taped gable width and rise are a measured
   triangle; this surface inflated them by 40%.

No defence is offered for any of the five. 0.70 was never a second
convention; it was a second implementation of the same number.

---

## ITEM 3 — WHAT WAS WIRED

**ONE formula, one constant, one label.**
- `measure_staging.GABLE_FACTOR = 0.70` → **`GABLE_TRIANGLE_FACTOR =
  0.5`**. The name changed on purpose: every consumer had to be re-read
  rather than silently inherit a new value.
- `GABLE_CONVENTION_LABEL` now reads *"½ × width × rise — the measured
  gable triangle (the 0.70 field factor is RETIRED, SEND-137)"*.
- The basis binary stands, re-cut: **`traced`** (drawn line-work) ·
  **`measured_triangle`** (½ × width × rise). `gable_basis_label` raises
  on any third value, exactly as before.
- All five surfaces above now compute ½: the walk, the panel, the
  per-profile split, the elevation sheet (number and label finally
  agree), the manual tape card. The read-back card's hard-coded 0.70
  sentence is gone.

**AN UNTRACED GABLE HAS NO AREA — and says which gable and why.**
`gable_claim_without_rise(wall)` refuses, by name, when a gable is
claimed and its triangle was never measured. **The claim must be
evidenced**, and only two signals count:
- the rise field is **present and null** — the read's own "not visible",
  which is *not* the `0` that means "this wall ends in an eave";
- an explicit upstream rise refusal (`_gable_rise_refusal`).

An **absent** field claims no gable and earns no refusal, so a hip house,
a rectangle wall and a hip-zeroed wall (the roof-type rule writes a
literal `0`) all stay silent. A gable profile callout is **not** accepted
as a rise claim — it would have started refusing on every hip-zeroed
wall. The refusal carries the real reason to `gable_refusal` and to
`faces_not_derivable`; the ft² is `None`, **never 0** (a 0 reads as
"measured and none"), and the per-profile split names the same gap.

**THE STORED PAST IS NAMED, NEVER REPRINTED AS CURRENT.**
`GABLE_BASIS_RETIRED_FIELD_FACTOR` survives for exactly one job:
recognising a figure stored before the ruling. Asked for its label, it
answers *"STALE BASIS — computed with the 0.70 field factor, RETIRED
2026-08-27… the stored figure reads high until this estimate is
re-derived."* It is **not** a member of `GABLE_BASES`, so nothing can
compute with it again.

**THE SEALED HAND TAKEOFF WAS NOT REWRITTEN.** The Letrick sealed key
carries a human's gable figure of 367.5 ft², written by hand as w×h×0.7.
That is a person's sealed number, not a computation the system performs —
so the number stands and its basis line now says so out loud: *sealed
hand takeoff, the factor it was written with is retired in software,
stands until Howard re-seals it*, with the measured-triangle read and the
delta printed beside it. **Software's 0.70 is gone; a human's sealed
figure is Howard's to re-seal.**

---

## ITEM 4 — THE PANEL AND THE STORED FIGURE NOW MATCH. PINNED.

Not a comment claiming parity — an **executable** one. The pin
`test_the_panels_coefficient_is_read_from_the_file_and_equals_the_backends`
regex-reads the coefficient out of `AIMeasureButton.jsx` itself and
asserts it equals the backend constant. A second pin runs an invented
four-wall house (two 40 ft gable fronts at rise 8, two 20 ft sides) and
asserts the panel's arithmetic — evaluated exactly as the file writes it
— equals the walk's stored `gable_sqft` (320.0 ft²). A third asserts the
per-profile split total equals body + gable from the walk. **If either
surface moves again, the suite fails.**

A further pin scans staging, both AI doors, hover, lp_package and
profile_callouts for `0.7 * width`, `0.70 * width`, `GABLE_BOOK_FACTOR`
and the retired basis assignment: **the factor cannot come back in
through a sixth copy.**

---

## NAMED PIN UPDATES (never silently flipped)
1. `test_three_doors_step1_2026_08_01.py` — the sealed factor moves 0.70
   → ½. **Step 1's invariant is unchanged** and is what the pins still
   hold: ONE formula, both doors, no second copy.
2. `test_gable_basis_2026_08_21_send74.py` — the binary's second member
   changed; its discipline did not. Exactly one basis per quantity, never
   both, never a third, label riding the quantity to sheet, card and
   money line. New pin: the retired basis is named STALE.
3. `test_ruling_y_gable_body_span_2026_08_14_send23.py` — Ruling Y is
   untouched in intent (the gable stays as wide as its real widths, never
   shrunk for a height reason); only the factor in its expected value
   moved, and the convention pin now demands the ½ sentence.

## NOT AUTHORISED, NOT TOUCHED
Annotate retirement · gable/dormer move into PhotoTakeoffEditor · phase 2
trim · rectify · splitting hover/photo storage. No estimate was written;
no job name entered code; the sealed-key gate stays a portable doc flag.
