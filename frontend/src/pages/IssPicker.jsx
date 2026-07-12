import React from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Home as HomeIcon, RectangleHorizontal, Hammer } from "lucide-react";
import { useT } from "@/lib/i18n";
import { useBranding } from "@/lib/branding";

/**
 * Iter 76 — Step 2A: ISS Quotes sub-picker.
 *
 * Three options:
 *   - ISS Siding Quotes              → /dashboard/iss
 *   - ISS Window Quotes              → /dashboard/windows
 *   - ISS New Construction Siding    → disabled (Coming Soon, awaiting catalog)
 */
export default function IssPicker() {
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
        data-testid="iss-picker-back"
      >
        {t("home.back")}
      </button>

      <div className="mb-10 sm:mb-12">
        <div className="section-tag mb-3">{t("home.issGroupTitle")}</div>
        <h1 className="font-heading text-3xl sm:text-4xl text-[var(--ink)]">
          {t("home.iss.title")}
        </h1>
        <p className="mt-2 text-[var(--ink-2)] max-w-2xl text-sm sm:text-base">
          {t("home.iss.subtitle")}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <button
          type="button"
          onClick={() => nav("/dashboard/iss")}
          className="card text-left p-6 sm:p-8 group hover:border-[var(--brand)] transition-colors"
          data-testid="iss-card-siding"
        >
          <div className="flex items-center gap-3 mb-4 text-[var(--brand-text)]">
            <HomeIcon className="w-8 h-8" />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold">
              {t("home.workspaceTag")}
            </span>
          </div>
          <h2 className="font-heading text-2xl text-[var(--ink)] mb-2">
            {t("home.issTitle")}
          </h2>
          <p className="text-sm text-[var(--ink-2)] mb-6">{t("home.issDesc")}</p>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--brand-text)] group-hover:underline">
            {t("home.issCta")}
          </div>
        </button>

        <button
          type="button"
          onClick={() => nav("/dashboard/windows")}
          className="card text-left p-6 sm:p-8 group hover:border-[var(--brand)] transition-colors"
          data-testid="iss-card-windows"
        >
          <div className="flex items-center gap-3 mb-4 text-[var(--brand-text)]">
            <RectangleHorizontal className="w-8 h-8" />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold">
              {t("home.workspaceTag")}
            </span>
          </div>
          <h2 className="font-heading text-2xl text-[var(--ink)] mb-2">
            {t("home.issWindowsTitle")}
          </h2>
          <p className="text-sm text-[var(--ink-2)] mb-6">
            {t("home.issWindowsDesc")}
          </p>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--brand-text)] group-hover:underline">
            {t("home.issWindowsCta")}
          </div>
        </button>

        {/* ISS New Construction Siding — pricing sheet pending from Howard.
            Card is intentionally disabled with a "Coming Soon" CTA so it
            shows in the picker but doesn't navigate anywhere yet. */}
        <div
          className="card text-left p-6 sm:p-8 opacity-60 cursor-not-allowed border-dashed"
          data-testid="iss-card-new-construction"
          aria-disabled="true"
        >
          <div className="flex items-center gap-3 mb-4 text-[var(--muted)]">
            <Hammer className="w-8 h-8" />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold">
              {t("home.workspaceTag")}
            </span>
          </div>
          <h2 className="font-heading text-2xl text-[var(--ink)] mb-2">
            {t("home.issNewConTitle")}
          </h2>
          <p className="text-sm text-[var(--ink-2)] mb-6">
            {t("home.issNewConDesc")}
          </p>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--muted)]">
            {t("home.issNewConCta")}
          </div>
        </div>
      </div>
    </main>
  );
}
