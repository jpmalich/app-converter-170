import React, { useEffect, useState } from "react";
import { Smartphone, X, Share, Plus } from "lucide-react";

const DISMISS_KEY = "install-banner-dismissed-v1";

function detectPlatform() {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent || "";
  // iPad masquerades as Mac on iPadOS 13+ — also check for touch points
  const isIPad =
    /iPad/i.test(ua) ||
    (navigator.maxTouchPoints > 1 && /Macintosh/i.test(ua));
  if (isIPad) return "ipad";
  if (/iPhone|iPod/i.test(ua)) return "ios";
  if (/Android/i.test(ua)) return "android";
  return "other";
}

function isStandalone() {
  if (typeof window === "undefined") return false;
  // Chrome/Android signals via display-mode; iOS Safari uses navigator.standalone
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    window.navigator?.standalone === true
  );
}

export default function InstallBanner() {
  const [visible, setVisible] = useState(false);
  const [platform, setPlatform] = useState("unknown");
  const [showHelp, setShowHelp] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isStandalone()) return; // already installed
    if (window.localStorage?.getItem(DISMISS_KEY) === "1") return;

    const p = detectPlatform();
    // Only show on phones — iPad/desktop already have a great layout.
    if (p !== "ios" && p !== "android") return;

    setPlatform(p);

    // For Android/Chrome, capture the native prompt event so we can fire it on click.
    const onBeforeInstall = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);

    // Defer the banner so it doesn't compete with the initial render.
    const t = setTimeout(() => setVisible(true), 1200);

    return () => {
      clearTimeout(t);
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
    };
  }, []);

  const dismiss = () => {
    setVisible(false);
    setShowHelp(false);
    try {
      window.localStorage?.setItem(DISMISS_KEY, "1");
    } catch { /* ignore */ }
  };

  const handleInstall = async () => {
    if (deferredPrompt) {
      // Android / Chrome native install flow
      deferredPrompt.prompt();
      try {
        await deferredPrompt.userChoice;
      } catch { /* ignore */ }
      setDeferredPrompt(null);
      dismiss();
    } else {
      // iOS or Android-without-native-prompt → show step-by-step instructions
      setShowHelp(true);
    }
  };

  if (!visible) return null;

  return (
    <>
      <div
        className="fixed bottom-0 left-0 right-0 z-40 md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
        data-testid="install-banner"
        role="dialog"
        aria-label="Install on your phone"
      >
        <div className="bg-[var(--bar-bg)] text-white border-t-4 border-[var(--brand)] shadow-2xl">
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-10 h-10 rounded bg-[var(--brand)] flex items-center justify-center shrink-0">
              <Smartphone className="w-5 h-5 text-[var(--ink)]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold">Install on your phone</div>
              <div className="text-[11px] text-[var(--muted)] leading-snug">
                Add to your home screen for a faster, app-like experience.
              </div>
            </div>
            <button
              type="button"
              onClick={handleInstall}
              className="bg-[var(--brand)] text-[var(--on-brand)] text-xs font-bold uppercase tracking-wider px-3 py-2.5 hover:bg-[var(--brand-hover)] transition"
              data-testid="install-banner-action"
            >
              Install
            </button>
            <button
              type="button"
              onClick={dismiss}
              className="p-2 text-[var(--bar-muted)] hover:text-white"
              aria-label="Dismiss"
              data-testid="install-banner-dismiss"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {showHelp && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-end md:hidden"
          onClick={dismiss}
          data-testid="install-banner-help"
        >
          <div
            className="w-full bg-[var(--surface)] p-6 pt-7"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--brand-text)]">
                  3-Step Install
                </div>
                <h2 className="text-xl font-bold text-[var(--ink)] mt-1">
                  {platform === "ios" ? "On iPhone / iPad" : "On Android"}
                </h2>
              </div>
              <button
                type="button"
                onClick={dismiss}
                className="p-2 text-[var(--muted)] hover:text-[var(--ink)]"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {platform === "ios" ? (
              <ol className="space-y-3 text-sm text-[var(--ink)]">
                <Step
                  n={1}
                  label="Tap the Share icon"
                  detail="(It looks like a square with an up arrow.) It's at the bottom of Safari or top of the screen."
                  icon={<Share className="w-5 h-5" />}
                />
                <Step
                  n={2}
                  label='Choose "Add to Home Screen"'
                  detail='Scroll through the actions row and tap the one labeled "Add to Home Screen."'
                  icon={<Plus className="w-5 h-5" />}
                />
                <Step
                  n={3}
                  label="Tap Add"
                  detail="The app icon will appear on your home screen. Open it like any other app — no browser bar, no clutter."
                  icon={<Smartphone className="w-5 h-5" />}
                />
              </ol>
            ) : (
              <ol className="space-y-3 text-sm text-[var(--ink)]">
                <Step
                  n={1}
                  label="Open the Chrome menu"
                  detail="Tap the three vertical dots at the top right of Chrome."
                  icon={<Smartphone className="w-5 h-5" />}
                />
                <Step
                  n={2}
                  label='Tap "Add to Home screen" or "Install app"'
                  detail='Different Android versions show one or the other — both work.'
                  icon={<Plus className="w-5 h-5" />}
                />
                <Step
                  n={3}
                  label="Confirm Install"
                  detail="The app icon will appear on your home screen and launch full-screen, just like any other app."
                  icon={<Share className="w-5 h-5" />}
                />
              </ol>
            )}

            <button
              type="button"
              onClick={dismiss}
              className="mt-6 w-full bg-[var(--bar-bg)] text-white py-3 text-sm font-bold uppercase tracking-wider hover:bg-[#27272A] transition"
              data-testid="install-banner-help-close"
            >
              Got it
            </button>
            <p className="mt-3 text-[11px] text-[var(--muted)] text-center">
              You can re-open this app from your home screen any time.
            </p>
          </div>
        </div>
      )}
    </>
  );
}

function Step({ n, label, detail, icon }) {
  return (
    <li className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-[var(--brand)] text-[var(--on-brand)] font-bold text-sm flex items-center justify-center shrink-0">
        {n}
      </div>
      <div className="flex-1 pt-0.5">
        <div className="font-bold text-[var(--ink)] flex items-center gap-2">
          {label}
          <span className="text-[var(--muted)]">{icon}</span>
        </div>
        <div className="text-[var(--ink-2)] text-[13px] leading-snug mt-0.5">{detail}</div>
      </div>
    </li>
  );
}
