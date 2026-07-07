import React from "react";
import { useT } from "@/lib/i18n";
import { recomputeWasteQtys, recomputeAllWaste } from "@/lib/wasteLogic";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import PorchCeilingsCard from "./PorchCeilingsCard";

export default function SettingsRow({ est, update }) {
  const t = useT();
  const mode = est.pricing_mode || "margin";
  const isMargin = mode === "margin";
  // Iter 78 — Waste % change recomputes line.qty for any cut-prone line
  // that carries a stored raw_qty (i.e. came from a HOVER/Blueprint
  // import). Lines entered manually are untouched.
  const updateWastePct = (newPct) => {
    const lines = recomputeWasteQtys(est?.lines, newPct);
    update({ waste_pct: newPct, lines });
  };
  // Iter 78b — Retroactive recompute for legacy estimates where lines
  // were stored before the cut-prone classifier was fixed. Treats every
  // cut-prone line's current qty as the raw value, stamps raw_qty, and
  // recomputes qty against the current waste %. Gated by a ConfirmDialog
  // (Radix AlertDialog) so manual edits don't get clobbered by accident.
  const wastePctNow = Number(est?.waste_pct) || 0;
  const recomputeCandidateCount = (est?.lines || []).filter((l) => {
    if (!l) return false;
    const hasRaw = l.raw_qty != null && Number(l.raw_qty) > 0;
    return !hasRaw; // candidate lines that would be stamped
  }).length;
  const recomputeAllNow = () => {
    update({ lines: recomputeAllWaste(est?.lines, wastePctNow) });
  };
  const recomputeConfirmText =
    `Re-bake ${wastePctNow}% waste into every cut-prone line on this estimate.\n\n` +
    `This treats each line's current qty as the raw measurement, then ` +
    `applies the waste %.\n\n` +
    `${recomputeCandidateCount} line(s) without a stored raw_qty will be updated. ` +
    `Lines already imported with raw_qty are also recomputed (same ` +
    `effect as changing the % field).\n\n` +
    `Heads-up: any manual qty edits on cut-prone lines (siding, soffit, ` +
    `J-channel, trim, corners, starter) will be treated as raw and bumped ` +
    `by ${wastePctNow}%.`;
  // Live preview of the multiplier so the contractor knows what %  actually does
  const pct = Math.min(Number(est.margin_pct) || 0, 99);
  const effectiveMultiplier = isMargin
    ? 1 / (1 - pct / 100)
    : 1 + pct / 100;
  // Windows-kind estimates price each opening individually (Vero W×H +
  // Mezzo W×H + per-line install qty), so the % siding waste factor
  // doesn't apply. Hide the card and let Sales Tax + Profit fill the row.
  const showWaste = est.kind !== "windows";

  return (
    <section className={`grid grid-cols-1 ${showWaste ? "lg:grid-cols-3" : "lg:grid-cols-2"} gap-6 mb-6`}>
      {showWaste && (
        <div className="card p-5" data-testid="waste-factor-card">
          <div className="section-tag mb-3">{t("est.wasteFactor")}</div>
          <div className="flex items-baseline gap-2">
            <input
              className="input num w-24"
              type="number"
              step="0.5"
              value={est.waste_pct || 0}
              onChange={(e) => updateWastePct(Number(e.target.value) || 0)}
              data-testid="waste-pct"
            />
            <span className="text-[var(--ink-2)]">{t("est.wasteSuffix")}</span>
          </div>
          <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
            {t("est.wasteHint")}
          </p>
          {/* Iter 78 — Waste is now baked directly into line qty on HOVER /
              Blueprint imports for siding, soffit, J-channel, finish trim,
              corners + starter. Changing the % here recomputes those line
              qtys (raw × 1+waste). Manual lines are untouched. */}
          <p className="mt-1 text-[10px] uppercase tracking-wider text-[var(--success)] font-bold">
            Baked into line qty on import — change % to recompute
          </p>
          {/* Iter 78b — Retroactive recompute button for legacy lines.
              Useful on estimates created before the Iter 78a LP
              cut-prone-classifier fix landed, where qty was stored
              raw and raw_qty=null. One-tap fix that doesn't require
              re-uploading the blueprint. */}
          <ConfirmDialog
            trigger={
              <button
                type="button"
                className="mt-2 px-3 py-1.5 bg-[var(--surface)] text-[var(--ai)] border border-[var(--ai)] hover:bg-[var(--surface-muted)] text-[10px] font-bold uppercase tracking-wider"
                data-testid="recompute-all-waste-btn"
                title="Stamp raw_qty + recompute every cut-prone line at the current waste %"
              >
                Recompute waste on existing lines
              </button>
            }
            title="Recompute waste on existing lines"
            description={recomputeConfirmText}
            confirmLabel="Recompute"
            onConfirm={recomputeAllNow}
          />
          {/* Iter 78 — LP soffit steering (LP-only). Backend's HOVER spec
              splits LP soffit into Vented (eaves) + Closed (rakes) by
              surface. This knob lets Howard collapse to all-vented or
              all-closed for jobs that only use one style. */}
          {est.kind === "lp_smart" && (
            <div className="mt-4 pt-4 border-t border-[var(--border)]">
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
                LP Soffit type
              </div>
              <select
                className="input h-9 text-sm"
                value={est.lp_soffit_type || "mix"}
                onChange={(e) => update({ lp_soffit_type: e.target.value })}
                data-testid="lp-soffit-type"
              >
                <option value="mix">Mix — Vented on eaves, Closed on rakes (default)</option>
                <option value="vented">Vented — all soffit qty as Vented (38 Series Vented)</option>
                <option value="closed">Closed — all soffit qty as Closed (38 Series Closed)</option>
              </select>
              <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                Applied on HOVER / Blueprint import — collapses or splits the two soffit lines automatically
              </p>
            </div>
          )}
          {/* Iter 45: soffit overhang in inches — drives the
              Pieces = (Overhang × Length) ÷ panel-area formula on the
              Vinyl Soffit line. Lives in the same card as Waste Factor
              since it's the other knob that affects qty-not-price. */}
          <div className="mt-4 pt-4 border-t border-[var(--border)]">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
              {t("est.overhang")}
            </div>
            <div className="flex items-baseline gap-2">
              <input
                className="input num w-24"
                type="number"
                step="1"
                min="0"
                value={est.overhang_in ?? 12}
                onChange={(e) => update({ overhang_in: Number(e.target.value) || 0 })}
                data-testid="overhang-in"
              />
              <span className="text-[var(--ink-2)]">in</span>
            </div>
            <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
              {t("est.overhangHint")}
            </p>
            {/* Iter 78aj — Porch ceilings live right below the overhang
                field so contractors see them as part of the same "what
                drives soffit qty" decision. The total sqft is summed
                into the same soffit formula. */}
            <PorchCeilingsCard
              value={est.porch_ceilings || []}
              onChange={(next) => update({ porch_ceilings: next })}
            />
          </div>
        </div>
      )}
      <div className="card p-5">
        <div className="section-tag mb-3">{t("est.salesTax")}</div>
        <label className="flex items-center gap-3 mb-3 text-sm">
          <input
            type="checkbox"
            checked={!!est.tax_enabled}
            onChange={(e) => update({ tax_enabled: e.target.checked })}
            data-testid="tax-toggle"
          />
          <span>{t("est.applyTaxOnMaterial")}</span>
        </label>
        <div className="flex items-baseline gap-2">
          <input
            className="input num w-24"
            type="number"
            step="0.01"
            aria-label={t("est.taxRate.aria")}
            disabled={!est.tax_enabled}
            value={est.tax_rate || 0}
            onChange={(e) => update({ tax_rate: Number(e.target.value) || 0 })}
            data-testid="tax-rate"
          />
          <span className="text-[var(--ink-2)]">%</span>
        </div>
      </div>
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="section-tag">{t("est.profit")}</div>
          <div
            className="inline-flex border border-[var(--border)] rounded-sm overflow-hidden text-[11px] font-bold uppercase tracking-wider"
            data-testid="pricing-mode-toggle"
          >
            <button
              type="button"
              className={`px-3 py-1.5 transition ${
                isMargin
                  ? "bg-[var(--bar-bg)] text-white"
                  : "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]"
              }`}
              onClick={() => update({ pricing_mode: "margin" })}
              data-testid="pricing-mode-margin"
            >
              {t("est.margin")}
            </button>
            <button
              type="button"
              className={`px-3 py-1.5 transition border-l border-[var(--border)] ${
                !isMargin
                  ? "bg-[var(--bar-bg)] text-white"
                  : "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]"
              }`}
              onClick={() => update({ pricing_mode: "markup" })}
              data-testid="pricing-mode-markup"
            >
              {t("est.markup")}
            </button>
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <input
            className="input num w-24"
            type="number"
            step="1"
            min="0"
            max={isMargin ? 99 : undefined}
            aria-label={t("est.profitPct.aria")}
            value={est.margin_pct || 0}
            onChange={(e) => update({ margin_pct: Number(e.target.value) || 0 })}
            data-testid="margin-pct"
          />
          <span className="text-[var(--ink-2)]">
            {isMargin ? t("est.marginSuffix") : t("est.markupSuffix")}
          </span>
        </div>
        <input
          type="range"
          min="0"
          max={isMargin ? 95 : 100}
          step="1"
          value={est.margin_pct || 0}
          onChange={(e) => update({ margin_pct: Number(e.target.value) || 0 })}
          className="w-full accent-[var(--brand)]"
          aria-label={t("est.profitPct.aria")}
          aria-valuetext={`${est.margin_pct || 0}%`}
          data-testid="margin-slider"
        />
        <div className="mt-2 text-[11px] text-[var(--muted)] font-mono-num">
          {isMargin ? (
            <>
              Sell = Base ÷ (1 − {pct}%) ={" "}
              <span className="text-[var(--ink)] font-bold">
                ×{effectiveMultiplier.toFixed(3)}
              </span>
            </>
          ) : (
            <>
              Sell = Base × (1 + {pct}%) ={" "}
              <span className="text-[var(--ink)] font-bold">
                ×{effectiveMultiplier.toFixed(3)}
              </span>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
