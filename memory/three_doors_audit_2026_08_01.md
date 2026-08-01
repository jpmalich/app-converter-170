# THREE DOORS ACCURACY AUDIT — REPORT ONLY, NOTHING BUILT
Date: 2026-08-01 · Doors: HOVER (`routes/hover.py`) · BLUEPRINT (`routes/ai_blueprint.py`) · PHOTO AI (`routes/ai_measure.py`)
Ordering: BLAST RADIUS — can it put a wrong number on a quote, and on how many doors. Fix cost deliberately omitted (per ruling).

---

## Q1 — ONE PIPELINE OR THREE COPIES

### The layer map (what is actually shared)

```
LAYER 1  EXTRACTION (per door, unavoidable — different sources)
  HOVER:     pdfplumber text → Claude Sonnet text-read → strict JSON fields
  BLUEPRINT: pdfium page renders → Claude vision → walls/windows/doors JSON
  PHOTO:     photo set → Claude vision (two-phase A/B + reconciler) → walls/openings JSON

LAYER 2  AGGREGATION → measurements dict   ← THIS LAYER IS THREE COPIES
  HOVER:     fields land directly (measured figures pass through)
  BLUEPRINT: _aggregate_to_hover_shape (ai_blueprint.py:483) — OWN COPY
  PHOTO:     _aggregate_to_hover_shape (ai_measure.py:1845)  — OWN COPY, different math

LAYER 3  DERIVATION → lines                ← ONE SHARED ENGINE (GOOD)
  _build_lines (hover.py:2342): all vinyl/ascend/windows rows, all three doors
  rebuild_lp_tab_lines / assemble_lp_package: all lp_smart rows, all three doors
  Shared everywhere: waste bake, color tier, trade-spec widths, whole-unit
  rounding (_order_whole_units), ID stamping (_stamp_item_ids), catalog binding.
```

**Verdict: the DOLLAR layer (rates, waste, rounding, price, ID binding) is one
pipeline — every fix there reaches all three doors.** The vinyl-drifted-from-LP
class does NOT exist at layer 3. It exists at layer 2: the two AI doors each
carry a private copy of the measurement-assembly math, and those copies have
already diverged. Every place a door does its own math, named:

| # | Own math | HOVER | BLUEPRINT | PHOTO | Diverged? |
|---|---|---|---|---|---|
| 1 | **Gable triangle area** | inside HOVER's measured siding_sqft | **0.5 × width × pitch-computed rise** (bp:498–529) | **0.7 × width × read height** (C4 ruled convention, am:1954) | **YES — 40% apart** |
| 2 | **Starter basis** | measured `starter_lf` | floor-plan perimeter + `_starter_basis` provenance note (bp:616–629) | `raw.starter_lf or eaves_lf` fallback, no basis note (am:2023) | **YES** |
| 3 | **Outside-corner LF** | measured LF + count | printed read, else 4 × avg height (bp:656) | per-corner from per-wall heights `_corner_lf_from_walls`, else AI, else 4 × avg (am:2029) | YES (fallback ladders differ) |
| 4 | **Corner COUNTS** | measured | read from plan (bp:693–694) | **never lands in measurements** (locations machinery is LP-engine-only) | **YES — see F5** |
| 5 | **Eaves defense** | measured | gable-wall recompute override (bp:606–614) | raw Claude value, no correction | YES |
| 6 | **Wall-height clamps** | n/a (measured) | printed dims at face value | <4 ft silently replaced by avg/story default; 4–7 ft kept + flagged (am:1909–1926) | per-source, but see F7 |
| 7 | **Opening dedupe/snap/symmetry** | n/a (schedule measured) | none (printed dims trusted) | dedupe → symmetry → snap-to-standard (am:1872–1874) | per-source, appropriate |
| 8 | **Window-openings builder** | `_build_window_openings` (shared with blueprint) | same shared builder | **own copy** `_build_vero_openings_from_ai` (am:1154) | YES (two builders) |
| 9 | **`door_count` roll-up** | extracted | **never summed** | **never summed** | **YES — see F4** |
| 10 | **Opening counts basis** | schedule | windows/doors arrays | counts from schedule, opening_sqft from deduped list (two bases, documented Iter 57i) | minor |

