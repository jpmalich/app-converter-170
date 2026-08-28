// SEND-142 — the mark vocabulary the editor and its three rail panels
// share. ONE declaration each: the colours, the category list, the tap
// order and the two label helpers. MOVED VERBATIM — not one colour,
// category, key or label string changed with the rail split.
export const SIDING = "#2563EB";                       // PdfOverlayEditor's siding blue
export const OPENING = "#FACC15";                      // the annotator's window yellow
export const GABLE = "#15803D";                        // the annotator's own gable green
export const DORMER = "#0EA5E9";                       // the annotator's dormer blue
// The drawing gesture, carried over word for word from the annotator.
export const TAP_ORDER = {
  gable: ["Tap the LEFT EAVE point of the gable.", "Tap the PEAK (ridge) point.",
    "Tap the RIGHT EAVE point to finish the triangle."],
  dormer: ["Tap the BOTTOM-LEFT corner of the dormer face.", "Tap the BOTTOM-RIGHT corner.",
    "Tap the TOP-RIGHT corner.", "Tap the TOP-LEFT corner to finish the face."],
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
  return (CATEGORIES.find((c) => c.key === m.category) || CATEGORIES[4]).color;
};
export const kindLabel = (m) => (m.kind === "siding_zone" ? "SIDING"
  : m.kind === "gable" ? "GABLE"
    : m.kind === "dormer" ? "DORMER"
      : m.kind === "opening" ? "OPENING"
    : (CATEGORIES.find((c) => c.key === m.category)?.name || "NON-SIDING").toUpperCase());
