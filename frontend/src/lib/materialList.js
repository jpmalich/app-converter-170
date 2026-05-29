// Build a print-ready Material List for a given estimate.
// Lists ONLY items with qty > 0, with AMI part #, description, color, unit,
// raw qty, and waste-applied qty (so contractors can hand the list to Alside
// to pull/ship the right amount of material).
// Renders via the existing /api/estimates/{id}/pdf endpoint, same as quotes.

import { tSection, tItem, tUnit } from "./catalogTranslations";

const FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif";
const C = {
  ink: "#09090B",
  muted: "#52525B",
  faint: "#A1A1AA",
  line: "#E4E4E7",
  accent: "#F97316",
  bg: "#FAFAFA",
};

const esc = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

// Round qty UP to nearest 0.5 — common ordering quantum for siding (no half-pieces, half-rolls).
function roundUpHalf(n) {
  if (!isFinite(n) || n <= 0) return 0;
  return Math.ceil(n * 2) / 2;
}

function absUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${process.env.REACT_APP_BACKEND_URL}${path}`;
}

export function buildMaterialListHtml({ estimate, company, branding, lang = "en" }) {
  const wastePct = Number(estimate.waste_pct) || 0;
  // Only material-relevant lines with quantity > 0. We intentionally include
  // labor-only lines too — they show qty but blank material columns, so the
  // installer reads them as a checklist.
  const linesByCat = (estimate.lines || [])
    .filter((l) => (l.qty || 0) > 0)
    .reduce((acc, l) => {
      (acc[l.section] = acc[l.section] || []).push(l);
      return acc;
    }, {});

  const supplierName = branding?.supplier_name || "Alside Supply";
  const companyName = company?.name || "Your Contractor";
  const logoUrl = company?.logo_url ? absUrl(company.logo_url) : null;

  const todayStr = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const sectionBlock = ([sectionName, items]) => {
    const totalRaw = items.reduce((s, l) => s + (l.qty || 0), 0);
    return `
      <tr><td colspan="5" style="padding:14px 0 4px 0;border-bottom:1px solid ${C.ink};font-family:${FONT};font-size:11px;font-weight:bold;letter-spacing:1.8px;text-transform:uppercase;color:${C.accent};">
        ${esc(tSection(sectionName, lang))}
        <span style="float:right;color:${C.muted};font-weight:600;letter-spacing:1px;">${items.length} item${items.length === 1 ? "" : "s"}</span>
      </tr>
      ${items
        .map((l) => {
          const rawQty = Number(l.qty) || 0;
          const wasteQty = roundUpHalf(rawQty * (1 + wastePct / 100));
          return `
        <tr style="border-bottom:1px solid ${C.line};">
          <td style="padding:8px 6px;font-family:${FONT};font-size:11px;color:${C.muted};font-family:'Courier New',monospace;white-space:nowrap;vertical-align:top;">
            ${l.ami_part ? esc(l.ami_part) : '<span style="color:' + C.faint + ';">—</span>'}
          </td>
          <td style="padding:8px 6px;font-family:${FONT};font-size:13px;color:${C.ink};vertical-align:top;">
            ${esc(tItem(l.name, lang))}
          </td>
          <td style="padding:8px 6px;font-family:${FONT};font-size:12px;color:${C.muted};text-align:center;vertical-align:top;">${esc(tUnit(l.unit, lang))}</td>
          <td style="padding:8px 6px;font-family:${FONT};font-size:13px;color:${C.ink};text-align:right;font-variant-numeric:tabular-nums;vertical-align:top;">${rawQty}</td>
          <td style="padding:8px 6px;font-family:${FONT};font-size:13px;color:${C.ink};text-align:right;font-variant-numeric:tabular-nums;font-weight:bold;vertical-align:top;">${wasteQty}</td>
        </tr>`;
        })
        .join("")}
      <tr><td colspan="3"></td>
        <td style="padding:6px 6px;font-family:${FONT};font-size:11px;color:${C.faint};text-align:right;font-variant-numeric:tabular-nums;border-top:1px solid ${C.line};">${totalRaw}</td>
        <td style="padding:6px 6px;font-family:${FONT};font-size:11px;color:${C.faint};text-align:right;font-variant-numeric:tabular-nums;border-top:1px solid ${C.line};">${roundUpHalf(totalRaw * (1 + wastePct / 100))}</td>
      </tr>
    `;
  };

  const sectionsHtml = Object.entries(linesByCat).map(sectionBlock).join("");
  const hasLines = Object.keys(linesByCat).length > 0;

  return `<!doctype html>
<html lang="${lang === "es" ? "es" : "en"}">
<head>
  <meta charset="utf-8">
  <title>Material List — ${esc(estimate.estimate_number || "")}</title>
