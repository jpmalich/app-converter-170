import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { SheetSvg } from "@/pages/ElevationSheet";

/* PRINT PACKAGE — EL-1..EL-4 in one print flow (Howard, authorized
   2026-07-20). Read-only: reuses SheetSvg verbatim, so printed sheets are
   IDENTICAL to on-screen sheets. One sheet per printed page (landscape,
   letter). Walls the run can't render get a NAMED block — never silently
   absent from the package. */

const SHEETS = ["front", "left", "back", "right"];
const CODES = { front: "EL-1", left: "EL-2", back: "EL-3", right: "EL-4" };

export default function ElevationSheetsPrint() {
  const { id } = useParams();
  const [sheets, setSheets] = useState(null);

  useEffect(() => {
    Promise.allSettled(SHEETS.map((w) => api.get(`/estimates/${id}/elevation-sheet/${w}`)))
      .then((rs) => setSheets(rs.map((r, i) => (r.status === "fulfilled"
        ? { which: SHEETS[i], data: r.value.data }
        : { which: SHEETS[i], error: r.reason?.response?.data?.detail || "Failed to load sheet" }))));
  }, [id]);

  const loaded = !!sheets;
  const okCount = (sheets || []).filter((s) => s.data).length;

  // One-click flow: the print dialog fires once, after all four fetches
  // settle and the SVGs have painted.
  useEffect(() => {
    if (loaded && okCount > 0) {
      const t = setTimeout(() => window.print(), 800);
      return () => clearTimeout(t);
    }
  }, [loaded, okCount]);

  if (!loaded) {
    return <div className="p-8 text-sm" data-testid="elevation-sheets-print-loading">Rendering sheets…</div>;
  }
  if (okCount === 0) {
    return (
      <div className="p-8 text-sm" data-testid="elevation-sheets-print-empty">
        No elevation sheets render for this estimate — {sheets[0]?.error}
      </div>
    );
  }
  return (
    <div className="min-h-screen bg-[#e8eaee] py-6 flex flex-col items-center gap-6" data-testid="elevation-sheets-print-page">
      {/* print-scoped page setup: applies ONLY while this page is mounted —
          other print flows (quote, takeoff) keep their own defaults */}
      <style>{`@media print {
        @page { size: letter landscape; margin: 0.2in; }
        header, footer { display: none !important; }
        [data-testid="elevation-sheets-print-page"] { padding: 0 !important; gap: 0 !important; background: #fff !important; min-height: 0 !important; }
        .print-sheet-page { page-break-after: always; break-inside: avoid; }
        .print-sheet-page:last-child { page-break-after: auto; }
        .print-sheet-page svg { width: 10.4in !important; height: auto !important; box-shadow: none !important; }
      }`}</style>
      <div className="flex items-center gap-4 print:hidden">
        <Link to={`/estimate/${id}`} className="text-xs underline" data-testid="elevation-sheets-print-back">← Back to estimate</Link>
        <button type="button" className="text-xs underline" onClick={() => window.print()} data-testid="elevation-sheets-print-btn">
          Print all {okCount} sheets
        </button>
        <span className="text-xs text-[#71717A]" data-testid="elevation-sheets-print-count">
          Print package — {okCount} of 4 elevations render for this estimate
        </span>
      </div>
      {sheets.map((s) => (s.data ? (
        <div key={s.which} className="print-sheet-page" data-testid={`print-sheet-${s.which}`}>
          <SheetSvg data={s.data} />
        </div>
      ) : (
        <div
          key={s.which}
          className="print-sheet-page w-[1056px] max-w-full bg-white border border-dashed border-[#A1A1AA] p-8 text-sm text-[#52525B]"
          data-testid={`print-sheet-missing-${s.which}`}
        >
          <span className="font-bold uppercase tracking-wider">{CODES[s.which]} {s.which} — not renderable: </span>
          {s.error}
        </div>
      )))}
    </div>
  );
}
