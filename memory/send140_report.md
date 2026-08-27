# SEND-140 — THE REFUSAL RECEIPT: GABLES AND DORMER CHEEKS — 2026-08-27

One contractor sentence on the refused mark, saying what to tape. Nothing
else. 15 pins in `tests/test_send140_refusal_receipt_2026_08_27.py`, all
four verifications done **in the browser on real photos**. No estimate was
written — the three marks and the scale the run created on EST-373526 were
deleted afterwards. **EST-886440 untouched.**

---

## THE LINE — WRITTEN FROM THE LIVE REFUSAL, NOT HARD-CODED

Every sentence is produced by the refusal that actually fired, from the
field that is actually missing. These are the real strings the app emits:

| what refused | the line the contractor sees |
|---|---|
| gable, peak on the eave line | **"Measure the rise at the peak on this photo — width is known, rise is not."** |
| gable, both eave taps on one spot | **"Re-tap the left and right eave points apart on this photo — rise is known, width is not."** |
| gable, not a triangle yet | **"Trace left eave, peak, and right eave — this mark is not a triangle yet (2 of 3 points)."** |
| gable, no scale on the photo | **"Set the scale on this photo — tap both ends of a span you measured and type its feet; the triangle is already drawn."** |
| dormer cheeks, depth not typed | **"Type the dormer depth in feet — the face is drawn, cheeks cannot be counted without it."** |
| dormer, not a face yet | **"Trace all four corners of the dormer face — this mark is not a face yet (3 of 4 points)."** |
| dormer, corners on one spot | **"Re-tap the dormer corners apart on this photo — two of them landed on the same spot."** |
| dormer, no scale on the photo | **"Set the scale on this photo — tap both ends of a span you measured and type its feet; the face is already drawn."** |

**IT NAMES THE MISSING FIELD, NOT A GENERIC PLEA.** A gable missing its
RISE says *rise is not* known and that the width IS. A gable missing its
WIDTH says the opposite, in the same breath — pinned both ways round, so
the two can never be swapped. The point-count lines carry the mark's **own
count** ("2 of 3"), which is why they could not be hard-coded.

**WHAT IT NEVER DOES** (each one pinned across every sentence the route can
emit): no invented number · **no `0.7`, no `0.70`, no "factor"** · no ft²,
no "typical", no "average", no "assume" · **never points at another photo
or another face** (no "another", no "other face", no "opposite", no
"mirror", no "same as") — every line points at THIS photo, THIS mark, or
the depth field in front of him.

**A MEASURED FIGURE CARRIES NO RECEIPT.** `receipt` is `None` on a
measured gable and `cheek_receipt` is `None` on a counted cheek; a drawn
dormer face whose depth is missing keeps its FACE figure and carries the
receipt on **the cheeks only**. A provisional mark earns none either —
not confirmed is not refused; it is guidance, already named as such.

**THE SERVER WRITES THE LINE; THE EDITOR ONLY PRINTS IT.** The rail sends
`gable_receipts` / `dormer_receipts` — `{id, label, receipt}` and nothing
else, keyed by mark — and the editor looks the sentence up by mark id. A
pin asserts none of these strings exists in the JSX, so the reason cannot
be re-decided (or drift) on the client.

---

## THE FOUR VERIFICATIONS — IN THE BROWSER, ON REAL PHOTOS

Estimate EST-373526, front elevation photo, scale set with a two-tap span:

1. **A gable missing rise shows the line.** Three taps on one line →
   confirmed → the row printed **"Measure the rise at the peak on this
   photo — width is known, rise is not."** and the rail's Gable ft² stayed
   an **em dash**. PASS
2. **A dormer with no depth shows the line on the cheeks.** Four taps →
   confirmed → **"Type the dormer depth in feet — the face is drawn,
   cheeks cannot be counted without it."**, Dormer cheeks ft² an **em
   dash**, Dormer face ft² **27 ft²** (the face was drawn, so the face
   counts). PASS
3. **A measured gable shows no receipt.** A real peak → panel read
   `12.5 ft × 5.3 ft rise · ½ × w × rise = 32.8 ft² · pitch 10.1/12`,
   rail **32.81 ft²**, receipt element count **0** — while the flat
   gable's receipt was still showing one row above, so the absence is the
   rule working, not the feature missing. PASS
4. **No money token on the route.** `total_sell`, `unit_price`, `"mat"`,
   `"lab"`, `margin`, `sell_price` — none appears anywhere in
   `routes/photo_takeoff.py`. The editor's own footer still reads *"ft²,
   counts — the photo lane only. No price, no priced line, no money.
   Protected estimates refuse (423)."* PASS

## SCOPE HELD
Gables and dormer cheeks in PhotoTakeoffEditor only. A pin asserts the
ONLY receipt keys in the whole route are `receipt`, `cheek_receipt`,
`gable_receipts`, `dormer_receipts` and that nothing above the gable
helper coaches anything — **no coach was built for wall-height refusals,
blueprint faces or openings.**

## NOT AUTHORISED, NOT TOUCHED
Rail split · phase 2 trim · fixture rename · quote wiring · rectify.

## ONE THING SEEN AND NOT TOUCHED (for Howard's ruling)
The refused gable's mark row shows **"0 ft²"** on the right-hand side —
that number is the DRAWN POLYGON's own area (a flat triangle really does
enclose nothing), not a quantity, and it sits on the same row as *"REFUSED,
never a 0"*. It reads as a contradiction. Fixing it is a display change
this send did not authorise ("Nothing else"), so it is reported and left
alone.
