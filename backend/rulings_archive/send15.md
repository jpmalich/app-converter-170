Claude's SEND-15 is below. Follow the rulings exactly.
New rulings:
E — Invert the axis catalog. Leaves declare VERTICAL / HORIZONTAL / UNKNOWN. Undeclared = UNKNOWN. A share involving UNKNOWN fires the conflict rail. Pin a novel vertical leaf name.
F — Money-line visibility: conflict-only. Conflict shares annotate the money line; plain shares stay on the read-back card. Also build the elevation-sheet surface for the rail. Note the two unbuilt surfaces from send-13 as NOT BUILT in the register.
G — Never-average binds the corner/OSC path. A corner over a wall with no verified height reports NOT DERIVABLE and names the wall. List every other place averaging feeds a priced quantity.
H — Repair all five silent siblings as one class. A killed/subset input never produces a silent number. Prefer making the subset-aware value the only thing a reader can obtain.
I — Archive every send verbatim in-repo so the register can audit prose against pins.
Acceptance still stands: Howard re-fires EST-713272 and reports the four faces. That report stamps A/B. Note that until H lands, a face may show DERIVED while eaves/base/gable silently read 0.
pro-quote 8-14-2026 — SEND 15
Send 14 accepted. Ruling D built, Ruling C sealed, four censuses
delivered. Report 2 is the most useful thing you have produced on
this thread — it found five defects by construction rather than by
accident, which is what the census was for.
Reports 1 and 2 found real gaps. Fix them. Details below.
=== RULING E — INVERT THE AXIS CATALOG ===
[ANSWER Q1: INVERT / LEAVE ENUMERATED]
_leaf_is_vertical is an enumerated catalog: endswith height_ft,
_height, rise, plate. Everything else falls through to horizontal
SILENTLY.
This is the fifth instance of the same shape on this project, and
the answer has been the same every time: INVERT INTO A DECLARATION.
  - Every dimension leaf DECLARES its axis: VERTICAL, HORIZONTAL,
    or UNKNOWN.
  - Undeclared is UNKNOWN. Not horizontal. Never inferred from the
    field name.
  - A share involving an UNKNOWN-axis leaf fires the CONFLICT rail,
    naming the undeclared leaf.
Rationale: a quiet failure here is invisible forever. If a future
knee_ft or eave_ft or story_ft classes as horizontal, the conflict
rail simply stops firing on real conflicts and nothing goes red.
Failing loud on an undeclared leaf makes the next added field
announce itself the first time it is shared.
Pin required: add a leaf with a novel vertical name, assert it
lands UNKNOWN and that a share involving it fires the conflict
rail. That pin is what stops the catalog rotting again.
=== RULING F — MONEY-LINE VISIBILITY ===
[ANSWER Q2: CONFLICT-ONLY / ALL SHARES / MONEY STAYS SILENT]
Report 1's finding stands as stated: three surfaces ordered, one
built, and the two unbuilt ones were a ruling that never became a
pin — the same prose-said-done shape Ruling C exists to kill. Note
that in the send-13 register file as a NOT BUILT line, retroactively,
so the record shows it was ordered and missed rather than never
ordered.
Now build:
  ELEVATION SHEET — carry the rail. A dim drawn on a sheet whose
  evidence is shared must say so on that sheet.
  MONEY LINE — per the answer above. If CONFLICT-ONLY, a money line
  whose quantity derives from a dim on the conflict rail carries a
  note naming the dim and its competing consumers. Plain shares stay
  on the read-back card.
