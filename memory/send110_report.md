# SEND-110 REPORT — PER-PAGE SCALE QUERY · X-RULER FRAGMENTATION TRACE · SILENT-STRIP RCA
2026-08-23 · QUANTITIES ONLY (ft, ft², %, counts). REPORT ONLY — nothing wired, no boundary
selection changed, no calibration changed, nothing tuned toward the sealed depths. The one
authorized text correction (the send-104 register claim) is the only code-tree edit.
Sequencing as ruled: scale query FIRST (it can kill the trace) → trace (stating the scale
answer) → RCA (independent). Predictions were recorded before the probes ran
(`memory/send110_prediction.md`); outcomes appended there unrevised. Probes:
`memory/send110_probe.py`, `send110_probe_v2.py`; raw output `send110_probe_out.txt`,
`send110_probe_v2_out.txt`.

---

# 1. THE PER-PAGE SCALE QUERY — FOUR SCALES, NOT TWO

## 1.1 The three things conflated under "scale", reported separately

### (1) THE DERIVED SCALE — ft per page-% from each face's own datum gap

Every face's ruler, computed independently. Two gap readings per face are given: the LABEL
gap (what the live pipeline divides into — `scale_y`, the datum LABEL box centers, carried
at ONE decimal of page-% by `height_read.py` L139) and the DRAWN gap (the drawn datum-level
closure lines the linework read resolves, at two decimals — the ink itself). fpp_x = ft ÷
(gap-frac × page_h px) × page_w px ÷ 100 (`routes/pdf_overlay.py` L1835).

**LETRICK** (real gap: front/left/right 9.08 ft derived chain; REAR CONTESTED — both
candidates reported, as ruled):

| face | page | label gap (y-%) | drawn gap (y-%) | ft | fpp_x LIVE (label) | fpp_x on drawn ink |
|---|---|---|---|---|---|---|
| front | p1 | 9.40 | 9.36 | 9.08 | **1.28794** | 1.29346 |
| rear  | p1 | 9.40 | 9.43 | 9'-1⅛" = 9.0938 | **1.28990** | 1.28580 |
| rear  | p1 | 9.40 | 9.43 | 9'-11" = 9.9167 | **1.40662** | 1.40216 |
| left  | p2 | 9.60 | 9.73 | 9.08 | **1.26111** | 1.24427 |
| right | p2 | 9.50 | 9.53 | 9.08 | **1.27439** | 1.27038 |

