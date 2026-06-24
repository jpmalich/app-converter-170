// Iter 78s — Build ElevationDrawing-ready props from AI Measure / Phase 2
// HOVER vision / Blueprint outputs. Single source of truth so the renderer
// stays decoupled from data shape.
//
// Input shapes supported:
//   1. AI Measure: { walls: [{name, width_ft, height_ft, ...}], openings: [{wall, width_in, height_in, bbox, label, type, id}] }
//   2. HOVER Phase 2 vision: { per_elevation_siding_from_drawing: { Front: {facade_width_ft, facade_height_ft, window_dims, ...} } }
//
// Returns: [ { label, facade_width_ft, facade_height_ft, openings: [{id, label, x_pct, y_pct, width_ft, height_ft, type}], rake_lf_on_face, roof_style? } ]

const WALL_LABELS = ["front", "back", "left", "right"];

export function buildElevationsFromAIMeasure(measurements) {
  const walls = Array.isArray(measurements?.walls) ? measurements.walls : [];
  const openings = Array.isArray(measurements?.openings) ? measurements.openings : [];
  return walls.map((w) => {
    const name = (w.name || w.wall || "").toLowerCase();
    const ownOpenings = openings
      .filter((op) => (op.wall || "").toLowerCase() === name)
      .map((op, idx) => {
        const bbox = op.bbox || {};
        // bbox is normalized 0–1 to the photo. Use bbox.x + bbox.w/2 as
        // wall-x center; bbox.y + bbox.h/2 as wall-y center. Good first
        // approximation — contractor can drag to fine-tune.
        const x = Number(bbox.x ?? 0.5);
        const y = Number(bbox.y ?? 0.5);
        const w_in_bbox = Number(bbox.w ?? 0);
        const h_in_bbox = Number(bbox.h ?? 0);
        return {
          id: op.id || `${name}-${op.type || "win"}-${idx}`,
          label: op.label || (op.type === "door" || op.type === "patio" || op.type === "garage" ? "D" : "W") + (idx + 1),
          x_pct: x + w_in_bbox / 2,
          y_pct: y + h_in_bbox / 2,
          width_ft: (Number(op.width_in) || 36) / 12,
          height_ft: (Number(op.height_in) || 48) / 12,
          type: op.type || "window",
        };
      });
    return {
      label: name.charAt(0).toUpperCase() + name.slice(1),
      facade_width_ft: Number(w.width_ft) || 0,
      facade_height_ft: (Number(w.height_ft) || Number(measurements?.avg_wall_height_ft) || 0),
      openings: ownOpenings,
      rake_lf_on_face: Number(w.gable_triangle_height_ft) > 0 ? Number(w.width_ft) : 0,
      // Roof style auto-inference: gable if Claude flagged a gable_triangle, else flat
      roof_style: Number(w.gable_triangle_height_ft) > 0 ? "gable" : null,
    };
  }).filter((e) => WALL_LABELS.includes(e.label.toLowerCase()) && e.facade_width_ft > 0);
}

export function buildElevationsFromHoverVision(measurements) {
  const src = measurements?.per_elevation_siding_from_drawing || {};
  return Object.entries(src).map(([label, data]) => {
    const wins = (data.window_dims || []).map((w, idx) => ({
      id: `hover-${label.toLowerCase()}-${idx}`,
      label: w.label || `W${idx + 1}`,
      x_pct: 0.2 + (idx % 4) * 0.2, // approximate spacing — contractor can nudge
      y_pct: 0.45,
      width_ft: Number(w.width_ft) || 3,
      height_ft: Number(w.height_ft) || 4,
      type: "window",
    }));
    return {
      label,
      facade_width_ft: Number(data.facade_width_ft) || 0,
      facade_height_ft: Number(data.facade_height_ft) || 0,
      openings: wins,
      rake_lf_on_face: Number(data.rake_lf_on_face) || 0,
    };
  }).filter((e) => e.facade_width_ft > 0);
}
