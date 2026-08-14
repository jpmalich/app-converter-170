Claude's SEND-16 is below. The standing principle is sealed and supersedes earlier money-line instructions.
Standing principle (register verbatim at the top of send-16):
Money is derived from the material quantities. Measure → honest material list (every quantity carries its real status) → populate line items → derive money from those quantities. No special money-line logic, averages, or silent zeros.
Key changes:
Ruling F (money-line flagging) is retired. Status travels with the quantity; the money surface only renders what arrived.
Ruling J — Status is a property of the quantity (DERIVED / PARTIAL / NOT DERIVABLE). It propagates. A quantity cannot exist without a status.
Ruling K — A NOT DERIVABLE line is present, quantity reads NOT DERIVABLE (names the dead input), price column is empty (not $0), and it blocks the quote gate.
Ruling L — Any total that includes a NOT DERIVABLE line is marked INCOMPLETE, states how many lines are refused, and is never presented as a price.
G and H become consequences of J rather than separate special cases.
Order: J plumbing first → then G/H (report which ones J does not fix by construction) → K/L → E → I.
Howard still re-fires EST-713272 for the four-face report (stamps A/B).
pro-quote 8-14-2026 — SEND 16
STANDING PRINCIPLE, SEALED. This governs all future work and
supersedes any conflicting instruction in earlier sends including
mine.
  MONEY IS DERIVED FROM THE MATERIAL QUANTITIES.
  Measure the house → produce an honest material list, where every
  quantity carries its real status → populate the correct line
  items → derive the money from those quantities.
  Do not build special money-line logic, averages, or silent zeros.
  If the takeoff is honest, the money is honest. If a quantity is
  NOT DERIVABLE, the money that depends on it must reflect that —
  not be filled in quietly.
Register this verbatim as the top of the send-16 register file. It
is a principle, not a task, so it does not "complete" — it is the
standard every later ruling is read against.
=== WHAT THIS CHANGES IN SEND 15 ===
RULING F IS RETIRED AS WRITTEN. Do not build a money-line flagging
mechanism, and do not implement the conflict-only-versus-all-shares
distinction as logic. There is nothing to decide there: the money
line INHERITS the status its quantity already carries. Status
travels with the quantity, from the read through the takeoff into
the line item, and the money surface RENDERS what arrived. It never
computes a status of its own.
What survives from Ruling F is only the display question: which
statuses are shown at which zoom level on which surface. That is a
rendering choice, made after the status plumbing exists, and it is
not urgent.
RULINGS G AND H STAND but are no longer two cases. They are the
same consequence of the principle:
  - G, the corner/OSC average: _ai_avg_wall_height_ft substitutes a
    computed number for a wall whose height died. That is filling
    in quietly. It goes.
  - H, the five silent siblings: gable, eaves, base course, corners,
    battens. Each returns a real-looking number from a dead input.
    That is filling in quietly. They go.
So the instruction to the agent simplifies to one sentence: NO
DERIVED QUANTITY MAY BE PRODUCED FROM A KILLED, SUBSET, OR MISSING
INPUT WITHOUT CARRYING THAT FACT FORWARD.
=== RULING J — STATUS IS A PROPERTY OF THE QUANTITY ===
Build the plumbing the principle requires, once, rather than five
times:
  - Every derived quantity carries a STATUS alongside its value:
    DERIVED · PARTIAL (a disclosed subset, with the excluded parts
    named) · NOT DERIVABLE (with the reason and the dead input
    named).
  - A quantity cannot exist without a status. Not defaulted to
    DERIVED. A quantity constructed without one is an error, not a
    DERIVED quantity.
  - Status PROPAGATES: any quantity computed from a PARTIAL input
    is at best PARTIAL; any quantity computed from a NOT DERIVABLE
    input is NOT DERIVABLE. This is the rule that makes the five
    siblings impossible rather than individually corrected.
  - The line item carries the status through unchanged. The money
    surface reads it and never recomputes it.
Report BEFORE building whether the status can ride the existing
quantity structures or needs a wrapper. The preferred shape from
send 15 stands: make the status-carrying value the only thing a
caller can obtain, so a raw top-level width_ft or height_ft cannot
be reached without acknowledging its state. Five call sites taught
individually is a sixth call site waiting.
=== RULING K — A NOT DERIVABLE LINE ===
[ANSWER Q1: PRESENT+NO PRICE+BLOCKS GATE / $0 WITH FLAG / OMITTED]
A line item whose quantity is NOT DERIVABLE is PRESENT on the
material list and on the quote. Its quantity column reads NOT
DERIVABLE and names the input that died. Its price column is EMPTY —
not zero. It registers as a blocker on the quote gate.
Reasoning: a zero in a money column reads as "nothing needed" to
anyone glancing at it, which is the silent zero wearing a flag. An
omitted line is invisible, which is precisely the Hover behavior
this product exists to beat. An empty price with a named cause is
the only one of the three that a contractor cannot misread.
=== RULING L — AN INCOMPLETE TOTAL IS NOT A PRICE ===
[ANSWER Q2: YES / NO]
Any total, subtotal, or grand total that sums over a NOT DERIVABLE
line is marked INCOMPLETE, states how many lines are refused, and
is never presented as a price.
Reasoning: this is the silent zero one level up, and it is the most
dangerous version, because the total is the number a contractor
actually looks at. An honest material list that rolls up into a
confident wrong total defeats the principle at the last step. A
PARTIAL input anywhere means the total is at best PARTIAL, by the
same propagation rule as Ruling J.
=== ORDER OF WORK ===
  1. Ruling J plumbing — status on the quantity, propagation, the
     structural report first.
  2. Rulings G and H — the average and the five siblings, which
     should mostly fall out of J rather than being fixed by hand.
     Report which ones J did NOT fix by construction; those are the
     ones that need a look.
  3. Rulings K and L — line and total behavior.
  4. Ruling E from send 15 — invert the axis catalog. Unchanged and
     still wanted.
  5. Ruling I from send 15 — archive the send prose. Unchanged.
Every one of these enters the send-16 register file as a pin or a
named skip, per sealed Ruling C.
=== ACCEPTANCE ===
Howard re-fires EST-713272 (65bcb89d-8291-4b84-920c-7b503273f332)
and reports the four faces separately. That report stamps rulings A
and B, not a green suite.
Note carried forward: until Ruling H lands, a face may report
DERIVED while eaves, base course, and gable silently read 0. The
four-face report is evidence about DERIVATION, not about money.
EST-886440 remains PROTECTED. 423 on every derived write. Nothing
applied. Integral-J stays ON. Purity pin holds — no derivation reads
another estimate at derivation time, no tuning toward any second
opinion.
