# SEND-67 — AUTHORIZED RE-ATTRIBUTION + CORRECTED BASELINE (2026-08-20)

Authorized by Howard (SEND-67). The ORIGINAL baseline (SEND-63 item 1,
PRD entry 2026-08-19) is PRESERVED — nothing above it was edited. This
file appends the corrected numbers beside it.

## 1. Which of the three are CONFIRMED — ALL THREE
All three zones are provenance HUMAN (drawn by hand, binding):
- `ba134619` p1 · 204.90 ft²
- `08126e7d` p1 · 106.30 ft²
- `1e5b2460` p1 · 330.54 ft²  (recorded at 324.63 in its event — the
  zone was edited after the event snapshot; the event keeps its own
  number)
Total 641.74 ft², tagged FRONT, centroid band says REAR → re-attributed
FRONT → BACK by centroid-band resolution.

## 2. The quantity delta — stated as numbers
- Superseded until now: FRONT (derived 490.32 ft²) — the front group
  carried 1,192.51 ft² (550.77 real front + 641.74 mis-tagged rear).
- Now supersede: BACK (derived 0.0 ft², named refusal: contested rails
  9'-1" vs 9'-11").
- **Siding line: 25.94 SQ before → 25.94 SQ after. THE LINE DID NOT
  MOVE.** Why, exactly: rear REFUSES, so its derived contribution was
  already 0 with a named refusal; the mis-tagged pieces were already
  summing into the class total under front's group. The defect was a
  live ATTRIBUTION error, not (yet) a live dollar error — it would have
  moved money the moment front's zones were edited independently or
  rear's derivation landed. The fix closes that trap.
- Tracking event `zones.face_reattribution` recorded on EST-569367
  naming what moved, why, and who authorized it (Howard, SEND-67) —
  same shape as the EST-803966 user_error_reversal.

## 3. SEND-66 census result (report only, nothing auto-corrected)
52 zones examined across every estimate holding zones.
- Tag disagrees with centroid band: 3 — exactly the three above.
  **No OTHER confirmed mis-tagged zone exists on any estimate.**
- 1 additional open item, NOT touched (needs Howard's ruling): EST-713272
  (Boni MUV rebuild test) zone `33e4b47a`, 95.80 ft², page 2, legacy
  provenance (binding), STRADDLES the LEFT and RIGHT drawings — the band
  cannot resolve it and re-drawing the shape may be the real answer.
- 3 orphaned PROPOSED gable zones from crashed test rigs were deleted
  (test artifacts on already-deleted test estimates; zero money).

## 4. Corrected baseline IN FULL (same denominator: 8 surfaces)
Restated per-face event attribution after re-attribution:

| face  | CORRECTED            | ADDED_FROM_SCRATCH                    |
|-------|----------------------|----------------------------------------|
| front | 550.77 ft² (1)       | —                                      |
| back  | —                    | 204.90 + 106.30 + 324.63 ft² (3)       |
| left  | — (metric ts gap)    | 54.01 + 125.71 ft² (2)                 |
| right | 293.96 ft² (1)       | 114.61 + 53.82 ft² (2)                 |

Split against the 8-surface denominator: **3 corrected, 5 missed —
UNCHANGED** as a split; what changed is that REAR now owns its own
641.7 ft² of missed area (it was booked under FRONT). This restated
split is what line-work gets measured against.

## 5. Prediction scoring UNAFFECTED — confirmed
The SEND-63 prediction scoring was about per-face vertical and
horizontal displacement of proposals, not about which face owned an
added zone. Nothing here re-scores it. Do not re-score it.
