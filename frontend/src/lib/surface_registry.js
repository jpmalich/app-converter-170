// SURFACE REGISTRY (Howard ruled 2026-08-11 send-4 item 2).
//
// "A SURFACE REGISTRY would be the same move [as the seam / TTL /
// schema-consumer registries]: every surface that can be conditionally
// hidden declares its gate condition and its chip, and the census
// fails the build on (1) a registered surface with no chip, and (2) an
// unregistered conditional render or mount it can grep."
//
// Rung shape (same as seam_accounting.SEAM_REGISTRY):
//   1. Every gated surface DECLARES itself here.
//   2. The detector at
//      backend/tests/test_surface_registry_census_2026_08_11.py
//      fails the build when a component ships a "return null" inside a
//      conditional OR a "mounted-only-inside-a-conditional" pattern
//      that is not declared here AND does not render a SurfaceAccessChip.
//   3. The whole point: instance five cannot hide.
//
// See memory/entry_link_surface_audit_2026-08-11.md §2 for the walk
// that motivated the four seed entries.

/**
 * @typedef {object} SurfaceEntry
 * @property {string} id — unique id (kebab-case).
 * @property {string} label — human name.
 * @property {string} gate — the state that gates the surface today.
 * @property {string} way_out — what the contractor does to reach it.
 * @property {"speaks" | "invisible" | "renders_null" | "modal_only"} class_before —
 *   the shape BEFORE the chip contract landed on it.
 * @property {string} chip_testid — the testid the SurfaceAccessChip renders with.
 * @property {string} chip_mount_component — file where the chip mounts today.
 * @property {string[]} [notes]
 */

/** @type {SurfaceEntry[]} */
export const SURFACE_REGISTRY = [
  // S1 — the elevation entry links. Class-before: mounted only inside
  // the run dialog modal. Retired via BlueprintElevationEntry which
  // itself mounts a SurfaceAccessChip when no completed run exists.
  {
    id: "s1-blueprint-elevation-entry",
    label: "Blueprint elevation sheets EL-1..EL-4",
    gate: "needs a completed blueprint read",
    way_out: "start a blueprint read from the tile to enable EL-1..EL-4",
    class_before: "modal_only",
    chip_testid: "bp-el-entry-blueprint-tile-chip",
    chip_mount_component: "components/estimate/BlueprintElevationEntry.jsx",
  },
  // S2 — photo elevation entry links. Class-before: rendered inside
  // FieldVerifyCard only. The chip variant already exists there —
  // pinned so a future refactor cannot un-mount it.
  {
    id: "s2-photo-elevation-entry",
    label: "Photo elevation sheets",
    gate: "photo door + completed run with walls",
    way_out: "AI photo measure the estimate; the empty-state names walls carried",
    class_before: "speaks",
    chip_testid: "field-verify-elevation-sheets-empty",
    chip_mount_component: "components/estimate/FieldVerifyCard.jsx",
  },
  // S3 — vinyl profile picker. Class-before: invisible on
  // blueprint/HOVER (no picker + no chip). Retired via chip on
  // the HOVER PDF tile in JobInfoPanel.
  {
    id: "s3-vinyl-profile-picker",
    label: "Vinyl profile picker",
    gate: "photo door only",
    way_out: "this row's profile came from the schedule/import; picker mounts inside the HOVER modal",
    class_before: "invisible",
    chip_testid: "s3-vinyl-profile-picker-chip",
    chip_mount_component: "components/estimate/JobInfoPanel.jsx",
  },
  // S4 — accent injection. Class-before: reachable only inside run
  // dialog modals. Retired via chips on both Blueprint and AI Photo
  // tiles in JobInfoPanel.
  {
    id: "s4-accent-injection",
    label: "Accent injection",
    gate: "needs a completed measurement run",
    way_out: "open the blueprint or AI photo dialog to inject an accent",
    class_before: "modal_only",
    chip_testid: "s4-accent-injection-chip-blueprint",
    chip_mount_component: "components/estimate/JobInfoPanel.jsx",
    notes: ["Also mounts as s4-accent-injection-chip-photo on the AI tile."],
  },
];

/**
 * @param {string} id
 * @returns {SurfaceEntry | undefined}
 */
export function findSurface(id) {
  return SURFACE_REGISTRY.find((s) => s.id === id);
}
