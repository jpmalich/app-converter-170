# ID BINDING — DAY 1 RECEIPT (2026-07-31)

## WHAT LANDED
- catalog_ids.py: 226 app-minted PERMANENT ids, checked in as literals
  (never regenerated — a rename can never re-mint an identity).
- Seed attaches item_id to every built tier item.
- migrate_2026_07_31_item_ids.py (STAMPS, NEVER DERIVES): 904 tier items
  + 506 estimate lines stamped across the 17 survivors. Self-refusing
  diff active on every estimate.

## THE PROOF HOWARD REQUIRED — per estimate, material list BYTE-IDENTICAL
Rendered through the real print builder (buildMaterialListHtml) before
and after the migration, byte-compared:
17/17 IDENTICAL — e452a988, db82ec7a (doug jones), 8f95c9c2 (Letrick),
673707d5 (red house), e2ce35b8 + 40bb13a3 (Casile), 786ff854 + 94712a40,
5fc1d3a0 + 6c837ebc, 34ca0985 + 533e770c, f3e7d728 + 1679183d (all four
3 Degree pairs), 48231310 + d78cd3b4 (both 261 Haugh), f064bffc (LP demo).
Ground-truth houses untouched to the byte.

## LEFT ALONE, NAMED (the migration never guesses)
- e2ce35b8 Jon Casile: [Seamless Gutter with Siding] "Gutter" and
  "Downspout" — legacy pre-rename row names outside today's catalog.
  Await a human ruling (bind to "Gutter 5\"" / "Downspout 6\"" or leave).

## BACKUPS
/app/memory/backups/20260731_150000_{estimates,price_tiers}_pre_item_ids.json

## REMAINING (days 2–4)
Binding flip (reads prefer item_id, name fallback) → rename-safety pin →
retire string classifiers → full-suite green.
