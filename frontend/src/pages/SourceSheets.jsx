import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";

/* SOURCE VIEW — READ-ONLY intake evidence, generalized to EVERY door
   (Howard, ruled 2026-07-20; blueprint mode shipped + accepted earlier the
   same day and unchanged). Routes: /estimate/:id/source-view (unified) with
   /estimate/:id/source-sheets kept as an alias so the accepted blueprint
   surface never moves. Zero writes: GETs only (estimate + blueprint latest
   + photo/hover latest). Door precedence: blueprint → photo → hover.
   - Blueprint: the exact compressed sheets Claude analyzed (durable store),
     per-sheet provenance, 24h run TTL defused by the CUT archive.
   - Photo: the exact photos the run consumed, numbered in consumption
     order (the SAME indices the elevation sheets' per-photo readings
     cite), 30-day run TTL defused by the CUT archive.
   - Hover: NO visual source is ever retained (PDFs process in memory) —
     an honest import reference (run identity + imported measurements)
     renders instead. */

const fmtNum = (n) => Number(n || 0).toLocaleString();
const UNIT_BY_KEY = (k) =>
  k.endsWith("_sqft") ? "ft²" : k.endsWith("_lf") ? "LF" : "";

// Mirrors the import surfaces' result summary — same numbers, same basis.
const SUMMARY_KEYS = [
  "siding_sqft", "siding_with_openings_sqft", "eaves_lf", "rakes_lf",
  "starter_lf", "outside_corner_lf", "inside_corner_lf", "window_count",
  "entry_door_count", "patio_door_count", "garage_door_count", "stories",
];
const KEY_LABEL = {
  siding_sqft: "Siding",
  siding_with_openings_sqft: "Siding + openings <20ft²",
  eaves_lf: "Eaves",
  rakes_lf: "Rakes",
  starter_lf: "Starter",
  outside_corner_lf: "Outside corners",
  inside_corner_lf: "Inside corners",
  window_count: "Windows",
  entry_door_count: "Entry doors",
  patio_door_count: "Patio doors",
  garage_door_count: "Garage doors",
  stories: "Stories",
};

