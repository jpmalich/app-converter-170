# SEND-104 REPORT — REACHABLE-PLANE RULINGS: WHAT SHIPPED, WHAT THE DRAWINGS SHOW
2026-08-22 · pins: `tests/test_reachable_2026_08_22_send104.py` (4) +
`tests/test_lines_door_census_2026_08_22_send104.py` (2) + one NAMED pin update
in `test_tape_2026_08_22_send98.py`. All live observations on disposable clones,
deleted after. **No real estimate touched. EST-886440 untouched.**

---

## ITEM 1 — PER FACE, BOTH HOUSES: DOES A TAPE RESOLVE THE SCALE OR ONLY THE HEIGHT

Read from each face's own drawing (datum_lines census, both houses' latest runs):

| house | face | TOF located | plate located | a TOF→soffit tape resolves |
|---|---|---|---|---|
| Letrick | front (p1) | YES y=30.9 | YES y=20.4 | **SCALE + HEIGHT** (TOF drop below FF 1.06 ft) |
| Letrick | rear (p1) | YES y=76.3 | YES y=65.9 | **SCALE + HEIGHT** |
| Letrick | left (p2) | YES y=31.8 | YES y=21.3 | **SCALE + HEIGHT** (drop 0.85 ft) |
| Letrick | right (p2) | YES y=71.8 | YES y=61.5 | **SCALE + HEIGHT** (drop 0.76 ft) |
| Boni | front (p1) | YES y=34.2 | YES (3 plates: 13.9/23.1/26.5) | **SCALE + HEIGHT** |
| Boni | rear (p1) | YES y=77.7 | YES (3 plates: 57.7/66.8/70.0) | **SCALE + HEIGHT** |
| Boni | left (p2) | YES y=33.8 | YES (3 plates: 13.9/23.1/26.5) | **SCALE + HEIGHT** |
| Boni | right (p2) | YES y=75.8 | YES (2 plates: 55.7/64.9) | **SCALE + HEIGHT** |

