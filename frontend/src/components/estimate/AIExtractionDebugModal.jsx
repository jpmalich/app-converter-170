// Iter 79j.36 — AI Extraction Debug view.
//
// PURPOSE. Shows two layers of the AI Measure pipeline side-by-side so
// contractors can diagnose why 3 runs on the same house returned eave
// heights of 7, 8.5, and 12 ft (and different dormer counts):
//
//   LEFT COLUMN  — per-photo RAW observations. For each attached
//                  photo, Claude's own read of what IT saw in THAT
//                  photo: which walls are visible, the eave height
//                  it measured, pitch, gable triangle height, dormer
//                  count, and each opening (type, size, bbox).
//                  Reveals whether variance is a DETECTION problem
//                  (different photos disagree).
//
//   RIGHT COLUMN — reconciled house JSON. Walls, openings, dormer,
//                  avg wall height — each annotated with the photo
//                  indices it was drawn from and Claude's own note
//                  explaining how it merged / averaged / discarded.
//                  Reveals whether variance is a RECONCILIATION
//                  problem (photos agree but the merge drifts).
//
// The fields all live on `preview.raw_ai` (per-photo → `photos[]`,
// reconciled → `walls[]`, `openings[]`, top-level scalars, and the
// per-value provenance in `walls[]._*`, `openings[]._*`, and
// `_reconciliation_notes`). Claude may not fill every optional
// provenance field — we render "not reported" placeholders so it's
// obvious whether the model omitted the trace vs the value.

import React, { useEffect, useMemo, useState } from "react";
import { X, Camera, Layers, Copy, Check, GitBranch, Loader2, GitCompareArrows } from "lucide-react";

import api from "@/lib/api";

const API = process.env.REACT_APP_BACKEND_URL;

function coalesce(v, fallback = "—") {
  if (v === null || v === undefined) return fallback;
  if (typeof v === "string" && !v.trim()) return fallback;
  return v;
}

function fmtFt(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return `${v.toFixed(1)} ft`;
  return String(v);
}

function fmtIn(v) {
  if (v === null || v === undefined || v === 0) return "—";
  return `${Math.round(Number(v))}"`;
}

