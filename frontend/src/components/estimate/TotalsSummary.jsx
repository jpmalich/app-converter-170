import React from "react";
import { fmt } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Save, FileText, Printer, Download, ClipboardList } from "lucide-react";

const TAB_LABEL = { vinyl: "Vinyl", ascend: "Ascend", lp_smart: "LP Smart", windows: "Windows" };

export default function TotalsSummary({ est, totals, activeTab, saving, onSave, onOpenQuote, onPrint, onExportCsv, onPrintMaterials }) {
  const t = useT();
  const modeLabel = est.pricing_mode === "markup" ? t("est.markup").toLowerCase() : t("est.margin").toLowerCase();
  const tabLabel = TAB_LABEL[activeTab] || "Vinyl";
  return (
    <section className="card p-6" data-testid="totals-summary">
      <div className="section-tag mb-4 flex items-center gap-2">
        <span>{t("est.summary")}</span>
        <span
          className="text-[10px] font-bold px-2 py-0.5 bg-orange-50 border border-[#F97316] text-[#F97316]"
          data-testid="summary-tab-badge"
        >
          {tabLabel} option
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <Stat label={t("est.sum.material")} val={fmt(totals.subMat)} />
        <Stat label={t("est.sum.waste", { pct: est.waste_pct || 0 })} val={fmt(totals.wasted)} />
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
          <ClipboardList className="w-4 h-4" /> Material List
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
    <div className="border-l-2 border-[#E4E4E7] pl-3">
      <div className="text-[10px] uppercase tracking-[0.18em] text-[#A1A1AA] font-bold">{label}</div>
      <div
        className={`font-mono-num mt-1 ${
          orange
            ? "text-2xl font-bold text-[#F97316]"
            : bold
            ? "text-lg font-bold text-[#09090B]"
            : "text-base text-[#09090B]"
        }`}
      >
        {val}
      </div>
    </div>
  );
}
