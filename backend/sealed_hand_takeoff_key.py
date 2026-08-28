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
(formula stated) — see "bases".

CHASE RATIFICATION AMENDMENT (Howard, 2026-07-19 — human ground truth,
ruled): the chimney chase PROJECTS from the back wall (CONFIRMED) and is
lap-clad (CONFIRMED). Dimensions TAPED (contractor tape 2026-07-19):
width 64" · depth 31" (proud of wall) · height 234-5/8" = 19'-6 5/8",
grade to cap. Supersedes "footprint untaped" and the prior ~18.91' chase
height. Entered via the appendage ratify machinery (appendage:back
height_ft/depth_ft, journey-logged); width rides this amendment only —
the dims machinery pin rejects width_ft (400) and pins are amended by
ruling, not silently.

ITEM-3 RATIFIED (Howard, ruled 2026-07-19 — area gate OPENED for this
ratification only, journey-logged): face-by-face TAPED chase derivation
enters the key's area story. chase_outer_sqft 47.97 → 51.37 (5.3333' ×
9.6321' outboard-above-roofline), chase_sides_sqft 97.56 → 101.02
(2.5833' × 19.5521' × 2); wall-abutting face carried by the back wall's
gross strip (photo-path gross convention — no deduction, no double
count). raw_sqft 2,092.8 → 2,099.7; lap 254 → 255 (key convention:
+10% waste, 11 pcs/sq). OSC unchanged 8 (POOLED convention SEALED as
standing contractor-spec, with placement rule: full sticks at corner
BOTTOMS, spliced remnants upper portion only, cut from shared sticks);
ISC unchanged 2.

GABLE RE-SEAL TO THE TRIANGLE (Howard ruled 2026-08-27, SEND-138 — after
the SEND-137 gable ruling retired the 0.70 factor in software): the sealed
gable total was written as w × h × 0.70 = 367.5. THE SEALED NUMBER IS NOW
THE SAME WALLS AT ½ × width × rise:

    two gable ends, one per side face, each 30.0' wide × 8.75' rise
    ½ × 30.0 × 8.75 = 131.25 per end → 262.5 TOTAL
    (= 367.5 × 0.5/0.7, Howard's own arithmetic, to the penny)

The two faces and both figures are confirmed by the key's OWN internal
evidence, not by an outside read: rakes_lf 69.6 = 4 × 17.4, and
√(15.0² + 8.75²) = 17.37 ≈ 17.4 — four rakes means two gable ends, and the
rake length reproduces the 15' half-width and the 8.75' rise.

**367.5 IS RETIRED AS A TARGET. NOTHING TUNES TOWARD IT.**

DEPENDENTS RE-DERIVED, per this key's own KEY-HYGIENE precedent (the
2026-07-18 correction re-derived front area, raw and lap) and under the
standing ruling that a computed total may not outlive a superseded input:
  gables            367.5 → 262.5   (−105.0)
  walls_gables_sqft 1947.3 → 1842.3 (the stated total less the same 105.0;
                    the pre-existing 0.4 rounding flag on 535.7 is left
                    exactly as it was — no new arithmetic is invented here)
  raw_sqft          2099.7 → 1994.7 (1842.3 + 51.37 + 101.02 = 1994.69)
  lap               255 → 242 PCS   (19.947 sq +10% = 21.94 sq × 11 pcs/sq
                    = 241.36 → 242)