// Small chip that highlights a photo index — clicking it scrolls the
// left column to the corresponding photo card so provenance is
// visually traceable.
function PhotoChip({ idx, onFocus }) {
  return (
    <button
      type="button"
      onClick={() => onFocus?.(idx)}
      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-bold bg-[#0EA5E9] text-white hover:bg-[#0284C7] transition-colors"
      data-testid={`debug-photo-chip-${idx}`}
      title={`Jump to photo ${idx}`}
    >
      <Camera className="w-2.5 h-2.5" />
      P{idx}
    </button>
  );
}

function PhotoCard({ photo, idx, photoUrls, focused }) {
  // photo may be undefined if Claude skipped an index — still render
  // a shell so the contractor sees the gap.
  const url = photoUrls?.[idx];
  const fullUrl = url ? (url.startsWith("http") ? url : `${API}/api/uploads/${url}`) : null;
  const p = photo || {};
  return (
    <div
      id={`debug-photo-${idx}`}
      className={`border ${focused ? "border-[#0EA5E9] shadow-[0_0_0_2px_#BAE6FD]" : "border-[var(--border)]"} bg-[var(--surface)]`}
      data-testid={`debug-photo-card-${idx}`}
    >
      <div className="flex items-center gap-2 px-3 py-2 bg-[var(--bg-app)] border-b border-[var(--border)]">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#0EA5E9]">P{idx}</span>
        <span className="text-[11px] text-[var(--ink-2)] font-mono">
          {coalesce(p.elevation)} <span className="text-[var(--muted)]">·</span>{" "}
          {p.elevation_confidence != null ? `${p.elevation_confidence}%` : "conf ?"}
        </span>
      </div>
      <div className="flex gap-3 p-3">
        {fullUrl && (
          <img
            src={fullUrl}
            alt={`Photo ${idx}`}
            className="w-24 h-24 object-cover flex-shrink-0 border border-[var(--border)]"
          />
        )}
        <div className="flex-1 min-w-0 space-y-1.5 text-[11px] font-mono-num">
          <Row label="Reasoning">{coalesce(p.elevation_reasoning)}</Row>
          <Row label="Walls visible">
            {(p.walls_visible && p.walls_visible.length)
              ? p.walls_visible.join(", ")
              : <span className="text-[var(--muted)] italic">not reported</span>}
          </Row>
          <Row label="Eave observed">
            {p.eave_height_ft_observed != null
              ? <span className="font-bold text-[#0EA5E9]">{fmtFt(p.eave_height_ft_observed)}</span>
              : <span className="text-[var(--muted)] italic">null (not measurable)</span>}
            {p.eave_reasoning && (
              <div className="text-[10px] text-[var(--muted)] mt-0.5">{p.eave_reasoning}</div>
            )}
          </Row>
          <Row label="Pitch observed">
            {coalesce(p.pitch_ratio_observed, <span className="text-[var(--muted)] italic">null</span>)}
          </Row>
          <Row label="Gable Δh">
            {p.gable_triangle_height_ft_observed != null
              ? fmtFt(p.gable_triangle_height_ft_observed)
              : <span className="text-[var(--muted)] italic">null</span>}
          </Row>
          <Row label="Dormers here">
            <span className={p.dormers_observed_count ? "font-bold text-[#0EA5E9]" : ""}>
              {coalesce(p.dormers_observed_count, 0)}
            </span>
          </Row>
          {p.notes && (
            <Row label="Notes">
              <span className="text-[var(--muted)]">{p.notes}</span>
            </Row>
          )}
          {p.openings_this_photo && p.openings_this_photo.length > 0 && (
            <div className="pt-1">
              <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold mb-0.5">
                Openings ({p.openings_this_photo.length})
              </div>
              <div className="space-y-0.5">
                {p.openings_this_photo.map((o, i) => (
                  <div key={i} className="text-[10px] flex items-center gap-1.5">
                    <span className="text-[var(--muted)]">·</span>
                    <span className="font-bold text-[#3F3F46]">{o.type}</span>
                    <span className="text-[var(--ink-2)]">{fmtIn(o.width_in)}×{fmtIn(o.height_in)}</span>
                    {o.opening_id && <span className="text-[var(--muted)] italic">{o.opening_id}</span>}
                    {o.bbox && Array.isArray(o.bbox) && (
                      <span className="text-[var(--muted)]" title="pixel bbox">
                        [{o.bbox.map((n) => Math.round(n)).join(",")}]
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold w-20 flex-shrink-0">{label}</span>
      <div className="flex-1 min-w-0 break-words">{children}</div>
    </div>
  );
}

function WallCard({ w, onFocusPhoto }) {
  const readings = Array.isArray(w._per_photo_readings) ? w._per_photo_readings : [];
  const sourcePhotos = Array.isArray(w._source_photo_indices) ? w._source_photo_indices : [];
  return (
    <div className="border border-[var(--border)] bg-[var(--surface)]" data-testid={`debug-wall-${w.label}`}>
      <div className="flex items-center gap-2 px-3 py-2 bg-[var(--bg-app)] border-b border-[var(--border)]">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--ai)]">Wall · {w.label}</span>
        {w.confidence != null && (
          <span className="text-[10px] text-[var(--ink-2)] font-mono">conf {w.confidence}%</span>
        )}
      </div>
      <div className="p-3 text-[11px] font-mono-num space-y-1.5">
        <Row label="Width">{fmtFt(w.width_ft)}</Row>
        <Row label="Eave (final)"><span className="font-bold text-[var(--ai)]">{fmtFt(w.height_ft)}</span></Row>
        <Row label="Gable Δh">{fmtFt(w.gable_triangle_height_ft)}</Row>
        <Row label="Dormer face">{coalesce(w.dormer_face_sqft, 0)} ft²</Row>
        <Row label="Siding %">{coalesce(w.siding_pct_this_wall, 100)}%</Row>
        <Row label="From photos">
          {sourcePhotos.length > 0
            ? <div className="flex gap-1 flex-wrap">
                {sourcePhotos.map((i) => <PhotoChip key={i} idx={i} onFocus={onFocusPhoto} />)}
              </div>
            : <span className="text-[var(--muted)] italic">not reported</span>}
        </Row>
        {readings.length > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold mb-0.5">
              Per-photo readings (before merge)
            </div>
            <div className="space-y-0.5 pl-2 border-l-2 border-[var(--border)]">
              {readings.map((r, i) => (
                <div key={i} className="text-[10px] flex items-center gap-2">
                  <PhotoChip idx={r.photo_idx} onFocus={onFocusPhoto} />
                  <span className="text-[var(--ink-2)]">
                    eave={fmtFt(r.eave_ft)} · gable={fmtFt(r.gable_triangle_ft)}
                  </span>
                  {r.notes && <span className="text-[var(--muted)] italic">{r.notes}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
        {w._reconciliation_note && (
          <div className="mt-1 px-2 py-1 bg-[var(--ai-soft)] border border-[#DDD6FE] text-[10px] text-[#5B21B6]">
            <b className="uppercase tracking-wider text-[9px]">Reconciliation:</b> {w._reconciliation_note}
          </div>
        )}
      </div>
    </div>
  );
}

function OpeningRow({ o, i, onFocusPhoto }) {
  const sources = Array.isArray(o._source_photo_indices)
    ? o._source_photo_indices
    : (o.photo_idx != null ? [o.photo_idx] : []);
  return (
    <div
      className="flex items-center gap-2 px-2 py-1.5 border-b border-[var(--bg-app)] last:border-b-0 text-[11px]"
      data-testid={`debug-opening-${i}`}
    >
      <span className="w-16 text-[var(--ink-2)] font-mono truncate">{o.type}</span>
      <span className="w-14 text-[#3F3F46] font-mono">{fmtIn(o.width_in)}×{fmtIn(o.height_in)}</span>
      <span className="w-14 text-[var(--ink-2)] font-mono truncate" title={o.style}>{o.style || "—"}</span>
      <span className="w-12 text-[var(--ink-2)] font-mono truncate">{o.wall || "—"}</span>
      <div className="flex gap-1 min-w-0 flex-1">
        {sources.length > 0
          ? sources.map((idx) => <PhotoChip key={idx} idx={idx} onFocus={onFocusPhoto} />)
          : <span className="text-[var(--muted)] italic text-[10px]">no photo tag</span>}
      </div>
      {o._reconciliation_note && (
        <span className="text-[10px] text-[var(--muted)] italic truncate" title={o._reconciliation_note}>
          {o._reconciliation_note}
        </span>
      )}
    </div>
  );
}

export default function AIExtractionDebugModal({ preview, photoUrls, estimateId, onClose }) {
  const [focusedPhoto, setFocusedPhoto] = useState(null);
  const [rawExpanded, setRawExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  // Iter 79j.54 — Run picker. When multiple runs exist for this
  // estimate (e.g. an original reconciled Run 3 + this morning's
  // marker-annotated Re-run), let the contractor switch between
  // them without leaving the modal. `pickerRuns` is the list from
  // /ai-measure/debug-runs; `activeRun` is the run currently
  // displayed. If null, we fall back to the `preview` prop the
  // parent gave us. Selecting a different run fetches its full
  // result via /status/{run_id} and swaps the local state.
  const [pickerRuns, setPickerRuns] = useState([]);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [activeRun, setActiveRun] = useState(null); // { run_id, result, raw_per_photo, pipeline }
  const [switchingRunId, setSwitchingRunId] = useState(null);
  // Iter 79j.54a — Diff mode. `diffRun` is the SECOND run loaded for
  // side-by-side comparison. When set, a DiffPanel renders at the
  // top of the reconciled column showing per-field deltas (A vs B).
  // Selecting the SAME run as the active view clears diff mode.
  const [diffRun, setDiffRun] = useState(null); // { run_id, raw_ai }
  const [diffLoadingRunId, setDiffLoadingRunId] = useState(null);

  useEffect(() => {
    if (!estimateId) return;
    let cancelled = false;
    setPickerLoading(true);
    api.get(`/measure/ai-measure/debug-runs/${estimateId}`)
      .then((r) => {
        if (cancelled) return;
        setPickerRuns(Array.isArray(r?.data?.runs) ? r.data.runs : []);
      })
      .catch(() => { if (!cancelled) setPickerRuns([]); })
      .finally(() => { if (!cancelled) setPickerLoading(false); });
    return () => { cancelled = true; };
  }, [estimateId]);

  const switchToRun = async (runId) => {
    if (!runId || switchingRunId) return;
    setSwitchingRunId(runId);
    try {
      const { data } = await api.get(`/measure/ai-measure/status/${runId}`);
      if (!data || data.status === "error") {
        // For failed runs the result is None but we can still show
        // Phase A / reconciliation_error via the run doc's saved
        // state. `raw_per_photo` alone drives the LEFT column.
      }
      setActiveRun({
        run_id: runId,
        result: data?.result || null,
        raw_per_photo: data?.raw_per_photo || null,
        pipeline: data?.pipeline || null,
        status: data?.status,
        stage: data?.stage,
        error: data?.error,
      });
      setFocusedPhoto(null);
    } catch {
      // Non-fatal — keep the current view.
    } finally {
      setSwitchingRunId(null);
    }
  };

  // Iter 79j.54a — Toggle a run into the diff slot. Clicking the
  // compare pill on the ACTIVE run is a no-op (nothing to diff
  // against itself); clicking the pill on the ALREADY-DIFFED run
  // clears the diff. Otherwise we fetch that run's status and stash
  // its raw_ai payload for the DiffPanel to consume.
  const toggleDiffRun = async (runId) => {
    if (!runId) return;
    if (runId === activeRunId) return;                 // can't diff against self
    if (diffRun?.run_id === runId) {                    // clicking same → clear
      setDiffRun(null);
      return;
    }
    if (diffLoadingRunId) return;
    setDiffLoadingRunId(runId);
    try {
      const { data } = await api.get(`/measure/ai-measure/status/${runId}`);
      const rawAi = data?.result?.raw_ai || null;
      setDiffRun({ run_id: runId, raw_ai: rawAi, status: data?.status });
    } catch {
      // Non-fatal — silent skip; user can retry.
    } finally {
      setDiffLoadingRunId(null);
    }
  };

  // Resolve which run's data to render. If the picker has swapped
  // to a different run, use that; otherwise fall back to whatever
  // preview the parent handed us.
  const view = activeRun
    ? {
        raw_ai: (activeRun.result || {}).raw_ai || { _reconciliation_error: null, photos: [] },
        raw_per_photo: activeRun.raw_per_photo,
        pipeline: activeRun.pipeline,
      }
    : {
        raw_ai: preview?.raw_ai || {},
        raw_per_photo: preview?.raw_per_photo,
        pipeline: preview?.pipeline,
      };
  const activeRunId = activeRun?.run_id
    || preview?.run_id
    || (pickerRuns.find((r) => r.score === 2)?.run_id)
    || null;

  const raw = view.raw_ai || {};
  // Iter 79j.37 — When the two-phase pipeline ran, `preview.raw_per_photo`
  // contains the ACTUAL per-photo Claude call outputs (one call per
  // photo), not the after-the-fact recollection embedded in the
  // reconciled JSON. Prefer those for the LEFT column. Fall back to
  // the single-call schema (`raw.photos`) for legacy runs.
  const rawPerPhoto = Array.isArray(view.raw_per_photo) ? view.raw_per_photo : null;
  const pipelineLabel = view.pipeline || raw._pipeline || (rawPerPhoto ? "two_phase" : "single_call");
  const photos = useMemo(() => {
    if (rawPerPhoto && rawPerPhoto.length) return rawPerPhoto;
    return Array.isArray(raw.photos) ? raw.photos : [];
  }, [rawPerPhoto, raw.photos]);
  const walls = useMemo(() => Array.isArray(raw.walls) ? raw.walls : [], [raw.walls]);
  const openings = useMemo(() => Array.isArray(raw.openings) ? raw.openings : [], [raw.openings]);
  const dormer = raw.dormer;
  const reconciliation = raw._reconciliation_notes || {};

  const focusPhoto = (idx) => {
    setFocusedPhoto(idx);
    document.getElementById(`debug-photo-${idx}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const copyRaw = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(raw, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* ignore */ }
  };

  // Align photoUrls to Claude's photo indices — Claude emits index=0
  // for the first image sent to it, and `photoUrls` from state is in
  // the same order (both come from the modal upload grid). Length
  // mismatches happen when Claude skipped an entry; we render the
  // union of both indices so gaps are visible.
  const maxIdx = Math.max(
    (photoUrls?.length || 0) - 1,
    ...photos.map((p) => (typeof p.index === "number" ? p.index : -1)),
    -1,
  );
  const photosByIdx = useMemo(() => {
    const m = new Map();
    photos.forEach((p) => {
      const i = typeof p.index === "number" ? p.index : -1;
      if (i >= 0) m.set(i, p);
    });
    return m;
  }, [photos]);

  return (
    <div
      className="fixed inset-0 z-[70] bg-[var(--bar-bg)]/80 flex items-center justify-center p-4"
      data-testid="debug-extraction-modal"
    >
      <div className="bg-[var(--surface)] w-full max-w-[1400px] h-[92vh] flex flex-col border border-[var(--border)]">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-[var(--border)] bg-[var(--surface-muted)]">
          <Layers className="w-4 h-4 text-[var(--ai)]" />
          <div className="flex-1">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--ink)]" data-testid="debug-modal-title">
              Extraction debug
            </h3>
            <p className="text-[11px] text-[var(--muted)] mt-0.5">
              Left: what Claude saw in each photo. Right: the reconciled house — with the photos each final number was drawn from and the merge trace.
            </p>
          </div>
          <span
            className={`text-[10px] uppercase font-bold tracking-wider px-2 py-1 border ${
              pipelineLabel === "two_phase"
                ? "bg-[#DCFCE7] text-[#166534] border-[var(--success)]"
                : "bg-[#FEF3C7] text-[var(--warning-text)] border-[#F59E0B]"
            }`}
            title={pipelineLabel === "two_phase"
              ? "TWO-PHASE: 1 Claude call per photo (real per-photo data) + 1 reconciliation call"
              : "SINGLE-CALL: all photos in one Claude call — per-photo values below are Claude's after-the-fact recollection, NOT actual per-photo extractions. Set AI_MEASURE_TWO_PHASE=1 on the backend to switch."}
            data-testid="debug-pipeline-badge"
          >
            {pipelineLabel === "two_phase" ? "Two-phase" : "Single-call"}
          </span>
          <button
            type="button"
            onClick={copyRaw}
            className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--ink-2)] hover:text-[var(--ink)] border border-[var(--border)] hover:bg-[var(--surface)] flex items-center gap-1.5"
            data-testid="debug-copy-raw-btn"
            title="Copy the raw AI JSON to clipboard — paste it into a bug report or diff two runs"
          >
            {copied ? <Check className="w-3 h-3 text-[var(--success)]" /> : <Copy className="w-3 h-3" />}
            {copied ? "Copied" : "Copy raw JSON"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--bg-app)]"
            data-testid="debug-close-btn"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Iter 79j.54 — Run picker. Shown only when the estimate has
            more than one run on record. Successful reconciliations
            are marked with a green dot; failed / stranded runs with
            an amber dot. Selecting a run swaps the whole modal
            (Phase A left + reconciled right) to that run's data.
            Doesn't touch the parent's session preview. */}
        {estimateId && (pickerRuns.length > 1 || pickerLoading) && (
          <div
            className="flex items-center gap-2 px-5 py-2 border-b border-[var(--border)] bg-[var(--surface)] flex-wrap"
            data-testid="debug-run-picker"
          >
            <GitBranch className="w-3.5 h-3.5 text-[var(--muted)]" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
              Inspect run:
            </span>
            {pickerLoading && pickerRuns.length === 0 ? (
              <span className="text-[11px] text-[var(--muted)] italic inline-flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" /> loading runs…
              </span>
            ) : (
              <div className="flex items-center gap-1.5 flex-wrap">
                {pickerRuns.map((r) => {
                  const isActive = activeRunId === r.run_id;
                  const isSwitching = switchingRunId === r.run_id;
                  const dot = r.score === 2
                    ? "bg-[var(--success)]"
                    : r.score === 1
                    ? "bg-[#F59E0B]"
                    : "bg-[#DC2626]";
                  const shortId = (r.run_id || "").slice(0, 6);
                  const when = r.completed_at
                    ? new Date(r.completed_at).toLocaleString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                      })
                    : "";
                  const dormerBadge = r.phase_a_dormer_total > r.dormer_count
                    ? ` · Phase A saw ${r.phase_a_dormer_total}d, reconciled ${r.dormer_count}d`
                    : ` · ${r.dormer_count}d`;
                  const reconMark = r.reconciled
                    ? "✓ reconciled"
                    : r.reconciliation_error
                    ? "recon 502"
                    : r.status === "error"
                    ? "errored"
                    : "no result";
                  return (
                    <div
                      key={r.run_id}
                      className={`inline-flex items-stretch border ${
                        isActive
                          ? "border-[var(--ai)] bg-[var(--ai)]/10 text-[var(--ink)]"
                          : diffRun?.run_id === r.run_id
                          ? "border-[#F59E0B] bg-[#FEF3C7] text-[var(--ink)]"
                          : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--surface-muted)]"
                      } transition-colors`}
                    >
                      <button
                        type="button"
                        onClick={() => switchToRun(r.run_id)}
                        disabled={isSwitching}
                        className="text-[10px] font-mono px-2 py-1 inline-flex items-center gap-1.5 disabled:opacity-50"
                        title={`${r.run_id}\n${r.model_choice || "?"} · ${r.photo_count}p · ${reconMark}${dormerBadge}\n${r.reconciliation_error || ""}`}
                        data-testid={`debug-run-picker-${r.run_id}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${dot}`} aria-hidden />
                        <span className="font-bold">{shortId}</span>
                        <span className="text-[var(--muted)]">·</span>
                        <span>{when}</span>
                        <span className="text-[var(--muted)]">·</span>
                        <span className="font-mono">
                          {r.wall_count}w · {r.dormer_count}d
                          {r.phase_a_dormer_total > r.dormer_count && (
                            <span className="text-[#F59E0B]" title="Phase A observed more dormers than reconciliation kept">
                              {" "}(A={r.phase_a_dormer_total})
                            </span>
                          )}
                          {" · "}{Math.round(r.siding_sqft || 0)}sf
                          {r.cost_usd != null && (
                            <span data-testid={`debug-run-cost-${r.run_id}`} title="Actual run cost from live token telemetry (input + output tokens × current rates, both phases)">
                              {" · $"}{r.cost_usd.toFixed(2)}
                            </span>
                          )}
                        </span>
                        {isSwitching && <Loader2 className="w-3 h-3 animate-spin" />}
                        {isActive && !isSwitching && (
                          <span className="text-[9px] uppercase tracking-wider text-[var(--ai)] font-bold ml-0.5">
                            viewing
                          </span>
                        )}
                      </button>
                      {/* Iter 79j.54a — Compare pill. Only shown for
                          runs that are NOT currently the active view;
                          otherwise diffing self vs self is a no-op.
                          Clicking sets the run as the diff target;
                          clicking again clears. */}
                      {!isActive && (
                        <button
                          type="button"
                          onClick={() => toggleDiffRun(r.run_id)}
                          disabled={diffLoadingRunId === r.run_id}
                          className={`px-1.5 border-l ${
                            diffRun?.run_id === r.run_id
                              ? "border-[#F59E0B] bg-[#FEF3C7] text-[#78350F]"
                              : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--ink-2)] hover:bg-[var(--surface-muted)]"
                          } disabled:opacity-50`}
                          title={
                            diffRun?.run_id === r.run_id
                              ? "Clear diff target"
                              : "Diff against the currently viewing run"
                          }
                          data-testid={`debug-run-diff-toggle-${r.run_id}`}
                        >
                          {diffLoadingRunId === r.run_id
                            ? <Loader2 className="w-3 h-3 animate-spin" />
                            : diffRun?.run_id === r.run_id
                            ? <span className="text-[9px] font-bold uppercase tracking-wider">diff · B</span>
                            : <GitCompareArrows className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Two-column body */}
        <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
          {/* LEFT — Per-photo raw observations */}
          <div className="overflow-y-auto p-4 space-y-3 border-r border-[var(--border)] bg-[var(--surface-muted)]">
            <div className="flex items-center gap-2 mb-1">
              <Camera className="w-3.5 h-3.5 text-[#0EA5E9]" />
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-[#0EA5E9]">
                {pipelineLabel === "two_phase" ? "Per-photo raw (Phase A)" : "Per-photo (Claude's recollection)"}
                {" "}({photos.length} reported / {photoUrls?.length || 0} uploaded)
              </h4>
            </div>
            {maxIdx < 0 && (
              <div className="text-[11px] text-[var(--muted)] italic px-3 py-8 text-center">
                No per-photo data. The AI didn&apos;t return a `photos[]` array for this run.
              </div>
            )}
            {[...Array(maxIdx + 1)].map((_, idx) => (
              <PhotoCard
                key={idx}
                idx={idx}
                photo={photosByIdx.get(idx)}
                photoUrls={photoUrls}
                focused={focusedPhoto === idx}
              />
            ))}
          </div>

          {/* RIGHT — Reconciled house JSON with provenance */}
          <div className="overflow-y-auto p-4 space-y-3 bg-[var(--surface)]">
            {/* Iter 79j.54a — Diff panel appears above the standard
                per-field cards when a compare target is set. Non-blocking
                (the full cards still render below so the eye can drill
                down); the panel just surfaces deltas up-front. */}
            {diffRun && diffRun.raw_ai && (
              <DiffPanel
                activeRaw={raw}
                activeRunId={activeRunId}
                diffRaw={diffRun.raw_ai}
                diffRunId={diffRun.run_id}
                onClose={() => setDiffRun(null)}
              />
            )}
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-3.5 h-3.5 text-[var(--ai)]" />
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-[var(--ai)]">
                Reconciled house — click any P# chip to jump to that photo
              </h4>
            </div>

            {/* Top-level scalars + reconciliation notes */}
            <div className="border border-[var(--border)] bg-[var(--surface)]">
              <div className="px-3 py-2 bg-[var(--bg-app)] border-b border-[var(--border)]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--ai)]">House-level</span>
              </div>
              <div className="p-3 text-[11px] font-mono-num space-y-1.5">
                <Row label="Avg eave">{fmtFt(raw.avg_wall_height_ft)}</Row>
                {reconciliation.avg_wall_height_ft && (
                  <ReconNote>{reconciliation.avg_wall_height_ft}</ReconNote>
                )}
                <Row label="Story count">{coalesce(raw.story_count)}</Row>
                {raw.story_count_reasoning && (
                  <div className="text-[10px] text-[var(--muted)] pl-22">{raw.story_count_reasoning}</div>
                )}
                <Row label="Roof type">
                  <span className="font-bold text-[var(--ai)]">{coalesce(raw.roof_type)}</span>
                  {raw.roof_type_confidence != null && (
                    <span className="text-[var(--muted)] ml-1">({Math.round(raw.roof_type_confidence * 100)}%)</span>
                  )}
                </Row>
                {raw.roof_type_reasoning && (
                  <div className="text-[10px] text-[var(--muted)] pl-22">{raw.roof_type_reasoning}</div>
                )}
                {reconciliation.roof_type && <ReconNote>{reconciliation.roof_type}</ReconNote>}
                <Row label="Siding cov.">{coalesce(raw.siding_coverage_pct)}%</Row>
                {reconciliation.siding_coverage_pct && (
                  <ReconNote>{reconciliation.siding_coverage_pct}</ReconNote>
                )}
                <Row label="Scale conf.">{coalesce(raw.scale_confidence)}</Row>
                <Row label="Reference">{coalesce(raw.reference_used)}</Row>
              </div>
            </div>

            {dormer && (
              <div className="border border-[var(--border)] bg-[var(--surface)]" data-testid="debug-dormer-card">
                <div className="px-3 py-2 bg-[var(--bg-app)] border-b border-[var(--border)]">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--ai)]">Dormer</span>
                </div>
                <div className="p-3 text-[11px] font-mono-num space-y-1.5">
                  <Row label="Face">{coalesce(dormer.face)}</Row>
                  <Row label="Width">{fmtFt(dormer.width_ft)}</Row>
                  <Row label="Knee wall">{fmtFt(dormer.knee_wall_height_ft)}</Row>
                  <Row label="Offset X">{fmtFt(dormer.offset_x_ft)}</Row>
                  {reconciliation.dormer && <ReconNote>{reconciliation.dormer}</ReconNote>}
                </div>
              </div>
            )}

            {walls.map((w, i) => (
              <WallCard key={`${w.label}-${i}`} w={w} onFocusPhoto={focusPhoto} />
            ))}

            <div className="border border-[var(--border)] bg-[var(--surface)]" data-testid="debug-openings-card">
              <div className="px-3 py-2 bg-[var(--bg-app)] border-b border-[var(--border)]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--ai)]">
                  Openings ({openings.length})
                </span>
              </div>
              {openings.length === 0
                ? <div className="p-3 text-[11px] text-[var(--muted)] italic">No openings extracted.</div>
                : openings.map((o, i) => <OpeningRow key={i} o={o} i={i} onFocusPhoto={focusPhoto} />)}
            </div>

            <details className="border border-[var(--border)] bg-[var(--surface)]" open={rawExpanded} onToggle={(e) => setRawExpanded(e.target.open)}>
              <summary className="px-3 py-2 text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold cursor-pointer bg-[var(--bg-app)]">
                Full raw JSON
              </summary>
              <pre className="text-[10px] font-mono-num p-3 overflow-x-auto max-h-96 bg-[var(--bar-bg)] text-[#E4E4E7]" data-testid="debug-raw-json-pre">
                {JSON.stringify(raw, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReconNote({ children }) {
  return (
    <div className="ml-22 mt-1 px-2 py-1 bg-[var(--ai-soft)] border border-[#DDD6FE] text-[10px] text-[#5B21B6]">
      <b className="uppercase tracking-wider text-[9px]">Reconciliation:</b> {children}
    </div>
  );
}

// Iter 79j.54a — DiffPanel. Renders a compact 3-column table
// (Field · A · B) of key reconciliation outputs so contractors can
// see WHY two runs on the same house produced different quotes.
// Deliberately minimal: no full JSON diff — just the fields that
// actually drive line items (roof type, avg eave, wall count / per-wall
// widths + heights, dormer count / per-dormer face + width + knee,
// opening count). Any row where A ≠ B gets the amber Δ marker so the
// eye lands on differences before values.
function fmtVal(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return "—";
    if (Number.isInteger(v)) return String(v);
    return v.toFixed(2);
  }
  return String(v);
}
function DiffRow({ label, a, b }) {
  const same = fmtVal(a) === fmtVal(b);
  return (
    <div
      className={`grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_24px] gap-2 px-2 py-1 text-[10px] font-mono-num border-b border-[var(--bg-app)] last:border-b-0 ${same ? "" : "bg-[#FEF3C7]"}`}
      data-testid={`debug-diff-row-${label.replace(/\s+/g, "-").toLowerCase()}`}
    >
      <span className="text-[var(--muted)] uppercase tracking-wider font-bold text-[9px] truncate" title={label}>{label}</span>
      <span className={`truncate ${same ? "text-[var(--ink-2)]" : "text-[var(--ink)] font-bold"}`}>{fmtVal(a)}</span>
      <span className={`truncate ${same ? "text-[var(--ink-2)]" : "text-[var(--ink)] font-bold"}`}>{fmtVal(b)}</span>
      <span className={`text-[9px] font-bold text-right ${same ? "text-[var(--muted)]" : "text-[#B45309]"}`}>{same ? "" : "Δ"}</span>
    </div>
  );
}
function DiffPanel({ activeRaw, activeRunId, diffRaw, diffRunId, onClose }) {
  const shortA = (activeRunId || "").slice(0, 6);
  const shortB = (diffRunId || "").slice(0, 6);
  const wallsByLabel = (raw) => {
    const m = new Map();
    (raw?.walls || []).forEach((w) => m.set((w.label || "").toLowerCase(), w));
    return m;
  };
  const wA = wallsByLabel(activeRaw);
  const wB = wallsByLabel(diffRaw);
  const wallLabels = Array.from(new Set([...wA.keys(), ...wB.keys()])).filter(Boolean).sort();
  const dormersA = Array.isArray(activeRaw?.dormers) ? activeRaw.dormers : (activeRaw?.dormer ? [activeRaw.dormer] : []);
  const dormersB = Array.isArray(diffRaw?.dormers) ? diffRaw.dormers : (diffRaw?.dormer ? [diffRaw.dormer] : []);
  const maxDormerIdx = Math.max(dormersA.length, dormersB.length);
  return (
    <div
      className="border border-[#F59E0B] bg-[var(--surface)]"
      data-testid="debug-diff-panel"
    >
      <div className="flex items-center gap-2 px-3 py-2 bg-[#FEF3C7] border-b border-[#F59E0B]">
        <GitCompareArrows className="w-3.5 h-3.5 text-[#B45309]" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#78350F]">
          Diff · A={shortA} vs B={shortB}
        </span>
        <span className="text-[10px] text-[#78350F] flex-1 truncate">
          amber rows show differences that will move quote quantities
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-[10px] text-[#78350F] underline hover:no-underline"
          data-testid="debug-diff-close-btn"
        >
          exit diff
        </button>
      </div>
      <div>
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_24px] gap-2 px-2 py-1 bg-[var(--surface-muted)] text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold">
          <span>Field</span>
          <span>Run A</span>
          <span>Run B</span>
          <span></span>
        </div>
        <DiffRow label="Roof type" a={activeRaw?.roof_type} b={diffRaw?.roof_type} />
        <DiffRow label="Roof pitch conf" a={activeRaw?.roof_type_confidence} b={diffRaw?.roof_type_confidence} />
        <DiffRow label="Story count" a={activeRaw?.story_count} b={diffRaw?.story_count} />
        <DiffRow label="Avg eave (ft)" a={activeRaw?.avg_wall_height_ft} b={diffRaw?.avg_wall_height_ft} />
        <DiffRow label="Siding cov %" a={activeRaw?.siding_coverage_pct} b={diffRaw?.siding_coverage_pct} />
        <DiffRow label="Scale conf" a={activeRaw?.scale_confidence} b={diffRaw?.scale_confidence} />
        <DiffRow label="Wall count" a={(activeRaw?.walls || []).length} b={(diffRaw?.walls || []).length} />
        <DiffRow label="Opening count" a={(activeRaw?.openings || []).length} b={(diffRaw?.openings || []).length} />
        <DiffRow label="Dormer count" a={dormersA.length} b={dormersB.length} />
        {wallLabels.map((label) => (
          <React.Fragment key={label}>
            <DiffRow label={`${label} · width`} a={wA.get(label)?.width_ft} b={wB.get(label)?.width_ft} />
            <DiffRow label={`${label} · eave`} a={wA.get(label)?.height_ft} b={wB.get(label)?.height_ft} />
            <DiffRow label={`${label} · gable Δh`} a={wA.get(label)?.gable_triangle_height_ft} b={wB.get(label)?.gable_triangle_height_ft} />
          </React.Fragment>
        ))}
        {[...Array(maxDormerIdx)].map((_, i) => (
          <React.Fragment key={`d${i}`}>
            <DiffRow label={`dormer ${i + 1} · face`} a={dormersA[i]?.face} b={dormersB[i]?.face} />
            <DiffRow label={`dormer ${i + 1} · width`} a={dormersA[i]?.width_ft} b={dormersB[i]?.width_ft} />
            <DiffRow label={`dormer ${i + 1} · knee`} a={dormersA[i]?.knee_wall_height_ft} b={dormersB[i]?.knee_wall_height_ft} />
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
