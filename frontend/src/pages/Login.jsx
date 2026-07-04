import React, { useState } from "react";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useBranding } from "@/lib/branding";
import { useT } from "@/lib/i18n";
import { toast } from "sonner";
import LangToggle from "@/components/LangToggle";

const BG = "/login-ascend.png";

export default function Login() {
  const { user, login, register, error } = useAuth();
  const branding = useBranding();
  const t = useT();
  const nav = useNavigate();
  const loc = useLocation();
  const [params] = useSearchParams();
  const [mode, setMode] = useState(() =>
    (params.get("mode") || "").toLowerCase() === "register" ? "register" : "login"
  );
  const [email, setEmail] = useState(() => params.get("email") || "");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [signupCode, setSignupCode] = useState(() => params.get("code") || "");
  // Default to 'create' (new company) when prefilled from invitation, since the
  // supplier code only unlocks creating a new company. Stays 'create' otherwise.
  const [joinMode, setJoinMode] = useState("create"); // 'create' | 'join'
  const [busy, setBusy] = useState(false);

  React.useEffect(() => {
    if (user) nav(loc.state?.from?.pathname || "/", { replace: true });
  }, [user, nav, loc]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    let ok;
    if (mode === "login") {
      ok = await login(email, password);
    } else if (joinMode === "create") {
      ok = await register(email, password, name, companyName, undefined, signupCode);
    } else {
      ok = await register(email, password, name, undefined, inviteCode, undefined);
    }
    setBusy(false);
    if (ok) toast.success(mode === "login" ? t("common.welcomeBack") : t("common.accountCreated"));
  };

  const logoUrl = branding.supplier_logo_url
    ? `${process.env.REACT_APP_BACKEND_URL}${branding.supplier_logo_url}`
    : null;

  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-[var(--surface)]">
      <div className="absolute top-4 right-4 z-10">
        <LangToggle />
      </div>
      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm" data-testid="auth-card">
          <div className="flex items-center gap-3 mb-10">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt={branding.supplier_name}
                className="w-11 h-11 object-contain bg-[var(--bar-bg)]"
                data-testid="supplier-logo"
              />
            ) : (
              <div className="w-11 h-11 bg-[var(--bar-bg)] text-[var(--brand)] flex items-center justify-center font-heading text-xl">
                {(branding.supplier_name || "A").charAt(0)}
              </div>
            )}
            <div>
              <div className="font-heading text-xl text-[var(--ink)] leading-none" data-testid="supplier-name">
                {branding.supplier_name}
              </div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--muted)] mt-1">
                {t("auth.sidingEstimator")}
              </div>
            </div>
          </div>

          <div className="mb-7">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-2">
              {mode === "login" ? t("auth.welcomeBack") : t("auth.createAccount")}
            </div>
            <h1 className="font-heading text-3xl sm:text-4xl text-[var(--ink)] leading-tight">
              {mode === "login" ? t("auth.signIn") : t("auth.freeTagline")}
            </h1>
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <>
                <div>
                  <label className="label">{t("auth.yourName")}</label>
                  <input
                    className="input"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    data-testid="name-input"
                  />
                </div>

                <div className="border border-[var(--border)] p-3">
                  <div className="flex border-b border-[var(--border)] mb-3">
                    <button
                      type="button"
                      className={`flex-1 py-2 text-xs uppercase tracking-wider font-bold ${joinMode === "create" ? "text-[var(--brand-text)] border-b-2 border-[var(--brand)]" : "text-[var(--muted)]"}`}
                      onClick={() => setJoinMode("create")}
                      data-testid="mode-create-co"
                    >
                      {t("auth.newCompany")}
                    </button>
                    <button
                      type="button"
                      className={`flex-1 py-2 text-xs uppercase tracking-wider font-bold ${joinMode === "join" ? "text-[var(--brand-text)] border-b-2 border-[var(--brand)]" : "text-[var(--muted)]"}`}
                      onClick={() => setJoinMode("join")}
                      data-testid="mode-join-co"
                    >
                      {t("auth.joinTeammate")}
                    </button>
                  </div>
                  {joinMode === "create" ? (
                    <>
                      <div className="mb-3">
                        <label className="label">{t("auth.yourCompanyName")}</label>
                        <input
                          className="input"
                          type="text"
                          value={companyName}
                          onChange={(e) => setCompanyName(e.target.value)}
                          placeholder={t("auth.companyNamePlaceholder")}
                          required
                          data-testid="company-name-input"
                        />
                      </div>
                      <div>
                        <label className="label">{t("auth.accessCodeFrom", { supplier: branding.supplier_name })}</label>
                        <input
                          className="input font-mono-num uppercase tracking-wider"
                          type="text"
                          value={signupCode}
                          onChange={(e) => setSignupCode(e.target.value.toUpperCase())}
                          placeholder={t("auth.accessCodePlaceholder")}
                          required
                          data-testid="signup-code-input"
                        />
                        <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mt-1">
                          {branding.supplier_tagline}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div>
                      <label className="label">{t("auth.teammateInviteCode")}</label>
                      <input
                        className="input font-mono-num uppercase tracking-wider"
                        type="text"
                        value={inviteCode}
                        onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                        placeholder={t("auth.invitePlaceholder")}
                        required={joinMode === "join"}
                        data-testid="invite-code-input"
                      />
                      <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mt-1">
                        {t("auth.inviteHelp")}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}

            <div>
              <label className="label">{t("auth.email")}</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                data-testid="email-input"
              />
            </div>
            <div>
              <label className="label">{t("auth.password")}</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                data-testid="password-input"
              />
            </div>
            {error && (
              <div className="text-sm text-[var(--danger)] border border-[var(--danger)]/30 bg-[var(--danger-soft)] px-3 py-2" data-testid="auth-error">
                {error}
              </div>
            )}
            <button
              type="submit"
              className="btn-primary w-full"
              disabled={busy}
              data-testid="auth-submit-btn"
            >
              {busy ? t("common.pleaseWait") : mode === "login" ? t("auth.signInBtn") : t("auth.createBtn")}
            </button>
          </form>

          <div className="text-sm text-[var(--ink-2)] mt-6">
            {mode === "login" ? (
              <>
                {t("auth.needAccount")}{" "}
                <button
                  className="font-semibold text-[var(--ink)] underline underline-offset-4 decoration-[var(--brand)]"
                  onClick={() => setMode("register")}
                  data-testid="switch-register"
                >
                  {t("auth.register")}
                </button>
              </>
            ) : (
              <>
                {t("auth.alreadyHaveOne")}{" "}
                <button
                  className="font-semibold text-[var(--ink)] underline underline-offset-4 decoration-[var(--brand)]"
                  onClick={() => setMode("login")}
                  data-testid="switch-login"
                >
                  {t("auth.signInBtn")}
                </button>
              </>
            )}
          </div>

          <div className="mt-10 text-[11px] text-[var(--muted)] uppercase tracking-widest">
            {t("auth.providedBy", { supplier: branding.supplier_name })}
          </div>
          <div className="mt-4 text-[10px] text-[var(--muted)] flex items-center gap-3">
            <span>© {new Date().getFullYear()} Pro-Quote Estimating Tool</span>
            <span aria-hidden="true">·</span>
            <a href="/terms" className="hover:text-[var(--ink)]" data-testid="login-terms-link">Terms</a>
            <span aria-hidden="true">·</span>
            <a href="/privacy" className="hover:text-[var(--ink)]" data-testid="login-privacy-link">Privacy</a>
          </div>
        </div>
      </div>
      <div
        className="hidden md:block bg-contain bg-center bg-no-repeat bg-[var(--surface)]"
        style={{ backgroundImage: `url(${BG})` }}
        aria-hidden="true"
      />
    </div>
  );
}
