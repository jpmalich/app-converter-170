// BLUEPRINT READ-BACK CARD (Howard authorized 2026-08-06).
// DISPLAY-ONLY: renders `result.readback` built server-side from the run's
// raw extraction. Recomputes nothing, writes nothing — visibility flags so
// geometry misses (gable-blind planes, phantom porches, averaged corners)
// are obvious at a glance instead of buried in the material list.
import React from "react";
import { AlertTriangle, CheckCircle2, XCircle, Info } from "lucide-react";
import { useT } from "@/lib/i18n";

const num = (v) => (v == null ? "—" : Math.round(v * 10) / 10);

const Flag = ({ level, children, testid }) => {
  const cls =
    level === "loud"
      ? "bg-[#FEF2F2] text-[#B91C1C] border-[#FCA5A5]"
      : level === "warn"
      ? "bg-[#FFFBEB] text-[#92400E] border-[#FCD34D]"
      : "bg-[var(--surface)] text-[var(--muted)] border-[var(--border)]";
  const Icon = level === "loud" ? XCircle : level === "warn" ? AlertTriangle : Info;
  return (
    <div data-testid={testid} className={`flex items-start gap-1.5 border px-2 py-1 text-[11px] leading-snug ${cls}`}>
      <Icon className="w-3.5 h-3.5 mt-[1px] shrink-0" />
      <span>{children}</span>
    </div>
  );
};

