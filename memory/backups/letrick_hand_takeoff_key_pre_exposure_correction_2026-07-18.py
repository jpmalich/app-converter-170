"""PHASE 3 GROUND TRUTH — Howard's sealed Letrick LP hand-takeoff answer key.
Composed BLIND (no reference to the app's LP takeoff — confirmed by Howard,
2026-07-13). Supersedes the letrick_hand_takeoff placeholder (backed up at
/app/memory/backups/letrick_hand_takeoff_placeholder_pre-supersede_2026-07-13.json).
Acceptance: per-line ±3%; composition absences are part of the key —
any J-channel / finish trim / coil line = composition FAIL regardless of totals.
Report protocol: against the key only; no reconciling either direction."""

LETRICK_HAND_TAKEOFF_KEY = {
    "estimate_number": "EST-191890",
    "composed": "2026-07-13",
    "inputs": {
        "raw_sqft": 2098.5,          # 21.0 squares raw
        "walls_gables_sqft": 1953.0, # front 483.8 + back 535.7 + stepped sides ~566.4 + gables ×0.7 = 367.5
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
    "lines": [
        {"item": "38 Series Lap 8\" x 16'", "qty": 255, "unit": "PCS",
         "derivation": "2,098.5 sqft raw = 21.0 sq +10% = 23.1 sq × 11 pcs/sq (6-7/8\" reveal) = 254.1 → 255 (mill basis pending finish selection)"},
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
