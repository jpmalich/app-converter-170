# UI PASS REPORT — WHAT A HUMAN SAW (2026-07-30, testing agent iterations 48 + 49)

## THE FINDING YOU PREDICTED — CAUGHT, FIXED, RETESTED
Iteration 48, walked like a contractor: every backend behavior was perfect
(PUT bounds 422'd, materialize renamed 4'x10'→4'x8' and moved 68→84, wrap
renamed name-only 62→62, values persisted in Mongo) — **and the browser
lost every spec on save anyway.** `buildPayload` in useEstimate.js is a
field WHITELIST and nobody had added the spec fields: batten_spacing_in,
fascia_width_in, shake_reveal_in, panel_size, wrap_trim_width_in (and
color_tier, lp_soffit_type — stripped since they were built). The PUT the
autosave sent simply did not contain them; the server "defaulted" what it
never received. Pytest-green, browser-broken — the exact shape of the
four builds you named. FIXED: all seven fields ride the payload;
SettingsRow specs now save IMMEDIATELY (saveSpec: no debounce race) and
dispatch the LP panel's re-derive event so the rename/count is visible
live.

## SECOND FIND (retest, iteration 49): WRAP LINE DOUBLED 62→124
Preview showed 540×6 at 124 after the wrap spec — my post-pass rename
broke assemble's assign-by-name against the tab seed hover had already
renamed → two lines merged. FIXED with the fascia pattern (SKU name
derived UP-FRONT) + OSC-precedent supersede of stale differently-named
540 seeds. Verified via API walk 4→6→12→4: qty 62 at every width,
name-only, no duplicates, clean round-trip.

## WHAT A HUMAN SAW AFTER THE FIXES (iteration 49 + API verification)
- Set 4×8 / wrap 6 / fascia 12 / batten 16 → navigate away → return:
  ALL FOUR VALUES STILL SELECTED, and GET /api/estimates/{id} carries them.
  THE SILENT-STRIP TEST PASSES IN THE BROWSER.
- Panel 4×8: LP package panel re-derives live → "38 Series 4' x 8' Panel"
  qty 84 (was 4'×10' qty 68). Count moved exactly 40/32.
- Wrap 6": 540 line renames, qty 62 unchanged.
- Fascia 12": 440 line renames to 4/4"×12".
- Material list: whole quantities everywhere; healed lines print
  "R3 whole units (healed 2026-07-30: was 5.28)".
- Coil colour chips render on .019/PVC/G8 rows in both blocks; blank
  colours show the amber "colour not set — set in Job Info".
- Print view opens and in-app navigation returns without browser back.

## STANDING STRUCTURAL GAP — NAMED, NOT PATCHED
THE VINYL/ASCEND TABS HAVE NO REBUILD PATH. Stored vinyl lines re-derive
only at import/recalc. Consequence a contractor can see: with fascia set
to 12", the .019 fascia-coil ROLL COUNT doubles on the NEXT import, not
on the stored lines of an old estimate. Same structural gap that froze
the 5.28s through the R3 seal. F2 itself is fixed and pytest+API-proven
(test_fascia_coil_width_conditional_reads_the_spec_key; live API build
returns 2.0→4.0 rolls at 8"→12"). If you want a "re-derive vinyl tab"
action, that is ~0.5–1 day — your call, not built.

## PVC/G8 COLOUR CHIP — GO DELIVERED (display layer, SectionAccordion)
A note cannot ride a line that is never emitted — so the chip lives at
the display layer for the manual rows, same visual as the emitted ones.

## MANUAL-ROW CENSUS — THE BLIND SPOT, QUANTIFIED
153 of 226 catalog rows are NEVER emitted by any derivation — no emitter
note can ever reach them. Structured:
- ~60 Vero/Mezzo window-engine rows: filled by the WINDOW quote engine,
  not estimate derivations (annotatable through that engine, not ours).
- ~30 Architectural colour twins: reached by the colour-tier swap of an
  emitted Standard row — notes RIDE the swap; not blind in practice.
- ~24 vinyl lap colourways: the family profile emitter emits the selected
  one; the rest are alternates — not blind, just unselected.
- **~39 TRULY BLIND manual rows** — hand-filled, structurally invisible
  to every note/provenance mechanism built this week: the Misc
  labor/material block (mini splits, J blocks, cut-out 4×4, dryer vents,
  gutter guard, shutters, gable vents…), sliding-door labor rows, LP
  manual substitutions (440 6/10/12, 540 alternates, 4×8 panel manual
  row, OSC 4", CTW/VSSFT, flash tape, trim coil), 1/2" J-channels, fan
  fold, PVC/G8 (now chip-covered), house-wrap tape class. Full list:
  memory/manual_rows_census_2026-07-30.txt.
Anything a contractor hand-types on those rows carries no derivation
note, no provenance chip, no spec binding — they show name, qty, price,
nothing else. That is the blind spot, quantified.
