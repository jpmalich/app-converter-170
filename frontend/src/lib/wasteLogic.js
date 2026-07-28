// Cut-waste logic — baked into line qty on import.
//
// AREA GOODS ONLY (Howard sealed 2026-07-29): the contractor's waste %
// multiplies AREA-counted goods — siding panels, lap, soffit panels,
// house wrap, fan fold. LENGTH-CUT goods (whole-stick-per-run /
// -per-corner / -per-segment counts: outside/inside corners, starter,
// finish trim, J-channel, soffit-J, LP trim sticks, battens) are
// waste-included BY CONSTRUCTION — the whole-stick count already
// contains the scrap; a percentage on top buys sticks nobody cuts.
// Those rows carry `_waste_included: true` from the backend spec and
// this classifier no longer matches them, both doors, every family.
//
// Iter 78 (Howard's "1C · 2C · 3A") mechanics still hold for area goods:
//   • Waste % is applied directly to the qty on HOVER / Blueprint import
//     so the estimate SHOWS the wasted total the contractor orders.
//   • When the contractor changes Waste % later, every line with a
//     stored `raw_qty` recomputes: qty = raw_qty × (1 + waste/100),
//     whole units. Length-cut rows with legacy baked waste snap back to
//     the whole-stick count (raw_qty) instead.

const ASCEND_SIDING_NAMES = new Set([
  'Ascend Composite Lap Siding 7"',
  'Ascend Composite B&B 12" (add 30% Waste)',
]);

export function isCutProneItem(line) {
  if (!line) return false;
  const section = String(line.section || "").toLowerCase();
  const name = String(line.name || "").toLowerCase();

  // Siding panels — full section gets waste in Vinyl; only the two
  // composite SKUs in Ascend.
  if (section === "vinyl siding") return true;
  if (
    (line.section === "Ascend Cladding" ||
      line.section === "Ascend Cladding/Accessories") &&
    ASCEND_SIDING_NAMES.has(line.name)
  ) {
    return true;
  }

  // LP panel + soffit sections are AREA goods (lap boards by coverage,
  // soffit by sqft). LP SmartSide Trim + OSC accessories are LENGTH-CUT
  // — dropped 2026-07-29 (rows carry _waste_included from the spec).
  if (section === "lp smart siding") return true;
  if (section === "lp smartside soffit") return true;

  // Soffit panels (Charter Oak) — area-counted (sqft ÷ 10/pc)
  if (
    section === "vinyl soffit with siding" &&
    name.includes("charter oak soffit")
  ) {
    return true;
  }

  // Iter 78l — House Wrap. Wrap rolls are full-coverage so contractors
  // cut waste at every opening, seam, and corner. Howard's request: the
  // waste % should apply to House Wrap (regular + RainDrop) the same
  // way it applies to siding panels.
  if (name === "house wrap" || name === "raindrop house wrap") return true;

  // Iter 78m — Fan Fold (3/8") insulation board. Same install reality
  // as House Wrap: full-coverage, cut around openings + corners.
  if (name === '3/8" fan fold' || name.includes("fan fold")) return true;

  return false;
}

// WHOLE UNITS AT THE ORDER LAYER (Howard — ruled in the convergence
// audit, made LIVE + sealed 2026-07-28): nobody orders half a stick and
// no yard will pick one. Every ordered quantity rounds UP to a whole
// unit AFTER waste, every family, every line. The 0.5 convention is
// RETIRED (540 trim: raw 100 × 1.1 → IEEE754 110.000…01 → round-up-half
// kept 110.5). The 1e-9 epsilon strips float noise, never real waste.
function roundUpWhole(n) {
  const x = Number(n);
  if (!isFinite(x) || x <= 0) return 0;
  return Math.ceil(x - 1e-9);
}

// WASTE — SEALED, ALL FAMILIES, ONE RULE (Howard, 2026-07-28): the
// contractor's visible Waste % field is the ONLY waste; whatever the
// field says is ALWAYS applied into the quantity, every family, at this
// one layer. applyWasteQty is the SINGLE frontend waste-math site —
// mirrored by backend routes/hover.py::_bake_tab_waste (equality pinned).
// Any second implementation fails test_one_waste_emitter.py.
export function applyWasteQty(raw, wastePct) {
  const pct = Math.max(0, Number(wastePct) || 0);
  return roundUpWhole((Number(raw) || 0) * (1 + pct / 100));
}

// On import (HOVER / Blueprint): take freshly-computed catalog lines
// and bake the waste % into qty for cut-prone items. Stores the
// original raw value in `raw_qty` so future waste-% changes can
// recompute without losing the source measurement.
//
// Items that don't qualify (gutter, downspouts, end caps, elbows,
// labor, etc.) are returned unchanged.
export function bakeWasteIntoLines(lines, wastePct) {
  const pct = Math.max(0, Number(wastePct) || 0);
  return (lines || []).map((l) => {
    const raw = Number(l.qty) || 0;
    if (raw <= 0 || l._waste_included) return l;
    if (!isCutProneItem(l)) {
      // WHOLE UNITS apply to every ordered line at this layer — a
      // fractional non-cut-prone qty (e.g. coil 5.28 ROLL) rounds up.
      return Number.isInteger(raw) ? l : { ...l, qty: roundUpWhole(raw) };
    }
    return {
      ...l,
      raw_qty: raw,
      qty: applyWasteQty(raw, pct),
    };
  });
}

