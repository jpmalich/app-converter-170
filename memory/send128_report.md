# SEND-128 REPORT — CORROBORATION, REPORTED BEFORE THE LIFT IS BUILT
2026-08-25 · Quantities only. Probe: `memory/send128_corroboration_probe.py`
(read-only — no proposal, no run, no estimate written; it calls the
pipeline's own `height_read.derive_face_heights` +
`linework_read.wall_outline_from_segments`, so every figure below is the
pipeline's, not a re-implementation).

## 0. THE PLAIN ANSWER OWED
`earned_claim()` computes **"fails safe on unfamiliar sets"** — FAILS_SAFE,
for the first time on the new metric. `unattributed_lanes()` is `{}`;
no lane leaks; `drafters_emitting` (attributed quantity) is 0, which is
why it is FAILS_SAFE and not the read claim. **No lane to name.**

## 1. PER FACE, ALL FOUR HOUSES — IS A LINE-WORK WIDTH AVAILABLE?

| house | face | model width | line-work wall-only | Δ | state |
|---|---|---|---|---|---|
| **boni** | left | 39.0 | — | — | line-work **INDETERMINATE**: "all spanning boundaries sit at one corner" |
| boni | right | 40.0 | — | — | **NOT_ATTEMPTED**: datum pair not located on this drawing |
| boni | front / back | 58.0 / 34.0 | — | — | no wall-only figure computed on front/back today (see §3) |
| **letrick** | front | 54.0 | **54.73** | **0.73 ft** | RESOLVED p1, body span = silhouette (no projection on this face) |
| letrick | back | 54.0 | geometry RESOLVED | **—** | **no usable scale**: the only face scale is the CONTESTED height (9'-11 1/8" vs 9-1), and that quote is the unattributed one |
| letrick | left | 30.0 | **29.41** | **0.59 ft** | RESOLVED p2, wall corners [19.45, 42.76]%, fence applied, **no fence-margin warning** |
| letrick | right | 30.0 | **29.67** | **0.33 ft** | RESOLVED p2, wall corners [54.71, 77.98]%, fence applied, **no fence-margin warning** |
| **tanis** | all four | all null | — | — | **NOT_ATTEMPTED ×4**: datum pair not located on p3/p4; no left elevation located |
| **dart** | all four | 58.0 / null / 56.0 / 56.0 | — | — | **NOT_ATTEMPTED ×4**: no front/rear/left/right elevation drawing located at all |

Line-work systematically UNDERSHOOTS the printed figure on every face
where both exist (−0.73, −0.59, −0.33) — the same direction SEND-109
recorded. Not one overshoot.

## 2. WHAT "AGREEMENT" MEANS — AND THE HARD CUT IS UNAVOIDABLE
Reported as magnitudes, XX-shape, no boolean: **0.33 / 0.59 / 0.73 ft.**
That is the whole honest content of the comparison.

**But a lift is a boolean by nature** — the quantity either feeds or
refuses. So a cut cannot be avoided by reporting the magnitude; it can
only be avoided by NOT gating on the magnitude at all. The two
formulations that need no number:
- **(A) STRUCTURAL, magnitude reported not gating**: corroborated = the
  line-work read RESOLVED on that face's own drawing, produced a
  WALL-ONLY figure (plate-terminated corners), carries no fence-margin
  warning, and its scale quote is not itself unattributed. The Δ is
  printed on the card and never decides. Cost: a 3-ft disagreement would
  still lift.
- **(B) MAGNITUDE-GATED**: same four structural conditions PLUS Δ inside a
  chosen number. Every candidate number is a choice: 0.35 ft admits
  letrick's right and rejects its left and front; 0.60 ft admits left and
  right, rejects front; 0.75 ft admits all three; a proportional cut
  (e.g. 2% of the figure = 0.60 ft on 30 ft, 1.08 ft on 54 ft) admits all
  three by scaling the allowance with the wall.
**BROUGHT TO HOWARD** — the number is not the agent's to pick, and (A)
vs (B) changes what letrick recovers. Nothing is built until this is
ruled.

**A second decision is owed with it**: when a face IS corroborated, WHICH
figure feeds the quantity — the printed model figure (30.0) or the drawn
line-work figure (29.41)? The undershoot is systematic, so this is not a
coin flip; it is 0.59 ft × the wall, every wall.

## 3. THE REQUIRED CHECK — CAN A CORROBORATION INHERIT THE SAME AMBIGUITY?
**YES, IT CAN, AND IT ALREADY DOES ON ONE REAL FACE.** Three inheritance
paths exist; the third is live:

1. **The band** (which drawing is read) is carved from the face's own
   TITLE. If a title appears twice, Ruling YY refuses that face BEFORE
   the line-work runs, so an ambiguous band cannot reach the read.
   Structurally clean — a title share cannot be inherited.
2. **The fence** (which strokes belong to this face) is the face's own
   datum extent, applied verbatim. SEND-84's `fence_margin_warning`
   fires when a neighbouring drawing's datum extent reaches INSIDE the
   fence — in that state the strokes inside the fence may not be this
   face's, and the read is ambiguous in its own right. Checked:
   letrick's left/right/front reads carry `fence_margin_warning: null`,
   so they are clean here. **The lift must refuse when this warning is
   present.**
3. **The scale** (pixels → feet) comes from the face's own datum-chain
   QUOTE. This is the inheritance path. **Letrick's BACK face has no
   scale except the CONTESTED 9'-11 1/8" — which is the very quote the
   attribution gate flagged (shared with the front, `conflicting: true`).
   A back-width "corroboration" would be measured with the ruler whose
   ownership is in dispute: circular, and it would lift the front/back
   width share using the front/back height share.** So the back face
   must NOT be lifted, on the exact ground Howard named.
   Letrick's left/right/front scales come from each face's own
   FIRST FLOOR → TOP OF PLATE chain (9.08 ft) which is NOT in the
   shared-source ledger — clean.

**Corollary, reported not built**: line-work can NEVER corroborate a
HEIGHT, because the height IS its ruler. Any height lift by line-work
would be circular by construction. Heights need a different second read.

## 4. WHAT MOVES, UNDER (A) OR (B) WITH THE Δ's ABOVE
### LETRICK — recovers the SIDES only
- left + right widths corroborated (Δ 0.59 / 0.33, clean scale, no fence
  warning) → the two side **GABLES return: 183.8 + 183.8 = 367.6 ft²**
  (a gable needs a width and a rise; the 8.75 ft rise quote is not in the
  shared ledger). Under (A) the **front width also lifts** (Δ 0.73).
- **RAKES 64 LF** can return with the sides: the plane `rake_lf` was
  tainted by the same 30'-0" record.
- **STILL REFUSED**: front + back BODY **1,069.2 ft²** (534.6 each) —
  their heights ride the contested 9'-11 1/8" share and no height can be
  corroborated by line-work (§3 corollary). **STARTER / PERIMETER 168 LF**
  — the sum needs all four widths and the BACK width cannot be lifted.
  **EAVES 108 LF** — the eave walls are front+back; back is refused.
  **OSC 39.6 LF** — corner heights ride the same contested quote.
- Net: letrick recovers **367.6 ft² + 64 LF** of the 1,532.70 ft² and
  379.6 LF it lost in SEND-127. **It does not get its read back — it gets
  its sides back.**

### DART — recovers NOTHING
No elevation drawing is located for ANY of its four faces, so the
line-work read is NOT_ATTEMPTED four times over. There is no second read
to corroborate the 56'-0" claimed by left and right. **Dart still
refuses: siding 0.0, starter/perimeter/eaves/rakes/OSC/ISC all None.**
The lift cannot resurrect dart's 1,280.53 ft².

### BONI — does not move
Zero unattributed dims, so there is nothing to lift; and its own
line-work is INDETERMINATE (left) / NOT_ATTEMPTED (right) anyway. Its
3,981.075 ft² and 194 LF stand untouched either way. EST-886440 remains
protected and unaffected by this ruling.

### TANIS — does not move
All four widths are already null (nothing derived to attribute), and
line-work is NOT_ATTEMPTED on all four. Still 0.0 ft², all lanes None.

## 5. REGISTERED THIS SEND — THE SEND-13 AMENDMENT
`seam_accounting.SEAM_REGISTRY["dims_demoted_quote_shared"]` (the send-13
retirement entry) now carries the amendment IN THE REGISTER, naming
send-13 explicitly: **the narrowing from KILL to FLAG was RIGHT FOR
DISPLAY and WRONG FOR QUANTITY.** Displaying a shared printed dim with
every consumer named is correct and stays; letting it feed money is what
bought dart 1,280.53 ft² and 170 LF off one 56'-0". Send-13 was not wrong
to stop the kill — it was wrong to let the flag stay silent where the
money is. The rail copy amended to "display only" in SEND-127 is the
matching correction on the card.

## 6. THE NEW CLASS — A REFUSAL A LATER PASS CAN OVERWRITE (inventory, NOT fixed)
Sweep of every place where a later pass can un-refuse an earlier
refusal. Five classes, 14 sites. **Reported only, per order.**

**CLASS A — LEDGER OVERWRITE (the record that drives the refusal is replaced)**
1. `ai_blueprint.py:_null_computed_lf_lanes` — `_lf_lane_nulled` was
   ASSIGNED; a second pass erased the earlier kills and a refused starter
   came back as a printed 16 LF. **FIXED send-127 (merges).** The class
   instance that named the class.
2. `ai_blueprint.py:1166` — `raw["_dim_evidence"] = evidence` is a whole-
   map assignment; a second evidence pass would replace, not merge, the
   provenance every downstream refusal reads.
3. `ai_blueprint.py:2439` — `_dim_shared_source` is `setdefault(...).extend(...)`:
   running the guard twice DUPLICATES records (no un-refusal, but inflated
   counts, and my own `_dim_unattributed` recompute reads it).
4. `seam_accounting.account` — additive and NOT idempotent: a re-run
   double-counts `removed`, so the disclosure of how much was refused
   drifts upward.

**CLASS B — STALE FLAG REVIVAL (a boolean from pass 1 tells pass 2 a refusal is a figure)**
5. `_rakes_plane_summed` — a stale True turned a refused rake into 0.0.
   **FIXED send-127 (cleared when no plane carries a live rake).**
6. `_eaves_plane_summed` (ai_blueprint.py:4803, read at 4942) — **the
   same shape, STILL LIVE, not fixed this pass.**
7. `spec["differs_from_derived_band"]` and `_gable_pitch_provenance` —
   flags describing an earlier pass that later passes trust without
   re-checking their inputs.

**CLASS C — `or 0` COERCION (a None refusal silently becomes a 0.0 quantity)**
8. `hover.py:478, 479, 645, 973, 1041` — `outside_corner_lf`,
   `inside_corner_lf`, `starter_lf` read as `float(m.get(...) or 0)`; a
   refusal arrives as a zero quantity, not as a refusal.
9. `lp_package_routes.py:1374` — `footprint_perimeter_ft or 0`: the
   refused perimeter reads as 0 LF of starter course / batten stackup.
10. `ai_blueprint.py:3906-3912, 3947-3949` — plane `rake_lf` / `eave_lf`
    and corner counts read `or 0` when building the readback rows.

**CLASS D — A SECOND WRITER TO THE SAME KEY**
11. `ai_measure.py:2117` writes `footprint_perimeter_ft` from the PHOTO
    door — it can overwrite the blueprint lane's refusal on the same
    estimate key.
12. `ai_blueprint.py:810-844` (the hover reconcile/merge) —
    `old_g["gable_ends"] = int(new_g...)`, `outside_corner_count/lf`
    reassigned from the new payload: a later merge can replace a refused
    or zeroed figure with the incoming one.

**CLASS E — RE-DERIVATION AFTER A NULL (a nulled input is recomputed from another route)**
13. `ai_blueprint.py:4851` — `_printed_starter = raw["starter_lf"] or
    raw["eaves_lf"] or 0`: a refused starter is re-sourced from a printed
    eaves figure. This is the fallback that fired during the SEND-127
    build.
14. `measure_staging._gable_rise` fallback chain — a refused TRACED rise
    falls back to the 0.70 field factor, so the refusal becomes an
    approximation under a different basis label.

## 7. WHAT IS OWED BACK BEFORE THE LIFT IS BUILT
1. **(A) structural or (B) magnitude-gated** — and if (B), the number.
2. **Which figure feeds** when a face is corroborated: the printed model
   figure or the drawn line-work figure (the undershoot is systematic).
Both are Howard's. The gate stays as built until then: no quantity leaves
without attribution.

Standing rules held: no cross-drawing borrowing, no estimate influenced
another, no job names in operative code, model heights hypothesis-only.
EST-886440 PROTECTED and unaffected. Purity pin holds. Gable placement
still noted-not-fixed. Symbols placement still NOT AUTHORIZED.

## 8. STAMP
RECORDED: 2026-08-25 19:00 UTC · d05461e · CLEAN
RESULT: 2873 passed, 9 skipped, 7 warnings in 468.19s (0:07:48)
CENSUS: census pin GREEN — 0 PENDING_CONVERSION · INGRESS SMOKE: 4 passed
(+2 pins over SEND-127's 2871: the register amendment and the FAILS_SAFE
answer. No quantity logic changed this send — the lift is not built.)
