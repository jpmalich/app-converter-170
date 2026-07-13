// Iter 100 — QR doctrine (ruled): public, read-only, redacted view of the
// EXACT frozen material list that was printed. When the live estimate has
// drifted, a banner flags that a newer list exists — never a silent swap.
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, Lock, TriangleAlert } from "lucide-react";

const fmt = (n) =>
  Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function MaterialListShare() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/public/lp-material-list/${token}`
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          setError(
            res.status === 410
              ? "This link has expired."
              : body.detail || "Link not found or revoked."
          );
        } else {
          setData(await res.json());
        }
      } catch {
        setError("Could not load the material list. Check your connection and try again.");
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-500" data-testid="material-share-loading">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading material list…
      </div>
    );
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md text-center" data-testid="material-share-error">
          <div className="text-lg font-bold text-zinc-900 mb-2">Material list unavailable</div>
          <p className="text-sm text-zinc-500">{error}</p>
        </div>
      </div>
    );
  }

  const pkg = data.frozen || {};
  const meta = data.meta || {};
  const pricing = pkg.summary?.pricing || {};
  const printedAt = data.printed_at
    ? new Date(data.printed_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
    : "";
  const bySection = {};
  (pkg.lines || []).forEach((l) => {
    (bySection[l.section] = bySection[l.section] || []).push(l);
  });

  return (
    <div className="min-h-screen bg-zinc-100 py-6 px-3 sm:px-6" data-testid="material-share-page">
      <div className="max-w-3xl mx-auto bg-white border border-zinc-200 shadow-sm">
        {data.newer_available && (
          <div className="flex items-start gap-2 px-5 py-3 bg-amber-50 border-b border-amber-300 text-amber-900 text-sm" data-testid="material-share-banner">
            <TriangleAlert className="w-4 h-4 mt-0.5 flex-none" />
            <div>
              <span className="font-bold">Updated list available.</span>{" "}
              This page shows the exact version printed on {printedAt}. The estimate has
              changed since — ask your contractor for the latest printout.
            </div>
          </div>
        )}
        <div className="px-5 py-4 border-b-4 border-orange-500 flex flex-wrap justify-between gap-3">
          <div>
            <div className="text-base font-extrabold tracking-wide text-zinc-900">
              MATERIAL LIST — LP SMARTSIDE
            </div>
            <div className="text-[11px] text-zinc-500 mt-1 inline-flex items-center gap-1">
              <Lock className="w-3 h-3" /> Read-only · frozen as printed {printedAt}
            </div>
          </div>
          <div className="text-right text-xs text-zinc-500">
            <div className="font-bold text-zinc-900" data-testid="material-share-est-number">{meta.estimate_number || ""}</div>
            <div>{meta.customer_name || ""}</div>
            <div>{meta.address || ""}</div>
            <div>{meta.estimate_date || ""}</div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-zinc-500 border-b-2 border-zinc-900 bg-zinc-50">
                <th className="text-left px-4 py-2">Item</th>
                <th className="text-left px-2 py-2">Color</th>
                <th className="text-right px-2 py-2">Qty</th>
                <th className="text-left px-2 py-2">Unit</th>
                <th className="text-right px-2 py-2">Unit $</th>
                <th className="text-right px-4 py-2">Line $</th>
              </tr>
            </thead>
            {Object.entries(bySection).map(([section, lines]) => (
              <tbody key={section}>
                <tr className="bg-zinc-50">
                  <td colSpan={6} className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-orange-700">
                    {section}
                  </td>
                </tr>
                {lines.map((l) => {
                  const priced = l.pricing_status === "priced";
                  return (
                    <tr key={`${l.name}::${l.color || ""}`} className="border-b border-zinc-200 align-top" data-testid={`material-share-line-${l.name}`}>
                      <td className="px-4 py-2">
                        <div className="font-medium text-zinc-900">{l.name}</div>
                        {l.substituted_from && (
                          <div className="text-[10px] text-violet-700">
                            substituted from {l.substituted_from} — re-derived
                          </div>
                        )}
                      </td>
                      <td className="px-2 py-2 text-xs text-zinc-600">{l.color || "—"}</td>
                      <td className="px-2 py-2 text-right font-mono">{l.qty}</td>
                      <td className="px-2 py-2 text-xs text-zinc-600">{l.unit}</td>
                      <td className="px-2 py-2 text-right font-mono">
                        {priced ? fmt(l.unit_sell) : (
                          <span className="text-[10px] uppercase tracking-wider font-bold text-amber-700">
                            pricing pending
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right font-mono font-semibold">
                        {priced ? fmt(l.line_sell) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            ))}
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 border-t-2 border-zinc-900 bg-zinc-50">
          <div className="text-[11px] text-amber-700">
            {pricing.pending_lines > 0 && `${pricing.pending_lines} line(s) pricing pending`}
          </div>
          <div className="text-sm font-extrabold" data-testid="material-share-total">
            Materials total: {fmt(pricing.total_sell || 0)}
          </div>
        </div>
        <div className="px-5 py-2 text-[10px] text-zinc-400 border-t border-zinc-200">
          Derived from confirmed AI measurements — run {String(pkg.run_id || "").slice(0, 8)} · single source
        </div>
      </div>
    </div>
  );
}
