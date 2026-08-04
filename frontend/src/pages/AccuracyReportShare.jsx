// Accuracy Report share — same /m/ doctrine: public, read-only view of the
// EXACT frozen report (honest-framing sections verbatim). When newer scored
// runs exist, a banner flags it — never a silent swap.
// BILINGUAL (Howard ruled 2026-08-04): the page chrome translates; the frozen
// report BODY is the sealed artifact and renders exactly as sealed — a note
// names that in Spanish rather than silently re-rendering a frozen document.
import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Loader2, Lock, TriangleAlert } from "lucide-react";
import { useT, useLang } from "@/lib/i18n";
import { PublicLangToggle } from "./MaterialListShare";

export default function AccuracyReportShare() {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const t = useT();
  const { lang, setLang } = useLang();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const wanted = searchParams.get("lang");
    if (wanted === "es" || wanted === "en") setLang(wanted);
  }, [searchParams, setLang]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/public/accuracy-report/${token}`
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          setError(res.status === 410 ? "expired" : body.detail || "notFound");
        } else {
          setData(await res.json());
        }
      } catch {
        setError("loadError");
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-500" data-testid="accuracy-share-loading">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> {t("ars.loading")}
      </div>
    );
  }
  if (error) {
    const known = { expired: t("mls.expired"), notFound: t("mls.notFound"), loadError: t("mls.loadError") };
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md text-center" data-testid="accuracy-share-error">
          <div className="text-lg font-bold text-zinc-900 mb-2">{t("ars.unavailable")}</div>
          <p className="text-sm text-zinc-500">{known[error] || error}</p>
        </div>
      </div>
    );
  }

  const meta = data.meta || {};
  const generatedAt = data.generated_at
    ? new Date(data.generated_at).toLocaleDateString(lang === "es" ? "es-MX" : "en-US", { year: "numeric", month: "short", day: "numeric" })
    : "";

  return (
    <div className="min-h-screen bg-zinc-100" data-testid="accuracy-share-page">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-widest text-orange-600">{t("ars.title")}</div>
            <div className="text-sm text-zinc-600" data-testid="accuracy-share-meta">
              {[meta.estimate_number, meta.customer_name].filter(Boolean).join(" — ")}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <PublicLangToggle />
            <div className="inline-flex items-center gap-1.5 text-[11px] text-zinc-500 border border-zinc-300 bg-white px-2 py-1" data-testid="accuracy-share-frozen-badge">
              <Lock className="w-3 h-3" /> {t("ars.frozen", { date: generatedAt })}
            </div>
          </div>
        </div>
        {data.newer_available && (
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-400 px-3 py-2 text-[12px] text-amber-900" data-testid="accuracy-share-newer-banner">
            <TriangleAlert className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{t("ars.newer")}</span>
          </div>
        )}
        {lang === "es" && (
          <div className="text-[11px] text-zinc-500" data-testid="accuracy-share-frozen-body-note">
            {t("ars.frozenBodyNote")}
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
