# SEND-75 (revised) + SEND-76 — REPORT (2026-08-21)
Report only. Nothing was written to any estimate, zone, or line.

## SEND-75 · EST-713272 RE-CHECK

### The headline, plainly
**Howard did not only delete the 18.0 SQ line — he deleted the entire
zone group.** All 9 human siding zones (the 3,291.26 ft² legacy group,
INCLUDING the suspended straddler `33e4b47a`) are gone from
`pdf_overlay_polygons`. The only zones left on EST-713272 are 4
PROPOSED zones (provisional, sqft None — Boni has no evidence scale;
proposals never feed a quantity).

### What siding computes to now
- Vinyl siding line: **22.0 SQ · qty_src DERIVED** — this is the
  polygon-captured derived baseline RESTORED by the delete-retirement
  path (`routes/pdf_overlay.py` L830-842: deleting the last binding
  zone of a class restores `derived_baseline_qty` and re-marks the
  line derived, "even if the editor stripped the line's overlay
  markers" — which is exactly what happened here).
- Ascend line: 18.0 SQ (raw 17.5) — the latest done run's own number.
- The 22.0 is NOT the zones' number (gone), NOT the latest run's
  number (17.5), and NOT the sealed 33. It is the baseline captured on
  the polygons at zone-creation time, frozen from an older read. Its
  note still carries stale HOVER waste text ("41.1 → 42") from the
  original derivation — the note does not describe the 22.0.

### Did the class rebind, and to what?
**No rebind occurred and none can** — there are no human zones left to
bind. The class retired to derived 22.0 SQ.

### The 31.95-vs-32.91 prediction
**Neither.** The live number is 22.0 SQ. The prediction's decomposition
was arithmetically right (32.91 − 31.95 = 0.96 SQ = the straddler's
95.8 ft²) but its PRECONDITION is gone: it assumed the 8 sound zones
still existed and only the straddler was out. Howard deleted all 9.
The difference decomposes as: 31.95 SQ (8 sound zones) − 22.0 SQ
(restored derived baseline) = 9.95 SQ = the entire zone layer being
removed, not a suspension defect. While the zones existed, the
suspension DID reach the math (`apply_overlay_to_takeoff` skips
`binding_suspended` zones) — the question is now moot, not refuted.

### The two layers, split explicitly (latest done run, 2026-08-16)
| face  | derived ft² | status |
|-------|------------|--------|
| front | 920.0 | derived |
| back  | 680.0 | PARTIAL — "garage wing 1-story" segment height not read (subset) |
| left  | — | REFUSES: "wall width not read — area not derivable" (body AND shake gable) |
| right | — | REFUSES: "footprint does not close: right depth 39 present but opposing left depth not read" |
| left chimney chase | 150.0 | appendage |
| **derived total** | **1,750 ft² = 17.5 SQ** | 2 of 4 faces, one partial |
| **human zones** | **0 ft²** | all deleted |

Two cautions on even that 1,750:
1. The run PREDATES the height build (SEND-47, 8-18) and line-work
   (SEND-69). A FRESH read today would refuse more — the Boni faces
   refuse on height under current law. The 920/680 stand on the
   pre-height chain.
2. Nothing anywhere on this estimate is near the sealed 33 SQ anymore.
   The zone layer that carried ~32 SQ is gone. If a total near 33
   reappears, it will be Howard redrawing zones — and must be reported
   as the zone layer, never as the app deriving it.

### The rest of the check
- **Suspension / other 8 zones:** deleted with the group. The
  `binding_suspended` flag died with its zone. Nothing remains to
  suspend.
- **Overlay markers:** neither "back" nor "stripped" — the line was
  RETIRED to derived; markers are correctly absent because nothing
  binds.
- **New warnings:** none. The estimate warns about LESS than before —
  the NOT BINDING banner is gone with the zone.
- **Anything else human-set:** NO. Zero lines on EST-713272 carry
  qty_src=human or lab_src=human.
- **A reporting gap, named (not fixed):** the zone-delete route
  records a DELETED correction event ONLY for proposals
  (`pdf_overlay.py` L811) and ledgers only protected estimates.
  Howard's 9 human-zone deletions on this unprotected estimate left
  NO record anywhere — no event, no tracking entry, no ledger. The
  deletion is inferred from the restored 22.0 baseline (only the
  editor delete path restores it). Deletion time/author unrecoverable.

## SEND-76 · CENSUS — human-set lines with overlay markers stripped

### The count
**The stripped class is EMPTY. Zero estimates carry it today.**
EST-713272's line was the only member ever observed, and Howard cured
it himself by deleting the zones (retirement restored the derived
value and the record).

Full sweep of all human-set lines (21 lines on 8 estimates):
- **Markers INTACT (modern, has record): 3 lines** — EST-886440
  (18.74 SQ), EST-655664 (11.77 SQ), EST-569367 (25.94 SQ). All three
  recompute to EXACTLY their stored value (delta 0.00 SQ / $0). Stored
  and computed agree.
- **Markers NEVER EXISTED (no zones ever on the estimate): 18 lines
  on 5 estimates** — plain hand-typed values, legitimate under Law A;
  these are a DIFFERENT finding from stripping. The ones carrying a
  `derived_qty` stamp and their deltas (stored − derived, direction):
  - EST-853809 "3 degree vinyl": Ascend Lap 7" stored 0.0 vs derived
    47.0 → **−47 SQ / −$27,382 (down)**; Ascend Starter stored 0 vs
    53 → −53 PCS / −$468 (down). Shape of a deliberate family zero-out,
    but they are stamped human, so they are listed.
  - EST-111561 "boni 8-9": Charter Oak 37.0 vs derived 37.0 → 0.
  - The remaining 14 (windows/mezzo fees, B&B 72 SQ, lovi road 18 SQ,
    Conquest/Coventry 0s) carry no derived stamp → "human-set — prior
    computed value unknown." Raw rows: `memory/send76_census.py`
    (re-runnable, read-only).

### THE QUESTION THAT OUTRANKS THE COUNT — how markers get stripped
**A LIVE CODE PATH EXISTS AND IS STILL REACHABLE.** Traced through the
write path, not inferred from data shape:

`routes/hover.py` rederive rebuild merge (~L3357-3372, shared by
`/rederive`, hover-lp-run, lp-package/materialize; fired by SPEC-SAVE
and the manual re-derive button — normal editor flow, not import-only):
1. The rebuild constructs FRESH line dicts from the derivation.
2. For a previous line with `qty_src == "human"` it carries ONLY
   qty/raw_qty/qty_src (+ mat/lab/adders/ami_part/contractor_note/
   item_id). `superseded_qty`, `overlay_superseded`, `overlay_sqft`,
   the PDF-OVERLAY note — ALL DROPPED.
3. **An overlay-BOUND line is qty_src "human" by construction**
   (`apply_overlay_to_takeoff` sets it at bind time). So every
   rederive of an overlay-bound estimate carries the zone-fed qty
   verbatim and strips the record of what it superseded.
4. Nothing re-runs `apply_overlay_to_takeoff` after the rebuild — its
   only callers are the pdf-overlay routes themselves.

This is EXACTLY EST-713272's history: zones bound the line, Howard's
8-14/8-15 manual rederives ran the merge, the markers vanished, the
human qty stayed. The class is produced by rederive-after-bind.

**Blast radius:** historically 1 known line (EST-713272, cured).
Today: the 3 marker-intact estimates above (EST-886440, EST-655664,
EST-569367) will EACH join the class on their next rederive/spec-save.
The set is empty but the tap is open.

**NOT FIXED in this pass — not authorized.** Fix shape for the report:
the rederive merge either carries the overlay marker fields through,
or re-runs `apply_overlay_to_takeoff` after the rebuild (the cleaner
cure — the overlay law is the single owner of those fields). Retrofit
ratio: 0 current entries need retroactive repair; prevention is the
entire value of the fix.
