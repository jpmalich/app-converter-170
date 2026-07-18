# Letrick Sealed-Key Hygiene Audit (2026-07-18, per Howard's standing rule)
RULE: every sealed-key value carries its basis — TAPED (direct reading) or
DERIVED (formula from taped inputs, formula stated). A DERIVED value whose
arithmetic doesn't reproduce from stated inputs is a FLAG.
Key corrected same day (Class-1, backup:
backups/letrick_hand_takeoff_key_pre_exposure_correction_2026-07-18.py).

## The June catch this rule would have made
Pre-correction, front height 8.96' was DERIVED from 25 courses × ~4.30"
exposure — but the key carried NO exposure input at all. The hygiene check
fails it two ways: (1) DERIVED value with an UNSTATED input; (2) once the
taped exposure (4.25") is stated, 25 × 4.25 ÷ 12 = 8.854 ≠ 8.96 — arithmetic
doesn't reproduce. The back wall reproduced fine (28 × 4.25 = 9.917 ≈ 9.92),
which is exactly the internal-consistency signal Howard used.

## Inputs
| Value | Basis | Formula / reading | Reproduces? |
|---|---|---|---|
| exposure_in 4.25" | TAPED | field tape; reconciles back wall | — |
| front height 8.854' | DERIVED | 25 × 4.25 ÷ 12 | ✓ (exact) |
| back height 9.92' | DERIVED | 28 × 4.25 ÷ 12 = 9.917 | ✓ (rounded to 9.92) |
| front sqft 478.1 | DERIVED | 54 × 8.854 = 478.1 | ✓ |
| back sqft 535.7 | DERIVED | 54 × 9.92 = 535.68 | ✓ via rounded height; exact-height gives 535.5 — Δ0.2 rounding-order FLAG (minor) |
| stepped sides ~566.4 | DERIVED | side-wall dims NOT stated in key | ⚠ FLAG — unstated inputs (the "~" is honest but unreproducible) |
| gables 367.5 | DERIVED | 525 raw × 0.7 | ✓ arithmetic; ⚠ FLAG — 525 raw gable area's dims not stated |
| walls_gables 1947.3 | DERIVED | 478.1+535.7+566.4+367.5 = 1947.7 | ⚠ Δ0.4 FLAG — inherited rounding (pre-correction 1953.0 vs sum 1953.4, same 0.4) |
| chase_outer 47.97 | DERIVED | dims not stated | ⚠ FLAG — unstated inputs |
| chase_sides 97.56 | DERIVED | 2.58 × 18.91 × 2 = 97.58 | ✓ (Δ0.02 trivial) |
| raw_sqft 2092.8 | DERIVED | 1947.3+47.97+97.56 = 2092.83 | ✓ |
| eaves 108 | DERIVED | 2 × 54 (54 TAPED, print-confirmed) | ✓ |
| rakes 69.6 | DERIVED | 4 × 17.4 (17.4 TAPED) | ✓ |
| fascia_rake 177.6 | DERIVED | 108 + 69.6 | ✓ |
| perimeter 168 | TAPED | direct | — |
| starter 165 | DERIVED | 168 − 3 (entry) | ✓ |

## Lines
| Line | Reproduces from stated derivation? |
|---|---|
| Lap 254 | ✓ 20.93 sq × 1.1 = 23.02 × 11 = 253.2 → 254 (corrected from 255) |
| OSC 8 | ✓ count logic stated (4 + 4) |
| ISC 2 | ✓ |
| 540 Trim 12 | ⚠ FLAG — derivation lists sides ("10 windows 4-side + entry 3-side + patio 3-side") with NO arithmetic reaching 12. Known open finish-trim question. Layer B independently reproduces 12 via 177 LF ÷ 16 — noted, not reconciled into the key. |
| Fascia/rake 12 | ✓ 177.6 ÷ 16 = 11.1 → 12 |
| Soffit 108 LF | ✓ eaves-only ruling |
| Starter 165 LF / 4 boards | ✓ ceil(165 ÷ 48) = 4 |

## Flags summary (5)
1. stepped sides 566.4 — unstated side-wall dims.
2. gables 525-raw — unstated gable dims.
3. chase_outer 47.97 — unstated dims.
4. walls_gables Δ0.4 rounding drift (carried into raw_sqft rounding, now ≈ exact).
5. 540 Trim 12 — stated derivation doesn't arithmetically reach the qty.
None change any verdict; 1–3 are Howard's to backfill if he wants the key
fully self-reproducing.

## Layer B re-score on corrected key (item 1b, re-run 2026-07-18)
Lap: key 254 vs app 252 → −0.79% PASS (pre-correction: 255 vs 252, −1.2%).
All other lines LF-based → unchanged (540 trim 12↔12, fascia 12↔12, OSC 8↔8,
ISC 2↔2, starter 165↔165, soffit basis unchanged). NO VERDICT FLIPS, as
predicted at −0.27% raw-area delta.

## Elevation-sheet inheritance (spec §3 updated)
DERIVED values wear the TAPED-DERIVED chip variant (green fill + dashed white
border), never the bare TAPED badge. Mock updated: front SIDING HEIGHT
(starter → soffit) 8'-10¼" TAPED-DERIVED · wall area 478.1 DERIVED.
