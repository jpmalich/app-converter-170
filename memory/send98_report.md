# SEND-98 REPORT — REAR TAPE ENTRY + CARD PRINTING (the four required items)
2026-08-22 · pins: `tests/test_tape_2026_08_22_send98.py` (10) + `tests/test_chase_confirm_2026_08_22_send100.py` (4)
All figures below were OBSERVED on a **disposable clone** of Letrick's blueprint run
(estimate `ZZ TEST_send100 LETRICK CLONE`, seeded with a copy of the real takeoff lines)
and a disposable clone of Boni's run. **Nothing was written to any real estimate.**
The clone and its polygons/tapes/lines are deleted after this report and the browser
verification.

---

## FIRST — A BUG THIS REPORT CAUGHT (SEND-100 finding, fixed and pinned)

Producing item 1 required confirming the proposed chase zones through the same
HTTP path the browser uses. That path was BROKEN in a way no existing pin saw:

- `resolve_face_from_bands` (the SEND-66 centroid-band resolver) knew the
  `gable:` prefix but was never taught `chase:`. Confirming a proposed
  `chase:back` zone **stripped the prefix** — the zone came back as a plain
  `back` body zone and merged into body-class math. No chase quote row, no
  Ruling L block, and the contested rear chase area **priced silently** into
  the siding line.
- Second half: the confirm upsert dropped the proposal's top-level
  `tier`/`basis`, so even a surviving chase zone could never detect its
  contest (`contested_pick_larger` was only in `confirmed_from`, which the
  quote builder does not read).

Both fixed (`routes/pdf_overlay.py`): a surface prefix survives band
resolution (only the host face resolves), and confirmation upgrades AUTHORITY,
not EVIDENCE — the proposal's tier/basis stay on the zone. Pinned end-to-end
over HTTP in `test_chase_confirm_2026_08_22_send100.py` (propose → confirm →
quote row REFUSES + gate fires → tape → re-confirm → row prices, gate clears).
The SEND-96 pins had exercised `apply_overlay_to_takeoff` as a pure function
with `chase:*` ids passed directly — the laundering happened one step earlier,
on the write.

---

## ITEM 1 — LETRICK'S QUOTE AFTER A TAPE IS ENTERED

**The tape value entered was 9'-6" (9.5 ft). THIS IS A TEST FIGURE chosen
because it agrees with NEITHER printed contestant — it is NOT Howard's
measurement and it was entered only on the disposable clone.**

### Before the tape (chase zones confirmed, rear still contested)
| row | qty | reads |
|---|---|---|
| Chimney Chase — rear | **REFUSED** (qty null, `not_derivable`) | note: `REFUSED — contested scale. Basis: chimney chase — its own bindable surface (interrupted-wall ruling SEND-89/94): drawn width 5.5 ft; drawn ink rises 10.2 ft above the plate closure — above-plate area carried (previously dropped); this face's scale stays CONTESTED…` · reason: `chase sits on a CONTESTED-scale face — an unverifiable quantity must not quietly price; the total is INCOMPLETE until the contest resolves (Ruling L)` |
| Chimney Chase — left | 0.49 SQ (48.67 ft²) | `Basis: … drawn depth 2.55 ft; drawn ink rises 9.02 ft above the plate closure — above-plate area carried` |
| Chimney Chase — right | 0.50 SQ (50.19 ft²) | `Basis: … drawn depth 2.59 ft; drawn ink rises 9.16 ft above the plate closure — above-plate area carried` |

Every chase row also prints: `carries 4 corner verticals running the chase
height — UNPRICED, corner count unchanged`.

- **Gate:** `chase_refused` / `chase_contested_scale`, tier QUOTE, **BLOCKING**
  — fires on the readiness registry. Refused-row count 1 → the quote banner
  reads INCOMPLETE.
- **Sides note:** the SEND-96 figures were ≈43.8 / 44.6 ft² **wall-band only**;
  today's partition carries the above-plate chase ink (SEND-94), so the sides
  now read 48.67 / 50.19 ft². The rear proposal area pre-tape was 116.99 ft²
  at the contested-larger 9.92 ft — refused, never priced.

### After the tape (9'-6" FIRST FLOOR → TOP OF PLATE, re-proposed, rear re-confirmed)
| row | qty | reads |
|---|---|---|
| Chimney Chase — rear | **1.07 SQ (107.30 ft²)** | `Basis: chimney chase — its own bindable surface (interrupted-wall ruling SEND-89/94): drawn width 5.27 ft; drawn ink rises 9.77 ft above the plate closure — above-plate area carried` |
| Chimney Chase — left | 0.49 SQ | unchanged |
| Chimney Chase — right | 0.50 SQ | unchanged |

