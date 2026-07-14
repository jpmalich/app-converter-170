# BLUEPRINT SHAKEDOWN — TWO-LAYER SCORING (2026-07-14)
**Protocol:** pre-registered in `/app/memory/blueprint_preregistration.md` BEFORE the fix.
**Scored run (Layer A, declared in advance, no cherry-picking):** `367b739727aa4db4838e3a50d446aa09`
(cached-pages rerun of Howard's upload `e4afda3a…`, fixed prompt, inherited claude-opus-4-5-20251101).
An interim run `dee88ba8…` predated the starter-contract fix and is NOT scored (disclosed).

## LAYER B — engine on the sealed key geometry: 7/7 CONFORMANT
| Line | Key | Engine | Verdict |
|---|---|---|---|
| 38 Series Lap | 255 | 252 | PASS (−1.2%, pre-registered rounding-order residual) |
| 540 OSC | 8 | **8** | **PASS — better than pre-registered.** The corner-walk fallback (per-location whole-stick house + per-feature pooled chase) lands exactly on the key doctrine. The pre-registered "9 FAIL" referenced the C3-locator path, which this run never takes. |
| 440 4" ISC | 2 | 2 | PASS (new corner-walk fallback — blueprint packages previously NEVER composed ISC) |
| 540 Trim (windows) | 12 | 12 | PASS |
| 440 8" fascia+rake | 12 | **12** | **PASS — better than pre-registered.** The Phase 3 ×1.10 cushion no longer exists in the engine (removed post-Phase 3); pre-registration mispredicted a stale divergence. Disclosed, favorable direction. |
| Soffit | eaves-only 108 LF | eaves-only basis, no rake row | PASS |
| Starter | 165 LF / 4 boards | 168 − 3'×1 entry = 165 → 4 boards | PASS (engine owns the deduction — see contract note) |
| Composition | no J-channel / finish trim / coil; integer qtys | zero cross-domain, zero fractional | **PASS — the defect under repair** |

**Contract fix mid-work (disclosed):** first implementation had the aggregator
pre-deducting entry doors from starter — double-deducting against the engine's
own deduction. Final contract: extraction reports RAW perimeter; the ENGINE owns
the convention (single source). Pinned in `test_blueprint_cut.py`.

## LAYER A — scored extraction vs key (as-is)
| Input | Key | Scored run | Verdict |
|---|---|---|---|
| Roof pitch | 7/12 printed | `"7/12"` extracted, expressed 7/12, GREEN "Printed" badge | **PASS (finding 6 closed)** |
| Gable rise | 8.75' | 8.75' (pitch-computed per prompt) | **PASS (June finding closed on this path)** |
| Siding area | 2098.5 | 1954.5 (incl. chase) | −6.9% — extraction stochasticity (photo-path provenance note was −7.9% on identical inputs); per-line lap lands −8% vs key on THIS read |
| Chase faces | 145.5 ft² | present, 180 ft² | Presence PASS (absence was the defect); magnitude +23.7% — extraction residual, logged |
| Chase in OSC | 4 chase edges | structured appendage → feature pool 54 LF | Presence PASS; engine pools it |
| House corner walk | 4 OSC | 6 OSC | over-read +2 — extraction residual, logged |
| Starter basis | perimeter 168 | 168 raw + engine-deducts note | **PASS (finding: 108 eaves-only closed)** |
| Windows | 10 | 10 | PASS |
| Opening placement | per elevation sheets | all 14 attributed, 0 defaulted (front 5W+2E vs key 4W+1E) | Mechanism PASS (finding 7 closed); 1 window + E2 misattributed — extraction residual |
| Door classes | 1 entry + 1 slider | 3 entry + 1 slider | KNOWN CLASS RESIDUAL (pre-registered, Phase 3 §4 analogue) — slider itself now classed correctly; E2/door-11 misreads persist |
| 3D chase render | rendered or honestly absent | structured payload renders; position_frac 0.5 → amber "assumed" | PASS (finding 8 closed — no malformed box) |

## Verdict
- **Composition conformance: SHIPPED and conformant** — one composition source
  (engine), pinned; mixed-fixture pins extended to blueprint-sourced estimates;
  double-waste dead (LP lines can no longer reach `bakeWasteIntoLines` on any
  path); whole-stick everywhere; source governance stamped (photo outranks
  unapplied blueprint — the demo estimate verified still serving its photo run).
- **Extraction residuals (Layer A) are MODEL-quality items** — area drift −6.9%,
  chase magnitude +24%, corner-walk over-count, door classes. These are the
  evidence base for the UN-DEFERRED validated-model ruling (composition shipped
  first, as ordered).
