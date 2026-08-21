# SEND-81 — PREDICTION (recorded BEFORE the run, unrevised)

Howard's fifth prediction, verbatim:

> AFTER THE CURE: LEFT ≈ 32.60 AND RIGHT ≈ 32.3–32.4 (29.65 plus
> 2'-7"), AGREEING WITHIN ABOUT 0.3 FT.
> BONI LEFT STOPS REFUSING, since its far boundary was being
> discarded by the same rule.
> NO CURRENTLY-RESOLVED FACE MOVES EXCEPT RIGHT, WHICH MOVES BY THE
> CHIMNEY.
> If left moves off 32.60, the refinement is admitting something
> Howard has just told us is not there.

Left settled by Howard's prints: the chimney is on the BACK wall,
appears ONLY on the LEFT SIDE of the left elevation; there is NO real
projection on the other edge; the correct left reading is 32.60 with
exactly one chimney projection.

Property under test (structural, no chimney exception): A PROJECTION
DISPLACES THE OUTERMOST BOUNDARY — NOTHING LIES BEYOND IT. A
course-end line or corner board has wall on both sides. A qualifying
stroke must be part of the OUTERMOST BOUNDARY: no drawn geometry
outside it in that direction, within the face's own band and fence,
± the drawing's own line-weight tolerance. Reported against all 7
dropped strokes BEFORE wiring.

## OUTCOME (appended after the run — unrevised above this line)

**THE PROPERTY AS STATED FAILS — REPORTED BEFORE SHIPPING, NOTHING
WIRED.** Probe: `memory/send81_outermost_probe.py`.

Tested three ways: (1) literal — any drawn geometry beyond ± line
weight; (2) restricted to ink inside the datum interval the boundary
claims to bound; (3) restricted to boundary-class (spanning) strokes.

- Literal and interval-restricted: **ALL 7 dropped strokes fail** —
  and as a control, **ALL 8 currently-KEPT boundaries fail too**
  (including wall corners that resolve correctly today). Elevation
  sheets carry dimension ticks and leader ink outboard of every
  silhouette edge; "nothing lies beyond it" is never literally true of
  ANY boundary on these drawings.
- Spanning-class restricted: admits right's chimney (79.77/80.01, only
  a dimension tick at x≈86 beyond) and Boni left's far corner (only
  0.5-ft ticks beyond) — **but ALSO admits left's 17.43/17.67**
  (only two tiny ladder ticks at x≈11.4 beyond). Left would move off
  32.60 — admitting exactly what Howard has said is not there.

**The irreducible finding:** left-17.67 and right-79.77 are
STRUCTURALLY IDENTICAL under every outermost variant tested — full
height double strokes, cladding courses ending on them, nothing but
tick-class ink beyond, ≈2'-7" outboard of a plate-terminated wall
line. Any rule that admits the right chimney admits the left edge;
any rule that excludes the left edge excludes the chimney. So the
prediction cannot be satisfied by this property: it demands left
UNMOVED and right MOVED from two configurations the property cannot
tell apart.

**Why today's 32.60 is right anyway (the cancellation):** both
candidate projections measure ≈2'-7". 30' wall + one 2'-7" projection
is ≈32.6 ft WHICHEVER edge carries it. Today's read reaches 32.60 via
the front-edge fragment chain (45.30) while dropping the back-edge
chimney (17.43) — per Howard's prints, the wrong edge — but the WIDTH
is insensitive to which edge, which is why the sealed figure held.

**The one drawn difference found (for a future ruling, not shipped):**
right has a drawn SHOULDER — a horizontal at y=64.55 whose ink spans
the wall→chimney gap (x 78.32→79.37) and stops at both strokes. Left
has NO equivalent joining 19.45→17.67 (only a 0.03-wide tick and
course lines that continue far past the wall line). But formalizing
"reaches both strokes" needs a tolerance smaller than the established
line-weight/box tolerances (the tick sits 1.45 from the stroke, the
true shoulder 0.34-0.40, and gap_tol is 1.53) — a smaller ad-hoc
number would be a tuned threshold, the shape ruled against. Not built.

**MIRROR CHECK: HOLDS.** The candidate chimney sits at LOW-x (left
side) of the LEFT elevation (17.43/17.67) and at HIGH-x ≈80 (right
side) of the RIGHT elevation — opposite edges, exactly how a back-wall
feature appears on two opposing side views. No elevation is mirrored
in the read.

**MOVE-CHECK: not applicable — nothing was wired; all 8 faces stand
exactly as before this send.**

