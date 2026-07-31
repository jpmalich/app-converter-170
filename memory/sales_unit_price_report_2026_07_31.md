# SALES-UNIT PRICE + STALENESS REPORT (2026-07-31, report only — NOTHING CONVERTED)

## 1. ROLL CONVERSION — PER-ESTIMATE IMPACT (House Wrap 9 SQ/roll @ $119.11 · RainDrop 11.25 SQ/roll @ $336.13)
Stored SQ prices today: HW $11.55/SQ · RD $30.73/SQ (NOTE: catalog carries
$30.73, Howard wrote $38.73 — flagged, likely typo, confirm before landing).
Roll-equivalents: HW $103.95/roll-equiv → $119.11 = **+14.6%**;
RD $345.71/roll-equiv → $336.13 = **−2.8%** (RainDrop actually gets cheaper
per covered square; the money that moves is mostly ROUNDING to whole rolls).

| Estimate | Item | Today | Converts to | Delta |
|---|---|---|---|---|
| doug jones (db82ec7a) | House Wrap | 16 SQ $184.80 | 2 ROLL $238.22 | +$53.42 |
| doug jones | RainDrop | 16 SQ $491.68 | 2 ROLL $672.26 | +$180.58 |
| Jon Casile (e2ce35b8) | House Wrap | 27 SQ $311.85 | 3 ROLL $357.33 | +$45.48 |
| Jon Casile | RainDrop | 27 SQ $829.71 | 3 ROLL $1,008.39 | +$178.68 |
| TEST_test run 7-25 (3a7761e2) | House Wrap | 16 SQ $184.80 | 2 ROLL $238.22 | +$53.42 |
| TEST_test run 7-25 | RainDrop | 16 SQ $491.68 | 2 ROLL $672.26 | +$180.58 |
| 7-26-26-2pm (e3c469df) | House Wrap | 16 SQ $184.80 | 2 ROLL $238.22 | +$53.42 |
| 7-26-26-2pm | RainDrop | 15 SQ $460.95 | 2 ROLL $672.26 | +$211.31 |
| TEST_test 7-26 7pm (3127b2fd) | House Wrap | 16 SQ $184.80 | 2 ROLL $238.22 | +$53.42 |
| TEST_test 7-26 7pm | RainDrop | 16 SQ $491.68 | 2 ROLL $672.26 | +$180.58 |
| (unnamed) (40b8d771) | House Wrap | 32 SQ $369.60 | 4 ROLL $476.44 | +$106.84 |
| (unnamed) | RainDrop | 27 SQ $829.71 | 3 ROLL $1,008.39 | +$178.68 |
| 3 degree rd (786ff854) | House Wrap | 50 SQ $577.50 | 6 ROLL $714.66 | +$137.16 |
| 3 degree rd | RainDrop | 45 SQ $1,382.85 | 4 ROLL $1,344.52 | **−$38.33** |
| 3 degree rd 7-28-26 (f3e7d728) | House Wrap | 47 SQ $542.85 | 6 ROLL $714.66 | +$171.81 |
| 3 degree rd 7-28-26 | RainDrop | 43 SQ $1,321.39 | 4 ROLL $1,344.52 | +$23.13 |
| **TOTALS (8 estimates)** | | **$8,840.65** | **$10,610.83** | **+$1,770.18** |

No company catalog overrides exist on either item — every line above uses the
seed price, so one seed+migration change covers everything.
SEQUENCE ANSWER: do NOT enter roll prices on the admin page first — $336.13
against a line still counted in SQ would price 16 SQ of RainDrop at $5,378.
The unit and the price land TOGETHER in one migration (delta named once, on
the line note per estimate); verify on the admin page AFTER.

