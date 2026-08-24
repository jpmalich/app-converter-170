# SEND-124 REPORT — THE SPLIT LANDED · PCT GATED · DIM LANES AUTHORIZED AND LANDED · THE REGISTRY STAYS IN STEP
2026-08-24 · Items 1–3 BUILT and pinned; item 4 already registered.
STAMP: `2026-08-24 19:29 UTC · 4dfce13 · CLEAN · 2852 passed, 9 skipped`
(+12 SEND-124 pins) · census GREEN 0 PENDING_CONVERSION · ingress 4
passed. Quantities only.

## ITEM 1 — THE MATERIAL-CLAIM SPLIT, BUILT
**THE SORT (as ruled, applied to all six fields):**
- `siding_pct_this_wall` — CHANGES QUANTITY → **GATED**.
- `wall_body_profile_callout` — routes a family → confirmation card.
- `gable_profile_callout` — routes a family → card.
- `dormer_profile_callout` — routes a family → card.
- `appendages[].profile_callout` — routes a family → card.
- `stone_callout` — its LABEL only routes/annotates → card; its
  QUANTITY path ran through the pct, which is now gated. Nothing it
  touches scales a face anymore without evidence.
**THE GATE** (`_gate_siding_pct`, runs after the quote guard): default
100; a pct < 100 stands ONLY when the callout justifying it
(stone_callout / body callout) LOCATES in the run's own OCR store;
otherwise it reverts to 100 NAMED (`_siding_pct_gated` + seam ledger
`siding_pct_gated_no_evidence`) and rides the card. Fraction forms
(0.85) are normalized before judgment.
**WHAT GATING DOES ON ALL FOUR HOUSES (replayed read-only BEFORE it
landed, as ordered):**
- **Tanis (SEND-121 run)**: back 85 → 100 and left 85 → 100 — both
  STONE WATERTABLE justifications fail to locate. At the seal that
  stops a silent removal of **≈192.5 ft² (back) + ≈88.8 ft² (left)**
  had those faces derived; in the stored read both faces are refused,
  so 0 ft² moves today — the gate protects the first derived read.
- **Tanis (fresh 580ff451 run)**: model claimed 100 everywhere —
  nothing gates (run-to-run claim variation noted).
- **dart / Boni / Letrick**: all faces claim 100 — the gate changes
  NOTHING. No house loses a quantity it has today.
**THE CARD**: `_material_claims` rides measurements — claim + face +
ft² at stake (face body ft² where derived, None where refused; a gated
pct joins with its reverted claim). A grouped loud rail
`material_claims_unconfirmed` (EN/ES) names every claim on the
readback: material callouts are the model's reading, never verified;
confirm or correct before pricing. The tap-to-confirm write path is
NOT built — a derived write needs its own 423 ruling.

## ITEM 2 — THE DIM SCHEMA CHANGE, AUTHORIZED AND LANDED
Landed while the surface is empty, exactly as priced:
- 5 schema fields flipped `number | null` → `DIM | null` in
  SYSTEM_PROMPT (`soffit_sqft`, `level_frieze_lf`, `sloped_frieze_lf`,
  `drip_edge_lf`, `total_trim_sqft`), each demanding the printed quote.
- The walker change collapsed to ONE seam: the five joined
  `_EVIDENCE_SCALARS`, so `_enforce_evidence_or_null` walks them with
  the existing machinery — a quoted DIM is normalized + its quote gets
  located by the OCR nuller; **a bare number NULLS as no-evidence**
  (`_nulled_no_evidence`, ledgered) — the named, accepted risk.
- Aggregation's ~13 sites needed NO change (values arrive back as
  plain numbers post-normalization); lp_package consumers untouched.
- Both structural censuses were extended the same send: the 5 suffixes
  joined `EVIDENCE_BEARING_FIELD_SUFFIXES` (normalizer registry) and
  the schema-side detector sees the DIM declarations.
**What the five lanes carry after the change** — see the fresh-read
section at the bottom (expected: still zero; anything that appears was
previously invisible).

