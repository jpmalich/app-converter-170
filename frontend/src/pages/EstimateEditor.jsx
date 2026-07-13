import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import api, { API, formatApiError } from "@/lib/api";
import { useT, useLang } from "@/lib/i18n";
import { useCompany } from "@/lib/company";
import { useBranding } from "@/lib/branding";
import useEstimate from "@/lib/useEstimate";
import useReconcileWindowSnapshots from "@/lib/useReconcileWindowSnapshots";
import useRecalcSoffitOnOverhang from "@/lib/useRecalcSoffitOnOverhang";
import { calcTotals } from "@/lib/calc";
import { buildMaterialListHtml, materialListFilename } from "@/lib/materialList";
import { buildLpMaterialListHtml } from "@/lib/lpMaterialList";
import QRCode from "qrcode";
import StickyBar from "@/components/estimate/StickyBar";
import JobInfoPanel from "@/components/estimate/JobInfoPanel";
import MezzoPanel from "@/components/estimate/MezzoPanel";
import MezzoJobSnapshot from "@/components/estimate/MezzoJobSnapshot";
import VeroPanel from "@/components/estimate/VeroPanel";
import VeroJobSnapshot from "@/components/estimate/VeroJobSnapshot";
import SettingsRow from "@/components/estimate/SettingsRow";
import PhotosPanel from "@/components/estimate/PhotosPanel";
import SectionAccordion from "@/components/estimate/SectionAccordion";
import TotalsSummary from "@/components/estimate/TotalsSummary";
import CatalogSyncBanner from "@/components/estimate/CatalogSyncBanner";
import EstimatorTabs from "@/components/estimate/EstimatorTabs";
import { VISIBLE_TAB_IDS, ALL_TAB_DEFS, WINDOWS_KIND_TAB_IDS, LP_KIND_TAB_IDS, SIDING_KIND_TAB_IDS } from "@/lib/tabsConfig";
import QuoteModal from "@/components/QuoteModal";
import TabPickerModal from "@/components/TabPickerModal";
import LpMaterialListPanel from "@/components/estimate/LpMaterialListPanel";
import { LP_SECTION_TITLES } from "@/lib/lpColors";

