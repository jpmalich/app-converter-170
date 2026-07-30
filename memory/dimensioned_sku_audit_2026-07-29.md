# DIMENSIONED-SKU AUDIT — ALL FAMILIES (2026-07-29)

Scope: every catalog SKU whose NAME carries a dimension — widths, lengths,
thicknesses, coverages, spacings — PLUS formula claims in names ("2 per Sq",
"1 per 50' fascia"), per Howard's addition. 81 SKUs in the estimate catalog
(SECTION_LAYOUT) + Mezzo/Vero window buckets + ISS labor bands.

Detector: `backend/tests/test_dimensioned_sku_register_2026_07_29.py`
(13 pins). An unregistered dimensioned SKU FAILS THE SUITE; a registered
name that leaves the catalog FAILS THE SUITE (no ghost guards).

Columns: (1) dimension in name · (2) SELECTABLE or BAKED · (3) wrong value
changes COUNT or just SKU/price row · (4) owning derivation · (5) variants
priced · (6) **NAME-CONSTANT == MATH-CONSTANT?**

## A. LP FAMILY

| SKU | Dim in name | Sel/Baked | Wrong value moves | Derivation | Variants priced | Name==Math |
|---|---|---|---|---|---|---|
| 38 Series Lap 3/8"×8"×16' | face 8", stick 16' | BAKED (8" is the only lap; 6" discontinued) | COUNT (11 pcs/sq curve is derived from 8"→7.875 face and 16') | lap_pieces_book / split path (register #3 unified) | single SKU | ✓ pinned: pieces_per_square(7.875−1, 16)=11=LAP_PCS_PER_SQUARE |
| 38 Series 4'×10' Panel | 4×10 = 40 ft² | BAKED (4×10 today; 4×8 selectability reported 2026-07-29, AWAITING RULING) | COUNT (÷40) | _lp_profile_sku_entry board_batten | 4×8 twin priced, manual | ✓ pinned: emitter SKU 4'×10' ↔ 40.0 ↔ BB_PANEL_SIZES_SQFT["4x10"] |
| 38 Series 4'×8' Panel | 4×8 = 32 ft² | MANUAL (register #8) | — (no derivation) | none | priced | n/a — BUT see F7: gated-legacy Vertical Panel row divides by 32 |
| 38 Series Vertical Panel (no dims in name) | hidden 32 ft² | BAKED, legacy path only (flag OFF) | COUNT ÷32 | _PROFILE_SKU_MAP legacy | priced | F7: legacy divides by 4×8's 32 while the live path is 4×10's 40 — cross-path divergence, gated, now pinned BY NAME |
| 190 Series Trim 19/32"×3"×16' (batten) | 3" width, 16' stock | width/length BAKED; **SPACING = TRADE SPEC** (12/16/24, default 12) | spacing → COUNT; 3"/16' → COUNT in hard formula | bb_batten_* (aggregate live; hard formula sealed, unwired) | single SKU | ✓ pinned: 3" == hard-formula default; 16' == BATTEN_STOCK_LENGTH_FT |
| 440 Series Trim 4/4"×{4,6,8,10,12}"×16' | width, 16' | **WIDTH = TRADE SPEC fascia_width_in** (4–12, default 8) | width → SKU/price row only (count is per-segment ceil LF/16, width-independent); 16' → COUNT | fascia_rake_takeoff + fascia_item_for_width | ✓ all 5 pinned priced (test_every_width_variant_sku_binds_to_a_priced_row) | ✓ pinned: every variant parses 16' == TRIM_STICK_LEN_FT |
| 540 Series Trim 5/4"×4"×16' | width 4", 16' | BAKED default (Q12): wrap + ISC + frieze | 16' → COUNT (÷16 everywhere); width → SKU only | wrap/ISC/frieze assembly in lp_package | ✓ 540 widths pinned priced | ✓ pinned 16' |
| 540 Series Trim 5/4"×{6,8,10,12}"×16' | width | MANUAL substitution options (register #8) | — | none | ✓ priced | n/a |
| 540 Series OSC 5/4"×6"×16' | width 6", 16' | BAKED (sealed 2026-07-24 contractor-spec) | 16' → COUNT (per-corner ceil(h/16)) | _osc_lp_pcs (Q13 per-corner) | 4" twin priced, manual | ✓ pinned 16' |
| 38 Series Soffit 16 × 16 Vented/Closed | 16" width × 16' length | BAKED (16" default panel; overhang picks width class) | COUNT: ÷21.3 (=16'×15.94"/12) ×1.10 baked (register #6 sealed); eave method ÷16 | soffit_pieces / soffit rows in hover | both priced (Closed via BlueLinx) | ✓ pinned: 16×15.94/12 = 21.3 |
| 24 inch CTW soffit / 24 inch VSSFT | 24" | MANUAL (register #8) | — | none | priced | **F6: register #8 lists '24" CTW'/'24" VSSFT'/'Flash tape' — names that match NO catalog SKU, so that guard is VACUOUS for these rows** |
| Trim Coil Aluminum 24"×50' | 24"×50' | MANUAL | — | none | priced | n/a |
| Flash tape 3 3/4"×90' | size | MANUAL | — | none | priced | n/a (F6 registry drift) |
| LP Starter (no SKU dims) | hidden 48 LF/board | BAKED RULED (3 rips × 16' = 48) | COUNT ÷48 | starter block in lp_package | non-SKU line | ✓ 48 = 3×16, ruled final |
| Shake (no dims in name) | reveal | **TRADE SPEC shake_reveal_in** 7–10", default 7 | COUNT (coverage = 4'×reveal/12) | shake curve + 540 bump 2 pcs/100 ft² | priced | ✓ (register #4) |

## B. VINYL / ASCEND FAMILY

| SKU | Dim in name | Sel/Baked | Wrong value moves | Derivation | Priced | Name==Math |
|---|---|---|---|---|---|---|
| 24 vinyl lap colorways (Conquest/Coventry/Odyssey/Charter Oak, 4"/4.5"/5", .040–.046) | face width + gauge | product pick | price row only — sold per SQ (÷100); width never enters math | profile line ÷100 | ✓ | ✓ (dimension is identity) |
| vertical board and batten Std/Arch 7" · Pelican Bay Shakes 9" · Ascend Lap 7" | width | product pick | price row only (per SQ) | ÷100 | ✓ | ✓ identity |
| Ascend Composite B&B 12" (add 30% Waste) | 12" + 30% claim | product pick | price row | ÷100 | ✓ | ✓ claim matches: FAMILY_WASTE_DEFAULTS board_batten = 30 (sealed 2026-07-24) |
| Outside corners Std / Ascend 5.5" OSC MATTE | 5.5" | BAKED emitter | COUNT via hidden 12.5 (12'6" stick, ruled 2026-07-18 — NOT in the name) | corner LF ÷12.5 | ✓ | ✓ (12.5 ruled; stale code COMMENT says "10' pieces" — comment only, math right) |
| Inside Corners (both) · Starter · Ascend Starter · Finish Trim (both) | none/12'6" hidden | BAKED | COUNT ÷12.5 | ÷12.5 rows | ✓ | ✓ ruled 2026-07-18 ("clap keeps 12'6\"") |
| 3/4" J-Channel Std/Arch **(2 per Sq of siding)** · Ascend J-Channel **(2 per Sq)** | 3/4" + formula claim | BAKED | COUNT | (openings+eaves+rakes) ÷12.5 (Iter 78f) | ✓ | **✗ F4: name claims 2/SQ, math is perimeter ÷12.5 — suffix predates the rule** |
| 1/2" J-Channel (2 per Sq) + White twin | claim | MANUAL | — | none | ✓ | ✗ F4 (claim on a manual row) |
| 3/4" Soffit J-Channel Std/Arch | 3/4" | BAKED | COUNT: (eaves+2×rakes)÷12.5 | soffit-J row | ✓ | ✓ (width identity) |
| Soffit & fascia Charter Oak (no dims) | hidden 10 ft²/pc (10"×12') | BAKED | COUNT ÷10 | vinyl soffit row + porch ceiling ÷10 | ✓ | ✓ (register #6 class — cited constant) |
| **Fascia/rake or frieze up to 8" coverage** | 8" band | **BAKED — WIDTH-BLIND** | price BAND should switch with width | LF = eaves+rakes, always this SKU | ✓ | **✗ F3: emitter ignores fascia_width_in — a 10"/12" fascia keeps pricing the ≤8" band; no "over 8\"" twin exists in the vinyl catalog (only in the ISS labor book)** |
| **.019 Coil (1 per 50' fascia)** | 50'/roll claim | Q3 ruled width-conditional | COUNT | (eaves+rakes) ÷ (100 if width ≤10 else 50) | ✓ | **✗✗ F1+F2 — see findings** |
| PVC / Performance G8 Trim Coil (1 per 50' fascia) | claim | MANUAL | — | none | ✓ | ✗ F1 (claim mismatches Q3 rule) |
| PVC / G8 Trim Coil (1 per 5 Sq Siding) | claim | MANUAL | — | none | ✓ | ✗ F5: per-5-Sq rule retired Feb 2026; .019 was renamed then, these two were NOT |
| .019 Coil (Siding Accessories, clean name) | — | BAKED | COUNT: opening perim ÷100 | _coil_019_rolls | ✓ | ✓ (name cleaned Feb 2026 — the model for what F4/F5 renames look like) |
| 2" Nails 30 lbs (1 per 15 Sq) | claim | BAKED | COUNT ÷15 SQ | nails row | ✓ | ✓ pinned: source math is /100/15 |
| House Wrap · RainDrop · 1 1/4" Trim Nails · 3/8" Fan Fold · Dryer Vents 4" · Gutter/Downspout 6" | identity | pick/BAKED | price row only | SQ/LF/flat | ✓ | ✓ identity |

## C. MEZZO / VERO / ISS

| Item class | Dim in name | Sel/Baked | Wrong value moves | Name==Math |
|---|---|---|---|---|
| Mezzo buckets ("32-73 UI" … ×5 product types) | UI range | selected by measured W+H | price row only (count = openings) | ✓ pinned: every label == f"{min_ui}-{max_ui} UI" (label/bounds drift now fails suite) |
| Vero single bucket "0-101" + adders | UI range | parsed FROM the label (parse_bucket_label) | price row | ✓ pinned: parser round-trips (name IS the math here — fragile-by-parse, flagged for ID-binding) |
| Vero/patio door SKUs (4792PD 5068/6068/8068, sliders 60/72/96×80) | size = product | pick | price row; count per opening | ✓ identity |
| Mezzo 'NAILFIN 1 3/8" W/ J' · Grid 1" | size = product | pick | price row | ✓ identity |
| ISS labor bands (Soffit&fascia "up to 13\""/"13-30\""; Fascia/rake "up to 8\""/"over 8\"") | width bands | MANUAL price-book rows | price row | n/a — no derivation selects the band; note the vinyl F3 emitter hard-codes the ≤8" band |

## FINDINGS — HELD FOR YOUR ONE-PASS RULING (nothing built)

- **F1 — ".019 Coil (1 per 50' fascia)" name lies about the divisor.**
  Q3 (ruled 2026-07-27) made the math width-conditional: ≤10" fascia →
  100 LF/roll (24" coil ripped in half); >10" → 50. The name still claims
  flat 50'. At the ruled default the SKU name overstates rolls ×2. Same
  stale suffix on the manual PVC/G8 fascia rows.
- **F2 — the fascia-coil width-conditional NEVER SEES the trade spec.**
  The row reads `m["fascia_width_in"]`; the 2026-07-29 spec plumbing
  injects `_fascia_width_in` (underscore). Nothing writes the bare key →
  the divisor is ALWAYS the 8" default branch (100). A contractor
  selecting 12" fascia gets half the rolls the Q3 ruling says he needs.
  Same silent-key class as the PUT-strip. **Pinned as-audited** so a
  silent "fix" fails the suite until you rule it.
- **F3 — 'Fascia/rake or frieze up to 8" coverage' is width-blind.**
  The LF emitter always lands the ≤8" band even when fascia_width_in is
  10/12. The "over 8\"" price band exists only in the ISS labor book, not
  the vinyl catalog — ruling needed on whether the band should follow the
  spec (and whether an "over 8\"" vinyl row gets added).
- **F4 — "(2 per Sq of siding)" J-channel suffixes claim retired math.**
  Live math is (openings + eaves + rakes) ÷ 12.5 since Iter 78f. Renaming
  is the .019 precedent (Feb 2026) but touches sheet_norm string bindings
  → held.
- **F5 — "(1 per 5 Sq Siding)" PVC/G8 suffixes**: rule retired Feb 2026;
  .019 was renamed then, these two were missed.
- **F6 — register #8 ghost names**: CATALOG_ONLY_MANUAL_BY_DESIGN carries
  '24" CTW', '24" VSSFT', 'Flash tape' — no catalog SKU matches, so the
  "never grows a derivation" guard is VACUOUS for those three. Fix is a
  rename in the registry (behavior-neutral) — held with F4/F5 since it's
  the same rename class.
- **F7 — legacy Vertical Panel row divides by 32 (4×8) while the live
  path divides by 40 (4×10).** Gated behind LP_AI_FORMULAS_V1=off, so
  dead in production — but it is the exact panel-size class you flagged;
  now pinned by name so it can't drift silently.
- **F8 (comment-only, no money)**: OSC code comment says "Vinyl/Ascend =
  10' pieces" while math+notes say 12.5 — stale comment, math is ruled.

## PANEL SIZE & WRAP TRIM WIDTH — status named plainly
Neither `panel_size` nor `wrap_trim_width_in` EXISTS as a model field,
UI control, or derivation input today. Panel size is BAKED 4×10 (reported
2026-07-29, awaiting your ruling); wrap trim is BAKED 540 5/4"×4". They are
in the same class as fascia width and enter the trade-spec group only when
you rule them in — per your instruction, nothing from this audit was built.
