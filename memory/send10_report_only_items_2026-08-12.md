# SEND-10 REPORT-ONLY ITEMS

Two reports Howard ordered on 2026-08-12 send-10. No build ordered here — cost estimates and available-source logging for later prioritisation.

## A. OCR-COVERAGE WEIGHTING on FABRICATED verdicts

**Class**: this OCR (Tesseract-driven `_ocr_runs`) cannot read stacked fraction glyphs at all (½, ¼, ⅛ etc.). A verdict of FABRICATED trusts that "OCR absence = drawing absence." That trust is defensible when OCR coverage on the page is HIGH — a page whose OCR yielded 400 legible runs and none contain the quote is strong evidence of absence. It is weak when coverage is poor (a photo of a raster stamp, a page rotated at odd angles, a busy detail sheet).

**Proposal**: weigh OCR coverage per page BEFORE calling a quote fabricated.

- **How**: for each page under the locator, compute `ocr_coverage_score` = `len(runs)` × `Σ len(run.norm)` (approximate character count captured). A quote norm not present is FABRICATED only when `coverage_score >= FABRICATED_MIN` (initial cutoff: tune with a handful of pages — e.g. 200 runs of ≥ 3 chars is plentiful; < 40 is thin).
- **Below the cutoff**: the verdict downgrades to UNVERIFIED with reason `"OCR coverage below threshold — absence not confirmable"`. The value still nulls from money-fed raw, but the card shows it under `dim_unverified` (kept for review) rather than under `dim_fabricated` (killed).
- **Where**: `_null_unverified_quotes` decides the split; add a `_page_ocr_score` map fed by `_ocr_locate_evidence` (already runs the OCR).

**Cost**: modest. One field on the miss record (`_page_ocr_score`), one branch in the classifier, one pin. **~1 hour of work, ~4 pins.** No architectural change.

**Risk**: the cutoff itself is a tuning knob. Making it a target would be the class Howard rules against; keeping it as a coarse threshold with an accompanying `_page_ocr_score` field on every miss (so anyone can see the score that classified) preserves the audit. Cutoff lives with a `# tuning: this is a threshold, not a target` comment.

**Not building now** (Howard's queue). Recording for post-P0-chips prioritisation.

---

## B. FLOOR PLAN AS AN AVAILABLE SOURCE for opening positions and attribution

**Class**: the Boni first floor plan (sheet 6) prints information Howard already relied on to confirm the read:

1. **Opening x-positions**: the bottom dimension run reads `3'-9", 8'-10", 8'-10", 3'-2 1/2", 6'-6 1/2", 11'-5 1/2", 6'-6 1/2"` — spacings between window marks.
2. **Opening wall attribution**: window/door marks sit visibly on their walls. Top wall carries `SH 3-0_5-0, SH 3-0_5-0, SH 3-0_4-0`. Front wall carries `SH 3-0_5-6` marks. Garage doors sit on the SIDE wall (which is how the send-10 item 2 arithmetic check would have caught them).

Both are printed on the DRAWING, not in the READ. The pipeline currently ignores them because the AI extraction is prompted for wall-tag attribution ("elevation": "front" | "back" | "left" | "right") without pointing at the floor-plan glyph positions.

**Howard's verdict**: "I am NOT ordering a read feature for this. Log it as a NAMED AVAILABLE SOURCE. It matters for the material zone layer: if zones can start from printed positions and printed attribution, I am NUDGING rather than drawing from scratch, and that is the difference between a tool I use and a tool I tolerate."

**Log**: the material zone layer (send-8 item 3) is buildable in two ways:

- **From scratch**: user draws all polygons on the elevation PDF pages, no priors.
- **From printed priors**: the floor plan reader (a NEW instrument, not the current AI blueprint reader) extracts the printed dim-chain positions + mark-on-wall attribution, and seeds the zone layer with them. The user then nudges rather than draws.

**When to build the printed-priors instrument**: AFTER the material zone layer ships from-scratch first. Every job the user runs seeds a dataset for calibrating the printed-priors reader. Do NOT build it into the ai_blueprint prompt (Howard's held rule: the read regresses under more structure).

**Cost**: substantial and NOT budgeted here. Requires a floor-plan-region locator (already partially there in `_sheets_by_page` typing), plus a dimension-chain parser (bottom/top/side runs of dims), plus a mark-position extractor. **Guess: 2 weeks of focused work.**

**Not building now.** Registered here as the seed for the material zone layer's second version.

---

## Purity

All Boni evidence in these reports (58'-0", 39'-0", 9'-11 1/8", 9'-6", 16'6", 25 ft garage doors) is EVIDENCE FOR RULINGS. None becomes a constant, default, fallback or assertion target. Nothing applies to EST-886440. Integral-J stays ON.
