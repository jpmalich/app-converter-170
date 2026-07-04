import React, { useState, useMemo } from "react";
import { X } from "lucide-react";
import { useT } from "@/lib/i18n";

const TAB_ORDER = ["vinyl", "ascend", "lp_smart", "windows"];

/**
 * Modal that asks the contractor which product-line tabs to include in the
 * customer quote or material list. Auto-skipped (caller decides) when only
 * one tab has data — the picker is only useful for hybrid estimates.
 */
export default function TabPickerModal({ open, mode, tabsWithData, onClose, onConfirm }) {
  const t = useT();
  const orderedTabs = useMemo(
    () => TAB_ORDER.filter((id) => tabsWithData.includes(id)),
    [tabsWithData]
  );
  // Default: all tabs selected — the contractor opts OUT of the ones they
  // don't want, which is closer to how they think about a hybrid estimate.
  const [selected, setSelected] = useState(() => new Set(orderedTabs));

  // When the modal re-opens for a different estimate or a different mode,
  // reset selection back to "all tabs with data".
  React.useEffect(() => {
    if (open) setSelected(new Set(orderedTabs));
  }, [open, orderedTabs]);

  if (!open) return null;

  const title = mode === "quote" ? t("tabPicker.title.quote") : t("tabPicker.title.material");
  const helper = mode === "quote" ? t("tabPicker.helper.quote") : t("tabPicker.helper.material");

  const toggle = (id) => {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center px-4"
      data-testid="tab-picker-modal"
      onClick={onClose}
    >
      <div
        className="bg-[var(--surface)] max-w-md w-full border border-[var(--border-strong)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-3">
          <div className="text-sm uppercase tracking-[0.18em] font-bold text-[var(--ink)]">
            {title}
          </div>
          <button
            type="button"
            className="p-1 text-[var(--muted)] hover:text-[var(--ink)]"
            onClick={onClose}
            data-testid="tab-picker-close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-5 py-5 space-y-4">
          <p className="text-xs text-[var(--ink-2)] leading-relaxed">{helper}</p>
          <div className="space-y-2">
            {orderedTabs.map((id) => (
              <label
                key={id}
                className="flex items-center gap-3 px-3 py-2.5 border border-[var(--border)] hover:border-[var(--border-strong)] cursor-pointer select-none"
                data-testid={`tab-picker-option-${id}`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(id)}
                  onChange={() => toggle(id)}
                  className="w-4 h-4"
                />
                <span className="text-sm font-semibold text-[var(--ink)]">
                  {t(`tabPicker.label.${id}`)}
                </span>
              </label>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-[var(--border)] px-5 py-3">
          <button
            type="button"
            className="px-3 py-2 text-xs uppercase tracking-wider font-bold text-[var(--ink-2)] hover:text-[var(--ink)]"
            onClick={onClose}
            data-testid="tab-picker-cancel"
          >
            {t("tabPicker.cancel")}
          </button>
          <button
            type="button"
            className="px-4 py-2 bg-[var(--brand)] text-[var(--on-brand)] border border-[var(--brand)] hover:bg-[var(--brand-hover)] text-xs font-bold uppercase tracking-wider disabled:opacity-50"
            disabled={selected.size === 0}
            onClick={() => onConfirm(Array.from(selected))}
            data-testid="tab-picker-confirm"
          >
            {t("tabPicker.continue", { n: selected.size })}
          </button>
        </div>
      </div>
    </div>
  );
}
