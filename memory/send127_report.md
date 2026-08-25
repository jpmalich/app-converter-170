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
See §9 below — written after the build, with the pins and the stamp.
