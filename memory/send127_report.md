# SEND-127 REPORT — ATTRIBUTION, REPORTED BEFORE ANYTHING WAS BUILT
2026-08-25 · Quantities only. Probe: `memory/send127_attribution_probe.py`
(read-only; no run rewritten, no estimate touched, no model call).

## 1. FIRST QUESTION — DID THE `dims_shared_source` RAIL FIRE ON THE 56'-0" BOX?

**YES. IT FIRED. The system disclosed correctly. The defect is that a
flagged value still fed a quantity.**

Verbatim from dart's run `ff0d596e`, `raw_ai._dim_shared_source`:
```
{"quote": "56'-0\"", "page": 4,
 "consumers": ["roof_planes.main.rake_lf",
               "walls.left.width_ft",
               "walls.right.width_ft"],
 "conflicting": false,
 "kept": [all three], "demoted": []}
```
Three facts inside that one record:
1. **The share was detected** — one located quote, three consumers, all
   named.
2. **`conflicting: false`** — it landed on the PLAIN rail, not the louder
   `dims_shared_source_conflict`. That is the send-14 D rule working as
   written: the conflict rail fires on vertical/horizontal mixes and on
   two VERTICAL spans of different features; an overall HORIZONTAL
   dimension serving two opposing facades was ruled "NOT impossible — it
   IS the house". Left+right is exactly that allowed case. So the
   classifier did not miss a rule; the rule says horizontal opposing
   shares are legitimate.
