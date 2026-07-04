// Iter 79j.46 — Theme registry + persistence.
//
// User-selectable UI themes for the CONTRACTOR working surface only.
// Customer-facing surfaces (QuoteModal, AcceptPage, generated HTML in
// lib/emailQuote / materialList / printTakeoff) intentionally keep a
// neutral document style regardless of the theme selected here.
//
// - Registry: every theme carries a stable `id`, a display-label i18n
//   key, and a 3-color swatch (brand + surface + ink) for the picker
//   chip.
// - "auto" resolves at boot to the OS prefers-color-scheme (dark →
//   "dark", otherwise → "orange" default).
// - "orange" removes the data-theme attribute entirely because the
//   :root values ARE the orange theme (no attribute selector needed).

export const STORAGE_KEY = "ui-theme-v1";

export const THEMES = [
  {
    id: "auto",
    labelKey: "theme.auto",
    // Auto is rendered with a subtle neutral swatch — actual resolved
    // theme handles the color story.
    swatch: ["#F97316", "#FFFFFF", "#09090B"],
  },
  {
    id: "orange",
    labelKey: "theme.orange",
    swatch: ["#F97316", "#FFFFFF", "#09090B"],
  },
  {
    id: "blueprint",
    labelKey: "theme.blueprint",
    swatch: ["#2563EB", "#F2F4F8", "#0C1220"],
  },
  {
    id: "forest",
    labelKey: "theme.forest",
    swatch: ["#15803D", "#F1F5F1", "#0A0F0B"],
  },
  {
    id: "steel",
    labelKey: "theme.steel",
    swatch: ["#334155", "#F2F4F6", "#0B0F14"],
  },
  {
    id: "highvis",
    labelKey: "theme.highvis",
    swatch: ["#FACC15", "#FFFFFF", "#854D0E"],
  },
  {
    id: "dark",
    labelKey: "theme.dark",
    swatch: ["#F97316", "#18181B", "#FAFAFA"],
  },
];

const VALID_IDS = new Set(THEMES.map((t) => t.id));
const APPLIED_IDS = new Set(THEMES.filter((t) => t.id !== "auto").map((t) => t.id));

// Resolve "auto" to the effective theme id we actually apply to the DOM.
export function resolveAuto(id) {
  if (id !== "auto") return id;
  try {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "orange";
    }
  } catch {
    /* ignore — fall through */
  }
  return "orange";
}

// Set / remove the data-theme attribute on <html>. "orange" clears it
// because :root ALREADY encodes the orange palette (no attribute rules
// need to match).
export function applyTheme(id) {
  const resolved = resolveAuto(id);
  const root = typeof document !== "undefined" ? document.documentElement : null;
  if (!root) return;
  if (!APPLIED_IDS.has(resolved) || resolved === "orange") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", resolved);
  }
}

export function readStoredTheme() {
  try {
    const raw = typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (raw && VALID_IDS.has(raw)) return raw;
  } catch {
    /* localStorage disabled */
  }
  return "auto";
}

export function setTheme(id) {
  if (!VALID_IDS.has(id)) return;
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* ignore */
  }
  applyTheme(id);
}

// Watch prefers-color-scheme so "auto" flips live when the OS toggles
// (e.g. macOS Night Shift schedule). Returns an unsubscribe fn.
export function watchSystemTheme(getCurrent) {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = () => {
    const current = typeof getCurrent === "function" ? getCurrent() : readStoredTheme();
    if (current === "auto") applyTheme("auto");
  };
  // Older Safari only exposes addListener; feature-detect both.
  if (mq.addEventListener) mq.addEventListener("change", handler);
  else if (mq.addListener) mq.addListener(handler);
  return () => {
    if (mq.removeEventListener) mq.removeEventListener("change", handler);
    else if (mq.removeListener) mq.removeListener(handler);
  };
}
