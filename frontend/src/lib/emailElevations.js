// Iter 78s — Standalone SVG renderer for the customer Quote PDF / email.
// Pure string output (no React) so it can be inlined into the WeasyPrint
// HTML and Gmail-compatible email. Mirrors the visual style of
// `ElevationDrawing.jsx` but at a fixed compact size suitable for print.
//
// Input: same elevation shape as ElevationDrawing.
// Output: `<svg>...</svg>` string.

const PADDING = 30;
const ROOF_H = 50;
const VB_W = 380;
const VB_H = 240;

const OPENING_COLORS = {
  window: "#0EA5E9",
  door: "#F97316",
  patio: "#A855F7",
  garage: "#71717A",
  other: "#52525B",
};

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function elevationToSvg(elev) {
  const widthFt = Number(elev?.facade_width_ft || 0);
  const heightFt = Number(elev?.facade_height_ft || 0);
  if (widthFt <= 0 || heightFt <= 0) return "";
  const ftPerPx = widthFt / (VB_W - PADDING * 2);
  const wallW = VB_W - PADDING * 2;
  const wallH = Math.min(heightFt / ftPerPx, VB_H - PADDING * 2 - ROOF_H);
  const wallX = PADDING;
  const wallY = VB_H - PADDING - wallH;
  const roofTop = wallY - ROOF_H;
  const shape = elev.roof_style || (Number(elev.rake_lf_on_face) > 0 ? "gable" : "flat");

  let roof = "";
  if (shape === "gable") {
    roof = `<path d="M ${wallX},${wallY} L ${wallX + wallW / 2},${roofTop} L ${wallX + wallW},${wallY} Z" fill="#E4E4E7" stroke="#52525B" stroke-width="1" />`;
  } else if (shape === "hip") {
    const inset = wallW * 0.18;
    roof = `<path d="M ${wallX},${wallY} L ${wallX + inset},${roofTop} L ${wallX + wallW - inset},${roofTop} L ${wallX + wallW},${wallY} Z" fill="#E4E4E7" stroke="#52525B" stroke-width="1" />`;
  } else if (shape === "flat") {
    roof = `<rect x="${wallX}" y="${wallY - 5}" width="${wallW}" height="5" fill="#E4E4E7" stroke="#52525B" stroke-width="1" />`;
  }

  const openings = (elev.openings || [])
    .map((op) => {
      const opW = (Number(op.width_ft) || 3) / ftPerPx;
      const opH = (Number(op.height_ft) || 4) / ftPerPx;
      const cx = wallX + Number(op.x_pct ?? 0.5) * wallW;
      const cy = wallY + Number(op.y_pct ?? 0.5) * wallH;
      const x = Math.max(wallX, Math.min(wallX + wallW - opW, cx - opW / 2));
      const y = Math.max(wallY, Math.min(wallY + wallH - opH, cy - opH / 2));
      const color = OPENING_COLORS[op.type] || OPENING_COLORS.other;
      return `
        <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${opW.toFixed(1)}" height="${opH.toFixed(1)}" fill="${color}" fill-opacity="0.18" stroke="${color}" stroke-width="1.2" />
        <text x="${(x + opW / 2).toFixed(1)}" y="${(y + opH / 2 + 3).toFixed(1)}" text-anchor="middle" font-size="8" font-family="ui-monospace, monospace" font-weight="700" fill="#09090B">${esc(op.label || (op.type === "door" ? "D" : "W"))}</text>`;
    })
    .join("");

  const scaleBarPx = Math.min(10 / ftPerPx, wallW * 0.3);
  return `<svg viewBox="0 0 ${VB_W} ${VB_H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:380px;height:auto;border:1px solid #E4E4E7;background:#FFFFFF;">
    <line x1="${wallX - 4}" y1="${wallY + wallH}" x2="${wallX + wallW + 4}" y2="${wallY + wallH}" stroke="#52525B" stroke-width="1.5" />
    ${roof}
    <rect x="${wallX}" y="${wallY}" width="${wallW}" height="${wallH}" fill="#FAFAFA" stroke="#09090B" stroke-width="1.5" />
    ${openings}
    <text x="${wallX + wallW / 2}" y="${wallY + wallH + 18}" text-anchor="middle" font-size="10" font-family="ui-monospace, monospace" font-weight="700" fill="#52525B">${widthFt.toFixed(0)}'</text>
    <text x="${wallX + wallW + 14}" y="${wallY + wallH / 2}" text-anchor="middle" font-size="10" font-family="ui-monospace, monospace" font-weight="700" fill="#52525B" transform="rotate(90 ${wallX + wallW + 14} ${wallY + wallH / 2})">${heightFt.toFixed(0)}'</text>
    <line x1="${wallX}" y1="${VB_H - 8}" x2="${wallX + scaleBarPx}" y2="${VB_H - 8}" stroke="#09090B" stroke-width="1.5" />
    <line x1="${wallX}" y1="${VB_H - 12}" x2="${wallX}" y2="${VB_H - 4}" stroke="#09090B" stroke-width="1.5" />
    <line x1="${wallX + scaleBarPx}" y1="${VB_H - 12}" x2="${wallX + scaleBarPx}" y2="${VB_H - 4}" stroke="#09090B" stroke-width="1.5" />
    <text x="${wallX + scaleBarPx / 2}" y="${VB_H - 14}" text-anchor="middle" font-size="8" font-family="ui-monospace, monospace" fill="#52525B">10 ft</text>
  </svg>`;
}

export function buildElevationsBlock(estimate, t, C, FONT) {
  const elevs = estimate?.measurements?._ai_elevations
    || estimate?.hover_measurements?._ai_elevations
    || [];
  if (!Array.isArray(elevs) || !elevs.length) return "";
  const title = (t && t("email.elevationDrawings")) || "Elevation Drawings";
  const subtitle = (t && t("email.elevationDrawingsSubtitle"))
    || "Generated from your job photos";
  return `
    <tr><td style="padding:18px 32px 8px 32px;border-top:1px solid ${C.line};font-family:${FONT};">
      <div style="font-family:${FONT};font-size:10px;letter-spacing:2px;text-transform:uppercase;color:${C.faint};font-weight:bold;margin-bottom:4px;">${esc(title)}</div>
      <div style="font-family:${FONT};font-size:11px;color:${C.muted};margin-bottom:12px;">${esc(subtitle)}</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        ${elevs
          .reduce((rows, e, idx) => {
            const cell = `<td valign="top" style="padding:4px;width:50%;font-family:${FONT};">
              <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;margin-bottom:4px;">${esc(e.label)} <span style="color:${C.muted};font-weight:normal;">· ${Number(e.facade_width_ft || 0).toFixed(0)}'W × ${Number(e.facade_height_ft || 0).toFixed(0)}'H</span></div>
              ${elevationToSvg(e)}
            </td>`;
            if (idx % 2 === 0) rows.push([cell]);
            else rows[rows.length - 1].push(cell);
            return rows;
          }, [])
          .map((row) => `<tr>${row.join("")}${row.length === 1 ? '<td style="width:50%;"></td>' : ""}</tr>`)
          .join("")}
      </table>
    </td></tr>`;
}
