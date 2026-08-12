# BASELINE 53 BURN-DOWN + PER-RUN VS PER-ESTIMATE CLASSIFICATION (2026-08-11 send-5)

Two reports Howard ordered in send-5, ranked by expected likelihood of
"the next thing I walk into is already sitting here."

---

## §1 · BASELINE 56 — SORTED BY LIKELIHOOD IT IS A REAL GATED SURFACE

Ranked P0 (real surface, contractor could walk into it) → P3 (internal
helper / modal-open / input validation, safe as-is). "P0/P1" are the
burn-down targets; P2/P3 stay grandfathered.

### P0 — HIGHEST PROBABILITY REAL SURFACES (5 entries)

These render an estimate-page-visible surface conditionally. Same
shape as the four Howard walked into.

| # | Surface | Snippet | Why P0 |
|---|---------|---------|--------|
| B1 | `SidingProfileChip.jsx` — `if (!carrier) return null;` | siding-profile chip | Renders the profile inline on line rows. When `carrier` is missing (blueprint/HOVER-sourced lines), the chip vanishes silently. Same class as S3 (vinyl profile picker). |
| B2 | `PhotoFillinGateBanner.jsx` — `if (!item) return null;` | photo-fillin gate | The banner tells the contractor which item needs a photo. When `item` is null (all items filled?), it disappears — but if a fill-in is required and `item` is briefly null while the request is in-flight, the banner is invisible when the contractor most needs to know. |
| B3 | `OpeningsReviewCard.jsx` — `if (!review \|\| !review.total) return null;` | openings review card | The card summarizes photo-openings review status. If the review is not yet computed, the card vanishes — no chip, no "reviewing…" state. |
| B4 | `CompositionTrace.jsx` — `if (!familyEntries.length) return null;` | LP composition trace | The trace explains how the LP-smart engine derived its takeoff. Empty familyEntries = a state the contractor should NEVER see on an lp_smart estimate — but the surface vanishes instead of speaking. |
| B5 | `FinalJobSurface.jsx` — `if (!gates) return null;` | final-job gate panel | The whole quote-gate panel disappears when `gates` is null. Should speak "gates loading" or "no gates configured." |

### P1 — LIKELY WORTH REVIEW (8 entries)

Content surfaces that might benefit from a chip.

- `AIMeasureButton.jsx` × 2 — "model history" and "location count" sub-panels; the model-history diff panel silently vanishes when history <2 entries (contractor may want "no comparison yet")
- `CatalogSyncBanner.jsx` — banner disappears when dismissed OR no changes; the "no changes" case is fine, but the dismissal state has no way back short of refresh
- `HoverImportButton.jsx` × 2 — internal elevs/tabLines guards inside the RESULT view; same class as S3/S4 (modal-only) already handled
- `MezzoPanel.jsx` × 2 — otherDef / rowAdders empty states
- `VisualAuditPanel.jsx` × 2 — evidence + items empty states (probably OK because the panel wraps the empty branch)

### P2 — LOADING / EMPTY-DATA (16 entries)

Loading/skeleton states. Chip would be nice but not load-bearing.

`GuidedCaptureWizard.jsx` (4), `PhotoAnnotateModal.jsx` (3), `HouseModel3D.jsx` (4), `ProfileAnnotator.jsx` (4), `SectionAccordion.jsx` (1)

### P3 — INTERNAL / MODAL-OPEN / INPUT VALIDATION (27 entries)

Safe by construction. `if (!open) return null;` modal-close, nested
render helpers, hooks that short-circuit on invalid props.

`BulkApplyConfirm.jsx`, `ElevationCompareModal.jsx`, `ElevationDrawing.jsx` (internal helpers), `PhotoMeasureButton.jsx`, `ProfileAnnotator.jsx` (internal), `ItemHelpButton.jsx`, `StickyBar.jsx`, `TapeCheckPanel.jsx` (5 hooks + verdict guards), `VeroPanel.jsx`, `TakeoffReconCard.jsx` (5), `BlueprintReadBackCard.jsx` (modal-only, covered by S1), `pages/BrandingAdmin.jsx`, `pages/EstimateEditor.jsx`, `pages/ISSEstimateEditor.jsx`, `pages/SourceSheets.jsx`

### BURN-DOWN PLAN

- **P0 batch (5 surfaces)**: build the chip + retire from baseline. Estimated 30 minutes each ≈ **2.5 hours total**. Should ship in the next 1–2 sessions.
- **P1 batch (8 surfaces)**: audit + case-by-case in a single ~1-hour pass.
- **P2**: skip unless a specific case bites. The detector's future-facing pin covers regression on any new surface.
- **P3**: leave in baseline; note as "audited, safe by construction, no chip needed."

**No new work commits P0/P1 to today** — Howard ordered Phase 2 built
first. This is the roadmap for the next-next session.

---

## §2 · PER-RUN VS PER-ESTIMATE CLASSIFICATION

