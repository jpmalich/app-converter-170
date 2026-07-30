# MULTI-USE CONSUMPTION + GUARD SWEEP + LP RECONCILIATION (2026-07-30, REPORT ONLY)

Companion to dimensioned_sku_audit_2026-07-29.md. Nothing built. Howard rules in one pass.

## 1. MULTI-USE ITEM MECHANISM

**(a) Named mechanism: LIST-PER-USE. No SUM, no overwrite.**
Lines are keyed (tab, section, name). The catalog carries a separate row per
category block for the same physical product, each derivation emits its own
row, and NO layer anywhere aggregates by product/AMI — the material list
prints per-line. Overwrite cannot happen (names/sections differ); summing
does not exist.

**(b) Live example — estimate "3 degree vinyl 7-28-26 8am" (vinyl tab):**
| Line | Block | Qty | Unit |
|---|---|---|---|
| .019 Coil | Siding Accessories (opening wrap ÷100 LF/roll) | 5.28 | ROLL |
| .019 Coil (1 per 50' fascia) | Vinyl Soffit (eaves+rakes ÷100, F2 key gap) | 6.28 | ROLL |
One physical product (AMI 103954, both $161.33). What the contractor sees:
two fractional lines in two blocks. Physical order = 11.56 → **12 rolls if he
sums then rounds; 13 if he rounds each line**. Neither line whole-rounds
today (ROLL rows never got the whole-unit treatment — parked post-Sept item).
Same estimate, same product twice: 3/4" J-Channel (wall) 63 PCS + 3/4"
Soffit J-Channel 76 PCS — AMI 105118, hand-sum to 139.

**(c) Which failure happens today: DOUBLE-LIST.** Nobody runs short; the
counter-confusion / over-order risk is the live one, plus the 12-vs-13
rounding gap above.

**(d) Every product living in >1 category block (live DB, by AMI):**
| AMI | Blocks / rows | Derivations firing |
|---|---|---|
| 103954 .019 Coil | Siding Acc + Vinyl Soffit + LP Siding Acc | **2 live** (openings; fascia) + LP manual |
| 105118 3/4" J-Channel | Siding Acc (Std+Arch) + Vinyl Soffit (Std+Arch) | **2 live** (wall J; soffit J) |
| 103956 PVC Trim Coil | Siding Acc + Vinyl Soffit + LP (bare name) | 0 — all manual; contractor can fill both |
| 103960 Performance G8 | same 3 blocks | 0 — same exposure |
| 105114 1/2" J-Channel | Siding Acc + Vinyl Soffit ("White") | 0 — manual both |
| 79092500 Flash tape 3 3/4"×90' | Siding Acc + LP Siding Acc (IDENTICAL name, 2 blocks) | 0 — manual both |
Std/Arch pairs sharing one AMI at different prices (015456…016067, 105053,
105200, 105644, 105020) are color-tier twins inside ONE block — a binding
identity question for the ID work, not a multi-use question.
OBSERVATION for the ruling, not a conclusion: at each rake the wall-J
derivation counts 1 pass AND soffit-J counts 2; the Iter-78f comment block
cites "exactly 2 passes per rake" when excluding rakes from finish trim.
Whether wall-J's rake pass is a third physical channel or a double-count is
an install-reality call — yours.

## 2. NAMING — SEALED (Howard 2026-07-30)
"A SKU NAME IN THE APP DESCRIBES THE PRODUCT. The math lives in the
derivation. A rate worth showing is a NOTE sourced from the emitter — never
welded into the name." Sheet parentheticals stay in the printed sheet.
STRIP LIST (app rows, held for the one-pass go): .019 Coil (1 per 50'
fascia) → ".019 Coil"; PVC/G8 ×2 suffixes each → bare; 3/4" J-Channel
Std/Arch "(2 per Sq of siding)" → stripped; 1/2" J ×2 → stripped; Ascend J →
stripped; 2" Nails 30 lbs "(1 per 15 Sq)" → stripped; Ascend B&B 12" "(add
30% Waste)" → stripped (rate already lives in FAMILY_WASTE_DEFAULTS).
KEEP: "Ascend - 5.5\" Trim (16' length)" — product dimension, not a rate.
Touches: catalog_seed sections + price keys + DB tier migration + existing
estimate-line rename + register/tests repoint. ~1 day, lands with the ruling.

