import React from "react";
import { fmt } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Save, FileText, Printer, Download, ClipboardList } from "lucide-react";

const TAB_LABEL_KEYS = {
  vinyl: "tabLabel.vinyl",
  ascend: "tabLabel.ascend",
  lp_smart: "tabLabel.lpSmart",
  windows: "tabLabel.windows",
  mezzo: "tabLabel.mezzo",
};

export default function TotalsSummary({ est, totals, activeTab, saving, onSave, onOpenQuote, onPrint, onExportCsv, onPrintMaterials, lpDerivedUnapplied, lpDerivedTotal }) {
  const t = useT();
  const modeLabel = est.pricing_mode === "markup" ? t("est.markup").toLowerCase() : t("est.margin").toLowerCase();
  const tabLabel = t(TAB_LABEL_KEYS[activeTab] || TAB_LABEL_KEYS.vinyl);
  return (
    <section className="card p-6" data-testid="totals-summary">
      <div className="section-tag mb-4 flex items-center gap-2">
        <span>{t("est.summary")}</span>
        <span
          className="text-[10px] font-bold px-2 py-0.5 bg-orange-50 border border-[var(--brand)] text-[var(--brand-text)]"
          data-testid="summary-tab-badge"
        >
          {t("est.tabOption", { tab: tabLabel })}
        </span>
      </div>
      {lpDerivedUnapplied && activeTab === "lp_smart" && (
        <div className="mb-4 flex flex-wrap items-center gap-3 bg-[#FFFBEB] border border-[#F59E0B] px-3 py-2" data-testid="summary-derived-unapplied">
          <span className="text-xs font-bold text-[#92400E]">
            LP takeoff derived ({fmt(lpDerivedTotal)}) — not yet applied to line items. Totals below reflect applied lines only.
          </span>
          <button
            type="button"
            className="text-[11px] font-bold uppercase tracking-wider underline text-[#92400E]"
            data-testid="summary-apply-affordance"
            onClick={() => {
              const el = document.querySelector('[data-testid="ai-measure-btn"]') || document.querySelector('[data-testid="lp-material-list-panel"]');
              el?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
          >
            Review &amp; apply takeoff
          </button>
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <Stat label={t("est.sum.material")} val={fmt(totals.subMat)} />
        <Stat label={t("est.sum.waste", { pct: est.waste_pct || 0 })} val={fmt(totals.wasteAdd || 0)} />
        <Stat label={t("est.sum.tax", { pct: est.tax_enabled ? est.tax_rate : 0 })} val={fmt(totals.tax)} />
        <Stat label={t("est.sum.labor")} val={fmt(totals.subLab)} />
        <Stat label={t("est.sum.baseCost")} val={fmt(totals.base)} bold />
        <Stat label={t("est.sum.sell", { pct: est.margin_pct, mode: modeLabel })} val={fmt(totals.sell)} orange />
      </div>
      <div className="flex flex-wrap gap-3">
        <button className="btn-primary" onClick={onSave} disabled={saving} data-testid="save-btn">
          <Save className="w-4 h-4" /> {saving ? t("common.saving") : t("common.save")}
        </button>
        <button className="btn-secondary" onClick={onOpenQuote} data-testid="open-quote-btn">
          <FileText className="w-4 h-4" /> {t("est.customerQuote")}
        </button>
        <button className="btn-secondary" onClick={onPrintMaterials} data-testid="material-list-btn">
          <ClipboardList className="w-4 h-4" /> {t("est.materialList")}
        </button>
        <button className="btn-secondary" onClick={onPrint} data-testid="print-btn">
          <Printer className="w-4 h-4" /> {t("est.print")}
        </button>
        <button className="btn-secondary" onClick={onExportCsv} data-testid="export-csv-btn">
          <Download className="w-4 h-4" /> {t("est.exportCsv")}
        </button>
      </div>
    </section>
  );
}

function Stat({ label, val, orange, bold }) {
  return (
    <div className="border-l-2 border-[var(--border)] pl-3">
      <div className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)] font-bold">{label}</div>
      <div
        className={`font-mono-num mt-1 ${
          orange
            ? "text-2xl font-bold text-[var(--brand-text)]"
            : bold
            ? "text-lg font-bold text-[var(--ink)]"
            : "text-base text-[var(--ink)]"
        }`}
      >
        {val}
      </div>
    </div>
  );
}
