// Takeoff Reconciliation Card
//
// Iter 78 (LETRICK follow-up): drop-in panel rendered inside the HOVER
// import and Blueprint Read preview modals. Shows three columns per row
// so Howard can spot drift between what the AI/HOVER returned and what
// the catalog will actually quote:
//
//   • Raw measurement   — the source number (eaves_lf, siding_sqft, etc.)
//   • Formula yields    — the line-qty the catalog mapper produced
//   • Order at X% waste — formula qty × (1 + waste/100), only for items
//                         where waste applies (siding + soffit panels)
//
// Reads `measurements` + `lines` from the takeoff result and the
// estimate's `waste_pct`. Pure presentation — no side effects.
import React from "react";
import { isCutProneItem, steerLpSoffit } from "@/lib/wasteLogic";

// Items to surface, in display order. Two parallel row sets keyed by
// estimate.kind: vinyl/ascend uses the standard catalog item names;
// LP SmartSide uses the LP-specific catalog (38 Series Lap, 540 OSC,
// 440/540 Series Trim, 38 Series Soffit). Gutters / downspouts / end
// caps are shared across all siding tabs.
//
// Each entry maps:
//   label  — what the contractor sees
//   raw    — function(measurements) → "108 LF" / "1,800 ft²" / "—"
//   item   — exact catalog item name to look up in `lines`
//   tab    — which tab the line lives on
const VINYL_RECON_ROWS = [
  {
    label: "Siding",
    raw: (m) => fmtSq(m.siding_sqft),
    item: "Install Vinyl Siding",
    tab: "vinyl",
  },
  {
    label: "Outside corners",
    raw: (m) => fmtLf(m.outside_corner_lf),
    item: "Outside corners Standard color",
    tab: "vinyl",
  },
  {
    label: "Inside corners",
    raw: (m) => fmtLf(m.inside_corner_lf),
    item: "Inside Corners (Siding) Standard color",
    tab: "vinyl",
  },
  {
    label: "J-Channel",
    raw: () => "—",
    item: '3/4" J-Channel Standard color (2 per Sq of siding)',
    tab: "vinyl",
  },
  {
    label: "Finish Trim",
    raw: () => "—",
    item: "Finish Trim Standard color",
    tab: "vinyl",
  },
  {
    label: "Soffit (Charter Oak)",
    raw: (m) => fmtSqft(m.soffit_sqft),
    item: "Charter Oak Soffit Standard color",
    tab: "vinyl",
  },
  {
    label: "Soffit J-Channel",
    raw: () => "—",
    item: '3/4" Soffit J-Channel (Charter Oak) Standard color',
    tab: "vinyl",
  },
  {
    label: "Gutter",
    raw: (m) => fmtLf(m.eaves_lf),
    item: 'Gutter 6"',
    tab: "vinyl",
  },
  {
    label: "Downspouts",
    raw: () => "—",
    item: 'Downspout 6"',
    tab: "vinyl",
  },
  {
    label: "End caps",
    raw: () => "—",
    item: "End Cap",
    tab: "vinyl",
  },
];

