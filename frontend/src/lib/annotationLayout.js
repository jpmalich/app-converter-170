// ANNOTATION LAYOUT — collision-managed callouts (ruled 2026-07-26):
// no overlapping text anywhere on a sheet. Pure + node-testable; pinned
// by tests/test_annotation_layout_pin.py (backend runs node against this
// file). Blocks: {id, x, y, w, h, fixed?} — x/y = top-left, SVG units.
// Fixed blocks (boxed panels) never move; movable blocks keep their x
// and shift DOWN below whatever they overlap (stack), so no two returned
// blocks intersect. Callers draw a leader when `moved` is true.
export function layoutAnnotations(blocks, gap = 4) {
  const placed = [];
  const out = {};
  const fixed = blocks.filter((b) => b.fixed);
  const movable = blocks.filter((b) => !b.fixed).sort((a, b) => a.y - b.y || a.x - b.x);
  for (const b of fixed) {
    placed.push({ x: b.x, w: b.w, y: b.y, h: b.h });
    out[b.id] = { y: b.y, moved: false };
  }
  for (const b of movable) {
    let y = b.y;
    let changed = true;
    while (changed) {
      changed = false;
      for (const p of placed) {
        const xOverlap = b.x < p.x + p.w && p.x < b.x + b.w;
        const yOverlap = y < p.y + p.h && p.y < y + b.h;
        if (xOverlap && yOverlap) {
          y = p.y + p.h + gap;
          changed = true;
        }
      }
    }
    placed.push({ x: b.x, w: b.w, y, h: b.h });
    out[b.id] = { y, moved: Math.abs(y - b.y) > 0.5 };
  }
  return out;
}

// crude but stable SVG text width estimate (Helvetica ~0.62em/char)
export function estWidth(text, fontSize) {
  return String(text || "").length * fontSize * 0.62;
}

// abbreviate long callouts — the FULL text stays in the schedule/footer
export function abbrev(text, max = 110) {
  const s = String(text || "");
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}
