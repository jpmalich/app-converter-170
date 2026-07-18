# Vinyl Starter / Base-Treatment Composition Trace (2026-07-18, trace-first per ruling)
Scope: how starter and vertical-base treatment derive TODAY on vinyl paths,
against the batch pins: no starter on B&B ever · shake regions derive shake
starter #65516000 · clap keeps 12'6" · B&B base = J-channel context line.

## T1 — Starter derivation today (hover.py HOVER_MAPPING_SPEC ~line 789)
- ONE vinyl line: item "Starter" (AMI 107361, PCS, IDENTICAL_PRICES $7.64 all
  tiers), qty = ceil(starter_lf ÷ 12.5). Ascend mirrors ("Ascend - Starter",
  AMI 107371, $8.83).
- Same spec drives BOTH the Hover import and the photo path
  (/api/measure/map): ai_measure.py maps starter_lf (falls back to eaves_lf,
  line 2022).
- STALE COMMENT (line 788-789): says "qty = LF ÷ 10 (per Howard)" while code
  does ÷12.5 — the old ÷10-vs-÷12.5 open question. RULING NOW CLOSES IT:
  clap keeps 12'6" → ÷12.5 is canonical; comment syncs in the cut.

## T2 — Starter is PROFILE-BLIND (the defect the batch fixes)
`starter_lf` is whole-house base LF. On mixed-profile vinyl estimates
(_per_profile_sqft: lap + shake + board_batten — e.g. Haugh {lap 1840,
shake 168, b&b 60} → 3 field lines), the single Starter line still prices
ALL base LF as clap starter:
- SHAKE regions → priced as clap starter today (violates "never priced as
  clap starter").
- B&B regions → get starter LF today (violates "no starter on B&B ever" —
  the existing pin is lp_smart-scoped only: lp_smartside_formulas.py
  starter_on_bb=False; vinyl B&B has NO equivalent guard).

## T3 — Shake starter #65516000 "Pelican Bay Shake Starter": CATALOG GAP
Zero hits in catalog_seed.py / routes / frontend. Not in ITEM_AMI, not in
any price dict. The cut adds it as its OWN product + price line:
- Section: Siding Accessories (vinyl tab), unit PCS.
- Four-tier structure available: PER_TIER_PRICES {whole-sale, Contractor,
  Builder-Dealer, one-opp} (59 items) or IDENTICAL_PRICES (61 items).
- Tier sheets carry NO price for it today → seeds in PRICING-PENDING state
  (price never borrowed from clap Starter $7.64 — pinned "never priced as
  clap starter"). AMI part = 65516000 via ITEM_AMI.

## T4 — B&B base J-channel (ruled: base treatment = J-CHANNEL, no starter)
Vinyl catalog J stock: 3/4" J-Channel Std/Arch + 1/2" J-Channel white.
Today NO base-J line derives anywhere for B&B regions. Per ruling (5): base J
derives as its OWN CONTEXT LINE per the (3+4) split, carrying the B&B
region's product color.

## T5 — Geometry available for per-region base LF split
- Photo path: profile_callouts.breakdown_walls_by_profile has per-wall family
  + wall widths → per-family base LF = Σ widths of walls in that family
  (gable-over-lap walls: base course is the body family — callout split is
  body vs gable, base always body).
- Hover path: no per-profile base-LF breakdown in the PDF parse; only
  whole-house starter_lf. Cut must state the Hover-path convention (options:
  pro-rate by per-profile sqft share, or hold single-profile behavior until
  facade data carries families).

## CUT GATE — (3+4) ruling text NOT IN THE RECORD
The fork handoff dropped the vinyl-conventions batch items (3) and (4);
PRD/registers/reminders contain no entry. (5) + pins are logged. The cut's
"context line" mechanics implement the (3+4) split — proceeding on a guessed
reconstruction would violate never-silently-pick. Howard to re-paste (3) and
(4) verbatim; logged as a handoff-state-loss note.
