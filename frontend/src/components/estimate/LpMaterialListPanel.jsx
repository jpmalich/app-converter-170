// Iter 98 — Phase 2 priority surface: the LP Material List tab.
// Renders the LP-native package derived from the latest completed AI
// Measure run (POST /estimates/{id}/lp-package/preview — ALWAYS the
// redacted contractor view: sell prices only, cost never present).
//
// Doctrine on this surface:
//   • READ-ONLY until explicitly edited ("Edit list" unlock) — the
//     color selector is a selector, not a list edit, and stays active.
//   • Substitutions are table-limited (backend `substitutable_with`),
//     re-derived server-side, provenance-carried, session-only (never
//     remembered across reloads — ruled).
//   • Component-group colors (ExpertFinish) with apply-to-all shortcut;
//     persisted on the estimate (lp_colors) and flat-repainting the 3D
//     mesh groups (siding → walls, opening_trim → trim; corner/fascia
//     meshes pending — flagged, not faked).
//   • Lines without a cost basis render "pricing pending", never $0.
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Lock, MapPin, Pencil, RefreshCcw, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import api, { fmt } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { lpHex, LP_GROUP_LABELS } from "@/lib/lpColors";
import HouseModel3D from "@/components/estimate/HouseModel3D";
import { OpeningsReviewCard } from "@/components/estimate/OpeningsReviewCard";

function Swatch({ name }) {
  const hex = lpHex(name);
  if (!hex) return null;
  return (
    <span
      className="inline-block w-3 h-3 border border-[var(--border)] align-middle"
      style={{ backgroundColor: hex }}
      title={name}
    />
  );
}