Rows 1, 2, 4, 9 put different numbers on the same house depending on which door
it walks through. Rows 6–7 are legitimately per-source (a photo needs defenses a
printed dim does not) — they belong in a door-specific "source adapter", not in
a copied aggregator where they silently drift.

---

## Q2 — PROVENANCE PER DOOR

### What is stamped today

| Stamp | HOVER | BLUEPRINT | PHOTO |
|---|---|---|---|
| `_source` on estimate's stored measurements (frontend apply) | `"hover"` | `"blueprint"` | **NOTHING — never stamped** |
| `_source_kind` in aggregator | none | `"blueprint"` | **none** |
| Scale confidence | n/a (measured) | `_ai_scale_confidence` | `_ai_scale_confidence` (high/med/low) |
| Per-wall confidence 0–100 + reasoning | n/a | n/a | emitted + surfaced as chips |
| Roof type confidence | n/a | pinned 1.0 (read from print) | 0–1, threshold 0.8 **enforced frontend-only** |
| Basis notes | line-note formulas | `_starter_basis`, `_gable_pitch_provenance` | dormer width_source, corner tiers (LP path only) |

**The blunt answer to "does the code know a photo read is a suggestion": NO.**
Confidence is a LABEL everywhere and a GATE nowhere in the backend. A wall
Claude marks confidence 12 ("barely visible / inferred") enters `siding_sqft`
with exactly the same authority as a HOVER-measured figure. The only hard block
in the whole photo path is the zero-data guard (Phase B total failure →
frontend hard-block, Iter 79j.51). Your region-crop probe went 2-of-5 and
nothing in the derivation would have treated those five reads differently.

### Every place an inferred number can reach a dollar without a human confirming it

**P1 — LP-pair seeding from an UNAPPLIED photo run (`estimates.py:306–360`, Iter 99).**
Creating the LP pair for an estimate with no stored measurements silently pulls
the LATEST completed `ai_measure_runs` doc — **whether or not the contractor
ever clicked Apply on that run** — and seeds priced lp_smart lines from it
(catalog mat prices bound, qty from `_build_lines`). A run the contractor
looked at, distrusted, and abandoned still becomes dollars the moment they hit
Pair-to-LP. This is the one clean violation of the human-gate doctrine.
(Asymmetry inside the asymmetry: only `ai_measure_runs` is consulted — a
blueprint run never seeds the pair.)

**P2 — Silent height substitution inside the "reviewed" preview (am:1909–1919).**
A junk wall read (<4 ft) is replaced by the average height or a story default —
up to **18.0 ft injected** — with NO flag, NO note, NO chip. The 4–7 ft band
gets an amber flag; the more aggressive substitution below it gets nothing. The
contractor's Apply click "confirms" a number the preview never disclosed as
invented. (Contrast: it sits beside the best-documented provenance in the photo
door — the dormer/corner machinery — so this is an omission, not a style.)

**P3 — The Apply gate is one click for ~30 rows.** Once Apply is pressed, every
derived quantity — high-confidence and low — lands identically. `qty_pending`
exists only for always-emit presence rows (Tear-Off/Dumpster). There is no
"this row is driven by a low-confidence read" marker on any line.

**P4 — Authority persists without identity.** Photo apply stores NO
measurements and NO `_source` on the estimate (see F3). Where measurements DO
get stored (hover/blueprint, or LP materialize), later `rederive` replays them
with full authority; nothing downstream ever asks "was this measured or
inferred?" — the `_source` stamp exists but has zero consumers in derivation.

Properly gated (credit where due): blueprint/photo LP apply goes through the
server-side materialize gate with a governing `lp_source_run_id` archived
(ruled 2026-07-25) — human-clicked, run-bound, idempotent. Reconciliation
failures can never masquerade as done (status parity, ruled 2026-07-17).
Human-typed quantities survive every re-derive (verified in suite).

---

## Q3 — CONSUMED VS DROPPED, PER DOOR