- **Does the gate clear? YES** — `chase_contested_scale` is gone from the
  registry, refused-row count 0, the INCOMPLETE banner drops.
- The estimate's OTHER pre-existing blockers stand untouched (labor-pending
  rows like "clean up/haul away", unpriced "Fascia/rake or frieze" — 11 open
  readiness items before and after). The tape clears the CHASE block only.
- **The rear body proposal** now carries tier `taped_human`, height 9.5 ft,
  basis: `TAPED HUMAN MEASUREMENT — 9'-6" = 9.5 ft, taped the FIRST FLOOR line
  → the TOP OF PLATE line; GOVERNS (top of the evidence ladder), never
  absorbed into the read. Kept in the record: CONTESTED height — rails 9'-11*
  vs 9-1%; proposed from the LARGER (9.92 ft)…`

### The total, before and after
**$13,171.75 → $13,171.75 — unchanged.** Honest reason: chase rows are
created with mat $0 / lab $0 (a quantity surface, not yet priced — same
treatment as other unpriced rows, which the readiness registry flags). The
tape moves the QUANTITY record (rear chase 0 → 1.07 SQ) and clears the gate;
dollars move only when Howard prices the chase rows.

### Does the ≈+0.9 SQ recovery land, and on what confirm?
YES — the two SIDE chases land **0.49 + 0.50 = 0.99 SQ** on confirming those
two zones (tape not required; their scale chain was never contested). The
REAR chase lands a further **1.07 SQ** only on the post-tape confirm.
Proposals alone move nothing (SEND-48 law) — every landing required a human
confirm, and the propose response warned first: `the chase partition newly
carries 102.82 ft² of above-plate chase area on this estimate — nothing moves
until a human confirms a chase zone…`

---

## ITEM 2 — WHAT EACH BONI CARD ASKS FOR (verbatim, from the clone's cards)

All four cards carry the estimate identifier and the face name in the card
header (print format: `{estimate_number or estimate_id} — {FACE} wall`).
The four refusals are all DIFFERENT and each card's "why" is the face's own
named refusal, not a generic line:

**FRONT (p1 — conflicting heights)**
- Why: `Two different wall heights found on this elevation (8'-1" and 29'-1"). This usually means the front and rear plate heights are different (common with cut-short side gables or stepped foundations). Please verify or draw a zone.`
- Card sentence: `The print shows two conflicting wall heights on this elevation. Tape plate-to-floor ONCE at this wall — the tape decides which figure is real.`
- Points: `put the tape on the top of the foundation, read at the bottom of the soffit`

**REAR (p1 — undimensioned band)**
- Why: `wall height not established from rear elevation — gap SECOND_FLOOR@66.0 → TOP_OF_PLATE@66.8 UNDIMENSIONED — area not derivable`
- Card sentence: `One band of this wall is printed with NO dimension. Tape the wall from TOP OF PLATE down to FIRST FLOOR in one pull — the missing band is inside that pull.`
- Points: same reachable pair as above.

**LEFT (p2 — conflicting heights)**
- Why: `Two different wall heights found on this elevation (6'-0" and 9'-1")…`
- Card sentence: same conflicting-heights instruction as FRONT (same refusal
  KIND ⇒ same instruction template; the figures and the page differ).

**RIGHT (p2 — no datum)**
- Why: `wall height not established from right elevation — no FIRST FLOOR datum located — area not derivable`
- Card sentence: `The drawing gives no usable floor line on this face. Tape the full wall height — grade to top of wall — and write the figure on this card.`

**Letrick prints one card** (rear): why: `the print carries two figures
(9'-11* vs 9-1%) and the app may not choose between them` · sentence: `Tape
ONE height on this wall: hook at the TOP OF PLATE line, read at the FIRST
FLOOR line. The tape decides between 9'-11* vs 9-1%.`

Honest note: FRONT and LEFT share one sentence because they share one refusal
KIND (two conflicting printed heights) — the refusal text on each card carries
the face's own figures. Boni's four cards are 3 distinct instructions + 4
distinct refusals. (A clone created raw over the API has an empty
`estimate_number`; the print falls back to the estimate id. Howard's real
estimates all carry an EST-number, which is what prints.)

---

## ITEM 3 — REFERENCE PLANE PER CARD vs THE DERIVATION BAND

