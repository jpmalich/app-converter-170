"""PHASE 3 GROUND TRUTH — Howard's sealed Letrick LP hand-takeoff answer key.
Composed BLIND (no reference to the app's LP takeoff — confirmed by Howard,
2026-07-13). Supersedes the letrick_hand_takeoff placeholder (backed up at
/app/memory/backups/letrick_hand_takeoff_placeholder_pre-supersede_2026-07-13.json).
Acceptance: per-line ±3%; composition absences are part of the key —
any J-channel / finish trim / coil line = composition FAIL regardless of totals.
Report protocol: against the key only; no reconciling either direction.

CLASS-1 GROUND-TRUTH CORRECTION (Howard, 2026-07-18 — backup at
/app/memory/backups/letrick_hand_takeoff_key_pre_exposure_correction_2026-07-18.py):
front eave height was DERIVED from 25 courses at a WRONG exposure (~4.30"),
not taped. Corrected to 25 × taped 4.25" = 8.854' (8'-10 1/4"). Basis:
internal consistency — back wall (28 × 4.25 = 9.92') already reconciled with
the taped exposure; ONE exposure now governs all walls. Dependents re-derived:
front area 478.1 (was 483.8), raw 2,092.8 (was 2,098.5), lap 254 (was 255).
Caught by Howard's as-built arithmetic (25 × 4.25). KEY-HYGIENE RULE applies
from this correction forward: every value carries basis TAPED or DERIVED
(formula stated) — see "bases"."""

LETRICK_HAND_TAKEOFF_KEY = {
    "estimate_number": "EST-191890",
    "composed": "2026-07-13",
    "corrected": "2026-07-18",
    "inputs": {
        "exposure_in": 4.25,         # TAPED — one exposure governs all walls
        "raw_sqft": 2092.8,          # 20.9 squares raw (was 2,098.5 pre-correction)
        "walls_gables_sqft": 1947.3, # front 478.1 + back 535.7 + stepped sides ~566.4 + gables ×0.7 = 367.5
        "chase_outer_sqft": 47.97,
        "chase_sides_sqft": 97.56,   # 2.58' × 18.91' × 2
        "eaves_lf": 108.0,           # 2 × 54
        "rakes_lf": 69.6,            # 4 × 17.4
        "fascia_rake_lf": 177.6,
        "perimeter_lf": 168.0,
        "starter_lf": 165.0,         # 168 − 3' entry; slider sits on starter
        "window_deductions": "none, per convention",
        "waste": 0.10,               # siding only; OSC/fascia = splice-and-round-up, no cushion
    },
    "bases": {
        # KEY-HYGIENE RULE (Howard 2026-07-18): TAPED = direct reading;
        # DERIVED = formula from taped inputs, formula stated.
        "exposure_in": {"basis": "TAPED", "note": "field tape, reconciles back wall 28 courses"},
        "front_height_ft": {"basis": "DERIVED", "formula": "25 courses × 4.25\" ÷ 12 = 8.854' (8'-10 1/4\")"},
        "back_height_ft": {"basis": "DERIVED", "formula": "28 courses × 4.25\" ÷ 12 = 9.917' (~9.92')"},
        "front_sqft": {"basis": "DERIVED", "formula": "54 × 8.854 = 478.1"},
        "back_sqft": {"basis": "DERIVED", "formula": "54 × 9.917 = 535.5 (key states 535.7 — rounding flag, key-hygiene audit)"},
        "raw_sqft": {"basis": "DERIVED", "formula": "walls_gables 1947.3 + chase_outer 47.97 + chase_sides 97.56 ≈ 2092.8"},
        "eaves_lf": {"basis": "DERIVED", "formula": "2 × 54 (54 TAPED, print-confirmed)"},
        "rakes_lf": {"basis": "DERIVED", "formula": "4 × 17.4 (17.4 TAPED)"},
        "fascia_rake_lf": {"basis": "DERIVED", "formula": "108 + 69.6 = 177.6"},
        "perimeter_lf": {"basis": "TAPED"},
        "starter_lf": {"basis": "DERIVED", "formula": "168 − 3 (entry; slider sits on starter)"},
    },
    "lines": [
        {"item": "38 Series Lap 8\" x 16'", "qty": 254, "unit": "PCS",
         "derivation": "2,092.8 sqft raw = 20.93 sq +10% = 23.02 sq × 11 pcs/sq (6-7/8\" reveal) = 253.2 → 254 (mill basis pending finish selection; was 255 pre-correction)"},
        {"item": "540 Series OSC 5/4\" x 6\" x 16'", "qty": 8, "unit": "PCS",
         "derivation": "4 house corners @ 1 stick + chimney 4 sticks (2 full-height edges ~18.9' + 2 above-roofline edges, ~55 LF total, splice-and-round-up). No cushion."},
        {"item": "440 Series 4/4\" x 4\" ISC", "qty": 2, "unit": "PCS",
         "derivation": "2 locations (chase wall junctions), 1 stick each, wall height"},
        {"item": "540 Series Trim 5/4\" x 4\" x 16'", "qty": 12, "unit": "PCS",
         "derivation": "10 windows 4-side + entry 3-side + patio 3-side"},
        {"item": "440 Series 4/4\" x 8\" x 16' fascia + rake", "qty": 12, "unit": "PCS",
         "derivation": "177.6 LF (eaves 2×54 + rakes 4×17.4), splice-and-round-up"},
        {"item": "LP Soffit", "qty": 108, "unit": "LF",
         "derivation": "eaves only, 108 LF at 12\" overhang (per the LP eaves-only ruling)"},
        {"item": "Starter rip stock", "qty": 165, "unit": "LF", "boards": 4,
         "derivation": "168 perimeter − 3' entry (slider sits on starter) → ceil(165 ÷ 48 LF/board) = 4 boards 38S 8\" lap"},
    ],
    "composition_absences": ["J-channel", "finish trim", "coil"],
}