3. **`demoted: []`, `kept: [all]`** — by the send-13 ruling
   ("SHARED-SOURCE IS A LOUD FLAG, NOT A KILL … the value SURVIVES and
   feeds money"), the flagged 56.0 went straight into the gable lane.

So: **rail gap, no. Consumer gap, yes.** The 2026-08-14 amendment
deliberately let flagged values feed money; SEND-126 is the first case
where that permission bought a fabricated 1,280.53 ft². This send's
ruling reverses the permission for quantity consumers only.

## 2. WHAT "UNATTRIBUTED" MEANS OPERATIONALLY
A located figure is **UNATTRIBUTED** when its one located quote (same
page + same printed string) is claimed by **two or more DIFFERENT named
features for the SAME leaf field** — two walls' `width_ft`, two walls'
`height_ft`. Existence passed; ownership did not. A quote shared between
a feature and its OWN derived consumer (`walls.left.width_ft` and
`roof_planes.main.rake_lf` computed from it) is not competing ownership —
it is one attribution flowing downstream, and it inherits that path's
status rather than creating a new ambiguity.

## 3. THE CONSUMER INVENTORY — DISPLAY vs QUANTITY

### DISPLAY (may show the flagged figure, per the ruling)
| consumer | what it shows |
|---|---|
| `_dim_evidence` provenance list | path → value, page, printed quote, loc box |
| `_dim_shared_source` ledger + readback `dim_shared_source` | the share itself, all consumers |
| rails `dims_shared_source` / `dims_shared_source_conflict` | the loud disclosure |
| wall record `width_ft` / `height_ft` on the run doc | the read, kept for the sheet |
| elevation sheet `width_label` / `height_label` | "56'-0"" rendered next to the face |
| `_wall_walk_detail.width_ft` / `eave_h` | per-face provenance of the walk |
| `_per_elevation_breakdown` callouts, material card | labels and claims, no ft² |
| model-height hypothesis (`_model_height_hypothesis_ft`) | already display-only, never a quantity |

### QUANTITY (must refuse under Evidence-and-Attribution-or-Null)
| consumer | lane | needs a height? |
|---|---|---|
| `walk_walls` body area (width × height × pct) | siding ft² | yes |
| `walk_walls` gable area (0.70 × width × rise) | siding ft² | **NO** |
| `blueprint_elevation` primary gable (½ × width × rise) | sheet ft² | **NO** |
| `blueprint_elevation` wing/secondary gable (½ × seg width × pitch rise) | sheet ft² | **NO** |
| `starter_lf` = Σ wall widths | LF | **NO** |
| `_perimeter_lf` / `footprint_perimeter_ft` = Σ wall widths | LF | **NO** |
| `eaves_lf` = Σ eave-wall widths | LF | **NO** |
| `rakes_lf` / `roof_planes.*.rake_lf` = f(width, rise) | LF | **NO** |
| `outside_corner_lf` = corners × height | LF | yes |
| `inside_corner_lf` = count × height | LF | yes |
| `lp_package` batten/starter course reading `footprint_perimeter_ft` | LF/PCS | **NO** |
| `lp_package` / pricing reading `siding_sqft` | ft² → $ | inherits |

### CHECKS that read a width but emit no quantity (left alone)
`box_model` (front width × left width vs printed footprint),
`opposing_walls_disagree`, `eave_rake_orientation` (g_sum / e_sum),
gutter-run vs wall-width cross-check, `footprint_closure`. These are
disclosure instruments; refusing them would blind the report.

## 4. LANES THAT COMPUTE FROM A WIDTH WITHOUT NEEDING A HEIGHT (blast radius)
Seven, listed above with **NO** in the height column:
1. primary gable area (walk_walls, 0.70 field factor),
2. primary gable area (elevation sheet, ½·w·rise),
3. wing/secondary gable area (elevation sheet),
4. `starter_lf`,
5. `_perimeter_lf` / `footprint_perimeter_ft` (→ lp_package batten + starter),
6. `eaves_lf`,
7. `rakes_lf` and per-plane `rake_lf`.
Height refusal stops none of these. That is why dart emitted 1,280.53 ft²
and 170 LF with every height refused.

## 5. CONSUMERS OF THE PERIMETER
- `starter_lf` (aggregation: perimeter IS the starter basis today),
- `measurements.footprint_perimeter_ft` (the key the engine reads),
- `lp_package_routes` batten/stacked-height + start-course math,
- `hover_field_register` / `door_field_register` registered as CONSUMED
  (registry pins the writer-key == reader-key contract),
- `ai_measure` writes the same key from the photo door (separate lane,
  untouched by this send).

## 6. THE FOUR-HOUSE REPLAY — WHAT REFUSES UNDER THE SPLIT (read-only, BEFORE building)

| house | unattributed widths | unattributed heights | quantity that REFUSES | quantity that SURVIVES |
|---|---|---|---|---|
| **boni** (EST-886440, run 5df22e6d) | **0** | **0** | **NOTHING** | siding 4,461.08 ft² · starter/perimeter 194 LF · eaves 284 · rakes 110 · OSC 140 · ISC 80 |
| **letrick** (EST-655664, run 725f8326) | **4 of 4** (front+back share 54'-0" p7; left+right share 30'-0" p7) | 2 (front+back share 9'-11 1/8" p1, conflicting) | **siding 1,532.70 ft²** (front body 534.6 + back body 534.6 + left gable 183.8 + right gable 183.8 + balance) · **starter/perimeter 168 LF** · **eaves 108 LF** · **rakes 64 LF** · **OSC 39.6 LF** | ISC 0 (already nil) |
| **tanis** (EST-564805, run 072e8c36) | 0 (all four widths already null) | 0 (all null) | nothing left to refuse | nothing — 0.0 ft², all lanes None |
| **dart** (EST-012540, run ff0d596e) | **2** (left+right share 56'-0" p4) | 6 (9'-2"/9'-4" shares, already refused) | **gable 1,280.53 ft²** · **starter/perimeter 170 LF** · **rakes 136 LF** · OSC 108 · ISC 74 | front width 58.0 stays on DISPLAY (its own quote, no competitor) — body still refused for want of a height |

### THE COST, NAMED
- **Boni loses NOTHING.** Every Boni face carries its own located quote —
  no share, no refusal. EST-886440's 4,461.08 ft² and 194 LF stand.
- **Letrick loses its ENTIRE derived read: 1,532.70 ft² and 379.6 LF**
  (168 starter + 108 eaves + 64 rakes + 39.6 OSC). That is the price of
  the ruling, stated plainly. Letrick's sharing is the *legitimate* kind
  the send-13/14 amendment was written to protect (front/back genuinely
  share one printed 54'-0"), and dart's is the *wrong* kind — and **no
  signal available today separates them**: both are horizontal opposing
  pairs drawing one located overall. Dart's 56'-0" is not the wrong FACE,
  it is the wrong LINE (truth 50'-0" on both sides), and shared-source
  cannot see that. So the rule that stops dart also stops letrick.
- Tanis loses nothing (nothing derived).
- Dart loses the two leaking lanes — which is the point.

## 7. GABLE PLACEMENT
Truth front 3 · left 3 · right 2 · back 0 versus read 0 · 1 · 1 · 0.
**Noted, not fixed in this pass** (per order).

## 8. WHAT THIS SEND THEN BUILT

**THE SPLIT** — `_unattributed_dim_paths` + `_attribution_gate`
(ai_blueprint.py), run at the top of aggregation so a replay of a stored
raw gates exactly like a fresh run, and idempotent.
- DISPLAY keeps everything: the wall record keeps `width_ft`, the mark
  rides `_width_unattributed` / `_height_unattributed`, the ledger rides
  `_dim_unattributed`, the readback carries `dim_unattributed`, and a new
  LOUD rail `dims_unattributed_quantity_refused` names each figure, its
  page and every face claiming it (EN + ES).
- QUANTITY refuses: `walk_walls(unattributed_faces=…)` refuses BODY AND
  GABLE on an unattributed face (the gable is the lane that needs no
  height, so nothing else would have stopped it) while the read width
  still rides the walk detail for display.
- TAINT: when a quote is ambiguous, EVERY consumer in that record is
  unattributed — a rake or a corner height computed from an unowned width
  is an unowned quantity. Pure quantity inputs with no display surface of
  their own (`roof_planes.*.rake_lf` / `eave_lf` / `wall_height_ft`,
  `corner_heights.i`, `gutter_runs.*.lf`) are nulled where they sit,
  because the plane sum otherwise rebuilds exactly what the face refusal
  just stopped (dart's rakes 136 LF did).
- PERIMETER UNDER THE SAME GUARD: `_perimeter_lf` refuses,
  `footprint_perimeter_ft` is not written, `starter_lf` is None and
  `_starter_basis` names the faces whose widths are claimed twice — so
  the lp_package starter/batten readers get nothing to read.
- SCOPE DISCIPLINE: the aggregation-time LF sweep runs
  `attribution_only=True`. The worker's full sweep already ran upstream;
  re-judging aliveness after the height build demotes model heights would
  have killed lanes for reasons OUTSIDE this ruling (it killed Boni's
  printed per-corner 126 LF in a pin — caught and narrowed).
- TWO DEFECTS FOUND WHILE BUILDING, both fixed: (1) the LF ledger was
  OVERWRITTEN on a second pass, which erased earlier kills and let a
  refused starter resurrect from a printed 16 LF fallback — it now MERGES;
  (2) a STALE `_rakes_plane_summed` flag turned a refused rake into 0.0 —
  the flag is cleared when no plane carries a live rake.
- METRIC CHANGED (`foreign_drafter_scoreboard.py`): the registry now
  tracks `unattributed_quantity_emitted` and `attributed_quantity_emitted`
  per drafter, plus `PRE_SEND127_LEAK` (dart: gable 1,280.53 ft², starter
  170 LF, perimeter 170 LF, rakes 136 LF) as the record of what a
  faces-derived metric was blind to. `earned_claim()` now returns
  CLAIM_NEITHER while ANY lane leaks, CLAIM_FAILS_SAFE at zero leaks, and
  the read-claim only when more than one drafter emits ATTRIBUTED
  quantity. Self-lifting coupling kept: the SEND-125 lexical ban still
  lifts by itself if the figures ever earn the read claim.

**THE REPLAY, AFTER THE BUILD (same read-only method, all four houses)**

| house | siding ft² | starter | perimeter | eaves | rakes | OSC | ISC |
|---|---|---|---|---|---|---|---|
| boni | 3,981.08 (unchanged) | 194 | 194 | 284 | 110 | 140 | 80 |
| letrick | 96.0 (was 1,498.62 on the same replay) | None | None | None | None | None | None |
| tanis | 0.0 | None | None | None | None | None | None |
| dart | **0.0 (was 1,280.53)** | **None (was 170)** | **None (was 170)** | None | **None (was 136)** | **None (was 108)** | **None (was 74)** |

- **Boni: byte-identical before and after** (verified by running the same
  replay on the pre-split code — 3,981.075 both times). EST-886440 loses
  nothing.
- **Letrick pays the cost, as reported in §6**: its 1,498.62 ft² replay
  total drops to 96.0 (an appendage/accent figure that rides its own dims,
  not a shared wall width), and all four LF lanes refuse.
- **Dart's two leaking lanes are closed.**

## 9. PINS + STAMP
`tests/test_send127_attribution_or_null_2026_08_25.py` — 13 pins:
detection (two faces one quote → unattributed + taint; own quote per face
→ nothing; one feature sharing with its own consumer → nothing), the gate
(marks, keeps the value, nulls quantity-only inputs, seam accounted,
idempotent), the walk (gable refuses without a height, width still on the
detail, surface `width_attribution`), aggregation (every width lane
refuses on the dart shape; an own-quote house is left alone), the readback
display lane + rail, the LF-ledger merge, and the three scoreboard states.
`tests/test_send125_claim_distinction_2026_08_24.py` updated to the new
metric. Seam `dims_unattributed_quantity_refused` registered.

STAMP: RECORDED 2026-08-25 12:00 UTC · 0baf5bc · CLEAN ·
**2871 passed, 9 skipped, 7 warnings in 462.70s** · census pin GREEN, 0
PENDING_CONVERSION · ingress smoke 4 passed. (+13 pins over SEND-126's
2858.)

Standing rules held: no cross-drawing borrowing, no estimate influenced
another, no job names in operative code, model heights hypothesis-only.
EST-886440 PROTECTED and provably unchanged. Purity pin holds. Gable
placement noted, not fixed. Symbols placement still NOT AUTHORIZED.
