// SEND-142 — the mark vocabulary the editor and its three rail panels
// share. ONE declaration each: the colours, the category list, the tap
// order and the two label helpers. MOVED VERBATIM — not one colour,
// category, key or label string changed with the rail split.
export const SIDING = "#2563EB";                       // PdfOverlayEditor's siding blue
export const OPENING = "#FACC15";                      // the annotator's window yellow
export const GABLE = "#15803D";                        // the annotator's own gable green
export const DORMER = "#0EA5E9";                       // the annotator's dormer blue
// SEND-147 — THE WALL-BASE MARK. A human two-tap start line, its own colour
// so it never reads as a zone edge or a trim run.
export const WALL_BASE = "#F97316";
// The drawing gesture, carried over word for word from the annotator.
export const TAP_ORDER = {
  gable: ["Tap the LEFT EAVE point of the gable.", "Tap the PEAK (ridge) point.",
    "Tap the RIGHT EAVE point to finish the triangle."],
  dormer: ["Tap the BOTTOM-LEFT corner of the dormer face.", "Tap the BOTTOM-RIGHT corner.",
    "Tap the TOP-RIGHT corner.", "Tap the TOP-LEFT corner to finish the face."],
  wall_base: ["Tap the LEFT end of the starter / wall base.",
    "Tap the RIGHT end to finish the start line."],
};
export const CATEGORIES = [                            // the annotator's own zone colours
  { key: "brick", name: "Brick", color: "#B45309" },
  { key: "stone", name: "Stone", color: "#57534E" },
  { key: "garage_door", name: "Garage door", color: "#FBBF24" },
  { key: "stucco", name: "Stucco", color: "#A8A29E" },
  { key: "other", name: "Other", color: "#DC2626" },
];

export const markColor = (m) => {
  if (m.kind === "siding_zone") return SIDING;
  if (m.kind === "opening") return OPENING;
  if (m.kind === "gable") return GABLE;
  if (m.kind === "dormer") return DORMER;
  if (m.kind === "wall_base") return WALL_BASE;
  return (CATEGORIES.find((c) => c.key === m.category) || CATEGORIES[4]).color;
};
export const kindLabel = (m) => (m.kind === "siding_zone" ? "SIDING"
  : m.kind === "gable" ? "GABLE"
    : m.kind === "dormer" ? "DORMER"
      : m.kind === "opening" ? "OPENING"
        : m.kind === "wall_base" ? "WALL BASE"
    : (CATEGORIES.find((c) => c.key === m.category)?.name || "NON-SIDING").toUpperCase());
