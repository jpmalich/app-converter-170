// OPTIMISTIC-WRITE REGISTRY (Howard ruled 2026-08-11 send-4).
//
// Every optimistic UI write in the app declares itself here. The
// detector at backend/tests/test_optimistic_write_detector_2026_08_11.py
// fails the build if any component mutates local state within 25 lines
// before an api.put/post/patch/delete WITHOUT either:
//   - importing writeThrough (retires the site to the helper contract), or
//   - being registered here as UNCONDITIONAL_SAFE (post-response
//     updates wrapping the await's data — Class Beta from the audit).
//
// Adding a new optimistic write? DECLARE IT HERE. This is rung-4:
// the wrong behaviour becomes unrepresentable — the build fails
// unless someone has thought about rollback on refusal.
//
// See memory/optimistic_ui_audit_2026-08-11.md for the class table.

/**
 * @typedef {object} OptimisticWriteEntry
 * @property {string} id — unique id (kebab-case).
 * @property {string} component_path — repo-relative path.
 * @property {string[]} fields — the local fields mutated optimistically.
 * @property {"paints-success" | "silently-reverts" | "names-refusal"} refusal_class_before — the class BEFORE routing through writeThrough (documentation).
 * @property {string} refuse_chip_testid — the testid the chip renders with when the write refuses.
 * @property {"routed" | "unconditional_safe" | "pending"} status — how this site is retired.
 * @property {string} [notes]
 */

/** @type {OptimisticWriteEntry[]} */
export const OPTIMISTIC_WRITES = [
  // W1 — Howard's exact 2026-08-11 case.
  {
    id: "blueprint-apply-lines",
    component_path: "components/estimate/BlueprintMeasureButton.jsx",
    fields: ["lines", "vero_openings", "mezzo_openings",
             "hover_measurements"],
    refusal_class_before: "paints-success",
    refuse_chip_testid: "bp-apply-refusal-chip",
    status: "routed",
    notes: ("Howard 2026-08-11: the 8-11 apply against EST-886440 was "
            + "refused with 423 but the local update painted 'applied'. "
            + "First site routed through writeThrough."),
  },
  // W2 — waste_pct spec change fires a rederive.
  {
    id: "settings-row-waste-pct",
    component_path: "components/estimate/SettingsRow.jsx",
    fields: ["waste_pct", "lines"],
    refusal_class_before: "paints-success",
    refuse_chip_testid: "waste-refusal-chip",
    status: "pending",
    notes: ("The waste chip flips locally before save + rederive fire. "
            + "On refusal today, waste chip stays new; recomputed line "
            + "qty stays wrong until refresh."),
  },
  // W3 — HOVER import resets waste_pct.
  {
    id: "hover-import-reset-waste",
    component_path: "components/estimate/HoverImportButton.jsx",
    fields: ["waste_pct"],
    refusal_class_before: "paints-success",
    refuse_chip_testid: "hover-import-refusal-chip",
    status: "pending",
  },
  // W4 — AI measure session delete.
  {
    id: "ai-measure-session-clear",
    component_path: "components/estimate/AIMeasureButton.jsx",
    fields: ["pendingSessionMeta"],
    refusal_class_before: "paints-success",
    refuse_chip_testid: "ai-measure-session-refusal-chip",
    status: "pending",
  },
  // W5 — ISS applied-lines write.
  {
    id: "iss-apply-hover-lines",
    component_path: "pages/ISSEstimateEditor.jsx",
    fields: ["lines"],
    refusal_class_before: "paints-success",
    refuse_chip_testid: "iss-apply-refusal-chip",
    status: "pending",
  },
  // W6 — post-response update inside settings save (Class Beta target
  // shape; documented so future refactors do not misclassify it).
  {
    id: "settings-row-spec-save-post-response",
    component_path: "components/estimate/SettingsRow.jsx",
    fields: ["lines"],
    refusal_class_before: "names-refusal",
    refuse_chip_testid: "n/a",
    status: "unconditional_safe",
    notes: ("Update runs INSIDE the response block — if the await "
            + "throws, no optimistic state paints. This is the target "
            + "shape (Class Beta)."),
  },
];

/**
 * @param {string} componentPath
 * @returns {OptimisticWriteEntry | undefined}
 */
export function findRegistryEntry(componentPath) {
  return OPTIMISTIC_WRITES.find(
    (e) => componentPath === e.component_path
       || componentPath.endsWith(e.component_path)
  );
}
