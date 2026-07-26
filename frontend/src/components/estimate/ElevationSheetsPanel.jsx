import React, { useEffect, useState } from "react";
import { Printer, ExternalLink, PencilRuler } from "lucide-react";
import api from "@/lib/api";
import { SheetSvg } from "@/pages/ElevationSheet";

/* ELEVATION SHEETS — inline on the estimate page (ruled 2026-07-24).
   Mounts automatically once a completed AI run exists — NOT gated on
   Apply; sheets render from the run regardless. EL-1..4 as tabs, the
   SAME SheetSvg the sheet pages use (identical by construction),
   read-only, sized to the page. No run yet → the named empty state,
   never a dead section. The estimate page is the primary home for the
   drawings; full-page/print links open in NEW TABS. */

const SHEETS = ["front", "left", "back", "right"];
const CODES = { front: "EL-1", left: "EL-2", back: "EL-3", right: "EL-4" };

export default function ElevationSheetsPanel({ est }) {
  const [sheets, setSheets] = useState(null); // {which: payload}
  const [active, setActive] = useState(null);

  useEffect(() => {
    let dead = false;
    setSheets(null);
    setActive(null);
    const probe = () => Promise.all(
      SHEETS.map((w) =>
        api.get(`/estimates/${est.id}/elevation-sheet/${w}`)
          .then(({ data }) => [w, data])
          .catch(() => [w, null])
      )
    ).then((pairs) => {
      if (dead) return;
      const ok = Object.fromEntries(pairs.filter(([, d]) => d));
      setSheets(ok);
      setActive((cur) => (cur && ok[cur] ? cur : SHEETS.find((w) => ok[w]) || null));
    });
    probe();
    // Re-probe when an AI run completes on THIS estimate — the mount-time
    // probe alone left the empty state stuck until a manual page reload
    // when the run finished while the page was open (EST-986945 defect).
    const onRunCompleted = (e) => {
      if (e?.detail?.estimateId && e.detail.estimateId !== est.id) return;
      probe();
    };
    window.addEventListener("ai-run-completed", onRunCompleted);
    return () => {
      dead = true;
      window.removeEventListener("ai-run-completed", onRunCompleted);
    };
  }, [est.id]);

  const available = sheets ? SHEETS.filter((w) => sheets[w]) : [];

  return (
    <div className="card p-4" data-testid="elevation-sheets-section">
      <div className="flex items-center justify-between gap-2 flex-wrap mb-3">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)] flex items-center gap-2">
          <PencilRuler className="w-3 h-3" /> Elevation Sheets — EL-1..EL-4 · live-rendered from the AI run
        </div>
        {available.length > 0 && (
          <a
            href={`/estimate/${est.id}/elevation-sheets/print`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2 py-1.5 border border-[var(--ai)] bg-[var(--ai)] text-white text-[10px] font-bold uppercase tracking-wider hover:opacity-90 transition-opacity"
            data-testid="elevation-sheets-print-all"
            title="Print all 4 sheets — one per page (leave-behind package), opens in a new tab"
          >
            <Printer className="w-3 h-3" /> Print all 4 sheets
          </a>
        )}
      </div>

      {sheets === null ? (
        <div className="text-xs text-[var(--muted)] p-3" data-testid="elevation-sheets-loading">
          Checking for a completed AI run…
        </div>
      ) : available.length === 0 ? (
        <div
          className="p-4 border border-dashed border-[var(--border)] text-[11px] font-bold uppercase tracking-wider text-[var(--muted)]"
          data-testid="elevation-sheets-empty"
          title="Sheets bind to a completed AI measure run carrying walls — none exists for this estimate yet"
        >
          Elevation sheets — no completed AI measurement run yet. Run AI Photo
          Measure and the sheets render here automatically — no Apply needed.
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-1 mb-2 flex-wrap" data-testid="elevation-sheets-tabs">
            {available.map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => setActive(w)}
                className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider border transition-colors ${
                  active === w
                    ? "border-[var(--ai)] bg-[var(--ai)] text-white"
                    : "border-[var(--border)] text-[var(--ink-2)] hover:border-[var(--ai)] hover:text-[var(--ai)]"
                }`}
                data-testid={`elevation-sheet-tab-${w}`}
              >
                {CODES[w]} {w}
              </button>
            ))}
            {active && (
              <a
                href={`/estimate/${est.id}/elevation-sheet/${active}`}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto inline-flex items-center gap-1 px-2 py-1.5 border border-[var(--border)] text-[var(--ink-2)] text-[10px] font-bold uppercase tracking-wider hover:border-[var(--ai)] hover:text-[var(--ai)] transition-colors"
                data-testid={`elevation-sheets-open-full-${active}`}
                title="Open this sheet full-page in a new tab"
              >
                <ExternalLink className="w-3 h-3" /> Open full page
              </a>
            )}
          </div>
          {active && sheets[active] && (
            <div
              className="border border-[var(--border)] overflow-hidden [&_svg]:w-full [&_svg]:h-auto"
              data-testid="elevation-sheets-inline-svg"
            >
              <SheetSvg data={sheets[active]} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
