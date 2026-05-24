import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { fmt, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, FileText, Search, Download, Copy } from "lucide-react";

// Categorize an estimate into one of the pipeline buckets based on its lifecycle fields.
function statusOf(e) {
  if (e.accepted_at) return "accepted";
  if (e.last_sent_at) return "sent";
  return "draft";
}

const FILTERS = [
  { key: "all", label: "All" },
  { key: "draft", label: "Draft" },
  { key: "sent", label: "Sent" },
  { key: "accepted", label: "Accepted" },
];

export default function Dashboard() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const nav = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/estimates");
      setItems(data);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const createEstimate = async () => {
    try {
      const { data } = await api.post("/estimates", {
        customer_name: "",
        estimate_number: `EST-${Date.now().toString().slice(-6)}`,
        estimate_date: new Date().toISOString().slice(0, 10),
      });
      nav(`/estimate/${data.id}`);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  const del = async (id) => {
    if (!window.confirm("Delete this estimate?")) return;
    await api.delete(`/estimates/${id}`);
    setItems((x) => x.filter((e) => e.id !== id));
    toast.success("Estimate deleted");
  };

  const duplicate = async (id) => {
    try {
      const { data } = await api.post(`/estimates/${id}/duplicate`);
      toast.success("Estimate duplicated — customer fields cleared");
      nav(`/estimate/${data.id}`);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  const calcTotals = (e) => {
    const subMat = (e.lines || []).reduce((s, l) => s + (l.qty || 0) * (l.mat || 0), 0) +
      (e.misc_material || []).reduce((s, l) => s + (l.mat || 0), 0);
    const subLab = (e.lines || []).reduce((s, l) => s + (l.qty || 0) * (l.lab || 0), 0) +
      (e.misc_material || []).reduce((s, l) => s + (l.lab || 0), 0) +
      (e.misc_labor || []).reduce((s, l) => s + (l.lab || 0), 0);
    const wasted = subMat * (1 + (e.waste_pct || 0) / 100);
    const tax = e.tax_enabled ? wasted * ((e.tax_rate || 0) / 100) : 0;
    const base = wasted + tax + subLab;
    const pct = (e.margin_pct || 0) / 100;
    const mode = e.pricing_mode || "markup";
    let sell;
    if (mode === "margin") {
      const denom = 1 - Math.min(pct, 0.99);
      sell = denom > 0 ? base / denom : base;
    } else {
      sell = base * (1 + pct);
    }
    return { base, sell };
  };

  // Pipeline stats: how many in each bucket + dollar values for sent (pending) and accepted (won).
  const stats = useMemo(() => {
    const out = { draft: 0, sent: 0, accepted: 0, won_total: 0, pending_total: 0 };
    for (const e of items) {
      const s = statusOf(e);
      out[s] += 1;
      const { sell } = calcTotals(e);
      if (s === "accepted") out.won_total += sell;
      if (s === "sent") out.pending_total += sell;
    }
    return out;
  }, [items]);

  const filtered = items
    .filter((e) => statusFilter === "all" || statusOf(e) === statusFilter)
    .filter((e) =>
      !q ||
      (e.customer_name || "").toLowerCase().includes(q.toLowerCase()) ||
      (e.estimate_number || "").toLowerCase().includes(q.toLowerCase()) ||
      (e.address || "").toLowerCase().includes(q.toLowerCase())
    );

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="dashboard">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-[#A1A1AA] mb-1">Dashboard</div>
          <h1 className="font-heading text-4xl sm:text-5xl text-[#09090B]">Estimates</h1>
        </div>
        <div className="flex gap-3">
          <button
            className="btn-secondary"
            onClick={async () => {
              try {
                const res = await api.get(`/exports/estimates.csv`, { responseType: "blob" });
                const url = URL.createObjectURL(res.data);
                const a = document.createElement("a");
                a.href = url;
                a.download = "estimates.csv";
                a.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              } catch (e) {
                toast.error(formatApiError(e.response?.data?.detail));
              }
            }}
            data-testid="export-all-csv-btn"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
          <button className="btn-primary" onClick={createEstimate} data-testid="new-estimate-btn">
            <Plus className="w-4 h-4" /> New Estimate
          </button>
        </div>
      </div>

      <div className="mb-6 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#A1A1AA]" />
        <input
          className="input pl-10"
          placeholder="Search by customer, address, or estimate #"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          data-testid="search-input"
        />
      </div>

      {/* Pipeline stats — Draft / Sent / Accepted with running dollar totals */}
      <div
        className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6"
        data-testid="pipeline-stats"
      >
        <StatCard label="Drafts" value={stats.draft} sublabel="In progress" />
        <StatCard
          label="Sent"
          value={stats.sent}
          sublabel={fmt(stats.pending_total) + " pending"}
          accent="orange"
        />
        <StatCard
          label="Accepted"
          value={stats.accepted}
          sublabel={fmt(stats.won_total) + " won"}
          accent="green"
        />
        <StatCard
          label="Win Rate"
          value={
            stats.sent + stats.accepted === 0
              ? "—"
              : `${Math.round((stats.accepted / (stats.sent + stats.accepted)) * 100)}%`
          }
          sublabel={`${stats.accepted} of ${stats.sent + stats.accepted} sent`}
        />
      </div>

      {/* Status filter chips */}
      <div
        className="flex flex-wrap gap-2 mb-4"
        data-testid="status-filter"
      >
        {FILTERS.map((f) => {
          const active = statusFilter === f.key;
          const count = f.key === "all" ? items.length : stats[f.key];
          return (
            <button
              key={f.key}
              type="button"
              onClick={() => setStatusFilter(f.key)}
              className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-bold uppercase tracking-wider border transition ${
                active
                  ? "bg-[#09090B] text-white border-[#09090B]"
                  : "bg-white text-[#52525B] border-[#E4E4E7] hover:border-[#09090B]"
              }`}
              data-testid={`filter-${f.key}`}
            >
              {f.label}
              <span
                className={`inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-sm text-[10px] font-mono-num ${
                  active ? "bg-white/20 text-white" : "bg-[#F4F4F5] text-[#71717A]"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="card">
        <div className="hidden md:grid grid-cols-12 gap-4 px-5 py-3 bg-[#E4E4E7] text-xs uppercase tracking-[0.18em] text-[#52525B] font-bold">
          <div className="col-span-2">Estimate #</div>
          <div className="col-span-4">Customer</div>
          <div className="col-span-3">Address</div>
          <div className="col-span-2 text-right">Sell Price</div>
          <div className="col-span-1 text-right">Actions</div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-[#52525B]">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center" data-testid="empty-state">
            <FileText className="w-12 h-12 mx-auto text-[#A1A1AA] mb-3" />
            <div className="font-heading text-xl text-[#09090B] mb-1">No estimates yet</div>
            <div className="text-sm text-[#52525B] mb-6">Create your first estimate to get going.</div>
            <button className="btn-primary" onClick={createEstimate}>
              <Plus className="w-4 h-4" /> New Estimate
            </button>
          </div>
        ) : (
          filtered.map((e) => {
            const { sell } = calcTotals(e);
            return (
              <div
                key={e.id}
                className="grid grid-cols-12 gap-4 px-5 py-4 border-t border-[#E4E4E7] items-center hover:bg-[#FAFAFA] cursor-pointer"
                onClick={() => nav(`/estimate/${e.id}`)}
                data-testid={`estimate-row-${e.id}`}
              >
                <div className="col-span-12 md:col-span-2 font-mono-num text-sm text-[#09090B]">
                  <div className="text-[10px] uppercase tracking-wider text-[#A1A1AA] md:hidden">#</div>
                  {e.estimate_number || "—"}
                </div>
                <div className="col-span-12 md:col-span-4">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="font-semibold text-[#09090B]">{e.customer_name || "Untitled"}</div>
                    {e.accepted_at ? (
                      <span
                        className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-[#DCFCE7] text-[#15803D] border border-[#86EFAC] rounded-sm"
                        title={`Accepted ${new Date(e.accepted_at).toLocaleString()}`}
                        data-testid={`status-accepted-${e.id}`}
                      >
                        ✓ Accepted
                      </span>
                    ) : e.last_sent_at ? (
                      <span
                        className="inline-flex items-center text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-[#FFF7ED] text-[#C2410C] border border-[#FED7AA] rounded-sm"
                        title={`Sent ${new Date(e.last_sent_at).toLocaleString()}`}
                        data-testid={`status-sent-${e.id}`}
                      >
                        Sent
                      </span>
                    ) : null}
                  </div>
                  <div className="text-xs text-[#A1A1AA]">{new Date(e.updated_at).toLocaleString()}</div>
                </div>
                <div className="col-span-12 md:col-span-3 text-sm text-[#52525B] truncate">{e.address || "—"}</div>
                <div className="col-span-8 md:col-span-2 text-right font-mono-num text-lg font-bold text-[#09090B]">
                  {fmt(sell)}
                </div>
                <div className="col-span-4 md:col-span-1 text-right flex items-center justify-end gap-1">
                  <button
                    className="btn-ghost"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      duplicate(e.id);
                    }}
                    aria-label="Duplicate"
                    title="Duplicate this estimate"
                    data-testid={`duplicate-${e.id}`}
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    className="btn-danger"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      del(e.id);
                    }}
                    aria-label="Delete"
                    data-testid={`delete-${e.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </main>
  );
}

function StatCard({ label, value, sublabel, accent }) {
  // The accent strip on the left signals which bucket this card belongs to
  // (orange = Sent / pending revenue, green = Accepted / won revenue).
  const stripe =
    accent === "orange" ? "bg-[#F97316]"
      : accent === "green" ? "bg-[#16A34A]"
      : "bg-[#E4E4E7]";
  return (
    <div className="card flex overflow-hidden">
      <div className={`w-1 ${stripe}`} />
      <div className="px-4 py-3 flex-1 min-w-0">
        <div className="text-[10px] uppercase tracking-[0.2em] text-[#A1A1AA] font-bold">
          {label}
        </div>
        <div className="font-mono-num text-2xl font-bold text-[#09090B] leading-tight">
          {value}
        </div>
        {sublabel ? (
          <div className="text-[11px] text-[#71717A] truncate">{sublabel}</div>
        ) : null}
      </div>
    </div>
  );
}

