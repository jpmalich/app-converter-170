import React, { useRef } from "react";
import { fmt } from "@/lib/api";
import { VISIBLE_TAB_DEFS } from "@/lib/tabsConfig";

/**
 * Product-line tab strip for the multi-product estimator.
 *
 * The contractor can quote up to three parallel options on one estimate —
 * Vinyl, Ascend, and LP Smart Siding. Each tab holds its own line items so
 * the homeowner can compare options apples-to-apples on one quote.
 *
 * Per-tab subtotal = sum of (qty × (mat + lab)) for that tab's lines + its
 * misc rows. The Grand Total at the bottom of the page still rolls all
 * tabs together so the contractor sees the full quote value.
 *
 * Implements the WAI-ARIA tabs keyboard pattern: roving tabindex + Arrow/
 * Home/End navigation, with `aria-controls` pointing at the shared tabpanel
 * (`#estimate-tabpanel`, rendered by EstimateEditor). The section content is
 * rendered by the parent, not here, so a manually-managed tablist is the right
 * fit rather than Radix Tabs (which co-locates triggers and content).
 */
export const TABS = VISIBLE_TAB_DEFS;

export const TABPANEL_ID = "estimate-tabpanel";

function subtotalForTab(est, tabId) {
  const lines = (est?.lines || []).filter((l) => (l.tab || "vinyl") === tabId);
  const miscLab = (est?.misc_labor || []).filter((m) => (m.tab || "vinyl") === tabId);
  const miscMat = (est?.misc_material || []).filter((m) => (m.tab || "vinyl") === tabId);
  const linesSell = lines.reduce(
    (s, l) => s + (l.qty || 0) * ((l.mat || 0) + (l.lab || 0)),
    0
  );
  const miscSell =
    miscLab.reduce((s, m) => s + (m.lab || 0), 0) +
    miscMat.reduce((s, m) => s + (m.mat || 0) + (m.lab || 0), 0);
  return linesSell + miscSell;
}

function filledCountForTab(est, tabId) {
  return (est?.lines || []).filter(
    (l) => (l.tab || "vinyl") === tabId && (l.qty || 0) > 0
  ).length;
}

export function tabButtonId(tabId) {
  return `estimator-tab-${tabId}`;
}

export default function EstimatorTabs({ est, activeTab, onChange, tabs = TABS }) {
  const listRef = useRef(null);

  const focusTab = (tabId) => {
    const btn = listRef.current?.querySelector(`#${CSS.escape(tabButtonId(tabId))}`);
    if (btn) btn.focus();
  };

  const onKeyDown = (e) => {
    const idx = tabs.findIndex((t) => t.id === activeTab);
    if (idx < 0) return;
    let next = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (idx + 1) % tabs.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (idx - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    if (next === null) return;
    e.preventDefault();
    const nextId = tabs[next].id;
    onChange(nextId);
    focusTab(nextId);
  };

  return (
    <div
      ref={listRef}
      className="card mb-4 p-2 flex flex-wrap gap-1"
      role="tablist"
      aria-label="Product line"
      onKeyDown={onKeyDown}
      data-testid="estimator-tabs"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const count = filledCountForTab(est, tab.id);
        const subtotal = subtotalForTab(est, tab.id);
        return (
          <button
            key={tab.id}
            id={tabButtonId(tab.id)}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={TABPANEL_ID}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab.id)}
            data-testid={`estimator-tab-${tab.id}`}
            className={[
              "flex-1 min-w-[140px] px-4 py-3 text-left border transition-colors outline-none",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
              isActive
                ? "border-[var(--brand)] bg-[var(--surface-muted)]"
                : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--muted)]",
            ].join(" ")}
            style={isActive ? { boxShadow: "inset 0 -2px 0 var(--brand)" } : undefined}
          >
            <div className="flex items-center justify-between gap-2">
              <span
                className={[
                  "text-xs uppercase tracking-[0.18em] font-bold",
                  isActive ? "text-[var(--brand-text)]" : "text-[var(--ink-2)]",
                ].join(" ")}
              >
                {tab.label}
              </span>
              {count > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 bg-[var(--bg-app)] text-[var(--ink-2)] rounded-sm">
                  {count}
                </span>
              )}
            </div>
            <div
              className={[
                "mt-1 font-mono-num text-sm",
                isActive ? "text-[var(--ink)] font-bold" : "text-[var(--muted)]",
              ].join(" ")}
            >
              {fmt(subtotal)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
