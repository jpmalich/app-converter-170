# RULINGS 2026-07-30 — LANDING REPORT (all six, one pass)
Stamps: R1 batch `2026-07-30 11:00 UTC · 2c53b54 · CLEAN · 1589` ·
main batch `2026-07-30 12:01 UTC · 9a899aa · CLEAN · 1594 passed, 1 skipped`.

## R1 accepted · Letrick supersession STAMPED (annotated, not edited)
lp_truck_reconcile.py Soffit-J block now carries: "records the 2× eave rule
as of the September truck; SUPERSEDED BY R1, 2026-07-30" — derivation and
matched-18 evidence untouched.

## COIL COLOUR — GO delivered
Both derived .019 Coil lines carry the wrapped component's colour from Job
Info MATERIAL COLORS (emitter-sourced note, never in the name):
- opening wrap ← `window_wrap_color`; fascia wrap ← `soffit_fascia_color`
- unset → "colour not set — set in Job Info" (never silence)
RESIDUAL, named: PVC/G8 are MANUAL rows with no emitter — no note can ride
a line that is never emitted. The colour hint for those two needs a small
display-layer pass on the tab renderer (~0.25d) — awaiting go, not built.

## R3 — DIAGNOSIS FIRST (a/b/c), THEN BUILT
(a) WHY coil escaped the f059181/9bc1dbd seal: the seal put whole units at
TWO order layers — backend `_bake_tab_waste` (runs ONLY on the LP tab
rebuild) and frontend `bakeWasteIntoLines` (runs ONLY at import/apply).
Your live 5.28s were imported the MORNING of 7-28; the seal landed 19:09
that evening, and the vinyl/ascend tabs have NO rebuild path — pre-seal
fractional rows sat frozen on the stored surface forever. And the server
emitter `_build_lines` itself never rounded, so any server-side door
skipping the frontend bake could store fractional. ROLL was never special;
the surface was.
(b) WHAT ELSE escaped: 26 distinct line names across vinyl/ascend/lp on 11
live estimates — coil ROLL (5.28/6.28/6.03/3.21…), OSC/J-channel/finish
PCS (14.5, 61.5, 70.5…), House Wrap/RainDrop SQ (31.5, 26.1), 38 soffit
PCS (15.5/12.5), 440/540/190 PCS (25.5, 68.5, 465.5). All healed.
(c) WHY the detector missed it: the pin tested the LAYER (the two bake
functions in isolation) — the wrong surface, as you suspected. It stayed
true while pre-seal rows printed because nothing walked the composed build
output and no retroactive sweep existed. NAMED.
BUILT: `_order_whole_units` now runs INSIDE `_build_lines` (every tab,
every unit, each line on its own; raw survives on raw_qty; cut-prone rows
ceil at the waste bake — 0.5 retired everywhere, same −1e-9 seal). Surface
detector `test_no_door_prints_a_fractional_order_quantity`. Retroactive
heal migration swept all stored fractional lines with the delta NAMED on
each line note ("R3 whole units (healed 2026-07-30: was 5.28)").
YOUR COIL, AS RULED: 5.28→6 and 6.28→7 — THIRTEEN ROLLS, lines apart.

## R4 — ASCEND INSIDE CORNERS RETIRED
Emitter deleted; orphaned $11.83 removed from the seed; the four estimates
healed — line deleted on each; TOTAL EFFECT $0.00 ON ALL FOUR (every line
was mat=$0.00 × qty: Casile 3, 3-degree family 14/15.5, unnamed 1) — the
quotes never carried a dollar of it, which is exactly the defect.
CLASS REGISTERED AS A DETECTOR: `test_every_static_emitter_item_resolves_
to_a_live_catalog_row` — any emitter item that no live catalog row carries
fails the suite.

## #5 — 540 readback closed by Howard (screenshot artifact). 540-trim-4"
outlier at 1.4023 KEPT on record.

## #6 — EVERYTHING ELSE
- STRIP LIST LANDED (13 renames, code+tests+frontend+DB tiers+stored
  estimate lines): coil ×3 suffixes ×2 blocks, J-channel ×5, nails,
  Ascend B&B. KEPT 'Ascend - 5.5" Trim (16' length)' (product dimension).
  ISS labor book bands untouched (real price bands, not app SKU names).
- REGISTER RENAMES: register #8 now carries the exact catalog strings;
  pinned by `test_registry_names_resolve_to_live_catalog_rows`.
- F1: math stands (Q3 width-conditional 100/50); name stripped.
- F2 FIXED: fascia-coil divisor reads `_fascia_width_in` — 12" fascia now
  actually halves the roll coverage. CLASS DETECTOR:
  `test_spec_keys_are_read_by_the_exact_key_they_are_written_under` (bans
  bare-key reads of any spec the plumbing writes). Consumer table: all 5
  spec keys (_shake_reveal_in, _batten_spacing_in, _fascia_width_in,
  _panel_size, _wrap_trim_width_in) written by hover scoped-injection +
  lp_package_routes merge; every consumer reads the exact underscore key.
- F3: 'Fascia/rake or frieze' loses the coverage wording (labor row keeps
  $0). Scan of every $0 labor row for material/dimension wording: CLEAN —
  no others in the class.
- F7: gated-legacy 4×8 Vertical Panel rows DELETED (both families); stale
  pin rewritten to assert ABSENCE.
- PANEL SIZE + WRAP TRIM WIDTH — BUILT into the trade-spec box.
  panel_size ∈ {4x10 default, 4x8}: changes COUNT and SKU (÷40 vs ÷32).
  wrap_trim_width_in ∈ {4 default,6,8,10,12}: renames the 540 line ONLY
  (whole Q12 scope wrap+ISC+frieze carries the width; counts untouched).
  TEST NAMES: test_spec_fields_survive_the_put_model (declared + 422 on
  panel "4x12" / wrap 5" + values persist) ·
  test_wrap_and_panel_specs_bind_and_move_what_they_claim ·
  test_bb_panel_spec_governs_sku_and_count_legacy_4x8_path_deleted ·
  test_every_width_variant_sku_binds_to_a_priced_row (540 widths priced =
  wrap variants priced). UI: panel-size-select / wrap-trim-width-select in
  the trade-spec group.
- ID BINDING: NOT AUTHORIZED — held, will re-present with a clear queue.

## Migration (backend/migrations/migrate_2026_07_30_rulings.py, ran once)
Tier item renames · estimate line renames · R4 removals · R3 heal — full
per-estimate console table preserved in this file's git history; heal
verification: 0 fractional lines remain, 0 old names in tiers, 0 Inside
Corners lines.
