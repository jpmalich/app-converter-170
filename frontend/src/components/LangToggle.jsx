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
  const activeLight = "bg-[#09090B] text-white";
  const inactiveLight = "bg-white text-[#52525B] hover:bg-[#F4F4F5]";
  const activeDark = "bg-[#F97316] text-white";
  const inactiveDark = "bg-transparent text-white/70 hover:text-white";

  const border = isDark ? "border border-white/20" : "border border-[#E4E4E7]";

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
        className={`${base} ${isDark ? "border-l border-white/20" : "border-l border-[#E4E4E7]"} ${
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