## 3. GHOST-GUARD SWEEP (guard string ⇄ catalog string, verbatim)

Register #8 CATALOG_ONLY_MANUAL_BY_DESIGN — the three, exactly:
| Guard looks for | Catalog actually says | Status |
|---|---|---|
| `Flash tape` | `Flash tape 3 3/4" x 90'` | WATCHES NOTHING |
| `24" CTW` | `24 inch CTW soffit` | WATCHES NOTHING |
| `24" VSSFT` | `24 inch VSSFT` | WATCHES NOTHING |
The other 10 register-#8 names bind exactly. Full sweep of every
name-referencing registry (MISC_LABOR_ROWS, RETIRED_LABOR_DEFAULTS,
LP_FORBIDDEN_LINE_MARKERS, emitter constants, all 59 hover emitter item
names, fam_markers, batten/fascia bindings):
- **NEW DEFECT, opposite direction — 'Inside Corners' (Ascend):** supplier
  dropped the row from the catalog (Iter 79, Feb 2026) but the hover emitter
  still emits it. Live: 4 estimates carry it at **mat=$0.00** (Casile qty 3).
  Its old $11.83 price sits orphaned in IDENTICAL_PRICES. An emitter feeding
  a retired name = permanently unpriced line, silent.
- `'j channel'` (space variant) in LP_FORBIDDEN_LINE_MARKERS matches no
  current name — defensive-broad by design (free-text variants), named not
  defective.
- 'Gutter'/'Downspout' bare names looked ghost vs the tier sheet but BIND in
  the ISS catalog engine (keyed section+name) — false positive, cleared.
- Everything else binds. The new dimensioned-SKU register self-checks
  (test_register_carries_no_ghost_names) so it cannot grow this disease.

## 4. LP RECONCILIATION — ROW BY ROW

**(d) first, because it explains everything: the app's LP prices do NOT come
from your Jan-2025 sheet.** Source chain: BlueLinx PIT00003 "LP ExpertFinish
Dealer Price Pages — Quick Reference **2.26.2026**" MILL cost → your margin
formula sell = cost ÷ (1−margin): one-opp ÷0.80, Builder-Dealer ÷0.75,
Contractor ÷0.70, whole-sale ÷0.65. That is where the four tiers come from —
one cost column × four margins, not four sheet columns. Your Jan-2025 tab
was diffed against this layer on 2026-07-18 (master_catalog_diff) and you
ruled KEEP-CURRENT; the deltas you found today are that same diff resurfacing.
Your 1.4073 is an artifact: PIT00003 Feb-2026 mill ≈ 98.5% of your Jan-2025
EACH on most rows, and 0.985 ÷ 0.70 = 1.4073.

**(a) Row-by-row (app Contractor price ⇄ Jan-2025 sheet EACH, live DB):**
| Row | App | Sheet | Ratio |
|---|---|---|---|
| 38 Lap 8"×16' | 30.99 | 22.02 | 1.4074 |
| Nickel Gap | 72.34 | 51.42 | 1.4068 |
| Shake | 23.74 | 16.87 | 1.4072 |
| 190 3"×16' | 19.66 | 13.97 | 1.4073 |
| 440 4/6/8/10/12 | 28.20/42.31/56.43/73.53/88.20 | 20.04/30.08/40.09/52.26/62.68 | 1.4066–1.4076 |
| 540 trim 4/6/8/10/12 | 34.30/51.44/68.59/89.81/107.73 | 24.46/36.56/48.74/63.83/76.55 | **1.4023**/1.4070/1.4073/1.4070/1.4073 |
| 540 OSC 4/6 | 181.11/271.69 | 128.71/193.08 | 1.4071/1.4071 |
| Panel 4×8 | 103.04 | 64.23 | **1.6042** |
| Panel 4×10 | 137.94 | 86.02 | **1.6036** |
| Vertical Panel | 73.50 | 44.77 | **1.6417** |
| Soffit 16×16 Vented | 85.83 | 52.23 | **1.6433** |
| 24" CTW / VSSFT | 124.94/134.21 | 88.79/95.37 | 1.4071/1.4073 |
| Touch up kits | 60.96 | 53.87 | 1.1316 |
| J blocks | 57.14 | 43.29 | 1.3199 |
| Mini Splits | 80.00 | 60.60 | 1.3201 |
| OSI Caulking | 14.03 | 10.36 | 1.3542 |
| Trim Coil 24"×50' | 223.21 | 156.25 | 1.4285 (cost == sheet, ÷0.70) |
| NO SOURCE IN SHEET | .019 Coil 161.33 / PVC 167.08 / G8 170.53 (mirror the vinyl tier rows by your coil ruling) · Flash tape 41.12 (vinyl AMI 79092500) · **Soffit 16×16 Closed: tier sheet $0.00 BY DESIGN — prices exclusively via the cost engine** | | |

