# SEND-105 REPORT — TWO RULINGS REGISTERED · SOFFIT CALIBRATION MEASURED · RULING V CONVERTED
2026-08-22 · QUANTITIES ONLY (Ruling 2 — no dollars in this or any future report;
the product's quote and chase rows still price, untouched). All live observations
on disposable clones, deleted after. No real estimate touched. EST-886440 untouched.

---

## RULING 1 — BONI LEFT: OPTION B, REGISTERED

- **Option (a) is RULED OUT, not deferred** — registered in
  `tests/test_boni_left_2026_08_22_send105.py` with a code-census pin: the
  far-member-as-corner cure (x=34.94) may not appear in shipping code; the
  member stays what it is — 3+ strokes the app cannot resolve.
- **Boni left keeps refusing and names why** (observed live): the only left
  proposal is the previously-RULED `datum_rectangle` (Ruling ZZ datum-marker
  span, basis prints "height NOT established on this elevation") — no corner
  invented; pinned that no far-member/promoted-corner wording can enter its
  basis.
- **Surfaces confirmed BINDABLE, not assumed** (the third appearance of this
  gap): a hand-drawn zone was PUT live on `left` AND on `chase:left` — both
  landed with their face kept (the SEND-100 chase-prefix fix holds here too;
  pinned). The chase:left refusal prints verbatim: `…no chase ink locatable
  on any evaluable face — the model's claim feeds nothing; the chase surface
  still exists and stays bindable — draw a zone to bind it`.

## RULING 2 — QUANTITIES ONLY, REGISTERED

Applies to every handback, report, register entry and send from here on.
The product keeps pricing (ruled three sends ago; chase pricing untouched).
Restated in the right units: the Letrick chase recovery is LEFT 23.00 ft²,
RIGHT 23.72 ft² wall-band (48.67 / 50.19 ft² with above-plate carried), REAR
54.37 ft² at the 9'-11" contestant and ≈49.8 ft² at 9'-1⅛" — about 101 ft²
wall-band, roughly ONE SQUARE.

---

## SOFFIT CALIBRATION — WALL-LINE TOP vs PLATE DATUM (report first, decided nothing)

Measured per face, both houses (wall-line top = topmost drawn wall-outline
vertex of the face's own linework; plate datum = the resolved TOP OF PLATE
line the calibration currently uses):

| house | face | wall-line top y | plate datum y | offset |
|---|---|---|---|---|
| Letrick | front | 20.37 | 20.40 | +0.03 %pts = **+0.03 ft** (rect fallback — wall line not resolved; offset is the artifact floor) |
| Letrick | rear | 65.84 | 65.90 | +0.06 %pts = **+0.06 ft** |
| Letrick | left | 21.18 | 21.30 | +0.12 %pts = **+0.11 ft** |
| Letrick | right | 61.32 | 61.50 | +0.18 %pts = **+0.17 ft** |
| Boni | front/rear/left | — | 13.90 / 57.70 / 13.90 | NOT MEASURABLE — datum_rectangle tiers carry no resolved wall outline (zone top IS the plate datum, an artifact zero), and no scale exists on these refusing faces to convert %pts to ft |
| Boni | right | — | 55.70 | NOT MEASURABLE — band_rectangle top is the band edge, not a wall line |

**VERDICT: negligible everywhere it is measurable — ≤ 0.17 ft (≈2 inches),
inside the label-box ambiguity itself. THE CURRENT CALIBRATION STANDS,
per the send's own test.** The proposal's concern was real in direction but
small in magnitude on these drawings: the plate label line and the drawn
wall-line top sit essentially on each other.

**The rear tape mapping under the wall-line pair** (the check, never a
target): drawn TOF→plate gap 269.6 px vs TOF→wall-line-top 271.1 px — ratio
1.0058. The SEND-104 mapping moves accordingly:
- plate pair (current): 54.00 ft lands at a tape of **9.852 ft = 9'-10.2"**
- wall-line pair: 54.00 ft lands at a tape of **9.909 ft = 9'-10.9"**

0.7 inches of tape between the two pairs — an order of magnitude inside the
contest itself (the rails sit ~10% apart). Nothing changed in the code.

## BONI'S MULTIPLE PLATE LINES (report only)

| face | plate ys | gaps (%pts) | other datums on the face |
|---|---|---|---|
| front (p1) | 13.9 / 23.1 / 26.5 | 9.2, 3.4 | SECOND_FLOOR@22.3, FIRST_FLOOR@32.8, TOF@34.2 |
| rear (p1) | 57.7 / 66.8 / 70.0 | 9.1, 3.2 | SECOND_FLOOR@66.0, FIRST_FLOOR@76.3, TOF@77.7, WALKOUT_FOOTER@91.2 |
| left (p2) | 13.9 / 23.1 / 26.5 | 9.2, 3.4 | SECOND_FLOOR@22.3, FIRST_FLOOR@32.7, TOF@33.8 |
| right (p2) | 55.7 / 64.9 | 9.2 | SECOND_FLOOR@64.1, TOF@75.8 |

The structure reads as a two-story stack: the TOPMOST plate is the upper
story's top-of-plate (13.9 → SECOND FLOOR at 22.3, a ~9.2 %pt story); the
middle plate (23.1) sits ~0.8 %pts above the SECOND FLOOR line — the first
story's top-of-plate; the third (26.5 / 70.0) sits ~3.3 %pts lower — a
lower-section closure (porch/garage plate). **Named risk, reported not
decided: the topmost plate is right for the full-height corner and wrong for
any lower section — a TOF→soffit tape on a lower run would span a different
pair.** No scale is verified on any Boni face, so the gaps stay in %pts; a
future tape converts them.

## RULING V — CONVERTED (was PENDING_CONVERSION since send 19)

Both reads moved onto VERIFIED-height bases (`_verified_wall_heights_ft`,
folded at the rebuild door from taped human dimensions + the estimate's own
DP-1 DERIVED chain faces — max, never averaged, source named). Where nothing
verified exists the read REFUSES with a named row (`not_derivable`, reason
printed) — never a silent zero, never a skipped row. KILLED: the
`_ai_avg_wall_height_ft` base, the `_ai_story_count or 1` ladder, the
hardcoded 9'/12-LF floors. Census baseline pruned per the Ruling U ratchet
(REMOVAL_LOG carries both). Named pin updates (SEND-99 cond. 1):
`test_gutter_geometry.py` (story-ladder pins → verified/refusal pins),
`test_gutter_geometry_http.py` (fallback trio → refusal pins), and the two
live Letrick-photo cost-preview pins (the photo estimate has no verified
height, so its height-based gutter rows now lawfully refuse — the pinned
totals moved and the update is named in each docstring).

**Resulting quantities, live (rederive door on clones):**

LETRICK — verified base found: DP-1 DERIVED chain 9.08 ft (front, left,
right; rear stays out — contested is not verified):
- Gutter 6": 108 LF (run inventory front 54' + back 54')
- Downspout 6": **6 sticks** (108 ÷ 25 → 5 drops × 12.08 LF verified drop
  ≈ 60 LF → 10' sticks) — basis prints `verified: dp1_derived_chain 9.08 ft
  (front face — max of 3 verified, never averaged)`
- Elbows 10 · End caps 4 · Hangers 56 · Pipe clips **15** (5 × 3 per drop)
  · Sealant 3 tubes · Mitres 0 (gable roof hides outside corners — ruled)

BONI — NO verified base (nothing taped, no DERIVED face — all four refuse):
- Derive (height-free): Gutter 6" 198 LF · Elbows 16 · End caps 14 ·
  Hangers 106
- **REFUSE, named on the row**: Downspout 6" sticks, Mitres, Pipe clips,
  Gutter Sealant — each prints `REFUSED — … not derivable: no verified wall
  height on this estimate — nothing taped and no DP-1 DERIVED chain; a model
  height is hypothesis only and never a quantity base (Ruling V)`. A single
  tape on any Boni face un-refuses all four.

Standing rules held: no cross-drawing evidence, no estimate influences
another, no job names in code, model heights hypothesis-only (now enforced
in the gutter family by construction). EST-886440 untouched. 423 on every
derived write. Purity pin holds. The QR field sheet stays parked until the
calibration pair is ruled — the measurement above says the current pair
already stands within 2 inches.
