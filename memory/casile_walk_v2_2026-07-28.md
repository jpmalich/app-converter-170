# JON CASILE — WALK v2 (2026-07-28, post corner correction)
**For Howard's FINAL clearance. NOTHING PRINTS until you clear v2 — and now the quote surface enforces it: PRINT-BLOCKED gates send + PDF by construction.**

## WHAT CHANGED FROM v1 (one delta, named)
Your re-book-check: the house has **14 outside corners, not Hover's 20** — the extras are returns/chase corners that take no posts (Hover's own >12 sanity warning had called it). Entered via the standing correction machinery: `corner_locators` closed with **human-provenance count 14**; Hover's 20 preserved on the line as the flagged comparison. OSC re-derives per-corner per Q13 from the corrected count.
- The OSC line now reads: *"Hover 14 corner(s) × per-corner whole-stick round-up (10.02' each, min 1 pc/corner — Q13) — HUMAN count 14 (report read 20, flagged comparison — correction ruled 2026-07-28)"*
- Reopening the flag restores the report count (pinned by test, both directions).

## HEADER
- **EST-523061** · Jon Casile · 261 Haugh Dr, Pittsburgh, PA 15237
- LP SmartSide · board & batten · Contractor tier · waste 30% (Q17 holds) · margin 30% · tax 7%
- Basis: Hover report 7c6194d4… (facade scope wrap 2,064 ft²; measured soffit breakdown 216/164/83) + **human corner correction (14)**

## MATERIALS — v2 (deltas vs v1 named; v1 deltas vs v3 unchanged)
| Line | v1 | **v2** | Δ | Why | Unit mat | Line total |
|---|---:|---:|---:|---|---:|---:|
| 38 Series 4'×10' Panel | 68 | 68 | — | | 137.94 | 9,379.92 |
| 440 4/4"×8" fascia+rake | 21 | 21 | — | | 56.43 | 1,185.03 |
| 540 5/4"×4" (wrap 33 + frieze 23 + ISC 6) | 62 | 62 | — | ISC count not corrected (24→ per-corner 6 unchanged; correction was OUTSIDE corners only) | 34.30 | 2,126.60 |
| 190 Series battens | 194 | 194 | — | heights still untaped — one-tap field stands ready | 19.66 | 3,814.04 |
| **540 OSC 5/4"×6"** | **20** | **14** | **−6** | **HUMAN count 14 governs Q13 (Hover 20 flagged comparison)** | 271.69 | **3,803.66** |
| 38 Soffit Vented / Closed | 14 / 11 | 14 / 11 | — | measured breakdown basis | 85.83 / 73.50 | 1,201.62 / 808.50 |
| Touch up kits / OSI caulk | 2 / 9 | 2 / 9 | — | Q15 | 60.96 / 14.03 | 121.92 / 126.27 |
| J blocks / Mini Splits | 9 / 2 | 9 / 2 | — | | 57.14 / 80.00 | 514.26 / 160.00 |
| Gutter chain (unchanged set) | — | — | — | | | 1,596.65 |
| Caps ×4 + clean-up | qty per counts | same | — | labor $0 pending (v3) | 0.00 | 0.00 |
| Tear-Off / Dumpster | qty 0 PENDING | qty 0 PENDING | — | Q1 — quantity + labor yours | — | 0.00 |

## THE WALK — v2
| Step | v3 (pre-rulings) | v1 (Q1–Q17) | **v2 (corner-corrected)** | v2 − v1 |
|---|---:|---:|---:|---:|
| **MATERIALS** | 20,025.74 | 26,468.61 | **24,838.47** | −1,630.14 |
| **TAX** (7% mat) | 1,401.80 | 1,852.80 | **1,738.69** | −114.11 |
| **LABOR** (all pending @ $0) | 0.00 | 0.00 | **0.00** | — |
| **BASE** | 21,427.54 | 28,321.41 | **26,577.16** | −1,744.25 |
| **HOMEOWNER** (÷ 0.70) | 30,610.77 | 40,459.16 | **37,967.38** | **−2,491.78** |

## WHAT PRINT-BLOCKED SHOWS ON THIS QUOTE RIGHT NOW
The quote header renders **"PRINT-BLOCKED: N items"** and send + PDF stay disabled until the readiness list clears (authorized 2026-07-28 — supersedes the 2026-07-23 soft-only ruling on the homeowner surface; the estimate-page readiness panel stays informational). Standing blockers on EST-523061: the 5 labor-pending rows (cap window ×32 is the big one), Tear-Off + Dumpster quantities, unpriced money-surface rows on the secondary tabs, and the open `batten_wall_heights` flag (tape the walls via the one-tap field).

*Pinned: `test_casile_closeout.py` (OSC 14 + note both ways, walk figures), `test_flag_checklist.py::TestCornerCountCorrection` (close→14, reopen→20, bad count 422), `test_labor_conventions_readiness.py::test_quote_gate_is_hard_print_block`.*

---
**CLEARED (Howard, 2026-07-28): WALK v2 CLEARED at $37,967.38** — book-checked
twice over (his corner count drove the final delta): materials-true,
labor-honest, print-blocked by construction until the contractor inputs land.
Recorded per item-1(g) of the 2026-07-28 reconciliation order.