// On waste-% change: walk existing lines, recompute qty from raw_qty
// for any line that has it. Lines without raw_qty (manually entered or
// non-cut-prone) keep whatever qty the contractor typed.
export function recomputeWasteQtys(lines, wastePct) {
  const pct = Math.max(0, Number(wastePct) || 0);
  return (lines || []).map((l) => {
    const raw = Number(l?.raw_qty);
    if (!raw || !isFinite(raw) || raw <= 0) return l;
    // LENGTH-CUT rows carrying legacy baked waste snap BACK to the
    // whole-stick count (sealed 2026-07-29): the count IS the allowance.
    if (!isCutProneItem(l)) return { ...l, qty: roundUpWhole(raw) };
    return { ...l, qty: applyWasteQty(raw, pct) };
  });
}

// Iter 78b — "Recompute waste on existing lines" helper.
//
// Legacy LP estimates (created before the Iter 78a classifier fix
// shipped) have cut-prone lines stored with `qty = raw` and
// `raw_qty = null` — so a waste-% change can't recompute them. This
// helper walks every cut-prone line in the estimate and:
//   1. If `raw_qty` is missing, treats the current `qty` AS the raw
//      measurement and stamps it into `raw_qty`.
//   2. Recomputes `qty = applyWasteQty(raw_qty, waste)` — whole units.
//
// Non-cut-prone lines (gutter, downspouts, manual entries that
// don't match the classifier) are left untouched.
//
// Important: a line that was manually edited (user typed a custom qty
// AFTER the original raw import) is indistinguishable from a legacy
// line — both have raw_qty=null. The button MUST be gated behind a
// confirm dialog so contractors don't accidentally bump manual lines.
export function recomputeAllWaste(lines, wastePct) {
  const pct = Math.max(0, Number(wastePct) || 0);
  return (lines || []).map((l) => {
    if (l._waste_included || !isCutProneItem(l)) return l;
    const stored = Number(l.raw_qty);
    const hasRaw = isFinite(stored) && stored > 0;
    const rawQty = hasRaw ? stored : (Number(l.qty) || 0);
    if (rawQty <= 0) return l;
    return {
      ...l,
      raw_qty: rawQty,
      qty: applyWasteQty(rawQty, pct),
    };
  });
}

// LP SmartSide soffit steering (Iter 78).
//
// The HOVER spec splits LP soffit into two rows by surface:
//   • "38 Series Soffit 16 x 16 Vented" — qty derived from eaves_lf
//   • "38 Series Soffit 16 x 16 Closed" — qty derived from rakes_lf
//
// Howard's "Soffit type" knob lets him steer those at apply time:
//   "mix"    — leave as-is (the smart default for most jobs)
//   "vented" — collapse Closed qty into Vented (all-vented job)
//   "closed" — collapse Vented qty into Closed (all-closed job)
//
// Combines both line.qty and line.raw_qty so a later waste-% change
// still recomputes correctly. Lines that aren't LP soffit are untouched.
const VENTED_SOFFIT = "38 Series Soffit 16 x 16 Vented";
const CLOSED_SOFFIT = "38 Series Soffit 16 x 16 Closed";

export function steerLpSoffit(lines, soffitType) {
  const type = soffitType || "mix";
  if (type === "mix") return lines || [];
  const out = [];
  let vented = null;
  let closed = null;
  for (const l of lines || []) {
    if (l?.name === VENTED_SOFFIT) {
      vented = l;
      continue;
    }
    if (l?.name === CLOSED_SOFFIT) {
      closed = l;
      continue;
    }
    out.push(l);
  }
  // Collapse the two LP soffit qtys into the winning row.
  const ventedQty = Number(vented?.qty) || 0;
  const closedQty = Number(closed?.qty) || 0;
  const ventedRaw = Number(vented?.raw_qty) || 0;
  const closedRaw = Number(closed?.raw_qty) || 0;
  const sumQty = ventedQty + closedQty;
  const sumRaw = ventedRaw + closedRaw;
  if (type === "vented" && (vented || closed)) {
    const base = vented || closed;
    out.push({
      ...base,
      name: VENTED_SOFFIT,
      qty: sumQty,
      raw_qty: sumRaw > 0 ? sumRaw : (base.raw_qty ?? null),
    });
  } else if (type === "closed" && (vented || closed)) {
    const base = closed || vented;
    out.push({
      ...base,
      name: CLOSED_SOFFIT,
      qty: sumQty,
      raw_qty: sumRaw > 0 ? sumRaw : (base.raw_qty ?? null),
    });
  } else {
    // No LP soffit rows in the input — nothing to steer
    if (vented) out.push(vented);
    if (closed) out.push(closed);
  }
  return out;
}
