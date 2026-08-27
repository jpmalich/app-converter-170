# SEND-138 — THE GABLE RE-SEAL: 367.5 → 262.5 · NO REDERIVE SWEEP — 2026-08-27

Two rulings, executed. 11 pins in
`tests/test_send138_gable_reseal_2026_08_27.py` + 6 NAMED pin updates.
**No estimate was written. No sweep was run. EST-886440 untouched.**

---

## RULING 1 — NO REDERIVE SWEEP. HONOURED BY DOING NOTHING.

The eleven 0.70 estimates keep their stored figures. Nothing was written,
no migration exists, no bulk gable write was added — and a pin now scans
`routes/` so a bulk write may not appear beside gable logic without failing
the suite. Software already computes ½ on the next live derivation
(SEND-137); those documents simply never take one.

---

## RULING 2 — THE RE-SEAL

### ITEM 1 — WHICH FACES, AND WHICH WIDTH × RISE, PRODUCE 262.5

**Two gable ends — one per SIDE face — each 30.0 ft wide with an 8.75 ft
rise.**

| | width | rise | ½ × w × rise |
|---|---|---|---|
| side gable end (one) | 30.0 ft | 8.75 ft | **131.25 ft²** |
| side gable end (other) | 30.0 ft | 8.75 ft | **131.25 ft²** |
| | | **SEALED TOTAL** | **262.5 ft²** |

Two independent routes land on the same number, which is why it can be
sealed rather than chosen:
1. **Howard's arithmetic**: 367.5 × (0.5 / 0.7) = **262.5**, to the penny.
2. **The old figure's own composition**: 367.5 = 0.70 × 2 × 30.0 × 8.75.
   The same walls, the same widths, the same rises — only the factor moved.

**AND THE SEAL PROVES ITS OWN GEOMETRY — no outside read is borrowed.**
The takeoff's `rakes_lf` is 69.6 = **4 × 17.4**. Four rakes means **two
gable ends**; and a rake over a 15.0 ft half-width at an 8.75 ft rise is
√(15.0² + 8.75²) = **17.37 ft ≈ 17.4**. The sealed rake figure reproduces
both the 30 ft width and the 8.75 ft rise from inside the seal itself.
(Pinned: `test_the_faces_are_confirmed_by_the_seals_own_rakes`.)

### ITEM 2 — THE FIXTURE AND THE REGISTER NOW EXPECT 262.5, NOT 367.5

- **262.5 is a REGISTERED VALUE, not a remark in a comment.** The sealed
  fixture gains an explicit `inputs["gables_sqft"] = 262.5` with its own
  `bases` entry stating the formula, the two ends, and the retirement. A
  figure nothing reads cannot be re-sealed — before this send the gable
  total existed only inside a code comment.
- **The consumer reads that value; it keeps no copy.** The area-basis line
  now takes `inp["gables_sqft"]` (pinned), so the sealed figure has exactly
  one home.
- **367.5 IS RETIRED AS A TARGET.** Pinned: no sealed input and no sealed
  line equals 367.5; the consumer holds no `"sqft": 367.5`; and wherever
  the digits still appear they appear **inside the sentence that retires
  them** ("the 0.70-era 367.5 is retired as a target"). Nothing tunes
  toward it, and the retirement is recorded rather than erased.

**DEPENDENTS RE-DERIVED — reported plainly, because a seal that does not
sum is not a seal.** Under this project's standing ruling that a computed
total may not outlive a superseded input, and following the fixture's own
KEY-HYGIENE precedent (the 2026-07-18 correction re-derived front area, raw
and lap in the same breath):

| | before | after | why |
|---|---|---|---|
| gables | 367.5 | **262.5** | the re-seal |
| walls_gables_sqft | 1947.3 | **1842.3** | the stated total less the same 105.0 — the pre-existing 0.4 rounding flag on the back wall is left exactly as it was; no new arithmetic invented |
| raw_sqft | 2099.7 | **1994.7** | 1842.3 + chase 51.37 + 101.02 = 1994.69 |
| sealed lap line | 255 PCS | **242 PCS** | 19.947 sq +10% = 21.94 sq × 11 pcs/sq = 241.36 → 242 |

**NOTHING ELSE IN THE SEAL MOVED** (pinned): eaves 108.0 · rakes 69.6 ·
fascia+rake 177.6 · perimeter 168.0 · starter 165.0 · OSC 8 · ISC 2 ·
soffit 108 · trim 12 — all LF- and count-driven, none reads gable area.
The item-3 chase figures (51.37 / 101.02) are untouched.

**THE MONEY CONSEQUENCE ON THE SEALED FIXTURE'S DEMO ESTIMATE, FULLY
ACCOUNTED — reported, not buried:** `total_sell` **13,089.60 → 12,672.70
(−416.90)**, and every cent is named: lap 255 → 242 pcs (−13 × $30.99 =
−$402.87) and caulk 21 → 20 tubes (1 per square; −$14.03). **THE IDENTITY
THAT MATTERS SURVIVED**: the app's derived lap and the sealed key's lap
still land on the SAME number (242 = 242, residual ZERO) — both ledgers
moved together, which is what that pin exists to prove.

### ITEM 3 — NO JOB NAME IS INTRODUCED INTO CODE

- This send adds **no customer name anywhere**. The new pin file is
  `test_send138_gable_reseal_2026_08_27.py`; it speaks of **THE SEALED
  FIXTURE**, and a pin enforces that the legacy name may appear in it only
  on the line that imports the pre-existing module or names its path.
- The consumer's docstring stopped calling the fixture by its customer name
  and now says "the sealed fixture".
- **The gate is still portable**: `est.get("sealed_key") != "letrick_v3"`
  — a doc flag, never a runtime match on an estimate number or a customer
  name (pinned, and the function's body carries no `customer_name` read).
- **PRE-EXISTING, REPORTED HONESTLY, NOT TOUCHED**: the key module's
  filename and constant, and the `fixture_figures` registry key, already
  carry that name from earlier sends. Renaming them is not authorised in
  this send and is not attempted; nothing new joins them.

---

## NAMED PIN UPDATES (never silently flipped)
1. Lap-unification seal 1 — gable component 367.5 → **262.5**; the
   itemisation total and `siding_sqft_effective` 2099.7 → **1994.7**.
2. Lap-unification seal 2 — the basis sentence now says **RE-SEALED TO THE
   TRIANGLE** with the two ends and the ½ formula; "retired as a target".
3. Lap-unification seal 3 — base_qty 230.97 → **219.42** (1994.7 ÷ 100 × 11).
4. Lap-unification seal 5 (the identity receipt) — app lap == key lap, both
   255 → **242**. **The pin's subject, residual zero, is unchanged.**
5. Item-3 chase ratification ledger — raw 2099.7 → **1994.7**, lap 255 →
   **242**; the chase figures themselves untouched.
6. Two live money pins on the sealed fixture's demo estimate — `total_sell`
   13,089.60 → **12,672.70**, amended with the −$416.90 decomposition.

## NOT AUTHORISED, NOT TOUCHED
Rederive sweep · Annotate retirement · gable/dormer move into
PhotoTakeoffEditor · phase 2 trim · rectify · split storage ·
refusal-receipt UI.
