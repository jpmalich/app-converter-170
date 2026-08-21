# SEND-84 — RULING CCC SHIPPED. FOUR REPORTS DELIVERED.
Suite: `bash scripts/handback_green.sh` (stamp in
`memory/handback_green_log.md`). Probes re-runnable:
`send84_anatomy_probe.py`, `send84_movecheck.py`,
`send84_guard_census.py`, `send84_deletion_ledger_report.py`,
`send84_preheight_census.py`.

## 0 — WHAT THE INK ACTUALLY SAYS (found before wiring)
SEND-82's "0.34/0.40 shortfall" was a MERGE ARTIFACT, not drawn
truth. The right chimney's joint is drawn as a rectangle WITH
CONNECTOR PIECES at y=64.04: x[77.978→78.323] (wall stroke → rect)
and x[79.389→79.769] (rect → chimney inner stroke) — breaks of
0.002/0.021, inside line-weight. The gap_tol merge had swallowed that
run into a siding course line, so the SEND-82 probe never saw it.
Judged on RAW drawn lines merged at LINE-WEIGHT ONLY, the shoulder's
ink runs member-to-member, ends exactly ON the strokes.

So the wired form of CCC(b)-as-minimum:
- Joints are judged per drawn jog LINE (y clustered at line-weight),
  its ink runs merged at line-weight — never on gap_tol-merged
  strokes.
- An end reaching its boundary stroke (line-weight) passes.
- An end falling SHORT passes only when it terminates ON the member's
  INNER TWIN: a through-going vertical at the end, with NO other
  through-going vertical between it and the boundary — the allowance
  is the member's own drawn twin separation, never a constant. No
  snapping.
- SHOULDER PAIRS (wall line × non-plate-terminated spanning stroke)
  run the same naming law OUTWARD: an overspanning end must terminate
  ON the boundary or the member's outer twin. Found necessary in
  probing: without it, face-long course lines whose ends merely come
  NEAR two members (within gap_tol) established phantom shoulders
  (Letrick left 42.76↔19.83, right 54.71↔77.64, Boni left
  12.01↔34.94). None moved an outline — but that was luck; now they
  are dead by law. Fragment chains (verticals that TERMINATE at the
  jog — the structural tie) keep the SEND-69 gap_tol law outside,
  which is what keeps the course-line chains unmoved.

