# SPANISH TRANSLATION REPORT (2026-07-31 — report only, NO CODE)

## 0. HEADLINE ANSWERS
- Coverage today: the core contractor journey (editor UI → material list →
  customer quote/email) is ~70% Spanish-ready; the gaps are (a) ~45 newer
  JSX surfaces with hardcoded English and (b) EVERY backend-generated label.
- The SKU pin: **CANNOT BE CONFIRMED — IT DOES NOT EXIST.** Worse: the rule
  is VIOLATED at render today — 84 catalog row names translate in ES,
  including AMI-numbered SKU rows. Detail in §4, ruling needed.
- Nothing stops a new string shipping English-only today. Detector sized §5.
- Cost to finish (contractor-facing): ~5–8 days. Breakdown in §6.

## 1. HOW TRANSLATIONS ARE STORED (the architecture, as built)
- Language is PER-DEVICE: `localStorage.lang` via `LangProvider`
  (frontend/src/lib/i18n.jsx). Missing key → falls back to the key/EN.
- **The backend never translates.** DB, API payloads, catalog names, line
  names, flags — all English. ES exists ONLY at render time. This is why
  catalog binding, money math, and provenance are language-safe by
  construction (identity keys never change with the toggle).
- Four frontend stores:
  1. `dictionaries.js` — UI strings: 458 EN / 459 ES keys, ZERO EN-only
     keys today (measured). One pin exists but only for email.* customer
     vocabulary (test_model3d_wording_split).
  2. `catalogTranslations.js` — SECTIONS_ES (~40 titles) · **ITEMS_ES (84
     catalog row names — see §4)** · UNITS_ES (12, incl. ROLL→ROLLO) ·
     COLORS_ES + legacy-alias map.
  3. `itemDescriptions.js` — 43/43 item help texts EN+ES.
  4. Print/email builders carry `lang` branches inline: materialList.js
     (EN/ES labels + note label), lpMaterialList.js, emailQuote.js,
     printTakeoff.js — 172 lang branches measured across the print/email
     pair.

## 2. COVERAGE TODAY — BY SURFACE
| Surface | State |
|---|---|
| Estimate editor core (rows, columns, totals, Job Info, ISS editor) | ES via dictionary — GOOD |
| Material list print (vinyl/ascend/windows) | ES labels + units + sections — GOOD (blind-row note label ES'd 2026-07-31) |
| LP material list print | ES ternaries throughout — GOOD |
| Customer quote + email + accept page | ES — GOOD (customer-vocabulary pin exists) |
| Item help descriptions | 43/43 EN+ES — GOOD |
| Provenance chips ("human qty", "contractor sets labor", "⌁ derived", coil colour, trade-spec titles) | HARDCODED EN |
| AI Measure / Tape Check / Elevation Sheets / Field Verify | HARDCODED EN (large surfaces) |
| Flag banners + checklist labels (facade scope, batten heights, opening schedule…) | **BACKEND-GENERATED EN** — print regardless of toggle |
| Derivation notes on lines ("converted 27 SQ → 3 ROLL @ 9 SQ/roll — $311.85 → $357.33") | BACKEND EN — these are provenance RECEIPTS (see §6 recommendation) |
| Branding Admin (supplier-internal) | EN — arguably stays EN (Alside staff) |
Measured: 27 of 72 JSX files use the dictionary; the other 45 carry at
least some hardcoded English (many are internal/supplier surfaces).

## 3. WHAT STOPS A NEW STRING SHIPPING ENGLISH-ONLY TODAY
**NOTHING.** The 458/459 parity is discipline, not enforcement. There is no
key-parity detector, no hardcoded-string lint, and nothing scanning the
print builders. The one existing pin checks email.* vocabulary only.

## 4. THE SKU / PRODUCT-NAME PIN — NOT CONFIRMED, AND THE RULE IS BREACHED
- `ITEMS_ES` translates **84 catalog row names at render**, including
  AMI-numbered SKU rows: House Wrap → "Membrana para casa" (AMI 646662A0),
  Starter → "Tira de arranque" (AMI 107361), the Finish Trim / Outside
  corner / Soffit & fascia families, and more. In ES mode these render in
  the editor AND in the printed material list's DESC column.
- Brand names (Charter Oak, Ascend, Conquest, Pelican Bay…) stay English
  today — but by a COMMENT CONVENTION in catalogTranslations.js, not a pin.
  Nothing fails if someone adds "Charter Oak": "Roble Carta" tomorrow.
- Mitigations that hold today: the AMI part-number column always prints
  untranslated, and the DB/API/binding layer is English-only — an order
  keyed by AMI# is safe; the exposure is the yard reading the desc column.
- **RULING NEEDED (two shapes, pick one):**
  a. HARD RULE — catalog row names render VERBATIM in every language;
     ITEMS_ES retires for catalog rows; ES help lives only in the
     secondary description line (itemDescriptions). Pin: test fails if
     ITEMS_ES contains any live catalog row name. ~0.5 day incl. purge.
  b. SOFT RULE — the EN SKU name always prints, with the ES descriptor as
     secondary text beside/under it ("House Wrap — membrana para casa").
     ~1 day (print + editor render changes) + the same pin scoped to
     "EN name always present".

## 5. THE DETECTOR (so a new string can't ship English-only) — ~0.5 day
- Pin 1: EN/ES key-set parity in dictionaries.js (fails on any EN-only key).
- Pin 2: contractor-facing component register — files on the contractor
  journey must import useT and carry no literal sentence-strings in JSX
  (register + grep-based, same species as the one-emitter detectors).
- Pin 3: print builders — every literal label in materialList/lpMaterialList
  must sit inside a lang branch or dictionary call.

## 6. COST TO FINISH (contractor-facing Spanish, supplier admin stays EN)
| Piece | Effort |
|---|---|
| Hardcoded strings in contractor-facing components (chips, banners, trade-spec group, AI Measure/Tape Check surfaces) | 2–4 days |
| Backend-generated labels: translate BY CODE at render (flags/checklist items already carry codes) — never by string match | 2–3 days |
| Derivation notes on lines | **RECOMMEND: DO NOT TRANSLATE.** They are provenance receipts quoting rulings and dollars; a translated receipt is a mutated record. Print them verbatim with an ES caption ("nota de derivación"). ~0 days |
| SKU pin + ITEMS_ES ruling (§4) | 0.5–1 day |
| Parity/lint detector (§5) | 0.5 day |
| **TOTAL** | **~5–8 days** |

## 7. QUEUE AFTER THIS REPORT (as ruled)
ID-BASED CATALOG BINDING comes back to Howard for a ruling — it is also
the structural fix for §4's exposure class (names stop being identity, so
display language can never corrupt binding).
