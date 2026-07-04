import React from "react";
import { Package } from "lucide-react";

/**
 * Iter 57v — Window Package Quote override.
 *
 * Drops at the top of VeroPanel / MezzoPanel. When enabled, the brand's
 * window-material total switches from the per-opening bucket sum to
 * `total` — used when the contractor has a single all-in package
 * number from Vero / Mezzo software / inside sales / a rep, rather
 * than per-row bucket prices.
 *
 * Labor lines, accessories, sales tax, profit, and markup all calc
 * normally on top (see calc.js / services.calc_totals).
 *
 * Props:
 *   brand   "vero" | "mezzo"
 *   est     full estimate doc
 *   update  partial-update fn from useEstimate
 */
const fmt = (n) => `$${(Number(n) || 0).toFixed(2)}`;

const BRAND_LABEL = {
  vero: "Vero",
  mezzo: "Mezzo",
};

export default function WindowPackageQuote({ brand, est, update }) {
  const key = `${brand}_package_quote`;
  const pq = est?.[key] || { enabled: false, total: 0, reference: "", notes: "" };
  const enabled = !!pq.enabled;
  const label = BRAND_LABEL[brand] || brand;

  const patch = (delta) => {
    update({ [key]: { ...pq, ...delta } });
  };

  return (
    <section
      className={`card mb-4 border-2 ${
        enabled ? "border-[var(--brand)] bg-[#FFFBEB]" : "border-[var(--border)] bg-[var(--surface)]"
      }`}
      data-testid={`${brand}-package-quote`}
    >
      <header className="flex items-center justify-between px-4 md:px-5 py-3 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <Package className={`w-4 h-4 ${enabled ? "text-[var(--brand-text)]" : "text-[var(--muted)]"}`} />
          <div>
            <div className="section-tag">Window Package — {label} Quote</div>
            <div className="text-[10px] text-[var(--muted)] mt-0.5">
              Optional override — replaces per-window pricing with one package total.
              Labor + accessories + tax calc normally on top.
            </div>
          </div>
        </div>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            className="w-4 h-4 accent-[var(--brand)]"
            checked={enabled}
            onChange={(e) => patch({ enabled: e.target.checked })}
            data-testid={`${brand}-package-quote-toggle`}
          />
          <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)]">
            Use Package Quote
          </span>
        </label>
      </header>

      {enabled && (
        <div className="px-4 md:px-5 py-4 grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-3">
            <label className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold block mb-1">
              Package Total
            </label>
            <div className="flex items-center">
              <span className="px-3 h-10 inline-flex items-center bg-[var(--surface-muted)] border border-r-0 border-[var(--border)] font-mono-num text-sm text-[var(--ink-2)]">
                $
              </span>
              <input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={pq.total || ""}
                onChange={(e) => patch({ total: Number(e.target.value) || 0 })}
                className="input h-10 text-sm flex-1 font-mono-num"
                data-testid={`${brand}-package-quote-total`}
              />
            </div>
          </div>

          <div className="md:col-span-4">
            <label className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold block mb-1">
              {label} Quote Reference
            </label>
            <input
              type="text"
              placeholder={`${label} quote # / rep name`}
              value={pq.reference || ""}
              onChange={(e) => patch({ reference: e.target.value })}
              className="input h-10 text-sm w-full"
              data-testid={`${brand}-package-quote-reference`}
            />
          </div>

          <div className="md:col-span-5">
            <label className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold block mb-1">
              Notes
            </label>
            <input
              type="text"
              placeholder="Color, glass package, lead time, etc."
              value={pq.notes || ""}
              onChange={(e) => patch({ notes: e.target.value })}
              className="input h-10 text-sm w-full"
              data-testid={`${brand}-package-quote-notes`}
            />
          </div>

          <div className="md:col-span-12 mt-1 flex items-center justify-between gap-3 px-3 py-2 bg-[#FFF7ED] border border-[var(--brand)]">
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#9A3412]">
              Active — {label} window material total
            </span>
            <span className="font-mono-num text-base font-bold text-[#9A3412]" data-testid={`${brand}-package-quote-active-total`}>
              {fmt(pq.total)}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