| face | plane the card asks for | derivation band | match? |
|---|---|---|---|
| Boni front | top of foundation → bottom of soffit | FIRST FLOOR → topmost TOP OF PLATE | **NO** |
| Boni rear | top of foundation → bottom of soffit | FIRST FLOOR → topmost TOP OF PLATE | **NO** |
| Boni left | top of foundation → bottom of soffit | FIRST FLOOR → topmost TOP OF PLATE | **NO** |
| Boni right | top of foundation → bottom of soffit | FIRST FLOOR → topmost TOP OF PLATE | **NO** |
| Letrick rear | top of foundation → bottom of soffit | FIRST FLOOR → topmost TOP OF PLATE | **NO** |

Every card states this itself: `band: FIRST FLOOR → TOP OF PLATE (the
derivation's band — not reachable from outside the house)` and carries
`plane_matches_band: false` — **never assumed**.

**NO CONVERSION EXISTS, and none is silently made — that is the design, and
it is the finding.** A tape entered on the reachable plane (foundation →
soffit) is RECORDED against its own named plane and does NOT govern the
derivation: the response and the card both print `…the bands DIFFER and are
never assumed equal (no silent conversion)`. That is Ruling KK's two-planes
hazard held at the HUMAN input.

How a governing pull happens: every card prints the alternative — `if the
FIRST FLOOR line is reachable (inside / garage), tape the FIRST FLOOR line →
the TOP OF PLATE line — that pull GOVERNS the derivation directly.` The
entry UI requires naming both reference points on every tape (dropdowns,
no default-blind submit).

**Where this is visible to Howard:** on the card (band line + alternative),
on the entry (the two reference dropdowns), on the response statement, and on
the face after commit (`TAPED: … (ref_from → ref_to) — recorded on its own
plane (bands differ)` vs `— GOVERNS`).

**What remains open (named, not hidden):** a foundation→soffit tape today is
a RECORDED figure that governs nothing. If Howard wants that reachable pull to
drive quantities, the conversion (soffit/foundation offsets from the drawing,
or a ruling that accepts the outside pull as the wall height) needs its own
ruling — nothing was invented here.

---

## ITEM 4 — A TAPE THAT AGREES WITH NEITHER CONTESTANT

Letrick rear contests `9'-11*` against `9-1%` (the print's own strings).
Entered: **9'-6" — matches neither.**

- **Does the tape GOVERN? YES.** The rear proposes at tier `taped_human`,
  9.5 ft, top of the ladder. It did not have to pick a side.
- **Are BOTH CONTESTANTS still in the record? YES — in three places.** The
  stored tape carries `prior_read` (tier `contested_pick_larger`, 9.92 ft,
  rails `9'-11*` vs `9-1%`, full basis); the proposal basis prints `…Kept in
  the record: CONTESTED height — rails 9'-11* vs 9-1%…`; the card still shows
  the original refusal with both figures.
- **What the face says on screen:** `TAPED: 9'-6" = 9.5 ft (first_floor_line
  → top_of_plate_line) — GOVERNS`, above the untouched refusal line naming
  both contestants.
- **What the quote row says:** `Chimney Chase — rear · 1.07 SQ` with the
  chase basis; the body proposal basis names the tape AND the kept contest.
- **Is the disagreement REPORTED, or overwritten quietly? REPORTED**, in the
  propose response verbatim:
  > `the tape governs this face; it contradicts the prior
  > contested_pick_larger read of 9.92 ft — the tape governs, the read is
  > kept, nothing moved silently; the contest (9'-11* vs 9-1%) is settled by
  > the tape — both contestants kept in the record; if the tape agrees with
  > NEITHER printed figure it still governs and the disagreement stays
  > visible here`

Also pinned this send (coverage gap the SEND-99 conditions named): a
band-matched tape on an ALREADY-RESOLVED face (left, `derived_chain`) governs
and says so — `it contradicts the prior derived_chain read of X ft — the tape
governs, the read is kept, nothing moved silently`
(`test_live_band_matched_tape_governs_an_already_resolved_face`).

---

## WHAT THE TAPE PINS COVER (SEND-99's question, answered directly)
- tape agreeing with NEITHER contestant: **pinned** (9'-6" vs 9'-11/9'-1⅛)
- tape on an already-resolved face governs and says so: **pinned this send**
  (was a gap — the earlier left-face pin used a differing plane)
- misparse rejected, never guessed: **pinned** (parser + live HTTP 422,
  Ruling HH inch ≥ 12, `9-13` → `REJECTED, never guessed: '9-13' carries an
  inch component of 12 or more — not feet-inches (Ruling HH)`)
- reference-plane recording (item 2): **pinned** (`plane_matches_band`,
  `bands DIFFER` statement, card points vs band, never converted)

Standing rules held: no cross-drawing evidence, no estimate influences
another, no job names in code, model heights hypothesis-only for quantities.
EST-886440 untouched. 423 on every derived write. Purity pin holds.
