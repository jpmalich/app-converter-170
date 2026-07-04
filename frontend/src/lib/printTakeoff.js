// Iter 78z++++ — Print helper for the HOVER / Blueprint / AI / ISS
// takeoff preview modals. Opens a new window, writes a self-contained
// styled HTML doc with the extracted measurements + line items, then
// fires the print dialog. The contractor walks away with a hard copy
// they can hand to a crew or staple into a job folder.
//
// Pure presentation — no API calls, no PDF backend round-trip. Works
// even if the contractor is offline once the preview modal is on
// screen.

const esc = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const fmtNum = (n) => {
  if (n === null || n === undefined || n === "") return "—";
  if (typeof n !== "number") return esc(n);
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
};

// Same KEY_LABELS as HoverImportButton — copied here so the printable
// doc isn't tied to that file's internal map. Add more as needed.
const KEY_LABELS = {
  siding_sqft: "Siding (ft²)",
  outside_corner_lf: "Outside Corners (LF)",
  inside_corner_lf: "Inside Corners (LF)",
  eaves_lf: "Eaves (LF)",
  rakes_lf: "Rakes (LF)",
  soffit_sqft: "Soffit (ft²)",
  fascia_lf: "Fascia (LF)",
  gutter_lf: "Gutters (LF)",
  downspouts_count: "Downspouts (count)",
  window_count: "Windows (count)",
  door_count: "Doors (count)",
  perimeter_lf: "Perimeter (LF)",
  brick_sqft: "Brick wainscot (ft²)",
  stone_sqft: "Stone wainscot (ft²)",
  shake_sqft: "Shake (ft²)",
  board_batten_sqft: "Board & Batten (ft²)",
};

const UNIT_BY_KEY = (k) => {
  if (k.endsWith("_sqft")) return "ft²";
  if (k.endsWith("_lf")) return "LF";
  if (k.endsWith("_count")) return "";
  return "";
};

const TAB_LABELS = {
  vinyl: "Vinyl Siding",
  ascend: "Ascend Composite",
  lp_smart: "LP SmartSide",
  windows: "Windows",
  iss: "ISS Quote",
};

