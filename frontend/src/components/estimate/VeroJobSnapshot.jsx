import React, { useMemo } from "react";
import { LayoutGrid, Hammer, Boxes } from "lucide-react";
import { useT } from "@/lib/i18n";

const fmt = (n) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(n) || 0);

// Same 6 shared sections the Mezzo snapshot uses — Vero shares Install,
// Trim and Material List with Mezzo via product_lines["vero","mezzo"].
const MATERIAL_SECTIONS = new Set(["Window Material List"]);
const INSTALL_SECTIONS = new Set([
  "Window Installation",
  "Sliding Glass Door Install",
  "Window Exterior Trim Work",
  "Window Interior Trim Work",
  "Window Misc.",
]);

/**
 * At-a-glance Vero tab snapshot. Mirrors MezzoJobSnapshot but reads
 * `est.vero_openings`. Each opening's per-window price stack =
 *   base + glass + tempered + premium (all snapshotted by VeroPanel).
 */
export default function VeroJobSnapshot({ est }) {
  const t = useT();
  const snapshot = useMemo(() => {
    const openings = est?.vero_openings || [];
    const openingCount = openings.reduce((s, o) => s + (Number(o.qty) || 0), 0);
    const pq = est?.vero_package_quote;
    const packageQuoteActive = !!pq?.enabled && Number(pq?.total) > 0;
    const openingDollars = packageQuoteActive
      ? Number(pq.total)
      : openings.reduce((sum, o) => {
          // Iter 44: Mezzo-style adders. Read legacy glass/temp/premium as
          // a fallback so historical estimates retain their totals.
          const base = (Number(o.qty) || 0) * (Number(o.base_mat) || 0);
          const ads = (o.adders || []).reduce(
            (a, x) => a + (Number(x.qty) || 0) * (Number(x.mat) || 0),
            0
          );
          const legacy =
            (Number(o.qty) || 0) * (
              (Number(o.glass_mat) || 0)
              + (Number(o.tempered_mat) || 0)
              + (Number(o.premium_mat) || 0)
            );
          return sum + base + ads + legacy;
        }, 0);

    // The windows-kind workspace uses "windows" as the Vero tab id (per
    // tabsConfig.js — Vero entries on the catalog get tab: "windows"). The
    // Mezzo tab uses "mezzo". Iter 42g fix: this filter was checking for
    // "vero" which never matches → Install/Trim/Material panels showed $0.
    const veroLines = (est?.lines || []).filter(
      (l) => (l.tab || "vinyl") === "windows" && (Number(l.qty) || 0) > 0
    );
    let installDollars = 0;
    let installLineCount = 0;
    let materialDollars = 0;
    let materialLineCount = 0;
    for (const l of veroLines) {
      const qty = Number(l.qty) || 0;
      const lineMat = qty * (Number(l.mat) || 0);
      const lineLab = qty * (Number(l.lab) || 0);
      const addersTotal = (l.adders || []).reduce(
        (a, ad) => a + (Number(ad.qty) || 0) * ((Number(ad.mat) || 0) + (Number(ad.lab) || 0)),
        0
      );
      if (MATERIAL_SECTIONS.has(l.section)) {
        materialDollars += lineMat + lineLab + addersTotal;
        materialLineCount += 1;
      } else if (INSTALL_SECTIONS.has(l.section)) {
        installDollars += lineMat + lineLab + addersTotal;
        installLineCount += 1;
      }
    }
    return {
      openingCount,
      openingDollars,
      installDollars,
      installLineCount,
      materialDollars,
      materialLineCount,
      total: openingDollars + installDollars + materialDollars,
    };
  }, [est]);

  const isEmpty =
    snapshot.openingCount === 0
    && snapshot.installLineCount === 0
    && snapshot.materialLineCount === 0;

  return (
    <section className="card mb-4 overflow-hidden" data-testid="vero-job-snapshot">
      <header className="flex items-center justify-between px-4 md:px-5 py-3 border-b border-[var(--border)] bg-[var(--surface-muted)]">
        <div>
          <div className="section-tag">Vero {t("win.snapshot")}</div>
          <div className="text-[10px] text-[var(--muted)] mt-0.5">
            {t("win.snapshot.subtitle")}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)] font-bold">{t("win.snapshot.baseTotal")}</div>
          <div
            className="font-mono-num text-2xl font-bold text-[var(--ink)] leading-tight"
            data-testid="vero-snapshot-total"
          >
            {fmt(snapshot.total)}
          </div>
        </div>
      </header>
      {isEmpty ? (
        <div className="px-5 py-5 text-center text-[12px] text-[var(--muted)]">
          {t("win.snapshot.empty")}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 divide-x divide-[#E4E4E7]">
          <StatTile
            icon={<LayoutGrid className="w-3.5 h-3.5" />}
            label={t("win.snapshot.openings")}
            value={t(snapshot.openingCount === 1 ? "win.snapshot.windowsCount" : "win.snapshot.windowsCountPlural", { n: snapshot.openingCount })}
            sub={fmt(snapshot.openingDollars)}
            accent="orange"
            testid="vero-snapshot-openings"
          />
          <StatTile
            icon={<Hammer className="w-3.5 h-3.5" />}
            label={t("win.snapshot.installTrim")}
            value={fmt(snapshot.installDollars)}
            sub={t(snapshot.installLineCount === 1 ? "win.snapshot.installSub" : "win.snapshot.installSubPlural", { n: snapshot.installLineCount })}
            accent="black"
            testid="vero-snapshot-install"
          />
          <StatTile
            icon={<Boxes className="w-3.5 h-3.5" />}
            label={t("win.snapshot.material")}
            value={fmt(snapshot.materialDollars)}
            sub={t(snapshot.materialLineCount === 1 ? "win.snapshot.materialSub" : "win.snapshot.materialSubPlural", { n: snapshot.materialLineCount })}
            accent="muted"
            testid="vero-snapshot-material"
          />
        </div>
      )}
    </section>
  );
}

function StatTile({ icon, label, value, sub, accent, testid }) {
  const accentText =
    accent === "orange" ? "text-[var(--brand-text)]"
      : accent === "black" ? "text-[var(--ink)]"
        : "text-[var(--ink-2)]";
  const accentBg =
    accent === "orange" ? "bg-[#FFF7ED]"
      : accent === "black" ? "bg-[var(--surface-muted)]"
        : "bg-[var(--surface)]";
  return (
    <div className={`px-4 md:px-5 py-3 ${accentBg}`} data-testid={testid}>
      <div className={`flex items-center gap-1.5 text-[10px] uppercase tracking-[0.2em] font-bold ${accentText}`}>
        {icon}
        <span className="text-[var(--ink-2)]">{label}</span>
      </div>
      <div className={`font-mono-num text-lg font-bold mt-1.5 ${accent === "muted" ? "text-[#3F3F46]" : "text-[var(--ink)]"}`}>
        {value}
      </div>
      {sub ? (
        <div className="text-[11px] text-[var(--muted)] font-mono-num mt-0.5 truncate" title={sub}>{sub}</div>
      ) : null}
    </div>
  );
}
