# SEND-109 REPORT — RULING 4 PREDICTIVE CHECK · TAPE-ENTRY NUDGE · CONFIRMATIONS
2026-08-22 · QUANTITIES ONLY. Stamp appended at the end after the clean run.

---

## 0. CONFIRMATIONS (rulings 1–3, executed)

- **The run-identity fix TRAVELS.** It is code, not data — `routes/hover.py`
  (`hover-{run12}-{profile}-{est8}`, commit 3697e35) ships with the codebase;
  the live published version gets it on the next publish. Existing stamped
  docs keep their old ids (the resolver falls back estimate-scoped), so
  nothing live breaks on arrival.
- Casile's four refused rows: UNTOUCHED, as ruled.
- No inverted 423 guard: NOT BUILT, as ruled.
- Catalog test onto a copy: DONE — `test_company_overrides_merge_into_sheet`
  now copies the company + catalog to a disposable pair (fresh id, reminted
  invite_code), writes the override on the COPY, loads the sheet for the
  copy, deletes both. The real company's catalog is never written.

## 1. RULING 4 — THE SOFFIT PREDICTIVE CHECK, ALL EIGHT FACES

Question: does the measured wall-line-top offset PREDICT each face's width
residual? Method: implied % = offset ÷ calibration gap (the pair the width
actually scales from: TOP OF PLATE → FIRST FLOOR, at that face's own
scale); predicted residual = implied % × face width. SIGN convention: the
wall-line top sits ABOVE the plate datum on every measured face, so the
wall-line pair is LONGER → if it were truth, current widths are OVERSTATED
→ every predicted residual is POSITIVE (overshoot). Widths re-derived from
the stamped propose linework (front 54.71 verified from px arithmetic:
42.48 x-% × 34.56 px/% ÷ 26.83 px/ft). Actual residual = read − sealed.

### LETRICK (sealed: front/rear width 54.00 · side depth 30.00)

| face | offset (ft) | gap (ft) | implied % | predicted (ft) | actual (ft) | difference | sign |
|---|---|---|---|---|---|---|---|
| front | +0.03 | 9.08 | 0.33% | **+0.18** | **+0.71** (54.71 read) | −0.53 | match |
| rear | +0.06 | 9.92 | 0.60% | **+0.33** | **+0.65** (54.65 wall-only) | −0.32 | match |
| left | +0.11 | 9.08 | 1.21% | **+0.36** | **−0.60** (29.40 wall-only) | +0.96 | **INVERTED** |
| right | +0.17 | 9.08 | 1.87% | **+0.56** | **−0.35** (29.65 wall-only) | +0.91 | **INVERTED** |

### BONI (all four faces)

| face | offset | gap | note |
|---|---|---|---|
| front / rear / left / right | NOT MEASURABLE | — | no resolved wall-line top (datum/band rectangles carry no traced wall outline), no verified scale to express an offset in feet, and no sealed width to residual against. Nothing to check, nothing confirmed. |

### VERDICT: THE OFFSET DOES NOT PREDICT THE RESIDUALS — 0 OF 4 MEASURABLE FACES.

- **The sides invert the sign.** The largest offsets (left +0.11, right
  +0.17) predict the largest OVERSHOOTS; the sides actually run UNDER
  (−0.60, −0.35). Per the mandate: right magnitude class, wrong sign — a
  different effect of similar size, NOT a match. Baking it in would run
  the correction the wrong way on exactly the faces where it is biggest.
- **Front/rear match the sign but not the magnitude** — predicted +0.18 /
  +0.33 against actual +0.71 / +0.65 (2–4× short). The offset explains at
  most a quarter to a half of the front/rear overshoot, and nothing it
  explains survives the side inversion as one cause.
- Your worked example resolved: front would need a 0.13-ft offset to carry
  its +0.71; the measured front offset is 0.03 ft. Coincidence, not cause.

**THEREFORE: the calibration pair does NOT move. The current TOP OF
FOUNDATION → TOP OF PLATE pair now stands ON EVIDENCE — the predictive
check ran and failed to predict — not on the offsets being small. The
~0.5-ft residual STAYS OPEN**, and it leaves this check with a sharper
shape than it entered: front/rear read OVER (+0.7ish), sides read UNDER
(−0.4 to −0.6) — opposite signs on perpendicular axes. A y-calibration
error cannot do that (it moves every width the same way); the cause lives
in the x-ruler or in what the silhouette includes per axis (fence posts /
label edges / fragment joining differ between length faces and depth
faces). That is the next place to look, reported as a finding, nothing
adjusted toward the sealed figures.

## 2. THE TAPE-ENTRY NUDGE (the refusal coach reaching Ruling V's material)

Built and verified live:
- `TapeNudgeCard` renders on any estimate whose lines carry a Ruling-V
  refusal (`not_derivable_code = RULING_V_NO_VERIFIED_HEIGHT`, with a
  section fallback for rows stored before the code existed). It names the
  refusing rows and says what one tape does. data-testids:
  `ruling-v-tape-nudge`, `tape-nudge-face-select`, `tape-nudge-input`,
  `tape-nudge-check-btn`, `tape-nudge-echo`, `tape-nudge-commit-btn`.
- Doctrine held: ECHO BEFORE COMMIT — "Check tape" parses through the real
  parse door and shows `9'-2" = 9.1667 ft` before anything lands. Commit
  posts the tape through the real door (FIRST FLOOR → TOP OF PLATE band),
  then re-derives through `/rederive`, then refreshes.
- VERIFIED END TO END ON A DISPOSABLE CLONE (the real Casile was read
  only; its four refusals stand): tape 9'-2" on front → re-derive →
  all four rows un-refuse with the basis NAMED on the row — drop
  "12 LF (verified: taped_human 9.1667 ft, front — max of 1 verified,
  never averaged)" → Downspout 10 sticks · Mitre 19 · Pipe Clips 24 ·
  Sealant 11 tubes. Refusal → tape → priced, one field tape.

## 3. FOUND WHILE BUILDING IT — THE SILENT-STRIP CLASS RECURRED (fixed)

The client merge layer (`useEstimate.js`) rebuilt line objects on every
load and DROPPED the refusal trio (`not_derivable`, `_reason`, `_code`)
while coercing a refused row's qty null → 0 — the next autosave would have
written that loss back to the server, silently erasing refusal provenance
(the sealed 2026-07-31 class, merge layer, recurred on the new fields).
Fixed: the trio rides the merge verbatim and a refused row keeps qty null.
Side effect repaired for free: the quote surface's refused-lines filter
(`calc.js`) had been reading a field the merge always stripped — it now
actually sees refusals.

## STANDING RULES HELD
No cross-drawing evidence · no estimate influences another · no job names
in code · model heights hypothesis-only · EST-886440 PROTECTED · 423 on
every derived write · purity pin holds · quantities only, no dollars.

## STAMP
(appended after the clean run)
