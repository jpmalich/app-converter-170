# SEND-143 — THE NAMES ARE OFF, AND PHASE 2 TRIM READS ONLY WHAT WAS DRAWN

Stamp, verbatim from `scripts/handback_green.sh`:

```
RECORDED: 2026-08-28 12:55 UTC · 734c97b · CLEAN
RESULT: 3091 passed, 9 skipped, 7 warnings in 452.29s (0:07:32)
CENSUS: census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION (none)
INGRESS SMOKE: 4 passed in 2.01s
```

Quote wiring stays OFF. No new mark type. No price. No material-list line.
EST-886440 untouched. EST-373526 was drawn on twice through the API for the
report and the browser check — **every mark deleted, every scale cleared**
(`marks left: 0, scales left: None`).

---

## ITEM 1 — THE RENAME TABLE, OLD → NEW

| old | new | where |
|---|---|---|
| `boni` | `sealed_fixture_c` | `fixture_figures.py` registry key |
| `tanis` | `sealed_fixture_d` | same |
| `dart` | `sealed_fixture_e` | same |
| `letrick_v3` | `sealed_v3` | the gate VALUE — `routes/lp_package_routes.py`, `routes/elevation_sheets.py`, `fixtures/docs/estimates.json`, **and the live EST-373526 doc (1 doc restamped)** |
| `backend/letrick_hand_takeoff_key.py` | **DELETED** | the one-release shim — grep first showed **zero live imports**; its manifest line went with it |
| `tests/test_letrick_item3_chase_ratification.py` | `tests/test_sealed_item3_chase_ratification.py` | `git mv` |
| `tests/test_letrick_lap_unification_ruling.py` | `tests/test_sealed_lap_unification_ruling.py` | `git mv` |
| `LETRICK` / `Letrick` / `letrick` inside those two files | `SEALED_FIXTURE` / "the sealed fixture" / `sealed_fixture` | prose + one test name |
| `test_letrick_identity_app_equals_key_residual_zero` | `test_sealed_fixture_identity_app_equals_key_residual_zero` | same file |

**NO FIGURE CHANGED.** `all_fixture_figures()` returns the **same 28 numbers**
it returned before either rename, and the registry still requires FOUR
entries — the coupling did not loosen. A pin now asserts every old key is
GONE, not merely that the new ones are present.

**STILL CARRYING THE NAME, NOT AUTHORISED THIS SEND**: `LETRICK_TAPE_WALLS`
in `routes/demo.py` (imported by `elevation_sheets.py`) and the name in
report narratives / demo-fixture customer records under `memory/` and in
`backend/tests/*` prose. Say the word and it goes.

## ITEM 0 — MY OWN SEND-142 REGRESSION, REPORTED THEN CLOSED

Moving photos off the pod disk left THREE readers looking for the file on
disk with no fallback. A photo uploaded after SEND-142 would have answered
**"Uploaded photo not found on server" (404)** at the main AI Photo Measure
door. Fixed:
· `upload_store.rehydrate_to_disk` now asks **object storage first**, then
  the Mongo backing store — a disk file is only ever a cache now.
· `routes/ai_measure.py:2565` (the measure door) and `:7329` (the
  cross-check pass) fetch the photo back before refusing or skipping.
· `routes/photo_takeoff.py` `_photo_natural_size` — the Stage-2 pull-in
  fetches the photo back; if the bytes cannot be found ANYWHERE the refusal
  still stands, because **no size is ever guessed**.
**LIVE PIN**: an object written to storage with **no Mongo blob at all**
comes back byte-identical through `rehydrate_to_disk`.

## ITEM 2 — THE REPORT, THEN ONLY WHAT IT SUPPORTED

The mark vocabulary is unchanged: `siding_zone` · `non_siding_zone` ·
`opening` · `gable` · `dormer`. **There is no corner tick, no wall-base
mark, no eave mark and no wall-height field**, so four of the six trims have
nothing to read. Numbers below are from `memory/send143_rig.py` on
EST-373526's FRONT photo (tape 10'-0" over 120 px; Phase 1 read back siding
900.0 ft², opening 18.0 ft², gable 150.0 ft² = ½ × 30 × 10 ✓).

