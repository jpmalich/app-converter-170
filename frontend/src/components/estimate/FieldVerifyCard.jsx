// FIELD VERIFY card (Howard, approved 2026-07-20) — the 3D panel's working
// machinery re-homed (re-mount, not rebuild) into the exact slot the 3D
// occupied: per-wall takeoff, TapeCheckPanel (identical writes: tape-check /
// score / freeze), taped appendage dims (the SAME DimEditRow rows, identical
// lp-appendage-dims writes), plus the "View Source Blueprints" entry —
// blueprint-path estimates only (live or CUT-archived run). Ships BEFORE the
// 3D flag flips so the tape workflow is never dark.
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Ruler, FileText } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import TapeCheckPanel from "@/components/estimate/TapeCheckPanel";
import { buildHouseJson, DimEditRow } from "@/components/estimate/HouseModel3D";

export default function FieldVerifyCard({ preview, estimate, runId, onDimsSaved, dimsRefreshKey }) {
  const [apDims, setApDims] = useState(() => estimate?.lp_appendage_dims || {});
  const [dimOffers, setDimOffers] = useState([]);
  const [bpRun, setBpRun] = useState(null);

  useEffect(() => {
    if (!estimate?.id) return;
    api.get(`/estimates/${estimate.id}/lp-appendage-dims`)
      .then(({ data }) => { setApDims(data.dims || {}); setDimOffers(data.offers || []); })
      .catch(() => {});
  }, [estimate?.id, dimsRefreshKey]);

  useEffect(() => {
    if (!estimate?.id) return;
    api.get(`/measure/ai-blueprint/latest-for-estimate/${estimate.id}`)
      .then(({ data }) => setBpRun(data?.run || null))
      .catch(() => {});
  }, [estimate?.id]);

  // Identical write path to the retired 3D panel (server stays SSOT).
  const saveDim = async (key, field, value, source) => {
    try {
      const { data } = await api.post(`/estimates/${estimate.id}/lp-appendage-dims`,
        value == null ? { key, field, action: "revert" } : { key, field, value, source: source || "user" });
      setApDims((prev) => {
        const next = { ...prev, [key]: { ...(prev[key] || {}) } };
        if (value == null) delete next[key][field];
        else next[key][field] = { value: data.value, status: data.status, at: data.at, by: data.by };
        return next;
      });
      onDimsSaved?.();
    } catch {
      toast.error("Could not save the dimension — try again.");
    }
  };

  const house = useMemo(() => {
    try {
      return buildHouseJson(preview, { pitch: null, eaveHeights: {}, widths: {} }, estimate, apDims);
    } catch {
      return null;
    }
  }, [preview, estimate, apDims]);

  const peb = preview?.measurements?._per_elevation_breakdown || [];
  const appendages = house?.appendages || [];

  return (
    <div className="space-y-3" data-testid="field-verify-card">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)] flex items-center gap-2">
          <Ruler className="w-3 h-3" /> Field Verify — per-wall takeoff · tape check · taped dims
        </div>
        {bpRun && (
          <Link
            to={`/estimate/${estimate.id}/source-sheets`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-[var(--ai)] text-[var(--ai)] text-[10px] font-bold uppercase tracking-wider hover:bg-[var(--ai)] hover:text-white transition-colors"
            data-testid="field-verify-source-blueprints-link"
            title="Read-only viewer — the exact blueprint pages the AI analyzed, with per-page provenance"
          >
            <FileText className="w-3 h-3" /> View Source Blueprints →
          </Link>
        )}
      </div>

      {peb.length > 0 && (
        <div className="p-3 bg-[var(--surface)] border border-[var(--border)]" data-testid="field-verify-per-wall">
          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-1.5">
            Per-wall takeoff <span className="text-[9px] italic font-normal">· AI-read, server-computed — SSOT</span>
          </div>
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-[9px] uppercase tracking-wider text-[var(--muted)]">
                <th className="text-left py-0.5">Wall</th>
                <th className="text-right py-0.5">Body ft²</th>
                <th className="text-right py-0.5">Gable ft²</th>
                <th className="text-right py-0.5">Dormer ft²</th>
                <th className="text-right py-0.5">Total ft²</th>
              </tr>
            </thead>
            <tbody>
              {peb.map((r, i) => {
                const total = (r.wall_body_sqft || 0) + (r.gable_sqft || 0) + (r.dormer_sqft || 0);
                return (
                  <tr key={i} className="border-t border-[var(--border)]" data-testid={`field-verify-wall-row-${i}`}>
                    <td className="py-1 uppercase font-bold text-[var(--ink-2)]">{r.label}</td>
                    <td className="py-1 text-right font-mono-num">{Math.round(r.wall_body_sqft || 0)}</td>
                    <td className="py-1 text-right font-mono-num">{Math.round(r.gable_sqft || 0)}</td>
                    <td className="py-1 text-right font-mono-num">{Math.round(r.dormer_sqft || 0)}</td>
                    <td className="py-1 text-right font-mono-num font-bold">{Math.round(total)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {appendages.length > 0 && (
        <div className="p-3 bg-[var(--surface)] border border-[var(--border)] space-y-1" data-testid="field-verify-taped-dims">
          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-1">
            Taped dims — appendages <span className="text-[9px] italic font-normal">· user-measured dims re-derive the math; assumed dims never enter it</span>
          </div>
          {appendages.map((ap, i) => {
            const apKey = `appendage:${ap.originalWall || ap.wall}`;
            return (
              <div key={i} className="py-1 border-t border-[var(--border)] first:border-t-0">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--ink-2)]">
                  {ap.kind || "Appendage"} — {ap.wall} wall
                </div>
                <DimEditRow
                  label="Depth" field="depth_ft" apKey={apKey}
                  entry={(apDims[apKey] || {}).depth_ft}
                  valueFt={ap.depthFt}
                  fallbackText={ap.depthSource === "printed"
                    ? `${ap.depthFt.toFixed(1)} ft — printed on plans`
                    : `~${ap.depthFt.toFixed(0)} ft — assumed, not measured`}
                  offer={(dimOffers.find((o) => o.key === apKey) || {}).depth_ft}
                  onSave={saveDim}
                  testid={`field-verify-appendage-depth-${i}`}
                />
                <DimEditRow
                  label="Height" field="height_ft" apKey={apKey}
                  entry={(apDims[apKey] || {}).height_ft}
                  valueFt={ap.heightFt}
                  fallbackText={ap.heightSource === "printed"
                    ? `${ap.heightFt.toFixed(1)} ft — printed on plans`
                    : "above roofline — assumed, not measured"}
                  offer={(dimOffers.find((o) => o.key === apKey) || {}).height_ft}
                  onSave={saveDim}
                  testid={`field-verify-appendage-height-${i}`}
                />
              </div>
            );
          })}
        </div>
      )}

      <TapeCheckPanel
        estimateId={estimate?.id}
        runId={runId}
        facades={house?.facades || []}
        dormers={house?.roof?.dormers || []}
      />
    </div>
  );
}
