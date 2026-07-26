# PROPOSAL — Part 2: "Add Dormer" mode + drag-to-adjust
Report-class, for Howard's ruling. Nothing wired. 2026-07-26.

## A. "Add Dormer" annotation mode — STATUS: ALREADY SHIPPED, ruled 7-25/26
The photo annotator carries MODE_DORMER (mirrors Add Gable): user taps
the 4 corners of the dormer front face → contractor-provenance quad,
tagged "TAPED (contractor quad)", W×KNEE derived, depth smart-default
1.5 ft (editable, synced with Field Verify), cheeks = height × depth,
guided-flow Step 7, drag-points refinement, never auto-injected into
money. As of today it also enters paired-feature reconciliation and
governs every view (cross-view pin). If Part 2 intends a SHEET-side
"Add Dormer" (placing a dormer on an elevation sheet where no photo
exists), that is NEW — proposed data model below covers it; otherwise
A is complete.

## B. Drag-to-adjust (sheets) — NEW, proposed
Interaction:
- On an elevation sheet (inline panel + full page), placed dormer bands
  and openings above the wall plate get a drag handle (vertical drag
  only — v-pos is the disputed axis; horizontal stays anchored to the
  measured center).
- Drag snaps to 1" increments; live readout "base 10'-9¾" above grade".
- Release = a HUMAN POSITION ENTRY: provenance tag
  "USER (sheet-dragged)", timestamped, upgradeable (a later tape entry
  outranks it), never overwrites the AI/contractor read — the prior
  read stays on the sheet as the flagged comparison
  ("photo-chain read 11'-2⅝" — reads disagree — flagged").
- Re-derives dependents: band top = base + knee; cheeks unchanged
  (depth-based); paired twin offered a "match twin LEVEL" one-tap
  (never silent); roofline bounds still clamp the drawn glyph.
Data model (estimate doc):
  "sheet_overrides": {
    "dormer:left": {"base_ft": 10.81, "src": "user_drag",
                     "at": iso, "prev": {"base_ft": 11.22, "src": "contractor_quad"}},
    "opening:left:W2": {"sill_in": 58, "src": "user_drag", "at": iso,
                         "prev": {"sill_in": 66, "src": "ai_read"}}
  }
Provenance ladder becomes: TAPED appendage > USER sheet-drag >
CONTRACTOR quad chain (pair-leveled) > AI chain. Money: none — v-pos
never prices; areas stay dimension-derived.
Pins before wiring: ladder order, prev-read preserved + flagged,
twin-level never silent, roofline bounds still apply, fixture sheets
byte-identical when no overrides exist.

## RULING REQUESTED
1. Confirm A is satisfied by the shipped photo tool (or order the
   sheet-side placement variant).
2. Approve B interaction + data model (drag = human position entry,
   ladder position, one-tap twin level)?
