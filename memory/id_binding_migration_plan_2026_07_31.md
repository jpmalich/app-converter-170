# ID CATALOG BINDING — MIGRATION PLAN (2026-07-31, REPORT — build starts on Howard's word)

AUTHORIZED SCOPE (Howard ruled 2026-07-31): move line identity to stable
app-minted IDs; AMI and BlueLinx descriptions become metadata; LP keys on
the app ID. Kills the name-string class: ghost guards, the RainDrop
classifier, rename risk, translation risk.

## THE ONE RULE OF THE MIGRATION
**IT STAMPS. IT NEVER DERIVES.** The migration adds ONE field (`item_id`)
to catalog items and estimate lines. It reads no measurement, calls no
derivation, and recomputes no quantity or price. A migration that
re-derives is a migration that can change a number — so the writer is
built to be INCAPABLE of it.

## HOW THE SURVIVING ESTIMATES MIGRATE WITHOUT MOVING A NUMBER
1. **Mint** — every catalog row gets a permanent `item_id`, checked into
   catalog_seed.py as LITERALS (not generated at runtime — reseeds are
   reproducible, IDs never re-mint). Tier docs + company catalogs get the
   same IDs stamped by name-match ONCE, at migration time.
2. **Stamp estimate lines** — for each of the 17 survivors' lines:
   resolve name → id through the EXISTING alias-canonical map (the same
   healing tItem uses), then `l["item_id"] = id`. Nothing else on the
   line is touched — not qty, not mat/lab, not unit, not notes, not
   qty_src. Human-typed rows are untouched by construction (field-add
   only).
3. **Unresolved rows are LEFT ALONE and named** — a line whose name
   resolves to no catalog row keeps no ID, appears on the receipt, and
   waits for a human. The migration never guesses (the exact-string
   lesson, kept).

## THE PROOF, BUILT INTO THE WRITER (not run after it)
- **Self-refusing diff**: before writing each estimate, the script builds
  the after-image and asserts `after == before` on EVERY line with only
  `item_id` added (canonical-JSON compare, key-by-key). ANY other
  difference aborts the whole estimate's write — zero rows land.
- **Receipt**: per estimate — lines stamped / lines skipped-unresolved /
  bytes-identical-otherwise: YES.
- **Pre-heal backup** of all 17 estimates + tier docs + catalogs to
  /app/memory/backups/ before the first write (standing rule).
- **Idempotent**: re-running stamps nothing new, changes nothing.
- **Pin**: test_id_migration_never_moves_a_number — fixture estimate with
  human-typed qty, frozen line, contractor note, adders; migrate; assert
  every field byte-identical except the added item_id. Runs in the guard
  forever.

## THEN THE BINDING FLIP (days 2–4, after the stamp lands green)
- Day 2: reads prefer `item_id`, fall back to canonical name during
  transition (catalog merge, price binds, rebuild inherit, LP package
  keys). Money walks pinned unchanged.
- Day 3: rename-safety — renaming a catalog item's display name moves NO
  price and breaks NO estimate (pin: rename → re-derive → identical
  numbers, new label). AMI/BlueLinx move to metadata fields.
- Day 4: retire the string classifiers/ghost guards that ID binding
  obsoletes (each retirement named, its pin rewritten against IDs);
  full-suite green; handback.

## WHAT DOES NOT CHANGE
- Estimate lines keep `name` as the printed label (now display-only).
- The alias map stays as historical healing for pre-ID docs.
- The SKU-verbatim ruling holds: IDs are identity, names are labels,
  labels render the same string in every language.

## RISKS, NAMED
- Duplicate names across sections (same name, two sections): resolver
  keys on (section, name) exactly like today's binding — no new ambiguity.
- Pre-ID documents arriving later (trash restores): fall-back-by-name
  path covers them; a startup sweep re-offers stamping, same
  self-refusing writer.
