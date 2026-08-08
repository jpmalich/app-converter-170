// VISUAL AUDIT (Howard ruled 2026-08-08 — SAME BUILD as evidence-or-null):
// highlight on the plan page exactly where each number came from. One
// schema, one renderer. Three ruled states: EXACT (PDF text layer),
// APPROXIMATE (vision box on a scan — labelled, never a tight box implying
// precision we do not have), and NO SOURCE — rendered as loudly as a
// highlight, because a number with no highlight is a number with no source.
import React, { useState } from "react";
import { MapPin, XCircle, AlertTriangle } from "lucide-react";
import { useT } from "@/lib/i18n";

const HighlightBox = ({ loc }) => (
  <div
    className="absolute border-2 border-[#DC2626] bg-[#DC2626]/10 pointer-events-none"
    style={{
      left: `${loc.x_pct}%`,
      top: `${loc.y_pct}%`,
      width: `${Math.max(loc.w_pct, 0.6)}%`,
      height: `${Math.max(loc.h_pct, 0.6)}%`,
    }}
  />
);

export const VisualAuditPanel = ({ evidence, pagePaths = [] }) => {
  const t = useT();
  const [openPath, setOpenPath] = useState(null);
  if (!evidence) return null;
  const items = evidence.items || [];
  const dropped = evidence.dropped || [];
  const unread = evidence.unread || [];
  if (!items.length && !dropped.length && !unread.length) return null;

  const srcsOf = (it) => (it.srcs || [it]).filter((s) => s && (s.page || s.from));

  return (
    <div className="px-3 py-2 space-y-1.5 border-t border-[var(--border)]" data-testid="bp-va-panel">
      <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{t("bp.va.title")}</div>
      {items.length === 0 && (
        <div className="text-[11px] text-[var(--muted)]" data-testid="bp-va-none">{t("bp.va.none")}</div>
      )}
      {items.map((it) => {
        const open = openPath === it.path;
        const srcs = srcsOf(it);
        return (
          <div key={it.path} className="border border-[var(--border)]">
            <button
              type="button"
              onClick={() => setOpenPath(open ? null : it.path)}
              className="w-full flex flex-wrap items-center gap-x-2 gap-y-0.5 px-2 py-1 text-left text-[11px] hover:bg-[var(--surface-muted)]"
              data-testid={`bp-va-item-${it.path}`}
            >
              <span className="font-mono-num font-bold">{it.path}</span>
              <span className="font-mono-num">{it.v}</span>
              {srcs.map((s, i) => (
                <span key={i} className="text-[10px] text-[var(--muted)]">
                  {s.page ? `${t("bp.va.page", { n: s.page })} ` : ""}“{s.from}”
                </span>
              ))}
              {it.calc && (
                <span className="text-[10px] text-[var(--muted)]" data-testid={`bp-va-calc-${it.path}`}>
                  {t("bp.va.calc", { text: it.calc })}
                </span>
              )}
              <MapPin className="w-3 h-3 ml-auto shrink-0 text-[var(--muted)]" />
            </button>
            {open && (
              <div className="p-2 space-y-2 border-t border-[var(--border)]" data-testid={`bp-va-viewer-${it.path}`}>
                {srcs.map((s, i) => {
                  const img = s.page ? pagePaths[s.page - 1] : null;
                  return (
                    <div key={i} className="space-y-1">
                      <div
                        className={`text-[10px] font-bold ${
                          s.precision === "exact"
                            ? "text-[#15803D]"
                            : s.precision === "approximate"
                            ? "text-[#92400E]"
                            : "text-[var(--muted)]"
                        }`}
                        data-testid={`bp-va-precision-${it.path}-${i}`}
                      >
                        {s.precision === "exact"
                          ? t("bp.va.exact")
                          : s.precision === "approximate"
                          ? t("bp.va.approx")
                          : t("bp.va.noloc")}
                      </div>
                      {img && s.loc ? (
                        <div className="relative inline-block max-w-full">
                          <img
                            src={`/api/uploads/${img}`}
                            alt={`sheet ${s.page}`}
                            className="max-w-full border border-[var(--border)]"
                          />
                          <HighlightBox loc={s.loc} />
                        </div>
                      ) : (
                        <div className="text-[11px] text-[var(--muted)]">
                          “{s.from}”{s.page ? ` — ${t("bp.va.page", { n: s.page })}` : ""}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      {dropped.length > 0 && (
        <div
          className="flex items-start gap-1.5 border px-2 py-1 text-[11px] leading-snug bg-[#FEF2F2] text-[#B91C1C] border-[#FCA5A5]"
          data-testid="bp-va-dropped"
        >
          <XCircle className="w-3.5 h-3.5 mt-[1px] shrink-0" />
          <span>{t("bp.va.dropped", { text: dropped.join(", ") })}</span>
        </div>
      )}
      {unread.length > 0 && (
        <div
          className="flex items-start gap-1.5 border px-2 py-1 text-[11px] leading-snug bg-[#FFFBEB] text-[#92400E] border-[#FCD34D]"
          data-testid="bp-va-unread"
        >
          <AlertTriangle className="w-3.5 h-3.5 mt-[1px] shrink-0" />
          <span>{t("bp.va.unread", { text: unread.join(", ") })}</span>
        </div>
      )}
    </div>
  );
};

export default VisualAuditPanel;