| trim | mark it reads | formula (feet) | missing / unconfirmed | live |
|---|---|---|---|---|
| **J-channel** | confirmed `opening` **with a drawn box** | Σ perimeter of the box = Σ‖edge‖ × ft/px | `—` "count only — this opening is a tap with no drawn extent; box it" · no scale → `—` · a box enclosing nothing → `—` | **18.00 LF** |
| **Gable rake** | confirmed `gable` — its two rake lines are drawn | ‖left→peak‖ + ‖peak→right‖, measured AS DRAWN | `—` carrying the gable's OWN refusal ("NO RISE") | **36.06 LF** |
| **Outside corners** | nothing | — | `—` "no corner is marked … no wall here carries a confirmed height … **No height is copied from another wall, another photo or another estimate**" | **—** |
| **Inside corners** | nothing | — | `—` same | **—** |
| **Starter** | nothing | — | `—` "no wall BASE is marked … a zone outline does not say which of its edges is the base, and the base **may not be read off the plate line or the eave**" | **—** |
| **Soffit** | nothing | — | `—` "no EAVE is marked — the roof edge is not invented" | **—** |
| **Fascia (horizontal)** | nothing | — | `—` "… not invented … **the GABLE RAKE is measured separately**" | **—** |

### THE WIRED ROWS, AS THEY RENDER
Seven rows in a fixed order — `outside_corner · inside_corner · j_channel ·
starter · soffit · fascia · gable_rake` — in a fourth rail panel,
*"Linear runs — confirmed marks only"*. Live on EST-373526:

```
Outside corners  —        no corner is marked on this photo, and no wall here…
Inside corners   —        no corner is marked on this photo, and no wall here…
J-channel        18.0 LF
  · front window   18.0 LF  perimeter of the box drawn on this photo · 3.0 ft × 6.0 ft · 18.0 LF
  · tapped window  —        count only — this opening is a tap with no drawn extent; box it…
Starter          —        no wall BASE is marked on this photo…
Soffit           —        no EAVE is marked on this photo — the roof edge is not invented…
Fascia           —        no EAVE is marked… The GABLE RAKE is measured separately…
Gable rake       36.06 LF   [GABLE ZONE]
  · front gable    36.06 LF  the two rake lines drawn on this photo · span 30.0 ft · rise 10.0 ft · 36.06 LF
  · flat gable     —        the peak sits on the eave line — this gable has NO RISE…
```

**THE RULES, HELD BY 23 PINS** (`test_send143_trim_and_names_2026_08_28.py`):
CONFIRMED marks only (a provisional box feeds nothing) · TAPE GOVERNS, and
with no scale the row still appears and says the box is drawn but its length
is not known · every measured row states its BASIS on screen · **the rake
never joins a wall lane** (with 36.06 LF on screen, starter and both corners
stay em dash) · a non-siding mask never shortens a linear run · the
refusals contain no "typical", "average", "assume" or "mirror" · **no lane
ever defaults to 0** — the totals move only behind an explicit
`is not None`, and `TrimPanel.jsx` prints the em dash whenever a figure is
null. The panel is a PURE PRINTER: not one refusal sentence exists in the
JSX, so no reason can drift on the client (the SEND-140 rule).

**APPLY** writes `photo_j_channel_lf` and `photo_gable_rake_lf` — quantity
only. Money tokens are absent from the whole module; a pin checks every
line of code that even contains "price" and passes only the sentences that
REFUSE money.

### FOUR PINS WERE UPDATED BY NAME, NONE RELAXED
· SEND-131A's phase-boundary pin: Phase 2 is no longer "NOT built" — it now
  asserts what IS built and that **PHASE1_KINDS and PHASE2_KINDS still do
  not overlap**, so a starter/corner/soffit/fascia MARK is still refused at
  the door. · SEND-136's correction-factor pin: `math.hypot` (the length of
  a line the contractor drew) is allowed outside the classifier; `acos`,
  `cos`, `sin`, `tan`, `atan`, `radians`, `degrees` stay banned line by
  line, so no angle can ever scale a figure. · the surface-audit pin: the
  panel has NO silent `return null` — the parent mounts it. · SEND-142's
  surface helper now reads `TrimPanel.jsx` too.

### BROWSER CHECK — REAL PHOTO, REAL MARKS
`test_reports/iteration_62.json` (41/41) and `iteration_63.json` together
read every row on EST-373526's FRONT photo: the panel and all seven rows in
order · every figure em dash with its named refusal before anything is drawn
· a provisional box counted as nothing · J-channel measuring the drawn box
with its basis line · the tapped opening refusing by name · the rake at
36.06 LF tagged GABLE ZONE with span/rise · the flat gable's NO RISE
refusal · **no "0" or "0 LF" anywhere in any state**.

## NOT TOUCHED
Quote wiring · blueprint line-work · new mark types · Phase 2 on blueprint
elevations · the storage lane split.

## SCOPED FOR NEXT SEND (Howard: "scope, do not build")
The three missing mark types — **corner tick · wall base · eave** — which
between them unlock starter, outside/inside corners, soffit and horizontal
fascia. Each needs: the mark kind + tap order, a confirm/refuse row, the
wall height it attaches to (measured on the photo, never copied), and the
pins that keep every one of them em dash until confirmed.