// LP SmartSide rows — uses the LP factory-finish catalog.
const LP_RECON_ROWS = [
  {
    label: "LP Lap Siding (38 Series)",
    raw: (m) => fmtSq(m.siding_sqft),
    item: '38 Series Lap 3/8" x 8" x 16\'',
    tab: "lp_smart",
  },
  {
    label: "Outside Corner (540 OSC)",
    raw: (m) => fmtLf(m.outside_corner_lf),
    item: "540 Series OSC 5/4\" x 4\" x 16'",
    tab: "lp_smart",
  },
  {
    label: "Trim (440 Series)",
    raw: () => "—",
    item: '440 Series Trim 4/4" x 4" x 16\'',
    tab: "lp_smart",
  },
  {
    label: "Trim (540 Series)",
    raw: () => "—",
    item: '540 Series Trim 5/4" x 4" x 16\'',
    tab: "lp_smart",
  },
  {
    label: "Soffit Vented (38 Series)",
    raw: (m) => fmtSqft(m.soffit_sqft),
    item: "38 Series Soffit 16 x 16 Vented",
    tab: "lp_smart",
  },
  {
    label: "Soffit Closed (38 Series)",
    raw: () => "—",
    item: "38 Series Soffit 16 x 16 Closed",
    tab: "lp_smart",
  },
  {
    label: "Coil (.019)",
    raw: () => "—",
    item: ".019 Coil",
    tab: "lp_smart",
  },
  {
    label: "Gutter",
    raw: (m) => fmtLf(m.eaves_lf),
    item: 'Gutter 6"',
    tab: "lp_smart",
  },
  {
    label: "Downspouts",
    raw: () => "—",
    item: 'Downspout 6"',
    tab: "lp_smart",
  },
  {
    label: "End caps",
    raw: () => "—",
    item: "End Cap",
    tab: "lp_smart",
  },
];

const num = (v) => (v == null ? null : Number(v));
const fmt = (v, decimals = 0) =>
  v == null || isNaN(Number(v))
    ? "—"
    : Number(v).toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: decimals,
      });
const fmtLf = (v) => (v == null ? "—" : `${fmt(v, 0)} LF`);
const fmtSqft = (v) => (v == null ? "—" : `${fmt(v, 0)} ft²`);
const fmtSq = (v) => {
  const n = num(v);
  if (n == null || isNaN(n)) return "—";
  return `${(n / 100).toFixed(1)} SQ`;
};

const roundUpHalf = (n) => {
  const x = Number(n);
  if (!isFinite(x) || x <= 0) return 0;
  return Math.ceil(x * 2) / 2;
};

// Iter 78g — compute total window perimeter from HOVER measurements.
// Mirrors backend `_window_perim_total_lf` in routes/hover.py so the
// recon card and the takeoff mapper agree.
const WINDOW_PERIM_LF_FALLBACK = 14.0;
const windowPerimTotalLf = (m) => {
  const wins = Array.isArray(m?.windows) ? m.windows : [];
  if (wins.length) {
    const perimIn = wins.reduce(
      (s, w) => s + 2 * ((Number(w?.width_in) || 0) + (Number(w?.height_in) || 0)),
      0,
    );
    return perimIn / 12;
  }
  return (Number(m?.window_count) || 0) * WINDOW_PERIM_LF_FALLBACK;
};

