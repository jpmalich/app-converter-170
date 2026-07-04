import React from "react";
import { useLang } from "@/lib/i18n";

/**
 * Small EN/ES pill switch.
 * `tone="dark"` flips colors for use on dark headers/backgrounds.
 */
export default function LangToggle({ tone = "light", className = "" }) {
  const { lang, setLang, t } = useLang();
  const isDark = tone === "dark";

  const base =
    "px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition";
  const activeLight = "bg-[var(--bar-bg)] text-white";
  const inactiveLight = "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]";
  const activeDark = "bg-[var(--brand)] text-[var(--on-brand)]";
  const inactiveDark = "bg-transparent text-white/70 hover:text-white";

  const border = isDark ? "border border-white/20" : "border border-[var(--border)]";

  return (
    <div
      className={`inline-flex ${border} rounded-sm overflow-hidden ${className}`}
      role="group"
      aria-label={t("lang.toggle.aria")}
      data-testid="lang-toggle"
    >
      <button
        type="button"
        onClick={() => setLang("en")}
        className={`${base} ${
          lang === "en"
            ? isDark ? activeDark : activeLight
            : isDark ? inactiveDark : inactiveLight
        }`}
        aria-pressed={lang === "en"}
        data-testid="lang-en"
      >
        {t("lang.en")}
      </button>
      <button
        type="button"
        onClick={() => setLang("es")}
        className={`${base} ${isDark ? "border-l border-white/20" : "border-l border-[var(--border)]"} ${
          lang === "es"
            ? isDark ? activeDark : activeLight
            : isDark ? inactiveDark : inactiveLight
        }`}
        aria-pressed={lang === "es"}
        data-testid="lang-es"
      >
        {t("lang.es")}
      </button>
    </div>
  );
}