Reasoning behind conflict-only, for the record: on this house nearly
every dim is shared (9'-11" cites nine consumers). Annotating every
plain share on every money line produces a quote where every line
is flagged, which is the same as no line being flagged. The rail
that must never be ignorable is the one that says two paths cannot
both be right.
Both surfaces get pins in the send-15 register file, and the pins
assert what RENDERS, not what the model returns.
=== RULING G — NEVER-AVERAGE BINDS THE CORNER PATH ===
[ANSWER Q3: BINDS / DOES NOT BIND]
lp_package L62-497 derives corners/OSC/ISC from a wall_heights map
plus _ai_avg_wall_height_ft. Where a wall's own height was killed
or is a subset, that path substitutes an AVERAGE and prices it.
Two sealed rules are in collision with that:
  1. NEVER AVERAGE A MATERIAL-GOVERNING DIMENSION. The P3 gable
     precedent is on the record: drawn at worst case, FLAGGED, never
     averaged. A corner stick count is as material-governing as a
     gable.
  2. A VALUE MUST NOT OUTLIVE ITS BASIS. An average computed from
     surviving walls has no basis on a wall whose height died.
REQUIRED: a corner over a wall with no verified height reports NOT
DERIVABLE and NAMES THE WALL. It does not price an average. If a
worst-case substitution is wanted instead of a refusal, that is a
separate ruling and is not assumed here.
State in the handback every other place _ai_avg_wall_height_ft or
any sibling average feeds a priced quantity. If averaging is wider
than the corner path, I want the list before anything is changed.
=== RULING H — REPAIR ALL FIVE SIBLINGS AS ONE CLASS ===
[ANSWER Q4: ALL FIVE NOW / SUBSET]
The five from Report 2:
  1. walk_walls gable (measure_staging L155) — silent 0
  2. eaves_from_walls (L32-36) — silent under-count
  3. base_starter_course_lf — silent 0
  4. corners/OSC/ISC (lp_package) — average, per Ruling G
  5. batten +1 run × wall_height (lp_smartside) — top-level height
Repair them together, not one at a time. They are one defect wearing
five hats, and repairing them singly is exactly the mechanism that
produced them.
THE STANDARD FOR ALL FIVE: A KILLED OR SUBSET INPUT NEVER PRODUCES A
SILENT NUMBER. It produces a named refusal or a disclosed subset.
Silent 0 is the worst available outcome — it looks like a real
answer, it costs money, and nothing on any surface says the input
died. Your own sealed rule: an instrument that kills good data is a
defect of equal urgency to one that passes bad data. A silent zero
is both at once.
Also fix the disagreement Report 2 surfaced directly: walk_walls
gable returns silent 0 while profile_callouts gable at L310
discloses. Two paths, same quantity, different honesty. Name which
one is now canonical and pin the agreement.
PREFERRED SHAPE, if it is reachable: rather than teaching five
readers about subsets, make the SUBSET-AWARE VALUE the only thing a
reader can obtain, so a caller cannot reach a raw top-level
width_ft or height_ft without acknowledging its status. Report
whether that is feasible before doing it the long way. Five sites
taught individually is a sixth site waiting.
=== RULING I — ARCHIVE THE SEND PROSE ===
Report 4's honest limit is the real finding: the register can only
audit what already became a test, so a ruling made mid-paragraph in
an older send and never pinned stays invisible in exactly the way
segment-partial did. The retro-walk therefore proves the pins are
consistent, not that the rulings are complete.
Close it: archive every send VERBATIM in-repo, one file per send,
and make the register audit compare PROSE TO PINS rather than tests
to tests. Sends 8 through 15 exist in full and can be pasted in.
Until that archive exists, no retro-registration report should be
described as complete — say "consistent with existing pins" instead.
=== ACCEPTANCE ===
Howard re-fires EST-713272 (65bcb89d-8291-4b84-920c-7b503273f332)
and reports the four faces separately. That report stamps rulings A
and B, not the 2400-green suite.
Reading unchanged: widths and heights survive the shared-source
stage · BACK and RIGHT derive from located segments even where the
top-level width was never read · 24'-0.5" and page 9's 30'-0" still
locate · every face reports DERIVED, PARTIAL, or NOT DERIVABLE, and
every PARTIAL names which segments are in and out.
NOTED FOR THAT READING: until Ruling H lands, a face may report
DERIVED while eaves, base course, and gable silently read 0. The
four-face report is evidence about DERIVATION, not about money.
EST-886440 remains PROTECTED. 423 on every derived write. Nothing
applied. Integral-J stays ON. Purity pin holds — no derivation reads
another estimate at derivation time, no tuning toward any second
opinion.

=== RULING J — MONEY DERIVES FROM HONEST QUANTITIES (principle, send-15 addendum) ===
One principle I want held as we go:
Money is derived from the material quantities.
Measure the house → produce an honest material list (every quantity carries its real status) → populate the correct line items → derive the money from those quantities.
Do not build special money-line logic, averages, or silent zeros.
If the takeoff is honest, the money is honest.
If a quantity is NOT DERIVABLE, the money that depends on it should reflect that — not be filled in quietly.
