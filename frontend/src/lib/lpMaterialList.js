// Iter 99 — ONE-SURFACE RULE (Howard ruling): for LP estimates the
// printable Material List composes from the DERIVED PACKAGE — the exact
// payload the Material List tab renders (colors + session substitutions
// included) — never from stored legacy lines. Sell prices only; lines
// without a cost basis print "PRICING PENDING", never $0.
const FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif";
const C = {
  ink: "#09090B", muted: "#52525B", faint: "#71717A",
  line: "#D4D4D8", accent: "#F97316", accentText: "#C2410C", bg: "#FAFAFA",
};

const esc = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const money = (n) =>
  `$${Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function buildLpMaterialListHtml({ pkg, estimate, company, branding, lang = "en", share = null }) {
  const es = lang === "es";
  const bySection = {};
  (pkg.lines || []).forEach((l) => {
    (bySection[l.section] = bySection[l.section] || []).push(l);
  });
  const pricing = pkg.summary?.pricing || {};
  const groupColors = pkg.summary?.group_colors || {};
  const colorLine = Object.entries(groupColors)
    .filter(([, v]) => v)
    .map(([g, v]) => `${g.replace("_", " ")}: ${v}`)
    .join(" · ");

  const sectionBlock = ([section, lines]) => `
    <tr><td colspan="6" style="padding:10px 8px 4px;font-size:10px;font-weight:700;
      letter-spacing:0.08em;text-transform:uppercase;color:${C.accentText};
      border-bottom:1px solid ${C.line};">${esc(section)}</td></tr>
    ${lines
      .map((l) => {
        const priced = l.pricing_status === "priced";
        const sub = l.substituted_from
          ? `<div style="font-size:8.5px;color:${C.faint};">${es ? "sustituido de" : "substituted from"} ${esc(l.substituted_from)} — re-derived</div>`
          : "";
        return `
      <tr style="border-bottom:1px solid ${C.line};">
        <td style="padding:6px 8px;font-size:10px;color:${C.ink};">${esc(l.name)}${sub}</td>
        <td style="padding:6px 8px;font-size:9.5px;color:${C.muted};">${esc(l.color || "—")}</td>
        <td style="padding:6px 8px;font-size:10px;text-align:right;">${esc(l.qty)}</td>
        <td style="padding:6px 8px;font-size:9.5px;color:${C.muted};">${esc(l.unit)}</td>
        <td style="padding:6px 8px;font-size:10px;text-align:right;">${
          priced ? money(l.unit_sell) : `<span style="color:${C.accentText};font-size:8.5px;font-weight:700;">${es ? "PRECIO PENDIENTE" : "PRICING PENDING"}</span>`
        }</td>
        <td style="padding:6px 8px;font-size:10px;text-align:right;font-weight:600;">${
          priced ? money(l.line_sell) : "—"
        }</td>
      </tr>`;
      })
      .join("")}`;

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    @page { size: Letter; margin: 14mm 12mm; }
    body { font-family:${FONT}; color:${C.ink}; margin:0; }
  </style></head><body>
    <div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:3px solid ${C.accent};padding-bottom:10px;">
      <div>
        <div style="font-size:16px;font-weight:800;letter-spacing:0.04em;">${es ? "LISTA DE MATERIALES" : "MATERIAL LIST"} — LP SMARTSIDE</div>
        <div style="font-size:10px;color:${C.muted};margin-top:2px;">
          ${esc(company?.name || branding?.supplier_name || "")}</div>
      </div>
      <div style="text-align:right;font-size:10px;color:${C.muted};">
        <div style="font-weight:700;color:${C.ink};">${esc(estimate?.estimate_number || "")}</div>
        <div>${esc(estimate?.customer_name || "")}</div>
        <div>${esc(estimate?.address || "")}</div>
        <div>${esc(estimate?.estimate_date || "")}</div>
      </div>
    </div>
    <div style="font-size:8.5px;color:${C.faint};margin:6px 0 10px;">
      ${es ? "Derivada de mediciones IA confirmadas" : "Derived from confirmed AI measurements"}
      — run ${esc(String(pkg.run_id || "").slice(0, 8))} · ${es ? "fuente única" : "single source"}
      ${colorLine ? ` · ${esc(colorLine)}` : ""}
    </div>
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr style="background:${C.bg};border-bottom:2px solid ${C.ink};">
        ${[es ? "Artículo" : "Item", "Color", es ? "Cant." : "Qty", es ? "Unidad" : "Unit", "Unit $", es ? "Total $" : "Line $"]
          .map((h, i) => `<th style="padding:6px 8px;font-size:9px;letter-spacing:0.08em;text-transform:uppercase;color:${C.muted};text-align:${i >= 2 && i !== 3 ? "right" : "left"};">${h}</th>`)
          .join("")}
      </tr></thead>
      <tbody>${Object.entries(bySection).map(sectionBlock).join("")}</tbody>
    </table>
    <div style="display:flex;justify-content:flex-end;gap:24px;margin-top:12px;padding-top:8px;border-top:2px solid ${C.ink};">
      ${pricing.pending_lines > 0
        ? `<div style="font-size:9px;color:${C.accentText};align-self:center;">${pricing.pending_lines} ${es ? "línea(s) con precio pendiente" : "line(s) pricing pending"}</div>`
        : ""}
      <div style="font-size:12px;font-weight:800;">${es ? "Total de materiales" : "Materials total"}: ${money(pricing.total_sell)}</div>
    </div>
    ${share ? `
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:16px;padding-top:10px;border-top:1px solid ${C.line};">
      <div style="font-size:8.5px;color:${C.faint};">
        <div style="font-weight:700;color:${C.muted};text-transform:uppercase;letter-spacing:0.08em;font-size:8px;">${es ? "Copia digital de ESTA lista impresa" : "Digital copy of THIS printed list"}</div>
        <div style="margin-top:2px;max-width:420px;">${es
          ? "El código QR abre exactamente la versión congelada aquí impresa — si el estimado cambia después, la página avisará que existe una lista más reciente."
          : "The QR opens the exact frozen version printed here — if the estimate changes later, the page will flag that a newer list exists."}</div>
        <div style="margin-top:2px;">${esc(share.shareUrl)} · ${es ? "impreso" : "printed"} ${esc(new Date(share.printedAt).toLocaleDateString(es ? "es" : "en-US"))}</div>
      </div>
      <img src="${share.qrDataUrl}" width="76" height="76" style="width:76px;height:76px;flex:none;" />
    </div>` : ""}
  </body></html>`;
}
