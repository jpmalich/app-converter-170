// Accuracy Report share — same /m/ doctrine: public, read-only view of the
// EXACT frozen report (honest-framing sections verbatim). When newer scored
// runs exist, a banner flags it — never a silent swap.
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, Lock, TriangleAlert } from "lucide-react";

export default function AccuracyReportShare() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/public/accuracy-report/${token}`
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
        setError("Could not load the report. Check your connection and try again.");
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-500" data-testid="accuracy-share-loading">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading accuracy report…
      </div>
    );
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md text-center" data-testid="accuracy-share-error">
          <div className="text-lg font-bold text-zinc-900 mb-2">Accuracy report unavailable</div>
          <p className="text-sm text-zinc-500">{error}</p>
        </div>
      </div>
    );
  }

  const meta = data.meta || {};
  const generatedAt = data.generated_at
    ? new Date(data.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
    : "";

  return (
    <div className="min-h-screen bg-zinc-100" data-testid="accuracy-share-page">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-widest text-orange-600">AI Measurement Accuracy Report</div>
            <div className="text-sm text-zinc-600" data-testid="accuracy-share-meta">
              {[meta.estimate_number, meta.customer_name].filter(Boolean).join(" — ")}
            </div>
          </div>
          <div className="inline-flex items-center gap-1.5 text-[11px] text-zinc-500 border border-zinc-300 bg-white px-2 py-1" data-testid="accuracy-share-frozen-badge">
            <Lock className="w-3 h-3" /> Read-only · frozen {generatedAt}
          </div>
        </div>
        {data.newer_available && (
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-400 px-3 py-2 text-[12px] text-amber-900" data-testid="accuracy-share-newer-banner">
            <TriangleAlert className="w-4 h-4 mt-0.5 shrink-0" />
            <span>
              <b>Newer scored runs exist</b> since this report was frozen. This page shows the exact report
              that was shared — ask the contractor for a fresh link to see the latest.
            </span>
          </div>
        )}
        <iframe
          title="Accuracy report"
          srcDoc={data.html}
          sandbox=""
          className="w-full bg-white border border-zinc-300"
          style={{ minHeight: "calc(100vh - 160px)" }}
          data-testid="accuracy-share-report-frame"
        />
      </div>
    </div>
  );
}
