// Iter 79j.73 — Run Readiness checklist. The generic pre-run checklist
// for ANY new property, written once for two audiences: the field crew
// shooting today's house AND a contractor onboarding onto their first.
// Auto-detects what the app can verify (exposure entered, tape values
// saved, annotation boxes location-tagged); the field-only items are
// manual checks persisted per estimate in localStorage.
import React, { useEffect, useMemo, useState } from "react";
import { CheckCircle2, AlertTriangle, Circle, ChevronDown, ChevronRight, ClipboardCheck } from "lucide-react";
import api from "@/lib/api";

const MANUAL_ITEMS = [
  {
    key: "exposure_measured",
    label: "Siding exposure MEASURED on this house",
    detail:
      "Tape one course face-to-face. Never assume 3.75″ — it's the most-assumed number in siding and the next house is rarely the last one.",
  },
  {
    key: "wall_ref",
    label: "WALL REF on every elevation — on the wall's OWN plane",
    detail:
      "A tape/bar on a different plane (porch, clerestory, fence) gets rejected: the AI will not scale across planes.",
  },
  {
    key: "win_refs",
    label: "WIN_REFs where dormers / upper features exist",
    detail: "Anything above the eave line needs its own reference in frame.",
  },
  {
    key: "bottom_courses",
    label: "Bottom courses visible (SOP)",
    detail:
      "Stand back far enough that the first course above grade is in frame — hidden courses force extrapolation and cost accuracy.",
  },
];

const storageKey = (estimateId) => `runReadiness:${estimateId || "draft"}`;

