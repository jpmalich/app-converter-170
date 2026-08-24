// SERVER-WAKING BANNER (Howard's bug report 2026-08-24): when the preview
// pod cold-starts, every /api route 404s from the ingress and the app used
// to silently render empty states over completed reads. The api client now
// health-probes and retries; THIS banner names the real state while it
// does — silence would mean nothing is wrong, and it is not.
import React, { useEffect, useState } from "react";
import { PlugZap } from "lucide-react";
import { useT } from "@/lib/i18n";

export default function ServerWakingBanner() {
  const t = useT();
  const [down, setDown] = useState(false);

  useEffect(() => {
    const onDown = () => setDown(true);
    const onUp = () => setDown(false);
    window.addEventListener("pq:backend-down", onDown);
    window.addEventListener("pq:backend-up", onUp);
    return () => {
      window.removeEventListener("pq:backend-down", onDown);
      window.removeEventListener("pq:backend-up", onUp);
    };
  }, []);

  if (!down) return null;
  return (
    <div
      data-testid="server-waking-banner"
      className="fixed top-0 inset-x-0 z-[100] flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-sm font-semibold text-black"
    >
      <PlugZap size={16} className="shrink-0" />
      {t("server.waking.msg")}
    </div>
  );
}