function ColorSelect({ value, onChange, colors, disabled, testId, matrix }) {
  // Approved constraint: badged combos remain SELECTABLE — the matrix
  // informs, never forbids (dealer-verified: available = orderable).
  const badge = (c) => {
    const m = matrix?.[c];
    if (!m || m.status === "available") return "";
    return m.status === "unsupported" ? " ⛔" : " ⚑";
  };
  const sel = matrix?.[value];
  return (
    <span className="inline-flex flex-col">
      <select
        className="input text-xs py-1 max-w-[190px]"
        value={value || ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={disabled}
        data-testid={testId}
      >
        <option value="">—</option>
        {colors.map((c) => (
          <option key={c} value={c}>{c}{badge(c)}</option>
        ))}
      </select>
      {value && sel && sel.status !== "available" && (
        <span
          className={`text-[10px] font-semibold max-w-[190px] ${sel.status === "unsupported" ? "text-red-700" : "text-[#B45309]"}`}
          data-testid={`${testId}-warning`}
        >
          {sel.status === "unsupported" ? "⛔ not available in this color (dealer-verified)" : "⚑ availability caveat — verify with dealer"}
          {sel.flagged_items > 0 && sel.item_count > 1 ? ` (${sel.flagged_items}/${sel.item_count} items)` : ""}
        </span>
      )}
    </span>
  );
}

export default function LpMaterialListPanel({ est, update, onPackage }) {
  const t = useT();
  const estId = est?.id;
  const [pkg, setPkg] = useState(null);
  const [run, setRun] = useState(null);
  const [palette, setPalette] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editMode, setEditMode] = useState(false);
  // session-only (ruled: substitutions are never remembered)
  const [subs, setSubs] = useState({});
  const [colors, setColors] = useState(() => est?.lp_colors || {});
  const [noRun, setNoRun] = useState(false);

  const toggleVerify = async (item, status) => {
    try {
      const { data } = await api.post(`/estimates/${estId}/lp-field-verify`, {
        key: item.key, status,
      });
      setPkg((p) => (p ? {
        ...p,
        amber_items: (p.amber_items || []).map((a) =>
          a.key === item.key
            ? { ...a, status, verified_at: data.at || null, verified_by: data.by || null }
            : a),
      } : p));
    } catch {
      toast.error("Could not save field verification — try again.");
    }
  };

  // Iter 99 one-surface rule: expose the live package upstream so the
  // MATERIAL LIST button prints the exact same composition (colors +
  // session substitutions) — never the legacy stored-lines view.
  useEffect(() => { onPackage?.(pkg); /* eslint-disable-next-line */ }, [pkg]);

  const fetchPackage = useCallback(async (nextColors, nextSubs) => {
    setRefreshing(true);
    try {
      const { data } = await api.post(`/estimates/${estId}/lp-package/preview`, {
        colors: nextColors && Object.keys(nextColors).length ? nextColors : undefined,
        substitutions: nextSubs && Object.keys(nextSubs).length ? nextSubs : undefined,
      });
      setPkg(data);
      setNoRun(false);
    } catch (e) {
      if (e?.response?.status === 404) setNoRun(true);
    } finally {
      setRefreshing(false);
    }
  }, [estId]);

  useEffect(() => {
    if (!estId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [pal, latest] = await Promise.all([
          api.get(`/lp-package/colors`),
          api.get(`/measure/ai-measure/latest-for-estimate/${estId}`).catch(() => null),
        ]);
        if (cancelled) return;
        setPalette(pal.data);
        let r = latest?.data?.run;
        // paired LP estimates: the AI run lives on the siding source
        const pairedId = est?.paired_lp_estimate_id || est?.paired_estimate_id;
        if (!(r?.status === "done" && r?.result?.raw_ai) && pairedId) {
          const pairedLatest = await api
            .get(`/measure/ai-measure/latest-for-estimate/${pairedId}`)
            .catch(() => null);
          r = pairedLatest?.data?.run;
        }
        if (r?.status === "done" && r?.result?.raw_ai) setRun(r);
        await fetchPackage(est?.lp_colors || {}, {});
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estId]);

  const groupColors = pkg?.summary?.group_colors || {};
  const groups = palette?.groups || [];
  const allColors = palette?.colors || [];

  const setGroupColor = (group, name) => {
    let next;
    if (group === "all") {
      next = name ? { all: name } : {};
    } else {
      next = { ...colors };
      delete next.all;
      // keep other groups at their resolved values so dropping "all"
      // doesn't silently clear them
      groups.forEach((g) => {
        if (next[g] === undefined && groupColors[g]) next[g] = groupColors[g];
      });
      if (name) next[group] = name; else delete next[group];
    }
    setColors(next);
    update({ lp_colors: next }); // persisted on the estimate (autosave)
    fetchPackage(next, subs);
  };

  const substitute = (line, newName) => {
    const key = line.substituted_from || line.name;
    const next = { ...subs };
    if (!newName || newName === key) delete next[key];
    else next[key] = newName;
    setSubs(next);
    fetchPackage(colors, next);
  };

  // 3D repaint colors (hex approximations)
  const lpGroupColors = useMemo(() => ({
    siding: lpHex(groupColors.siding),
    opening_trim: lpHex(groupColors.opening_trim),
  }), [groupColors.siding, groupColors.opening_trim]);

  const preview3d = useMemo(
    () => (run ? { ...run.result, run_id: run.run_id } : null),
    [run]
  );

  const bySection = useMemo(() => {
    const acc = {};
    (pkg?.lines || []).forEach((l) => {
      (acc[l.section] = acc[l.section] || []).push(l);
    });
    return acc;
  }, [pkg]);

  if (loading) {
    return (
      <div className="card p-6 mb-4 flex items-center gap-2 text-sm text-[var(--ink-2)]" data-testid="lp-material-list-loading">
        <Loader2 className="w-4 h-4 animate-spin" /> {t("lp.mat.title")}…
      </div>
    );
  }
  if (noRun || !pkg) {
    return (
      <div className="card p-6 mb-4" data-testid="lp-material-list-norun">
        <div className="section-tag mb-2">{t("lp.mat.title")}</div>
        <p className="text-sm text-[var(--ink-2)]">{t("lp.mat.noRun")}</p>
      </div>
    );
  }

  const pricing = pkg.summary?.pricing || {};
  const subErrors = pkg.summary?.substitution_errors || [];
  const colorErrors = pkg.summary?.color_errors || [];

  return (
    <div className="card p-0 mb-4 overflow-hidden" data-testid="lp-material-list-panel">
      {/* header */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 bg-[var(--surface-muted)] border-b border-[var(--border)]">
        <div>
          <div className="section-tag">{t("lp.mat.title")}</div>
          <div className="text-[11px] text-[var(--muted)] font-mono-num">
            run {String(pkg.run_id || "").slice(0, 8)} · {pkg.summary?.line_count} lines
            {pkg.source_label && (
              <span
                className="ml-2 inline-flex items-center px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-bold border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]"
                data-testid="lp-source-chip"
                title={`Composition derived from: ${pkg.source_label}`}
              >
                derived from: {pkg.source_label}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {refreshing && <Loader2 className="w-4 h-4 animate-spin text-[var(--muted)]" />}
          <button
            type="button"
            className={`px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider inline-flex items-center gap-1 border ${
              editMode
                ? "bg-[var(--bar-bg)] text-white border-transparent"
                : "bg-[var(--surface)] text-[var(--ink-2)] border-[var(--border)]"
            }`}
            onClick={() => setEditMode((v) => !v)}
            data-testid="lp-material-list-edit-toggle"
          >
            {editMode ? <Pencil className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
            {editMode ? t("lp.mat.lock") : t("lp.mat.edit")}
          </button>
        </div>
      </div>

      {/* color selector */}
      <div className="px-4 py-3 border-b border-[var(--border)]">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)] mb-2">
          {t("lp.mat.colors")} — ExpertFinish
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <label className="flex items-center gap-1.5 text-xs">
            <span className="font-bold">{t("lp.mat.allComponents")}:</span>
            <Swatch name={colors.all} />
            <ColorSelect
              value={colors.all}
              onChange={(v) => setGroupColor("all", v)}
              colors={allColors}
              testId="lp-color-all"
              matrix={pkg.color_matrix?.all}
            />
          </label>
          {groups.map((g) => (
            <label key={g} className="flex items-center gap-1.5 text-xs">
              <span>{LP_GROUP_LABELS[g] || g}:</span>
              <Swatch name={groupColors[g]} />
              <ColorSelect
                value={colors.all ? groupColors[g] : (colors[g] ?? groupColors[g])}
                onChange={(v) => setGroupColor(g, v)}
                colors={allColors}
                testId={`lp-color-${g}`}
                matrix={pkg.color_matrix?.[g]}
              />
            </label>
          ))}
        </div>
        {colorErrors.length > 0 && (
          <div className="text-[11px] text-[#B45309] mt-2" data-testid="lp-color-errors">
            {colorErrors.join(" · ")}
          </div>
        )}
      </div>

      {/* confirm openings — pre-derivation ratification (skippable) */}
      <OpeningsReviewCard
        review={pkg.openings_review}
        estId={estId}
        onChanged={() => fetchPackage(colors, subs)}
        t={t}
      />

      {/* read-only hint */}
      {!editMode && (
        <div className="px-4 py-2 text-[11px] text-[var(--muted)] border-b border-[var(--border)]" data-testid="lp-material-list-readonly-hint">
          <Lock className="w-3 h-3 inline mr-1 align-[-1px]" />{t("lp.mat.readonly")}
        </div>
      )}
      {subErrors.length > 0 && (
        <div className="px-4 py-2 text-[11px] text-[#B91C1C] border-b border-[var(--border)]" data-testid="lp-sub-errors">
          {subErrors.join(" · ")}
        </div>
      )}

      {/* lines */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-[var(--muted)] border-b border-[var(--border)]">
              <th className="text-left px-4 py-2">Item</th>
              <th className="text-right px-2 py-2">Qty</th>
              <th className="text-left px-2 py-2">Unit</th>
              <th className="text-left px-2 py-2">Color</th>
              <th className="text-right px-2 py-2">Unit $</th>
              <th className="text-right px-4 py-2">Line $</th>
            </tr>
          </thead>
          {Object.entries(bySection).map(([section, lines]) => (
            <tbody key={section}>
              <tr className="bg-[var(--surface-muted)]">
                <td colSpan={6} className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--ink-2)]">
                  {section}
                </td>
              </tr>
              {lines.map((l) => {
                const key = `${l.name}::${l.color || ""}`;
                const canSub = editMode && (l.substitutable_with || []).length > 0;
                return (
                  <tr key={key} className="border-b border-[var(--border)] last:border-0 align-top" data-testid={`lp-line-${l.name}`}>
                    <td className="px-4 py-2">
                      <div className="font-medium">{l.name}</div>
                      {l.substituted_from && (
                        <div className="text-[10px] text-[#7C3AED]" data-testid={`lp-line-substituted-${l.name}`}>
                          {t("lp.mat.substituted")} {l.substituted_from} — re-derived
                        </div>
                      )}
                      {(l.color_flags || []).map((f, fi) => (
                        <div
                          key={fi}
                          className={`text-[10px] font-semibold ${l.color_status === "unsupported" ? "text-red-700" : "text-[#B45309]"}`}
                          data-testid={`lp-line-color-flag-${l.name}`}
                        >
                          ⚑ {f}
                        </div>
                      ))}
                      {l.note && (
                        <details className="text-[10px] text-[var(--muted)] mt-0.5">
                          <summary className="cursor-pointer select-none">{t("lp.mat.provenance")}</summary>
                          <div className="mt-1 max-w-xl whitespace-pre-wrap">{l.note}</div>
                        </details>
                      )}
                      {canSub && (
                        <select
                          className="input text-xs py-1 mt-1"
                          value=""
                          onChange={(e) => e.target.value && substitute(l, e.target.value)}
                          data-testid={`lp-line-substitute-${l.name}`}
                        >
                          <option value="">Substitute with…</option>
                          {l.substitutable_with.map((o) => (
                            <option key={o} value={o}>{o}</option>
                          ))}
                          {l.substituted_from && (
                            <option value={l.substituted_from}>{`↩ revert to ${l.substituted_from}`}</option>
                          )}
                        </select>
                      )}
                    </td>
                    <td className="px-2 py-2 text-right font-mono-num">{l.qty}</td>
                    <td className="px-2 py-2">{l.unit}</td>
                    <td className="px-2 py-2">
                      {l.color ? (
                        <span className="inline-flex items-center gap-1 text-xs">
                          <Swatch name={l.color} /> {l.color}
                        </span>
                      ) : (
                        <span className="text-[var(--muted)] text-xs">—</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-right font-mono-num">
                      {l.pricing_status === "priced" ? (
                        l.priced_unit && l.pieces_added ? (
                          <span className="inline-flex flex-col items-end leading-tight" data-testid={`lp-line-board-pricing-${l.name}`}>
                            <span>{fmt(l.unit_sell)}<span className="text-[9px] text-[var(--muted)]"> /board</span></span>
                            <span className="text-[9px] text-[var(--muted)]">× {l.pieces_added} whole board{l.pieces_added === 1 ? "" : "s"}</span>
                          </span>
                        ) : (
                          fmt(l.unit_sell)
                        )
                      ) : (
                        <span className="text-[10px] uppercase tracking-wider text-[#B45309] font-bold" data-testid={`lp-line-pending-${l.name}`}>
                          {t("lp.mat.pending")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right font-mono-num">
                      {l.pricing_status === "priced" ? fmt(l.line_sell) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          ))}
        </table>
      </div>

      {/* totals */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 bg-[var(--surface-muted)] border-t border-[var(--border)]">
        <div className="text-[11px] text-[var(--muted)]">
          {pricing.pending_lines > 0 && (
            <span data-testid="lp-pending-count">{pricing.pending_lines} line(s) {t("lp.mat.pending")}</span>
          )}
        </div>
        <div className="text-sm font-bold" data-testid="lp-material-total">
          {t("lp.mat.total")}: <span className="font-mono-num">{fmt(pricing.total_sell || 0)}</span>
        </div>
      </div>

      {/* amber field-verify checklist — presence-guarantee ratification */}
      {(pkg.amber_items || []).length > 0 && (
        <div className="border-t border-[var(--border)] px-4 py-3 bg-[#FFFBEB]" data-testid="lp-field-verify-card">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#92400E] mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> {t("lp.fv.title")}
          </div>
          <div className="text-[11px] text-[#92400E] mb-2">{t("lp.fv.note")}</div>
          <div className="space-y-1.5">
            {pkg.amber_items.map((it) => (
              <div key={it.key} className="flex flex-wrap items-center justify-between gap-2 text-xs" data-testid={`lp-fv-item-${it.key}`}>
                <div className="flex items-center gap-1.5 text-[var(--ink)]">
                  <MapPin className="w-3 h-3 text-[#B45309]" />
                  <span className="font-mono text-[10px] uppercase text-[#B45309]">{it.kind}</span>
                  <span>{it.locator}</span>
                </div>
                {it.status === "verified" ? (
                  <button
                    type="button"
                    onClick={() => toggleVerify(it, "unverified")}
                    className="text-[10px] font-bold uppercase tracking-wider text-emerald-700"
                    data-testid={`lp-fv-verified-${it.key}`}
                    title={`${it.verified_by || ""} ${it.verified_at ? new Date(it.verified_at).toLocaleDateString() : ""}`}
                  >
                    ✓ {t("lp.fv.verified")}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => toggleVerify(it, "verified")}
                    className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider bg-[#B45309] text-white"
                    data-testid={`lp-fv-verify-${it.key}`}
                  >
                    {t("lp.fv.verify")}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3D — mesh-group flat repaints */}
      {preview3d && (
        <div className="border-t border-[var(--border)] p-3" data-testid="lp-material-3d">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)] mb-2 flex items-center gap-2">
            <RefreshCcw className="w-3 h-3" /> 3D — colors repaint live (siding + opening trim mesh groups; corner/fascia meshes pending)
          </div>
          <HouseModel3D preview={preview3d} estimate={est} runId={run.run_id} lpGroupColors={lpGroupColors} />
        </div>
      )}
    </div>
  );
}
