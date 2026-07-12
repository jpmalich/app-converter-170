import React from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Home as HomeIcon, RectangleHorizontal, Layers } from "lucide-react";
import { useT } from "@/lib/i18n";
import { useBranding } from "@/lib/branding";

/**
 * Iter 76 — Step 2B: Contractor Quotes sub-picker.
 *
 * Three options:
 *   - Window Quotes            → /dashboard/windows
 *       (mirrors ISS Windows for now per Howard; labor will diverge later)
 *   - Vinyl + Ascend Siding    → /dashboard/siding
 *   - LP SmartSide             → /dashboard/lp_smart
 */
export default function ContractorPicker() {
  const t = useT();
  const nav = useNavigate();
  const { lp_native_mode } = useBranding();
  if (lp_native_mode) return <Navigate to="/dashboard/lp_smart" replace />;
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16">
      <button
        type="button"
        onClick={() => nav("/")}
        className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--ink-2)] hover:text-[var(--brand-text)] mb-6"
        data-testid="contractor-picker-back"
      >
        {t("home.back")}
      </button>

      <div className="mb-10 sm:mb-12">
        <div className="section-tag mb-3">{t("home.contractorGroupTitle")}</div>
        <h1 className="font-heading text-3xl sm:text-4xl text-[var(--ink)]">
          {t("home.contractor.title")}
        </h1>
        <p className="mt-2 text-[var(--ink-2)] max-w-2xl text-sm sm:text-base">
          {t("home.contractor.subtitle")}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <button
          type="button"
          onClick={() => nav("/dashboard/windows")}
          className="card text-left p-6 sm:p-8 group hover:border-[var(--brand)] transition-colors relative"
          data-testid="contractor-card-windows"
        >
          {/* Iter 77 — Howard flagged Contractor Window Quotes as
              under construction (labor logic will diverge from ISS
              Windows). Badge stays until the contractor-specific
              labor model lands. */}
          <span
            className="absolute top-3 right-3 inline-flex items-center px-2.5 py-1 bg-[#FEF3C7] text-[var(--warning-text)] text-[10px] font-bold uppercase tracking-[0.16em] border border-[#FCD34D] rounded-sm"
            data-testid="contractor-windows-under-construction-badge"
          >
            {t("home.underConstruction")}
          </span>
          <div className="flex items-center gap-3 mb-4 text-[var(--brand-text)]">
            <RectangleHorizontal className="w-8 h-8" />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold">
              {t("home.workspaceTag")}
            </span>
          </div>
          <h2 className="font-heading text-2xl text-[var(--ink)] mb-2">
            {t("home.windowsTitle")}
          </h2>
          <p className="text-sm text-[var(--ink-2)] mb-6">{t("home.windowsDesc")}</p>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--brand-text)] group-hover:underline">
            {t("home.windowsCta")}
          </div>
        </button>

        <button
          type="button"
          onClick={() => nav("/dashboard/siding")}
          className="card text-left p-6 sm:p-8 group hover:border-[var(--brand)] transition-colors"
          data-testid="contractor-card-siding"
        >
          <div className="flex items-center gap-3 mb-4 text-[var(--brand-text)]">
            <HomeIcon className="w-8 h-8" />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold">
              {t("home.workspaceTag")}
            </span>
          </div>
          <h2 className="font-heading text-2xl text-[var(--ink)] mb-2">
            {t("home.sidingTitle")}
          </h2>
          <p className="text-sm text-[var(--ink-2)] mb-6">{t("home.sidingDesc")}</p>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--brand-text)] group-hover:underline">
            {t("home.sidingCta")}
          </div>
        </button>

        <button
          type="button"
          onClick={() => nav("/dashboard/lp_smart")}
          className="card text-left p-6 sm:p-8 group hover:border-[var(--brand)] transition-colors relative"
          data-testid="contractor-card-lp_smart"
        >
          {/* Iter 78ae — LP SmartSide is open for contractor testing.
              Swapped the amber "Under Construction" badge for a green
              "Beta · Feedback Welcome" invitation that matches the
              dashboard banner. */}
          <span
            className="absolute top-3 right-3 inline-flex items-center px-2.5 py-1 bg-[#ECFDF5] text-[#065F46] text-[10px] font-bold uppercase tracking-[0.16em] border border-[#6EE7B7] rounded-sm"
            data-testid="contractor-lp-beta-badge"
          >
            Beta · Feedback Welcome
          </span>
          <div className="flex items-center gap-3 mb-4 text-[var(--brand-text)]">
            <Layers className="w-8 h-8" />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold">
              {t("home.workspaceTag")}
            </span>
          </div>
          <h2 className="font-heading text-2xl text-[var(--ink)] mb-2">
            {t("home.lpTitle")}
          </h2>
          <p className="text-sm text-[var(--ink-2)] mb-6">{t("home.lpDesc")}</p>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--brand-text)] group-hover:underline">
            {t("home.lpCta")}
          </div>
        </button>
      </div>
    </main>
  );
}
