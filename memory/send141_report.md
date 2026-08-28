# SEND-141 — A REFUSED ROW SHOWS NO NUMBER — 2026-08-27

**STAMP: `2026-08-28 00:10 UTC · 83319d8 · CLEAN · 3058 passed, 9 skipped,
7 warnings in 463.71s`** · census pin GREEN, 0 PENDING_CONVERSION · ingress
smoke 4 passed. **Zero pre-stamp reds.**

The 0 is gone. 13 pins in
`tests/test_send141_refused_rows_show_no_zero_2026_08_27.py`, all four
verifications done **in the browser on real photos**. No estimate was
written — the run's three marks and its scale were deleted from EST-373526
afterwards. **EST-886440 untouched.**

---

## THE RULE, IN ONE PLACE

A refused mark's quantity cell is an **em dash**. Never 0, never 0.0,
never 0 ft². The receipt line stays. The reason stays. A measured gable
still prints ½ × width × rise.

`qtyCell(mark, area)` is now **the only thing in the editor allowed to
decide what a quantity cell may say**, and it answers in this order:

1. a point mark → "count only — no drawn extent";
2. no scale on the photo → "no scale";
3. **the mark is refused, or its FIGURE refused, or the area is not > 0 →
   `—`**;
4. only then, a number.

The em dash is reached BEFORE the number can be, and `!(a > 0)` catches
both `0` and `0.0` — pinned, including the ordering inside the helper.

**THE ROW AND THE TAG ON THE SHAPE ASK THE SAME QUESTION.** The 0 was
printed twice: in the mark list AND on the coloured tag drawn over the
polygon. Both call `qtyCell` now — a pin counts exactly two call sites, so
the number cannot come back on one surface while the other stays honest.

**THE SAME LIE ON THE PANELS IS GONE TOO.** The gable panel printed
`½ × w × rise = 0.0 ft²` and the cheek line could print `= 0.0 ft²`. Every
ft² figure on those panels now goes through `ft2(v)`, which answers an em
dash when there is no figure. Pinned that no `.toFixed(1)} ft²` remains.

**A FACE REFUSAL BLANKS THE CELL; A CHEEK REFUSAL NEVER DOES.** SEND-140's
ruling survives intact: the drawn dormer FACE keeps its figure while its
cheeks refuse for want of a typed depth. `figureRefused()` reads
`row.refusal` only — a pin asserts it never reads `cheek_refusal`.

**THE SAME RULE COVERS SIDING, NON-SIDING AND OPENINGS** (Howard's scope
note): any refused mark of any kind, and any degenerate shape enclosing
nothing, now shows the em dash. One rule, one helper, every kind.

**NOTHING IS PROMOTED, AND NOTHING IS WRITTEN.** The 0 was the flat
polygon's pixel area — a client-side drawing figure that never existed on
the server. The lane a refusal feeds is `None`, apply accumulates a lane
**only** `if … is not None` and emits the key as `None` unless a live
figure arrived, and a pin scans the route for `"photo_gable_sqft": 0`,
`"gable_sqft": 0.0`, `or 0` defaults and finds none. **No new coach was
added** — a pin asserts the only receipt keys in the editor are the ones
SEND-140 introduced.

---

## THE FOUR VERIFICATIONS — IN THE BROWSER (EST-373526, front elevation)

1. **Refused gable: receipt line, no 0 ft².** Row read
   `GABLE | — | CONFIRMED | … | "Measure the rise at the peak on this
   photo — width is known, rise is not."` · panel read `20.0 ft × 0.0 ft
   rise · ½ × w × rise = —` · the tag on the shape read `GABLE·—`.
   `"0 ft²" in row → False`. PASS
2. **Dormer cheeks with no depth: receipt line, no 0 ft².** Row read
   `DORMER | 27 ft²` (the FACE was drawn and measured) with the depth
   receipt; rail Dormer cheeks ft² read **—**; the cheek line still said
   *"cheeks REFUSED — depth is measured on the roof… No default depth."*
   PASS
3. **Measured gable still shows the ½ number.** Row **32.81 ft²**, panel
   `12.5 ft × 5.3 ft rise · ½ × w × rise = 32.8 ft² · pitch 10.1/12`,
   receipt element count **0** — while the refused gable's em dash and
   receipt were still on screen two rows above. PASS
4. **Nothing writes 0 ft² onto the estimate from a refusal.** The refused
   lanes report `None`; Gable ft² printed a real figure only for the
   measured triangle; Siding / Non-siding / Openings all read **—** with
   nothing drawn. Pinned on the server side as well. PASS

## SCOPE HELD · NOT AUTHORISED, NOT TOUCHED
PhotoTakeoffEditor mark list (plus the two other places the same number
was printed). Rail split · phase 2 trim · fixture rename · quote wiring:
untouched.
