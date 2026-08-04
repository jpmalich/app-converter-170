// Iter 100 — QR doctrine (ruled): public, read-only, redacted view of the
// EXACT frozen material list that was printed. When the live estimate has
// drifted, a banner flags that a newer list exists — never a silent swap.
// BILINGUAL (Howard ruled 2026-08-04): chrome, sections and units translate;
// SKU names and color names stay VERBATIM — the crew orders by the name.
import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { Loader2, Lock, TriangleAlert } from "lucide-react";
import { useT, useLang } from "@/lib/i18n";
import { tSection, tUnit } from "@/lib/catalogTranslations";

export function PublicLangToggle() {
  const { lang, setLang } = useLang();
  return (
    <div className="inline-flex border border-zinc-300 bg-white text-[10px] font-bold uppercase tracking-wider" data-testid="public-lang-toggle">
      {["en", "es"].map((l) => (
        <button key={l} type="button" onClick={() => setLang(l)}
          className={`px-2 py-1 ${lang === l ? "bg-zinc-900 text-white" : "text-zinc-500"}`}
          data-testid={`public-lang-${l}`}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export default function MaterialListShare() {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const backEst = searchParams.get("est");
  const t = useT();
  const { lang, setLang } = useLang();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reqState, setReqState] = useState("idle"); // idle | sending | sent | failed

  // Honor ?lang=es on the QR link — the crew scans in their language.
  useEffect(() => {
    const wanted = searchParams.get("lang");
    if (wanted === "es" || wanted === "en") setLang(wanted);
  }, [searchParams, setLang]);

  const requestUpdate = async () => {
    setReqState("sending");
    try {
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/public/lp-material-list/${token}/request-update`,
        { method: "POST" }
      );
      setReqState(res.ok ? "sent" : "failed");
    } catch {
      setReqState("failed");
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/public/lp-material-list/${token}`
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
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-500" data-testid="material-share-loading">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> {t("mls.loading")}
      </div>
    );
  }
  if (error) {
    const known = { expired: t("mls.expired"), notFound: t("mls.notFound"), loadError: t("mls.loadError") };
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md text-center" data-testid="material-share-error">
          <div className="text-lg font-bold text-zinc-900 mb-2">{t("mls.unavailable")}</div>
          <p className="text-sm text-zinc-500">{known[error] || error}</p>
        </div>
      </div>
    );
  }

  const pkg = data.frozen || {};
  const meta = data.meta || {};
  const printedAt = data.printed_at
    ? new Date(data.printed_at).toLocaleDateString(lang === "es" ? "es-MX" : "en-US", { year: "numeric", month: "short", day: "numeric" })
    : "";
  const bySection = {};
  (pkg.lines || []).forEach((l) => {
    (bySection[l.section] = bySection[l.section] || []).push(l);
  });

  const backLink = backEst ? (
    <Link to={`/estimate/${backEst}`} className="text-sm underline text-zinc-600"
      data-testid="material-share-back-to-estimate">
      {t("mls.backToEstimate")}
    </Link>
  ) : null;

  return (
    <>
    <div className="no-print px-6 pt-4 flex items-center justify-between gap-3">
      <div>{backLink}</div>
      <PublicLangToggle />
    </div>
    <div className="min-h-screen bg-zinc-100 py-6 px-3 sm:px-6" data-testid="material-share-page">
      <div className="max-w-3xl mx-auto bg-white border border-zinc-200 shadow-sm">
        {data.newer_available && (
          <div className="flex items-start gap-2 px-5 py-3 bg-amber-50 border-b border-amber-300 text-amber-900 text-sm" data-testid="material-share-banner">
            <TriangleAlert className="w-4 h-4 mt-0.5 flex-none" />
            <div>
              <span className="font-bold">{t("mls.updatedTitle")}</span>{" "}
              {t("mls.updatedBody", { date: printedAt })}
              <div className="mt-2">
                {reqState === "sent" ? (
                  <span className="text-xs font-bold text-emerald-700" data-testid="request-update-sent">
                    {t("mls.requestSent")}
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={requestUpdate}
                    disabled={reqState === "sending"}
                    className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider bg-amber-700 text-white disabled:opacity-60"
                    data-testid="request-update-btn"
                  >
                    {reqState === "sending" ? t("mls.sending") : t("mls.requestBtn")}
                  </button>
                )}
                {reqState === "failed" && (
                  <span className="ml-2 text-xs text-red-700" data-testid="request-update-failed">
                    {t("mls.requestFailed")}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
        <div className="px-5 py-4 border-b-4 border-orange-500 flex flex-wrap justify-between gap-3">
          <div>
            <div className="text-base font-extrabold tracking-wide text-zinc-900">
              {t("mls.title")}
            </div>
            <div className="text-[11px] text-zinc-500 mt-1 inline-flex items-center gap-1">
              <Lock className="w-3 h-3" /> {t("mls.readOnly", { date: printedAt })}
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
                <th className="text-left px-4 py-2">{t("mls.th.item")}</th>
                <th className="text-left px-2 py-2">{t("mls.th.color")}</th>
                <th className="text-right px-2 py-2">{t("mls.th.qty")}</th>
                <th className="text-left px-4 py-2">{t("mls.th.unit")}</th>
              </tr>
            </thead>
            {Object.entries(bySection).map(([section, lines]) => (
              <tbody key={section}>
                <tr className="bg-zinc-50">
                  <td colSpan={4} className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-orange-700">
                    {tSection(section, lang)}
                  </td>
                </tr>
                {lines.map((l) => {
                  return (
                    <tr key={`${l.name}::${l.color || ""}`} className="border-b border-zinc-200 align-top" data-testid={`material-share-line-${l.name}`}>
                      <td className="px-4 py-2">
                        {/* SKU NAME VERBATIM (ruled 2026-07-31) — never translates */}
                        <div className="font-medium text-zinc-900">{l.name}</div>
                        {l.substituted_from && (
                          <div className="text-[10px] text-violet-700">
                            {t("mls.substitutedFrom", { name: l.substituted_from })}
                          </div>
                        )}
                        {(l.color_flags || []).map((f, fi) => (
                          <div key={fi} className={`text-[10px] font-semibold ${l.color_status === "unsupported" ? "text-red-700" : "text-amber-700"}`}>
                            ⚑ {f}
                          </div>
                        ))}
                      </td>
                      {/* COLOR NAME VERBATIM (Howard ruled: color names never translate) */}
                      <td className="px-2 py-2 text-xs text-zinc-600">{l.color || "—"}</td>
                      <td className="px-2 py-2 text-right font-mono">{l.qty}</td>
                      <td className="px-4 py-2 text-xs text-zinc-600">{tUnit(l.unit, lang)}</td>
                    </tr>
                  );
                })}
              </tbody>
            ))}
          </table>
        </div>
        {/* ONE MONEY SURFACE (ruled 2026-07-23): the shared list is the
            verification surface — quantities & derivations only, unpriced. */}
        <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 border-t-2 border-zinc-900 bg-zinc-50">
          <div className="text-[11px] text-zinc-500" data-testid="material-share-unpriced-note">
            {t("mls.unpricedNote")}
          </div>
        </div>
        <div className="px-5 py-2 text-[10px] text-zinc-400 border-t border-zinc-200" data-testid="material-share-geometry-basis">
          {pkg.geometry_basis?.label
            ? t("mls.geometryFrozen", { label: pkg.geometry_basis.label })
            : t("mls.derivedFrom", { id: String(pkg.run_id || "").slice(0, 8) })}
        </div>
      </div>
    </div>
    </>
  );
}
