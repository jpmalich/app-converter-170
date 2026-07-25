// GABLE / ABOVE-EAVE math (ruled 2026-07-24). Shared by the photo
// annotator, the burn-in renderer, and the run-launch payload builder.
// Scale ladder: WALL scale anchor first, WINDOW anchor second — the same
// calibration the rest of the annotator already trusts.

export const GABLE_PITCH_PRESETS = [4, 5, 6, 7, 8, 9, 10, 12];
export const GABLE_PITCH_MIN = 3;   // gentle warning below 3/12
export const GABLE_PITCH_MAX = 18;  // gentle warning above 18/12
export const RIDGE_TOLERANCE_FT = 1.0; // ruled: 1.0 ft cross-elevation ridge check

export function inchesPerPx(reference, windowReference) {
  for (const ref of [reference, windowReference]) {
    if (!ref || !ref.p1 || !ref.p2 || !ref.inches) continue;
    const px = Math.hypot(ref.p2.x - ref.p1.x, ref.p2.y - ref.p1.y);
    if (px > 0 && Number(ref.inches) > 0) return Number(ref.inches) / px;
  }
  return null;
}

// pts = [leftEave, peak, rightEave] in photo-pixel coords.
// Base = eave-point distance; rise = perpendicular distance from the
// peak to the eave line (photos are square-on; the eave line may tilt a
// touch — perpendicular keeps the math honest). Pitch is scale-free.
export function gableDims(pts, inPerPx) {
  if (!pts || pts.length !== 3) return null;
  const [L, P, R] = pts;
  const basePx = Math.hypot(R.x - L.x, R.y - L.y);
  if (basePx <= 0) return null;
  const risePx = Math.abs(
    (R.x - L.x) * (L.y - P.y) - (L.x - P.x) * (R.y - L.y)
  ) / basePx;
  const pitch = basePx > 0 ? (risePx / (basePx / 2)) * 12 : null;
  const out = { basePx, risePx, pitch: pitch === null ? null : Math.round(pitch * 10) / 10 };
  if (inPerPx) {
    out.baseFt = (basePx * inPerPx) / 12;
    out.riseFt = (risePx * inPerPx) / 12;
    out.grossAreaFt = (out.baseFt * out.riseFt) / 2;
  }
  return out;
}

export function pitchOutOfRange(pitch) {
  return pitch !== null && pitch !== undefined &&
    (pitch < GABLE_PITCH_MIN || pitch > GABLE_PITCH_MAX);
}

function zonePoints(z) {
  if (z.shape === "poly" && Array.isArray(z.points)) return z.points;
  if (z.x1 !== undefined) {
    return [{ x: z.x1, y: z.y1 }, { x: z.x2, y: z.y1 },
            { x: z.x2, y: z.y2 }, { x: z.x1, y: z.y2 }];
  }
  return null;
}

export function polyAreaPx(points) {
  if (!points || points.length < 3) return 0;
  let s = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length];
    s += a.x * b.y - b.x * a.y;
  }
  return Math.abs(s) / 2;
}

function centroid(points) {
  const n = points.length;
  return {
    x: points.reduce((s, p) => s + p.x, 0) / n,
    y: points.reduce((s, p) => s + p.y, 0) / n,
  };
}

export function pointInTriangle(pt, [a, b, c]) {
  const sign = (p1, p2, p3) =>
    (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y);
  const d1 = sign(pt, a, b), d2 = sign(pt, b, c), d3 = sign(pt, c, a);
  const neg = d1 < 0 || d2 < 0 || d3 < 0;
  const pos = d1 > 0 || d2 > 0 || d3 > 0;
  return !(neg && pos);
}