function SummaryTable({ measurements, testid }) {
  const rows = SUMMARY_KEYS.filter(
    (k) => measurements[k] !== null && measurements[k] !== undefined
  );
  if (rows.length === 0) return null;
  return (
    <table className="w-full text-sm" data-testid={testid}>
      <tbody>
        {rows.map((k) => (
          <tr key={k} className="border-b border-[var(--border)] last:border-0">
            <td className="py-1.5 text-[var(--ink-2)]">{KEY_LABEL[k] || k}</td>
            <td className="py-1.5 text-right font-mono-num font-bold text-[var(--ink)]">
              {fmtNum(measurements[k])} {UNIT_BY_KEY(k)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function SourceSheets() {
  const { id } = useParams();
  const [est, setEst] = useState(null);
  const [run, setRun] = useState(undefined); // blueprint run: undefined=loading, null=none
  const [aiRun, setAiRun] = useState(undefined); // photo / hover-materialized run
  const [err, setErr] = useState("");
  const [zoomIdx, setZoomIdx] = useState(null);

  useEffect(() => {
    setErr("");
    Promise.all([
      api.get(`/estimates/${id}`),
      api.get(`/measure/ai-blueprint/latest-for-estimate/${id}`),
      api.get(`/measure/ai-measure/latest-for-estimate/${id}`),
    ])
      .then(([e, r, a]) => {
        setEst(e.data);
        setRun(r.data?.run || null);
        setAiRun(a.data?.run || null);
      })
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load the source view"));
  }, [id]);

  // Door precedence: blueprint → photo → hover (ruled 2026-07-20).
  const isHoverRun = aiRun && (aiRun.source === "hover" || String(aiRun.run_id || "").startsWith("hover-"));
  const photos = (!isHoverRun && aiRun?.photo_paths ? aiRun.photo_paths : "").split(",").filter(Boolean);
  const mode = run ? "blueprint" : (photos.length > 0 ? "photo" : (isHoverRun ? "hover" : "none"));

  const pages = (run?.page_paths || "").split(",").filter(Boolean);
  const rid8 = String(run?.run_id || "").slice(0, 8);
  const measurements = (run?.result || {}).measurements || {};
  const uploadedAt = run?.age_seconds != null
    ? new Date(Date.now() - run.age_seconds * 1000)
    : null;

  const pid8 = String(aiRun?.run_id || "").slice(0, 8);
  const photoKinds = (aiRun?.photo_kinds || "").split(",").map((s) => s.trim());
  const photoMeasurements = (aiRun?.result || {}).measurements || {};
  const photoUploadedAt = aiRun?.age_seconds != null
    ? new Date(Date.now() - aiRun.age_seconds * 1000)
    : null;

  const items = mode === "photo" ? photos : pages;

  const onKey = useCallback((e) => {
    if (zoomIdx == null) return;
    if (e.key === "Escape") setZoomIdx(null);
    if (e.key === "ArrowRight") setZoomIdx((i) => Math.min(i + 1, items.length - 1));
    if (e.key === "ArrowLeft") setZoomIdx((i) => Math.max(i - 1, 0));
  }, [zoomIdx, items.length]);
  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  if (err) return <div className="p-8 text-sm" data-testid="source-sheets-error">{err}</div>;
  if (run === undefined || aiRun === undefined) {
    return <div className="p-8 text-sm" data-testid="source-sheets-loading">Loading source view…</div>;
  }

  const title = mode === "photo" ? "Source Photos"
    : mode === "hover" ? "Hover Import Reference"
    : "Blueprint Source Sheets";

  return (
    <div className="max-w-6xl mx-auto px-4 py-6" data-testid="source-sheets-page">
      {/* ── Header + per-estimate provenance ─────────────────────────── */}
      <div className="mb-1 flex items-baseline gap-3 flex-wrap">
        <h1 className="font-heading text-xl text-[var(--ink)]">{title}</h1>
        <span className="text-sm text-[var(--muted)]" data-testid="source-sheets-estimate">
          {est?.estimate_number ? `Estimate ${est.estimate_number}` : `Estimate ${id.slice(0, 8)}`}
          {est?.customer_name ? ` — ${est.customer_name}` : ""}
        </span>
        <Link to={`/estimate/${id}`} className="text-xs underline text-[var(--muted)]" data-testid="source-sheets-back-link">
          ← back to estimate
        </Link>
      </div>
      <p className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-4" data-testid="source-sheets-readonly-note">
        READ-ONLY — the exact intake evidence the AI worked from, served from the durable store. Nothing on this page writes.
      </p>

      {mode === "none" && (
        <div className="card p-6 text-sm text-[var(--ink-2)]" data-testid="source-sheets-no-run">
          <div className="font-bold mb-2">No intake run on record for this estimate.</div>
          <p className="leading-snug">
            Live run indexes expire on a TTL — 24h for blueprint runs, 30 days for photo
            runs. APPLIED takeoffs survive it: the CUT archives them and this view serves
            the archived index indefinitely. Neither a live nor an archived run exists on
            any door; a fresh import restores the view.
          </p>
        </div>
      )}

      {mode === "blueprint" && (pages.length === 0 ? (
        <div className="card p-6 text-sm text-[var(--ink-2)]" data-testid="source-sheets-no-run">
          <div className="font-bold mb-2">No blueprint pages on record for this run.</div>
          <p className="leading-snug">
            The live run index expires 24h after upload (TTL). APPLIED takeoffs survive
            it — the CUT archives them and this viewer serves the archived index
            indefinitely. A fresh blueprint upload or re-run restores the view.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ── Source pages (2/3) ─────────────────────────────────── */}
          <div className="lg:col-span-2">
            <div
              className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2"
              data-testid="source-sheets-provenance"
            >
              blueprint extraction run {rid8} · {pages.length} sheet(s)
              {run.page_count && run.page_count !== pages.length ? ` of ${run.page_count} queued` : ""}
              {uploadedAt ? ` · uploaded ${uploadedAt.toLocaleString()}` : ""} · status {run.status}
              {run.archived ? " · ARCHIVED INDEX (served past TTL via the CUT archive)" : ""}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {pages.map((name, i) => (
                <figure key={name} className="card p-2">
                  <button
                    type="button"
                    className="block w-full cursor-zoom-in"
                    onClick={() => setZoomIdx(i)}
                    data-testid={`source-sheet-thumb-${i}`}
                    title="Click to zoom"
                  >
                    <img
                      src={`/api/uploads/${name}`}
                      alt={`Blueprint sheet ${i + 1}`}
                      className="w-full h-auto block border border-[var(--border)]"
                      loading="lazy"
                    />
                  </button>
                  <figcaption
                    className="mt-1.5 text-[10px] uppercase tracking-wider text-[var(--muted)] font-mono-num"
                    data-testid={`source-sheet-caption-${i}`}
                  >
                    Sheet {i + 1} of {pages.length} · {name} · run {rid8}
                  </figcaption>
                </figure>
              ))}
            </div>
          </div>

          {/* ── AI measure alongside (1/3) ─────────────────────────── */}
          <div>
            <div className="card p-4 sticky top-4" data-testid="source-sheets-ai-summary">
              <div className="section-tag mb-1">AI Measure — same run</div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-3">
                AI-READ · blueprint extraction run {rid8} — compare against the sheets at left
              </div>
              {SUMMARY_KEYS.every((k) => measurements[k] === null || measurements[k] === undefined) ? (
                <div className="text-sm text-[var(--ink-2)]" data-testid="source-sheets-ai-summary-empty">
                  No completed AI read on this run (status: {run.status}).
                </div>
              ) : (
                <SummaryTable measurements={measurements} testid="source-sheets-ai-summary-table" />
              )}
            </div>
          </div>
        </div>
      ))}

      {mode === "photo" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ── Source photos (2/3) ────────────────────────────────── */}
          <div className="lg:col-span-2">
            <div
              className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2"
              data-testid="source-photos-provenance"
            >
              photo extraction run {pid8} · {photos.length} photo(s)
              {photoUploadedAt ? ` · uploaded ${photoUploadedAt.toLocaleString()}` : ""} · status {aiRun.status}
              {aiRun.archived ? " · ARCHIVED INDEX (served past TTL via the CUT archive)" : ""}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {photos.map((name, i) => (
                <figure key={name} className="card p-2">
                  <button
                    type="button"
                    className="block w-full cursor-zoom-in"
                    onClick={() => setZoomIdx(i)}
                    data-testid={`source-photo-thumb-${i}`}
                    title="Click to zoom"
                  >
                    <img
                      src={`/api/uploads/${name}`}
                      alt={`Source photo ${i + 1}`}
                      className="w-full h-auto block border border-[var(--border)]"
                      loading="lazy"
                    />
                  </button>
                  <figcaption
                    className="mt-1.5 text-[10px] uppercase tracking-wider text-[var(--muted)] font-mono-num"
                    data-testid={`source-photo-caption-${i}`}
                  >
                    Photo {i + 1} of {photos.length}{photoKinds[i] ? ` · ${photoKinds[i]}` : ""} · {name} · run {pid8}
                  </figcaption>
                </figure>
              ))}
            </div>
            <div className="text-[10px] text-[var(--muted)] mt-2" data-testid="source-photos-numbering-note">
              Numbering = the order the run consumed the photos — the same indices the
              elevation sheets' per-photo readings cite.
            </div>
          </div>

          {/* ── AI measure alongside (1/3) ─────────────────────────── */}
          <div>
            <div className="card p-4 sticky top-4" data-testid="source-photos-ai-summary">
              <div className="section-tag mb-1">AI Measure — same run</div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-3">
                AI-READ · photo extraction run {pid8} — compare against the photos at left
              </div>
              <SummaryTable measurements={photoMeasurements} testid="source-photos-ai-summary-table" />
            </div>
          </div>
        </div>
      )}

      {mode === "hover" && (
        <div className="max-w-2xl" data-testid="source-hover-reference">
          <div
            className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-2"
            data-testid="source-hover-provenance"
          >
            hover import run {pid8}
            {photoUploadedAt ? ` · imported ${photoUploadedAt.toLocaleString()}` : ""} · status {aiRun.status}
            {aiRun.archived ? " · ARCHIVED INDEX (served past TTL via the CUT archive)" : ""}
          </div>
          <div className="card p-4 mb-4 text-sm text-[var(--ink-2)]" data-testid="source-hover-no-visual-note">
            No visual source retained — HOVER PDFs are processed in memory and never
            stored. This reference shows the run identity and the measurements the
            import carried; the original report lives in the contractor's HOVER account.
          </div>
          <div className="card p-4">
            <div className="section-tag mb-2">Imported measurements — same run</div>
            <SummaryTable measurements={photoMeasurements} testid="source-hover-summary-table" />
          </div>
        </div>
      )}

      {/* ── Lightbox (blueprint + photo modes) ───────────────────────── */}
      {zoomIdx != null && items[zoomIdx] && (
        <div
          className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-6"
          onClick={() => setZoomIdx(null)}
          data-testid="source-sheets-lightbox"
        >
          <img
            src={`/api/uploads/${items[zoomIdx]}`}
            alt={`Source item ${zoomIdx + 1} (zoomed)`}
            className="max-w-full max-h-[85vh] object-contain bg-white"
            onClick={(e) => e.stopPropagation()}
            data-testid="source-sheets-lightbox-img"
          />
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white text-xs font-mono-num" data-testid="source-sheets-lightbox-caption">
            {mode === "photo" ? "Photo" : "Sheet"} {zoomIdx + 1} of {items.length} · {items[zoomIdx]} · run {mode === "photo" ? pid8 : rid8} · Esc to close, ←/→ to page
          </div>
          {zoomIdx > 0 && (
            <button
              type="button"
              className="absolute left-4 top-1/2 -translate-y-1/2 text-white text-3xl px-3 py-1"
              onClick={(e) => { e.stopPropagation(); setZoomIdx(zoomIdx - 1); }}
              data-testid="source-sheets-lightbox-prev"
            >‹</button>
          )}
          {zoomIdx < items.length - 1 && (
            <button
              type="button"
              className="absolute right-4 top-1/2 -translate-y-1/2 text-white text-3xl px-3 py-1"
              onClick={(e) => { e.stopPropagation(); setZoomIdx(zoomIdx + 1); }}
              data-testid="source-sheets-lightbox-next"
            >›</button>
          )}
          <button
            type="button"
            className="absolute top-4 right-4 text-white text-2xl px-3 py-1"
            onClick={() => setZoomIdx(null)}
            data-testid="source-sheets-lightbox-close"
          >✕</button>
        </div>
      )}
    </div>
  );
}
