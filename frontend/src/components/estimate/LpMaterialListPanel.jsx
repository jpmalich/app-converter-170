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
import { Loader2, Lock, MapPin, Pencil, RefreshCcw, Ruler, ShieldCheck } from "lucide-react";
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
  const [relocating, setRelocating] = useState(null); // amber key picking a wall
  // "Tape the chase" nudge (approved 2026-07-15): offer-only quick entry
  const [tapeVals, setTapeVals] = useState({});
  const [dimsKey, setDimsKey] = useState(0);
  // Compare-profiles (approved 2026-07-16, geometry-source rule): derived
  // per request, never cached — toggling off discards the comparison.
  const [compare, setCompare] = useState(null);
  const [comparing, setComparing] = useState(false);

  const toggleCompare = async () => {
    if (compare) { setCompare(null); return; }
    setComparing(true);
    try {
      const { data } = await api.post(`/estimates/${estId}/lp-package/compare`, {
        alt_profile: "board_batten",
      });
      setCompare(data);
    } catch {
      toast.error("Could not derive the comparison — try again.");
    } finally {
      setComparing(false);
    }
  };

  // Slice 1 — estimate-level default siding profile (LP only). Every wall
  // composes at the default unless a per-region annotation overrides it.
  // Changing it re-derives through the engine on the same named geometry;
  // provenance is event-logged backend-side; applied lines still only
  // change through the normal apply gate.
  const [defaultProfile, setDefaultProfile] = useState(est?.default_siding_profile || null);
  const [profileChange, setProfileChange] = useState(est?.default_siding_profile_change || null);
  const [savingProfile, setSavingProfile] = useState(false);

  // Slice 2 — colors re-validated against the availability matrix for the
  // new profile (matrix INFORMS, never forbids — degraded combos warned,
  // never cleared or blocked).
  const revalidateColors = (matrix, profileLabel) => {
    if (!matrix) return;
    const degraded = [];
    for (const [group, color] of Object.entries(colors || {})) {
      if (!color) continue;
      const cell = matrix[group]?.[color];
      if (cell && cell.status !== "available") {
        degraded.push(`${group}: ${color} → ${cell.status.toUpperCase()}${cell.note ? ` (${cell.note})` : ""}`);
      }
    }
    if (degraded.length) {
      toast.warning(
        `Colors re-validated for ${profileLabel}: ${degraded.join(" · ")} — matrix informs, never forbids.`,
        { duration: 9000 }
      );
    }
  };

  const applyProfile = async (next) => {
    setSavingProfile(true);
    try {
      const { data } = await api.post(`/estimates/${estId}/default-profile`, { profile: next });
      setDefaultProfile(data.to);
      setProfileChange(data.change || null);
      toast.success(data.to
        ? `Default profile → ${data.label} — list re-derived on the same geometry`
        : "Default profile cleared — composition follows the extraction");
      const { data: fresh } = await api.post(`/estimates/${estId}/lp-package/preview`, {
        colors: colors && Object.keys(colors).length ? colors : undefined,
        substitutions: subs && Object.keys(subs).length ? subs : undefined,
      });
      setPkg(fresh);
      revalidateColors(fresh.color_matrix, data.label || "extraction default");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not set default profile");
    } finally {
      setSavingProfile(false);
    }
  };
  const changeDefaultProfile = (val) => applyProfile(val === defaultProfile ? null : val);

  // Field-verify-from-flags (approved 2026-07-17): close/reopen mapping-
  // contract flags; closing batten wall-heights re-derives batten LF live.
  const [flagInput, setFlagInput] = useState({});
  const actFlag = async (code, action, values) => {
    try {
      await api.post(`/estimates/${estId}/flag-checklist`, { code, action, values });
      toast.success(action === "close" ? "Flag closed — basis updated" : "Flag reopened");
      setFlagInput((p) => ({ ...p, [code]: undefined }));
      await fetchPackage(colors, subs);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Checklist update failed");
    }
  };

  const toggleVerify = async (item, status, extra) => {
    try {
      await api.post(`/estimates/${estId}/lp-field-verify`, {
        key: item.key, status, ...(extra || {}),
      });
      setRelocating(null);
      // relocations/removals re-derive stick counts + notes server-side —
      // refetch the whole package instead of patching locally.
      fetchPackage(colors, subs);
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

  // "Tape the chase" nudge groups (approved 2026-07-15): one per amber
  // appendage whose dims are still assumed. Offer only, never a gate —
  // fully-measured appendages show no prompt. Save key mirrors the 3D
  // panel (accent-profile wall); backend derivation is group-scoped.
  const APPENDAGE_MARKERS = ["chase", "chimney", "bump", "cantilever", "appendage"];
  const tapeNudges = useMemo(() => {
    const dims = pkg?.appendage_dims || {};
    const accentWalls = [];
    (run?.result?.raw_ai?.walls || []).forEach((w) => {
      (w.accent_profiles || []).forEach((ap) => {
        const loc = String(ap.location || "").toLowerCase();
        if (APPENDAGE_MARKERS.some((m) => loc.includes(m))) accentWalls.push(String(w.label || "").toLowerCase());
      });
    });
    const groups = {};
    (pkg?.amber_items || []).forEach((it) => {
      if (it.status === "user_removed") return;
      const text = String(it.locator || "").toLowerCase();
      const marker = APPENDAGE_MARKERS.find((m) => text.includes(m));
      if (!marker) return;
      groups[marker] = groups[marker] || { marker, walls: [] };
      (it.walls || []).forEach((w) => {
        const k = String(w).toLowerCase();
        if (!groups[marker].walls.includes(k)) groups[marker].walls.push(k);
      });
    });
    return Object.values(groups).map((g) => {
      const walls = [...new Set([...accentWalls, ...g.walls])];
      const measured = (field) => walls.some((w) => {
        const e = (dims[`appendage:${w}`] || {})[field];
        return e && (e.status === "user_measured" || e.status === "user_confirmed_from_blueprint");
      });
      const fields = ["height_ft", "depth_ft"].filter((f) => !measured(f));
      const saveWall = accentWalls[0] || g.walls[0];
      return fields.length && saveWall ? { marker: g.marker, key: `appendage:${saveWall}`, fields } : null;
    }).filter(Boolean);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pkg, run]);

  const saveTape = async (nudge) => {
    const entries = nudge.fields
      .map((f) => [f, parseFloat(tapeVals[`${nudge.key}.${f}`])])
      .filter(([, v]) => Number.isFinite(v) && v >= 0.5 && v <= 100);
    if (!entries.length) return;
    try {
      for (const [f, v] of entries) {
        await api.post(`/estimates/${estId}/lp-appendage-dims`, { key: nudge.key, field: f, value: v });
      }
      setTapeVals({});
      setDimsKey((k) => k + 1); // 3D panel refetches dims + redraws
      fetchPackage(colors, subs);
    } catch {
      toast.error("Could not save the measurements — try again.");
    }
  };

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
                title={`Composition source: ${pkg.source_label}`}
              >
                source: {pkg.source_label}
              </span>
            )}
            {pkg.summary?.waste_pct_applied != null && (
              <span
                className="ml-1 inline-flex items-center px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-bold border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]"
                data-testid="lp-waste-applied-chip"
                title="Waste the engine actually applied in its formulas — the display always mirrors the application (ruled 2026-07-18)"
              >
                waste: {Math.round(pkg.summary.waste_pct_applied * 100)}% in formulas
              </span>
            )}
          </div>
          {pkg.geometry_basis?.label && (
            <div
              className={`text-[10px] mt-0.5 font-mono-num ${pkg.geometry_basis.pinned ? "text-[var(--muted)]" : "text-[#92400E]"}`}
              data-testid="lp-geometry-basis"
              title="Geometry-source naming: every derivation states the geometry it stands on"
            >
              geometry: {pkg.geometry_basis.label}
              {/* Elevation Sheets entry point (Howard-approved placement, 2026-07-18) */}
              <a
                href={`/estimate/${est.id}/elevation-sheet/front`}
                className="ml-2 inline-flex items-center px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-bold border border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] underline"
                data-testid="lp-elevation-sheets-link"
                title="Dimensioned 2D elevation sheet — source-tagged verification (front, EL-1)"
              >
                Elevation Sheets →
              </a>
            </div>
          )}
          <div className="flex items-center gap-1.5 mt-1.5" data-testid="lp-default-profile-picker">
            <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--muted)]">
              Default profile:
            </span>
            {[["lap", "Lap"], ["board_batten", "B&B"], ["shake", "Shake"], ["nickel_gap", "Nickel Gap"]].map(([val, lbl]) => (
              <button
                key={val}
                type="button"
                disabled={savingProfile}
                className={`px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider border disabled:opacity-50 ${
                  defaultProfile === val
                    ? "bg-[var(--bar-bg)] text-white border-transparent"
                    : "bg-[var(--surface)] text-[var(--muted)] border-[var(--border)]"
                }`}
                onClick={() => changeDefaultProfile(val)}
                data-testid={`lp-default-profile-${val}`}
                title={defaultProfile === val ? "Click again to clear — composition follows the extraction" : `Compose every unannotated wall as ${lbl}`}
              >
                {lbl}
              </button>
            ))}
          </div>
          {profileChange && profileChange.to !== profileChange.from && (
            <div className="text-[9px] text-[var(--muted)] mt-1 font-mono-num" data-testid="lp-profile-provenance">
              {(profileChange.from || "extraction default")} → {(profileChange.to || "extraction default")}
              {" · "}{profileChange.by}{" · "}{String(profileChange.at || "").slice(0, 16).replace("T", " ")}
              <button
                type="button"
                className="ml-2 underline text-[#92400E] font-bold uppercase tracking-wider"
                onClick={() => applyProfile(profileChange.from || null)}
                disabled={savingProfile}
                data-testid="lp-profile-revert"
              >
                Revert
              </button>
            </div>
          )}
          {(pkg.hover_mapping_flags || []).length > 0 && (
            <div className="mt-1.5 space-y-1" data-testid="lp-hover-mapping-flags">
              {pkg.hover_mapping_flags.map((f, i) => {
                const code = f.code || `flag-${i}`;
                const label = f.label || String(f);
                const closed = f.status === "closed";
                return (
                  <div key={code} className="text-[9px] leading-snug" data-testid={`lp-flag-${code}`}>
                    {closed ? (
                      <span className="text-[var(--muted)] line-through">⚑ {label}</span>
                    ) : (
                      <span className="text-[#92400E]">⚑ {label}</span>
                    )}
                    {closed ? (
                      <span className="ml-1 text-[var(--muted)] no-underline">
                        closed · {f.closed_by} ·
                        <button type="button" className="ml-1 underline" onClick={() => actFlag(code, "reopen")} data-testid={`lp-flag-${code}-reopen`}>
                          reopen
                        </button>
                      </span>
                    ) : code === "batten_wall_heights" ? (
                      flagInput[code] !== undefined ? (
                        <span className="ml-1 inline-flex items-center gap-1">
                          <input
                            className="border border-[var(--border)] px-1 py-0.5 w-40 text-[9px] font-mono-num"
                            placeholder="wall heights ft, e.g. 9, 9, 18.5, 9"
                            value={flagInput[code]}
                            onChange={(e) => setFlagInput((p) => ({ ...p, [code]: e.target.value }))}
                            data-testid={`lp-flag-${code}-input`}
                          />
                          <button
                            type="button"
                            className="underline font-bold uppercase"
                            onClick={() => {
                              const hs = String(flagInput[code] || "").split(/[,\s]+/).map(Number).filter((n) => n > 0);
                              if (!hs.length) { toast.error("Enter taped wall heights in feet"); return; }
                              actFlag(code, "close", { wall_heights_ft: hs });
                            }}
                            data-testid={`lp-flag-${code}-save`}
                          >
                            Save
                          </button>
                        </span>
                      ) : (
                        <button type="button" className="ml-1 underline font-bold uppercase" onClick={() => setFlagInput((p) => ({ ...p, [code]: "" }))} data-testid={`lp-flag-${code}-verify`}>
                          Field-verify
                        </button>
                      )
                    ) : (
                      <button type="button" className="ml-1 underline font-bold uppercase" onClick={() => actFlag(code, "close", { confirmed: true })} data-testid={`lp-flag-${code}-verify`}>
                        Mark verified
                      </button>
                    )}
                    {!closed && f.verify && (
                      <div className="text-[8px] text-[var(--muted)] ml-3">{f.verify}</div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {refreshing && <Loader2 className="w-4 h-4 animate-spin text-[var(--muted)]" />}
          <button
            type="button"
            className={`px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider inline-flex items-center gap-1 border ${
              compare
                ? "bg-[var(--bar-bg)] text-white border-transparent"
                : "bg-[var(--surface)] text-[var(--ink-2)] border-[var(--border)]"
            }`}
            onClick={toggleCompare}
            disabled={comparing}
            data-testid="lp-compare-toggle"
          >
            {comparing ? "…" : compare ? "Hide compare" : "Compare Lap vs B&B"}
          </button>
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

      {compare && <CompareProfilesCard compare={compare} />}

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

      {/* dimension cross-check flags — disagreement flagged, never averaged */}
      {(pkg.appendage_dim_flags || []).length > 0 && (
        <div className="border-t border-[var(--border)] px-4 py-3 bg-[#FFFBEB]" data-testid="lp-dim-flags-card">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#92400E] mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> Dimension cross-check
          </div>
          {pkg.appendage_dim_flags.map((f, i) => (
            <div key={i} className="text-[11px] text-[#92400E]" data-testid={`lp-dim-flag-${i}`}>{f}</div>
          ))}
        </div>
      )}

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
                  <span className={it.status === "user_removed" ? "line-through opacity-60" : ""}>{it.locator}</span>
                  {it.status === "user_relocated" && it.relocated_to && (
                    <span className="text-[10px] font-bold text-sky-700" data-testid={`lp-fv-reloc-badge-${it.key}`}>
                      → {it.relocated_to} {t("lp.fv.wall")}
                    </span>
                  )}
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
                ) : it.status === "user_relocated" ? (
                  <button
                    type="button"
                    onClick={() => toggleVerify(it, "unverified")}
                    className="text-[10px] font-bold uppercase tracking-wider text-sky-700"
                    data-testid={`lp-fv-relocated-${it.key}`}
                    title={`${it.verified_by || ""} ${it.verified_at ? new Date(it.verified_at).toLocaleDateString() : ""}`}
                  >
                    ⇄ {t("lp.fv.relocated")}
                  </button>
                ) : it.status === "user_removed" ? (
                  <button
                    type="button"
                    onClick={() => toggleVerify(it, "unverified")}
                    className="text-[10px] font-bold uppercase tracking-wider text-red-700"
                    data-testid={`lp-fv-removed-${it.key}`}
                    title={`${it.verified_by || ""} ${it.verified_at ? new Date(it.verified_at).toLocaleDateString() : ""}`}
                  >
                    ✕ {t("lp.fv.removed")}
                  </button>
                ) : relocating === it.key ? (
                  <select
                    className="input text-[10px] py-0.5"
                    defaultValue=""
                    onChange={(e) => e.target.value
                      ? toggleVerify(it, "relocated", { to_wall: e.target.value, from_walls: it.walls })
                      : setRelocating(null)}
                    data-testid={`lp-fv-wall-select-${it.key}`}
                  >
                    <option value="">{t("lp.fv.pickWall")}</option>
                    {["front", "back", "left", "right"]
                      .filter((w) => !(it.walls || []).includes(w))
                      .map((w) => <option key={w} value={w}>{w}</option>)}
                  </select>
                ) : (
                  <span className="flex gap-1.5">
                    <button
                      type="button"
                      onClick={() => toggleVerify(it, "verified")}
                      className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider bg-[#B45309] text-white"
                      data-testid={`lp-fv-verify-${it.key}`}
                    >
                      {t("lp.fv.verify")}
                    </button>
                    <button
                      type="button"
                      onClick={() => setRelocating(it.key)}
                      className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider border border-sky-700 text-sky-800"
                      data-testid={`lp-fv-relocate-${it.key}`}
                    >
                      {t("lp.fv.wrongWall")}
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleVerify(it, "removed")}
                      className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider border border-red-700 text-red-700"
                      data-testid={`lp-fv-remove-${it.key}`}
                    >
                      {t("lp.fv.notPresent")}
                    </button>
                  </span>
                )}
              </div>
            ))}
          </div>
          {/* "Tape the chase" quick entry — offer only, never a gate */}
          {tapeNudges.map((n) => (
            <div key={n.key} className="mt-3 pt-2 border-t border-[#FDE68A]" data-testid={`lp-tape-nudge-${n.marker}`}>
              <div className="text-[11px] font-bold text-[#92400E] flex items-center gap-1.5">
                <Ruler className="w-3 h-3" /> {t("lp.fv.tape.title")} — {n.marker}
              </div>
              <div className="text-[10px] text-[#92400E] mt-0.5 mb-1.5">{t("lp.fv.tape.note")}</div>
              <div className="flex flex-wrap items-center gap-3">
                {n.fields.map((f) => (
                  <label key={f} className="flex items-center gap-1.5 text-[11px] text-[var(--ink)]">
                    {t(f === "height_ft" ? "lp.fv.tape.height" : "lp.fv.tape.depth")}
                    <input
                      type="number" step="0.1" min="0.5" max="100"
                      className="input w-20 text-xs py-0.5 px-1.5"
                      value={tapeVals[`${n.key}.${f}`] || ""}
                      onChange={(e) => setTapeVals((v) => ({ ...v, [`${n.key}.${f}`]: e.target.value }))}
                      data-testid={`lp-tape-${f === "height_ft" ? "height" : "depth"}-${n.marker}`}
                    />
                    {t("lp.fv.tape.ft")}
                  </label>
                ))}
                <button
                  type="button"
                  onClick={() => saveTape(n)}
                  disabled={!n.fields.some((f) => parseFloat(tapeVals[`${n.key}.${f}`]) >= 0.5)}
                  className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider bg-sky-700 text-white disabled:opacity-40"
                  data-testid={`lp-tape-save-${n.marker}`}
                >
                  {t("lp.fv.tape.save")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 3D — mesh-group flat repaints */}
      {preview3d && (
        <div className="border-t border-[var(--border)] p-3" data-testid="lp-material-3d">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)] mb-1 flex items-center gap-2">
            <RefreshCcw className="w-3 h-3" /> 3D Model — colors repaint live
          </div>
          {pkg.geometry_basis?.label && (
            <div className="text-[10px] mb-2 font-mono-num text-[var(--muted)]" data-testid="lp-3d-geometry-basis">
              geometry: {pkg.geometry_basis.label}
            </div>
          )}
          <HouseModel3D
            preview={preview3d}
            estimate={est}
            runId={run.run_id}
            lpGroupColors={lpGroupColors}
            onDimsSaved={() => fetchPackage(colors, subs)}
            dimsRefreshKey={dimsKey}
          />
        </div>
      )}
    </div>
  );
}


// Compare-profiles card (approved 2026-07-16): Lap vs Board & Batten
// side-by-side — SAME named geometry, same engine, derived per request.
function CompareProfilesCard({ compare }) {
  const cur = compare.current || {};
  const alt = compare.alternative || {};
  const altLabel = compare.alt_profile === "board_batten" ? "Board & Batten" : "Lap";
  const total = (p) => p?.summary?.pricing?.total_sell || 0;
  const byName = (p) =>
    Object.fromEntries((p.lines || []).filter((l) => (l.qty || 0) > 0).map((l) => [l.name, l]));
  const curMap = byName(cur);
  const altMap = byName(alt);
  const names = Array.from(new Set([...Object.keys(curMap), ...Object.keys(altMap)]));
  const changed = names.filter((n) => {
    const a = curMap[n];
    const b = altMap[n];
    return (a?.qty || 0) !== (b?.qty || 0) || (a?.line_sell || 0) !== (b?.line_sell || 0);
  });
  const sameCount = names.length - changed.length;
  const cell = (l) =>
    l ? (
      <>
        <span className="font-mono-num">{l.qty} {l.unit}</span>
        <span className="font-mono-num text-[var(--muted)] ml-2">
          {l.pricing_status === "priced" ? fmt(l.line_sell) : "pending"}
        </span>
      </>
    ) : (
      <span className="text-[var(--muted)]">—</span>
    );
  return (
    <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--surface-muted)]" data-testid="lp-compare-card">
      <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)]">
        Compare profiles — same geometry, same engine
      </div>
      {compare.geometry_basis?.label && (
        <div className="text-[10px] font-mono-num text-[var(--muted)] mt-0.5" data-testid="lp-compare-basis">
          geometry: {compare.geometry_basis.label}
        </div>
      )}
      <table className="w-full text-xs mt-2">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold">
            <th className="text-left py-1 w-[44%]">Line</th>
            <th className="text-left py-1">Current — Lap</th>
            <th className="text-left py-1">{altLabel}</th>
          </tr>
        </thead>
        <tbody>
          {changed.map((n) => (
            <tr key={n} className="border-t border-[var(--border)]" data-testid={`lp-compare-line-${n}`}>
              <td className="py-1.5 pr-2 text-[var(--ink)]">{n}</td>
              <td className="py-1.5">{cell(curMap[n])}</td>
              <td className="py-1.5">{cell(altMap[n])}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-[var(--ink)]">
            <td className="py-1.5 font-bold text-[var(--ink)]">
              Materials total
              {sameCount > 0 && (
                <span className="font-normal text-[10px] text-[var(--muted)] ml-2">
                  ({sameCount} shared line{sameCount === 1 ? "" : "s"} identical in both)
                </span>
              )}
            </td>
            <td className="py-1.5 font-mono-num font-bold" data-testid="lp-compare-current-total">{fmt(total(cur))}</td>
            <td className="py-1.5 font-mono-num font-bold" data-testid="lp-compare-alt-total">
              {fmt(total(alt))}
              <span className={`ml-2 text-[10px] font-bold ${total(alt) - total(cur) >= 0 ? "text-[#92400E]" : "text-emerald-700"}`}>
                {total(alt) - total(cur) >= 0 ? "+" : "−"}{fmt(Math.abs(total(alt) - total(cur)))}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <div className="text-[10px] text-[var(--muted)] mt-1.5">
        Comparison view only — nothing is saved or applied. Pending lines are excluded from both totals.
      </div>
    </div>
  );
}

