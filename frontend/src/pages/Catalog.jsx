import React, { useEffect, useState, useCallback, useMemo } from "react";
import api, { formatApiError } from "@/lib/api";
import { useT, useLang } from "@/lib/i18n";
import { tSection, tItem, tUnit } from "@/lib/catalogTranslations";
import { toast } from "sonner";
import { Save, RotateCcw, Lock } from "lucide-react";
import { VISIBLE_TAB_IDS, VISIBLE_TAB_DEFS } from "@/lib/tabsConfig";

export default function Catalog() {
  const [sections, setSections] = useState([]);
  const [tierName, setTierName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  // Active product-line tab on the catalog page. Mirrors the estimator's
  // Excel-style tab strip so contractors can edit labor on Vinyl, Ascend
  // and Windows independently without scrolling through all sections.
  const [activeTab, setActiveTab] = useState(VISIBLE_TAB_IDS[0] || "vinyl");
  const t = useT();
  const { lang } = useLang();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/catalog");
      // Hide sections that belong only to tabs the contractor has turned off
      // in tabsConfig (e.g. LP SmartSide while LP pricing is paused). The
      // backend still returns everything so catalog data stays intact —
      // we just don't render hidden sections in the catalog admin UI.
      const visible = (data.sections || []).filter((s) => {
        const pls = s.product_lines || ["vinyl", "ascend"];
        return pls.some((p) => VISIBLE_TAB_IDS.includes(p));
      });
      setSections(visible);
      setTierName(data.tier_name || "");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updateItem = (si, ii, key, val) => {
    setSections((arr) => {
      const next = JSON.parse(JSON.stringify(arr));
      // Contractor can only override labor; material is supplier-controlled
      if (key !== "lab") return arr;
      next[si].items[ii].lab = Number(val) || 0;
      const item = next[si].items[ii];
      item.lab_overridden = Number(val) !== Number(item.tier_lab);
      return next;
    });
  };

  const resetItem = (si, ii) => {
    setSections((arr) => {
      const next = JSON.parse(JSON.stringify(arr));
      const it = next[si].items[ii];
      it.lab = it.tier_lab;
      it.lab_overridden = false;
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      // Build labor-only overrides; material is locked supplier-side
      const overrides = {};
      sections.forEach((s) => {
        s.items.forEach((it) => {
          if (it.lab_overridden) {
            overrides[`${s.title}::${it.name}`] = { lab: it.lab };
          }
        });
      });
      await api.put("/catalog", { overrides });
      toast.success(t("cat.saved"));
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const resetAll = async () => {
    if (!window.confirm(t("cat.resetConfirm"))) return;
    const { data } = await api.post("/catalog/reset");
    setSections(data.sections);
    toast.success(t("cat.resetDone"));
  };

  // Sections that belong to the active tab. Sections with multi-tab
  // product_lines (e.g. shared Misc rows) appear under every relevant tab.
  const visibleSections = useMemo(
    () =>
      sections.filter((s) =>
        (s.product_lines || ["vinyl", "ascend"]).includes(activeTab)
      ),
    [sections, activeTab]
  );

  // Per-tab override count for the tab badge so contractors can see at a
  // glance which tab has labor edits in flight (not yet saved or already
  // saved as an override).
  const tabBadges = useMemo(() => {
    const counts = {};
    VISIBLE_TAB_DEFS.forEach((t) => (counts[t.id] = 0));
    sections.forEach((s) => {
      const pls = s.product_lines || ["vinyl", "ascend"];
      const overrideCount = (s.items || []).filter((it) => it.lab_overridden).length;
      pls.forEach((p) => {
        if (counts[p] != null) counts[p] += overrideCount;
      });
    });
    return counts;
  }, [sections]);

  if (loading) return <div className="p-10 text-center text-[#52525B]">{t("common.loading")}</div>;

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="catalog-page">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-[#71717A] mb-1">{t("cat.eyebrow")}</div>
          <h1 className="font-heading text-4xl text-[#09090B]">{t("cat.title")}</h1>
          <div className="flex items-center gap-3 mt-3">
            <span className="inline-flex items-center gap-2 bg-[#09090B] text-[#F97316] px-3 py-1 text-xs font-bold uppercase tracking-wider" data-testid="tier-badge">
              <Lock className="w-3 h-3" /> {t("cat.tier", { name: tierName })}
            </span>
            <span className="text-xs text-[#52525B]">
              {t("cat.intro")}
            </span>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary" onClick={resetAll} data-testid="reset-catalog-btn">
            <RotateCcw className="w-4 h-4" /> {t("cat.clearOverrides")}
          </button>
          <button className="btn-primary" onClick={save} disabled={saving} data-testid="save-catalog-btn">
            <Save className="w-4 h-4" /> {saving ? t("common.saving") : t("cat.save")}
          </button>
        </div>
      </div>

      <div
        className="card mb-4 p-2 flex flex-wrap gap-1"
        role="tablist"
        data-testid="catalog-tabs"
      >
        {VISIBLE_TAB_DEFS.map((tab) => {
          const isActive = activeTab === tab.id;
          const badge = tabBadges[tab.id] || 0;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab.id)}
              data-testid={`catalog-tab-${tab.id}`}
              className={[
                "flex-1 min-w-[140px] px-4 py-3 text-left border transition-colors",
                isActive
                  ? "border-[#F97316] bg-orange-50"
                  : "border-[#E4E4E7] bg-white hover:border-[#A1A1AA]",
              ].join(" ")}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={[
                    "text-xs uppercase tracking-[0.18em] font-bold",
                    isActive ? "text-[#C2410C]" : "text-[#52525B]",
                  ].join(" ")}
                >
                  {tab.label}
                </span>
                {badge > 0 && (
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5 bg-[#F97316] text-[#09090B]"
                    title={`${badge} labor override${badge === 1 ? "" : "s"} on this tab`}
                  >
                    {badge}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <div className="space-y-8">
        {visibleSections.map((s) => (
          <div key={s.title} className="card">
            <div className="px-5 py-3 border-b border-[#E4E4E7]">
              <div className="section-tag">{tSection(s.title, lang)}</div>
            </div>
            <div className="hidden md:grid grid-cols-12 gap-3 px-5 py-2 text-[10px] uppercase tracking-[0.18em] text-[#71717A] font-bold border-b border-[#E4E4E7]">
              <div className="col-span-5">{t("cat.col.item")}</div>
              <div className="col-span-1">{t("cat.col.unit")}</div>
              <div className="col-span-2 text-right">{t("cat.col.material")}</div>
              <div className="col-span-2 text-right">{t("cat.col.labor")}</div>
              <div className="col-span-2"></div>
            </div>
            {s.items.map((it) => {
              const ii = s.items.indexOf(it);
              const si = sections.indexOf(s);
              return (
                <div key={it.name} className="grid grid-cols-12 gap-3 px-5 py-2 border-b border-[#E4E4E7] items-center">
                  <div className="col-span-12 md:col-span-5 text-sm text-[#09090B]">{tItem(it.name, lang)}</div>
                  <div className="col-span-3 md:col-span-1 text-xs text-[#71717A] uppercase tracking-wider">
                    {tUnit(it.unit, lang)}
                  </div>
                  <div className="col-span-4 md:col-span-2 text-right text-sm font-mono-num text-[#52525B] flex items-center justify-end gap-1.5">
                    <Lock className="w-3 h-3 text-[#71717A]" />
                    {it.mat.toLocaleString("en-US", { style: "currency", currency: "USD" })}
                  </div>
                  <div className="col-span-4 md:col-span-2">
                    <input
                      className={`input num h-10 ${it.lab_overridden ? "border-[#F97316] bg-orange-50" : ""}`}
                      type="number"
                      step="0.01"
                      value={it.lab}
                      onChange={(e) => updateItem(si, ii, "lab", e.target.value)}
                      title={it.lab_overridden ? `Tier default: $${it.tier_lab}` : ""}
                    />
                  </div>
                  <div className="col-span-1 md:col-span-2 text-right">
                    {it.lab_overridden && (
                      <button
                        className="btn-ghost text-[#C2410C]"
                        onClick={() => resetItem(si, ii)}
                        title="Reset labor to tier default"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </main>
  );
}
