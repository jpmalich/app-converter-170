// Contractor Window Quotes labor divergence — admin GATE panel
// (approved 2026-07-15). Side-by-side ISS vs Contractor labor with
// per-item deltas; nothing reaches a contractor-visible surface until
// the diff is reviewed and approved. Divergence VALUES are HELD pending
// Howard's rate ruling — the draft starts empty.
import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Check, PanelsTopLeft, ShieldAlert } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const fmt = (n) => (n == null ? "—" : `$${Number(n).toFixed(2)}`);

export default function WindowLaborPanel({ token }) {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("draft");
  const [approvedAt, setApprovedAt] = useState(null);
  const [valuesHeld, setValuesHeld] = useState(true);
  const [edits, setEdits] = useState({}); // name → input string (unsaved)
  const [busy, setBusy] = useState(false);
  const headers = { "X-Admin-Token": token };

  const load = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/admin/window-labor/compare`, { headers });
      setRows(data.rows);
      setStatus(data.status);
      setApprovedAt(data.approved_at);
      setValuesHeld(data.values_held);
      setEdits({});
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const dirty = Object.keys(edits).length > 0;

  const saveDraft = async () => {
    const proposed = {};
    for (const [name, raw] of Object.entries(edits)) {
      const s = String(raw).trim();
      proposed[name] = s === "" ? null : parseFloat(s);
      if (proposed[name] != null && !(proposed[name] >= 0)) {
        toast.error(`Invalid rate for ${name}`);
        return;
      }
    }
    setBusy(true);
    try {
      await axios.put(`${API}/admin/window-labor/draft`, { proposed }, { headers });
      toast.success("Draft saved — gate re-opened for review");
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/admin/window-labor/approve`, {}, { headers });
      toast.success(`Approved — ${data.count} diverged rate(s) unlocked for the contractor windows surface`);
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const proposedCount = rows.filter((r) => r.proposed_lab != null).length;

  return (
    <div className="card p-6 mt-6" data-testid="window-labor-panel">
      <div className="flex items-center gap-3 mb-2">
        <PanelsTopLeft className="w-5 h-5 text-[var(--brand-text)]" />
        <div className="section-tag">Contractor Window Labor — Divergence Gate</div>
        {status === "approved" ? (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-[#DCFCE7] text-[#166534] border border-[#16A34A]" data-testid="window-labor-status">
            Approved {approvedAt ? new Date(approvedAt).toLocaleDateString() : ""}
          </span>
        ) : (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-[#FEF3C7] text-[#92400E] border border-[#F59E0B]" data-testid="window-labor-status">
            Gated — draft
          </span>
        )}
      </div>
      <p className="text-sm text-[var(--ink-2)] mb-2">
        Contractor Window Quotes currently mirror ISS Replacement Windows labor. Enter proposed
        contractor rates below, review the per-item deltas, then approve — no diverged rate reaches
        any contractor-visible surface until you approve the diff.
      </p>
      {valuesHeld && (
        <div className="flex items-center gap-2 text-xs font-semibold text-[#92400E] bg-[#FFFBEB] border border-[#F59E0B] px-3 py-2 mb-3" data-testid="window-labor-held-note">
          <ShieldAlert className="w-3.5 h-3.5" />
          Divergence values HELD pending your rate ruling (direction, structure, magnitude). The mechanism is live; the draft is empty.
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-xs" data-testid="window-labor-table">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-wider text-[var(--muted)] border-b border-[var(--border)]">
              <th className="py-1.5 pr-2">Item</th>
              <th className="py-1.5 pr-2">Unit</th>
              <th className="py-1.5 pr-2 text-right">ISS labor</th>
              <th className="py-1.5 pr-2 text-right">Contractor labor (proposed)</th>
              <th className="py-1.5 pr-2 text-right">Δ $</th>
              <th className="py-1.5 text-right">Δ %</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const editing = edits[r.name] !== undefined;
              const shown = editing ? edits[r.name] : (r.proposed_lab ?? "");
              const num = parseFloat(shown);
              const delta = Number.isFinite(num) ? num - r.iss_lab : null;
              return (
                <tr key={r.name} className="border-b border-[var(--border)]" data-testid={`window-labor-row-${r.name}`}>
                  <td className="py-1.5 pr-2">
                    {r.kind === "adder" ? <span className="text-[9px] font-bold uppercase text-[var(--muted)] mr-1">adder</span> : null}
                    {r.name}
                  </td>
                  <td className="py-1.5 pr-2 text-[var(--muted)]">{r.unit}</td>
                  <td className="py-1.5 pr-2 text-right font-mono-num">{fmt(r.iss_lab)}</td>
                  <td className="py-1.5 pr-2 text-right">
                    <input
                      type="number" step="0.01" min="0"
                      className="input w-24 text-xs py-0.5 px-1.5 text-right"
                      value={shown}
                      placeholder="—"
                      onChange={(e) => setEdits((p) => ({ ...p, [r.name]: e.target.value }))}
                      data-testid={`window-labor-input-${r.name}`}
                    />
                  </td>
                  <td className={`py-1.5 pr-2 text-right font-mono-num ${delta > 0 ? "text-emerald-700" : delta < 0 ? "text-red-700" : "text-[var(--muted)]"}`}>
                    {delta == null ? "—" : `${delta >= 0 ? "+" : ""}${delta.toFixed(2)}`}
                  </td>
                  <td className={`py-1.5 text-right font-mono-num ${delta > 0 ? "text-emerald-700" : delta < 0 ? "text-red-700" : "text-[var(--muted)]"}`}>
                    {delta == null || !r.iss_lab ? "—" : `${delta >= 0 ? "+" : ""}${((delta / r.iss_lab) * 100).toFixed(1)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3 mt-4">
        <button
          type="button"
          onClick={saveDraft}
          disabled={!dirty || busy}
          className="px-4 py-2 text-xs font-bold uppercase tracking-wider bg-[var(--bar-bg)] text-white disabled:opacity-40"
          data-testid="window-labor-save-draft"
        >
          Save draft
        </button>
        <button
          type="button"
          onClick={approve}
          disabled={busy || dirty || proposedCount === 0 || status === "approved"}
          className="px-4 py-2 text-xs font-bold uppercase tracking-wider border border-[#16A34A] text-[#166534] disabled:opacity-40 inline-flex items-center gap-1.5"
          title={proposedCount === 0 ? "Values held pending the rate ruling — nothing to approve" : dirty ? "Save the draft first, then review and approve" : ""}
          data-testid="window-labor-approve"
        >
          <Check className="w-3.5 h-3.5" /> Approve diff ({proposedCount})
        </button>
        {dirty && <span className="text-[11px] text-[#92400E]">Unsaved draft edits — save before approving.</span>}
      </div>
    </div>
  );
}
