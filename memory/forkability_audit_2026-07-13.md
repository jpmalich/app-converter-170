# FORKABILITY AUDIT — LP SmartSide Domain (2026-07-13)

**Question audited:** can the LP catalog, conventions, pricing engine, and templates be extracted as a standalone white-label product — no shared mutable state across domains, all data domain-tagged?

**VERDICT: FORKABLE — with one enumerated carve-out (hover.py `_build_lines` LP branches) and five thin, named seams. No cross-domain mutable state found. All LP data is domain-tagged.**

## 1. Module dependency audit (backend)
**LP core modules import ZERO app infrastructure** (no `db`, `deps`, `config`, `server`, no route modules):
| Module | Imports | Role |
|---|---|---|
| `lp_conventions.py` | stdlib + `lp_smartside_formulas` | ruled conventions, PENDING_CONFIRMATIONS, MILESTONES |
| `lp_package.py` | stdlib + `lp_conventions`, `lp_smartside_formulas` | package assembly (C3/C4 corner features, starter, fascia) |
| `lp_costs.py` | stdlib only | BlueLinx cost sheet, tier ladder seed, sell math, redaction |
| `lp_colors.py` | `lp_conventions` | ExpertFinish palette + component groups |
| `lp_smartside_formulas.py` | stdlib (`os` for the flag) | PDF coverage formulas, `LP_AI_FORMULAS_V1` gate |
| `lp_truck_reconcile.py` | stdlib + `lp_conventions` | acceptance harness |
| `letrick_hand_takeoff_key.py` | none | sealed ground truth |
**Dependency direction is strictly one-way: app → LP.** LP modules never import vinyl/ISS/Vero/Mezzo domain code. (The "vinyl" strings inside `lp_conventions.SYSTEM_DERIVATION` are doctrine DATA — the per-system derivation table — not code coupling.)

## 2. Shared mutable state audit
- **Cross-domain: NONE.** The single deliberate cross-domain bridge is `lp_costs.CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS` — a **frozenset** (immutable), explicitly named as a contract, consumed read-only by `catalog.py` / `pricing_admin.py`.
- **Intra-LP:** one module-level mutable — `lp_smartside_formulas._OVERRIDE_FLAG` (request-local admin-preview override, documented thread caveat, never touched by other domains). Everything else at module level is compiled regexes / derived constant dicts.

## 3. Data / DB tagging audit
| Store | Tagging | Forkable? |
|---|---|---|
| `lp_material_list_snapshots`, `lp_legacy_price_archive` | dedicated `lp_`-prefixed collections | ✓ lift whole |
| `settings` docs | domain-tagged ids: `lp_margin_tiers`, `lp_native_mode` | ✓ filter by id prefix |
| `estimates` | `kind="lp_smart"`, all LP fields `lp_`-prefixed (`lp_pricing_tier`, `lp_colors`, `lp_field_verify`, `lp_openings_review`), lines carry `tab="lp_smart"` | ✓ tagged (shared doc model comes along in a fork — a fork is a full quoting product) |
| Catalog seed | `SECTION_PRODUCT_LINES` maps every LP section EXCLUSIVELY to `["lp_smart"]`; seed comment pins "nothing shared bleeds into the LP tab by accident" | ✓ |
| Cost data | `BLUELINX_COSTS` embedded in `lp_costs.py` (single source; BlueLinx sheet upload pending as ruled) | ✓ |
| Env | one flag: `LP_AI_FORMULAS_V1` | ✓ |

## 4. Templates & frontend audit
- `lib/lpMaterialList.js` — **zero imports, fully self-contained** printable-list builder (EN/ES, QR block, verification trail).
- `lib/lpColors.js` — LP-only palette mapping.
- Components: `LpMaterialListPanel.jsx`, `OpeningsReviewCard.jsx`, `pages/LpFormulaPreview.jsx`, `pages/MaterialListShare.jsx` — consume only shared UI infrastructure (api client, i18n, shadcn) + LP libs.
- i18n: 52 `lp.*` keys inside the shared `dictionaries.js` — extractable by prefix (SEAM S5).

## 5. Route adapter layer (thin, enumerated seams)
LP-only routers: `lp_package_routes.py`, `lp_admin.py` (import db/deps as adapters — expected; they ARE the extraction's HTTP layer). Non-LP consumers of LP modules, all read-only one-way:
- S1 `routes/catalog.py` — LP engine pricing at estimate tier + exceptions frozenset
- S2 `routes/estimates.py` — tier seed, CSV one-surface derive, share endpoints
- S3 `routes/pricing_admin.py` — LP section guard
- S4 `routes/hover.py` — **THE CARVE-OUT** (see §6)
- S5 `dictionaries.js` — `lp.*` key prefix
- (migrations `migrate_iter97/100_*.py` are one-time scripts, not runtime deps)

## 6. The one carve-out: `routes/hover.py`
`_build_lines` is a shared multi-domain estimate builder with **~95 LP touchpoints** (LP formula swaps, soffit scaling, shake bumps) branching inside vinyl/ascend logic. Extraction requires carving the LP branches into an `lp_build_lines` seam (the LP math itself already lives in `lp_smartside_formulas` — the branches are thin call sites, but they are interleaved). This is the only file where LP logic is not physically separated. **Recommendation:** when the fork is actually exercised, extract an `lp_ingest.py` that owns the LP branches of `_build_lines`; until then the entanglement is contained and one-way.

## 7. Test portability
9 dedicated `tests/test_lp_*.py` files + the sealed key module pin conventions, costs, colors, package assembly, and single-source doctrine — the pin suite travels with the domain (854-test app suite green as of this audit).

## Findings summary
- **F1 (PASS):** one-way dependency, pure domain core, no infrastructure imports.
- **F2 (PASS):** no cross-domain mutable state; the one bridge is an immutable, named contract.
- **F3 (PASS):** all LP data domain-tagged (collections, settings ids, estimate fields, catalog sections, line tabs).
- **F4 (PASS):** templates self-contained; frontend LP surface enumerable.
- **F5 (ACTION, non-blocking):** hover.py `_build_lines` LP branches need carving at fork time (§6).
- **F6 (NOTE):** `lp.*` i18n keys live in the shared dictionary — extract by prefix.

**Conclusion: the domain-separation architecture holds. A white-label LP extraction is a lift of 7 backend modules + 2 LP routers + 4 frontend files + prefix-filtered data, with one planned carve (hover ingest) and five thin seams — no untangling of shared mutable state required anywhere.**