// Iter 78g — small horizontal stacked-bar coverage breakdown. Each
// segment is colored, labeled with its LF value, and proportional to
// its share of the total. Spot-checking aid for Howard to catch HOVER
// mis-reads before sending a quote.
function CoverageBar({ label, segments, totalLf, pcs, unit, formula }) {
  const total = segments.reduce((s, x) => s + (Number(x.lf) || 0), 0);
  if (total <= 0) return null;
  return (
    <div className="mb-2.5 last:mb-0" data-testid={`coverage-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[11px] font-bold text-[#09090B]">{label}</span>
        <span className="text-[10px] font-mono-num text-[#52525B]">
          {total.toFixed(0)} LF ÷ 12.5 = <span className="font-bold text-[#09090B]">{pcs} {unit}</span>
        </span>
      </div>
      <div className="flex h-5 w-full border border-[#E4E4E7] overflow-hidden">
        {segments.map((seg) => {
          const lf = Number(seg.lf) || 0;
          if (lf <= 0) return null;
          const pct = (lf / total) * 100;
          return (
            <div
              key={seg.label}
              className="flex items-center justify-center text-[10px] text-white font-mono-num"
              style={{ width: `${pct}%`, backgroundColor: seg.color, minWidth: 0 }}
              title={`${seg.label}: ${lf.toFixed(0)} LF`}
            >
              {pct >= 12 ? `${lf.toFixed(0)}` : ""}
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
        {segments.filter((s) => (Number(s.lf) || 0) > 0).map((seg) => (
          <span key={seg.label} className="flex items-center gap-1 text-[10px] text-[#52525B]">
            <span className="inline-block w-2 h-2" style={{ backgroundColor: seg.color }} />
            <span>{seg.label} <span className="font-mono-num text-[#71717A]">{seg.detail}</span></span>
          </span>
        ))}
      </div>
      {formula && (
        <div className="text-[10px] font-mono-num text-[#A1A1AA] mt-0.5">{formula}</div>
      )}
    </div>
  );
}

export default function TakeoffReconCard({ measurements, lines, wastePct = 0, kind = "siding", lpSoffitType = "mix" }) {
  if (!measurements || !lines || !lines.length) return null;
  const pct = Math.max(0, Number(wastePct) || 0);
  // Iter 78 — apply the LP soffit steering for the preview so Howard
  // sees exactly what will land on the estimate after Apply.
  const steeredLines = kind === "lp_smart" ? steerLpSoffit(lines, lpSoffitType) : lines;
  const rowSet = kind === "lp_smart" ? LP_RECON_ROWS : VINYL_RECON_ROWS;

  // Build a quick lookup: item name (lowercase) → first matching line.
  // Prefer same-tab matches; fall back to any tab so kind=ascend or
  // kind=lp estimates still surface a row.
  const byName = (name, tab) => {
    const lc = (name || "").toLowerCase();
    return (
      lines.find(
        (l) =>
          (l.name || "").toLowerCase() === lc && (l.tab || "vinyl") === tab
      ) ||
      lines.find((l) => (l.name || "").toLowerCase() === lc) ||
      null
    );
  };

  const rows = rowSet.map((r) => {
    const ln = byName(r.item, r.tab);
    if (!ln) return null;
    const qty = Number(ln.qty) || 0;
    const rawQty = Number(ln.raw_qty);
    const unit = ln.unit || "";
    // Iter 78 — waste is baked into qty on apply (via bakeWasteIntoLines).
    // Two scenarios:
    //   1) PRE-apply (preview modal): line has raw qty in `qty` and no
    //      `raw_qty` field. Simulate the waste for display so Howard sees
    //      what the estimate WILL look like after Apply.
    //   2) POST-apply (line already on the estimate): qty has waste baked
    //      in; raw_qty carries the original measurement.
    const hasRaw = isFinite(rawQty) && rawQty > 0;
    let formulaQty;
    let orderQty;
    if (hasRaw) {
      formulaQty = rawQty;
      orderQty = qty;
    } else if (isCutProneItem(ln)) {
      formulaQty = qty;
      orderQty = roundUpHalf(qty * (1 + pct / 100));
    } else {
      formulaQty = qty;
      orderQty = qty;
    }
    return {
      label: r.label,
      raw: r.raw(measurements),
      formula: formulaQty > 0 ? `${fmt(formulaQty, 1)} ${unit}` : "—",
      order: orderQty > 0 ? `${fmt(orderQty, 1)} ${unit}` : "—",
      drift: orderQty > formulaQty,
    };
  }).filter(Boolean);

  if (!rows.length) return null;

  // Iter 78g — Coverage breakdown for Finish Trim + Soffit J-Channel.
  // Vinyl/Ascend only — LP catalog doesn't use these item names. Computes
  // the LF contribution of each surface and renders compact stacked bars
  // so Howard can spot drift in the source measurements at a glance.
  const finishTrimLine = kind === "lp_smart" ? null : (
    byName("Finish Trim Standard color", "vinyl") ||
    byName("ASCEND Finish Trim", "ascend")
  );
  const soffitJLine = kind === "lp_smart" ? null : byName(
    '3/4" Soffit J-Channel (Charter Oak) Standard color',
    "vinyl",
  );
  const eavesLf = Number(measurements?.eaves_lf) || 0;
  const rakesLf = Number(measurements?.rakes_lf) || 0;
  const winPerim = windowPerimTotalLf(measurements);
  const winSrc = (measurements?.windows?.length || 0) > 0
    ? `${measurements.windows.length} dims`
    : `${Number(measurements?.window_count) || 0} wins × 14 LF`;

  const showCoverage = finishTrimLine || soffitJLine;

  return (
    <section
      className="p-5 border-b border-[#E4E4E7] bg-white"
      data-testid="takeoff-recon-card"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider font-bold text-[#A1A1AA]">
          Takeoff Reconciliation
        </div>
        <div className="text-[10px] uppercase tracking-wider text-[#71717A]">
          Waste · <span className="font-bold text-[#09090B]">{pct}%</span>{" "}
          <span className="text-[#A1A1AA]">(Siding + Soffit panels only)</span>
        </div>
      </div>
      <p className="text-[11px] text-[#52525B] leading-snug mb-3">
        AI reads the raw measurements; the catalog mapper converts them to
        line quantities; the Order column applies the waste factor so you
        can spot drift against what you&apos;d actually need to order.
      </p>
      <div className="border border-[#E4E4E7] overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-[#FAFAFA] text-[10px] uppercase tracking-wider text-[#71717A]">
            <tr>
              <th className="text-left px-3 py-2">Item</th>
              <th className="text-right px-3 py-2 w-32">AI raw</th>
              <th className="text-right px-3 py-2 w-32">Formula yields</th>
              <th className="text-right px-3 py-2 w-36">
                Order @ {pct}% waste
              </th>
            </tr>
          </thead>
          <tbody className="font-mono-num">
            {rows.map((r, i) => (
              <tr
                key={r.label}
                className={i % 2 ? "bg-white" : "bg-[#FAFAFA]"}
                data-testid={`recon-row-${r.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
              >
                <td className="px-3 py-1.5 text-[#09090B] font-bold font-sans">
                  {r.label}
                </td>
                <td className="px-3 py-1.5 text-right text-[#52525B]">{r.raw}</td>
                <td className="px-3 py-1.5 text-right text-[#09090B]">
                  {r.formula}
                </td>
                <td
                  className={`px-3 py-1.5 text-right ${
                    r.drift ? "text-[#F97316] font-bold" : "text-[#09090B]"
                  }`}
                >
                  {r.order}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showCoverage && (
        <div className="mt-4 pt-3 border-t border-[#E4E4E7]" data-testid="coverage-breakdown">
          <div className="text-[10px] uppercase tracking-wider font-bold text-[#A1A1AA] mb-2">
            Coverage Breakdown
          </div>
          <p className="text-[11px] text-[#52525B] leading-snug mb-3">
            Spot-check the source LF each piece count is built from. If a
            segment looks off vs the home, the underlying HOVER measurement
            (eaves / rakes / window dims) likely needs a second look.
          </p>
          {finishTrimLine && (
            <CoverageBar
              label="Finish Trim"
              segments={[
                { label: "Eaves run", lf: eavesLf, detail: `${eavesLf.toFixed(0)} LF`, color: "#0EA5E9" },
                { label: "Window perimeter", lf: winPerim, detail: `${winPerim.toFixed(0)} LF · ${winSrc}`, color: "#A855F7" },
              ]}
              pcs={Number(finishTrimLine.qty) || 0}
              unit={finishTrimLine.unit || "PCS"}
              formula="Formula: ceil((Eaves + Full Window Perim) ÷ 12.5)"
            />
          )}
          {soffitJLine && (
            <CoverageBar
              label="Soffit J-Channel"
              segments={[
                { label: "Eaves run", lf: eavesLf, detail: `${eavesLf.toFixed(0)} LF`, color: "#0EA5E9" },
                { label: "Rake @ 2 passes", lf: rakesLf * 2, detail: `2 × ${rakesLf.toFixed(0)} LF rake`, color: "#F97316" },
              ]}
              pcs={Number(soffitJLine.qty) || 0}
              unit={soffitJLine.unit || "PCS"}
              formula="Formula: ceil((Eaves + 2 × Rakes) ÷ 12.5) — 2 passes per rake (wall side + fascia return)"
            />
          )}
        </div>
      )}
    </section>
  );
}
