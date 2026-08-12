# FALSE-POSITIVE LOCATOR — MECHANISM (SEND-8 item 1)

**Ruled**: Howard 2026-08-12 send-8 item 1. A quote that locates must
be real. Report the mechanism before the fix.

## Howard's hypothesis (partly killed, partly confirmed)

**Hypothesis**: "The proximity rule shipped 8-9 was scoped to
schedule-table regions only. A dimension quote can still match
ANYWHERE on the page — so a real `9'-6"` printed somewhere else
(porch, step, footer) satisfies a garage-wall quote."

**Kill (for THIS specific quote)**: `9'-6"` does not exist ANYWHERE on
the Boni PDF. I searched every page's text layer (empty — the PDF is a
scan) AND ran OCR on page 1 for norms containing `96` — zero hits.
Zero hits for `911` either. **The AI hallucinated `9'-6" garage wall`
whole cloth.** Not a proximity failure — a fabrication.

**Confirm (for the class)**: The OCR locator's proximity gate is
absent even for schedule-scoped fields. `_ocr_match(runs, nq)` at
`routes/ai_blueprint.py:1333` accepts ANY OCR run whose normalised
text equals or contains the quote's norm — no feature-anchor
proximity, no radius. The FIRST match at any pixel position wins. If
`9'-6"` HAD been printed somewhere else on this sheet, the current
locator would have pinned it and the quote would have "verified".
Howard's class fix stands.

## The bigger cause on THIS quote (send-6 regression I introduced)

The send-6 SEND-6 read added two per-plane fields on `roof_planes`:
- `overhang_in`
- `wall_height_ft`

Both emit the evidence dict `{"v","page","from"}`.

**I did not add them to `_normalize_evidence`.** The function walks
walls, wall segments, porch dims, `eave_lf` / `rake_lf` on planes,
`gutter_runs`, and `corner_heights` — but not `overhang_in` /
`wall_height_ft`. Confirmed by inspecting the fresh Boni raw:

```
roof_planes["garage"].overhang_in:      {"v":12,   "page":11, "from":"1'-0\""}   ← STILL DICT (not normalized)
roof_planes["garage"].wall_height_ft:   {"v":9.5,  "page":1,  "from":"9'-6\" garage wall"}  ← STILL DICT (not normalized)
```

Both fields sit in the raw as evidence dicts. `_dim_evidence` does not
carry them. `_exact_locate_evidence` and `_ocr_locate_evidence` never
run on them. The `plane_rows` walker in the readback extracts the `v`
straight from the dict — the value flows to rendering with no
verification of any kind.

**This is a two-day hole** — a class of new fields I opened on send-6
that bypasses the entire evidence discipline. It also means the
readback rail's `wall_height_by_plane: garage=9.5 ft` fired with no
proof the quote exists on the PDF.

## Where the general locate stands

Ran the pdfium text search over every one of the 49 `_dim_evidence`
quotes on the fresh Boni read. **All 49 quotes returned zero
pdfium hits** — because the Boni PDF has no text layer (it is a
scan, `native_text` check exits early). This is expected for scans.
The OCR locator picks up the load for scans, but:

1. Not every AI evidence path is walked by the OCR locator either —
   only those routed into `_dim_evidence` via `_normalize_evidence`.
2. The OCR locator has no feature-proximity gate.
3. `_ocr_quote_misses` is recorded but does NOT null the value —
   the AI's `v` still flows to takeoff. A miss is a NAMED
   contradiction but not a refusal.

## What must be true after the fix (Howard's ruling, plainly)

- Every quote we call "verbatim from the print" is actually FOUND on
  the print.
- Every located match sits NEAR the feature it claims to dimension
  — not merely somewhere on the same page.
- A quote that cannot locate near its feature is REFUSED — the value
  drops to null. Evidence-or-null, as ruled 2026-08-08.
- The per-plane fields I added on send-6 enter the evidence pipeline
  like every other dim.
- Then we re-run the locator over every quote on this read and count
  the survivors. Howard asked for that number.

## Fix plan (next commit)

1. Extend `_normalize_evidence` to walk `overhang_in` and
   `wall_height_ft` per plane.
2. Add a feature-anchor proximity gate to `_ocr_locate_evidence`:
   - Derive feature-anchor tokens from the evidence PATH
     (`roof_planes.garage.wall_height_ft` → `["GARAGE"]`).
   - Only accept an OCR match whose bbox sits within a proximity
     radius of at least one feature-anchor run's bbox.
   - No feature-anchor bbox on the page ⇒ refuse the locate.
3. The same rule for `_exact_locate_evidence` (native text path).
4. An unlocated (or refused-locate) evidence quote → the value
   nulls; a `_dim_quote_unverified` list surfaces on the readback,
   loud, per path.
5. Re-run over the Boni raw, count.

Purity: 9'-11 1/8" (Howard corrected the record from 9'-11 7/8"),
9'-6" fabricated, four gable ends not six. All EVIDENCE. Nothing
becomes a target. Nothing applies to EST-886440. Integral-J stays ON.
