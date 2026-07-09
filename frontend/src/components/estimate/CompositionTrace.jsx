// Iter 79j.75 — "Where every ft² comes from" composition trace. The
// shake-audit turned into a permanent self-service tool: every square
// foot in every profile family traced to exactly one owned surface,
// one owner each. Recomputed live from per_elevation so it stays true
// through chip swaps and added accents (the run-time trace on
// measurements only covers the original AI output).
import React, { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle, ListTree } from "lucide-react";

const OWNER_LABELS = {
  geometry: "AI geometry",
  "user-profile": "AI geometry · your profile",
  annotation: "your annotation box",
  manual: "manual accent",
  "ai-accent": "AI accent",
};

export default function CompositionTrace({ perElevation, conflicts, sidingFamilies, profileLabels }) {
  const [open, setOpen] = useState(false);

  const { families, duplicates } = useMemo(() => {
    const rows = [];
    for (const e of perElevation || []) {
      const label = e.label || "unknown";
      const push = (family, sqft, surface, owner) => {
        const fam = family || "";
        const sq = Number(sqft) || 0;
        if (!fam || sq <= 0 || !sidingFamilies.has(fam)) return;
        rows.push({ family: fam, sqft: sq, elevation: label, surface, owner });
      };
      push(e.wall_body_profile, e.wall_body_sqft, "body", "geometry");
      push(e.gable_profile, e.gable_sqft, "gable",
        String(e.gable_callout || "").startsWith("user:") ? "user-profile" : "geometry");
      push(e.dormer_profile, e.dormer_sqft, "dormer",
        String(e.dormer_callout || "").startsWith("user:") ? "user-profile" : "geometry");
      for (const a of e.accents || []) {
        const owner = a._source === "annotation"
          ? "annotation"
          : a.callout === "manual override" ? "manual" : "ai-accent";
        push(a.profile, a.sqft, `accent: ${a.location || "accent"}`, owner);
      }
    }
    const fams = {};
    const seen = new Set();
    const dups = [];
    for (const r of rows) {
      (fams[r.family] = fams[r.family] || []).push(r);
      // accents may legitimately repeat locations; body/gable/dormer must not
      if (!r.surface.startsWith("accent:")) {
        const key = `${r.elevation}|${r.surface}`;
        if (seen.has(key)) dups.push(key);
        seen.add(key);
      }
    }
    return { families: fams, duplicates: dups };
  }, [perElevation, sidingFamilies]);

  const familyEntries = Object.entries(families);
  if (!familyEntries.length) return null;
  const conflictList = Array.isArray(conflicts) ? conflicts : [];

  return (
    <div className="mb-3 border border-[var(--border)] bg-[var(--surface-2,#FAFAFA)]" data-testid="composition-trace">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
        data-testid="composition-trace-toggle"
      >
        <span className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold text-[var(--ink)]">
          <ListTree className="w-3.5 h-3.5 text-[var(--ai)]" />
          Where every ft² comes from
          {(conflictList.length > 0 || duplicates.length > 0) && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 text-[9px] bg-amber-100 text-amber-700 border border-amber-300">
              <AlertTriangle className="w-3 h-3" />
              {conflictList.length + duplicates.length} conflict{conflictList.length + duplicates.length === 1 ? "" : "s"}
            </span>
          )}
        </span>
        <span className="flex items-center gap-2">
          <span className="text-[9px] text-[var(--muted)] normal-case hidden md:inline">
            Each surface once, one owner each
          </span>
          {open ? <ChevronDown className="w-3.5 h-3.5 text-[var(--muted)]" /> : <ChevronRight className="w-3.5 h-3.5 text-[var(--muted)]" />}
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-3">
          {conflictList.map((c, i) => (
            <div
              key={`c${i}`}
              className="flex items-start gap-2 text-[10px] text-amber-700 bg-amber-50 border border-amber-300 px-2 py-1.5"
              data-testid={`composition-conflict-${i}`}
            >
              <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
              <span>
                <b className="uppercase">{profileLabels[c.family] || c.family}</b>: {c.reason} —
                this family's quote line is amber-flagged (qty 0) until verified.
              </span>
            </div>
          ))}
          {duplicates.map((d, i) => (
            <div
              key={`d${i}`}
              className="flex items-start gap-2 text-[10px] text-amber-700 bg-amber-50 border border-amber-300 px-2 py-1.5"
              data-testid={`composition-duplicate-${i}`}
            >
              <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
              <span>Surface <b>{d.replace("|", " · ")}</b> appears twice — two owners for one surface.</span>
            </div>
          ))}
          {familyEntries.map(([fam, surfaces]) => {
            const total = surfaces.reduce((a, s) => a + s.sqft, 0);
            return (
              <div key={fam} data-testid={`composition-family-${fam}`}>
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-[var(--ink)]">
                    {profileLabels[fam] || fam}
                  </span>
                  <span className="text-[10px] font-mono-num font-bold text-[var(--ai)]">
                    {Math.round(total * 10) / 10} ft²
                  </span>
                  <span className="text-[9px] text-[var(--muted)]">
                    = {surfaces.length} surface{surfaces.length === 1 ? "" : "s"}, each counted once
                  </span>
                </div>
                <table className="w-full text-[10px]">
                  <tbody>
                    {surfaces.map((s, i) => (
                      <tr key={i} className="border-t border-[var(--border)]/60">
                        <td className="py-0.5 pr-2 uppercase font-bold text-[var(--ink-2)] whitespace-nowrap">{s.elevation}</td>
                        <td className="py-0.5 pr-2 text-[var(--ink)]">{s.surface}</td>
                        <td className="py-0.5 pr-2 font-mono-num text-right text-[var(--ink)] whitespace-nowrap">
                          {Math.round(s.sqft * 10) / 10} ft²
                        </td>
                        <td className="py-0.5 text-[var(--muted)] whitespace-nowrap text-right">
                          {OWNER_LABELS[s.owner] || s.owner}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })}
          <div className="text-[9px] text-[var(--muted)] italic">
            Same trace that prints on the quote line notes — if a number here
            looks wrong, fix the surface that owns it (chip swap, accent, or
            annotation), not the total.
          </div>
        </div>
      )}
    </div>
  );
}
