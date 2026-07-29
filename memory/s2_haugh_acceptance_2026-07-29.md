# S2 ELEVATION-GEOMETRY READ — 261 HAUGH ACCEPTANCE RUN (2026-07-29)

Run: fresh live import `18ac182047fe4def9b2de2063277fa89` (S1 persisted
PDF at backend/uploads/hover_pdfs/, 2,106,063 bytes). S2 read: 8 drawn
view pages (FRONT … LEFT-FRONT), Claude Opus vision, 116s.
Provenance: HOVER-DIM (HOVER-READ ✓/⚠). REPORT ONLY — S3 unwired by test.

## FORMAT FIX SHIPPED (commit d98b89d)
Current Hover format titles drawn pages with bare compass tokens
(FRONT / FRONT-RIGHT / …), not "<label> Elevation" — first S2 attempt
read 0 pages. Dedicated exactly-one-token page locator added (the
compass/footprint page carries all four cardinal tokens → excluded);
legacy renderer kept as fallback. ID vocabulary widened so real printed
IDs (SGD/STC/BR) are never falsely flagged; region-label-in-openings
and facade-label-printed-nowhere are now named warnings.
Guard: 2026-07-29 02:54 UTC · 469bf90 · CLEAN · 1575 passed.

## HEADLINES
- 39/39 real openings placed at least once (W-101…W-432, D-1…D-4,
  SGD-1…3) — zero missed.
- 18'5" back corner read TWICE: BACK view near WR-13 and LEFT view near
  WR-16, both 18.42'.
- WR-20 width 29'3" (29.25) — the batten-input read — landed exactly.
- 35 corner-height callouts read total; per-facade HEIGHT callouts are
  NOT printed on these drawn pages (only 2 opening-height-like reads:
  WR-1 5'8", WR-8 2'8") — corner dims are the vertical truth on this
  format.
- 24 INVENTED opening IDs (printed nowhere in the report): W-42/43/44,
  W-91, W-129/130, W-201/202/203, W-303/304, W-320/329, W-410/411/424,
  SG2-1/SG2-3, NG-1/3/4 — all on oblique views. 1 invented facade label
  (WR-30 on RIGHT-BACK, reading 13'4").
- Width disagreements: WR-2 (FRONT 9'2" vs FRONT-RIGHT 14'3"),
  STC-6 (BACK-LEFT 20'8" vs LEFT 26'8" — tens-digit misread).
- 22 openings drawn on 2–3 different walls across views (oblique pages
  re-place the same window on the adjacent facade).
- FIVE BLOCK OPENINGS: Hover's own facade table prints STC-1 with 5
  openings; the vision read placed ZERO openings on STC-1 — doors landed
  on adjacent regions instead: D-1 (36×96 entry) on WR-1+WR-3+BR-3 ⚠,
  D-2 (192×96 garage) on WR-7 (single), D-3 on BR-3, D-4 on WR-10+WR-12 ⚠.

## PER-FACADE placements (unique real IDs) vs Hover printed counts
Matched (12): BR-1/2/4/5, STC-2..6, WR-4/5/6/8/9/13/16/19 …
Mismatched: WR-1 (2 printed vs 7 placed — oblique double-places),
WR-2 (4 vs 10), WR-3 (0 vs 4), WR-7 (4 vs 6), WR-10 (0 vs 2),
WR-11 (2 vs 0), WR-12 (0 vs 2), WR-14 (3 vs 5), WR-15 (1 vs 3),
WR-17 (1 vs 3), WR-18 (0 vs 1), WR-20 (2 vs 0), BR-3 (2 vs 3),
STC-1 (5 vs 0).

Raw JSON: /tmp/s2_report_18ac182047fe4def9b2de2063277fa89.json (also on
the run doc as `elevation_read`).

## 3 DEGREE — STOPPED
The second chat asset (hover_pro_measurements_21447034.pdf) is
**2692 Timberglen Drive East, Franklin Park PA** — NOT 3 Degree Rd.
Per Howard's order, no substitution. The 3 Degree Hover PDF must be
re-uploaded before the panel/batten formula columns can run.
