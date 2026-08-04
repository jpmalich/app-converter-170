// PRINT SMOKE ENTRY (ruled 2026-08-04 — the _lang ReferenceError crash).
// Bundled by esbuild from test_print_smoke_2026_08_04.py and executed in
// node with DOM stubs (runner.cjs). ACTUALLY INVOKES the print render for
// every JS print-builder surface, per language — a ReferenceError anywhere
// in the render path crashes the run and fails the pin.
import { printTakeoff } from "/app/frontend/src/lib/printTakeoff.js";
import { buildMaterialListHtml } from "/app/frontend/src/lib/materialList.js";
import { buildLpMaterialListHtml } from "/app/frontend/src/lib/lpMaterialList.js";

export function run(lang) {
  const results = [];
  const lines = [
    { tab: "vinyl", section: "Vinyl Siding", name: "Charter Oak Dutch Lap 4.5\"", qty: 42.4, raw_qty: 38.5, unit: "SQ", mat: 100,
      note: "From HOVER 'SIDING WASTE TOTALS' — + Openings < 20ft² +10%" },
    { tab: "ascend", section: "Siding Accessories", name: "Ascend - Starter", qty: 13, unit: "PCS", mat: 10,
      note: "Per-elevation breakdown: BOARD BATTEN 2064 ft²" },
    { tab: "lp_smart", section: "LP Smart Siding", name: "38 Series 4' x 10' Panel", qty: 68, unit: "PCS", mat: 50,
      note: "waste 30% baked into qty" },
    { tab: "windows", section: "Window Installation", name: "Cap window (Windows)", qty: 32, unit: "EA", mat: 5,
      note: "install fee" },
    { tab: "iss", section: "Gutter Service", name: "ISS Service Call", qty: 1, unit: "EA", mat: 20,
      note: "service overlay" },
  ];
  const openings = [{ id: "o1", hover_id: "W-101", width: 36, height: 60, style: "Vero Double Hung" }];
  const measurements = { siding_sqft: 4239, eaves_lf: 210, window_count: 30 };
  const est = { customer_name: "PRINT SMOKE", address: "1 Test Ln", estimate_number: "EST-000000",
                waste_pct: 10, lines };

  // printTakeoff drives the PRINT button on: the HOVER restore/import
  // modal (the crash site), the ISS Hover modal (kind iss), the
  // Blueprint modal and the AI Measure modal — all four kinds walked.
  // DOOR SEPARATION ON PAPER (ruled 2026-08-04): the mixed all-family
  // line set below is EXACTLY the raw mapper output that leaked a
  // VINYL SIDING section onto EST-536665's LP printout — each kind's
  // printout must carry ONLY its own family.
  const FAMILY_MARKER = {
    siding: { must: "Charter Oak", never: ["38 Series", "Cap window", "ISS Service Call"] },
    lp_smart: { must: "38 Series", never: ["Charter Oak", "Ascend - Starter", "Cap window"] },
    windows: { must: "Cap window", never: ["Charter Oak", "38 Series", "ISS Service Call"] },
    iss: { must: "ISS Service Call", never: ["Charter Oak", "38 Series", "Cap window"] },
  };
  for (const [surface, kind] of [
    ["hover-restore-modal", "siding"],
    ["hover-lp-modal", "lp_smart"],
    ["blueprint-ai-modal", "windows"],
    ["iss-modal", "iss"],
  ]) {
    globalThis.__printCapture = "";
    printTakeoff({ source: "HOVER", measurements, lines, openings, est, kind });
    if (!globalThis.__printCapture.includes("<html")) throw new Error(surface + ": no html written");
    const m = FAMILY_MARKER[kind];
    if (!globalThis.__printCapture.includes(m.must)) throw new Error(surface + ": own-family lines missing");
    for (const alien of m.never) {
      if (globalThis.__printCapture.includes(alien)) {
        throw new Error(surface + `: CROSS-FAMILY LEAK on the printout — '${alien}' (kind ${kind})`);
      }
    }
    results.push(surface);
  }

  // Estimate page + ISS editor material-list print
  const mlHtml = buildMaterialListHtml({
    estimate: { ...est, lines: [{ ...lines[0], contractor_note: "hand note" }, ...lines.slice(1)] },
    company: { name: "Test Co" }, branding: {}, lang,
  });
  if (!mlHtml.includes("<html")) throw new Error("estimate-material-list: no html");
  results.push("estimate-material-list");

  // LP Material List panel print (derived package surface)
  const lpHtml = buildLpMaterialListHtml({
    pkg: { lines: [{ section: "LP Smart Siding", name: "38 Series 4' x 10' Panel", qty: 68, unit: "PCS", color: "Snowscape" }],
           run_id: "hover-12345678", summary: {} },
    estimate: est, company: { name: "Test Co" }, branding: {}, lang,
  });
  if (!lpHtml.includes("MATERIAL")) throw new Error("lp-material-list: no html");
  results.push("lp-material-list");

  return results;
}
