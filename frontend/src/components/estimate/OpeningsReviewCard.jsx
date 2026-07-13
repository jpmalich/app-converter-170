// Confirm-openings review (approved post-C4): one-tap photo ratification
// of detected openings before package derivation. Same surface family as
// the amber field-verify checklist — human ratification of stochastic
// extraction. Skippable; unconfirmed flags persist.
import React, { useState } from "react";
import { DoorOpen, Eye } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const TYPE_LABELS = {
  window: "Window", entry_door: "Entry door", patio_door: "Patio slider",
  garage_door: "Garage door", vent: "Vent",
};
const BACKEND = process.env.REACT_APP_BACKEND_URL;

export function OpeningsReviewCard({ review, estId, onChanged, t }) {
  const [busyKey, setBusyKey] = useState(null);
  const [correcting, setCorrecting] = useState(null); // key being corrected
  const [collapsed, setCollapsed] = useState(false);
  if (!review || !review.total) return null;
  const items = review.items || [];

  const act = async (item, action, correctedType) => {
    setBusyKey(item.key);
    try {
      await api.post(`/estimates/${estId}/openings-review`, {
        key: item.key, action, corrected_type: correctedType,
      });
      setCorrecting(null);
      onChanged?.(); // corrections can shift derived counts — refetch
    } catch {
      toast.error("Could not save the openings review — try again.");
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="border-b border-[var(--border)] px-4 py-3 bg-[#FFFBEB]" data-testid="lp-openings-review-card">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex items-center justify-between text-left"
        data-testid="lp-or-toggle"
      >
        <span className="text-[11px] font-bold uppercase tracking-wider text-[#92400E] flex items-center gap-1.5">
          <DoorOpen className="w-3.5 h-3.5" /> {t("lp.or.title")}
        </span>
        <span className="text-[10px] font-bold text-[#92400E]" data-testid="lp-or-summary">
          {review.confirmed + review.corrected}/{review.total} {t("lp.or.reviewed")}
          {review.unconfirmed > 0 && ` · ${review.unconfirmed} ${t("lp.or.unconfirmed")}`}
        </span>
      </button>
      {!collapsed && (
        <>
          <div className="text-[11px] text-[#92400E] mt-1 mb-2">{t("lp.or.note")}</div>
          <div className="space-y-1.5">
            {items.map((it) => {
              const effType = it.corrected_type || it.type;
              return (
                <div key={it.key} className="flex flex-wrap items-center gap-2 text-xs" data-testid={`lp-or-item-${it.key}`}>
                  {it.photo_url ? (
                    <a href={`${BACKEND}${it.photo_url}`} target="_blank" rel="noreferrer" title={t("lp.or.viewPhoto")}>
                      <img
                        src={`${BACKEND}${it.photo_url}`}
                        alt={it.elevation}
                        className="w-10 h-8 object-cover border border-[var(--border)]"
                        loading="lazy"
                      />
                    </a>
                  ) : (
                    <span className="w-10 h-8 flex items-center justify-center bg-[var(--surface-muted)] border border-[var(--border)]"><Eye className="w-3 h-3 text-[var(--muted)]" /></span>
                  )}
                  <div className="flex-1 min-w-[180px]">
                    <span className="font-mono text-[10px] uppercase text-[#B45309] mr-1.5">{it.elevation}</span>
                    <span className="text-[var(--ink)]">
                      {TYPE_LABELS[effType] || effType}
                      {it.count > 1 ? ` ×${it.count}` : ""} · {it.size_label}
                      {it.style ? ` · ${it.style}` : ""}
                    </span>
                    {it.status === "user_corrected" && (
                      <span className="ml-1.5 text-[10px] font-bold text-violet-700" data-testid={`lp-or-corrected-${it.key}`}>
                        {t("lp.or.corrected")}: {TYPE_LABELS[it.type]} → {TYPE_LABELS[it.corrected_type]}
                      </span>
                    )}
                  </div>
                  {it.status === "unconfirmed" ? (
                    correcting === it.key ? (
                      <select
                        className="input text-[10px] py-0.5"
                        defaultValue=""
                        onChange={(e) => e.target.value && act(it, "correct", e.target.value)}
                        data-testid={`lp-or-correct-select-${it.key}`}
                      >
                        <option value="">{t("lp.or.pickType")}</option>
                        {Object.entries(TYPE_LABELS)
                          .filter(([k]) => k !== it.type)
                          .map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    ) : (
                      <span className="flex gap-1.5">
                        <button
                          type="button"
                          disabled={busyKey === it.key}
                          onClick={() => act(it, "confirm")}
                          className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider bg-[#B45309] text-white disabled:opacity-60"
                          data-testid={`lp-or-confirm-${it.key}`}
                        >
                          ✓ {t("lp.or.confirm")}
                        </button>
                        <button
                          type="button"
                          onClick={() => setCorrecting(it.key)}
                          className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider border border-[#B45309] text-[#92400E]"
                          data-testid={`lp-or-wrong-${it.key}`}
                        >
                          {t("lp.or.wrongType")}
                        </button>
                      </span>
                    )
                  ) : (
                    <button
                      type="button"
                      disabled={busyKey === it.key}
                      onClick={() => act(it, "reset")}
                      className="text-[10px] font-bold uppercase tracking-wider text-emerald-700"
                      title={`${it.by || ""} ${it.at ? new Date(it.at).toLocaleDateString() : ""}`}
                      data-testid={`lp-or-done-${it.key}`}
                    >
                      ✓ {it.status === "user_confirmed" ? t("lp.or.confirmed") : t("lp.or.correctedShort")}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
