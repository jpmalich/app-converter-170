# SEND-90 REGISTER — RULING XX WIDTH CROSS-CHECK, WIRED
2026-08-21 · code: `routes/pdf_overlay.py` (`_xx_seat_verdict`, `_xx_width_cross_check`, `XX_CROSS_CHECK_REGISTER`, propose wiring) · pins: `tests/test_xx_crosscheck_2026_08_21_send90.py` (11)

## WHAT IT EXISTS FOR (Howard's words, in the register constant)
THIS WOULD HAVE CAUGHT THE MISSING CHIMNEY WITHOUT ANYONE CHECKING PRINTS.
Left read 32.60 and right read 29.65, three feet apart, on a house XX already
knew had equal depths. Nobody noticed until Howard looked at the drawings.

## AS BUILT
- **Seat:** the verdict is read on the run's FLOOR-PLAN sheets (`sheets_identified`,
  `useful_for == floor_plan`) — a depth is a plan-derived figure; elevation pages
  establish envelopes of their own and would seat the verdict on the wrong
  instrument. Plan sheets that disagree are FLAGGED INDETERMINATE naming each
  page — never resolved.
- **Compares WALL-ONLY, never silhouette:** the compared figures are the
  plate-terminated `wall_corners` span in feet; the silhouette (`x_span`,
  includes projections) rides alongside explicitly marked "NOT the compared
  figures". This survives SEND-89's coming side-body reversion (31.94/32.24 →
  29.4/29.65) without the check's meaning shifting.
- **A reported difference, not a boolean:** `difference_ft` magnitude + plain
  statement ("left 29.4, right 29.65 — differ by 0.25 ft"). No threshold, no
  agree/disagree bit, no loud rail — pinned that a 3 ft gap reports in the same
  STATE. If Howard wants a rail above some size, that is his threshold, in a send.
- **Distinguishable silences:** `SILENT_INDETERMINATE` (attribution unresolved —
  "NOT because the sides agree") vs `REPORTED` vs `SILENT_NO_FIGURE` (verdict
  EQUAL but a side has no wall-only figure, side + reason named) vs
  `NOT_COMPARED` (MATERIAL — equality never claimed).
- The verdict also rides every proposal at `proposed_from.attribution`
  (status/why/seat_pages — never a value).

## WHAT IT SAYS TODAY (live, both houses)
- **LETRICK:** verdict IMMATERIAL (equal 30'-0" side depths on every floor-plan
  sheet, pages 5, 7) → REPORTED: "wall-only widths: left 29.4 ft, right 29.65 ft —
  differ by 0.25 ft (silhouettes: 31.94 / 32.24 — differ by 0.3 ft; NOT the
  compared figures)". Small, agreeing — turned on while it agrees, so a future
  disagreement is a signal, not a pre-existing condition.
- **BONI:** verdict INDETERMINATE — floor-plan sheets disagree, flagged never
  resolved: p4 INDETERMINATE (the exact positional tie ['5′-10°','30-2'] —
  segment-vs-total needs its ruling); p6 MATERIAL; p7 MATERIAL → check is
  SILENT_INDETERMINATE, and the payload says the silence is NOT agreement.
