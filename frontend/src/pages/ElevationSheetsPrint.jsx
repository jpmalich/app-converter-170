import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { SheetSvg } from "@/pages/ElevationSheet";

/* PRINT PACKAGE — EL-1..EL-4 in one print flow (Howard, authorized
   2026-07-20). Read-only: reuses SheetSvg verbatim, so printed sheets are
   IDENTICAL to on-screen sheets. One sheet per printed page (landscape,
   letter). Walls the run can't render get a NAMED block — never silently
   absent from the package.

   COVER STRIP (authorized 2026-07-20): page-1 strip — customer · address ·
   methodology line · latest Tape Check accuracy %. PROVENANCE RULE applies:
   the figure binds the estimate's real tape-check record (accuracy_pct +
   scored_at from history) and renders ONLY where a record exists — no
   record, "not yet field-scored". No hardcoded scores anywhere. */

const SHEETS = ["front", "left", "back", "right"];
const CODES = { front: "EL-1", left: "EL-2", back: "EL-3", right: "EL-4" };

// Pitch language — approved wording for the Accuracy Report PDF (PRD,
// user-approved Jul 8 2026), reused verbatim pending Howard's sign-off
// for this surface.
const METHODOLOGY_LINE = "AI reads scored against contractor tape, per wall, per run.";

export default function ElevationSheetsPrint() {
  const { id } = useParams();
  const [sheets, setSheets] = useState(null);
  const [tapeLatest, setTapeLatest] = useState(null); // last history entry or null

  useEffect(() => {
    Promise.allSettled(SHEETS.map((w) => api.get(`/estimates/${id}/elevation-sheet/${w}`)))
      .then((rs) => setSheets(rs.map((r, i) => (r.status === "fulfilled"
        ? { which: SHEETS[i], data: r.value.data }
        : { which: SHEETS[i], error: r.reason?.response?.data?.detail || "Failed to load sheet" }))));
    api.get(`/estimates/${id}/tape-check`)
      .then(({ data }) => {
        const h = data?.history || [];
        setTapeLatest(h.length ? h[h.length - 1] : null);
      })
      .catch(() => setTapeLatest(null));
  }, [id]);

  const loaded = !!sheets;
  const okCount = (sheets || []).filter((s) => s.data).length;
  const firstOk = (sheets || []).find((s) => s.data);

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
  const scored = tapeLatest && tapeLatest.accuracy_pct != null;
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
        .print-sheet-page.has-cover svg { width: 9.2in !important; }
        .print-cover-strip { width: 9.2in !important; box-shadow: none !important; padding-top: 0.06in !important; padding-bottom: 0.06in !important; }
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
        <div key={s.which} className={`print-sheet-page flex flex-col items-center gap-2${s === firstOk ? " has-cover" : ""}`} data-testid={`print-sheet-${s.which}`}>
          {s === firstOk && (
            <div
              className="print-cover-strip w-[1056px] max-w-full bg-white border-2 border-[#1a2332] px-5 py-2.5 flex items-center justify-between gap-4"
              style={{ boxShadow: "0 2px 12px rgba(0,0,0,.18)", fontFamily: "Helvetica, Arial, sans-serif" }}
              data-testid="print-package-cover-strip"
            >
              <div className="min-w-0">
                <div className="text-[13px] font-bold tracking-wide uppercase text-[#1a2332] truncate">
                  {s.data.customer_name}{s.data.address ? ` · ${s.data.address}` : ""}
                </div>
                <div className="text-[10px] italic text-[#5a6472]" data-testid="print-package-methodology">
                  {METHODOLOGY_LINE}
                </div>
              </div>
              {scored ? (
                <div
                  className="shrink-0 text-right border border-[#0d7a3f] px-3 py-1"
                  data-testid="print-package-accuracy"
                >
                  <div className="text-[15px] font-bold text-[#0d7a3f] leading-tight">{tapeLatest.accuracy_pct}%</div>
                  <div className="text-[8px] uppercase tracking-wider text-[#0d7a3f]">
                    latest tape check · {String(tapeLatest.scored_at || "").slice(0, 10)}
                  </div>
                </div>
              ) : (
                <div
                  className="shrink-0 border border-dashed border-[#b45309] text-[#b45309] px-3 py-1.5 text-[9px] font-bold uppercase tracking-wider"
                  data-testid="print-package-not-scored"
                >
                  not yet field-scored
                </div>
              )}
            </div>
          )}
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
