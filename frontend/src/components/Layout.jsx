import React from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useCompany } from "@/lib/company";
import { useT } from "@/lib/i18n";
import { LogOut, LayoutGrid, Settings2, Users } from "lucide-react";
import CompanyLogo from "@/components/CompanyLogo";
import InstallBanner from "@/components/InstallBanner";
import LangToggle from "@/components/LangToggle";
import ThemePicker from "@/components/ThemePicker";
import Footer from "@/components/Footer";

export default function Layout() {
  const { user, logout } = useAuth();
  const { company } = useCompany();
  const t = useT();
  const nav = useNavigate();
  const loc = useLocation();

  const roleLabel =
    user?.role === "owner"
      ? t("nav.role.owner")
      : user?.role === "estimator"
      ? t("nav.role.estimator")
      : user?.role || "";

  const linkCls = (path) =>
    `px-3 py-2 text-sm font-semibold uppercase tracking-wider border-b-2 transition-colors ${
      loc.pathname === path || (path === "/" && loc.pathname.startsWith("/estimate"))
        ? "border-[var(--brand)] text-[var(--ink)]"
        : "border-transparent text-[var(--ink-2)] hover:text-[var(--ink)]"
    }`;

  return (
    <div className="min-h-screen bg-[var(--bg-app)] flex flex-col">
      <header className="bg-[var(--surface)] border-b border-[var(--border)] sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-3" data-testid="brand-link">
            <CompanyLogo company={company} size={36} testid="nav-logo" />
            <div className="leading-tight">
              <div className="font-heading text-base text-[var(--ink)]" style={{ minHeight: "1em" }}>
                {company?.name || "\u00A0"}
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)]">{t("nav.estimatorTag")}</div>
            </div>
          </Link>
          <nav className="hidden sm:flex items-center gap-1">
            <Link to="/" className={linkCls("/")} data-testid="nav-estimates">
              <LayoutGrid className="inline w-4 h-4 mr-1" /> {t("nav.estimates")}
            </Link>
            <Link to="/catalog" className={linkCls("/catalog")} data-testid="nav-catalog">
              <Settings2 className="inline w-4 h-4 mr-1" /> {t("nav.catalog")}
            </Link>
            <Link to="/team" className={linkCls("/team")} data-testid="nav-team">
              <Users className="inline w-4 h-4 mr-1" /> {t("nav.team")}
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <ThemePicker />
            <LangToggle />
            <div className="hidden sm:block text-right">
              <div className="text-sm font-semibold text-[var(--ink)]" data-testid="user-name">
                {user?.name}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{roleLabel}</div>
            </div>
            <button
              className="btn-ghost"
              onClick={async () => {
                await logout();
                nav("/login");
              }}
              data-testid="logout-btn"
              aria-label={t("nav.logout")}
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="sm:hidden flex border-t border-[var(--border)]">
          <Link to="/" className={`flex-1 text-center ${linkCls("/")}`}>{t("nav.estimates")}</Link>
          <Link to="/catalog" className={`flex-1 text-center ${linkCls("/catalog")}`}>{t("nav.catalog")}</Link>
          <Link to="/team" className={`flex-1 text-center ${linkCls("/team")}`}>{t("nav.team")}</Link>
        </div>
      </header>
      <div className="flex-1">
        <Outlet />
      </div>
      <Footer />
      <InstallBanner />
    </div>
  );
}