## 1 — THE FOUR FIXED POINTS (verified on the data)
| point | verdict |
|---|---|
| true shoulder (right) | PASSES — ends ON wall stroke 77.98 and chimney inner twin 79.77; joins to outer 80.01 via the inner-twin allowance (0.244, the member's own separation) |
| left 24% wrong-edge jog (43.22↔45.30) | DEAD — its jog ink ends 0.19/1.39 short, landing on nothing |
| left 1–8% ticks | DEAD — name no references |
| 100–105% course-line chains | UNMOVED — fragment-chain law unchanged; front/rear faces byte-identical before/after |

## 2 — WHAT SHIPPED, ALL EIGHT FACES (three numbers each)
| face | before | after | SIL / WALL / SEALED |
|---|---|---|---|
| LETRICK front | [14.01,56.49] v4 | UNCHANGED | 54.71 / — / 54' |
| LETRICK rear | [38.13,80.88] v4 | UNCHANGED | 60.15 / — / 54' (contested scale, standing) |
| LETRICK left | [19.45,45.30] v6, 32.60, bump on FRONT edge | **[17.43,42.76] v6, bump on BACK edge at drawn joint y=22.28** | **31.94 / 29.4 / 32.7** |
| LETRICK right | [54.71,77.98] v4, 29.65 | **[54.71,80.01] v6, bump on RIGHT edge at drawn joint y=62.40** | **32.24 / 29.65 / 32.7** |
| BONI front | [16.29,62.01] v4 | UNCHANGED | — (no evidence scale) |
| BONI rear | [36.11,81.80] v4 | UNCHANGED | — |
| BONI left | INDETERMINATE (one corner) | UNCHANGED — CCC does not reach it (34.94 refused: member carries 3+ strokes); its cure stays a separate ruling | — |
| BONI right | NOT_ATTEMPTED (datum pair not located) | UNCHANGED | — |

RIGHT vertices: [54.71,61.32] [77.98,61.32] [77.98,62.40] [80.01,62.40]
[80.01,70.85] [54.71,70.85]. Boundary carried on the OUTER stroke
80.01 per your ruling (the wall's own convention) — that reads
32.24 ft, not the 31.9 the inner twin would give; the outer twin adds
2.59 ≈ 2'-7". Stated for the record: nothing tuned toward it — the
outer-carry is your convention ruling and the number lands where it
lands.

LEFT — BETTER THAN THE REGISTERED FLOOR. You ruled left becomes
honestly unresolvable at wall-only 29.4. The data says more: the same
drawn-joint law finds a REAL shoulder line at y=22.28 — ink
[17.669→19.459], ends ON the chimney's inner twin 17.67 (member
{17.43, 17.67}, separation 0.244) and ON the wall stroke 19.45 — the
BACK-EDGE chimney your prints settled. The wrong-edge front bump is
dead, the real one is read: bump on the LEFT (back) edge, silhouette
31.94, wall 29.4, projection 2.54 ft ≈ 2'-6½" vs your 2'-7". The
32.60-with-front-bump failure state is gone; the shape is now the
house's. SEND-82's probe missed this joint for the same merge-artifact
reason it missed the right one.

JOG HEIGHT, STATED PLAINLY: several drawn lines connect wall to
chimney (the top cap plus brick-course lines below it, at the
drawing's own course spacing; on right, also the shoulder rect at
y≈64.5). The wired read carries the jog at the TOPMOST connecting
line (right y=62.40, left y=22.28) — the drawn top of the projection
body, i.e. the largest honest projection area. If you want the step
carried at a different drawn line (e.g. right's rect at 64.55), that
is a ruling on WHICH drawn joint carries the step when several
establish — say the word and it moves; the acceptance shape above is
what ships today.

## 3 — GUARD-CASE CENSUS (the three inapplicability paths)
All 21 non-plate-terminated spanning strokes, both houses:
- JOINED (real projections): 4 — Letrick left 17.43/17.67, right
  79.77/80.01 (each pair = one chimney's two strokes).
- "no jog ink between the members": 15 — including all 8 KEPT eave
  boundaries (Letrick front 14.01/56.49, rear 38.13/80.88; Boni front
  16.29/62.01, rear 36.11/81.80): no joint exists on those faces at
  all, CCC takes nothing from a kept single — ZERO of the 8 hit any
  guard case, all outlines byte-identical.
- "member carries 3+ strokes": 3 — Letrick left 19.83, right 77.64
  (each the wall's own far twin), Boni left 34.94.
- "endpoint names no reference": 0 remaining (the dead candidates die
  there before reaching member analysis).

## 4 — THE n=1 CAVEAT, REGISTERED (memory/register_send84.md)
**UNVALIDATED.** One house's chimney, two joints, one drafting hand.
The rule is principled, control-tested, and shape-verified — and
still rests on Letrick alone. The third plan set is what tests it.
Every handback reporting the chimney working carries UNVALIDATED
alongside until then, the same way the anchor did.
Also registered: an unresolvable projection now SAYS SO —
`projection_refusals` rides the payload and the proposal basis
("PROJECTION REFUSED — spanning stroke at x=…% carries no drawn
shoulder…"). Pinned by synthetic test; no live face currently
carries one (both real chimneys joined).

## 5 — REPORT 1: DELETION LEDGER (EST-713272's nine zones)
**NOT RECOVERABLE — from any source.** Scanned everything persistent:
`zone_correction_events` (0 rows for the estimate),
`protected_estimate_ledger` (0), `estimates_trash` (0), line overlay
markers (only a derived vinyl line remains), all 14 run docs
(ai_measure/ai_blueprint/fixture/sessions — none embed zone
vertices). The deletions predate any ledger; the decay you named has
completed. Restored nothing, per your word.
**Wired going forward (every estimate):** `zone_deletion_ledger` —
- human DELETE snapshots the full victim polygon verbatim
  (kind=human_delete, actor, timestamp);
- re-propose snapshots the derived proposals it replaces
  (kind=propose_rebuild_wipe) — a rule change overwrites geometry;
  the ledger keeps what the superseded rules had drawn.
3 pins in `test_deletion_ledger_2026_08_21_send84.py` (snapshot
verbatim; wipe ledgered; no phantom entries). This loss class ends
here.

## 6 — REPORT 2: RULING XX WIRING (what it takes — not built)
`attribution_verdict(runs)` (ocr_geometry.py) is sealed and tested
but called only by `scripts/send38_report.py`. To put it in the live
pipeline:
1. CALL SITE: propose (routes/pdf_overlay.py) already walks every
   face; the natural seat is a per-estimate pre-pass — locate the
   floor-plan page via the envelope probe's ESTABLISHED status (the
   probe already identifies it), run `attribution_verdict`, stash the
   verdict on the proposal batch (`proposed_from.attribution`).
2. THE CHECK IT UNLOCKS (SEND-79 item 3): where XX says IMMATERIAL
   (equal side depths) and BOTH side elevations resolve via
   line-work, their widths should agree; disagreement → FLAG, NEVER
   RESOLVE. Post-CCC it would compare left 31.94 vs right 32.24 —
   0.3 ft apart, agreeing where they should (both = wall + one
   chimney; the old 32.60-vs-29.65 flag case is cured).
3. GUARDS ALREADY IN THE VERDICT: equality never overrides closure;
   INDETERMINATE (Boni's positional tie) stays silent — no pair, no
   claim; a true single-sided projection is a legitimate disagreement
   (a flag, not a verdict).
4. COST: ~30 lines in propose + surface on the proposal payload +
   pins (verdict stored verbatim; flag fires on width disagreement;
   silent on INDETERMINATE). No new rules needed — say the word.

## 7 — REPORT 3: FENCE MARGIN WARNING (authorized — WIRED)
On every propose, each face's fence is compared against every OTHER
drawing's own datum extent on the same page: when they share the
band's y-range and the neighbour's extent reaches inside the fence,
the proposal carries a PLAIN WARNING (`fence_margin_warning` in the
linework disclosure + "FENCE MARGIN WARNING — …" in the basis). The
fence itself stays applied VERBATIM — never shrunk, exactly as
ruled. No current face on either house triggers it (Letrick p2's two
drawings sit in separate bands) — the warning exists for the day a
sheet packs two drawings side by side.

## 8 — REPORT 4: PRE-HEIGHT-BUILD CENSUS (superseded-rule geometry)
20 stored proposals across 5 estimates:
- **EST-713272 (Boni): the ONLY estimate carrying superseded-rule
  wall-outline geometry** — 4 proposals from the pre-SEND-77 era (no
  x-fence, pre-CCC). A re-propose would refresh them under current
  law (and now ledgers what it replaces); left as-is pending your
  word.
- EST-655664 / EST-715139 / EST-351320 (Letrick series): proposals
  predating the line-work read entirely (no linework disclosure —
  band-rectangle era). EST-655664 additionally carries 1 human front
  zone and a line riding overlay qty.
- ZZ TEST_send68 TEMP: suite fixture, current-era (regenerates on
  every run).
- Human zones live on EST-886440 (PROTECTED — untouched) and
  EST-569367 (11 zones). No writes made anywhere by this census.

## STANDING RULES HELD
No cross-drawing evidence (each face read from its own band/fence);
no estimate influenced another; no job names in code (synthetic tests
only); EST-886440 untouched (423 guard intact on propose); purity pin
holds — the shoulder allowance is the drawing's own twin separation,
and nothing tunes toward 54, 30, 58, 30'-2", 33, 2'-7", or any sealed
figure (the checks above are checks).