Howard's send-5 ruling: "Go through the three dialogs and classify
every surface as PER-RUN or PER-ESTIMATE. The profile picker was
per-estimate and misfiled — that is exactly why it was unreachable.
Accent injection, same. Trade specs and colours probably too."

Format: SURFACE · CURRENT MOUNT · CLASSIFICATION · MOVE?

### BlueprintMeasureButton.jsx (Blueprint run dialog)

| Surface | Currently | Class | Move? |
|---------|-----------|-------|-------|
| Read Blueprints upload zone | modal | **PER-RUN** — the file+config for ONE read | STAY |
| Read status / progress indicator | modal | **PER-RUN** | STAY |
| Blueprint Read-Back card (planes/corners/porch) | modal | **PER-RUN** — the run's read | STAY |
| Takeoff Preview (recon card) | modal | **PER-RUN** — this run's proposed takeoff | STAY (with 8-11 send-3 fix: card names the run identity) |
| Apply Takeoff button + refusal chip | modal | **PER-RUN** — this run's apply | STAY |
| EL-1..EL-4 entry links | ALREADY MOVED (send-3) — mount both estimate-tile and preview | **PER-ESTIMATE** (any completed read) | DONE |
| Accent injection (S4) | modal | **PER-ESTIMATE** — accents ride on the estimate's takeoff, not on ONE run | **MOVE** (chip on tile already; the injection UI itself could live in an "Estimate accents" persistent panel on JobInfoPanel) |
| Profile annotator | modal | **PER-ESTIMATE** — profiles apply to the ESTIMATE's material choices | **MOVE** (chip on HOVER tile already; the annotator itself belongs on JobInfoPanel as a persistent per-line control) |
| Model comparison history | modal | **PER-ESTIMATE** — the comparison across runs | **MOVE** to a persistent "Read history" chip on the tile |

### AIMeasureButton.jsx (Photo run dialog)

| Surface | Currently | Class | Move? |
|---------|-----------|-------|-------|
| Photo upload + capture | modal | **PER-RUN** | STAY |
| Reference dimension entry | modal | **PER-RUN** | STAY |
| Wall/height/siding-% inputs | modal | **PER-RUN** | STAY |
| Photo annotations (dormer/opening tags) | modal | **PER-RUN** (per-photo → belongs with the run) | STAY |
| Guided capture wizard | modal | **PER-RUN** | STAY |
| Model history / diff panel | modal | **PER-ESTIMATE** — across runs | **MOVE** (same class as Blueprint's history) |
| Vinyl siding profile picker (S3) | modal | **PER-ESTIMATE** — the profile applies to every line on the estimate | **MOVE** (chip landed on tile 8-11 send-4; the picker itself belongs in JobInfoPanel spec area) |
| Start-over / delete session | modal | **PER-RUN** (that run's session) | STAY |

### HoverImportButton.jsx (HOVER dialog)

| Surface | Currently | Class | Move? |
|---------|-----------|-------|-------|
| HOVER PDF upload | modal | **PER-RUN** | STAY |
| Elevation-face selector (include/exclude) | modal | **PER-RUN** | STAY |
| Restore HOVER (past runs) | modal | **PER-ESTIMATE** — jumps to a prior run | **MOVE** to an estimate-level "HOVER history" chip |
| Waste-percent reset preview | modal | **PER-RUN** — this upload's implied waste reset | STAY |

### THE THREE MOVES THAT MATTER

Ordered by likelihood the misfile is why the surface hides:

1. **Vinyl profile picker → JobInfoPanel spec area** (per-line profile control that persists on the estimate page).
   - Class-before: photo door only, modal-only. S3 chip already speaks the state.
   - Effort: medium (~2 hours). The picker itself is a self-contained control; wiring per-line assignment requires touching the line-editor UI.

2. **Accent injection → JobInfoPanel accents panel** (per-elevation accent control that persists).
   - Class-before: run-dialog only.
   - Effort: medium (~2 hours). The PerElevationBreakdownCard has the injection logic; moving it out of the modal is a re-mount.

3. **Model comparison history → persistent tile-chip** (both dialogs).
   - Class-before: run-dialog only.
   - Effort: small (~45 min). Just a chip that renders count-of-runs and expands to show the diff.

**Not shipped today.** These are moves, not new features. Howard ordered
Phase 2 built first. This report is the roadmap for the next session.

### THE REST STAY WHERE THEY ARE

- All PER-RUN surfaces belong inside their dialogs. Hoisting them
  would reintroduce the "which run am I looking at?" ambiguity that
  the run-identity print on the card fixed.
- The 8-11 send-3 fix (run ID + applied/not-applied on every entry
  chip) is the mechanism that lets PER-RUN surfaces stay in the
  dialog without ambiguity.

---

## §3 · PURITY

The classifications above are EVIDENCE (from reading the JSX and
naming what each surface serves — the run's identity vs the
estimate's identity). Never constants, never fallbacks. If any of
these classifications turn out wrong on inspection (e.g., a surface I
called PER-ESTIMATE was actually PER-RUN by design), the fix is to
report the disagreement in the next session, not to force it into
the wrong class.