export default function EstimateEditor() {
  const { id } = useParams();
  const nav = useNavigate();
  const t = useT();
  const { lang } = useLang();
  const { company } = useCompany();
  const branding = useBranding();
  const { est, catalog, loading, emailStatus, update, updateLineQty, updateLineField, resetLineToDefault, toggleLineAdder, updateAdderQty, setInstallMethod, setHomePre1978, save } = useEstimate(id);
  // Reconcile window-opening price snapshots once per estimate load — fixes
  // the $0 totals on freshly HOVER-imported windows estimates whose openings
  // arrive with base_mat: 0. No-op for estimates without window openings.
  useReconcileWindowSnapshots(est, update);
  // Iter 78ai/78aj/78ak — Auto-recalculate soffit qty (Charter Oak + LP
  // Vented + LP Closed) and Porch Ceiling labor rows (Charter Oak + Wrap
  // porch beam) when the contractor changes Eave Overhang or porch
  // ceiling dimensions. Pulls eaves_lf / rakes_lf from cached
  // hover_measurements; catalog is passed in so the hook can hydrate
  // mat/lab when it auto-adds new Porch Ceiling rows.
  useRecalcSoffitOnOverhang(est, update, catalog);
  // Start with every section collapsed so the editor stays compact —
  // contractors expand only the categories they need for the job.
  const [openSections, setOpenSections] = useState({});
  const [saving, setSaving] = useState(false);
  const [showQuote, setShowQuote] = useState(false);
  // Tab-picker modal — appears when the contractor clicks Customer Quote
  // or Material List on a hybrid estimate that spans multiple product
  // lines. mode is "quote" or "materials"; quoteFilter / materialsFilter
  // hold the array of tab ids selected.
  const [pickerMode, setPickerMode] = useState(null);
  const [tabFilter, setTabFilter] = useState(null); // null = include all tabs
  // Active product-line tab. Default depends on the estimate's `kind`:
  // window estimates start on the Windows tab and lock to just that one;
  // LP-kind start on lp_smart; siding estimates start on Vinyl.
  const isWindowKind = est?.kind === "windows";
  const isLpKind = est?.kind === "lp_smart";
  // Iter 99 — live derived package shared up from LpMaterialListPanel
  // (one-surface rule: exports compose from this, never legacy lines)
  const [lpPkg, setLpPkg] = useState(null);
  const [lpMeta, setLpMeta] = useState(null);
  const [activeTab, setActiveTab] = useState("vinyl");

  // Iter 37: For windows-kind, snap to "windows" (Vero) on first load
  // only if the current activeTab is a siding-only tab — otherwise leave
  // the user's choice intact so toggling to Mezzo sticks. For siding-
  // kind, leave the default "vinyl" alone.
  // Iter 73: same snap behavior for lp_smart-kind → snap to "lp_smart".
  useEffect(() => {
    if (isWindowKind && activeTab !== "windows" && activeTab !== "mezzo") {
      setActiveTab("windows");
    } else if (isLpKind && activeTab !== "lp_smart") {
      setActiveTab("lp_smart");
    }
  }, [isWindowKind, isLpKind, activeTab]);

  // Visible tab set for THIS estimate.
  //   windows kind → Vero + Mezzo (Iter 37)
  //   lp_smart kind → LP only (Iter 73)
  //   siding kind  → Vinyl + Ascend (Iter 73 — LP got its own workspace;
  //     Iter 78z++++ dropped the legacy back-compat path so siding now
  //     NEVER renders the LP tab regardless of stored data).
  const visibleTabIds = useMemo(() => {
    if (isWindowKind) return WINDOWS_KIND_TAB_IDS;
    if (isLpKind) return LP_KIND_TAB_IDS;
    // Iter 78z++++ — Howard removed LP from the siding workspace.
    // Even legacy estimates that had LP imports applied to them
    // before now render only Vinyl + Ascend tabs. LP line data stays
    // in MongoDB (recoverable) but is invisible in the siding UI; to
    // quote LP for the same job, use the LP standalone workspace.
    return SIDING_KIND_TAB_IDS.filter((id) => VISIBLE_TAB_IDS.includes(id));
  }, [isWindowKind, isLpKind]);
  // Tab defs aligned to visibleTabIds (preserves label + order).
  const visibleTabDefs = useMemo(
    () => ALL_TAB_DEFS.filter((t) => visibleTabIds.includes(t.id)),
    [visibleTabIds]
  );
  const totals = useMemo(() => (est ? calcTotals(est, { tab: activeTab }) : null), [est, activeTab]);
  // Per-tab totals for the sticky bar. Only compute for visible tabs so
  // hidden product lines don't ghost into the header.
  const tabTotals = useMemo(() => {
    if (!est) return [];
    return visibleTabIds.map((id) => ({
      id,
      totals: calcTotals(est, { tab: id }),
    }));
  }, [est, visibleTabIds]);

  // Compute which tabs actually have line items so the picker only shows
  // tabs that have data — Vinyl-only estimates never see the picker.
  const tabsWithData = useMemo(() => {
    const s = new Set();
    for (const l of est?.lines || []) {
      if ((l.qty || 0) > 0) s.add(l.tab || "vinyl");
    }
    // Openings itemize on the quote now — count them as tab data too.
    if ((est?.vero_openings || []).some((op) => (Number(op.qty) || 0) > 0)) s.add("windows");
    if ((est?.mezzo_openings || []).some((op) => (Number(op.qty) || 0) > 0)) s.add("mezzo");
    return Array.from(s);
  }, [est]);

  // Filtered estimate that the QuoteModal renders. When the picker isn't
  // applied (single-tab estimate or quote was opened directly), tabFilter
  // stays null and we pass the full estimate through.
  const quoteEstimate = useMemo(() => {
    if (!est) return est;
    // CUSTOMER QUOTE COMPOSITION (ruled iter100): derived material
    // package (quote tier, colors, session substitutions) governs the
    // LP material sections; contractor service lines stay theirs from
    // est.lines; pending lines carry a flag — never hidden, never $0.
    let base = est;
    if (isLpKind && lpPkg) {
      // The package governs EVERY line it derives — any section (LP
      // materials, gutters, caps). Pending lines carry the flag with
      // mat 0 so they render blank + qualifier and never hit the total.
      const pkgLines = (lpPkg.lines || [])
        .filter((l) => (l.qty || 0) > 0)
        .map((l) => ({
          section: l.section,
          name: l.color ? `${l.name} — ${l.color}` : l.name,
          unit: l.unit,
          qty: l.qty,
          mat: l.pricing_status === "priced" ? l.unit_sell || 0 : 0,
          lab: 0,
          tab: "lp_smart",
          adders: [],
          pricing_pending: l.pricing_status !== "priced",
        }));
      // Contractor service lines: stored lp_smart lines the package does
      // NOT track (their labor/services keep contractor pricing). Lines
      // the package derives are deduped by name so a stale stored price
      // can never shadow the derived/pending truth.
      const pkgNames = new Set();
      (lpPkg.lines || []).forEach((l) => {
        pkgNames.add(l.name);
        if (l.substituted_from) pkgNames.add(l.substituted_from);
      });
      const serviceLines = (est.lines || []).filter(
        (l) =>
          (l.tab || "vinyl") === "lp_smart" &&
          !pkgNames.has(l.name) &&
          !LP_SECTION_TITLES.has(l.section) &&
          (l.qty || 0) > 0
      );
      base = { ...est, lines: [...pkgLines, ...serviceLines] };
    }
    if (!tabFilter) return base;
    return {
      ...base,
      lines: (base.lines || []).filter((l) =>
        tabFilter.includes(l.tab || "vinyl")
      ),
      misc_labor: (est.misc_labor || []).filter((m) =>
        tabFilter.includes(m.tab || "vinyl")
      ),
      misc_material: (est.misc_material || []).filter((m) =>
        tabFilter.includes(m.tab || "vinyl")
      ),
      // Ruled (d/b): openings itemize on the quote — scope them with the
      // picker exactly like calcTotals does (vero→windows, mezzo→mezzo).
      vero_openings: tabFilter.includes("windows") ? est.vero_openings || [] : [],
      mezzo_openings: tabFilter.includes("mezzo") ? est.mezzo_openings || [] : [],
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [est, tabFilter, isLpKind, lpPkg]);

  // Totals for the customer quote — scoped to the picked tabs so the
  // customer-facing PDF shows only the work-in-scope dollars.
  const quoteTotals = useMemo(
    () => (quoteEstimate ? calcTotals(quoteEstimate) : null),
    [quoteEstimate]
  );

  if (loading || !est) {
    if (est === false) {
      setTimeout(() => nav("/"), 0);
    }
    return (
      <div className="flex items-center justify-center h-[60vh] text-[var(--ink-2)]">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> {t("est.loading")}
      </div>
    );
  }

  // Filter catalog sections to those that belong to the active tab AND
  // are allowed by the estimate's kind. For window-kind estimates we
  // restrict to sections that include "windows" in product_lines so
  // siding sections never leak in.
  // Iter 39: on the Vero tab the 7 product-specific catalog sections are
  // replaced by the new W×H VeroPanel; keep the shared install/trim/misc
  // sections (which have ["windows","mezzo"] product_lines) visible.
  const VERO_PRODUCT_SECTIONS_HIDDEN_ON_VERO_TAB = new Set([
    "Vero Windows Custom Quote",
    "Vero Double Hung Windows",
    "Vero 2 Lite Slider Windows",
    "Vero 3 Lite Slider Windows",
    "Vero Casement Windows",
    "Vero Picture Windows",
    "Vero Sliding Glass Doors",
  ]);
  const visibleSections = catalog.filter((s) => {
    const pls = s.product_lines || ["vinyl", "ascend"];
    if (!pls.includes(activeTab)) return false;
    if (isWindowKind && !pls.includes("windows")) return false;
    if (activeTab === "windows" && VERO_PRODUCT_SECTIONS_HIDDEN_ON_VERO_TAB.has(s.title)) return false;
    return true;
  });

  // Lines grouped by section, scoped to the active tab. The catalog merge
  // in useEstimate creates one line entry per (tab, section, name), so we
  // just slice by activeTab here.
  const linesBySection = est.lines
    .filter((l) => (l.tab || "vinyl") === activeTab)
    .reduce((acc, l) => {
      (acc[l.section] = acc[l.section] || []).push(l);
      return acc;
    }, {});

  const handleSave = async () => {
    setSaving(true);
    await save();
    setSaving(false);
  };

  const handleExportCsv = async () => {
    try {
      const res = await api.get(`/exports/estimates/${id}.csv`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `estimate_${est.estimate_number || id}.csv`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  const handlePrintMaterials = async (tabsToInclude = null) => {
    // Save first so the server has the latest qty/color before we render the PDF.
    await handleSave();
    // Iter 99 — ONE-SURFACE RULE (ruled): when the derived LP package
    // exists, it is the ONLY material-list composition. The legacy
    // stored-lines composer never renders for LP estimates with a run.
    // Iter 100 — QR doctrine (ruled): every printed LP list freezes a
    // server-side snapshot and carries a QR to THAT exact version.
    let share = null;
    let trail = null;
    if (isLpKind && lpPkg) {
      // Verification trail (approved): honest count/status — partial
      // states shown as partial, never suppressed. Contractor surface
      // only (the printed crew list; never the public /m/ page).
      const amber = lpPkg.amber_items || [];
      const orv = lpPkg.openings_review || null;
      trail = {
        amber: {
          total: amber.length,
          verified: amber.filter((a) => a.status === "verified").length,
          unverified: amber.filter((a) => a.status !== "verified").map((a) => a.locator),
          verifiers: [...new Set(amber.filter((a) => a.verified_by).map((a) => a.verified_by))],
        },
        openings: orv && orv.total
          ? { total: orv.total, confirmed: orv.confirmed, corrected: orv.corrected, unconfirmed: orv.unconfirmed }
          : null,
      };
      try {
        const subs = {};
        (lpPkg.lines || []).forEach((l) => {
          if (l.substituted_from) subs[l.substituted_from] = l.name;
        });
        const { data } = await api.post(`/estimates/${id}/lp-material-list/freeze`, {
          colors: est.lp_colors && Object.keys(est.lp_colors).length ? est.lp_colors : undefined,
          substitutions: Object.keys(subs).length ? subs : undefined,
        });
        const shareUrl = `${window.location.origin}/m/${data.token}`;
        const qrDataUrl = await QRCode.toDataURL(shareUrl, { width: 240, margin: 1 });
        share = { shareUrl, qrDataUrl, printedAt: new Date().toISOString() };
      } catch {
        // QR is best-effort — the list still prints without it
      }
    }
    const html = isLpKind && lpPkg
      ? buildLpMaterialListHtml({ pkg: lpPkg, estimate: est, company, branding, lang, share, trail })
      : buildMaterialListHtml({
          estimate: tabsToInclude
            ? { ...est, lines: (est.lines || []).filter((l) => tabsToInclude.includes(l.tab || "vinyl")) }
            : est,
          company, branding, lang,
        });
    try {
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/estimates/${id}/pdf`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ recipient_email: "noreply@noreply.com", html_quote: html }),
        }
      );
      if (!res.ok) throw new Error(`PDF render failed: ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // Suffix the filename with the tabs included so the contractor knows
      // which file is which when they print Vinyl + Ascend separately.
      const suffix =
        tabsToInclude && tabsToInclude.length < 4
          ? `_${tabsToInclude.join("-")}`
          : "";
      const baseName = materialListFilename(est).replace(/\.pdf$/i, "");
      a.download = `${baseName}${suffix}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(`Could not generate material list: ${e.message}`);
    }
  };

  // Compute which tabs actually have line items so the picker only shows
  // tabs that have data — Vinyl-only estimates never see the picker.
  // (tabsWithData, quoteEstimate, quoteTotals declared above the early
  // return to keep hook order stable.)

  // Click handler for the Customer Quote button — when the job spans more
  // than one product line, ask the contractor which to include first.
  const handleOpenQuote = async () => {
    await handleSave();
    if (tabsWithData.length > 1) {
      setPickerMode("quote");
    } else {
      setTabFilter(null);
      setShowQuote(true);
    }
  };

  const handleOpenMaterials = async () => {
    if (isLpKind && lpPkg) {
      // one-surface rule: derived package is the only LP composition —
      // no tab picker, no legacy stored-lines render
      await handlePrintMaterials(null);
    } else if (tabsWithData.length > 1) {
      setPickerMode("materials");
    } else {
      await handlePrintMaterials(null);
    }
  };

  const handlePickerConfirm = async (tabs) => {
    const mode = pickerMode;
    setPickerMode(null);
    setTabFilter(tabs);
    if (mode === "quote") {
      setShowQuote(true);
    } else if (mode === "materials") {
      await handlePrintMaterials(tabs);
    }
  };

  return (
    <>
      <StickyBar est={est} tabTotals={tabTotals} activeTab={activeTab} tabs={visibleTabDefs} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-24" data-testid="estimate-editor">
        <CatalogSyncBanner est={est} update={update} />
        <JobInfoPanel
          est={est}
          update={update}
          save={save}
          setInstallMethod={setInstallMethod}
          setHomePre1978={setHomePre1978}
        />
        <SettingsRow est={est} update={update} />
        <PhotosPanel est={est} update={update} />

        <EstimatorTabs est={est} activeTab={activeTab} onChange={setActiveTab} tabs={visibleTabDefs} />

        {activeTab === "mezzo" ? (
          <>
            <MezzoJobSnapshot est={est} />
            <MezzoPanel est={est} update={update} />
            {visibleSections.map((s) => (
              <SectionAccordion
                key={s.title}
                section={s}
                lines={linesBySection[s.title] || []}
                isOpen={!!openSections[s.title]}
                onToggle={() => setOpenSections((o) => ({ ...o, [s.title]: !o[s.title] }))}
                onQty={updateLineQty}
                onField={updateLineField}
                onResetLine={resetLineToDefault}
                onToggleAdder={toggleLineAdder}
                onUpdateAdderQty={updateAdderQty}
                est={est}
                update={update}
                activeTab={activeTab}
              />
            ))}
          </>
        ) : activeTab === "windows" ? (
          <>
            <VeroJobSnapshot est={est} />
            <VeroPanel est={est} update={update} />
            {visibleSections.map((s) => (
              <SectionAccordion
                key={s.title}
                section={s}
                lines={linesBySection[s.title] || []}
                isOpen={!!openSections[s.title]}
                onToggle={() => setOpenSections((o) => ({ ...o, [s.title]: !o[s.title] }))}
                onQty={updateLineQty}
                onField={updateLineField}
                onResetLine={resetLineToDefault}
                onToggleAdder={toggleLineAdder}
                onUpdateAdderQty={updateAdderQty}
                est={est}
                update={update}
                activeTab={activeTab}
              />
            ))}
          </>
        ) : visibleSections.length === 0 ? (
          <>
            {isLpKind && activeTab === "lp_smart" && (
              <LpMaterialListPanel est={est} update={update} onPackage={setLpPkg} />
            )}
            <div
              className="card p-8 text-center"
              data-testid={`empty-tab-${activeTab}`}
            >
              <div className="section-tag mb-3">LP Smart Siding</div>
              <p className="text-sm text-[var(--ink-2)] max-w-md mx-auto">
                The LP SmartSide catalog hasn&apos;t been loaded yet. Send Howard your
                LP Smart Siding price sheet (Excel/CSV) and it&apos;ll populate here.
              </p>
            </div>
          </>
        ) : (
          <>
            {isLpKind && activeTab === "lp_smart" && (
              <LpMaterialListPanel est={est} update={update} onPackage={setLpPkg} />
            )}
            {visibleSections.map((s) => (
            <SectionAccordion
              key={s.title}
              section={s}
              lines={linesBySection[s.title] || []}
              isOpen={!!openSections[s.title]}
              onToggle={() => setOpenSections((o) => ({ ...o, [s.title]: !o[s.title] }))}
              onQty={updateLineQty}
              onField={updateLineField}
              onResetLine={resetLineToDefault}
              onToggleAdder={toggleLineAdder}
              onUpdateAdderQty={updateAdderQty}
              est={est}
              update={update}
              activeTab={activeTab}
            />
            ))}
          </>
        )}

        <TotalsSummary
          est={est}
          totals={totals}
          activeTab={activeTab}
          saving={saving}
          onSave={handleSave}
          onOpenQuote={handleOpenQuote}
          onPrint={() => window.print()}
          onExportCsv={handleExportCsv}
          onPrintMaterials={handleOpenMaterials}
        />
      </main>

      <TabPickerModal
        open={!!pickerMode}
        mode={pickerMode}
        tabsWithData={tabsWithData}
        onClose={() => setPickerMode(null)}
        onConfirm={handlePickerConfirm}
      />

      {showQuote && (
        <QuoteModal
          estimate={quoteEstimate}
          totals={quoteTotals}
          onClose={() => setShowQuote(false)}
          emailConfigured={emailStatus.configured}
          onEmail={async ({ recipient_email, html, subject, accept_token }) => {
            try {
              await api.post(`/estimates/${id}/email`, {
                recipient_email,
                html_quote: html,
                subject,
                accept_token,
              });
              toast.success(t("quote.sentToast"));
              // Iter 79j.47 — Two-way sync. If the sent address differs
              // from the stored customer_email, write it back through
              // update() so autosave persists it. This is why the
              // send flow no longer prompts "no email on file" the
              // next time the same estimate is reopened.
              const sent = (recipient_email || "").trim();
              const stored = (est?.customer_email || "").trim();
              if (sent && sent !== stored) update({ customer_email: sent });
              // Refresh local estimate through the proper state update
              // (Object.assign mutated the ref without re-rendering,
              // leaving pipeline stage badges stale).
              try {
                const { data } = await api.get(`/estimates/${id}`);
                if (data) update(data);
              } catch (err) {
                console.warn("[quote-modal] post-send refresh failed:", err?.message || err);
              }
              return true;
            } catch (e) {
              toast.error(formatApiError(e.response?.data?.detail));
              return false;
            }
          }}
        />
      )}
    </>
  );
}
