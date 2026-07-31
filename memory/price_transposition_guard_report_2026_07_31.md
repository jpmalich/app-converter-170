# PRICE TRANSPOSITION GUARD — SIZING REPORT (2026-07-31, report only, NOTHING BUILT)

## WHAT HAPPENED (the class, named)
Howard's price-page upload landed House Wrap and RainDrop CROSSED
(HW $336.13 / RD $119.11 — each carrying the other's roll dollar), stamped
2026-07-31 11:57:44 UTC by `supplier-admin`, same instant across all four
tiers — one bulk write burst. The bulk flow DID show a diff preview; the
preview printed raw old→new numbers with no percentage, no loudness, no
pair-check. "House Wrap $11.55 → $336.13" scrolled past as one quiet row
among many. Only Howard's own sanity check (31.5 SQ = 4 rolls = $476.44)
caught it. NOTHING in the app would ever have said a word.

## WHAT IT WOULD TAKE (three pieces, sized separately)

### 1. Magnitude gate on the diff preview — the one that stops the hand (~0.5 day)
`_diff_upload` (routes/pricing_admin.py) already computes `old` and `new`
per cell. Add per-change: `pct` (+2810%), `magnitude_flag` when the move
exceeds 3× up or 3÷ down. Preview table renders flagged rows LOUD (red row,
"×29.1 — confirm this row" checkbox); the Apply endpoint REFUSES any flagged
change that arrives without its per-row confirm. Same gate on preview-bump
(a fat-fingered 300% bump gets the same wall).
CARVE-OUT REQUIRED: a legitimate sales-unit flip (SQ → ROLL) IS a ~10×
dollar move — which is why this is a CONFIRM gate, never an auto-refuse.
The row states its unit beside the dollar so the human sees "$11.55/SQ →
$336.13/SQ" and smells it.
This piece alone would have printed "House Wrap $11.55 → $336.13 (+2810%)"
in red and demanded a click on that specific row. Howard's words: that
would have stopped his hand.

### 2. Transposition pair-detector — the class-specific catch (~0.5 day)
Signature that is cheap and precise: among the magnitude-flagged rows of ONE
upload, find pairs (A, B) where SWAPPING their new values would put BOTH
rows back under the threshold while as-entered BOTH breach it. That is
exactly what crossed rows look like and almost nothing else does. Renders
one banner: "These two rows look TRANSPOSED: House Wrap ↔ RainDrop —
confirm each individually." Runs only on flagged rows, so zero cost on
clean uploads.

### 3. Same gate on the single-cell tier editors (~0.5 day)
The four tier editors (`admin_update_tier`) write per-cell with no preview
at all. Server-side: a >3× move returns 409 with the old/new/pct named;
the UI re-sends with `confirm: true` after an explicit click. Keeps the
one-emitter shape (the check lives in one helper both surfaces call).

## WHERE IT BELONGS
Same price-integrity surface as the age chip (price_age.py) — the flag
threshold, the loud-row styling, and the stamps all live together on the
admin panel. The register test (test_price_write_stamps_2026_07_31.py)
already enumerates every price-write surface; the magnitude helper joins
that register so a new surface cannot ship without the gate.

## TOTAL
~1–1.5 days for all three, incl. pins. Piece 1 is the half-day that
catches the next transposition before it lands; pieces 2–3 close the
class. Nothing built until Howard rules.
