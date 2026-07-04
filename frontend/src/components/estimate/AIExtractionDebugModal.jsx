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

import React, { useMemo, useState } from "react";
import { X, Camera, Layers, Copy, Check } from "lucide-react";

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
      className={`border ${focused ? "border-[#0EA5E9] shadow-[0_0_0_2px_#BAE6FD]" : "border-[#E4E4E7]"} bg-white`}
      data-testid={`debug-photo-card-${idx}`}
    >
      <div className="flex items-center gap-2 px-3 py-2 bg-[#F4F4F5] border-b border-[#E4E4E7]">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#0EA5E9]">P{idx}</span>
        <span className="text-[11px] text-[#52525B] font-mono">
          {coalesce(p.elevation)} <span className="text-[#A1A1AA]">·</span>{" "}
          {p.elevation_confidence != null ? `${p.elevation_confidence}%` : "conf ?"}
        </span>
      </div>
      <div className="flex gap-3 p-3">
        {fullUrl && (
          <img
            src={fullUrl}
            alt={`Photo ${idx}`}
            className="w-24 h-24 object-cover flex-shrink-0 border border-[#E4E4E7]"
          />
        )}
        <div className="flex-1 min-w-0 space-y-1.5 text-[11px] font-mono-num">
          <Row label="Reasoning">{coalesce(p.elevation_reasoning)}</Row>
          <Row label="Walls visible">
            {(p.walls_visible && p.walls_visible.length)
              ? p.walls_visible.join(", ")
              : <span className="text-[#A1A1AA] italic">not reported</span>}
          </Row>
          <Row label="Eave observed">
            {p.eave_height_ft_observed != null
              ? <span className="font-bold text-[#0EA5E9]">{fmtFt(p.eave_height_ft_observed)}</span>
              : <span className="text-[#A1A1AA] italic">null (not measurable)</span>}
            {p.eave_reasoning && (
              <div className="text-[10px] text-[#71717A] mt-0.5">{p.eave_reasoning}</div>
            )}
          </Row>
          <Row label="Pitch observed">
            {coalesce(p.pitch_ratio_observed, <span className="text-[#A1A1AA] italic">null</span>)}
          </Row>
          <Row label="Gable Δh">
            {p.gable_triangle_height_ft_observed != null
              ? fmtFt(p.gable_triangle_height_ft_observed)
              : <span className="text-[#A1A1AA] italic">null</span>}
          </Row>
          <Row label="Dormers here">
            <span className={p.dormers_observed_count ? "font-bold text-[#0EA5E9]" : ""}>
              {coalesce(p.dormers_observed_count, 0)}
            </span>
          </Row>
          {p.notes && (
            <Row label="Notes">
              <span className="text-[#71717A]">{p.notes}</span>
            </Row>
          )}
          {p.openings_this_photo && p.openings_this_photo.length > 0 && (
            <div className="pt-1">
              <div className="text-[9px] uppercase tracking-wider text-[#71717A] font-bold mb-0.5">
                Openings ({p.openings_this_photo.length})
              </div>
              <div className="space-y-0.5">
                {p.openings_this_photo.map((o, i) => (
                  <div key={i} className="text-[10px] flex items-center gap-1.5">
                    <span className="text-[#A1A1AA]">·</span>
                    <span className="font-bold text-[#3F3F46]">{o.type}</span>
                    <span className="text-[#52525B]">{fmtIn(o.width_in)}×{fmtIn(o.height_in)}</span>
                    {o.opening_id && <span className="text-[#71717A] italic">{o.opening_id}</span>}
                    {o.bbox && Array.isArray(o.bbox) && (
                      <span className="text-[#A1A1AA]" title="pixel bbox">
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
      <span className="text-[9px] uppercase tracking-wider text-[#A1A1AA] font-bold w-20 flex-shrink-0">{label}</span>
      <div className="flex-1 min-w-0 break-words">{children}</div>
    </div>
  );
}

function WallCard({ w, onFocusPhoto }) {
  const readings = Array.isArray(w._per_photo_readings) ? w._per_photo_readings : [];
  const sourcePhotos = Array.isArray(w._source_photo_indices) ? w._source_photo_indices : [];
  return (
    <div className="border border-[#E4E4E7] bg-white" data-testid={`debug-wall-${w.label}`}>
      <div className="flex items-center gap-2 px-3 py-2 bg-[#F4F4F5] border-b border-[#E4E4E7]">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED]">Wall · {w.label}</span>
        {w.confidence != null && (
          <span className="text-[10px] text-[#52525B] font-mono">conf {w.confidence}%</span>
        )}
      </div>
      <div className="p-3 text-[11px] font-mono-num space-y-1.5">
        <Row label="Width">{fmtFt(w.width_ft)}</Row>
        <Row label="Eave (final)"><span className="font-bold text-[#7C3AED]">{fmtFt(w.height_ft)}</span></Row>
        <Row label="Gable Δh">{fmtFt(w.gable_triangle_height_ft)}</Row>
        <Row label="Dormer face">{coalesce(w.dormer_face_sqft, 0)} ft²</Row>
        <Row label="Siding %">{coalesce(w.siding_pct_this_wall, 100)}%</Row>
        <Row label="From photos">
          {sourcePhotos.length > 0
            ? <div className="flex gap-1 flex-wrap">
                {sourcePhotos.map((i) => <PhotoChip key={i} idx={i} onFocus={onFocusPhoto} />)}
              </div>
            : <span className="text-[#A1A1AA] italic">not reported</span>}
        </Row>
        {readings.length > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-wider text-[#A1A1AA] font-bold mb-0.5">
              Per-photo readings (before merge)
            </div>
            <div className="space-y-0.5 pl-2 border-l-2 border-[#E4E4E7]">
              {readings.map((r, i) => (
                <div key={i} className="text-[10px] flex items-center gap-2">
                  <PhotoChip idx={r.photo_idx} onFocus={onFocusPhoto} />
                  <span className="text-[#52525B]">
                    eave={fmtFt(r.eave_ft)} · gable={fmtFt(r.gable_triangle_ft)}
                  </span>
                  {r.notes && <span className="text-[#71717A] italic">{r.notes}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
        {w._reconciliation_note && (
          <div className="mt-1 px-2 py-1 bg-[#EDE9FE] border border-[#DDD6FE] text-[10px] text-[#5B21B6]">
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
      className="flex items-center gap-2 px-2 py-1.5 border-b border-[#F4F4F5] last:border-b-0 text-[11px]"
      data-testid={`debug-opening-${i}`}
    >
      <span className="w-16 text-[#52525B] font-mono truncate">{o.type}</span>
      <span className="w-14 text-[#3F3F46] font-mono">{fmtIn(o.width_in)}×{fmtIn(o.height_in)}</span>
      <span className="w-14 text-[#52525B] font-mono truncate" title={o.style}>{o.style || "—"}</span>
      <span className="w-12 text-[#52525B] font-mono truncate">{o.wall || "—"}</span>
      <div className="flex gap-1 min-w-0 flex-1">
        {sources.length > 0
          ? sources.map((idx) => <PhotoChip key={idx} idx={idx} onFocus={onFocusPhoto} />)
          : <span className="text-[#A1A1AA] italic text-[10px]">no photo tag</span>}
      </div>
      {o._reconciliation_note && (
        <span className="text-[10px] text-[#71717A] italic truncate" title={o._reconciliation_note}>
          {o._reconciliation_note}
        </span>
      )}
    </div>
  );
}

export default function AIExtractionDebugModal({ preview, photoUrls, onClose }) {
  const [focusedPhoto, setFocusedPhoto] = useState(null);
  const [rawExpanded, setRawExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const raw = preview?.raw_ai || {};
  // Iter 79j.37 — When the two-phase pipeline ran, `preview.raw_per_photo`
  // contains the ACTUAL per-photo Claude call outputs (one call per
  // photo), not the after-the-fact recollection embedded in the
  // reconciled JSON. Prefer those for the LEFT column. Fall back to
  // the single-call schema (`raw.photos`) for legacy runs.
  const rawPerPhoto = Array.isArray(preview?.raw_per_photo) ? preview.raw_per_photo : null;
  const pipelineLabel = preview?.pipeline || raw._pipeline || (rawPerPhoto ? "two_phase" : "single_call");
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
      className="fixed inset-0 z-[70] bg-[#09090B]/80 flex items-center justify-center p-4"
      data-testid="debug-extraction-modal"
    >
      <div className="bg-white w-full max-w-[1400px] h-[92vh] flex flex-col border border-[#E4E4E7]">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-[#E4E4E7] bg-[#FAFAFA]">
          <Layers className="w-4 h-4 text-[#7C3AED]" />
          <div className="flex-1">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#09090B]" data-testid="debug-modal-title">
              Extraction debug
            </h3>
            <p className="text-[11px] text-[#71717A] mt-0.5">
              Left: what Claude saw in each photo. Right: the reconciled house — with the photos each final number was drawn from and the merge trace.
            </p>
          </div>
          <span
            className={`text-[10px] uppercase font-bold tracking-wider px-2 py-1 border ${
              pipelineLabel === "two_phase"
                ? "bg-[#DCFCE7] text-[#166534] border-[#16A34A]"
                : "bg-[#FEF3C7] text-[#92400E] border-[#F59E0B]"
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
            className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[#52525B] hover:text-[#09090B] border border-[#E4E4E7] hover:bg-white flex items-center gap-1.5"
            data-testid="debug-copy-raw-btn"
            title="Copy the raw AI JSON to clipboard — paste it into a bug report or diff two runs"
          >
            {copied ? <Check className="w-3 h-3 text-[#16A34A]" /> : <Copy className="w-3 h-3" />}
            {copied ? "Copied" : "Copy raw JSON"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-[#52525B] hover:text-[#09090B] hover:bg-[#F4F4F5]"
            data-testid="debug-close-btn"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Two-column body */}
        <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
          {/* LEFT — Per-photo raw observations */}
          <div className="overflow-y-auto p-4 space-y-3 border-r border-[#E4E4E7] bg-[#FAFAFA]">
            <div className="flex items-center gap-2 mb-1">
              <Camera className="w-3.5 h-3.5 text-[#0EA5E9]" />
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-[#0EA5E9]">
                {pipelineLabel === "two_phase" ? "Per-photo raw (Phase A)" : "Per-photo (Claude's recollection)"}
                {" "}({photos.length} reported / {photoUrls?.length || 0} uploaded)
              </h4>
            </div>
            {maxIdx < 0 && (
              <div className="text-[11px] text-[#A1A1AA] italic px-3 py-8 text-center">
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
          <div className="overflow-y-auto p-4 space-y-3 bg-white">
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-3.5 h-3.5 text-[#7C3AED]" />
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED]">
                Reconciled house — click any P# chip to jump to that photo
              </h4>
            </div>

            {/* Top-level scalars + reconciliation notes */}
            <div className="border border-[#E4E4E7] bg-white">
              <div className="px-3 py-2 bg-[#F4F4F5] border-b border-[#E4E4E7]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED]">House-level</span>
              </div>
              <div className="p-3 text-[11px] font-mono-num space-y-1.5">
                <Row label="Avg eave">{fmtFt(raw.avg_wall_height_ft)}</Row>
                {reconciliation.avg_wall_height_ft && (
                  <ReconNote>{reconciliation.avg_wall_height_ft}</ReconNote>
                )}
                <Row label="Story count">{coalesce(raw.story_count)}</Row>
                {raw.story_count_reasoning && (
                  <div className="text-[10px] text-[#71717A] pl-22">{raw.story_count_reasoning}</div>
                )}
                <Row label="Roof type">
                  <span className="font-bold text-[#7C3AED]">{coalesce(raw.roof_type)}</span>
                  {raw.roof_type_confidence != null && (
                    <span className="text-[#A1A1AA] ml-1">({Math.round(raw.roof_type_confidence * 100)}%)</span>
                  )}
                </Row>
                {raw.roof_type_reasoning && (
                  <div className="text-[10px] text-[#71717A] pl-22">{raw.roof_type_reasoning}</div>
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
              <div className="border border-[#E4E4E7] bg-white" data-testid="debug-dormer-card">
                <div className="px-3 py-2 bg-[#F4F4F5] border-b border-[#E4E4E7]">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED]">Dormer</span>
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

            <div className="border border-[#E4E4E7] bg-white" data-testid="debug-openings-card">
              <div className="px-3 py-2 bg-[#F4F4F5] border-b border-[#E4E4E7]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED]">
                  Openings ({openings.length})
                </span>
              </div>
              {openings.length === 0
                ? <div className="p-3 text-[11px] text-[#A1A1AA] italic">No openings extracted.</div>
                : openings.map((o, i) => <OpeningRow key={i} o={o} i={i} onFocusPhoto={focusPhoto} />)}
            </div>

            <details className="border border-[#E4E4E7] bg-white" open={rawExpanded} onToggle={(e) => setRawExpanded(e.target.open)}>
              <summary className="px-3 py-2 text-[10px] uppercase tracking-wider text-[#71717A] font-bold cursor-pointer bg-[#F4F4F5]">
                Full raw JSON
              </summary>
              <pre className="text-[10px] font-mono-num p-3 overflow-x-auto max-h-96 bg-[#09090B] text-[#E4E4E7]" data-testid="debug-raw-json-pre">
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
    <div className="ml-22 mt-1 px-2 py-1 bg-[#EDE9FE] border border-[#DDD6FE] text-[10px] text-[#5B21B6]">
      <b className="uppercase tracking-wider text-[9px]">Reconciliation:</b> {children}
    </div>
  );
}
