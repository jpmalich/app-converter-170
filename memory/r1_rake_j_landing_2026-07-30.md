# R1 LANDED — RAKE J = 2 PASSES + NAMED DELTAS · R2 SEALED · R3 TRUNCATED (2026-07-30)

## R1 — SOFFIT-J RAKE TERM FIXED (2×→1×), DERIVATION+COMMENT PINNED TOGETHER
Ruling: exactly 2 J passes per rake — wall pass on the wall J-Channel line
(vinyl accessories), ONE rake pass on Soffit J (soffit category). The
finish-trim comment was CORRECT; the derivation was wrong.
- Emitter: routes/hover.py soffit-J extract now (eaves + rakes) ÷ 12.5.
- ONE marker ("R1 ruled 2026-07-30" / RAKE_J_DOCTRINE) lives in the doctrine
  constant, the finish-trim exclusion docstring, the wall-J comment and the
  emitted line note. Pin file: tests/test_rake_j_passes_2026_07_30.py —
  behavioral triangle (wall-J rake pass == 1, soffit-J rake pass == 1,
  finish-trim rake pass == 0, total == 2) + marker coupling + the note must
  NAME the pre-ruling quantity ("pre-ruling 2×rakes rule gave 31 pcs, now
  20") so the move can never arrive silently inside a rebuild.
- LETRICK HARNESS LEFT FROZEN, NAMED: lp_truck_reconcile.py derives Soffit J
  by the historical "2× eave rule on file" (2×108÷12.5=18, matched the real
  truck). It is September evidence of the rules THEN, not a live money
  emitter — rewriting it to match R1 would falsify the record. Flagged for
  Howard only if he wants a supersession note added.

## R1 DELTA TABLE — EVERY AFFECTED LIVE ESTIMATE (basis: stored fascia LF = eaves+rakes)
| Estimate | kind | E+R LF | OLD | NEW | Δpcs | Δ$ mat @7.28 | status |
|---|---|---|---|---|---|---|---|
| 3 degree vinyl 7-28-26 8am | siding | 628 | 76 | 51 | −25 | −$182.00 | **ACTIVE MONEY (vinyl job)** |
| 3 degree rd | lp_smart | 628 | 84 | 51 | −33 | −$240.24 | alternate vinyl tab (LP job) |
| 3 degree rd 7-28-26- 8am | lp_smart | 628 | 84 | 51 | −33 | −$240.24 | alternate tab |
| 3 degree rd 7-28-26 1 pm | lp_smart | 628 | 76 | 51 | −25 | −$182.00 | alternate tab |
| Jon Casile | lp_smart | 321 | 37 | 26 | −11 | −$80.08 | alternate tab (LP quote $38,139.13 UNTOUCHED) |
| (unnamed) ×2 | lp_smart | 321 | 44/41 | 26 | −18/−15 | −134.68/−109.20 | alternate tabs |
| doug jones | lp_smart | 171 | 20 | 14 | −6 | −$43.68 | alternate tab |
| 7-26-26-2pm | lp_smart | 161 | 20 | 13 | −7 | −$50.96 | alternate tab |
| TEST_ ×2 | lp_smart | 163/164 | 18 | 14 | −4 | −$29.12 | alternate tabs |
Stored lines are NOT mutated — each estimate re-derives on its next rebuild
and the line note names old→new on that estimate's own numbers.

## R2 — SEALED: A SHARED PRODUCT CONSUMED FOR DIFFERENT PURPOSES IS
## DIFFERENT LINES (physical fact — coil colours differ; never summed).
shared-product_id order layer: NOT BUILT, removed from the ID-binding scope
(−1–1.5d; ID-binding stands at 3–4d + 0.5d metadata).

### R2 FOLLOW-ON (REPORT ONLY): coil lines carrying the wrapped component's colour
YES — and with ZERO new inputs. Job Info MATERIAL COLORS already carries
per-estimate `window_wrap_color` and `soffit_fascia_color` (live fields on
every estimate doc, contractor-set).
- Opening-wrap coil line (Siding Accessories) ← window_wrap_color
- Fascia-wrap coil line (Vinyl Soffit) ← soffit_fascia_color
Shape: emitter-sourced NOTE + colour chip on the line ("wraps openings —
window-wrap colour: Musket Brown"), never welded into the SKU name (naming
seal). Blank colour → "colour not set — set in Job Info" instead of silence.
Size: ~0.5 day (note emitters + material-list display + pins). Same
mechanism extends to PVC/G8 manual rows for free. Awaiting go.

## R3 — MESSAGE TRUNCATED
Howard's ruling 3 arrived as the headline "COIL ROUNDS UP — AND SO DOES
EVERYTHING" with no body, and nothing after it ("ALL OPEN ITEMS CLOSED" was
promised — rulings on F1–F8, strip-list go, Inside Corners, register-#8
renames, 540 readback did not arrive). NOTHING BUILT on rounding: scope
(coil only vs every fractional line, quote vs order layer, the parked
0.5-retires item) cannot be guessed. Re-send requested.