**(b) The six explained — all one cause, NEWER PRICING, no transcription
error:** the four 1.60–1.64 rows are exactly the rows where PIT00003
Feb-2026 mill jumped 12–15% above your Jan-2025 EACH (72.13 vs 64.23,
96.56 vs 86.02, 51.45 vs 44.77, 60.08 vs 52.23 — flagged ⚠ in the 07-18
diff, ruled KEEP-CURRENT). Each app price equals its PIT00003 mill ÷ 0.70
to the cent. **Your 540 4"/6" ratios (1.4849/1.4617) I cannot reproduce**
from any live tier price against the workbook's Jan-2025 tab — I get
1.4023/1.4070 (trim) and 1.4071 (OSC). They reproduce exactly only if your
printed sheet's 540 rows read **23.10 and 35.19** (the workbook tab says
24.46/36.56). Read me the two sheet numbers you divided and I will close it.
Named small outlier regardless: 540-trim-4" at 1.4023 (PIT00003 24.01 vs
sheet 24.46 — 1.8% drift vs the family's typical 1.5%).

**(c) THE SOFFIT.** App VENTED $85.83 = PIT00003 mill **60.08** ÷ 0.70 —
it comes from the Feb-2026 BlueLinx page's own "16 x 16 Vented" line, no
transform of your sheet. App CLOSED $73.50 = PIT00003 mill **51.45** ÷ 0.70
(Closed re-added by your 2026-06 dealer ruling, cost-engine-exclusive).
The match you spotted (your vented 52.23 × 1.4073 = 73.51 ≈ CLOSED) is a
numeric coincidence: 51.45 ≈ 0.985 × 52.23. One fact FOR your ruling:
PIT00003 prices **16×16 Closed and Vertical Panel identically in every
finish column** (51.45/55.05/77.18/82.60…) — consistent with the closed
soffit being the same physical 16" vertical panel, but if your dealer page
shows different numbers for those two rows, that layer has a transposition.

## 5. ID-BINDING RE-SIZED against the real key facts
AMI was never a candidate key and the design never assumed one: LP prints no
item numbers, 8 vinyl rows carry none, ranges ("015456-015457") and shared
AMIs at different prices (105644, 105118) make AMI non-unique even where it
exists. The ID must be APP-MINTED (stable slug per catalog row, LP included);
AMI/BlueLinx description become reference METADATA on the row, never the key.
LP keys on the app ID; its BlueLinx binding stays description+finish inside
the cost layer. Honest number: **base unchanged 3–4 days** (mint + dual-bind
with name fallback + drift flag ~1.5–2d; retire name binding ~1–1.5d), plus
**+0.5d** AMI/metadata columns, plus — only if you rule that multi-use lines
should SUM at an order layer (finding 1) — **+1–1.5d** for a shared
product_id per physical product and an order-quantity roll-up. Ceiling with
everything: ~5.5 days.

## AWAITING ONE-PASS RULING
F1–F8 (prior audit) + today's: name-strip list execution · 'Inside Corners'
Ascend emitter (retire line or restore row) · register-#8 three renames ·
multi-use order treatment (hand-sum stays / order-layer sums by product) ·
wall-J rake pass count · 540 4"/6" sheet numbers readback.
