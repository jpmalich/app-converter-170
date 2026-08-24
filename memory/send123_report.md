# SEND-123 REPORT — PROMPT NEUTRALIZED · THE COMPOSITION ANSWERED · MATERIAL-CALLOUT VERIFIABILITY · PRINTED-ONLY LANE SIZING
2026-08-24 · Items 1–2 BUILT + answered; items 3–4 REPORT ONLY.
STAMP: `2026-08-24 18:25 UTC · 6e6fd72 · CLEAN · 2840 passed, 9 skipped`
(+3 SEND-123 pins, first-run) · census GREEN 0 PENDING_CONVERSION ·
ingress 4 passed. One fresh Tanis read executed (rerun of the cached
pages; no estimate written; EST-886440 untouched). Quantities only.

## ITEM 1 — THE PROMPT EXPOSURE, FIXED
- **Swapped to obviously-synthetic figures** (odd eighths no fixture
  house carries):
  - Derived-value worked example: `9'-11 1/8" + 1'-0" + 8'-1 1/8" +
    11 1/2"` → `7'-4 3/8" + 1'-1" + 6'-5 5/8" + 10 1/2"`; the
    lie-with-citation example `"20'-0\""` → `"15'-9 1/2\""` (the
    synthetic stackup's own sum — the pedagogy is preserved).
  - Schedule SIZE example `2'-11 1/2" x 4'-11 1/2"` (a real send-6-era
    schedule string) → `2'-7 3/8" x 4'-3 5/8"` at all three sites,
    parse example updated (→ 31.375).
  - Real garage wall `9'-11 7/8"` → `7'-10 3/8"`.
  - Floor-plan dim example `32'-0"` → `43'-0"`.
  - Hover scale prompt `30'-0"` (Boni's SEALED side width) / `40'-6"` →
    `41'-3"` / `27'-9"`.
- **THE QUALIFICATION REGISTERED** (ocr_geometry.RULINGS_REGISTER):
  prior-house figures were in front of the model on EVERY read since
  the example was written — it qualifies every prior run the way the
  20.0 census qualified every Boni accuracy claim; a condition, not an
  invalidation.
- **PINNED**: `test_send123_prompt_purity_2026_08_24.py` — structural
  AST scan of every prompt constant (>400 chars) in 6 modules against a
  19-figure fixture set (Letrick/Boni/Tanis distinctive figures).
  Industry shorthand (3068 codes, 6'-8" door height, 16'×8' garage
  door, 1'-0" scale/overhang) is REVIEWED-GENERIC — conventions, not
  house evidence. 3 pins, green.
- **THE SWEEP (was any other prompt carrying real figures?)**: 8 prompt
  constants + 2 inline prompt strings swept across
  ai_blueprint/ai_measure/schedule_read/pdf_overlay/height_read/
  page_rotation. Real figures existed in TWO: the blueprint
  SYSTEM_PROMPT (the worked example + schedule examples + garage wall,
  all above) and the hover OCR_SCALE_PROMPT (30'-0"). ROOF_PASS_PROMPT
  and the four hover photo/reconcile prompts carry none.
  READ_PAGE_SCALE_PROMPT carries only the scale convention
  (1/4" = 1'-0") — generic. Comments and the rulings register carry
  historical figures as data; they never reach a model call.

## ITEM 2 — THE COMPOSITION, ANSWERED BY THE POST-SWAP RE-READ
Fresh Tanis read under the NEUTRAL prompt (run `580ff451…`, rerun of
the cached pages, same build otherwise):
- **THE MODEL VOLUNTEERED 9'-1⅛" AGAIN.** Every face height and the
  corner heights carry the quote `9'-1 1/8"` (value 9.0 this run) —
  and every one was nulled by the quote guard again (fabricated/
  misread against the page OCR).
- **VERDICT: the print's tail alone produces the figure.** The vertical
  `-1 1/8"` glyph string on p3 plus the model's own feet-digit read
  lands on 9'-1⅛" with no prior-house figure anywhere in the prompt.
  THE EXPOSURE WAS REAL BUT WAS NOT DOING THE WORK ON THIS CLAIM.
  Recorded in the register as the composition's answer.
- The read stayed honest end to end, and SEND-122's guards fired LIVE
  on their first fresh run: heights 0/4 (all refused named) · widths
  nulled (97'-0" ×2, 57'-0" ×2 this run — run-to-run claim variation,
  same refusals) · LF lanes nulled NAMED (starter 308, eaves 194,
  rakes 122, corner LF 54/18 → None; an evidenced garage-plane eave
  of 24.0 LF survived through the plane lane, which is the design) ·
  window_count 3 with 5 count refusals named (model claimed different
  rows this run; counts landed only where evidence located) ·
  siding 0.0 · 11 rails including `lf_lane_refused` and
  `below_grade_unread` — both new rails firing on the house that
  earned them.

## ITEM 3 — MATERIAL CALLOUTS: THE VERIFIABILITY REPORT (nothing built)
**Every material claim with reach to a quantity:**
1. `walls[].siding_pct_this_wall` (default 100) — DIRECT area reach:
   measure_staging L248 multiplies each face's ft² by pct/100. Never
   OCR-verified. **Tanis carries 85/85 on back/left** (from the stone
   watertable claim) — had those faces derived, 15% of two faces
   leaves the takeoff on an unverified claim. THE LARGEST REACH.
2. `walls[].wall_body_profile_callout` — whole-face family routing:
   classify_profile → `_per_profile_sqft` → LP profile SKU lines;
   stone routes a face OUT of siding entirely.
3. `walls[].gable_profile_callout` — gable-triangle ft², same path.
4. `walls[].dormer_profile_callout` — dormer ft², same path.
5. `appendages[].profile_callout` — appendage ft², same path.
6. `walls[].stone_callout` — drives the pct reductions and watertable
   surfaces (feeds 1).
**Are they OCR-verifiable in principle? MOSTLY NO.** Across the four
houses' latest reads, 24 material-callout claims: **2 of 24 locate in
the OCR store** (Boni's gable `SHINGLES` ×2 — real ink, locatable).
The other 22: `VINYL` ×10 (Letrick, Boni — category answers, no such
ink), `HORIZONTAL SIDING` ×6 (dart), `SIDING AS SPECIFIED` ×3 +
`SYNTHETIC STONE AS SPECIFIED` + `STONE WATERTABLE` ×2 (Tanis — the
elevation ink text is thin; the strings do not locate). Verifiability
is bounded by the OCR store: some of these may be printed but
un-OCR'd; none can be LOCATED, which is what a gate needs.
**What refuses on all four houses if the gate lands: effectively the
entire profile lane.** 22/24 claims null → every wall-body family
assignment on all four houses refuses; Tanis's 85s revert to
unverified; only Boni's two gable SHINGLES survive.
**THE ANSWER HOWARD ASKED FOR PLAINLY: most callouts cannot be
verified — this changes the ruling FROM A GATE TO A HUMAN
CONFIRMATION.** The claim should surface as an unconfirmed material
card (claim + face + ft² at stake) that a human confirms or corrects
— the same shape as the walkout answer. NOT BUILT; awaiting ruling.

## ITEM 4 — THE PRINTED-ONLY LANES: SHAPE, COST, AND SIZE (nothing built)
**The schema change's shape**: 5 fields flip `number` → `DIM
{v, page, from}` in SYSTEM_PROMPT (`soffit_sqft`, `level_frieze_lf`,
`sloped_frieze_lf`, `drip_edge_lf`, `total_trim_sqft`); +5 path
registrations in the evidence walker (the quote nuller then covers
them for free); ~13 aggregation conversion sites in ai_blueprint
(3/2/2/3/3 per field) + 3 lp_package consumers unchanged (they read
measurements, which aggregation would keep as floats).
**The risk**: model compliance — a model returning bare numbers gets
nulled as unverifiable, flipping any future printed claim to refused
until the quote locates; prompt grows ~5 lines.
**THE SIZE OF THE EXPOSURE TODAY: ZERO ft² / ZERO LF.** On all four
houses' latest reads, all five lanes carry **None** — the model never
volunteers them on any fixture drafter. The only bare counts carried:
vents (Tanis 2, dart 2, Boni 2, Letrick 1) and shutters (dart 8,
others 0). The unguarded surface is large in PRINCIPLE and empty in
FACT on every house seen so far — known first, as ordered; the ruling
can price the change against a zero present exposure.

## OPEN ITEMS AFTER THIS SEND
- **Dart's sealed ground truth — Howard.** Tanis alone is still an
  anecdote; dart completes the property.
- Material-callout HUMAN-CONFIRMATION surface (the gate is off the
  table by the numbers above) — awaits ruling.
- Printed-only lanes DIM change — shape/cost/size reported; awaits
  ruling against the zero present exposure.
- Symbols placement — NOT AUTHORIZED.
- Catch-all message inventory — still owed.
- rot180 — held. CCC — unvalidated at n=2.

Standing rules held: no cross-drawing borrowing, no estimate influenced
another, no job names in code (register/data only), model heights
hypothesis-only. EST-886440 untouched. 423 discipline untouched (no
derived write occurred — the rerun stores a run, applies nothing).
Purity pin now enforced structurally. 
