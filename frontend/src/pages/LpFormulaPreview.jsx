import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Shield, FlaskConical, AlertTriangle, CheckCircle2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Iter 78ab — Admin-only side-by-side preview of LP qty under the
// legacy `sqft × 0.11` math vs the new PDF-accurate per-profile
// formulas. Lets Howard confirm the delta on a Campbell-sized job
// before flipping `LP_AI_FORMULAS_V1` in production.
export default function LpFormulaPreview() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [presets, setPresets] = useState([]);
  const [preset, setPreset] = useState("campbell");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    axios
      .get(`${API}/admin/lp-formula-preview/presets`, {
        headers: { "X-Admin-Token": token },
      })
      .then((r) => setPresets(r.data.presets || []))
      .catch((e) => {
        setError(
          e.response?.status === 403
            ? "Invalid admin token. Check the ?token=... in your URL."
            : "Failed to load presets: " + (e.response?.data?.detail || e.message)
        );
      });
  }, [token]);

  const runPreview = async (presetKey) => {
    setLoading(true);
    setError("");
    try {
      const r = await axios.post(
        `${API}/admin/lp-formula-preview`,
        { preset: presetKey },
        { headers: { "X-Admin-Token": token } }
      );
      setData(r.data);
    } catch (e) {
      setError("Preview failed: " + (e.response?.data?.detail || e.message));
      toast.error("Preview failed");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-app)]">
        <div className="card p-8 max-w-md w-full">
          <Shield className="w-10 h-10 text-[var(--brand-text)] mb-4" />
          <h1 className="font-heading text-2xl text-[var(--ink)] mb-2">LP Formula Preview</h1>
          <p className="text-sm text-[var(--ink-2)]">
            This URL requires an admin token. Append{" "}
            <code className="font-mono">?token=YOUR_TOKEN</code> to the URL.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-app)] py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <header className="mb-6">
          <div className="flex items-center gap-2 mb-1">
            <FlaskConical className="w-5 h-5 text-[var(--brand-text)]" />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--muted)]">
              Supplier Admin · LP Formula Go/No-Go Gate
            </span>
          </div>
          <h1 className="font-heading text-3xl text-[var(--ink)] mb-1">
            LP SmartSide AI Formula Preview
          </h1>
          <p className="text-sm text-[var(--ink-2)] max-w-3xl">
            Side-by-side LP-line qty diff between the legacy{" "}
            <code className="font-mono">sqft × 0.11</code> math and the PDF-accurate
            per-profile formulas (8&quot; Lap / 16&quot; Soffit / 7&quot; Shake reveal + 10% waste).
            Pick a preset, review the deltas, then decide whether to flip{" "}
            <code className="font-mono">LP_AI_FORMULAS_V1=true</code> in{" "}
            <code className="font-mono">backend/.env</code>.
          </p>
        </header>

        {data?.flag_currently_enabled !== undefined && (
          <div
            className={`mb-4 p-3 border ${
              data.flag_currently_enabled
                ? "border-[var(--success)] bg-[#F0FDF4]"
                : "border-[var(--muted)] bg-[var(--surface-muted)]"
            } flex items-center gap-2 text-sm`}
            data-testid="lp-flag-status"
          >
            {data.flag_currently_enabled ? (
              <CheckCircle2 className="w-4 h-4 text-[var(--success)]" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-[var(--muted)]" />
            )}
            <div>
              <span className="font-bold">
                {data.flag_currently_enabled ? "LIVE" : "STAGED (OFF)"}
              </span>{" "}
              — <code className="font-mono">LP_AI_FORMULAS_V1</code> is currently{" "}
              <strong>{data.flag_currently_enabled ? "enabled" : "disabled"}</strong>{" "}
              in production. {data.flag_currently_enabled
                ? "Contractors are quoting with the PDF formulas."
                : "Contractors are quoting with the legacy math."}
            </div>
          </div>
        )}

        <div className="card p-4 mb-4">
          <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--muted)] block mb-2">
            Sample Job Preset
          </label>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              className="input h-10 text-sm flex-1 min-w-[300px]"
              value={preset}
              onChange={(e) => setPreset(e.target.value)}
              data-testid="lp-preview-preset"
            >
              {presets.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="px-4 py-2 bg-[var(--bar-bg)] text-white hover:bg-[#27272A] text-xs font-bold uppercase tracking-wider"
              onClick={() => runPreview(preset)}
              disabled={loading}
              data-testid="lp-preview-run"
            >
              {loading ? "Running…" : "Run Side-by-Side Preview"}
            </button>
          </div>
          {data?.preset_label && (
            <div className="mt-2 text-[11px] text-[var(--muted)]">
              <span className="uppercase tracking-wider font-bold mr-1">Scenario:</span>
              {data.preset_label}
            </div>
          )}
        </div>

        {error && (
          <div className="card p-3 mb-4 border-l-4 border-[#DC2626] bg-[var(--danger-soft)] text-sm text-[#991B1B]">
            {error}
          </div>
        )}

        {data && (
          <>
            <div className="card p-4 mb-4 flex items-center gap-6">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--muted)]">
                  LP Lines Total
                </div>
                <div className="font-mono-num text-2xl font-bold text-[var(--ink)]">
                  {data.summary?.lines_total ?? 0}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--muted)]">
                  Lines With Δ
                </div>
                <div
                  className={`font-mono-num text-2xl font-bold ${
                    (data.summary?.lines_changed ?? 0) > 0 ? "text-[var(--brand-text)]" : "text-[var(--ink)]"
                  }`}
                  data-testid="lp-preview-changed"
                >
                  {data.summary?.lines_changed ?? 0}
                </div>
              </div>
            </div>

            <div className="card overflow-x-auto" data-testid="lp-preview-diff-table">
              <table className="w-full text-sm">
                <thead className="bg-[var(--surface-muted)] border-b border-[var(--border)]">
                  <tr>
                    <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-[var(--muted)]">
                      Section
                    </th>
                    <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-[var(--muted)]">
                      Item
                    </th>
                    <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-[var(--muted)]">
                      Legacy
                    </th>
                    <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-[var(--muted)]">
                      PDF Formula
                    </th>
                    <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-[var(--muted)]">
                      Δ Qty
                    </th>
                    <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-[var(--muted)]">
                      Δ %
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.diff?.map((row, i) => {
                    const changed = Math.abs(row.delta_qty) > 0.0001;
                    return (
                      <tr
                        key={`${row.section}-${row.name}-${i}`}
                        className={`border-b border-[var(--bg-app)] ${
                          changed ? "bg-[#FFF7ED]" : ""
                        }`}
                        data-testid={`lp-preview-row-${i}`}
                      >
                        <td className="px-3 py-2 text-[12px] text-[var(--ink-2)]">
                          {row.section}
                        </td>
                        <td className="px-3 py-2 text-[12px] text-[var(--ink)]">
                          {row.name}
                          {row.pdf_note && row.pdf_note !== row.legacy_note && (
                            <div className="text-[10px] text-[var(--muted)] mt-0.5">
                              {row.pdf_note}
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2 text-[12px] text-right font-mono-num text-[var(--ink-2)]">
                          {row.legacy_qty} <span className="text-[var(--muted)]">{row.unit}</span>
                        </td>
                        <td className="px-3 py-2 text-[12px] text-right font-mono-num text-[var(--ink)] font-bold">
                          {row.pdf_qty} <span className="text-[var(--muted)]">{row.unit}</span>
                        </td>
                        <td
                          className={`px-3 py-2 text-[12px] text-right font-mono-num ${
                            row.delta_qty > 0
                              ? "text-[var(--success)] font-bold"
                              : row.delta_qty < 0
                              ? "text-[var(--danger-text)] font-bold"
                              : "text-[var(--muted)]"
                          }`}
                        >
                          {row.delta_qty > 0 ? "+" : ""}
                          {row.delta_qty}
                        </td>
                        <td
                          className={`px-3 py-2 text-[12px] text-right font-mono-num ${
                            row.delta_pct > 0
                              ? "text-[var(--success)]"
                              : row.delta_pct < 0
                              ? "text-[var(--danger-text)]"
                              : "text-[var(--muted)]"
                          }`}
                        >
                          {row.delta_pct > 0 ? "+" : ""}
                          {row.delta_pct}%
                        </td>
                      </tr>
                    );
                  })}
                  {(!data.diff || data.diff.length === 0) && (
                    <tr>
                      <td colSpan={6} className="px-3 py-6 text-center text-[var(--muted)] text-sm">
                        No LP lines emitted for this preset.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="mt-4 p-3 border border-[var(--border)] bg-[var(--surface-muted)] text-[11px] text-[var(--muted)] leading-relaxed">
              <strong>Go/No-Go decision:</strong> If the deltas above look right, set{" "}
              <code className="font-mono text-[var(--ink)]">LP_AI_FORMULAS_V1=true</code> in{" "}
              <code className="font-mono text-[var(--ink)]">backend/.env</code> and restart the
              backend (<code className="font-mono">sudo supervisorctl restart backend</code>).
              All four ingest paths (HOVER, AI Photo, Blueprint, manual) will pick up the new
              formulas immediately. Existing quotes are not retroactively recalculated.
            </div>
          </>
        )}
      </div>
    </div>
  );
}
