Claude's SEND-14 is below. Report only on the censuses (except Ruling D, which is a code change).
Accepted and sealed:
Ruling C — Register discipline is permanent: one register file per send, ruling words verbatim in docstrings, held rulings as visible named skips.
Ruling D — Narrow the conflict rail to physically-impossible shares only. An overall dimension serving two opposing facades (58'-0" front + back) stays on the plain rail. State the predicate and name the pin that proves the 58'-0" front/back share lands on the plain rail.
Report only (do not build yet):
Surface census for the shared-source flag (sheet / read-back card / money-line note) — which surfaces actually render it, exact string the user sees.
Consumer census of every call site of wall_body_gross_sqft, top-level width_ft, and height_ft — which received the subset treatment.
The no-fallback pin that fails if the top-level rectangle fallback returns.
Retro-registration walk of the last six sends (which rulings have a pin, a named skip, or neither).
After those reports, Howard will re-fire EST-713272 and report the four faces.
pro-quote 8-14-2026 — SEND 14
REPORT ONLY, except Ruling D. No other code until the reports below
are read.
Send 13 accepted on rulings A and B. The process report in item 3 is
accepted and promoted to standing discipline.
=== RULING C — REGISTER DISCIPLINE, SEALED ===
[ANSWER Q1: SEAL / DECLINE]
Adopt as permanent, not as a one-off for send 13:
  - ONE REGISTER FILE PER SEND. Every ruling in that send becomes a
    pin in it, whether the ruling arrived as a numbered item or as a
    clause inside a paragraph answering something else.
  - The RULING WORDS go in the docstring, verbatim. Not a paraphrase,
    not a restatement of what was built.
  - A ruling that is HELD enters as a VISIBLE NAMED SKIP stating why
    it is held and what would unhold it. It shows in every run as
    on-the-record-and-unbuilt.
  - A ruling that cannot be expressed as a pin is reported NOT
    BUILT in the handback. That is an acceptable line.
The mechanism you named is correct and is now the standing
assumption: THE SUMMARY TRANSPORTS WHAT THE TESTS ENFORCE, NOT WHAT
PROSE SAID. Every handoff from here inherits the register file, not
the prose.
Retro-registration required, report only: walk the last six sends
and report which ruled items have a pin, which have a named skip,
and which have neither. Do not build anything found missing. Report
it. A fourth vanished ruling is more likely to be already gone than
about to happen.
=== RULING D — NARROW THE CONFLICT RAIL ===
[ANSWER Q2: NARROW TO PHYSICALLY-IMPOSSIBLE / LEAVE LOUD]
The current trigger is a FIELD-NAME COLLISION: the same leaf field on
two different named features. That trigger fires on the exact case
send 13 defended as legitimate — the printed 58'-0" overall serving
both walls.front.width_ft and walls.back.width_ft. On a rectangular
house that is not a misattribution, it is the house.
Correct predicate is PHYSICAL IMPOSSIBILITY: two features that
cannot both hold that value. Two walls' heights on a house with
differing wall heights. A wall height and a dormer height. A width
and a height. Those go to dims_shared_source_conflict.
An overall dimension serving two opposing facades goes to the plain
dims_shared_source rail with its consumers named.
Reason this matters more than it looks: a rail that fires on the
most common legitimate share teaches the reader to ignore it, and
then it is not there when the real conflict arrives. A flag that
cries wolf is the same defect class as a flag that never fires.
State in the handback which predicate you implemented and name the
pin that proves the 58'-0" front/back share lands on the PLAIN rail.
=== REPORT 1 — SURFACE CENSUS FOR THE SHARED-SOURCE FLAG ===
Send 13 ordered the flag onto three surfaces: the elevation sheet,
the read-back card, and the derived money line's note. The handback
names a rail plus dictionary text.
Report, per surface, the component or template that renders it and
the pin that proves it renders. Where a surface does not carry it,
say NOT BUILT. Do not build it in this pass.
Include: what a user actually SEES on a flagged money line. The
exact string, and where on the line it sits.
=== REPORT 2 — CONSUMER CENSUS ===
The handback names two consumers of wall_body_gross_sqft: walk_walls
and breakdown_walls_by_profile. Two named is not a census.
Enumerate EVERY call site of:
  - wall_body_gross_sqft
  - the top-level walls.<face>.width_ft
  - the top-level walls.<face>.height_ft
For each, state whether it received the subset treatment, and if not,
what it does when the value is a subset or was killed. Corners, OSC,
base course, soffit, frieze, gutter, opening perimeter — anything
that reads a wall dimension is in scope.
This is the project's signature failure shape: A FIX APPLIED TO ONE
PATH AND NOT ITS SIBLING. It has bitten on sheet-scoping, on the
fraction skeleton, and on the consumer-key detector. The census is
how it stops being discovered by accident.
=== REPORT 3 — THE NO-FALLBACK PIN ===
Name the pin that FAILS if the top-level rectangle fallback returns.
Not the three rewritten stale pins — the one that catches a
reintroduction. If it does not exist, say so.
The rectangle fallback is a VALUE OUTLIVING ITS BASIS, which is the
second recurring shape on the register. It needs a live guard, not
corrected documentation.
=== ACCEPTANCE — THE RE-FIRE ===
Howard re-fires EST-713272 (65bcb89d-8291-4b84-920c-7b503273f332)
and reports separately. That report, not the 2393-green suite, is
what stamps rulings A and B built. Standing reason: this project
has shipped four builds with a green suite and a broken browser.
The reading:
  - widths and heights survive the shared-source stage
  - BACK and RIGHT derive from their located segments even where the
    top-level width was never read
  - 24'-0.5" and page 9's 30'-0" still locate (both were recovered
    last build and must not regress)
  - every face reports DERIVED, PARTIAL, or NOT DERIVABLE, and every
    PARTIAL names which segments are in and which are out
EST-886440 remains PROTECTED. 423 on every derived write. Nothing
applied. Integral-J stays ON. Purity pin holds — no derivation reads
another estimate at derivation time, no tuning toward any second
opinion.
