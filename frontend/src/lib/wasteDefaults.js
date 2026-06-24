// Per-workspace default Waste % store (Iter 78).
//
// Howard's typical mix:
//   • Vinyl / Ascend (kind=siding) → ~15%
//   • LP SmartSide   (kind=lp_smart) → ~25%
//   • ISS            (kind=iss)    → ~10–15%
//   • Windows        (kind=windows) → 0% (no panel cutwaste)
//
// We persist the contractor's chosen default per workspace kind in
// localStorage so the Blueprint reader / HOVER importer can silently
// auto-fill the estimate's waste_pct on subsequent uploads — one-time
// prompt, then it sticks.
//
// localStorage key shape: `defaultWastePct:${kind}`.
const KEY = (kind) => `defaultWastePct:${kind || "siding"}`;

export function getSavedWasteDefault(kind) {
  try {
    const v = Number(localStorage.getItem(KEY(kind)));
    return v > 0 ? v : null;
  } catch {
    return null;
  }
}

export function saveWasteDefault(kind, pct) {
  try {
    if (pct > 0) localStorage.setItem(KEY(kind), String(pct));
  } catch {
    /* private mode — silently ignore */
  }
}

export function clearWasteDefault(kind) {
  try {
    localStorage.removeItem(KEY(kind));
  } catch {
    /* private mode — silently ignore */
  }
}

// Human-readable workspace label for the prompt message.
export function workspaceLabel(kind) {
  if (kind === "lp_smart") return "LP SmartSide";
  if (kind === "iss") return "ISS";
  if (kind === "windows") return "Windows";
  return "Vinyl + Ascend";
}
