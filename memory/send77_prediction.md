# SEND-77 — X-SCOPING CURE — PREDICTION (recorded BEFORE the run)

Howard's prediction, verbatim from the send (fourth prediction; the
last three each paid off). Recorded unrevised; outcome appended below
after the dry run.

> LETRICK RIGHT SHOULD RESOLVE TO ROUGHLY 32.6 FT WITH 6 VERTICES —
> 30' wall plus the 2'-7" chimney — MATCHING LEFT.
>
> A chimney projecting from the back wall shows in PROFILE on BOTH
> side elevations, so if it appears on left it should appear on right.
>
> IF IT RETURNS 30.0 FLAT WITH 4 VERTICES, either the chimney is
> offset toward the left side of the house, or the read missed it on
> right. Howard's prints settle which, and the difference matters — a
> read that finds a feature on one side and not the other is a
> different problem from a house that only has it on one side.

Mechanism under test: FENCE CONTAINMENT — a qualifying stroke lies
entirely inside the face's OWN datum-line extent in x (the union of
the governing datum labels' marker boxes), exactly as BAND CONTAINMENT
requires it to lie inside the title band in y. Set membership against
the drawing's own evidence; no threshold; the fence is NEVER shrunk to
fit. The fence carries the leader offset (10–16 ft wide of the wall,
Ruling ZZ) — acceptable only as an OUTER BOUND; the actual gap to the
neighbouring drawing is reported against the fence width below.

## OUTCOME (appended after the run — unrevised above this line)

Dry run 2026-08-21 (`memory/send77_dryrun.py`), latest done runs, both
houses, all 8 faces BEFORE/AFTER:

**LETRICK RIGHT: RESOLVED — 29.65 ft, 4 VERTICES, x [54.71, 77.98].**
The prediction's SECOND branch fired, exactly as written: 30-flat-ish
with 4 vertices, NOT 32.6 with 6. Per the prediction's own words:
either the chimney is offset toward the left side of the house, or the
read missed it on right — **Howard's prints settle which.** Residual
−0.35 vs the 30' wall alone (−3.05 vs wall + chimney IF the chimney
should show). No step survived on right; left's 2'-7" step (6 vertices)
stands untouched.

Downstream (a change, reported as one): with right's wall now trusted,
the right GABLE TRACES — 128.82 ft² at right's own scale, within 1% of
left's traced 129.98 ft². Two independent drawings tracing to the same
gable is corroboration, not tuning. Gable read fed FENCED vs UNFENCED
strokes returns byte-identical results on every traceable face
(`memory/send77_gable_check.py`) — the gable call needs no fence and
was left as-is.

**MOVE-CHECK, EXHAUSTIVE (all 8): NO currently-resolved face moved.**
- LETRICK front 54.71 ft v=4 (+0.71) — unchanged
- LETRICK rear 60.15 ft v=4 @9'-11" contested — unchanged
- LETRICK left 32.60 ft v=6 (30' + 2'-7") — unchanged
- LETRICK right INDETERMINATE → **RESOLVED 29.65 ft v=4** (the cure)
- BONI front x [16.29, 62.01] v=4 (no evidence scale) — unchanged
- BONI rear x [36.11, 81.80] v=4 — unchanged
- BONI left INDETERMINATE (one corner) — unchanged
- BONI right NOT_ATTEMPTED (no FF datum → no fence either) — unchanged

**THE FENCE MARGIN, MEASURED (gap to nearest foreign spanning stroke
vs fence width):** LETRICK front 25% · rear 9% · left 111% · right 16%
· BONI front **2%** · rear **3%** · left 73%. Said plainly: **the Boni
front/rear margins are THIN** — the two drawings on that shared sheet
sit 1.5–1.6% of page outside the fence. The cure works there today by
the sheet's spacing, not by principle; a tighter-spaced set will put a
neighbour INSIDE a leader-inflated fence and the fence will exclude
nothing. The fence was NOT shrunk to fit (Boni front/rear resolved
both before and after, so nothing depended on it here — but the
margin is the fact to carry forward).

WIRED after this report: `linework_read.wall_outline_from_segments`
(x_fence param, FENCE CONTAINMENT beside BAND CONTAINMENT) +
`routes/pdf_overlay.py` propose (fence = union of the face's own datum
marker boxes, disclosed on `proposed_from.linework.x_fence`). Pins:
`tests/test_xscope_2026_08_21_send77.py` (6).

