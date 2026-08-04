import React, { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Loader2, CircleCheck, TriangleAlert, RefreshCw } from "lucide-react";

// READINESS CHECKLIST (authorized 2026-07-23): "the app tells the
// contractor exactly what stands between him and a real number."
// SOFT surface only — informational, never a hard block (ruled).

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

const KNOWN_KINDS = new Set([
  "pending_price", "open_flag", "field_verify", "unpriced_row",
  "labor_pending_row", "labor_pending", "qty_pending",
  "family_conflict", "quote_gate",
]);

export default function ReadinessPanel({ estId }) {
  const t = useT();
  const { readiness, loading, reload } = useReadiness(estId);
  const grouped = {};
  (readiness?.items || []).forEach((it) => {
    (grouped[it.kind] = grouped[it.kind] || []).push(it);
  });
  return (
    <div className="mt-4 border border-[var(--border)] bg-[var(--surface-muted)] p-4" data-testid="readiness-panel">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="section-tag">{t("readiness.title")}</div>
        <button type="button" className="text-[11px] font-bold uppercase tracking-wider text-[var(--muted)] inline-flex items-center gap-1"
          onClick={reload} data-testid="readiness-refresh-btn">
          <RefreshCw className="w-3 h-3" /> {t("readiness.refresh")}
        </button>
      </div>
      {loading && !readiness ? (
        <div className="flex items-center gap-2 text-xs text-[var(--muted)]"><Loader2 className="w-4 h-4 animate-spin" /> {t("readiness.checking")}</div>
      ) : !readiness ? (
        <div className="text-xs text-[var(--muted)]">{t("readiness.unavailable")}</div>
      ) : readiness.ready ? (
        <div className="flex items-center gap-2 text-sm font-bold text-emerald-700" data-testid="readiness-all-clear">
          <CircleCheck className="w-4 h-4" /> {t("readiness.allClear")}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-[#92400E]" data-testid="readiness-open-count">
            <TriangleAlert className="w-4 h-4" /> {t("readiness.openCount", { n: readiness.open_count })}
          </div>
          {Object.entries(grouped).map(([kind, items]) => (
            <div key={kind}>
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">
                {KNOWN_KINDS.has(kind) ? t(`readiness.kind.${kind}`) : kind} ({items.length})
              </div>
              <ul className="space-y-0.5">
                {items.map((it, i) => (
                  <li key={i} className="text-xs text-[var(--ink)]" data-testid="readiness-item">• {it.label}</li>
                ))}
              </ul>
            </div>
          ))}
          <div className="text-[10px] text-[var(--muted)]">
            {t("readiness.footer")}
          </div>
        </div>
      )}
    </div>
  );
}