// NET gable area: gross triangle minus masked NO-SIDING zones whose
// centroid sits inside the triangle (vents, decorative panels, stone
// accents — the same masking tools the walls use). Clamped ≥ 0.
export function gableNetArea(gable, zones, inPerPx) {
  const dims = gableDims(gable.pts, inPerPx);
  if (!dims || dims.grossAreaFt === undefined) return dims;
  let maskedPx = 0;
  for (const z of zones || []) {
    const pts = zonePoints(z);
    if (!pts || pts.length < 3) continue;
    if (pointInTriangle(centroid(pts), gable.pts)) maskedPx += polyAreaPx(pts);
  }
  const maskedFt = (maskedPx * inPerPx * inPerPx) / 144;
  return {
    ...dims,
    maskedFt,
    netAreaFt: Math.max(0, dims.grossAreaFt - maskedFt),
  };
}

// Cross-elevation ridge check (ruled: 1.0 ft): compare the LARGEST
// implied rise per elevation; a spread beyond tolerance flags a gentle
// warning — never a block.
export function crossCheckRidges(risesByElevation) {
  const entries = Object.entries(risesByElevation || {})
    .map(([elev, rises]) => [elev, Math.max(...rises)])
    .filter(([, r]) => Number.isFinite(r));
  if (entries.length < 2) return null;
  entries.sort((a, b) => b[1] - a[1]);
  const [hiE, hi] = entries[0];
  const [loE, lo] = entries[entries.length - 1];
  if (hi - lo <= RIDGE_TOLERANCE_FT) return null;
  return (
    `Gable rise disagrees across elevations: ${hiE} implies ${hi.toFixed(1)} ft ` +
    `vs ${loE} ${lo.toFixed(1)} ft (Δ ${(hi - lo).toFixed(1)} ft > ${RIDGE_TOLERANCE_FT.toFixed(1)} ft). ` +
    `Double-check the tapped points — same ridge should read the same height.`
  );
}

// ── DORMER FACE math (ruled 2026-07-25 — mirrors the gable tool) ──
// pts = [bottomLeft, bottomRight, topRight, topLeft] photo-pixel corners
// of the VERTICAL dormer face. Width/height average the opposing edges
// (photos are square-on; a touch of tilt averages out honestly).
// Area = width × height, minus NO-SIDING masks inside the quad.
export function pointInPolygon(pt, pts) {
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const xi = pts[i].x, yi = pts[i].y, xj = pts[j].x, yj = pts[j].y;
    if ((yi > pt.y) !== (yj > pt.y) &&
        pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

export function dormerDims(pts, inPerPx) {
  if (!pts || pts.length !== 4) return null;
  const [bl, br, tr, tl] = pts;
  const widthPx = (Math.hypot(br.x - bl.x, br.y - bl.y) +
                   Math.hypot(tr.x - tl.x, tr.y - tl.y)) / 2;
  const heightPx = (Math.hypot(tl.x - bl.x, tl.y - bl.y) +
                    Math.hypot(tr.x - br.x, tr.y - br.y)) / 2;
  if (widthPx <= 0 || heightPx <= 0) return null;
  const out = { widthPx, heightPx };
  if (inPerPx) {
    out.widthFt = (widthPx * inPerPx) / 12;
    out.heightFt = (heightPx * inPerPx) / 12;
    out.grossAreaFt = out.widthFt * out.heightFt;
  }
  return out;
}

// NET dormer-face area: width × height minus masked NO-SIDING zones
// whose centroid sits inside the quad — same rule the gables follow.
export function dormerNetArea(dormer, zones, inPerPx) {
  const dims = dormerDims(dormer.pts, inPerPx);
  if (!dims || dims.grossAreaFt === undefined) return dims;
  let maskedPx = 0;
  for (const z of zones || []) {
    const pts = zonePoints(z);
    if (!pts || pts.length < 3) continue;
    if (pointInPolygon(centroid(pts), dormer.pts)) maskedPx += polyAreaPx(pts);
  }
  const maskedFt = (maskedPx * inPerPx * inPerPx) / 144;
  return {
    ...dims,
    maskedFt,
    netAreaFt: Math.max(0, dims.grossAreaFt - maskedFt),
  };
}