Pairwise disagreement of the four live rulers (rear at the 9'-1⅛" candidate):
- front vs rear: **0.15%** (agree)
- left vs right: **1.04%** (disagree)
- front vs left: 2.08% · front vs right: 1.05% · rear vs left: 2.23% · rear vs right: 1.20%

On the drawn ink the spread is LARGER, not smaller: front 1.29346 vs left 1.24427 = **3.80%**.
So the disagreement is NOT label-box noise: label vs drawn differ by ≤0.14% per face; **the
drawings themselves place the FIRST FLOOR → TOP OF PLATE gap at different drawn heights per
face** — front draws 9.08 ft as 9.36 y-%, left draws the same 9.08 ft as 9.73 y-%. The
quantization of the label y to 0.1 y-% (worth up to ±1.06% of a 9.4% gap per endpoint) is a
real but SECONDARY roughness riding on a real per-face drawn difference.

### (2) THE PAGE NORMALIZATION — code checked, not inferred

**Each page uses its OWN box. No shared normalization box exists.**
- Vector strokes: `linework_read.py` `page_segments` L590 — `W, H = float(pg.width),
  float(pg.height)` per page inside the page loop; every stroke divides by that page's own box.
- OCR store: `routes/ai_blueprint.py` L1860–1903 — `w, h = im.size` from each page's own
  rendered image inside the page loop; `_pw, _ph` rebound per page; `page_w`/`page_h`
  persisted per page and read back per page (`ot[pg]["page_w"]`).
- The x-ruler at `pdf_overlay.py` L1835 reads `pgd = ot.get(spec["page"])` — the face's own page.

The single most likely per-page mechanism (a shared box) DOES NOT EXIST in this code.

### (3) THE SHEET'S DRAWING SCALE — page boxes confirmed identical, not assumed

Measured, both houses, all four pages each: PDF box **1728.00 × 1296.00 pt = 24.000 ×
18.000 in (ARCH C)** on every page; OCR raster **3456 × 2592 px (144 DPI)** on every page.
Identical. At the printed 3/16"=1'-0" on a 24-in sheet the anchor ruler is 1.28 ft/x-%
(0.96 ft/y-%) — an ANCHOR FOR COMPARISON ONLY, not evidence for any width. Against it:
front +0.62% (label) / +1.05% (drawn); rear +0.77% / +0.45% (@9'-1⅛"); left −1.48% /
−2.79%; right −0.44% / −0.75%. **p1 sits high, p2 sits low — on every reading.**

## 1.2 The same run on Boni

Boni's evaluable faces sit front+rear on p1, left on p2 (right: no FIRST FLOOR datum, no
gap). No face carries a verified real gap in ft (front/rear heights contested/undimensioned)
— **no quotient is derivable**; the drawn gaps are the only measurable analogue:

| face | page | label gap (y-%) | drawn gap (y-%) |
|---|---|---|---|
| front | p1 | 18.90 | 18.77 |
| rear  | p1 | 18.60 | 18.64 |
| left  | p2 | 18.80 | (linework INDETERMINATE — one corner) |

Boni front and rear sit on the SAME page and their drawn gaps differ by **0.70%** — IF their
real gaps are equal (unverified — that is exactly what is contested on this house), a
same-page disagreement is the per-face signature, not per-page. Suggestive, not proof.

## 1.3 The prediction, scored (recorded first, unrevised)

> "IF FRAGMENTATION IS THE CAUSE, THE FOUR SCALES AGREE. IF IT IS PER-PAGE, THEY DISAGREE
> BY ROUGHLY THE RESIDUAL PERCENTAGES — p1 high by about 1.3%, p2 low by about 1.5 to 2%."

**Outcome: the four scales DO NOT AGREE — and they do not group cleanly by page either.**
Front/rear agree at 0.15%; left/right disagree with the p1 pair AND WITH EACH OTHER by
1.04% (3.80% spread on the drawn ink). Under the ruled decision table that is **ALL FOUR
DIFFER → PER-FACE; the per-page grouping was a coincidence** — but the DIRECTION of the
per-page prediction is confirmed: p1 high (+0.6 to +1.1%), p2 low (−0.4 to −2.8%),
magnitudes at roughly half to the low edge of the predicted band. Predicted residual from
scale alone (vs the sheet anchor, live rulers): front +0.34 ft, rear +0.42 ft, left
−0.44 ft, right −0.13 ft against actual +0.71 / +0.65 / −0.60 / −0.35. **Sign correct on
4 of 4 faces; magnitude roughly half.** Scale is IMPLICATED but not the whole cause —
the trace below carries the other half. Neither hypothesis died; both are real and additive.

## 1.4 What a scale fix would cost (stated, not recommended)

- **Carry the label y at 2 decimals** (`height_read.py` L139): ~1 line. Moves every derived
  figure by ≤0.14% here (≤0.08 ft) — too small to touch the residual, and every pinned exact
  figure across ~dozens of live pins churns. Not worth its own risk.
- **Re-seat each face's scale on its drawn closure gap** where linework resolves: ~20–40
  lines in the propose path. Moves widths −1.3% to +0.4% per face — and moves LEFT THE WRONG
  WAY (29.40 → 29.01: the drawn gap is LARGER on left, so the drawn ruler is SMALLER). The
  drawn ink itself disagrees per face; re-seating on it does not converge the four faces.
- **Rule the printed sheet scale (3/16"=1'-0" × recorded DPI) as the x-ruler**: ~10–20 lines
  (the `printed_scale` mode already exists in `polygon_sqft_from_scale`). Lands sides at
  30.28/30.27 outer-to-outer but front at 54.46 and rear silhouette 54.74 — fixes one axis,
  worsens nothing badly, but it REPLACES per-face evidence with a printed convention, which
  is a doctrine change only Howard can rule; and it still leaves front/rear +0.5 ft.
- **Register the per-face scale spread and leave it**: 0 lines. The spread is now NAMED with
  its numbers — a known ±1–2.8% per-face ruler property of these prints.

No option both fixes all four residuals and moves nothing kept. CLEAN CAUSE + NO CLEAN
SMALL FIX on the scale axis alone.

---

# 2. THE X-RULER FRAGMENTATION TRACE

Scale query answer carried in, as ruled: **the four scales disagree per-face (§1.3), so
this trace is NOT the sole cause** — it is the other, additive half. Twin separations below
are measured in page-% (scale-free drawn fact) and expressed in ft at that face's own live
ruler. PRE-MERGE = raw strokes clustered at line-weight identity (_COORD_EPS 0.05) with NO
gap_tol joining; POST-MERGE = after `_merge_collinear` (the pipeline's own gap_tol joins).
The merge has produced two wrong conclusions already (the phantom 0.34/0.40 shortfall, left's
false bump) — both columns shown.

## 2.1 Per face, per boundary — items (a)–(d)

**Every outer boundary stroke on both houses is FRAGMENTED pre-merge** (2–4 pieces on
Letrick, gaps 0.23–0.5 y-%; Boni's inner strokes shatter into 10–22 pieces — different
drafting hand). "Continuous" below = a single unbroken drawn piece spanning the datum
interval. cov = union of fragment ink as % of the datum interval.

### LETRICK (8 boundaries — the 8 kept boundaries, as controls and as suspects)

| boundary | current landing | twin pair x (inner ↔ outer) | twin sep | outer twin pre-merge | inner twin pre-merge | post-merge outer spans? |
|---|---|---|---|---|---|---|
| front L | **OUTER** | 14.259 ↔ 13.950 | 0.309% = **0.40 ft** | 2 frags, cov 125%, gap 0.4 | 3 frags, cov 97% | YES (joined) |
| front R | **OUTER** | 56.201 ↔ 56.499 | 0.298% = **0.38 ft** | 4 frags, cov 109%, gaps 0.27/0.27/0.4 | 4 frags, cov 98% | YES (joined) |
| rear L | **OUTER** | 38.549 ↔ 38.128 | 0.421% = **0.54 ft** (@9'-1⅛") | 2 frags, cov 112%, gap 0.4 | **1 frag, CONTINUOUS, cov 101%** | YES (joined) |
| rear R | **OUTER** | 80.473 ↔ 80.895 | 0.422% = **0.54 ft** | 2 frags, cov 112%, gap 0.4 | 2 frags, cov 101% | YES (joined) |
| left wall-L | **OUTER** | 19.793 ↔ 19.446 | 0.347% = **0.44 ft** | 2 frags, cov 98%, gap 0.23 | 2 frags, cov 113%, gap 0.07 | YES (joined) |
| left wall-R | **INNER** | 42.757 ↔ 43.100 | 0.343% = **0.43 ft** | 2 frags, cov 90% — **top frag MISSING: never reaches the plate box (ink starts 0.7% below it), even post-merge** | 2 frags, cov 105%, gap 0.07 | **NO** |
| right wall-L | **INNER** | 54.680 ↔ 54.332 | 0.348% = **0.44 ft** | 2 frags, cov 90% — **same signature: never reaches the plate box, even post-merge** | 2 frags, cov 106%, gap 0.07 | **NO** |
| right wall-R | **OUTER** | 77.642 ↔ 77.978 | 0.336% = **0.43 ft** | 2 frags, cov 98%, gap 0.23 | 2 frags, cov 113%, gap 0.07 | YES (joined) |

(Left/right silhouette edges — the chimney chains at 17.43 and 80.01 — ride the CONTINUOUS
chimney outer strokes exactly as SEND-89 found; unchanged, not in contest here.)

### BONI (resolved faces)

| boundary | current landing | twin pair (inner ↔ outer) | twin sep (%) | outer twin | inner twin |
|---|---|---|---|---|---|
| front L | **OUTER** | 16.570 ↔ 16.282 | 0.288% | 2 frags, cov 107%, gap 0.4 | 12 frags, cov 89% |
| front R | **OUTER** | 61.661 ↔ 62.003 | 0.342% | 2 frags, cov 107%, gap 0.38 | 22 frags, cov 78% |
| rear L | **OUTER** | 36.440 ↔ 36.115 | 0.325% | 2 frags, cov 107%, gap 0.4 | 11 frags, cov 89% |
| rear R | **OUTER** | 81.458 ↔ 81.810 | 0.352% | 3 frags, cov 127% | **1 frag CONTINUOUS cov 97% — but IT misses the plate box** (starts 1.5% below it) |
| left | — | linework INDETERMINATE (one corner) — the refusal stands, no boundary to land | | | |

**The pattern REPRODUCES on Boni — it is a mechanism, not one plan set's quirk**: outer
twins are 2–3 fragment lines that the gap_tol merge joins into spanners and the boundary
rides them; and the same reach-the-plate-box discriminator decides the landing (Boni rear-R
inverts the winner exactly as the discriminator says it should).

## 2.2 The prediction, scored (recorded first, unrevised)

> "SIDES: outer stroke FRAGMENTED, boundary on the INNER twin, under-read ≈ the twin
> separation. FRONT/REAR: outer stroke CONTINUOUS, boundary on the OUTER, slight over-read
> by line weight. IF THE SIDES COME BACK CONTINUOUS, OR FRONT/REAR FRAGMENTED, THE
> HYPOTHESIS DIES."

**Front/rear came back FRAGMENTED — so the hypothesis AS STATED dies, and it dies telling
us what is actually true.** Said plainly, no surviving variant is being fitted:

- Fragmented-vs-continuous is NOT the discriminator. EVERY outer stroke on every face of
  both houses is fragmented (2–4 pieces). Front/rear land OUTER anyway, because the merge
  joins their outer fragments into spanners.
- The REAL discriminator, visible in the table: **whether the outer twin's fragments ever
  reach the PLATE BOX.** On exactly two of the eight Letrick boundaries — left wall-R and
  right wall-L, one corner on each side face — the outer twin's TOP fragment is simply not
  drawn (ink starts 0.7% of page below the plate box; no join can manufacture it). There the
  boundary drops to the inner twin. Everywhere else it rides the outer.
- The predicted MAGNITUDE holds where the landing is inner: under-read per dropped corner =
  twin separation 0.43–0.44 ft, one corner per side face. The predicted SIGN mechanism holds:
  sides under (one inner corner each), front/rear over (both corners outer).

Cross-check against the sealed figures, both twin choices, live rulers: inner-to-inner
lands front 54.02 and rear 54.08 (sealed 54.00) but sides 28.96/29.26 (sealed 30.00);
outer-to-outer lands sides 29.83/30.13 but front 54.71/rear 55.15. **The sealed numbers
match OPPOSITE twin choices on the two axes under the current per-face rulers** — which is
§1's scale finding restated in ink: no single twin rule closes all four faces while the
four rulers disagree.

## 2.3 Item (e) — the theoretical rule against sealed depths AND the 8 kept boundaries

The rule as ruled: "outermost COLLINEAR fragment's outer edge, no joining — collinear with
the wall line and inside the datum band" (fence applied verbatim as everywhere else).
Measured, per face, with the fragment span visible:

| face | current | rule verdict | rule width | what it grabbed (fragment span) |
|---|---|---|---|---|
| front | 54.71 | **OVER-EXTENDS +12.4 ft** | 67.10 | leader/dimension ink at x=8.64/60.74, cov 2.05%/1.50% of interval |
| rear | 60.14 sil (@9'-11) | **OVER-EXTENDS +15.6 ft** | 75.76 | fence-edge dimension rail at x=87.69 |
| left | 29.40 wall | **OVER-EXTENDS +16.1 ft** | 45.53 | ink at x=11.42/47.53, cov 1.32%/2.05% |
| right | 29.66 wall | **OVER-EXTENDS +20.5 ft** | 50.14 | ink at x=46.69/86.04, cov 0.33%/1.00% |

A restricted variant (outermost cluster whose UN-JOINED fragment union still reaches both
datum boxes) also fails: front 55.00 (+1.00), left 40.91 (a dimension line at x=43.86 with
an 8.2 y-% internal gap "reaches both"), right 33.67, rear 63.93–69.71. **CONTROL VERDICT:
the rule and its variant move ALL 8 kept boundaries, by +0.08 ft to +10.1 ft. The rule dies
against the controls** — the same discipline that killed the outermost-boundary property
(SEND-81) and the literal span property. SEND-81's finding is re-measured here, now with
fragment spans attached: dimension/leader ink lies inside the fence and outboard of every
silhouette edge on every face, with fragment coverage of 0.3–3% of the datum interval —
the over-reach risk is in the numbers, not argued.

Two-things-the-rule-must-do check: the sign does NOT come out right per face (it pushes
front and rear FURTHER OVER while "fixing" the sides — the half-a-rule case, and its
restricted variant lands 55.00 on front, near the sealed 54, which is the dangerous kind);
and it moves every kept boundary. Both requirements fail.

## 2.4 What an x-ruler fix would cost (stated, not recommended)

- The literal rule: ~20–40 lines in `linework_read.py` boundary selection. Risk MEASURED
  above: all 8 kept boundaries move, by feet. Disqualified by the controls.
- A targeted cure for the two inner-landing corners (accept an outer twin that reaches the
  floor box but not the plate box): ~15–25 lines. It would admit left 43.100 and right
  54.332 (+0.43/+0.44 ft, sides → 29.83/30.13) — but the SAME relaxation admits course-end
  ink on front-R at 56.654 (reaches both boxes across an 8.54 y-% gap, +0.21 ft) and
  fence-edge ink on rear — front/rear move FURTHER over. Half a rule; fails the sign test.
- **Register the residual and leave it: 0 lines.** The residual is now NAMED per corner:
  front/rear ride the outer twin at both corners (+0.38 to +0.54 ft of twin separation per
  corner relative to the inner ink); each side face drops ONE corner to the inner twin
  (−0.43/−0.44 ft) because the drawing never drew that outer stroke's top fragment; and the
  four per-face rulers disagree by 1–3.8% underneath it all (§1). A known, named, sub-1%
  under/over-read with its mechanism on the record is a different thing from an unexplained
  one. **This report's recommendation, offered not assumed: cause found, fix declined,
  residual registered with its explanation.**

---

# 3. SILENT-STRIP RCA — WHY THE SEND-104 CENSUS MISSED THE FIFTH MEMBER

The fifth member (SEND-109 §3): the browser catalog merge (`frontend/src/lib/useEstimate.js`
L99–172) rebuilt every line object on load, dropping the refusal trio (`not_derivable`,
`not_derivable_reason`, `not_derivable_code`) and coercing a refused row's qty null → 0;
the next autosave wrote the loss back. Already fixed in SEND-109 (trio + null ride the
merge verbatim). This RCA answers WHY the census missed it. No further fix in this pass.

## 3.1 The three outcomes — (b) checked explicitly and first

**(b) SWEPT-AND-EXCUSED-WRONGLY: NO.** The register
(`tests/test_lines_door_census_2026_08_22_send104.py`) holds exactly THREE entries, each
re-read against its code today:
1. `demo.py` — "provision-time seed of a FRESHLY-CREATED demo estimate… no overlay zones
   can exist yet". Re-checked: the seed writes to an estimate inserted in the same function.
   **Reason HOLDS.**
2. `lp_admin.py` — "in-place tier reprice of the STORED rows… nothing is rebuilt or merged —
   non-LP rows, chase rows included, pass through object-identical". Re-checked:
   `reprice_lp_engine_lines(est.get("lines"))` maps over stored rows. **Reason HOLDS.**
3. `pdf_overlay.py` — "the overlay law's own write sites". **Reason HOLDS.**
No entry excuses the client merge; the client merge was never on the register. Not (b).

**(c) ADDED AFTER: PARTIALLY — the FIELD, not the PATH.** The merge path predates the
census by weeks. What was added after (SEND-105's Ruling V conversion) was the refusal trio
itself — new law-adjacent fields on rows an old rebuild-everything merge didn't know to
carry. The path was always lossy for any field it didn't enumerate; the new fields made the
loss visible.

**(a) NOT SWEPT: YES — and it could not have been swept, by construction.** The census's
unit of analysis is the SERVER-SIDE Mongo write: an AST walk over `routes/*.py` for
`update_one/insert_one/replace_one` calls carrying a `lines` key. The strip happens in the
browser BEFORE the payload reaches any door. **Anything that transforms a payload before it
reaches a write is invisible to a write-boundary census.** Scope failure — the likeliest
read, confirmed.

## 3.2 Does the client merge path re-run the law at the write? YES — and that is why only HALF the loss landed

`estimates.py` PUT (L447-448) and PATCH (L476-477) both call `reapply_overlay_law` on every
lines write — the census asserts it. So the stripped payload DID pass through a door that
re-runs the law, and everything the law RECOMPUTES was immune: chase rows rebuilt from
zones, overlay quantities re-derived (that is why SEND-100's class stayed closed). The
refusal trio was lost anyway because **the overlay law does not own those fields** — nothing
server-side re-derives refusal provenance on a lines write. The sharp finding: "the
invariant is enforced at the write" held exactly as far as the law's OWNERSHIP reaches, and
the doctrine's fields had grown wider than the law's ownership. The write-side cure that
would have made the client merge harmless regardless (re-derive the refusal trio at the
write, as chase rows are) is a fix SHAPE, ~15–30 lines in the reapply path — NOT BUILT,
not authorized this pass.

## 3.3 What else transforms a payload before a write — the real scope of the class, never swept

Inventory (frontend, feeds `estimates` lines writes):
1. `useEstimate.js` catalog merge (L99–172) — rebuilds EVERY line object on every load.
   THE fifth member. Fixed for the trio + null qty (SEND-109); still rebuilds by field
   enumeration — any FUTURE law-adjacent field starts life stripped until someone adds it.
2. `useEstimate.js` save shaper (L483–500) — filters rows before every PUT: drops
   `overlay_chase_line` rows (by design — the server law rebuilds them) and qty-0 note-less
   catalog rows (re-materialize by design; human zeros and noted rows survive by ruled
   exception). A transform with three ruled carve-outs riding on it.
3. `useRecalcSoffitOnOverhang.js` `applyPorchRows` (L45–133) — maps over lines, rewrites
   soffit rows, then `update({lines: next})` → autosave PUT. Never swept.
4. `HoverImportButton.jsx` / `ISSHoverImportButton.jsx` (~L371–397) — merge source-side
   lines into the current estimate client-side before save. Never swept.
5. `PdfOverlayEditor.jsx` — zone writes go to the overlay law's own routes (law-owned).
An adjacent precedent already exists for client-side structural enforcement: the
optimistic-write registry (`optimistic_write_registry.js` + its backend AST detector) fails
the build when a component mutates state before a write without declaring itself. The
silent-strip class has no client-side analogue; these five sites are its unswept scope,
now named.

## 3.4 The discipline point — the correction, made

Send-104 claimed "no fourth accidental member" (structural impossibility). A fifth appeared.
**A census proves what it swept. It never proves a class is closed** — and the stronger
claim is worse than useless, because it stops people looking. Send-44 stated the honest
form ("I can only audit what became a test") and nobody was surprised by segment-partial.
**CORRECTED (the one authorized edit):** the census test's register docstring now states its
scope — every SERVER-SIDE lines door re-runs the law or sits on the reason-checked register
— and names the class it structurally cannot see (client-side payload transforms, the fifth
member's home), pointing here. No assertion changed; the pins still enforce exactly what
they enforced.

---

## STANDING RULES HELD
No cross-drawing evidence · no estimate influences another · no job names in code · model
heights hypothesis-only · EST-886440 PROTECTED (untouched; probes read-only) · 423 on every
derived write · purity pin holds · quantities only, no dollars · nothing adjusted toward
any sealed figure.

## STAMP
(appended after the clean run)
