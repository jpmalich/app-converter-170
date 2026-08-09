// STALE PAGE DETECTION (Howard ruled 2026-08-09): "SOMETHING WAS OUT OF
// DATE AND NOTHING REPORTED IT." If the loaded page is older than the
// deployed build, say so plainly and prompt a refresh. The client/server
// version pair is printed — a surface that silently disagrees with its
// own backend is a seam like any other (seam_accounting: client_build_stale).
// A network failure NEVER fires the banner — absence of an answer is not
// evidence of a mismatch.
import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";

const CHECK_MS = 5 * 60 * 1000;

export default function BuildMismatchBanner() {
  const t = useT();
  const loadedRef = useRef(null);
  const [server, setServer] = useState(null);

  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const r = await api.get("/version");
        const v = r?.data?.version;
        if (!alive || !v) return;
        if (loadedRef.current === null) loadedRef.current = v;
        else if (v !== loadedRef.current) setServer(v);
      } catch {
        /* network noise never fires the banner */
      }
    };
    check();
    const timer = setInterval(check, CHECK_MS);
    window.addEventListener("focus", check);
    return () => {
      alive = false;
      clearInterval(timer);
      window.removeEventListener("focus", check);
    };
  }, []);

  if (!server) return null;
  return (
    <div
      className="fixed top-0 inset-x-0 z-[200] bg-amber-400 text-black text-sm px-4 py-2 flex items-center gap-3 shadow-md"
      data-testid="build-mismatch-banner"
    >
      <AlertTriangle className="w-4 h-4 shrink-0" />
      <span data-testid="build-mismatch-text">
        {t("build.stale.msg", { client: loadedRef.current, server })}
      </span>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="ml-auto shrink-0 border border-black px-2.5 py-1 font-bold text-xs uppercase tracking-wider hover:bg-black hover:text-amber-400"
        data-testid="build-mismatch-refresh"
      >
        {t("build.stale.btn")}
      </button>
    </div>
  );
}