Nothing else in the key reads the gable: eaves/rakes/fascia/soffit/starter/
OSC/ISC/trim are LF- and count-driven and are UNCHANGED."""

SEALED_HAND_TAKEOFF_KEY = {
    "estimate_number": "EST-191890",
    "composed": "2026-07-13",
    "corrected": "2026-07-18",
    "amended": "2026-07-19",  # chase ratification (see docstring)
    "inputs": {
        "exposure_in": 4.25,         # TAPED — one exposure governs all walls
        "raw_sqft": 1994.7,          # RE-SEALED 2026-08-27 (gable to the triangle): 1842.3 + 51.37 + 101.02
        "walls_gables_sqft": 1842.3, # front 478.1 + back 535.7 + stepped sides ~566.4 + gables 262.5
        "gables_sqft": 262.5,        # RE-SEALED 2026-08-27 — the sealed gable total: 2 ends × ½ × 30.0' × 8.75'
        "chase_outer_sqft": 51.37,   # item-3 RATIFIED: 5.3333' × 9.6321' (was 47.97 composed)
        "chase_sides_sqft": 101.02,  # item-3 RATIFIED: 2.5833' × 19.5521' × 2 (was 97.56 composed)
        "chase_width_in": 64.0,      # TAPED 2026-07-19 (ratification amendment)
        "chase_depth_in": 31.0,      # TAPED 2026-07-19 — proud of wall
        "chase_height_in": 234.625,  # TAPED 2026-07-19 — 19'-6 5/8" grade to cap
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
        "raw_sqft": {"basis": "DERIVED", "formula": "walls_gables 1842.3 + chase_outer 51.37 + chase_sides 101.02 ≈ 1994.7 (gable re-seal 2026-08-27; was 2099.7 on the 0.70-era gable)"},
        "gables_sqft": {"basis": "DERIVED", "formula": "2 gable ends (one per side face), each ½ × 30.0' width × 8.75' rise = 131.25 → 262.5. Faces and figures confirmed by this key's own rakes_lf: 4 × 17.4 and √(15.0² + 8.75²) = 17.37. RE-SEALED 2026-08-27 (Howard) — 367.5 (w×h×0.70) is retired as a target"},
        "chase_outer_sqft": {"basis": "DERIVED", "formula": "chase width 5.3333' × above-roofline 9.6321' (19.5521 − 9.92) = 51.37 — item-3 ratified 2026-07-19"},
        "chase_sides_sqft": {"basis": "DERIVED", "formula": "2 × depth 2.5833' × height 19.5521' = 101.02 — item-3 ratified 2026-07-19"},
        "eaves_lf": {"basis": "DERIVED", "formula": "2 × 54 (54 TAPED, print-confirmed)"},
        "rakes_lf": {"basis": "DERIVED", "formula": "4 × 17.4 (17.4 TAPED)"},
        "fascia_rake_lf": {"basis": "DERIVED", "formula": "108 + 69.6 = 177.6"},
        "perimeter_lf": {"basis": "TAPED"},
        "starter_lf": {"basis": "DERIVED", "formula": "168 − 3 (entry; slider sits on starter)"},
        "chase_width_in": {"basis": "TAPED", "note": "contractor tape 2026-07-19 — chase ratification amendment (Howard)"},
        "chase_depth_in": {"basis": "TAPED", "note": "contractor tape 2026-07-19 — proud of back wall; matches composed sides basis 2.58'"},
        "chase_height_in": {"basis": "TAPED", "note": "contractor tape 2026-07-19 — 234-5/8\" = 19'-6 5/8\" grade to cap; supersedes ~18.91'. Area dependents re-derived per item-3 ratification (2026-07-19)"},
    },
    "lines": [
        {"item": "38 Series Lap 8\" x 16'", "qty": 242, "unit": "PCS",
         "derivation": "1,994.7 sqft raw = 19.947 sq +10% = 21.94 sq × 11 pcs/sq (6-7/8\" reveal) = 241.36 → 242 (gable re-seal to the triangle 2026-08-27; was 255 on the 0.70-era gable, 254 pre-ratification)"},
        {"item": "540 Series OSC 5/4\" x 6\" x 16'", "qty": 8, "unit": "PCS",
         "derivation": "4 house corners @ 1 stick + chimney 4 sticks (2 full-height edges 19.5521' + 2 above-roofline edges 9.6321', pooled 58.37 LF → ceil(58.37/16) = 4 — POOLED convention SEALED 2026-07-19 with placement rule: full sticks at corner bottoms, spliced remnants upper portion only). No cushion."},
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