## 2. THE OTHER THREE — CATALOG vs SALES-UNIT (confirm before converting)
| Item | Catalog today | As sales unit (implied) | Money movement |
|---|---|---|---|
| 2" Nails 30 lbs | $81.63 per JOB (flat, size-blind) | BOX @ ceil(SQ÷15) — implied $81.63/box | any job >15 SQ pays more: 20 SQ → 2 boxes $163.26; 45 SQ → 3 boxes $244.89. CONFIRM $81.63 is the price of ONE box |
| 3/8" Fan Fold | $11.06 per SQ | BUNDLE (2 SQ) — implied $22.12/bundle | none if bundle really is $22.12 — CONFIRM |
| Downspout 6" | $2.80 per LF | 10' STICK — implied $28.00/stick | rounding to whole sticks only — CONFIRM stick price |
Gutter 6" stays LF (seamless — ruled OK).
RainDrop ≠ House Wrap divisors honored: two constants (11.25 / 9.00), never a
shared "wrap roll" number. When it lands: qty in the SALES unit, rounded up,
material list prints "4 ROLL" not "31.5 SQ". Coverage: HW = vinyl · RD =
Ascend (each family's wall underlayment, by nature); nails/fan-fold vinyl+ascend.

## 3. PRICE AGE — THE ANSWERS
a) RECORDED? Only a DOC-LEVEL `updated_at` per surface (whole tier doc, whole
   vero/mezzo/iss doc, company catalog doc). NO per-item, NO per-field, NO
   history. Worse: the stamp is POLLUTED — seed re-syncs on backend restart
   refresh it (all four tier docs read 2026-07-31 today from last night's
   restarts, not from any human price change). So in practice: **a price's
   age is NOT recorded anywhere trustworthy.**
b/c) Cost to add (it must be ADDED, not displayed): stamp `mat_changed_at` /
   `lab_changed_at` per item on every HUMAN write path (4 tier editors, bulk
   apply, ISS CSV, Mezzo/Vero matrix, LP admin) with seed-sync explicitly NOT
   stamping — ~1–1.5 days incl. tests. Showing it (date on the row + amber
   age chip on anything older than N days + oldest-price line on each tier
   card) — +0.5 day. Optional price-history event (who/old/new/when) — +0.5–1 day.
   Total ~2–3 days for the full thing.
d) Last-changed per family, from what exists today (doc stamps + git):
   - Vinyl/Ascend contractor tiers: **unknown** (doc stamps overwritten by
     restart syncs; last human seed change via git: catalog_seed.py 2026-07-31 —
     that was the Pelican Bay half-square ruling, not a price review)
   - Vero: **unknown** (doc stamp today, same pollution)
   - Mezzo: **unknown** (no updated_at on docs at all)
   - ISS: 2026-06-15 (doc stamp — plausibly the real CSV upload date)
   - LP: source-dated by construction — BlueLinx PIT00003 2.26.2026
e) YES, PIT00003 2.26.2026 IS STILL LIVE — QUOTE_REF in lp_costs.py, last
   touched 2026-07-24 (structural, not a re-source). Your KEEP-CURRENT ruling
   chose the source; the source is now ~5 months old. Nothing in the app ages it.

## 4. ADMIN-PAGE FINDINGS
1. COMPANIES: the page shows 500 because the endpoint caps at `.to_list(500)`
   (catalog.py:213). REAL COUNT: **2,043 companies — 2,039 are TEST_***.
   Non-TEST: Pro-Quote Estimating Tool (yours), GusGear, Pappans, and
   "ZZ Fixture Test Co" (test by name). So ~3 real. All 146 invitations are
   @resend.dev test invites sitting PENDING. WHY UNTAGGED: the test-artifact
   tag + purge tool exist ONLY for fixture_runs (run_archive) — suite-created
   companies/users/invitations have no tagging mechanism, so the purge tool
   cannot see them. The 28-estimate PIPELINE count is all in real companies,
   but 5 of the 28 are TEST_-named estimates created by testing agents logged
   in as you. Cleanup options (awaiting go): one-off purge by TEST_ prefix +
   resend.dev with a census receipt (~0.25d), or the durable fix — tag-on-create
   and extend the purge tool to companies/users/invitations/estimates (~0.5–1d).
2. LP-NATIVE MODE OFF — noted in the September demo checklist (REMINDERS.md):
   Howard flips it ON himself before the demo.

## 5. QUEUE (as ruled)
1. Sales-unit conversions — HELD until Howard rules the three price confirms
   above (+ the $30.73-vs-$38.73 RainDrop discrepancy)
2. Blind row notes (39 rows, note prints on material list)
3. Spanish report (report only)
4. ID binding queue
