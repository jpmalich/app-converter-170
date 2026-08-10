# ROOF SECOND PASS — MECHANISM REPORT + RULING LANDED (2026-08-09 send 7)

Howard: "A conditional second AI read that OVERWRITES GEOMETRY ON THE
PRIMARY READ — the three things it names are the three that will not
hold still." Ordered: mechanism first, then register, ledger, and rule
what it may never touch.

## WHEN IT FIRES (`_roof_pass_needed`)
ONLY on garage evidence: a door with type_hint "garage" OR a wall whose
label contains "garage", AND (no garage roof plane in the primary read,
OR the garage plane is gable-blind: rake 0 and gable_ends 0). It sends
AT MOST 5 SHEETS (roof plan first, then elevations, then floor plans —
`picked[:5]`, a NAMED LIMIT). A house with no garage never fires it.

## WHAT IT OVERWRITES (as found — before the 8-9 fix)
1. **corner counts + LF — THE MAX-WINS RATCHET.** Accepted when the new
   walk satisfies out−in=4, lf>0, AND `oc >= old_oc`. A second read
   counting MORE corners always wins; one counting fewer never does.
   Two stochastic reads race and the higher one prints — the
   6→10→12→8→6 swing is exactly that signature, run by run.
2. **corner heights — THE DEFECT HOWARD HYPOTHESIZED, CONFIRMED.** The
   roof-pass schema asked for BARE NUMBERS (`[number | null]`) while
   the main schema asks for evidenced DIMs. The merge runs BEFORE
   evidence enforcement. So: quoted, located corner heights from the
   primary read were REPLACED by bare numbers — which the evidence
   gate then NULLED. Evidence AND value destroyed in two steps, each
   step individually "correct". This is why corners were the one
   family that never stabilised while everything around them did.
3. **roof_pitch** — replaced whenever the second read returns a valid,
   different pitch; every existing gable wall's triangle is rescaled at
   the new pitch. Second read beats primary unconditionally. NOTE: it
   can only RESCALE walls already marked gabled — it cannot flip WHICH
   walls are gables, so it is NOT by itself the EST-040221
   orientation-flip mechanism (that flip remains unattributed; the
   primary read or the plane-append below are the live candidates).
4. **garage plane appended** — additive; but when the primary read had
   already counted the garage eave inside its "main" plane, the
   appended plane DOUBLE-COUNTS into the plane-sum → top-level eaves.
   THE ORIGINAL GUTTER DOUBLE-COUNT MECHANISM.
5. **gutter runs** — fill-only when the primary has none. Conservative.

## WHAT IT LEAVES ALONE
Windows, doors, schedules, wall widths/heights, all evidence fields
except corner heights, starter, area table, appendages.

## RULING LANDED (2026-08-09)
- Seam REGISTERED: `roof_pass_overwrite` in SEAM_REGISTRY; every
  accepted overwrite ledgered old→new (pitch, corners, heights).
- NEVER-TOUCH RULE, enforced: the roof pass may NEVER replace an
  EVIDENCED value with an unevidenced one. A bare-number height list
  arriving against quoted primary heights is REFUSED; the refusal is
  NAMED on the rail (`roof_pass_rejected`).
- Roof-pass schema now demands DIM-or-null corner heights (same
  evidence form as the main read) — the asymmetry that fed the defect
  is closed at the source.
- Pinned: tests/test_roof_pass_seam_2026_08_10.py.

## OPEN — HOWARD'S CALL (reported, not changed)
- The MAX-WINS corner acceptance (`oc >= old_oc`) still stands.
  Candidate rule: AGREEMENT-OR-FLAG — when the two reads disagree on
  the walk, keep the primary and flag `corner_walk_conflict` naming
  both counts, instead of letting the higher read win.
- rakes_lf top-level: the model's bare number vs the plane sum — the
  LARGER wins (`if plane_rakes > rakes_lf`). Same max-wins shape on the
  rake side. Candidate: plane sum governs whenever planes exist
  (mirror of the eaves rule).

## THE FOUR NUMBERS THAT BUY MATERIAL (Howard's question, answered)
- **eaves_lf** → soffit + fascia + gutter coil. When ANY plane carries
  eave figures, the top-level number IS the plane sum (override,
  `_eaves_plane_summed`) — and plane eave/rake are DIM-or-null since
  8-9, so it inherits printed sources. No planes + gabled walls → sum
  of non-gable wall widths (evidenced walls). No planes, no gables →
  the model's bare top-level number rides (PROMPT tier). ONE governing
  number whenever planes exist.
- **rakes_lf** → fascia/rake trim. TWO numbers race, larger wins — see
  OPEN above. This is the weakest of the four eave-side figures.
- **starter_lf** → starter. Wall-width perimeter when walls extracted
  (evidenced walls; engine deducts entry doors); the printed/bare read
  only when no walls came back.
- **corner count/LF/heights** → corner posts. Counts are bare numbers
  (PROMPT tier) + the roof-pass ratchet (now ledgered, acceptance rule
  awaiting ruling); heights are evidenced DIMs with the never-touch
  rule now guarding them.
