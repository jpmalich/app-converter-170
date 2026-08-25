# SEND-129 REPORT — SWEEP FIRST, THEN THE LIFT
2026-08-25 · Quantities only. Re-check probe:
`memory/send129_recheck_probe.py` (read-only — no estimate, no run, no
proposal written). Stamp in §7.

## 1. THE Δ-DIRECTION CONTRADICTION — CORRECTED
SEND-128 said "every face undershoots." **That sentence was wrong.**
The numbers, restated with their signs (drawn minus printed):

| face | printed | drawn | signed Δ | direction |
|---|---|---|---|---|
| letrick front | 54.00 | 54.73 | **+0.73 ft** | line-work runs **OVER** |
| letrick left | 30.00 | 29.41 | **−0.59 ft** | under |
| letrick right | 30.00 | 29.67 | **−0.33 ft** | under |

**Front runs OVER by 0.73 ft.** The sides run under. The undershoot is a
SIDE pattern (SEND-109's finding, which was about the sides), not a
universal one — the front is the only face here with no projection, so
its body span IS its silhouette, and it reads long, not short. The
generalisation was mine and it was not earned; the per-face signs stand
and no direction is claimed for a face that has not been read.

## 2. THE SWEEP — 14 SITES, WHAT HAPPENED TO EACH
Order honoured: the sweep landed BEFORE the lift was wired.

| # | site | class | disposition |
|---|---|---|---|
| 1 | `_lf_lane_nulled` assigned, not merged | A | **FIXED send-127** — merges |
| 2 | `_dim_evidence` whole-map assignment | A | **FIXED** — merges (`{**prev, **new}`), so a second pass cannot drop provenance a refusal reads |
| 3 | `_dim_shared_source` duplicates on re-run | A | **FIXED** — idempotent extend keyed on (quote, page, consumers) |
| 4 | `seam_accounting.account` not idempotent | A | **FIXED** — the same item is counted once; the disclosure of how much was refused can no longer drift upward |
| 5 | `_rakes_plane_summed` stale flag | B | **FIXED send-127** |
| 6 | `_eaves_plane_summed` stale flag (the live twin) | B | **FIXED** — cleared when no plane carries a live eave |
| 7 | `differs_from_derived_band`, `_gable_pitch_provenance` | B | **CLEARED ON INSPECTION, not a site**: both are written and read inside ONE pass (`_gable_pitch_provenance` is never read to decide anything). Reported as inspected rather than "fixed" — no change made |
| 8 | hover `or 0` on corner/starter LF | C | **FIXED** — `_key_refused()` distinguishes REFUSED (present and None) from a real zero; mitre counts and corner-post pieces refuse; the starter row says REFUSED instead of computing a door deduction off 0 |
| 9 | `lp_package_routes` perimeter `or 0` | C | **FIXED** — a refused perimeter prints a refused batten term, never "term = 0" |
| 10 | readback plane/corner rows `or 0` | C | **FIXED** — rows carry `eave_refused` / `rake_refused`, corners carry `basis: "refused"` + `refused_keys` |
| 11 | `ai_measure` second writer to `footprint_perimeter_ft` | D | **FIXED (named, not blocked)** — the photo lane stamps `_perimeter_writer`, and `seam_accounting.carry_refusals` records `_refused_overwritten` at the estimate seam. A fresh read may replace a refusal; it may not hide that it did |
| 12 | roof-pass corner FILL over a primary refusal | D | **FIXED** — the fill stands (it is a real read) and names the refused keys it replaced |
| 13 | `_printed_starter = starter_lf or eaves_lf` | E | **FIXED** — a lane the input-death sweep killed cannot re-source itself from another printed lane |
| 14 | `_gable_rise` traced→0.70 fallback | E | **CLEARED ON INSPECTION, not a site**: the blueprint lane always uses the 0.70 field factor with its basis label; there is no refused traced rise upstream of it to resurrect. Reported, not changed |

**Plus one refusal-shape fix the sweep exposed**: an EXPLICIT `None` in
`eaves_lf` / `rakes_lf` now stays a refusal through the measurement
assembly; only an ABSENT key (never read) reads as 0.

**And one leak the sweep exposed in my own send-127 work**: the walk
refused body AND gable on any unattributed face, but the
`_per_elevation_breakdown` lane computed the same body independently —
the two lanes disagreed. Now one mark drives both, with the right
granularity: an unattributed **WIDTH** refuses body and gable; an
unattributed **HEIGHT** refuses the **BODY only** (the gable reads no
height).

## 3. THE MARK BELONGS TO THE FIGURE, NOT TO THE FACE
The sweep surfaced a second-order case that changes the sizing. The
attribution mark is made about a SPECIFIC figure. Where the height build
DEMOTES the model's height to hypothesis and replaces it with a reading of
that face's OWN `FIRST FLOOR → TOP OF PLATE` chain, the shared figure is
gone from the quantity — refusing then would refuse evidence that is no
longer shared. So the height mark is **CLEARED AND NAMED** when
`height_src == "height_build"`, with the substitution printed on the
corroboration ledger. Letrick's front/left/right heights (9.08 ft) come
from their own chains; its back has none, so the back mark stands.

## 4. THE LIFT AS RULED
`attribution_lift.evaluate()` — structural conditions **plus** Δ inside
the **already-registered 3.8% elevation noise floor** (SEND-111,
`ocr_geometry.RULINGS_REGISTER` findings: two elevations of one house draw
the same real dimension up to 3.8% apart). **Derived, not chosen.** Δ IS
PRINTED EITHER WAY, lifted or refused, on the rail and in the readback
(`attribution_corroboration`, EN + ES copy).
- **Decision 2 honoured**: on a lift the **PRINTED figure feeds**; the
  drawn read confirms and never measures (`figure_that_feeds` is the
  printed number in every lifted verdict).
- **Standing limit registered in the module and pinned**: corroboration is
  a **WIDTH INSTRUMENT ONLY** — a height can never be corroborated this
  way because the height is the read's own ruler.
- The second read is produced by `linework_corroboration.read_face_widths`
  (the pipeline's own `derive_face_heights` + `wall_outline_from_segments`),
  run off the event loop in the worker. If it fails or is absent, the gate
  simply refuses, as built.
- Four structural refusals, each pinned: not RESOLVED · no wall-only
  figure (a silhouette is never the compared figure) · fence-margin
  warning (a neighbour's datum extent inside this face's fence) ·
  contested or itself-unattributed scale quote (the read would inherit
  the ambiguity it is resolving).

## 5. AFTER THE SWEEP AND THE LIFT — DID ANYTHING MOVE?

| house | siding ft² | starter | perimeter | eaves | rakes | OSC | ISC | moved? |
|---|---|---|---|---|---|---|---|---|
| **boni** | 3,981.08 | 194 | 194 | 284 | 110 | 140 | 80 | **NO — identical** |
| **letrick** | **1,498.62** (was 96.0 after the gate) | None | None | None | **64** | None | None | **YES — recovered** |
| **tanis** | 0.0 | None | None | None | None | None | None | NO |
| **dart** | 0.0 | None | None | None | None | None | None | **NO — still refuses** |

`earned_claim()` = **"fails safe on unfamiliar sets"** — FAILS_SAFE, now
over a swept pipeline rather than over fourteen open sites.
`unattributed_lanes()` = `{}`. **No lane to name.**

### THE SIZING CORRECTION HOWARD SHOULD SEE
The honest-sizing line in the ruling says letrick recovers **~368 ft² +
64 LF**. **The machine recovers more: 1,402.62 ft² + 64 LF** (96.0 of the
1,498.62 was never lost). The extra is not a leak — it is §3:
- front width 54.0 CORROBORATED (Δ +0.73 ft = 1.35%, inside the floor) →
  front body **490.3 ft²** returns, on a height (9.08) read from the
  front's own datum chain, not from the contested 9'-11 1/8";
- left/right widths CORROBORATED (Δ −0.59 / −0.33) → their bodies
  **272.4 + 272.4** and gables **183.75 + 183.75** return;
- **STILL REFUSED**: the BACK — its width shares 54'-0" and its line-work
  read has **no wall-only figure** (no plate-terminated corners), so the
  back body stays out; **starter / perimeter 168 LF** (the sum needs all
  four widths), **eaves 108 LF** (the eave pair includes the back),
  **OSC 39.6 LF** and **ISC** (corner heights ride the contested quote).

One correction to SEND-128 inside that: the back's blocker is **the
missing wall-only figure**, not the contested scale. The contested-scale
refusal is real and is pinned, but on this house it is the second lock,
not the first.

### DART — WHY NOTHING COULD LIFT
No elevation drawing is located for any of dart's four faces, so
`read_face_widths` returns NOT_ATTEMPTED four times. There is no second
read to confirm the 56'-0" claimed by left and right. Dart's 1,280.53 ft²
and 170 LF stay refused.

## 6. WHAT IS STILL OPEN (unchanged by this send)
Gable placement (truth 3/3/2/0 vs read 0/1/1/0) — noted, not fixed.
Height corroboration needs a DIFFERENT instrument (line-work cannot do
it). Symbols placement still NOT AUTHORIZED.

## 7. STAMP
RECORDED: 2026-08-25 20:33 UTC · 935f267 · CLEAN
RESULT: 2886 passed, 9 skipped, 8 warnings in 476.22s (0:07:56)
CENSUS: census pin GREEN — 0 PENDING_CONVERSION · INGRESS SMOKE: 4 passed
(+13 pins over SEND-128's 2873: `test_send129_sweep_and_lift_2026_08_25.py`
— the sweep half and the lift half, including the four structural
refusals, the printed-figure-feeds decision, the registered floor, and
the width-instrument-only limit.)

Standing rules held: no cross-drawing borrowing, no estimate influenced
another, no job names in operative code, model heights hypothesis-only.
EST-886440 PROTECTED and byte-identical across the sweep and the lift.
Purity pin holds.
