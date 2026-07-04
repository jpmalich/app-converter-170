// Iter 78u — Multi-source Elevation Drawing comparison modal.
//
// Reads `estimate.hover_measurements._ai_elevations_by_source` (populated
// by AI Measure / HOVER import / Blueprint import) and renders:
//   - Tabs: one per source the estimate has drawings from
//   - "Compare" tab: side-by-side rendering of every elevation that exists
//     in 2+ sources, so drift is instantly visible
//
// Read-only — no edits here. Re-import (or open the source's import modal)
// to nudge or override.
import React, { useMemo, useState } from "react";
import { X, Layers } from "lucide-react";
import ElevationDrawing from "@/components/estimate/ElevationDrawing";

const SOURCE_LABELS = {
  ai_photo: "AI Photo",
  hover: "HOVER PDF",
  blueprint: "Blueprint",
};
const SOURCE_COLORS = {
  ai_photo: "#7C3AED",
  hover: "#0EA5E9",
  blueprint: "#059669",
};

function getElevationsBySource(est) {
  return (
    est?.hover_measurements?._ai_elevations_by_source
    || est?.measurements?._ai_elevations_by_source
    || {}
  );
}

export function countSources(est) {
  const bySource = getElevationsBySource(est);
  return Object.entries(bySource).filter(
    ([, arr]) => Array.isArray(arr) && arr.length > 0,
  ).length;
}

export default function ElevationCompareModal({ est, open, onClose }) {
  const bySource = useMemo(() => getElevationsBySource(est), [est]);
  const sourceKeys = useMemo(
    () => Object.entries(bySource)
      .filter(([, arr]) => Array.isArray(arr) && arr.length > 0)
      .map(([k]) => k),
    [bySource],
  );
  const canCompare = sourceKeys.length >= 2;
  const [activeTab, setActiveTab] = useState(
    canCompare ? "compare" : (sourceKeys[0] || null),
  );

  // For the Compare view, group elevations by label across sources.
  // Computed unconditionally to satisfy hooks rules.
  const compareGroups = useMemo(() => {
    const labels = new Set();
    sourceKeys.forEach((src) => {
      (bySource[src] || []).forEach((e) => labels.add(e.label));
    });
    return Array.from(labels).map((label) => ({
      label,
      versions: sourceKeys
        .map((src) => ({
          source: src,
          elev: (bySource[src] || []).find((e) => e.label === label),
        }))
        .filter((v) => v.elev),
    })).filter((g) => g.versions.length >= 1);
  }, [bySource, sourceKeys]);

  if (!open) return null;
  if (!sourceKeys.length) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}
      data-testid="elevation-compare-backdrop"
    >
      <div
        className="bg-[var(--surface)] max-w-5xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
        data-testid="elevation-compare-modal"
      >
        <div className="bg-[var(--bar-bg)] text-white px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5" />
            <div>
              <div className="font-heading text-lg">Compare Elevation Drawings</div>
              <div className="text-xs opacity-90 mt-0.5">
                {sourceKeys.length} measurement source{sourceKeys.length > 1 ? "s" : ""} on this estimate · drift between them is highlighted in the Compare tab
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-white/90 hover:text-white"
            data-testid="elevation-compare-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="border-b border-[var(--border)] px-5 flex items-center gap-1">
          {canCompare && (
            <button
              type="button"
              onClick={() => setActiveTab("compare")}
              className={`px-3 py-2 text-[11px] uppercase tracking-wider font-bold border-b-2 ${
                activeTab === "compare"
                  ? "border-[var(--border-strong)] text-[var(--ink)]"
                  : "border-transparent text-[var(--muted)] hover:text-[var(--ink)]"
              }`}
              data-testid="elevation-compare-tab-compare"
            >
              Compare ({compareGroups.length})
            </button>
          )}
          {sourceKeys.map((src) => (
            <button
              key={src}
              type="button"
              onClick={() => setActiveTab(src)}
              className={`px-3 py-2 text-[11px] uppercase tracking-wider font-bold border-b-2 ${
                activeTab === src
                  ? "border-[var(--border-strong)] text-[var(--ink)]"
                  : "border-transparent text-[var(--muted)] hover:text-[var(--ink)]"
              }`}
              style={activeTab === src ? { borderColor: SOURCE_COLORS[src] } : {}}
              data-testid={`elevation-compare-tab-${src}`}
            >
              {SOURCE_LABELS[src] || src} ({(bySource[src] || []).length})
            </button>
          ))}
        </div>
        <div className="overflow-y-auto flex-1 p-5">
          {activeTab === "compare" && canCompare && (
            <div className="space-y-5">
              {compareGroups.map((group) => (
                <div
                  key={group.label}
                  className="border border-[var(--border)]"
                  data-testid={`compare-group-${group.label.toLowerCase()}`}
                >
                  <div className="px-3 py-2 bg-[var(--surface-muted)] border-b border-[var(--border)] flex items-center justify-between">
                    <div className="text-[12px] uppercase tracking-wider font-bold text-[var(--ink)]">
                      {group.label} Elevation
                    </div>
                    {group.versions.length >= 2 && (() => {
                      const widths = group.versions.map((v) => Number(v.elev.facade_width_ft) || 0);
                      const heights = group.versions.map((v) => Number(v.elev.facade_height_ft) || 0);
                      const widthRange = Math.max(...widths) - Math.min(...widths);
                      const heightRange = Math.max(...heights) - Math.min(...heights);
                      const drift = widthRange > 2 || heightRange > 2;
                      return (
                        <div
                          className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 ${
                            drift
                              ? "bg-[#FEF3C7] text-[var(--warning-text)] border border-[#FCD34D]"
                              : "bg-[#DCFCE7] text-[#15803D] border border-[#86EFAC]"
                          }`}
                        >
                          {drift
                            ? `⚠ Drift: ${widthRange.toFixed(0)}'W · ${heightRange.toFixed(0)}'H`
                            : "✓ Sources agree"}
                        </div>
                      );
                    })()}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-2">
                    {group.versions.map((v) => (
                      <div key={v.source} className="border border-[var(--border)]">
                        <div
                          className="px-2 py-1 text-[10px] uppercase tracking-wider font-bold text-white"
                          style={{ background: SOURCE_COLORS[v.source] }}
                        >
                          {SOURCE_LABELS[v.source] || v.source}
                        </div>
                        <ElevationDrawing elevation={v.elev} editable={false} compact />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {compareGroups.length === 0 && (
                <div className="text-center py-12 text-[12px] text-[var(--muted)]">
                  No matching elevation labels across sources.
                </div>
              )}
            </div>
          )}
          {activeTab !== "compare" && sourceKeys.includes(activeTab) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(bySource[activeTab] || []).map((elev) => (
                <ElevationDrawing
                  key={elev.label}
                  elevation={elev}
                  editable={false}
                  compact
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
