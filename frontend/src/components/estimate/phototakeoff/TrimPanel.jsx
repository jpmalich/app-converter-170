// SEND-143 (Howard ruled 2026-08-28) — PHASE 2 LINEAR RUNS, ON SCREEN.
// Every trim row Howard named is here whether or not it can be measured:
// J-channel and the gable rake carry a figure from marks ALREADY DRAWN,
// and the four with no mark to read print the em dash and NAME the missing
// mark. The server writes both the figure and the basis line — this panel
// prints them and decides nothing.
import React from "react";

import { GABLE } from "./marks";

const lf = (v) => (v == null ? "—" : `${v} LF`);

export const TrimPanel = ({ qty }) => {
  const rows = qty?.trim_rows || [];
  return (
    <div className="p-3 border-b border-[var(--border)]" data-testid="photo-takeoff-trim-panel">
      <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">
        Linear runs — confirmed marks only
      </div>
      <div className="space-y-1.5">
        {rows.map((r) => (
          <div key={r.key} className="border-b border-dashed border-[var(--border)] pb-1.5 last:border-0"
            data-testid={`photo-takeoff-trim-row-${r.key}`}>
            <div className="flex items-baseline gap-2 text-[11px]">
              <span className="flex-1">
                {r.label}
                {r.zone === "gable" && (
                  <span className="ml-1 text-[9px] font-bold uppercase tracking-wider" style={{ color: GABLE }}>gable zone</span>
                )}
              </span>
              <span className="font-bold text-right" data-testid={`photo-takeoff-trim-lf-${r.key}`}>{lf(r.lf)}</span>
            </div>
            {r.lf != null && r.basis && (
              <div className="mt-0.5 text-[9px] text-[var(--muted)] leading-snug" data-testid={`photo-takeoff-trim-basis-${r.key}`}>
                {r.basis}
              </div>
            )}
            {r.refusal && (
              <div className="mt-0.5 text-[9px] text-[var(--warning-text)] leading-snug" data-testid={`photo-takeoff-trim-refusal-${r.key}`}>
                {r.refusal}
              </div>
            )}
            {(r.rows || []).filter((x) => x.basis || x.refusal).map((x) => (
              <div key={x.id} className="mt-0.5 pl-2 text-[9px] leading-snug"
                data-testid={`photo-takeoff-trim-item-${r.key}-${x.id}`}>
                <span className="font-bold">{x.label}</span>{" "}
                <span className={x.lf == null ? "text-[var(--warning-text)]" : "text-[var(--ink-2)]"}>
                  {x.lf == null ? "—" : `${x.lf} LF`} · {x.basis || x.refusal}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
      {qty?.trim_basis_note && (
        <div className="mt-1.5 text-[9px] text-[var(--muted)] leading-snug" data-testid="photo-takeoff-trim-basis-note">
          {qty.trim_basis_note}
        </div>
      )}
    </div>
  );
};

export default TrimPanel;
