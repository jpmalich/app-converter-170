# SEND-81 — OUTERMOST-BOUNDARY REFINEMENT: REPORT. NOT WIRED.

Full prediction + outcome: `memory/send81_prediction.md`.
Probe (re-runnable, read-only): `memory/send81_outermost_probe.py`.

## The property, tested against all 7 dropped strokes — and 8 kept controls

"OUTERMOST = no drawn geometry outside it in that direction" was run
three ways within each face's band + fence: literal, restricted to the
datum interval, restricted to boundary-class (spanning) strokes.

| stroke | face | literal | interval-only | spanning-class | what actually lies beyond |
|---|---|---|---|---|---|
| x=79.77 chimney | LETRICK right | INTERIOR | INTERIOR | **OUTERMOST** | one dimension tick H x[85.96,86.08] |
| x=80.01 chimney twin | LETRICK right | INTERIOR | INTERIOR | **OUTERMOST** | same tick |
| x=77.64 wall twin | LETRICK right | INTERIOR | INTERIOR | INTERIOR | the chimney itself (correct) |
| x=34.94 far corner | BONI left | INTERIOR | INTERIOR | **OUTERMOST** | 0.5-ft leader ticks x≈36.6 |
| x=17.43 back edge | LETRICK left | INTERIOR | INTERIOR | **OUTERMOST** | two ladder ticks x≈11.4 |
| x=17.67 back edge twin | LETRICK left | INTERIOR | INTERIOR | **OUTERMOST** | same ticks |
| x=19.83 corner twin | LETRICK left | INTERIOR | INTERIOR | INTERIOR | 17.67 spans beyond it (correct) |
| *controls: all 8 currently-KEPT boundaries* | both houses | INTERIOR | INTERIOR | — | dimension/leader ink outboard of every silhouette edge |

- The literal and interval readings exclude EVERYTHING — including
  every boundary that resolves correctly today. Not a discriminator.
- The spanning-class reading admits the chimney and Boni's far corner
  (the two Howard wants in) — **and left's back-edge strokes (the one
  Howard has ruled is not to move the face)**. Left would go ~35.

**Left-17.67 vs right-79.77 are structurally identical** under every
variant: full-height double strokes, courses ending on them, ≈2'-7"
outboard of a pt wall line, nothing but tick-ink beyond. The property
cannot admit one and exclude the other. Reported before shipping, as
ordered.

**The cancellation that protected the sealed figure:** both candidate
projections measure ≈2'-7", so 30' + one projection ≈ 32.6 ft
whichever edge carries it. Today's 32.60 rides the front-edge fragment
chain while dropping the back-edge chimney — the wrong edge per the
prints, the right width by arithmetic.

**One drawn difference exists** (right has a true shoulder horizontal
spanning the wall→chimney gap and stopping at both strokes; left has
none joining 19.45→17.67) — but formalizing it needs a joint tolerance
smaller than the established line-weight/box tolerances (true shoulder
0.34–0.40 off the strokes; the false tick 1.45 off; gap_tol 1.53).
Inventing a smaller number would be a tuned threshold. Left for
Howard's ruling.

**MIRROR CHECK: HOLDS** — chimney at the left side of the left view,
right side (x≈80) of the right view. Opposite edges; no mirrored read.

**PREDICTION #5 OUTCOME: not satisfiable by this property** — it
requires separating two configurations the property cannot tell apart.
Recorded unrevised in the prediction file.

**MOVE-CHECK: n/a — nothing wired; all 8 faces unchanged.**
