// Maps Vinyl Siding catalog items into brand-level sub-categories so the
// editor can nest each profile family inside its own collapsible drop-down
// under the parent "Vinyl Siding" section.
//
// Order matters — defines the display order of the sub-categories.
const VINYL_SIDING_BRANDS = [
  { id: "conquest", label: "Conquest .040", match: (n) => n.startsWith("Conquest") },
  { id: "coventry", label: "Coventry .042", match: (n) => n.startsWith("Coventry") },
  { id: "odyssey", label: "Odyssey .044", match: (n) => n.startsWith("Odyssey") },
  { id: "charter", label: "Charter Oak .046", match: (n) => n.startsWith("Charter Oak") },
  { id: "vbb", label: "Vertical Board & Batten", match: (n) => n.toLowerCase().startsWith("vertical board") },
  { id: "shakes", label: "Shakes", match: (n) => /shake/i.test(n) },
];

// Vero Windows broken out by United-Inch (UI) size range so contractors
// can quickly find the right SKU. "Standard (0-101 UI)" holds the single-
// size styles (Double Hung, Slider); the other three buckets carry the
// size-split styles (3 lite slider, Casement, Picture).
const VERO_WINDOW_SIZES = [
  {
    id: "ui-0-101",
    label: "Standard (0-101 UI)",
    match: (n) => /0-101 UI$/.test(n),
  },
  {
    id: "ui-0-45",
    label: "0-45 UI",
    match: (n) => /0-45 UI$/.test(n),
  },
  {
    id: "ui-46-70",
    label: "46-70 UI",
    match: (n) => /46-70 UI$/.test(n),
  },
  {
    id: "ui-71-101",
    label: "71-101 UI",
    match: (n) => /71-101 UI$/.test(n),
  },
];

const SUBCATS_BY_SECTION = {
  "Vinyl Siding": VINYL_SIDING_BRANDS,
  "Vero Windows": VERO_WINDOW_SIZES,
};

/** Returns the array of sub-category definitions for a section, or null
 *  if the section has no sub-grouping. */
export function subCategoriesFor(sectionTitle) {
  return SUBCATS_BY_SECTION[sectionTitle] || null;
}

/** Group a list of catalog lines into the section's sub-categories.
 *  Returns an array of { id, label, lines }. Items that don't match any
 *  sub-category fall into a trailing "Other" bucket. */
export function groupLinesBySubCategory(sectionTitle, lines) {
  const cats = subCategoriesFor(sectionTitle);
  if (!cats) return null;
  const buckets = cats.map((c) => ({ id: c.id, label: c.label, lines: [] }));
  const other = { id: "other", label: "Other", lines: [] };
  for (const l of lines) {
    const cat = cats.find((c) => c.match(l.name));
    if (cat) {
      const b = buckets.find((x) => x.id === cat.id);
      b.lines.push(l);
    } else {
      other.lines.push(l);
    }
  }
  if (other.lines.length) buckets.push(other);
  return buckets.filter((b) => b.lines.length > 0);
}
