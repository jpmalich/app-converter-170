import React, { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import { Loader2, CircleCheck, TriangleAlert, RefreshCw } from "lucide-react";

// READINESS CHECKLIST (authorized 2026-07-23): "the app tells the
// contractor exactly what stands between him and a real number."
// SOFT surface only — informational, never a hard block (ruled).

const KIND_LABELS = {
  pending_price: "Pending prices",
  open_flag: "Open flags",
  field_verify: "Field-verify",
  unpriced_row: "Unpriced money rows",
};

export function useReadiness(estId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!estId) return;
    setLoading(true);
    try {
      const r = await api.get(`/estimates/${estId}/readiness`);
      setData(r.data);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [estId]);
  useEffect(() => { load(); }, [load]);
  return { readiness: data, loading, reload: load };
}

export default function ReadinessPanel({ estId }) {
  const { readiness, loading, reload } = useReadiness(estId);
  const grouped = {};
  (readiness?.items || []).forEach((it) => {
    (grouped[it.kind] = grouped[it.kind] || []).push(it);
  });
  return (
    <div className="mt-4 border border-[var(--border)] bg-[var(--surface-muted)] p-4" data-testid="readiness-panel">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="section-tag">Estimate readiness</div>
        <button type="button" className="text-[11px] font-bold uppercase tracking-wider text-[var(--muted)] inline-flex items-center gap-1"
          onClick={reload} data-testid="readiness-refresh-btn">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>
      {loading && !readiness ? (
        <div className="flex items-center gap-2 text-xs text-[var(--muted)]"><Loader2 className="w-4 h-4 animate-spin" /> Checking…</div>
      ) : !readiness ? (
        <div className="text-xs text-[var(--muted)]">Readiness unavailable.</div>
      ) : readiness.ready ? (
        <div className="flex items-center gap-2 text-sm font-bold text-emerald-700" data-testid="readiness-all-clear">
          <CircleCheck className="w-4 h-4" /> All clear — nothing stands between you and a real number.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-[#92400E]" data-testid="readiness-open-count">
            <TriangleAlert className="w-4 h-4" /> {readiness.open_count} open item{readiness.open_count === 1 ? "" : "s"}
          </div>
          {Object.entries(grouped).map(([kind, items]) => (
            <div key={kind}>
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">
                {KIND_LABELS[kind] || kind} ({items.length})
              </div>
              <ul className="space-y-0.5">
                {items.map((it, i) => (
                  <li key={i} className="text-xs text-[var(--ink)]" data-testid="readiness-item">• {it.label}</li>
                ))}
              </ul>
            </div>
          ))}
          <div className="text-[10px] text-[var(--muted)]">
            Soft check only — nothing here blocks the quote.
          </div>
        </div>
      )}
    </div>
  );
}
