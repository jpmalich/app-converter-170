# SEND-100 — TAPE-ENTRY UI + CARD PRINTING, VERIFIED ON THE RENDERED SURFACE
2026-08-22 · Everything below was OBSERVED in the browser (Playwright against the
preview URL), on **disposable clones** — `ZZ TEST_send100 BONI CLONE` and
`ZZ TEST_send100 LETRICK CLONE` (blueprint runs cloned, run_ids renamed
TEST_send100-*). **No real estimate was written.** Clones deleted after this send.

## TAPE ENTRY — observed
- **The field**: sits on every refusing face's card inside the Material Zone
  Editor side panel ("HEIGHT CARDS — WHAT TO TAPE (4 REFUSING FACES)" on Boni).
  Before anything is typed it shows placeholder `feet-inches, e.g. 9'-11"`,
  two reference dropdowns defaulting `top of foundation → bottom of soffit`,
  and a CHECK button.
- **FEET-INCHES ACCEPTED** (all three forms typed into the front card):
  - `9-11` → `Parsed: 9'-11" = 9.9167 ft — commit?`
  - `9'-11"` → `Parsed: 9'-11" = 9.9167 ft — commit?`
  - `9' 11"` → `Parsed: 9'-11" = 9.9167 ft — commit?`
- **THE ECHO-BACK** appears before commit, in the form typed AND in feet
  (above), with COMMIT TAPE / Cancel buttons. The parse endpoint commits
  nothing (pinned).
- **A MISPARSE REJECTED** — typed `9-13` (inch component ≥ 12, Ruling HH's
  bound). The user sees, in red under the field:
  `'9-13' carries an inch component of 12 or more — not feet-inches (Ruling
  HH); rejected, never guessed`
- **THE FACE AFTER COMMIT** (Letrick rear, test figure 9'-6"):
  `TAPED: 9'-6" = 9.5 ft (first_floor_line → top_of_plate_line) — GOVERNS`
  — labelled as taped, the reference plane named on screen, and BOTH original
  contestants still visible directly above it in the card's refusal line:
  `the print carries two figures (9'-11* vs 9-1%) and the app may not choose
  between them`.
- **THE QUOTE ROW after the tape clears the chase block**: the INCOMPLETE
  banner is GONE (`quote-incomplete-banner` absent), the chase gate is clear,
  and the customer quote document renders under VINYL SIDING:
  `Chimney Chase — left · 0.49 SQ / Chimney Chase — right · 0.5 SQ /
  Chimney Chase — rear · 1.07 SQ`. The PRINT-BLOCKED checklist still lists
  the estimate's PRE-EXISTING unrelated blockers (labor-pending rows,
  unpriced Fascia/rake) — the tape clears the chase block only.

## CARD PRINTING — observed (the popup sheet as it prints)
- Boni's four cards print on ONE page (each card `page-break-inside:avoid`);
  Letrick prints one. Screenshot of the sheet taken from the print popup.
- EVERY card carries the estimate identifier and face:
  `EST-TEST98 — REAR wall` style header (`{estimate_number || estimate_id} —
  {FACE} wall`). Note: an estimate created raw over the API has an empty
  estimate_number and the sheet falls back to the estimate id; every real
  estimate carries an EST-number.
- Each card prints: **Why the app could not read it** (the face's own named
  refusal — all four of Boni's differ), **What to tape**, **Between** (the two
  reference points), **Note** (the governing FIRST FLOOR → TOP OF PLATE
  alternative), and a ruled write-line: *Write the figure (feet-inches):*

## THE REFERENCE PLANE (the one thing most likely to be wrong)
The actual sentence on the card:
`Between: put the tape on the top of the foundation, read at the bottom of
the soffit` — a person at the house CAN put a tape on that. The card also
names the derivation band and says it is NOT reachable, and the note gives
the reachable-case pull that GOVERNS. A foundation→soffit tape is recorded
against its own plane and never silently converted (full analysis in
`send98_report.md` item 3).

## WHAT THE VERIFICATION CAUGHT (both fixed, pinned, suite re-stamped)
1. **Chase confirm laundering** — confirming a proposed `chase:*` zone
   stripped the prefix (`resolve_face_from_bands` knew `gable:` only) and
   dropped the proposal's tier/basis: the contested rear chase merged into
   body math and priced silently. Fixed; pinned over HTTP
   (`test_chase_confirm_2026_08_22_send100.py`).
2. **Client save stripped chase rows** — the browser's catalog merge cannot
   re-materialize non-catalog rows, so every autosave/Customer-Quote save
   deleted the chase rows (and the Ruling L block with them) from the
   estimate. Fixed by construction (SEND-79's own principle): the estimate
   PUT/PATCH now re-runs the overlay law on every lines write — chase rows
   rebuild from the zones, never from the client. The frontend shows them
   read-only and deliberately never sends them. Pinned
   (`test_live_client_save_cannot_strip_chase_rows`).

## NOT CHECKED IN THE BROWSER (named, with reason)
- The pre-tape INCOMPLETE banner rendering: the clone had already accepted
  the test tape when the quote modal was first opened, so the banner's
  presence was verified by API state (refused row count 1 → 0) and by the
  existing SEND-96 UI test-agent pass (iteration_57), not re-screenshotted
  this send. Its ABSENCE post-tape was observed directly.
- The physical print dialog itself (headless browser): the popup DOCUMENT was
  screenshotted; the OS print dialog cannot render headless.