### HOVER — Class B register carried in (sealed 2026-07-28)
26 fields registered: 22 CONSUMED with derivation named, 4 deliberately
NOT_CONSUMED with reasons (footprint_area, united_inches,
per_elevation_siding, roof_area). Published-figure detector
(`HOVER_PUBLISHED_FIELDS`) maps every printed figure to a schema key. This door
is clean — with ONE exception found by this audit:

**F-REG — the register contains a FALSE "CONSUMED" entry.**
`window_bottom_width_total_lf` is registered CONSUMED by "starter deduction at
window sills" (`hover_field_register.py:28`). **No such consumer exists
anywhere in the codebase.** The only starter deduction is entry-door widths
(`lp_package.py:616–628`). The field is extracted, registered as consumed, and
then dropped — the exact silent-loss class the register was built to catch,
hiding inside the register itself.

### BLUEPRINT — no register exists for this door
Consumed: walls (width/height/gable/dormer/pct), window & door schedules
(dims, qty, type), corners (counts + LF), eaves/rakes (with gable-wall
correction), starter (perimeter-derived), vents, shutters, stories, appendage
faces, pitch (drives gable rise), overhang_in.
**Dropped by schema design:** plans routinely PRINT soffit/overhang detail
sections, frieze/trim callouts, and drip-edge specs — the blueprint schema has
no `soffit_sqft`, no frieze LF, no `drip_edge_lf`, no `total_trim_sqft`, no
`footprint_perimeter_ft` key at all. Printed = measured-grade, and these are
the SAME fields whose Hover drops (soffit #1, frieze #2, footprint #5) cost a
day each to find. Downstream the LP soffit split falls back to eaves × overhang
inference even when the plan printed the real figure.
`door_count` counted per-type but never summed → see F4.

### PHOTO — no register exists for this door
Consumed: walls (with clamps), openings (dedupe→symmetry→snap), schedules
(counts + perimeter), accent/appendage attribution, dormers[] (multi, with
width_source provenance), corner LF from per-wall heights, eaves/rakes/starter
raw reads, vents, shutters, stories, roof type, annotations (authoritative
overrides).
**Dropped / never landing:**
- `door_count` never summed → see F4.
- Corner COUNTS never land in measurements → per-corner Q13/Q12 rules
  silently inactive on the `_build_lines` path → see F5.
- Per-wall `confidence` / `confidence_reasoning` — surfaced as chips, consumed
  by NO derivation and NO gate (see Q2).
- Soffit/frieze/drip-edge — legitimately unmeasurable from photos, but the door
  emits no "this source cannot see X" manifest, so the estimate shows absence
  identically to a dropped field.

**Structural point:** the tripwire that made Hover auditable — "a published
figure with no schema key FAILS; a consumed field that stops being consumed
FAILS" — exists ONLY on the Hover door. The two AI doors have no
consumed-vs-dropped register, so every silent loss found below had no alarm.

---

## FINDINGS — RANKED BY BLAST RADIUS

**F1 — Gable area: two doors, two formulas, 40% apart.** Photo: 0.7 × w × h
(C4 ruled 2026-07-13, "angle-cut coverage IS the estimating convention, NOT the
true triangle ÷2"). Blueprint: 0.5 × w × pitch-computed rise — the true
triangle the C4 ruling explicitly rejected. Same gabled house → blueprint door
credits ~29% less gable siding than the ruled convention, on EVERY gabled
blueprint job, flowing straight into siding SQ dollars on both vinyl and LP
paths. Needs a ruling: either C4 governs all doors, or blueprint's
printed-geometry basis is a deliberate exception — today it's an accident.
*Wrong number on a quote: YES. Doors: 1 (blueprint), inconsistency across 2.*

**F2 — Dollars from a run no human confirmed (P1 above).** LP-pair creation
seeds priced lines from the latest completed photo run even if it was never
applied. *Wrong number on a quote: YES (whatever the abandoned run said).
Doors: 1 (photo). Doctrine violation: the only unconditional one found.*

**F3 — The photo door is locked out of the shared rebuild, and its numbers
carry no identity.** Photo apply (siding-kind) merges lines but stores NO
measurements on the estimate → `rederive` 409s ("import a HOVER/Blueprint
first"). The "ONE SHARED REBUILD, EVERY FAMILY" door (ruled 2026-07-31)
therefore covers 2 of 3 doors: a spec change (overhang, waste, widths) or a
rule fix landing after a photo apply can never replay onto that estimate — its
quantities freeze at apply-day rules. And because photo apply stamps no
`_source` (hover and blueprint both do), any photo measurements that DO land
(via LP materialize) are indistinguishable from measured ones forever after.
*Wrong number on a quote: YES (stale rules = yesterday's numbers). Doors: 1.*

**F4 — `door_count` never lands on either AI door.** Both AI doors count
entry/patio/garage doors but never write the `door_count` sum Hover provides.
Consumers: Caulking per-color (`window_count + door_count`, hover.py:1373) and
J blocks (`door_count / 2`, hover.py:1017) — both under-count on every photo
and blueprint job that has doors (every job). Small rows, systematic, two
doors. *Wrong number on a quote: YES. Doors: 2.*

**F5 — Per-corner rules silently inactive on the photo `_build_lines` path.**
`_osc_lp_pcs` / `_isc_540_pcs` per-corner math (Q13 min-1-per-corner, Q12, and
the never-average tall-corner rule sealed off 261 Haugh's hidden 18'5" corner)
requires `outside_corner_count` / `inside_corner_count` — which the photo
aggregator never sets. The photo door falls to pooled ÷16, the exact math the
261 Haugh finding retired. (The LP-engine path has its own corner-location
machinery; the `_build_lines` mirror does not.) *Wrong number on a quote: YES
(under-counts corners the sealed rule was built to catch). Doors: 1.*

**F6 — Photo starter falls back to EAVES.** `starter_lf = raw or eaves_lf`:
on any gabled house eaves exclude the gable ends, so when Claude omits
starter_lf the start course under-runs the footprint by both gable-end widths.
Blueprint computes perimeter and writes a `_starter_basis` provenance note;
photo writes neither. *Wrong number on a quote: YES (gabled houses, when the
fallback fires). Doors: 1.*

**F7 — Silent 18-ft substitution (P2 above).** The <4 ft clamp injects
avg/story defaults into `siding_sqft` with no flag while the milder 4–7 ft case
IS flagged. *Wrong number on a quote: YES when a junk read occurs — and it's
invisible when it does. Doors: 1.*

**F8 — Confidence is decoration (P3/P4 above).** No backend gate, discount,
or per-line marker anywhere; roof-type's 0.8 threshold lives frontend-only;
`_source` stamps have zero derivation consumers. This is the structural
enabler of F2/F7 rather than a defect with its own number on a quote.
*Doors: structurally all 3 (bites on photo).*

**F9 — Register integrity (F-REG above + no registers for AI doors).** The
instrument that guards consumed-vs-dropped has one false CONSUMED entry and
covers one door of three. *Wrong number on a quote: not directly — it's the
alarm system, and today two doors have no alarm.*

**F10 — Minor asymmetries (recorded, low blast):** blueprint-only eaves
gable-correction (photo trusts raw); two vero-openings builders (row 8 above);
photo opening_sqft vs counts computed from two different bases (documented);
LP-pair seeding consults only photo runs, never blueprint runs.

---

## WHAT IS ALREADY RIGHT (so it is not re-litigated)
- One derivation engine at the dollar layer, all doors: `_build_lines` +
  `rebuild_lp_tab_lines`/`assemble_lp_package`, shared waste bake, whole-unit
  rounding, color tier, trade-spec widths, ID binding at birth.
- LP materialize apply-gate: server-side, human-clicked, governing run
  archived and stamped (`lp_source_run_id`).
- Status parity: a failed reconciliation can never present as done.
- Human-typed quantities survive every re-derive (suite-enforced).
- Photo zero-data hard block; dedupe/symmetry/snap ladder; dormers[] with
  width_source provenance; corner-location presence guarantee on the LP path.
- Hover Class B + published-field registers (minus the F-REG entry).

No code was changed. Awaiting rulings per finding before any build.
