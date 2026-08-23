# SEND-111 REPORT — RULING EXECUTED: RESIDUAL REGISTERED · REFUSAL LAW WIDENED · FIVE-SITE INVENTORY · QUOTE TAPE NUDGE · QR FIELD SHEET
2026-08-23 · Quantities only. Standing rules held: no cross-drawing evidence, no estimate
influences another, no job names in code, model heights hypothesis-only, EST-886440
PROTECTED, 423 on every derived write, purity pin holds.

---

# 1. THE X-RULER RULING — REGISTERED, TWO ENTRIES

Both entries live in `ocr_geometry.RULINGS_REGISTER["findings"]`, pinned by
`tests/test_send111_2026_08_23.py::test_register_carries_residual_and_noise_floor`:

1. **THE RESIDUAL, NAMED** — ~half a foot; both causes with both magnitudes (~half the
   per-face scale spread drawn into the prints; the sides' extra under-read an outer-stroke
   top fragment never drawn at one corner each, −0.43/−0.44 ft, reproduces on the second
   house); the candidate rule tested and REJECTED against controls (moved all eight kept
   boundaries by up to +10 ft). The app reads the drawing correctly; the drawing is
   internally inconsistent. Nothing in software is to chase this residual.
2. **THE 3.8% SPREAD AS A STANDING ACCURACY FLOOR** for every elevation-derived quantity —
   the same 9.08 ft drawn at 9.36 y-% (front) vs 9.73 y-% (left), the ink itself as
   evidence. ~4% bounds what line-work can ever achieve on any set. Any future proposal
   chasing a sub-4% elevation residual gets read against this floor FIRST.

# 2. THE REFUSAL LAW — WIDENED, NOT GUARDED (authorized fix)

Built exactly as ruled: the law's OWNERSHIP widened, no guard beside it.

- `routes/pdf_overlay.py` — `apply_refusal_law` / `reapply_refusal_law`: at the write, the
  refusal trio (`not_derivable`, `not_derivable_reason`, `not_derivable_code`) and the
  refused row's qty null are SERVER-OWNED, exactly as chase rows are. The stored trio
  re-seats verbatim; a client payload can neither CREATE a refusal, CLEAR one (dropping the
  row re-adds it — the law re-adds what it owns), nor ALTER one; a refused row's qty null is
  never laundered into a 0. The one thing that supersedes the null is an explicit HUMAN
  figure (Law A — qty_src human, qty present), and the trio stays riding as visible
  provenance even then.
- Called ONLY at the two CLIENT-SHAPED doors (`estimates.py` PUT L446-455 and PATCH
  L478-484, right after `reapply_overlay_law`). Rebuild doors never call it — a fresh
  derivation is the trio's birthplace and stays authoritative (pinned structurally: no
  rebuild path imports it).
- Chase rows pass through the refusal law untouched — the overlay law owns them entirely;
  no stale re-seat can fight a fresh chase recompute.
- Pins (9, all green): trio re-seat + null protection, human supersession, cannot-mint,
  cannot-clear-by-dropping, chase passthrough, both-doors structural pin, LIVE
  HTTP pin replaying the fifth member's exact move on a disposable estimate (trio came
  back, qty stayed null), and the field-sheet live pins.

## 2b. WHAT ELSE THE LAW DOES NOT OWN — the boundary, checked field by field (report only)

Census of all 29 line-field keys across 1,106 stored lines (all estimates), classified
against the law's ownership:

- **Law-owned at every lines write (overlay law)** — chase rows entirely; the zone
  supersede/restore set: `superseded_qty` (1), `superseded_qty_src` (1),
  `superseded_raw_qty` (1), `overlay_superseded` (1), `overlay_merged` (1),
  `overlay_polygon_count` (1), `overlay_sqft` (1).
- **Law-owned as of SEND-111 (refusal law)** — `not_derivable` (4), `not_derivable_reason`
  (4), `not_derivable_code` (0 stored yet — pre-code rows), the qty null on refused rows.
- **Human/client-owned by design** — `qty` (1106) when human, `qty_src` (22) human values,
  `mat`/`lab` (1106), `adders` (1064), `qty_pending` (40), identity fields
  `tab`/`section`/`name`/`unit` (catalog-bound), `item_id` (1086, id-binding).
- **THE EXPOSED CLASS — born in derivation, carried by the client, re-derived by NOTHING
  at a client-shaped write (10 fields):** `raw_qty` (167), `derived_qty` (4), `note` (554 —
  mixed human/derivation basis text), `viz` (35 — the bars=chips breakdown),
  `ami_part` (504), `lab_src` (402 — labor provenance), `pricing_source` (10),
  `cross_family_flag` (19), `_waste_included` (532), and `qty_src` when it carries a
  DERIVED provenance. These survive round-trips only because the client whitelist
  (`useEstimate.js` save shaper) sends them back — the same one-refactor-from-stripped
  posture the trio had before this send. That boundary was drawn at "what
  `apply_overlay_to_takeoff` recomputes" (SEND-79/100) and had never been checked against
  the full field list until now. REPORT ONLY — no further widening authorized.

# 3. THE FIVE UNSWEPT CLIENT-TRANSFORM SITES (report only, no fix)

