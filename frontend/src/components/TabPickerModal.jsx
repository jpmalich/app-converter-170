import React, { useState, useMemo } from "react";
import { X } from "lucide-react";

const TAB_LABEL = {
  vinyl: "Vinyl Siding",
  ascend: "Ascend Composite Siding",
  windows: "Windows",
};
const TAB_ORDER = ["vinyl", "ascend", "windows"];

/**
 * Modal that asks the contractor which product-line tabs to include in the
 * customer quote or material list. Auto-skipped (caller decides) when only
 * one tab has data — the picker is only useful for hybrid estimates.
 */
export default function TabPickerModal({ open, mode, tabsWithData, onClose, onConfirm }) {
  const orderedTabs = useMemo(
    () => TAB_ORDER.filter((t) => tabsWithData.includes(t)),
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

  const title = mode === "quote" ? "Print Customer Quote" : "Print Material List";
  const helper =
    mode === "quote"
      ? "Pick which product lines to send to the customer. One PDF per pick keeps the quote uncluttered when the job spans multiple product lines."
      : "Pick which product lines to print for the supplier. Each pick gets its own list so the warehouse can pull and stage materials separately.";

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
        className="bg-white max-w-md w-full border border-[#09090B] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[#E4E4E7] px-5 py-3">
          <div className="text-sm uppercase tracking-[0.18em] font-bold text-[#09090B]">
            {title}
          </div>
          <button
            type="button"
            className="p-1 text-[#71717A] hover:text-[#09090B]"
            onClick={onClose}
            data-testid="tab-picker-close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-5 py-5 space-y-4">
          <p className="text-xs text-[#52525B] leading-relaxed">{helper}</p>
          <div className="space-y-2">
            {orderedTabs.map((id) => (
              <label
                key={id}
                className="flex items-center gap-3 px-3 py-2.5 border border-[#E4E4E7] hover:border-[#09090B] cursor-pointer select-none"
                data-testid={`tab-picker-option-${id}`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(id)}
                  onChange={() => toggle(id)}
                  className="w-4 h-4"
                />
                <span className="text-sm font-semibold text-[#09090B]">
                  {TAB_LABEL[id]}
                </span>
              </label>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-[#E4E4E7] px-5 py-3">
          <button
            type="button"
            className="px-3 py-2 text-xs uppercase tracking-wider font-bold text-[#52525B] hover:text-[#09090B]"
            onClick={onClose}
            data-testid="tab-picker-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            className="px-4 py-2 bg-[#F97316] text-white border border-[#F97316] hover:bg-[#EA580C] text-xs font-bold uppercase tracking-wider disabled:opacity-50"
            disabled={selected.size === 0}
            onClick={() => onConfirm(Array.from(selected))}
            data-testid="tab-picker-confirm"
          >
            Continue · {selected.size}
          </button>
        </div>
      </div>
    </div>
  );
}