export const RunReadinessChecklist = ({ estimateId, sidingExposure, annotations }) => {
  const [open, setOpen] = useState(true);
  const [manual, setManual] = useState({});
  const [tapeCount, setTapeCount] = useState(null); // null = loading / unavailable

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey(estimateId));
      if (raw) setManual(JSON.parse(raw));
    } catch { /* fresh start */ }
  }, [estimateId]);

  useEffect(() => {
    if (!estimateId) { setTapeCount(0); return; }
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/estimates/${estimateId}/tape-check`);
        const walls = data?.walls || {};
        const n = Object.values(walls).filter((v) => v != null && v !== "").length;
        if (!cancelled) setTapeCount(n);
      } catch {
        if (!cancelled) setTapeCount(0);
      }
    })();
    return () => { cancelled = true; };
  }, [estimateId]);

  const toggle = (key) => {
    setManual((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try { localStorage.setItem(storageKey(estimateId), JSON.stringify(next)); } catch { /* quota */ }
      return next;
    });
  };

  // ── auto-detected statuses ──
  const exposureVal = parseFloat(sidingExposure);
  const exposureSet = Number.isFinite(exposureVal) && exposureVal > 0;

  const boxStats = useMemo(() => {
    let total = 0;
    let untagged = 0;
    Object.entries(annotations || {}).forEach(([k, v]) => {
      if (k.startsWith("_") || !Array.isArray(v)) return;
      v.forEach((b) => {
        if (!b || typeof b !== "object") return;
        total += 1;
        if (!b.location) untagged += 1;
      });
    });
    return { total, untagged };
  }, [annotations]);

  const items = [];

  // 1. Calibration entered (auto) — the named trap gets its own line.
  items.push({
    key: "auto_exposure",
    status: exposureSet ? "ok" : "warn",
    label: exposureSet
      ? `Calibration set — exposure ${exposureVal}″`
      : "Calibration NOT set — enter siding exposure before running",
    detail: exposureSet
      ? "Confirm below that this number came off a tape on THIS house."
      : "Open “Calibrate window sizing” next to the Run button.",
  });

  // 2-5. Manual field checks (incl. the measured-not-assumed confirm).
  MANUAL_ITEMS.forEach((m) => {
    items.push({
      key: m.key,
      status: manual[m.key] ? "ok" : "todo",
      manual: true,
      label: m.label,
      detail: m.detail,
    });
  });

  // 6. Tape fields pre-filled (auto).
  items.push({
    key: "auto_tape",
    status: tapeCount == null ? "todo" : tapeCount > 0 ? "ok" : "warn",
    label:
      tapeCount == null
        ? "Tape Check — loading…"
        : tapeCount > 0
        ? `Tape Check pre-filled — ${tapeCount}/4 walls (scoring is one click after the run)`
        : "Tape Check empty — pre-fill wall heights so scoring is one click",
    detail: "Tape values live on the estimate and survive re-runs.",
  });

  // 7. Annotation boxes location-tagged (auto).
  items.push({
    key: "auto_boxes",
    status:
      boxStats.total === 0 ? "none" : boxStats.untagged > 0 ? "warn" : "ok",
    label:
      boxStats.total === 0
        ? "No profile boxes drawn — only needed for accent siding (shake / B&B regions)"
        : boxStats.untagged > 0
        ? `${boxStats.untagged} of ${boxStats.total} profile boxes missing a location tag`
        : `All ${boxStats.total} profile boxes location-tagged`,
    detail:
      boxStats.untagged > 0
        ? "Untagged boxes can't override the surface they overlap — set body / gable / dormer in the annotator."
        : "Location tags let a box OWN the surface it overlaps instead of double-counting it.",
  });

  const readyCount = items.filter((i) => i.status === "ok" || i.status === "none").length;
  const allReady = readyCount === items.length;

  const StatusIcon = ({ status }) => {
    if (status === "ok") return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />;
    if (status === "warn") return <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />;
    if (status === "none") return <CheckCircle2 className="w-3.5 h-3.5 text-[var(--muted)] shrink-0 mt-0.5" />;
    return <Circle className="w-3.5 h-3.5 text-[var(--muted)] shrink-0 mt-0.5" />;
  };

  return (
    <div
      className={`mb-3 border ${allReady ? "border-emerald-600/40" : "border-[var(--border)]"} bg-[var(--surface)]`}
      data-testid="run-readiness-checklist"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
        data-testid="run-readiness-toggle"
      >
        <span className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold text-[var(--ink)]">
          <ClipboardCheck className={`w-3.5 h-3.5 ${allReady ? "text-emerald-600" : "text-[var(--ai)]"}`} />
          Run Readiness
          <span
            className={`px-1.5 py-0.5 text-[9px] ${allReady ? "bg-emerald-600 text-white" : "bg-[var(--ai)]/10 text-[var(--ai)]"}`}
            data-testid="run-readiness-count"
          >
            {readyCount}/{items.length}
          </span>
        </span>
        <span className="flex items-center gap-2">
          <span className="text-[9px] text-[var(--muted)] normal-case hidden md:inline">
            Same checklist every property — first house or fiftieth
          </span>
          {open ? <ChevronDown className="w-3.5 h-3.5 text-[var(--muted)]" /> : <ChevronRight className="w-3.5 h-3.5 text-[var(--muted)]" />}
        </span>
      </button>
      {open && (
        <ul className="px-3 pb-3 space-y-2">
          {items.map((it) => (
            <li key={it.key} className="flex items-start gap-2" data-testid={`run-readiness-item-${it.key}`}>
              {it.manual ? (
                <input
                  type="checkbox"
                  checked={!!manual[it.key]}
                  onChange={() => toggle(it.key)}
                  className="mt-0.5 accent-[var(--ai)] shrink-0 cursor-pointer"
                  data-testid={`run-readiness-check-${it.key}`}
                />
              ) : (
                <StatusIcon status={it.status} />
              )}
              <div className="min-w-0">
                <div className={`text-[11px] leading-tight ${it.status === "warn" ? "text-amber-600 font-bold" : "text-[var(--ink)]"}`}>
                  {it.label}
                </div>
                <div className="text-[9px] text-[var(--muted)] leading-tight mt-0.5">{it.detail}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default RunReadinessChecklist;
