import React, { useState, useRef, useMemo } from "react";
import { fmt } from "@/lib/api";
import { useCompany } from "@/lib/company";
import { useBranding } from "@/lib/branding";
import { useAuth } from "@/lib/auth";
import { useLang, useT, tFor } from "@/lib/i18n";
import { gateBlockMessage } from "@/lib/gateMessages";
import CompanyLogo from "@/components/CompanyLogo";
import { X, Printer, Send } from "lucide-react";
import { buildEmailHtml, buildEmailSubject, defaultEmailGreeting } from "@/lib/emailQuote";
import { tSection, tItem, tUnit } from "@/lib/catalogTranslations";
import { isValidEmail } from "@/lib/validate";
import { useReadiness } from "@/components/estimate/ReadinessPanel";
import TapeNudgeCard from "@/components/estimate/TapeNudgeCard";

export default function QuoteModal({ estimate, totals, onClose, emailConfigured, onEmail, derivedUnapplied, onRederived }) {
  const { company } = useCompany();
  const branding = useBranding();
  const { user } = useAuth();
  const { readiness } = useReadiness(estimate?.id);
  // PRINT-BLOCKED (authorized 2026-07-28): hard gate on the homeowner surface.
  // ONE TRUTH (Howard ruled 2026-08-04): the backend stamps every readiness
  // item with its registry tier + blocking flag — the modal reads the SAME
  // flag the gate chips read (quote-tier items block; order-tier items like
  // field-verify ambers stay visible but never gate the quote; LABOR
  // UNDECIDED never blocks, re-ruled 2026-07-29).
  const laborItem = (readiness?.items || []).find((i) => i.kind === "labor_pending");
  const blockingItems = (readiness?.items || []).filter((i) => i.blocking);
  const blocked = blockingItems.length > 0;
  const { lang: uiLang } = useLang();
  const t = useT();
  // Iter 79j.47 — Two-way email sync. Prefill the recipient input
  // from the estimate's own contact fields (customer_email preferred,
  // then legacy recipient_email). If neither is set, leave blank and
  // show a note that whatever is entered here will be saved back to
  // the estimate after send.
  const [email, setEmail] = useState(
    () => (estimate?.customer_email || estimate?.recipient_email || "").trim(),
  );
  const noStoredEmail = !((estimate?.customer_email || "").trim());
  // Iter 79j.49 — Soft-warn on invalid recipient; also gates Send.
  // The backend uses EmailStr and would reject a malformed address
  // with a 422 anyway — fail helpfully in the UI first.
  const emailInvalid = !!email && !isValidEmail(email);
  // Per-estimate send language — defaults to the contractor's current UI lang,
  // but the contractor can flip it before sending. Note for the contractor only:
  // the message body resets when they change languages so they don't accidentally
  // send a Spanish quote with an English greeting.
  const [sendLang, setSendLang] = useState(uiLang);
  const [message, setMessage] = useState(() =>
    defaultEmailGreeting({ estimate, company, lang: uiLang })
  );
  const [sending, setSending] = useState(false);
  // Clarity ruling (Cluster A): sending a quote while the LP takeoff is
  // derived-but-unapplied requires an explicit second confirmation.
  const [confirmArmed, setConfirmArmed] = useState(false);
  const printRef = useRef();
  const showSupplierFooter = company?.quote_footer_enabled !== false;

  // When the contractor flips EN/ES, refresh the greeting to match. We DON'T
  // overwrite the message if they've already customized it (i.e. it differs
  // from the last default we generated). Capture the old default BEFORE
  // mutating the ref so the setMessage callback compares against the right value.
  const lastDefaultRef = useRef(defaultEmailGreeting({ estimate, company, lang: uiLang }));
  React.useEffect(() => {
    const oldDefault = lastDefaultRef.current;
    const nextDefault = defaultEmailGreeting({ estimate, company, lang: sendLang });
    lastDefaultRef.current = nextDefault;
    setMessage((prev) => (prev === oldDefault ? nextDefault : prev));
  }, [sendLang, estimate, company]);

  const subject = useMemo(
    () => buildEmailSubject({ estimate, company, lang: sendLang }),
    [estimate, company, sendLang]
  );

  // Stable accept token for this customer-facing quote. Reuse any existing one
  // saved on the estimate (so the link stays valid across re-sends) or mint a
  // fresh UUID4 client-side.
  const acceptToken = useMemo(
    () => estimate.accept_token || (typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`),
    [estimate.accept_token]
  );
  // Tack the language onto the accept link so the customer's hosted page
  // matches the language of their email/PDF.
  const acceptUrl = `${window.location.origin}/accept/${acceptToken}?lang=${sendLang}`;

  const linesWithQty = (estimate.lines || []).filter((l) => (l.qty || 0) > 0);
  // Group by TAB first, then by section within each tab. Some section names
  // (e.g. "Siding Accessories", "Vinyl Soffit with Siding", "Misc.") are
  // used on both the Vinyl and Ascend tabs — without the tab-level grouping
  // their items would land in one mixed bucket, which is what Howard hit
  // when he ran a hybrid Vinyl + Ascend estimate.
  const TAB_LABEL = {
    vinyl: "Vinyl Siding",
    ascend: "Ascend Composite Siding",
    lp_smart: "LP SmartSide",
    windows: "Windows",
    iss: "ISS Siding",
  };
  const TAB_ORDER = ["vinyl", "ascend", "lp_smart", "windows", "iss"];
  const linesByTab = linesWithQty.reduce((acc, l) => {
    const tab = l.tab || "vinyl";
    (acc[tab] = acc[tab] || {});
    (acc[tab][l.section] = acc[tab][l.section] || []).push(l);
    return acc;
  }, {});
  const tabOrder = TAB_ORDER.filter((t) => linesByTab[t]);

  const handleEmail = async () => {
    if (blocked) return;
    if (!email) return;
    if (derivedUnapplied && !confirmArmed) {
      setConfirmArmed(true);
      return;
    }
    setSending(true);
    // Build an email-safe HTML (inline styles, table layout) instead of dumping the on-screen DOM.
    const html = buildEmailHtml({
      estimate,
      totals,
      company,
      branding,
      message,
      acceptUrl,
      acceptEmail: user?.email,
      lang: sendLang,
    });
    const ok = await onEmail({ recipient_email: email, html, subject, accept_token: acceptToken });
    setSending(false);
    if (ok) onClose();
  };

  const handleDownloadPdf = async () => {
    if (blocked) return;
    setSending(true);
    try {
      const html = buildEmailHtml({
        estimate, totals, company, branding, message,
        acceptUrl,
        acceptEmail: user?.email,
        lang: sendLang,
      });
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/estimates/${estimate.id}/pdf`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ recipient_email: "noreply@noreply.com", html_quote: html }),
        }
      );
      if (!res.ok) throw new Error(await gateBlockMessage(res, t));
      const blob = await res.blob();
      // Pull filename from Content-Disposition if present
      const dispo = res.headers.get("content-disposition") || "";
      const match = dispo.match(/filename="?([^";]+)"?/);
      const filename = match ? match[1] : `estimate-${estimate.estimate_number || estimate.id}.pdf`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      window.alert(e.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-[#09090B]/70 backdrop-blur-sm overflow-y-auto" data-testid="quote-modal">
      <div className="min-h-screen flex flex-col items-center py-6 sm:py-10 px-4">
        {/* PRINT-BLOCKED GATE (authorized 2026-07-28, supersedes the
            2026-07-23 soft-only ruling for the homeowner surface): a
            half-walked quote can't reach a homeowner by construction —
            send + PDF stay disabled while readiness items stand. */}
        {blocked && (
          <div className="no-print w-full max-w-3xl mb-3 bg-[#FEF2F2] border border-[#DC2626] px-4 py-3" data-testid="quote-print-blocked-banner">
            <div className="text-xs font-bold text-[#991B1B] mb-1">
              {t("quote.printBlocked", { n: blockingItems.length })}
            </div>
            <ul className="space-y-0.5">
              {blockingItems.slice(0, 6).map((it, i) => (
                <li key={i} className="text-[11px] text-[#991B1B]" data-testid="quote-readiness-item">• {it.label}</li>
              ))}
              {blockingItems.length > 6 && (
                <li className="text-[11px] text-[#991B1B]">{t("quote.printBlockedMore", { n: blockingItems.length - 6 })}</li>
              )}
            </ul>
          </div>
        )}
        {(() => {
          const refused = (estimate.lines || []).filter((l) => l?.not_derivable);
          if (refused.length === 0) return null;
          return (
            <div className="no-print w-full max-w-3xl mb-3 bg-[#FEF2F2] border border-[#DC2626] px-4 py-3" data-testid="quote-incomplete-banner">
              <div className="text-xs font-bold text-[#991B1B] mb-1">
                {`INCOMPLETE — ${refused.length} line(s) refused (Ruling L: not a price)`}
              </div>
              <ul className="space-y-0.5">
                {refused.map((l, i) => (
                  <li key={i} className="text-[11px] text-[#991B1B]" data-testid="quote-refused-line">
                    • {l.name}: {l.not_derivable_reason || "REFUSED"}
                  </li>
                ))}
              </ul>
            </div>
          );
        })()}
        {/* SEND-111 order item 3 — QUOTE TAPE NUDGE: the refusal coach
            landing on the surface a contractor actually looks at. A
            refused row gets its one field tape right where the price is
            read; the card renders only when Ruling-V refusals exist. */}
        {(estimate.lines || []).some((l) => l?.not_derivable) && (
          <div className="no-print w-full max-w-3xl" data-testid="quote-tape-nudge-wrap">
            <TapeNudgeCard est={estimate} onRederived={onRederived} />
          </div>
        )}
        {/* LABOR UNDECIDED — one line, a count, never a block (re-ruled 2026-07-29) */}
        {laborItem && (
          <div className="no-print w-full max-w-3xl mb-3 bg-[#FFFBEB] border border-[#D97706] px-4 py-2 text-[11px] text-[#92400E]" data-testid="quote-labor-undecided-line">
            {laborItem.label}
          </div>
        )}
        {/* Floating action bar */}
        <div className="no-print w-full max-w-3xl flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
          <div className="flex flex-col md:flex-1 gap-1">
            <div className="flex flex-col md:flex-row md:items-center gap-2">
              <input
                type="email"
                className="input bg-white h-12 md:h-9 text-base md:text-sm"
                placeholder={t("quote.recipientPlaceholder")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={emailInvalid}
                aria-describedby={emailInvalid ? "quote-email-warn" : undefined}
                autoComplete="off"
                data-testid="email-recipient"
                style={{ minWidth: 240 }}
              />
              <button
                className="btn-primary h-12 md:h-9 justify-center md:justify-start"
                onClick={handleEmail}
                disabled={!email || sending || !emailConfigured || emailInvalid || blocked}
                data-testid="send-email-btn"
                title={blocked ? t("quote.printBlockedTooltip") : (!emailConfigured ? "Add RESEND_API_KEY in backend/.env to enable" : "")}
              >
                <Send className="w-4 h-4" /> {sending ? t("quote.sending") : t("quote.emailBtn")}
              </button>
            </div>
            {confirmArmed && (
              <div className="flex flex-wrap items-center gap-2 bg-[#FFFBEB] border border-[#F59E0B] px-3 py-2" data-testid="quote-send-gate">
                <span className="text-[11px] font-bold text-[#92400E]">
                  This estimate carries a derived takeoff that has not been applied — the quote and Accept page render applied lines only ({fmt(totals.sell)}). Send anyway?
                </span>
                <button type="button" onClick={handleEmail} className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider bg-[#92400E] text-white" data-testid="quote-send-gate-confirm">
                  Confirm send
                </button>
                <button type="button" onClick={() => setConfirmArmed(false)} className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider border border-[#92400E] text-[#92400E]" data-testid="quote-send-gate-cancel">
                  Cancel
                </button>
              </div>
            )}
            {emailInvalid && (
              <div
                id="quote-email-warn"
                role="alert"
                className="text-[11px] font-bold text-[var(--warning-text)]"
                data-testid="quote-email-warn"
              >
                {t("est.warnEmail")}
              </div>
            )}
            {!emailInvalid && noStoredEmail && (
              <div className="text-[10px] text-white/70 md:text-[var(--muted)]" data-testid="quote-email-will-save">
                {t("quote.emailWillSave")}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 justify-between md:justify-end">
            <button
              className="btn-secondary h-12 md:h-9 flex-1 md:flex-none justify-center md:justify-start"
              onClick={handleDownloadPdf}
              disabled={sending || blocked}
              data-testid="download-pdf-btn"
              title={blocked ? t("quote.printBlockedTooltip") : t("quote.downloadPdf")}
            >
              <Printer className="w-4 h-4" /> {sending ? "…" : t("quote.downloadPdf")}
            </button>
            <button
              className="btn-ghost text-white hover:text-white p-3 md:p-1"
              onClick={onClose}
              data-testid="quote-close-btn"
              aria-label={t("common.close")}
            >
              <X className="w-6 h-6 md:w-5 md:h-5" />
            </button>
          </div>
        </div>

        {/* Editable email preamble + send-language picker */}
        <div className="no-print w-full max-w-3xl mb-4 bg-white border border-[#E4E4E7] p-4" data-testid="email-preamble">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] font-bold">
              {t("quote.subject")}
            </div>
            <div className="flex items-center gap-2" data-testid="send-lang-picker">
              <span className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] font-bold">
                {t("quote.langPicker")}
              </span>
              <div className="inline-flex border border-[#E4E4E7] rounded-sm overflow-hidden text-[11px] font-bold uppercase tracking-wider">
                <button
                  type="button"
                  onClick={() => setSendLang("en")}
                  className={`px-2.5 py-1 ${sendLang === "en" ? "bg-[#09090B] text-white" : "bg-white text-[#52525B] hover:bg-[#F4F4F5]"}`}
                  data-testid="send-lang-en"
                >EN</button>
                <button
                  type="button"
                  onClick={() => setSendLang("es")}
                  className={`px-2.5 py-1 border-l border-[#E4E4E7] ${sendLang === "es" ? "bg-[#09090B] text-white" : "bg-white text-[#52525B] hover:bg-[#F4F4F5]"}`}
                  data-testid="send-lang-es"
                >ES</button>
              </div>
            </div>
          </div>
          <div className="text-sm font-mono-num text-[#09090B] mb-3 break-words">{subject}</div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] font-bold mb-1">
            {t("quote.personalNote")}
          </div>
          <textarea
            className="input w-full"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t("quote.personalNote")}
            data-testid="email-message"
            style={{ resize: "vertical", minHeight: 96 }}
          />
          <div className="text-[11px] text-[#71717A] mt-1">
            {t("quote.personalNoteHelp")}
          </div>
        </div>
        {!emailConfigured && (
          <div className="no-print w-full max-w-3xl mb-3 text-xs text-amber-200 bg-amber-900/40 border border-amber-200/40 px-3 py-2">
            {t("quote.emailNotConfigured")}
          </div>
        )}

        {/* The printable quote */}
        <div
          ref={printRef}
          className="quote-page w-full max-w-3xl bg-white shadow-xl border border-[#09090B]"
          data-testid="quote-page"
        >
          <div className="border-b-4 border-[#F97316] px-8 sm:px-12 py-8 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <CompanyLogo company={company} size={56} />
              <div>
                <div className="font-heading text-2xl text-[#09090B]" style={{ minHeight: "1em" }}>
                  {company?.name || "\u00A0"}
                </div>
                <div className="text-xs uppercase tracking-[0.25em] text-[#52525B]">
                  {tFor(sendLang, "quote.docSubtitle")}
                </div>
                {derivedUnapplied && (
                  <div className="mt-1 text-[10px] font-bold uppercase tracking-wider text-[#92400E] bg-[#FFFBEB] border border-[#F59E0B] px-2 py-0.5 inline-block" data-testid="quote-not-ready">
                    Not ready — takeoff derived but not applied; this quote renders applied lines only
                  </div>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-[0.25em] text-[#71717A]">{tFor(sendLang, "email.estimate")}</div>
              <div className="font-mono-num text-lg text-[#09090B]">{estimate.estimate_number}</div>
              <div className="text-xs text-[#52525B]">{estimate.estimate_date}</div>
            </div>
          </div>

          <div className="px-8 sm:px-12 py-6 grid grid-cols-2 gap-6 border-b border-[#E4E4E7]">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] mb-1 font-bold">
                {tFor(sendLang, "email.preparedFor")}
              </div>
              {/* Iter 79j.47 — Company name (bold) sits above the
                  customer name when set; contact chip line below the
                  address; billing address only if it differs. Lead
                  source, fax, and preferred contact are contractor-
                  internal — never rendered on customer documents. */}
              {estimate.customer_company && (
                <div className="font-semibold text-[#09090B]" data-testid="quote-prepared-company">
                  {estimate.customer_company}
                </div>
              )}
              <div className={`text-[#09090B] ${estimate.customer_company ? "" : "font-semibold"}`}>
                {estimate.customer_name || "—"}
              </div>
              <div className="text-sm text-[#52525B]">{estimate.address || ""}</div>
              {(estimate.customer_phone || estimate.customer_email) && (
                <div className="text-xs text-[#52525B] mt-1" data-testid="quote-prepared-contact">
                  {[estimate.customer_phone, estimate.customer_email].filter(Boolean).join(" · ")}
                </div>
              )}
              {(estimate.billing_address || "").trim() && (
                <div className="text-xs text-[#52525B] mt-1" data-testid="quote-prepared-billing">
                  <span className="uppercase tracking-wider text-[10px] font-bold text-[#71717A]">{tFor(sendLang, "email.billing")}:</span> {estimate.billing_address}
                </div>
              )}
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] mb-1 font-bold">
                {tFor(sendLang, "email.estimator")}
              </div>
              <div className="font-semibold text-[#09090B]">{estimate.estimator || "—"}</div>
            </div>
          </div>

          {estimate.notes && (
            <div className="px-8 sm:px-12 py-5 border-b border-[#E4E4E7]">
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] mb-2 font-bold">
                {tFor(sendLang, "email.scopeOfWork")}
              </div>
              <div className="text-sm whitespace-pre-line text-[#09090B]">{estimate.notes}</div>
            </div>
          )}

          {/* Iter 71 — Per-Elevation Siding Breakdown card. Renders when
              HOVER import populated `hover_measurements.per_elevation_siding`.
              Mirrors the same block in `buildEmailHtml` so the on-screen
              preview matches the customer-facing email/PDF. */}
          {(() => {
            const elev = estimate.hover_measurements?.per_elevation_siding;
            if (!elev) return null;
            const entries = Object.entries(elev).filter(([, v]) => Number(v) > 0);
            if (entries.length === 0) return null;
            const total = entries.reduce((s, [, v]) => s + Number(v || 0), 0);
            const labels = {
              front: tFor(sendLang, "email.elevationFront"),
              back: tFor(sendLang, "email.elevationBack"),
              left: tFor(sendLang, "email.elevationLeft"),
              right: tFor(sendLang, "email.elevationRight"),
            };
            return (
              <div className="px-8 sm:px-12 py-5 border-b border-[#E4E4E7]" data-testid="per-elevation-card">
                <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] mb-3 font-bold">
                  {tFor(sendLang, "email.elevationTitle")}
                </div>
                <table className="w-full text-sm">
                  <tbody>
                    {entries.map(([key, sqft]) => {
                      const pct = total > 0 ? Math.round((Number(sqft) / total) * 100) : 0;
                      return (
                        <tr key={key} className="border-b border-[#E4E4E7]">
                          <td className="py-2 text-[#09090B] w-[28%]">{labels[key] || key}</td>
                          <td className="py-2 px-2 w-[52%]">
                            <div className="h-1.5 bg-[#E4E4E7] w-full">
                              <div className="h-1.5 bg-[#F97316]" style={{ width: `${pct}%` }} />
                            </div>
                          </td>
                          <td className="py-2 text-right text-[#09090B] font-semibold font-mono-num whitespace-nowrap w-[20%]">
                            {Math.round(Number(sqft)).toLocaleString()} ft²
                            <span className="text-[#71717A] font-normal"> · {pct}%</span>
                          </td>
                        </tr>
                      );
                    })}
                    <tr>
                      <td className="pt-3 text-[#52525B] font-semibold">{tFor(sendLang, "email.elevationTotal")}</td>
                      <td></td>
                      <td className="pt-3 text-right text-[#09090B] font-bold font-mono-num whitespace-nowrap">
                        {Math.round(total).toLocaleString()} ft²
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            );
          })()}

          <div className="px-8 sm:px-12 py-6">
            {tabOrder.map((tabId) => (
              <div key={tabId} className="mb-6">
                <div className="text-[10px] uppercase tracking-[0.25em] font-bold text-[#71717A] mb-2">
                  {tSection(TAB_LABEL[tabId], sendLang)}
                </div>
                {Object.entries(linesByTab[tabId]).map(([section, items]) => (
                  <div key={section} className="mb-4">
                    <div className="text-xs uppercase tracking-[0.18em] font-bold text-[#C2410C] border-b border-[#09090B] pb-1 mb-2">
                      {tSection(section, sendLang)}
                    </div>
                    {items.map((l) => (
                      <React.Fragment key={l.name}>
                        <div className="flex justify-between py-1 text-sm">
                          <span className="text-[#09090B]">{tItem(l.name, sendLang)}</span>
                          <span className="text-[#52525B] font-mono-num text-right">
                            {l.qty} {tUnit(l.unit, sendLang)}
                            {l.pricing_pending && (
                              <span className="block text-[10px] uppercase tracking-wider font-bold text-[#B45309]" data-testid={`quote-line-pending-${l.name}`}>
                                {tFor(sendLang, "email.pricePending")}
                              </span>
                            )}
                          </span>
                        </div>
                        {(l.adders || [])
                          .filter((a) => (Number(a.qty) || 0) > 0)
                          .map((a) => (
                            <div key={a.name} className="flex justify-between py-0.5 pl-4 text-xs text-[#52525B]" data-testid={`quote-adder-${l.name}-${a.name}`}>
                              <span>+ {tItem(a.name, sendLang)}</span>
                              <span className="text-[#71717A] font-mono-num">× {a.qty}</span>
                            </div>
                          ))}
                      </React.Fragment>
                    ))}
                  </div>
                ))}
              </div>
            ))}
            {/* Ruled (d/b): window openings itemize on the customer quote —
                mirrors the windowsBlock in buildEmailHtml. Qty only, no
                unit prices; adders as indented sub-lines. */}
            {(() => {
              const ops = [
                ...(estimate.vero_openings || []),
                ...(estimate.mezzo_openings || []),
              ].filter((op) => (Number(op.qty) || 0) > 0);
              if (ops.length === 0) return null;
              const dispName = (op) => {
                const dims =
                  (Number(op.width) || 0) > 0 && (Number(op.height) || 0) > 0
                    ? `${op.width}\u2033 × ${op.height}\u2033`
                    : op.model || "";
                return [op.product_type, op.label && `\u201C${op.label}\u201D`, dims]
                  .filter(Boolean)
                  .join(" — ");
              };
              return (
                <div className="mb-6" data-testid="quote-windows-openings">
                  <div className="text-xs uppercase tracking-[0.18em] font-bold text-[#C2410C] border-b border-[#09090B] pb-1 mb-2">
                    {tFor(sendLang, "email.windowsOpenings")}
                  </div>
                  {ops.map((op) => (
                    <React.Fragment key={op.id || dispName(op)}>
                      <div className="flex justify-between py-1 text-sm">
                        <span className="text-[#09090B]">{dispName(op)}</span>
                        <span className="text-[#52525B] font-mono-num">{op.qty} {tUnit("Each", sendLang)}</span>
                      </div>
                      {(op.adders || [])
                        .filter((a) => (Number(a.qty) || 0) > 0)
                        .map((a) => (
                          <div key={a.name} className="flex justify-between py-0.5 pl-4 text-xs text-[#52525B]" data-testid={`quote-opening-adder-${a.name}`}>
                            <span>+ {tItem(a.name, sendLang)}</span>
                            <span className="text-[#71717A] font-mono-num">× {a.qty}</span>
                          </div>
                        ))}
                    </React.Fragment>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Quote visual: NONE (ruled 2026-07-20) — the 3D model block was
              removed; the customer quote ships with no picture and the
              layout closes up cleanly. Homeowners who want a visual use the
              LP/Alside visualizer outside the quote. */}

          {(estimate.photos || []).length > 0 && (
            <div className="px-8 sm:px-12 py-4 border-t border-[#E4E4E7]">
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] mb-3 font-bold">
                {tFor(sendLang, "email.jobPhotos")}
              </div>
              <div className="grid grid-cols-3 gap-3">
                {estimate.photos.map((p, i) => (
                  <img
                    key={`${p}-${i}`}
                    src={`${process.env.REACT_APP_BACKEND_URL}${p}`}
                    alt=""
                    className="aspect-square object-cover border border-[#E4E4E7]"
                  />
                ))}
              </div>
            </div>
          )}

          <div className="px-8 sm:px-12 py-6 border-t-4 border-[#09090B] bg-[#FAFAFA]">
            <div className="flex justify-between items-baseline">
              <div className="font-heading text-2xl text-[#09090B]">{tFor(sendLang, "email.total")}</div>
              <div className="font-mono-num text-4xl font-black text-[#09090B]">
                {fmt(totals.sell)}
              </div>
            </div>
            {linesWithQty.some((l) => l.pricing_pending) && (
              <div className="text-xs text-[#B45309] mt-2" data-testid="quote-pending-note">
                {tFor(sendLang, "email.pendingNote")}
              </div>
            )}
            <div className="text-xs text-[#52525B] mt-2">
              {tFor(sendLang, "email.validityGeneric")}
            </div>
          </div>

          <div className="px-8 sm:px-12 py-8 grid grid-cols-2 gap-8">
            <div>
              <div className="border-b border-[#09090B] h-8" />
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] mt-1 font-bold">
                {tFor(sendLang, "quote.signature")}
              </div>
            </div>
            <div>
              <div className="border-b border-[#09090B] h-8" />
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A] mt-1 font-bold">
                {tFor(sendLang, "quote.dateSigned")}
              </div>
            </div>
          </div>

          {showSupplierFooter && (
            <div
              className="border-t border-[#E4E4E7] px-8 sm:px-12 py-3 text-[10px] uppercase tracking-[0.2em] text-[#71717A] text-center"
              data-testid="supplier-footer"
            >
              {tFor(sendLang, "email.materialsBy", { supplier: branding.supplier_name })} · {tFor(sendLang, "email.poweredBy")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

