# SEND-91 — BONI (EST-713272) RE-PROPOSE, WIPE LEDGERED
2026-08-21 22:26 UTC · live via POST /pdf-overlay/propose (actor hhunt6677@yahoo.com) · response kept at `/app/memory/send91_propose_response.json`

## PROVENANCE OF THE NUMBER BEING REPLACED — stated as ruled
The wiped geometry descends from run `c54633996e7a49e48432cf66a61efaf7` — the
8-16 read that PREDATES the height build, the run whose 20.0 ft stackup the
census proved UNRECONSTRUCTABLE: 9'-11" + 8'-1½" = 18.04, not 20.0, and the
8'-1½" was never located on any sheet (the sheets print 8'-1⅛" as a ceiling
note). **The geometry being replaced was built on a fabrication. That is the
reason it goes — not "stale".** The 22.0 SQ figure from the SEND-75 report is
that run's polygon-captured baseline story; the estimate's stored model
`siding_sqft` (4,113 ft² = 41.1 SQ) descends from the same pre-height read.
For the record as observed today: the stored money line itself is human-set
18.0 SQ (raw 17.5) with no overlay markers — proposals never fed it and this
re-propose does not touch it (proposals are provisional by law).

## HUMAN-ZONE GUARD — verified BEFORE the wipe, as ruled
- Zero human-provenance zones remained: `pdf_overlay_polygons` count with
  `provenance != "proposed"` = **0** (the nine human zones were already lost
  unrecoverably — SEND-84 report 1).
- The wipe path CANNOT reach one if it existed: both the ledger snapshot query
  and the delete are filtered `{"provenance": "proposed"}` in the propose route
  (`routes/pdf_overlay.py`, wipe block), and the SEND-84 pins in
  `test_deletion_ledger_2026_08_21_send84.py` hold it.
- Confirmed after: human zones still 0; proposed = 4 (all fresh).

## THE WIPE, LEDGERED
`zone_deletion_ledger` row `kind=propose_rebuild_wipe`, 4 polygons snapshotted
IN FULL (vertices, provenance, tiers, proposed_from incl. run id) — the four
pre-SEND-77 proposals (no x_fence on any of them: superseded-rule geometry).

## WHAT CAME BACK — coverage is a FACT, never an improvement
4 of 4 faces propose, ALL at the weak tiers, exactly as expected:
- front: datum_rectangle · wall_outline geometry · **height NOT established**
  (refusal: two different wall heights 8'-1" and 29'-1" — contested)
- back: datum_rectangle · wall_outline geometry · height NOT established
  (gap SECOND_FLOOR→TOP_OF_PLATE **UNDIMENSIONED** — the joist band)
- left: datum_rectangle · datum_span_after_linework_refused ("all spanning
  boundaries sit at one corner") · height contested (6'-0" vs 9'-1")
- right: band_rectangle (no datum pair located; **no FIRST FLOOR datum**)

**Split as always:** derived ft² = 0 (every face refuses on height under
current rules — named reasons above); human-zone ft² = 0 (none remain);
faces refusing = 4 of 4. The re-derived total is far below the old figure —
**that is the rulings working, not a regression**: a confident wrong number
descending from a fabricated stackup, replaced by named refusals a crew can
answer with a tape.

New proposals carry current-rule disclosure: x_fence on every line-worked
face, `proposed_from.attribution` (SEND-90), and the response's
`width_cross_check` = SILENT_INDETERMINATE on the Boni p4 tie — silence
because attribution is unresolved, distinguishable from agreement.

## CENSUS ITEM CLOSED
Boni was the ONLY estimate on superseded-rule wall-outline geometry. Post-wipe
sweep across ALL estimates: **zero** proposals remain with wall_outline
geometry and no x_fence. Nothing else has drifted onto superseded rules since
the census ran.
