// Single source of truth for which product-line tabs are visible in the
// estimator UI. Flipping `lp_smart: false` → `true` brings back the LP
// SmartSide tab instantly — no migration needed. All LP catalog data,
// pricing, HOVER mappings, and lightbulb flags stay intact in code and the
// database; they're just not shown until the flag is back on.
export const TAB_VISIBILITY = {
  vinyl: true,
  ascend: true,
  lp_smart: true,  // Iter 66 — re-enabled per Howard's request to work on LP pricing/UX.
  windows: true,   // Vero (legacy) — windows-kind only
  mezzo: true,     // Iter 37 — Mezzo (3000 series), windows-kind only
};

export const ALL_TAB_DEFS = [
  { id: "vinyl", label: "Vinyl" },
  { id: "ascend", label: "Ascend" },
  { id: "lp_smart", label: "LP Smart" },
  { id: "windows", label: "Vero" },
  { id: "mezzo", label: "Mezzo" },
];

/** Tab defs filtered to only the currently-enabled tabs. */
export const VISIBLE_TAB_DEFS = ALL_TAB_DEFS.filter((t) => TAB_VISIBILITY[t.id]);

/** Plain id list — handy for `Array.includes()` checks. */
export const VISIBLE_TAB_IDS = VISIBLE_TAB_DEFS.map((t) => t.id);

/** Tab ids that show in a windows-kind estimate (separate set from siding). */
export const WINDOWS_KIND_TAB_IDS = ["windows", "mezzo"];