</head>
<body style="margin:0;padding:0;background:#FFFFFF;font-family:${FONT};color:${C.ink};-webkit-font-smoothing:antialiased;">
  <div style="max-width:760px;margin:0 auto;padding:32px 36px;">
    <!-- Header -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-bottom:4px solid ${C.accent};padding-bottom:18px;margin-bottom:18px;">
      <tr>
        <td valign="middle" style="font-family:${FONT};">
          ${
            logoUrl
              ? `<img src="${logoUrl}" alt="${esc(companyName)}" height="44" style="display:block;height:44px;width:auto;max-width:200px;">`
              : `<div style="font-family:${FONT};font-size:20px;font-weight:800;color:${C.ink};">${esc(companyName)}</div>`
          }
          <div style="margin-top:6px;font-family:${FONT};font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;">Material List</div>
        </td>
        <td align="right" valign="middle" style="font-family:${FONT};">
          <div style="font-family:${FONT};font-size:10px;letter-spacing:2px;text-transform:uppercase;color:${C.faint};font-weight:bold;">Estimate</div>
          <div style="font-family:${FONT};font-size:16px;font-weight:700;color:${C.ink};">${esc(estimate.estimate_number || "—")}</div>
          <div style="font-family:${FONT};font-size:11px;color:${C.muted};">Printed ${esc(todayStr)}</div>
        </td>
      </tr>
    </table>

    <!-- Job info -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:20px;">
      <tr>
        <td width="33%" valign="top" style="padding-right:8px;">
          <div style="font-family:${FONT};font-size:9px;letter-spacing:2px;text-transform:uppercase;color:${C.faint};font-weight:bold;">Customer</div>
          <div style="font-family:${FONT};font-size:13px;font-weight:600;color:${C.ink};">${esc(estimate.customer_name || "—")}</div>
        </td>
        <td width="33%" valign="top" style="padding:0 8px;">
          <div style="font-family:${FONT};font-size:9px;letter-spacing:2px;text-transform:uppercase;color:${C.faint};font-weight:bold;">Job Address</div>
          <div style="font-family:${FONT};font-size:12px;color:${C.ink};">${esc(estimate.address || "—")}</div>
        </td>
        <td width="33%" valign="top" style="padding-left:8px;">
          <div style="font-family:${FONT};font-size:9px;letter-spacing:2px;text-transform:uppercase;color:${C.faint};font-weight:bold;">Estimator</div>
          <div style="font-family:${FONT};font-size:13px;color:${C.ink};">${esc(estimate.estimator || "—")}</div>
        </td>
      </tr>
    </table>

    <div style="background:${C.bg};border-left:3px solid ${C.accent};padding:10px 14px;margin-bottom:18px;font-family:${FONT};font-size:11px;color:${C.muted};line-height:1.5;">
      <strong style="color:${C.ink};">Order Quantity</strong> shows the qty <em>with</em> ${wastePct}% waste factor applied (rounded up). Hand this list to ${esc(supplierName)} to pull / quote materials.
    </div>

    <!-- Estimate-level color block. Blank fields show as a fillable underline
         so contractors can hand-write a color on the printed copy if needed. -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:22px;border:1px solid ${C.line};">
      <tr style="background:${C.bg};">
        <td colspan="4" style="padding:6px 12px;font-family:${FONT};font-size:9px;letter-spacing:2px;text-transform:uppercase;color:${C.faint};font-weight:bold;border-bottom:1px solid ${C.line};">
          Material Colors
        </td>
      </tr>
      <tr>
        ${[
          ["Siding", estimate.siding_color],
          ["Accessories", estimate.accessories_color],
          ["Outside Corner", estimate.outside_corner_color],
          ["Soffit / Fascia", estimate.soffit_fascia_color],
        ]
          .map(
            ([label, value]) => `
          <td width="25%" valign="top" style="padding:8px 12px;border-right:1px solid ${C.line};">
            <div style="font-family:${FONT};font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;margin-bottom:3px;">${esc(label)}</div>
            <div style="font-family:${FONT};font-size:13px;font-weight:600;color:${C.ink};min-height:18px;">${
              value ? esc(value) : '<span style="color:' + C.faint + ';font-weight:normal;">________________</span>'
            }</div>
          </td>`
          )
          .join("")}
      </tr>
    </table>

    ${
      hasLines
        ? `
    <!-- Material table -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;">
      <thead>
        <tr style="border-bottom:2px solid ${C.ink};">
          <th align="left" style="padding:6px 6px;font-family:${FONT};font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;width:90px;">AMI #</th>
          <th align="left" style="padding:6px 6px;font-family:${FONT};font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;">Description</th>
          <th align="center" style="padding:6px 6px;font-family:${FONT};font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;width:60px;">Unit</th>
          <th align="right" style="padding:6px 6px;font-family:${FONT};font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;width:70px;">Job Qty</th>
          <th align="right" style="padding:6px 6px;font-family:${FONT};font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:${C.faint};font-weight:bold;width:90px;background:${C.bg};">Order Qty<br><span style="font-size:8px;text-transform:none;letter-spacing:0;color:${C.muted};font-weight:normal;">+${wastePct}% waste</span></th>
        </tr>
      </thead>
      <tbody>
        ${sectionsHtml}
      </tbody>
    </table>
    `
        : `
    <div style="padding:32px;text-align:center;border:1px dashed ${C.line};font-family:${FONT};color:${C.muted};">
      No materials yet. Add quantities on the estimate, then print the material list.
    </div>
    `
    }

    <div style="margin-top:32px;padding-top:14px;border-top:1px solid ${C.line};font-family:${FONT};font-size:10px;color:${C.faint};text-align:center;">
      Prepared by ${esc(companyName)} · Materials supplied by ${esc(supplierName)}
    </div>
  </div>
</body>
</html>`;
}

export function materialListFilename(estimate) {
  const parts = [];
  if (estimate.estimate_number) parts.push(estimate.estimate_number);
  if (estimate.customer_name) parts.push(estimate.customer_name.replace(/\s+/g, "_"));
  parts.push("materials");
  return `${parts.join("-")}.pdf`;
}