| # | site | what it transforms | does anything downstream re-derive it? | would a strip be visible? |
|---|---|---|---|---|
| 1 | `useEstimate.js` catalog merge (L99–172) | REBUILDS every non-chase line from the catalog skeleton on every load, carrying stored fields by ENUMERATION (the fifth member's home; trio + qty null now also restored at the write) | Overlay set: yes (law). Trio/qty-null: yes as of SEND-111. The 10 exposed-class fields: NO | SILENT — the next autosave writes the loss back with no diff surface; exactly how the fifth member hid |
| 2 | `useEstimate.js` save shaper (L483–540) | FILTERS rows before every PUT (chase rows out — law rebuilds; qty-0 note-less non-human rows out — re-materialize by design) and WHITELISTS the fields on the wire | Chase: rebuilt by law. Dropped refused rows: re-added by the refusal law now. A whitelist omission: NO | SILENT — a field missing from the whitelist vanishes on the next save (this was the frontend half of the class, sealed 2026-07-31; the whitelist is the residual risk) |
| 3 | `useRecalcSoffitOnOverhang.js` (L45–133) | Rewrites soffit/porch-beam row qtys client-side and — notably — POST-PROCESSES FRESH REDERIVE OUTPUT (`baseLines = data.lines` → `applyPorchRows` → `update({lines})` → autosave PUT), sitting BETWEEN a rebuild door and the write | The law re-runs at the write for what it owns; the porch-row edits themselves: NO (they ARE the intended change) | Partially — the targeted qtys are visible on the rows; any field its row-spread failed to carry would strip silently. Never swept |
| 4 | `HoverImportButton.jsx` (L371–430) | Merges SOURCE-side lines + openings into the current estimate client-side before save (cross-family rules applied in the browser; Vero→Mezzo openings rebuilt field-by-field) | The write door re-runs both laws for what they own; the merged line set itself: NO | Partially — an import is an explicit user moment (rows appear), but field losses inside carried rows are silent. Never swept |
| 5 | `ISSHoverImportButton.jsx` | Same class as #4 on the ISS surface | Same as #4 | Same as #4. Never swept |

(`PdfOverlayEditor` zone writes are excluded — they go to the overlay law's own routes.)
An adjacent precedent exists for structural client-side enforcement — the optimistic-write
registry's AST detector — but building its analogue for this class is NOT authorized and
was not built. This inventory is the class's first naming.

# 4. QUOTE TAPE NUDGE — LANDED (order item 3)

`QuoteModal.jsx` — the Ruling-V tape coach (`TapeNudgeCard`, the SEND-109 component,
reused not duplicated) now renders directly under the INCOMPLETE banner on the quote
surface: the refused rows and the one-field tape entry sit right where the price is read.
`no-print` — it never reaches a homeowner page. Echo-before-commit doctrine unchanged
(parse → visible echo → commit through the real tape door → rederive → surface refreshes,
`onRederived` wired to the editor's reload). Renders ONLY when refusals exist.
data-testids: `quote-tape-nudge-wrap`, plus the card's existing `ruling-v-tape-nudge`,
`tape-nudge-face-select/-input/-check-btn/-commit-btn`. Verified live on the Casile
estimate (4 refused gutter rows): banner + nudge + face select + tape field render in the
open quote modal.

# 5. QR FIELD SHEET — LANDED (order item 4)

- Backend `GET /api/estimates/{id}/pdf-overlay/field-sheet?app_url=…`: one printable
  payload — estimate header, the HEIGHT CARDS (what to tape per refusing face — the
  SEND-96/98/104 card logic reused verbatim, wording as ruled), the refused rows, and QR
  PNGs (server-generated, data-URIs): OPEN THIS ESTIMATE (the tape nudge is right there on
  a phone) and the FROZEN MATERIAL LIST share link if one exists — never minted silently;
  absent, the sheet says why. A field sheet is instructions and links, never a quantity.
- Frontend: print route `/estimate/:id/field-sheet` (`FieldSheetPrint.jsx`, matching the
  elevation-sheet print-route convention) + a FIELD SHEET button on the estimate action
  row (`field-sheet-btn`). Each card carries a write-in line (FIGURE ___ ft / BY / DATE)
  when no tape is entered, and shows the entered tape when one is.
- Verified live: Casile field sheet renders both QRs (estimate link + frozen material
  list), 4 refused rows, note; endpoint pins green (QR data-URI, no-mint reason on a fresh
  estimate).

# 6. INCIDENT DURING THIS SEND — THE EXPOSED CLASS FIRED LIVE, ON MY OWN SESSION

Stated plainly: my browser smoke-test on the REAL Casile estimate (EST-523061) triggered
its quote-open autosave, and that autosave STRIPPED `cross_family_flag` from the 6
typed-dollar survivor rows — the exact guard Howard ruled ("flag it for me, do not
silently delete it"). The cross-family pin caught it on the very next full run, exactly as
designed. This is exposed-class field #8 from §2b demonstrating itself in the wild:
`cross_family_flag` appeared NOWHERE in `useEstimate.js` — neither the merge rebuild nor
the save whitelist carried it, so any human opening that estimate in a browser would have
done the same.
- FIXED (same class of fix as SEND-109's trio carry, not a law widening): the flag now
  rides the catalog merge and the save whitelist (`useEstimate.js`).
- REPAIRED: the 6 rows re-flagged to their exact prior state (restoration of stripped
  data, nothing new invented).
- VERIFIED E2E: re-drove the same quote-open autosave through the real browser path —
  all 6 flags and all 4 refusal trios survived the round-trip; the cross-family pin green.
The register's lesson holds: the pin proved what it swept. The other nine exposed-class
fields remain carried-but-unswept — inventoried in §2b, no further fix authorized.

---

## STAMP
(appended after the clean run)