export default function BlueprintReadBackCard({ readback }) {
  const t = useT();
  if (!readback) return null;
  const { planes, no_planes, plane_totals, garage_banner, corners, wing_check, porch, rail } = readback;

  return (
    <div data-testid="bp-readback-card" className="border border-[var(--border)] mt-3">
      <div className="px-3 py-2 border-b border-[var(--border)] flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider">{t("bp.rb.title")}</span>
        <span className="text-[10px] text-[var(--muted)]">{t("bp.rb.readonly")}</span>
      </div>

      {/* 1 — roof-plane census */}
      <div className="px-3 py-2 space-y-1.5">
        <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{t("bp.rb.planes")}</div>
        {garage_banner && (
          <Flag level="loud" testid="bp-rb-no-garage-banner">{t("bp.rb.noGarage")}</Flag>
        )}
        {no_planes ? (
          <Flag level="loud" testid="bp-rb-no-planes">{t("bp.rb.noPlanes")}</Flag>
        ) : (
          <table className="w-full text-[11px] font-mono-num" data-testid="bp-rb-plane-table">
            <thead>
              <tr className="text-left text-[10px] uppercase text-[var(--muted)]">
                <th className="pr-2 font-semibold">{t("bp.rb.plane")}</th>
                <th className="pr-2 font-semibold text-right">{t("bp.rb.eave")}</th>
                <th className="pr-2 font-semibold text-right">{t("bp.rb.rake")}</th>
                <th className="pr-2 font-semibold text-right">{t("bp.rb.gableEnds")}</th>
                <th className="pr-2 font-semibold text-right">{t("bp.rb.porchSqft")}</th>
              </tr>
            </thead>
            <tbody>
              {planes.map((p, i) => (
                <React.Fragment key={i}>
                  <tr data-testid={`bp-rb-plane-${p.label}`}>
                    <td className="pr-2">{p.label}{p.is_porch ? " ⌂" : ""}</td>
                    <td className="pr-2 text-right">{num(p.eave_lf)}</td>
                    <td className={`pr-2 text-right ${p.gable_blind ? "text-[#B91C1C] font-bold" : ""}`}>{num(p.rake_lf)}</td>
                    <td className="pr-2 text-right">{p.gable_ends}</td>
                    <td className="pr-2 text-right">{p.is_porch ? num(p.porch_ceiling_sqft) : "—"}</td>
                  </tr>
                  {p.gable_blind && (
                    <tr>
                      <td colSpan={5} className="pb-1">
                        <Flag level="loud" testid={`bp-rb-gable-blind-${p.label}`}>{t("bp.rb.gableBlind", { plane: p.label })}</Flag>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {plane_totals && (
                <tr className="border-t border-[var(--border)] font-bold" data-testid="bp-rb-plane-totals">
                  <td className="pr-2">{t("bp.rb.totals")}</td>
                  <td className="pr-2 text-right">{num(plane_totals.eaves_lf)}</td>
                  <td className="pr-2 text-right">{num(plane_totals.rakes_lf)}</td>
                  <td className="pr-2 text-right">{plane_totals.gable_ends}</td>
                  <td className="pr-2 text-right">—</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* 2 — corner ledger */}
      <div className="px-3 py-2 space-y-1.5 border-t border-[var(--border)]">
        <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{t("bp.rb.corners")}</div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono-num" data-testid="bp-rb-corner-ledger">
          <span>{t("bp.rb.outside")}: <b>{corners.outside}</b> ({num(corners.outside_lf)} LF)</span>
          <span>{t("bp.rb.inside")}: <b>{corners.inside}</b> ({num(corners.inside_lf)} LF)</span>
          {corners.invariant_ok != null && (
            <span data-testid="bp-rb-invariant" className={`inline-flex items-center gap-1 font-bold ${corners.invariant_ok ? "text-[#15803D]" : "text-[#B91C1C]"}`}>
              {corners.invariant_ok ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
              {t("bp.rb.invariant")}: {corners.invariant_ok ? t("bp.rb.pass") : t("bp.rb.fail")}
            </span>
          )}
        </div>
        {corners.basis === "averaged" && (
          <Flag level="warn" testid="bp-rb-basis-averaged">{t("bp.rb.basis.averaged")}</Flag>
        )}
        {corners.basis === "per_corner" && (
          <Flag level="info" testid="bp-rb-basis-percorner">{t("bp.rb.basis.per_corner")}</Flag>
        )}
        {corners.basis === "missing" && (
          <Flag level="warn" testid="bp-rb-basis-missing">{t("bp.rb.basis.missing")}</Flag>
        )}
        {wing_check?.flag && (
          <Flag level="loud" testid="bp-rb-wing-flag">
            {t("bp.rb.wing", { fp: num(wing_check.footprint_area_sqft), rect: num(wing_check.rectangle_area_sqft) })}
          </Flag>
        )}
      </div>

      {/* 3 — porch tag */}
      <div className="px-3 py-2 space-y-1.5 border-t border-[var(--border)]">
        <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{t("bp.rb.porch")}</div>
        {porch.status === "plane_read" && (
          <Flag level="info" testid="bp-rb-porch-read">{t("bp.rb.porch.plane_read", { sqft: num(porch.ceiling_sqft) })}</Flag>
        )}
        {porch.status === "plane_without_ceiling" && (
          <Flag level="warn" testid="bp-rb-porch-noceiling">{t("bp.rb.porch.plane_without_ceiling")}</Flag>
        )}
        {porch.status === "phantom_ceiling" && (
          <Flag level="loud" testid="bp-rb-porch-phantom">{t("bp.rb.porch.phantom_ceiling", { sqft: num(porch.ceiling_sqft) })}</Flag>
        )}
        {porch.status === "absent" && (
          <Flag level="warn" testid="bp-rb-porch-absent">{t("bp.rb.porch.absent")}</Flag>
        )}
      </div>

      {/* 4 — honesty-flag rail */}
      {rail?.length > 0 && (
        <div className="px-3 py-2 space-y-1 border-t border-[var(--border)]">
          <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{t("bp.rb.rail")}</div>
          {rail.map((f, i) => (
            <Flag key={i} level={f.level} testid={`bp-rb-rail-${f.code}`}>
              {t(`bp.rb.rail.${f.code}`, { text: f.text || "" })}
            </Flag>
          ))}
        </div>
      )}
    </div>
  );
}