## ITEM 3 — THE PIN STAYS IN STEP WITH THE SEALS
**The mechanism**: the fixture-figure set moved out of the pin into
`backend/fixture_figures.py` — a registry keyed by house (boni,
letrick, tanis, dart), each entry `{figures, pending_seal}`. The purity
pin scans every prompt constant against the UNION of all houses.
**The coupling that stops silent narrowing**:
- a house entry may sit EMPTY only while explicitly `pending_seal:
  True` (dart today);
- the coupling pin fails any sealed-class entry with no figures and
  fails if any of the four known drafters is missing;
- **THE STANDING PROCEDURE: when Howard seals a house — dart next —
  its distinctive figures JOIN THE REGISTRY IN THE SAME SEND and
  `pending_seal` flips to False.** Sealing without feeding the
  registry leaves a pending entry that the sealing send's review
  catches; growing the fixture set without growing the scan is no
  longer possible silently.
House names in the registry are DATA (capture_sheet_baseline ESTS
precedent), never operative logic.

## ITEM 4 — REGISTERED (no action)
Both halves stand in RULINGS_REGISTER since SEND-123: the exposure was
real; it was not the driver of the 9'-1⅛" claim; the swap fixed a
genuine breach of a sealed invariant regardless.

## GUARD REDS BEFORE THE STAMP (both censuses catching this send)
1. Consumer-key census: internal record keys (`claimed_pct`,
   `wall_body_sqft`) read via `.get` — fixed to subscript + membership
   (SEND-116 precedent, census untouched).
2. Normalizer registry: the 5 new DIM fields had to be REGISTERED as
   evidence-bearing suffixes and the walk-detector taught they ride
   the `_EVIDENCE_SCALARS` loop — the send-6 bypass class doing its
   job on the very change it was built for.

## THE FRESH READ AFTER THE CHANGE (Tanis, cached pages, run 072e8c36)
(One earlier rerun attempt, e476c690, died when the guard's ingress
smoke recycled the server mid-run — errored honestly, retried after
the stamp.)
- **THE FIVE LANES CARRY: None · None · None · None · None.** Nothing
  in `_nulled_no_evidence` either — under the DIM schema the model
  claimed nothing at all. STILL ZERO, as expected; nothing previously
  invisible appeared.
- pct: 100 on all four faces this run — the gate is armed, nothing to
  gate (the 85s were a prior run's claims; run-to-run claim variation
  continues).
- **THE CARD IS LIVE**: 7 material claims surfaced (body callouts on
  all four faces + stone callouts on back/left/right), ft²-at-stake
  None on every one — the faces are refused, so no ft² rides any
  unconfirmed claim. 12 rails render, including
  `material_claims_unconfirmed`, `lf_lane_refused`,
  `below_grade_unread`.
- The model volunteered **9'-1⅛" a THIRD time** ("9'-1 1/8\" FIRST
  FLOOR LEVEL TOP OF WALL") under the fully neutral prompt — nulled
  again; the composition answer strengthens (n=2 post-swap reads, the
  print's own glyphs both times).
- window_count 2 this run (5 count refusals named — the model claimed
  different rows again; counts land only where evidence locates).
  starter None · siding 0.0 · every SEND-122/124 guard holding.

## OPEN ITEMS AFTER THIS SEND
- **Dart's sealed ground truth — Howard.** Its figures join
  fixture_figures.py in the sealing send. Tanis alone is still an
  anecdote.
- Material-card tap-to-confirm write path — not built; needs a 423
  ruling if wanted.
- Walkout human-flag entry surface — rail exists; manual entry path
  awaits ruling.
- Symbols placement — NOT AUTHORIZED.
- Catch-all message inventory — still owed.
- rot180 — held. CCC — unvalidated at n=2.

Standing rules held: no cross-drawing borrowing, no estimate influenced
another, no job names in operative code (registries are data), model
heights hypothesis-only. EST-886440 untouched. Purity pin now scans a
growing set. 423 untouched (no derived write).