**The honest surprise: the four Boni faces DO all answer the same on datum
location** — TOF and at least one plate are drawn on every face of both houses
(Boni right binds FOUNDATION→plate directly, exactly as the send predicted; it
lacks only FIRST FLOOR, which the reachable tape does not need). Where they
differ is the UPPER datum: Boni's faces carry MULTIPLE plate lines (two-story;
2–3 per face). The calibration takes the TOPMOST TOP OF PLATE — the same
band-top convention DP-1 uses — and the chosen pair is printed on the face
(`scale_source` names both y's). The height-only refusal path exists, is
stated ("a width block never lifts on a height tape"), and is pinned at the
helper level (`_reachable_scale`: missing datum → named refusal) — **no live
face on either house exercises it**, a fact, not a gap.

## ITEM 2 — IS THE SOFFIT THE SAME LINE AS TOP OF PLATE?

**Neither house's drawings carry a soffit line at all.** Every elevation band
on all eight faces was searched for SOFFIT text: NONE — no soffit datum is
labelled anywhere. So there is no drawn pair of lines to measure a
plate-to-soffit offset from; the question "how far apart in feet" has no
drawn answer on these prints.

What ships, per the ruling (decided nothing): the card wording stays exactly
as ruled ("Measure from the top of the foundation to the bottom of the
soffit."); the CALIBRATION spans TOF → topmost TOP OF PLATE (the datums the
drawing actually carries); and the difference is RECORDED on every taped
face, verbatim in its `scale_source`:
> `no soffit line is drawn on this face — the TOP OF PLATE closure is the
> upper datum, difference recorded, not decided (SEND-104 item 2)`

The open risk, named and visible, not resolved here: if the physical soffit
overhangs below/above the plate line, a TOF→soffit pull is longer than the
drawn TOF→plate gap by that offset, and every width scaled from it inherits
the ratio. The record carries the assumption on its face; the ruling on
whether to name the plate on the card, or accept the offset, stays with
Howard.

## ITEM 3 — A TAPED SCALE STAYS ON ITS OWN FACE (pinned)

`test_live_taped_scale_stays_on_its_own_face`: with the rear taped, the other
three faces' proposals all carry `scale_source`/`height_source` starting
`DP-1 FALLBACK`, no TAPED wording anywhere on them, tier untouched. The tape
seats per `face_id` and the spec is built per face — locality is structural
AND pinned. Every face now STATES its band and scale — TAPED or DP-1
FALLBACK, never both, never silently (`proposed_from.height_source` /
`scale_source` on every proposal, defaulted explicitly).

## ITEM 4 — WHAT THE LETRICK REAR TAPE WILL SETTLE

Reproduced live on a disposable clone (wall-outline width, rear body):

- Pre-tape the contest is exactly as named: **60.15 ft** under the larger
  rail (9'-11" ≈ 9.92 ft over the FF→plate gap of 243.6 px) vs **55.14 ft**
  under the smaller (9'-1⅛"). One drawn span, two scales.
- The taped scale divides the tape over the drawn TOF→plate gap (269.6 px).
  The mapping is linear and single-valued: **rear width = 5.481 ft of width
  per taped foot.**
- **The 54' check (a check, never a target):** the rear width lands exactly
  54.00 ft if the TOF→soffit tape reads **9.852 ft = 9'-10.2"**.
- The two contestants, translated onto the tape's own plane (the drawn
  gap ratio 269.6/243.6 = 1.106): the 9'-11" rail predicts a tape of
  ≈10.97 ft (width 60.15, residual **+6.15 ft over 54'**); the 9'-1⅛" rail
  predicts ≈10.06 ft (width 55.14, residual **+1.14 ft**).
- With the TEST FIGURE 9'-6" (NOT Howard's measurement, entered only on the
  clone): width lands **52.07 ft**, residual **−1.93 ft** against 54'.

So the tape settles it cleanly: one pull, one width, and the residual against
the sealed 54' falls straight out. If the real tape reads near 9'-10", the
whole chain lands on 54' and the face contested since send 47 is confirmed.
If it reads near either rail's prediction, 54' does NOT hold on this face —
the more important result, and nothing gets adjusted either way. Both
contestants stay in the record regardless (pinned; the governs statement
names the contest and keeps it).

## WHAT SHIPPED (all pinned, live on the clone)
- Card wording exactly as ruled (every card, pinned string-equal).
- TOF→soffit tape governs the SIDED HEIGHT directly — no conversion into
  DP-1's band (`height_source`: "TAPED (top of foundation → bottom of
  soffit) — the SIDED height directly, no conversion into DP-1's band").
- Taped scale governs that face's widths where both datums exist
  (`scale_y` re-seated on the drawn TOF→plate pair; chases and body derive
  under it); where they do not, the tape resolves the height only, the width
  blocks stand, and the statement says so.
- TAPED vs DP-1 FALLBACK stated on every face, never both, never silently.
- Both original contestants stay in the record (`taped_over`, "Kept in the
  record:", prior_read on the tape doc).
- Tape available on every face; where it contradicts a resolved read it
  governs and says so (send98 pin updated — NAMED below — and re-pinned).

**NAMED PIN UPDATE (SEND-99 condition 1's one exception):**
`test_live_band_matched_tape_governs_the_contested_rear` (send98 file)
asserted a TOF→soffit tape on LEFT is RECORDED only — statement "bands
DIFFER", governs False, left stays `derived_chain`. The SEND-104
reachable-plane ruling made that assertion stale: the same tape now GOVERNS
(height + scale; both datums drawn on Letrick left). The pin now asserts the
ruled behavior — governs True, "height AND scale", prior derived_chain read
kept and its contradiction stated.

## STILL-OWED LEDGER
- **Silent-strip sweep: DONE, sealed by census.** Every `estimates` write
  carrying `lines` in routes/ must re-run the overlay law or sit on a named,
  reason-checked register (`test_lines_door_census_2026_08_22_send104.py`).
  Census found the three known members cured (estimates PUT/PATCH — SEND-100;
  hover rebuild — SEND-79; notes — 2026-07-31 merge layer) and two
  registered non-members: `demo.py` (provision-time seed of a
  freshly-created demo estimate — no zones can exist yet) and `lp_admin.py`
  (in-place tier reprice of stored rows, nothing rebuilt or merged). A NEW
  lines door fails the suite until it re-runs the law or registers with a
  reason.
- **The three Boni-left options (relayed at last, from the send96 record):**
  (a) accept the far member x=34.94 as the second corner when it is the ONLY
  full spanner beyond the fence-side corner — names its basis, weakest tier;
  (b) let a drawn human zone stand as the cure (already possible today);
  (c) leave it refusing. Nothing wired without the ruling.
- **Chase pricing (authorized): WIRED AND PINNED this send.** A clean chase
  row prices at the HOST siding line's own rates, source named verbatim on
  the row (`…; priced at the host siding line's rates (Charter Oak Standard
  color Dutch Lap 4.5" .046: $151.31/SQ mat, $0/SQ lab) — the chase is sided
  in the face's own material`). A contested chase still refuses (Ruling L
  untouched); no host line → the row stays unpriced with the reason printed;
  rates are never invented (4 pins,
  `test_chase_pricing_2026_08_22_send104.py`). **Letrick's dollars, observed
  on a disposable clone (deleted after):**
  - Baseline, no chase confirmed: **$13,171.75**
  - Sides confirmed — the ≈0.99 SQ recovery is worth **+$149.80**
    (0.49 + 0.50 SQ at $151.31/SQ mat, $0 lab): **$13,321.55**
  - Rear confirmed pre-tape: REFUSED, $0, gate blocking — total unchanged
  - Rear taped (TEST FIGURE 9'-6" TOF→soffit, not Howard's measurement) and
    re-confirmed: 0.88 SQ, **+$133.15**, gate clear: **$13,454.70**
  - All-in recovery on the clone: **+$282.95** (rear portion moves with the
    real tape; the sides' $149.80 stands on its own confirms)
- **Ruling V conversion: not started** (verified-height bases, refuse where
  unverified, no story defaults, no `_ai_story_count or 1`, no hardcoded 9').

Standing rules held: no cross-drawing evidence (the taped scale cannot leave
its face — pinned), no estimate influences another, no job names in code,
model heights hypothesis-only. EST-886440 untouched. 423 on every derived
write. Purity pin holds.
