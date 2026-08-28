# SEND-142 — CLEANUP: THE DUPES, THE RAIL, THE NAME

Stamp, quoted verbatim from `scripts/handback_green.sh`:

```
RECORDED: 2026-08-28 01:34 UTC · e3f83e6 · CLEAN
RESULT: 3058 passed, 9 skipped, 7 warnings in 461.45s (0:07:41)
CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none); 8 removal(s) logged
INGRESS SMOKE: 4 passed in 1.98s
```

Cleanup only. **No sealed figure moved. No quote number moved. Phase 2
stays off.** EST-886440 untouched; EST-373526 was drawn on in the browser
check and every mark plus the scale was deleted after.

---

## ITEM 1 — THE DUPLICATE CATALOG KEYS ARE GONE, AND THE LAST ONE WAS NOT IDENTICAL

`memory/send142_probe_catalog.py` (read-only) now prints **NOTHING** —
there is not one repeated dict-literal key left in `catalog_seed.py`.

- **11 dropped earlier in this send**: the three coil items
  (`.019 Coil`, `PVC Trim Coil`, `Performance G8 Trim Coil`) were declared
  twice in `ITEM_META` and twice in `PER_TIER_PRICES` with **byte-identical
  values**. The second declaration always won at module load; the survivor
  is the value that was already in force, so the catalog fingerprint is
  unchanged and pinned.
- **1 dropped on the way out of this send, and it was NOT identical**:
  `'3/8" Fan Fold'` appeared twice in `IDENTICAL_PRICES` — **11.06 then
  22.12**. The later literal governs in Python, so the catalog has always
  charged **22.12** (the 2026-07-31 SALES UNIT ruling, SQ → Bundle, 11.06 × 2).
  The dead 11.06 line was removed and its history written into the comment
  above the surviving row. **NO PRICE CHANGED** — `test_pricing_parity`
  locks the round-trip and is green.

## ITEM 2 — THE RAIL IS THREE PANELS, AND THE PINS WERE UPDATED BY NAME

`PhotoTakeoffEditor.jsx` 800 → **626 lines**; the right rail is now
`phototakeoff/ScalePanel.jsx` (52) · `QuantitiesPanel.jsx` (70) ·
`MarksPanel.jsx` (217), with the shared mark vocabulary (colours,
categories, tap order, labels) in `phototakeoff/marks.js` (35) so each
file reads ONE declaration.

**The panels stay dumb**: `qtyCell`, `sqftOf`, `gDims`, `ft2` and
`receiptFor` are still OWNED BY THE EDITOR and passed as props — SEND-141's
rule (`qtyCell` is the ONLY thing allowed to decide what a quantity cell
may say) survives untouched, and the combined surface still contains
`qtyCell(m, a)` exactly TWICE: the mark row and the tag on the shape.

**NAMED PIN UPDATE, not a silent flip.** Ten pins read the editor's source
TEXT and went red the moment the text moved into the panels — the suite was
RED on arrival at this fork and is green now.
`tests/phototakeoff_surface.py` reads the WHOLE surface (editor + three
panels + marks.js) and **fails loud if a surface file is missing**, so a
pin can never pass over a file that quietly disappeared. Every assertion
is the same assertion; nothing was relaxed. Files updated: send131a,
send132, send136, send139 (incl. the 0.70 sweep, which now scans every
panel), send140, send141.

**BROWSER VERIFICATION (`test_reports/iteration_61.json`, 6/6, EST-373526
front elevation, real photos)**: three separate panels in one screenshot ✓ ·
anchor then tape → **TAPE GOVERNS**, refusal cleared ✓ · confirmed gable
prints `26.4 ft × 11.0 ft rise · ½ × w × rise = 145.2 ft² · pitch 10/12`
and the row and the Gable lane both read 145.2 ✓ · flat gable → row **—**,
dims `= —`, receipt *"Measure the rise at the peak on this photo — width is
known, rise is not."*, **no `0 ft²` anywhere** ✓ · contractor REFUSE on a
measured gable → **—** ✓ · pull-in HTTP 200, no 500, no console exception ✓.
Every drawn mark and the scale were deleted at teardown.

## ITEM 3 — THE CUSTOMER NAME IS OFF THE PATH AND OFF THE CONSTANT

- `backend/letrick_hand_takeoff_key.py` → **`backend/sealed_hand_takeoff_key.py`**
  (`git mv`), constant `LETRICK_HAND_TAKEOFF_KEY` → **`SEALED_HAND_TAKEOFF_KEY`**.
  **CONTENTS BYTE-IDENTICAL** apart from that one constant name: no figure,
  no basis line, no ruling text touched (the 262.5 re-seal, the 2026-07-18
  exposure correction and the item-3 chase ratification read exactly as
  they did).
- `letrick_hand_takeoff_key.py` remains as a **thin re-export shim for ONE
  release** — it holds no figure of its own, so there is still exactly one
  home for the sealed values.
- Live imports repointed: `routes/lp_package_routes.py` ·
  `routes/elevation_sheets.py` · `lp_domain_manifest.py` (both the new
  module and the shim are enumerated, so the fork-boundary drift check
  stays green) · the `lp_conventions.py` ground-truth docstring · and the
  four test files that import it (send138, item-3 chase ratification, lap
  unification, sealed-key portability).
- `fixture_figures.py`: `"letrick"` → **`"sealed_hand_takeoff"`**. The
  figures list is unchanged and `all_fixture_figures()` returns the SAME
  28 numbers, so the prompt-purity pin scans exactly what it scanned
  before. Its coupling pin was updated by name and now also asserts the
  old key is GONE.

### WHERE THE NAME STILL LIVES — REPORTED, NOT AUTHORISED THIS SEND
1. **`boni`, `tanis`, `dart`** are still customer names in the same
   registry (`fixture_figures.py`). Howard ruled letrick only this send.
2. The portable gate flag value **`sealed_key == "letrick_v3"`** — DATA on
   the fixture estimate doc, matched in `routes/lp_package_routes.py` and
   `routes/elevation_sheets.py`. Renaming it is a fixture-data migration,
   not a code rename.
3. **`LETRICK_TAPE_WALLS`** in `routes/demo.py` (imported by
   `elevation_sheets.py`) — a second constant of the same family.
4. Two test FILENAMES (`test_letrick_item3_chase_ratification.py`,
   `test_letrick_lap_unification_ruling.py`) — imports fixed, filenames
   left per Howard's ruling.
5. The name appears in ~80 files overall (demo/fixture customer records,
   report narratives in `memory/`, `memory/backups/` — including the two
   backup paths the sealed module's own ruling text cites, which is why
   that text was not edited).

## NOT TOUCHED
Phase 2 trim runs · quote / material-list wiring · rectify / homography ·
the blueprint path · hover/photo storage split · the eleven 0.70
estimates (still no sweep, per SEND-138 ruling 1).
