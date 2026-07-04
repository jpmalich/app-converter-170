// Iter 79j.46 — ThemePicker.
//
// Palette-icon button (btn-ghost) → Radix Popover with a role=radiogroup
// list. Each row = 3-dot swatch + theme label + check on active.
// Instant apply on click, aria-live status announcement.
//
// - `inline` prop renders the same list WITHOUT the popover chrome —
//   used on the Team page settings card.
// - Bilingual labels via useT() so the picker respects the current
//   lang without re-mounting.
import React, { useCallback, useEffect, useState } from "react";
import { Palette, Check } from "lucide-react";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "./ui/popover";
import { useT } from "../lib/i18n";
import {
  THEMES,
  readStoredTheme,
  setTheme as persistTheme,
  applyTheme,
} from "../lib/themes";

function Swatch({ colors }) {
  // Three overlapping dots that hint at brand / surface / ink so the
  // contractor can preview each theme without applying it.
  return (
    <span
      aria-hidden="true"
      className="inline-flex items-center flex-shrink-0"
      style={{ width: 30, height: 12 }}
    >
      {colors.map((c, i) => (
        <span
          key={i}
          style={{
            width: 12,
            height: 12,
            borderRadius: 999,
            background: c,
            border: "1px solid rgba(0,0,0,0.15)",
            marginLeft: i === 0 ? 0 : -4,
          }}
        />
      ))}
    </span>
  );
}

function ThemeList({ current, onPick, t }) {
  return (
    <div
      role="radiogroup"
      aria-label={t("theme.toggle.aria")}
      className="flex flex-col"
      data-testid="theme-picker-radiogroup"
    >
      {THEMES.map((th) => {
        const active = current === th.id;
        return (
          <button
            key={th.id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onPick(th.id)}
            className={`flex items-center gap-3 px-3 py-2 text-sm text-left transition-colors ${
              active
                ? "bg-[var(--ai-soft)] text-[var(--ink)]"
                : "text-[var(--ink-2)] hover:bg-[var(--surface-muted)] hover:text-[var(--ink)]"
            }`}
            data-testid={`theme-option-${th.id}`}
          >
            <Swatch colors={th.swatch} />
            <span className="flex-1">{t(th.labelKey)}</span>
            {active && <Check className="w-4 h-4 text-[var(--brand-text)]" aria-hidden="true" />}
          </button>
        );
      })}
    </div>
  );
}

export default function ThemePicker({ inline = false }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState(() => readStoredTheme());
  const [statusMsg, setStatusMsg] = useState("");

  useEffect(() => {
    // On mount, ensure the DOM reflects storage (FOUC guard already
    // applied it, this is a safety re-apply after JS boot).
    applyTheme(current);
  }, [current]);

  const onPick = useCallback(
    (id) => {
      setCurrent(id);
      persistTheme(id);
      const name = t(THEMES.find((x) => x.id === id)?.labelKey);
      setStatusMsg(t("theme.status", { name }));
      if (!inline) setOpen(false);
    },
    [t, inline],
  );

  const activeLabel = t(THEMES.find((x) => x.id === current)?.labelKey);

  if (inline) {
    return (
      <div className="card p-4" data-testid="theme-picker-inline">
        <div className="label mb-2">{t("theme.toggle.aria")}</div>
        <ThemeList current={current} onPick={onPick} t={t} />
        <p className="text-xs text-[var(--muted)] mt-3 leading-relaxed" data-testid="theme-picker-blurb">
          {t("theme.blurb")}
        </p>
        <div className="sr-only" aria-live="polite" role="status">
          {statusMsg}
        </div>
      </div>
    );
  }

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="btn-ghost"
            aria-label={t("theme.toggle.aria")}
            title={`${t("theme.toggle.aria")} — ${activeLabel}`}
            data-testid="theme-picker-trigger"
          >
            <Palette className="w-4 h-4" aria-hidden="true" />
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="end"
          sideOffset={6}
          className="w-56 p-1 bg-[var(--surface)] border border-[var(--border)]"
          data-testid="theme-picker-popover"
        >
          <ThemeList current={current} onPick={onPick} t={t} />
        </PopoverContent>
      </Popover>
      <div className="sr-only" aria-live="polite" role="status" data-testid="theme-picker-status">
        {statusMsg}
      </div>
    </>
  );
}