function renderMeasurementsHtml(measurements) {
  const entries = Object.entries(measurements || {}).filter(
    ([k, v]) =>
      v !== null &&
      v !== undefined &&
      v !== "" &&
      typeof v !== "object" &&
      !k.startsWith("_")
  );
  if (!entries.length) return "";
  return `
    <section class="block">
      <div class="block-title">Extracted Measurements</div>
      <div class="grid">
        ${entries
          .map(
            ([k, v]) => `
          <div class="cell">
            <div class="cell-label">${esc(KEY_LABELS[k] || k)}</div>
            <div class="cell-value">${fmtNum(v)} ${esc(UNIT_BY_KEY(k))}</div>
          </div>`
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderLinesHtml(lines, kind) {
  if (!lines || !lines.length) return "";
  if (kind === "iss") {
    // ISS: single flat table.
    return `
      <section class="block">
        <div class="block-title">ISS Quote — Auto-generated Line Items (${lines.length})</div>
        <table>
          <thead>
            <tr>
              <th>Section</th>
              <th>Item</th>
              <th class="num">Qty</th>
              <th>Unit</th>
            </tr>
          </thead>
          <tbody>
            ${lines
              .map(
                (l) => `
              <tr>
                <td class="muted">${esc(l.section || "")}</td>
                <td>
                  <div>${esc(l.name || "")}</div>
                  ${l.note ? `<div class="muted small">${esc(l.note)}</div>` : ""}
                </td>
                <td class="num bold">${esc(l.qty)}</td>
                <td class="muted">${esc(l.unit || "")}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </section>
    `;
  }
  // Multi-tab (siding/windows): group by tab.
  const byTab = {};
  lines.forEach((l) => {
    const t = l.tab || "vinyl";
    (byTab[t] = byTab[t] || []).push(l);
  });
  return ["vinyl", "ascend", "lp_smart", "windows"]
    .filter((t) => byTab[t] && byTab[t].length)
    .map(
      (t) => `
      <section class="block">
        <div class="block-title">${esc(TAB_LABELS[t] || t)} — ${byTab[t].length} line${byTab[t].length === 1 ? "" : "s"}</div>
        <table>
          <thead>
            <tr>
              <th>Section</th>
              <th>Item</th>
              <th class="num">Qty</th>
              <th>Unit</th>
            </tr>
          </thead>
          <tbody>
            ${byTab[t]
              .map(
                (l) => `
              <tr>
                <td class="muted">${esc(l.section || "")}</td>
                <td>
                  <div>${esc(l.name || "")}</div>
                  ${l.note ? `<div class="muted small">${esc(l.note)}</div>` : ""}
                </td>
                <td class="num bold">${esc(l.qty)}</td>
                <td class="muted">${esc(l.unit || "")}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </section>
    `
    )
    .join("");
}

function renderOpeningsHtml(openings) {
  if (!openings || !openings.length) return "";
  return `
    <section class="block">
      <div class="block-title">Window Openings (${openings.length})</div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th class="num">W (in)</th>
            <th class="num">H (in)</th>
            <th class="num">UI</th>
            <th>Style</th>
          </tr>
        </thead>
        <tbody>
          ${openings
            .map(
              (o) => `
            <tr>
              <td class="muted">${esc(o.hover_id || o.id || "")}</td>
              <td class="num">${esc(o.width)}</td>
              <td class="num">${esc(o.height)}</td>
              <td class="num muted">${esc(Math.round((o.width || 0) + (o.height || 0)))}</td>
              <td>${esc(o.style || o.product || "—")}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </section>
  `;
}

/**
 * Open a new window with a printable takeoff sheet.
 *
 * @param {object} opts
 * @param {"HOVER"|"Blueprint"|"AI Photo Measure"} opts.source — banner label
 * @param {object} opts.measurements — measurements map
 * @param {Array<object>} [opts.lines] — auto-generated line items
 * @param {Array<object>} [opts.openings] — window openings (HOVER schedule)
 * @param {object} [opts.est] — estimate (customer / address / number)
 * @param {string} [opts.kind] — "siding" | "windows" | "lp_smart" | "iss"
 */
export function printTakeoff({
  source = "Takeoff",
  measurements = {},
  lines = [],
  openings = [],
  est = {},
  kind = "siding",
}) {
  const customer = est?.customer_name || "Untitled";
  const address = est?.address || "—";
  const estNum = est?.estimate_number || "Draft";
  const now = new Date().toLocaleString();

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>${esc(source)} Takeoff Preview — ${esc(customer)} (${esc(estNum)})</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #09090B;
      margin: 0;
      padding: 20px 28px;
      font-size: 12px;
      line-height: 1.4;
    }
    .header {
      border-bottom: 2px solid #09090B;
      padding-bottom: 14px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
    }
    .header h1 {
      font-size: 20px;
      margin: 0 0 4px 0;
      font-weight: 800;
      letter-spacing: 0.01em;
    }
    .header .source-tag {
      display: inline-block;
      background: #F97316;
      color: #09090B;
      padding: 2px 8px;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }
    .header .meta {
      font-size: 11px;
      color: #52525B;
    }
    .header .meta strong { color: #09090B; }
    .header .right {
      text-align: right;
      font-size: 10px;
      color: #71717A;
      text-transform: uppercase;
      letter-spacing: 0.16em;
    }
    .block {
      margin-bottom: 22px;
      page-break-inside: avoid;
    }
    .block-title {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: #C2410C;
      border-bottom: 1px solid #09090B;
      padding-bottom: 3px;
      margin-bottom: 8px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
    }
    .cell {
      border: 1px solid #E4E4E7;
      padding: 6px 8px;
    }
    .cell-label {
      font-size: 9px;
      color: #71717A;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }
    .cell-value {
      font-weight: 700;
      font-size: 13px;
      font-variant-numeric: tabular-nums;
      color: #09090B;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th {
      text-align: left;
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #71717A;
      padding: 4px 6px;
      border-bottom: 1px solid #09090B;
      font-weight: 700;
    }
    td {
      padding: 5px 6px;
      border-bottom: 1px solid #F4F4F5;
      vertical-align: top;
    }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    td.muted { color: #52525B; }
    td.bold { font-weight: 700; color: #09090B; }
    td .small { font-size: 10px; }
    .footer {
      margin-top: 28px;
      padding-top: 10px;
      border-top: 1px solid #E4E4E7;
      font-size: 9px;
      color: #71717A;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      display: flex;
      justify-content: space-between;
    }
    @media print {
      body { padding: 14px; }
      .header { margin-bottom: 12px; }
      .block { margin-bottom: 14px; }
    }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="source-tag">${esc(source)} Takeoff Preview</div>
      <h1>${esc(customer)}</h1>
      <div class="meta">
        <strong>Address:</strong> ${esc(address)} &nbsp;·&nbsp;
        <strong>Estimate #:</strong> ${esc(estNum)} &nbsp;·&nbsp;
        <strong>Kind:</strong> ${esc(TAB_LABELS[kind] || kind)}
      </div>
    </div>
    <div class="right">
      <div>Printed</div>
      <div style="color:#09090B;font-weight:700;font-size:11px;">${esc(now)}</div>
    </div>
  </div>

  ${renderMeasurementsHtml(measurements)}
  ${renderLinesHtml(lines, kind)}
  ${renderOpeningsHtml(openings)}

  <div class="footer">
    <div>Source: ${esc(source)}</div>
    <div>Verify all quantities before ordering</div>
  </div>

  <script>
    // Fire the print dialog as soon as the doc renders. Close the
    // window automatically once the user dismisses the dialog.
    window.addEventListener("load", () => {
      setTimeout(() => {
        window.focus();
        window.print();
      }, 80);
    });
    window.addEventListener("afterprint", () => {
      setTimeout(() => window.close(), 200);
    });
  </script>
</body>
</html>`;

  const w = window.open("", "_blank", "width=900,height=1000");
  if (!w) {
    // Pop-up blocker stopped us. Fall back to a printable iframe in
    // the current document.
    const iframe = document.createElement("iframe");
    iframe.style.position = "fixed";
    iframe.style.right = "0";
    iframe.style.bottom = "0";
    iframe.style.width = "0";
    iframe.style.height = "0";
    iframe.style.border = "0";
    document.body.appendChild(iframe);
    const idoc = iframe.contentWindow.document;
    idoc.open();
    idoc.write(html);
    idoc.close();
    setTimeout(() => {
      iframe.contentWindow.focus();
      iframe.contentWindow.print();
      setTimeout(() => document.body.removeChild(iframe), 1000);
    }, 200);
    return;
  }
  w.document.open();
  w.document.write(html);
  w.document.close();
}
