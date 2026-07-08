// AI Photo Measure button.
//
// Mirrors the HOVER import button visually + behaviorally so contractors
// have a familiar workflow:
//   click → upload 2-8 phone photos (and optional reference dim) →
//   preview Claude's diff → Apply.
//
// The backend (/api/measure/ai-measure) returns the same `measurements`
// shape as HOVER, so we hand it to the same `onApply` callback the page
// already uses for HOVER.
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, X, Check, Loader2, AlertTriangle, Camera, Upload, Ruler, RotateCcw, Wand2, FileText, Printer, Bug, Lightbulb, ScanSearch, HelpCircle } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import PhotoMeasureButton from "@/components/estimate/PhotoMeasureButton";
import PhotoAnnotateModal from "@/components/estimate/PhotoAnnotateModal";
// Iter 78z — Profile annotator: lets contractor draw boxes tagged
// Shake / B&B / etc. so the AI worker treats those regions as
// authoritative accent material. Both AI Measure + Blueprint share it.
import ProfileAnnotator from "@/components/estimate/ProfileAnnotator";
import AnnotatorErrorBoundary from "@/components/estimate/AnnotatorErrorBoundary";
import GuidedCaptureWizard from "@/components/estimate/GuidedCaptureWizard";
import { renderAnnotated, describeAnnotations } from "@/lib/photoAnnotate";
// Iter 78s — HOVER-style elevation drawings, generated from the AI Measure
// raw_ai output.
// Iter 79j.12 — ElevationDrawing / Elevation3DPreview imports removed
// with the Elevation Drawings preview block. `buildElevationsFromAIMeasure`
// is still used further down for the report PDF sheet layout.
import { buildElevationsFromAIMeasure } from "@/lib/elevationBuilder";
// Iter 78z (P1.3) — Per-Elevation Breakdown card + "+ Add Accent" override
import PerElevationBreakdownCard from "@/components/estimate/PerElevationBreakdownCard";
import { printTakeoff } from "@/lib/printTakeoff";
// Iter 79j.22 — 3D House Model view (parametric Three.js render from raw_ai)
import HouseModel3D from "@/components/estimate/HouseModel3D";
// Iter 79j.36 — Debug view: per-photo raw observations + reconciled
// house JSON with provenance. Behind Advanced.
import AIExtractionDebugModal from "@/components/estimate/AIExtractionDebugModal";

const ELEVATION_OPTIONS = [
  { key: "",            label: "Untagged" },
  { key: "front",       label: "Front" },
  { key: "front-left",  label: "Front-Left corner" },
  { key: "left",        label: "Left" },
  { key: "rear-left",   label: "Rear-Left corner" },
  { key: "back",        label: "Back" },
  { key: "rear-right",  label: "Rear-Right corner" },
  { key: "right",       label: "Right" },
  { key: "front-right", label: "Front-Right corner" },
  { key: "aerial",      label: "Aerial (satellite)" },
  { key: "detail",      label: "Detail" },
];
const annotEmpty = (a) =>
  !a || (!a.reference && !a.windowReference && (!a.zones || a.zones.length === 0) && (!a.elevation || a.elevation === "") && !a.targetPin);

const KEY_LABELS = {
  siding_sqft: "Siding",
  siding_with_openings_sqft: "Siding (+openings)",
  opening_sqft: "Openings (ft²)",
  eaves_lf: "Eaves",
  rakes_lf: "Rakes",
  opening_count: "Openings",
  window_count: "Windows",
  entry_door_count: "Entry doors",
  patio_door_count: "Patio doors",
  garage_door_count: "Garage doors",
  opening_perimeter_lf: "Opening perimeter",
};
const fmt = (n) => Number(n || 0).toLocaleString();
const unitOf = (k) =>
  k.endsWith("_sqft") ? "ft²" : k.endsWith("_lf") ? "LF" : "";

export default function AIMeasureButton({ kind, onApply, address, overhangIn, estimateId, estimate }) {
  const fileRef = useRef();
  // `files` is the locally-selected file objects (used for previews until
  // upload completes); `photoUrls` is the canonical server-side list that
  // survives across sessions. Once a file finishes uploading, the URL is
  // appended to photoUrls and the local File is discarded.
  const [files, setFiles] = useState([]);
  const [photoUrls, setPhotoUrls] = useState([]); // ["/api/uploads/<uuid>.jpg", …]
  // Iter 56: per-photo pre-AI annotations. Keyed by photo filename
  // (matches the value stored in photoUrls). Each entry holds:
  //   { elevation: "front"|"back"|"left"|"right"|"detail"|"",
  //     reference: { p1, p2, inches } | null,
  //     zones: Array<{ kind, category, points }> }
  // Annotations are burned into the photo via Canvas in runMeasure()
  // before sending to Claude, and described as text alongside.
  const [photoAnnotations, setPhotoAnnotations] = useState({});
  const [annotateOpenFor, setAnnotateOpenFor] = useState(null); // filename or null
  // Iter 78z — Profile annotator modal (box-tag Shake / B&B regions).
  const [profileAnnotatorOpen, setProfileAnnotatorOpen] = useState(false);
  const [savedProfileAnnotations, setSavedProfileAnnotations] = useState({});
  // Iter 56c — free aerial fetch via Esri World Imagery.
  const [satBusy, setSatBusy] = useState(false);
  const [resumePrompt, setResumePrompt] = useState(false); // shows banner
  // Iter 79j.64 — Fix 2: specifics for the loud recovery banner
  // (photo count / result / marker counts pulled from the server
  // session at detection time).
  const [pendingSessionMeta, setPendingSessionMeta] = useState(null);
  // Iter 79j.64 — Fix 3: destructive-action confirm state.
  // null | { kind: "start_over" | "start_fresh" | "remove_photo", idx?, name? }
  const [destructiveConfirm, setDestructiveConfirm] = useState(null);
  const [refDim, setRefDim] = useState("");
  const [wallHeight, setWallHeight] = useState("");
  const [sidingPct, setSidingPct] = useState("");
  // Iter 57g — optional course-counting calibration. If the contractor
  // tells us the brick course size or the siding exposure, Claude can
  // size windows by counting visible rows in the photo — far more
  // accurate than estimating pixel ratios. Defaults:
  //   • Brick: 8 in (standard 3-bricks-per-8" course w/ 3/8" mortar)
  //   • Siding D5: 5 in, D6: 6 in, Cedar Impressions: 7 in (default 5)
  // Blank = "don't pass to Claude"; user can also disable each
  // independently by emptying the field.
  const [brickCourse, setBrickCourse] = useState("");
  const [sidingExposure, setSidingExposure] = useState("");
  // Iter 79j.44 — Deep Dormer Scan removed. Two-phase Phase A/B
  // owns dormer detection end-to-end. Flag no longer sent to the
  // backend; toggle UI + state variable are gone.
  // Iter 79j.15 — A/B model dropdown. Persisted so a contractor's
  // last choice survives modal close/reopen. Keys must match the
  // backend `_MODEL_CHOICES` registry.
  const [modelChoice, setModelChoice] = useState(() => {
    try {
      return localStorage.getItem("aiMeasureModelChoice") || "claude-opus-4-5";
    } catch {
      return "claude-opus-4-5";
    }
  });
  useEffect(() => {
    try { localStorage.setItem("aiMeasureModelChoice", modelChoice); } catch { /* ignore */ }
  }, [modelChoice]);
  // Iter 79j.16 — Model Comparison history state moved below `open`
  // and `preview` state declarations to avoid TDZ (state hooks
  // referenced by the effect must exist first).
  // Iter 57h — popover state for the inline "📐 Calibrate window sizing"
  // mini-panel that hangs next to the Run AI Measure button.
  const [calibOpen, setCalibOpen] = useState(false);
  // Iter 79j.11 — pre-Guided-Capture calibration prompt. Fires when
  // the contractor taps "Guided Capture" so they set the CURRENT
  // siding exposure BEFORE the first photo (contractor is at the
  // house, has line of sight to the wall — ideal moment). Does NOT
  // override the Wall / Window Reference lines the contractor draws
  // in-photo; it's an additional prompt hint to Claude on walls
  // where a red/blue reference line isn't reachable per opening.
  const [calibPrepOpen, setCalibPrepOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  // Iter 57q — when AI Measure is running, show the worker's current
  // stage ("claude" → "dormer_scan" → "aggregating" → "mapping") in the
  // Run button so the contractor knows progress is happening. Empty
  // string when idle.
  const [busyStage, setBusyStage] = useState("");
  // Iter 79j.60 — Live per-photo progress from the two-phase pipeline.
  // Populated by every /status/{run_id} poll from `phase_a_progress`.
  // Rendered as a contractor-plain HUD (photo dots + plain-english
  // status line — no wave/proxy/phase jargon per Howard 2026-07-07).
  // `null` = pipeline hasn't started or is single-call.
  const [photoProgress, setPhotoProgress] = useState(null);
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState(null); // {measurements, raw_ai}
  // Iter 79j.22 — Preview / 3D Model tab toggle inside the results block.
  // Auto-resets to "preview" whenever a new run lands so contractors see
  // the numbers first, then choose to switch to 3D for structural review.
  const [previewTab, setPreviewTab] = useState("preview");
  useEffect(() => {
    if (preview) setPreviewTab("preview");
  }, [preview?.run_id, preview?.session_id, preview?.model]);
  // Iter 79j.16 — Model Comparison history. Refetched whenever the
  // preview flips to a new run OR the modal opens. Empty until at
  // least one "done" run exists for this estimate. Declared here so
  // both `open` and `preview` are in scope (avoids TDZ).
  const [modelHistory, setModelHistory] = useState([]);
  useEffect(() => {
    if (!estimateId || !open) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/measure/ai-measure/history/${estimateId}?limit=5`);
        if (!cancelled) setModelHistory(Array.isArray(data?.runs) ? data.runs : []);
      } catch {
        if (!cancelled) setModelHistory([]);
      }
    })();
    return () => { cancelled = true; };
    // Re-fetch every time a fresh preview lands (new run completed).
  }, [estimateId, open, preview?.session_id]);
  // Iter 57r — Resume support. When the modal opens we ask the
  // backend for the most recent AI Measure run for this estimate
  // (regardless of status). If it's still "running" or finished within
  // the last 30 minutes, we surface a small banner that lets the
  // contractor pick up where they left off after a page reload or
  // screen lock — no re-uploading photos, no re-running Claude.
  const [lastRun, setLastRun] = useState(null);  // { run_id, status, stage, age_seconds, photo_paths, result }
  // Iter 78z (Cross-Check) — track the active run's ID so the
  // PerElevationBreakdownCard can fire the cross-check endpoint.
  // Populated by both the fresh-run path and the resume path.
  const [currentRunId, setCurrentRunId] = useState(null);
  const [refineOpen, setRefineOpen] = useState(false);
  // Iter 51: Optional "quote gables as shake" override. Adds a shake-
  // siding line for the total gable ft² and deducts that area from the
  // main Charter Oak / Ascend siding qty so we don't double-count.
  const [quoteGablesAsShake, setQuoteGablesAsShake] = useState(false);
  const [shakeSku, setShakeSku] = useState("Pelican Bay Shakes 9\"");
  // Iter 52: Same idea for dormer faces — homeowners often want shake or
  // an accent siding on the dormer for visual interest. Independent
  // toggle + SKU from gables so they can be quoted differently.
  const [quoteDormersAsShake, setQuoteDormersAsShake] = useState(false);
  const [dormerShakeSku, setDormerShakeSku] = useState("Pelican Bay Shakes 9\"");
  // Iter 47: contractor can override Claude's wall geometry inline.
  // Tracks whether walls were edited so apply() refreshes lines via
  // /measure/map (otherwise the pre-rolled lines are reused).
  const [wallsDirty, setWallsDirty] = useState(false);
  // Iter 55: how to merge the values coming out of Refine on Photo into
  // the AI's aggregate. Howard's mental model is "I'm tapping each
  // elevation in turn; the LFs and counts should ADD together across
  // refines." Previously the merge was a hard overwrite which silently
  // downgraded the multi-photo aggregate (136 LF eaves → 58 LF, 11
  // windows → 3) whenever the contractor refined a single elevation.
  //   "add"     — running total grows with each refine (default)
  //   "max"     — take the larger of refined vs current (safe baseline)
  //   "replace" — refined wins (legacy Iter 39 behavior)
  // Stored in localStorage so the contractor's pick sticks across jobs.
  const [refineMergeMode, setRefineMergeMode] = useState(() => {
    try {
      const v = localStorage.getItem("aiMeasureRefineMergeMode");
      return v === "max" || v === "replace" || v === "add" ? v : "max";
    } catch {
      return "max";
    }
  });
  useEffect(() => {
    try { localStorage.setItem("aiMeasureRefineMergeMode", refineMergeMode); } catch { /* ignore */ }
  }, [refineMergeMode]);
  // Iter 57: hide Refine on Photo behind an Advanced Tools toggle.
  // Now that pre-AI annotations (Iter 56) cover most use cases, Refine
  // on Photo is the rare-case escape hatch — keep it accessible but out
  // of the primary flow.
  // Iter 79j.36 — Debug modal open state. Advanced-only. Shows per-
  // photo raw observations + the reconciled house JSON side-by-side,
  // so contractors can diagnose whether variance between runs is a
  // detection problem (photos disagree) or a reconciliation problem
  // (photos agree but the merge drifts).
  const [debugOpen, setDebugOpen] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(() => {
    try {
      return localStorage.getItem("aiMeasureShowAdvanced") === "1";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem("aiMeasureShowAdvanced", showAdvanced ? "1" : "0");
    } catch { /* ignore */ }
  }, [showAdvanced]);

  // Iter 79j.57c — First-run onboarding checklist. Explains the marker
  // SOP so contractors don't ship 8-photo runs that only mark corners
  // (which the reconciler treats as low-confidence). localStorage
  // remembers the dismissal so it doesn't nag every session, but the
  // in-modal Tips button re-opens it on demand.
  const [showOnboarding, setShowOnboarding] = useState(() => {
    try {
      return localStorage.getItem("aiMeasureOnboardingSeen") !== "1";
    } catch {
      return true;
    }
  });
  const dismissOnboarding = () => {
    try { localStorage.setItem("aiMeasureOnboardingSeen", "1"); } catch { /* ignore */ }
    try { localStorage.setItem("aiMeasureUnanchoredNudgeSeen", "1"); } catch { /* ignore */ }
    setShowOnboarding(false);
    setUnanchoredNudgeActive(false);
  };

  // Iter 79j.61 — Contextual accuracy nudge. Howard 2026-07-07: once
  // scale-refs plumbing is live, auto-trigger the checklist the FIRST
  // time a contractor uploads photos WITHOUT any `_scale_refs`, so
  // the warning lands at the exact moment the accuracy risk exists.
  // Uses a SEPARATE localStorage key from the first-run nudge so
  // dismissing "show once" doesn't also dismiss "you have photos but
  // no markers".
  const hasAnyScaleRef = useMemo(() => {
    const refs = photoAnnotations?._scale_refs;
    return refs && typeof refs === "object" && Object.keys(refs).length > 0;
  }, [photoAnnotations]);
  const [unanchoredNudgeActive, setUnanchoredNudgeActive] = useState(false);
  useEffect(() => {
    if (!open) return;
    if (photoUrls.length === 0) return;      // no photos → nothing to nudge
    if (hasAnyScaleRef) return;               // markers present → healthy
    let seen = false;
    try { seen = localStorage.getItem("aiMeasureUnanchoredNudgeSeen") === "1"; }
    catch { seen = false; }
    if (seen) return;
    setShowOnboarding(true);
    setUnanchoredNudgeActive(true);
  }, [open, photoUrls.length, hasAnyScaleRef]);

  // Iter 79j.57d — Re-run confirmation. Howard buried a graduating run
  // once with a stray click; a confirmation dialog now guards ONLY the
  // done+reconciled case (dismissing on failed runs would just train
  // click-through). The dialog is intentionally SPECIFIC — "N dormers,
  // N sqft" instead of "are you sure?" — because generic warnings get
  // reflexively dismissed.
  const [rerunConfirm, setRerunConfirm] = useState(false);
  const attemptRerun = () => {
    const ra = preview?.raw_ai || null;
    const hasGoodReconciled = !!(ra
      && !ra._reconciliation_error
      && (Array.isArray(ra.walls) ? ra.walls.length : 0) > 0);
    if (hasGoodReconciled) {
      setRerunConfirm(true);
      return;
    }
    runMeasure();
  };

  // Iter 57d — Window styles dropdown. Kept in display order grouped
  // by category so the contractor can scan it quickly. Empty option
  // at the top means "not a window / not known yet".
  const WINDOW_STYLES = [
    { value: "", label: "— Select / N/A —" },
    { value: "Double Hung", label: "Double Hung" },
    { value: "Single Hung", label: "Single Hung" },
    { value: "Casement", label: "Casement" },
    { value: "Twin Casement", label: "Twin Casement" },
    { value: "Awning", label: "Awning" },
    { value: "Hopper", label: "Hopper" },
    { value: "2-Lite Slider", label: "2-Lite Slider (XO)" },
    { value: "3-Lite Slider", label: "3-Lite Slider (XOX)" },
    { value: "Picture", label: "Picture / Fixed" },
    { value: "Twin Double Hung", label: "Twin Double Hung" },
    { value: "Twin Single Hung", label: "Twin Single Hung" },
    { value: "Triple Double Hung", label: "Triple Double Hung" },
    { value: "Bay Window", label: "Bay Window" },
    { value: "Bow Window", label: "Bow Window" },
    { value: "Half-Round", label: "Half-Round" },
    { value: "Quarter-Round", label: "Quarter-Round" },
    { value: "Arch", label: "Arch / Eyebrow" },
    { value: "Octagon", label: "Octagon" },
    { value: "Hexagon", label: "Hexagon" },
    { value: "Garden Window", label: "Garden Window" },
    { value: "Other Shape", label: "Other / Custom Shape" },
  ];

  // Update the AI-detected style for one opening_schedule row. We mutate
  // the saved preview.measurements._ai_openings_schedule so the change
  // sticks across re-renders + the autosave hook pushes it back to the
  // ai_measure_sessions doc. Also propagates to preview.raw_ai.openings
  // (best-effort match by wall+size+type) so the Apply Measurements
  // step uses the corrected style when populating Vero rows.
  const updateOpeningStyle = (elev, type, sizeLabel, w, h, newStyle) => {
    setPreview((prev) => {
      if (!prev) return prev;
      const m = prev.measurements || {};
      const sched = m._ai_openings_schedule || [];
      const nextSched = sched.map((row) => {
        if (
          (row.elevation || "").toLowerCase() === (elev || "").toLowerCase() &&
          (row.type || "").toLowerCase() === (type || "").toLowerCase() &&
          (row.size_label || "") === (sizeLabel || "") &&
          Math.round(Number(row.width_in) || 0) === Math.round(Number(w) || 0) &&
          Math.round(Number(row.height_in) || 0) === Math.round(Number(h) || 0)
        ) {
          return { ...row, style: newStyle };
        }
        return row;
      });
      // Also propagate to raw_ai.openings so Apply uses the new style.
      const raw = prev.raw_ai || {};
      const rawOps = (raw.openings || []).map((op) => {
        const sameWall = (op.wall || "").toLowerCase() === (elev || "").toLowerCase();
        const sameType = (op.type || "").toLowerCase() === (type || "").toLowerCase();
        const sameW = Math.round(Number(op.width_in) || 0) === Math.round(Number(w) || 0);
        const sameH = Math.round(Number(op.height_in) || 0) === Math.round(Number(h) || 0);
        if (sameWall && sameType && sameW && sameH) {
          return { ...op, style: newStyle };
        }
        return op;
      });
      return {
        ...prev,
        measurements: { ...m, _ai_openings_schedule: nextSched },
        raw_ai: { ...raw, openings: rawOps },
      };
    });
  };


  // Hits /api/measure/report-pdf with the current estimate_id; backend
  // reads the saved session and renders a 1–2 page report with photos,
  // confidence chips, openings schedule, and notes.
  const [reportBusy, setReportBusy] = useState(false);
  // Iter 79j.12 — show3DPreview state removed with the Elevation
  // Drawings preview block.
  const downloadReportPdf = async () => {
    if (!estimateId) {
      toast.error("Save the estimate first — the report needs an estimate ID");
      return;
    }
    setReportBusy(true);
    try {
      const res = await api.post(
        "/measure/report-pdf",
        { estimate_id: estimateId },
        { responseType: "blob" },
      );
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${estimateId.slice(0, 8)}-measurement.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Measurement report downloaded");
    } catch (err) {
      // Blob responses make the JSON error invisible — decode manually
      let detail = err?.response?.data?.detail || err?.message || "Report failed";
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          detail = JSON.parse(text)?.detail || text || detail;
        } catch { /* ignore */ }
      }
      toast.error(detail);
    } finally {
      setReportBusy(false);
    }
  };

  // Apply Howard's geometry math to the edited wall list and update
  // siding_sqft / gable / dormer totals on the preview in-place. Mirrors
  // backend `_aggregate_to_hover_shape` so the headline number tracks
  // every keystroke without a round-trip.
  const recomputeFromWalls = (walls) => {
    let sidingSqft = 0;
    let gableSqft = 0;
    let dormerSqft = 0;
    for (const w of walls) {
      const width = Number(w.width_ft) || 0;
      const eave = Number(w.height_ft) || 0;
      const gross = width * eave;
      let pct = Number(w.siding_pct_this_wall);
      if (!pct || pct <= 0) pct = 100;
      if (pct > 100) pct = 100;
      sidingSqft += gross * (pct / 100);
      const gableH = Number(w.gable_triangle_height_ft) || 0;
      if (gableH > 0 && width > 0) gableSqft += 0.5 * width * gableH;
      dormerSqft += Number(w.dormer_face_sqft) || 0;
    }
    sidingSqft += gableSqft + dormerSqft;
    return {
      siding_sqft: Math.round(sidingSqft * 10) / 10,
      _ai_gable_sqft: Math.round(gableSqft * 10) / 10,
      _ai_dormer_sqft: Math.round(dormerSqft * 10) / 10,
    };
  };

  // Edit one cell on one wall and recompute totals so the headline
  // sqft figure on the preview shifts immediately.
  const setWall = (idx, key, val) => {
    setPreview((p) => {
      if (!p?.raw_ai?.walls) return p;
      const walls = p.raw_ai.walls.map((w, i) =>
        i === idx ? { ...w, [key]: val === "" ? 0 : Number(val) } : w
      );
      const totals = recomputeFromWalls(walls);
      return {
        ...p,
        raw_ai: { ...p.raw_ai, walls },
        measurements: {
          ...p.measurements,
          siding_sqft: totals.siding_sqft,
          siding_with_openings_sqft: totals.siding_sqft,
          _ai_gable_sqft: totals._ai_gable_sqft,
          _ai_dormer_sqft: totals._ai_dormer_sqft,
        },
      };
    });
    setWallsDirty(true);
  };

  // Iter 79j.66 — Edit a dormer's WIDTH or KNEE height straight from the
  // Wall Breakdown and have the wall's dormer face ft² recompute itself.
  // Correcting a dormer used to mean knowing the face-area formula by
  // heart (face ft² includes cheeks/shed-rise beyond w×knee); instead we
  // RESCALE the AI's ft² by the ratio of the w×knee products, which
  // preserves the AI's geometry factor while making the correction
  // formula-free. Editing here mutates `raw_ai.dormers` — the same
  // object the 3D sidebar reads — so the model updates in lock-step.
  const setDormerDims = (dormerIdx, wallIdx, key, val) => {
    setPreview((p) => {
      if (!p?.raw_ai?.dormers?.[dormerIdx] || !p?.raw_ai?.walls?.[wallIdx]) return p;
      const num = val === "" ? 0 : Number(val);
      const wallLabel = ((p.raw_ai.walls[wallIdx].label || "")).toLowerCase();
      const product = (d) =>
        (Number(d.width_ft) || 0) * (Number(d.knee_wall_height_ft) || 0);
      const matched = p.raw_ai.dormers
        .map((d, j) => ({ d, j }))
        .filter(({ d }) => (d.face || "").toLowerCase() === wallLabel);
      const before = matched.reduce((a, { d }) => a + product(d), 0);
      const dormers = p.raw_ai.dormers.map((d, j) =>
        j === dormerIdx ? { ...d, [key]: num } : d
      );
      const after = matched.reduce(
        (a, { j }) => a + product(dormers[j]), 0
      );
      const walls = p.raw_ai.walls.map((w, i) => {
        if (i !== wallIdx) return w;
        const sqft = Number(w.dormer_face_sqft) || 0;
        const next = before > 0 && sqft > 0
          ? sqft * (after / before)   // preserve AI's cheek/rise factor
          : after;                    // no basis — fall back to Σ w×knee
        return { ...w, dormer_face_sqft: Math.round(next * 10) / 10 };
      });
      const totals = recomputeFromWalls(walls);
      return {
        ...p,
        raw_ai: { ...p.raw_ai, walls, dormers },
        measurements: {
          ...p.measurements,
          siding_sqft: totals.siding_sqft,
          siding_with_openings_sqft: totals.siding_sqft,
          _ai_gable_sqft: totals._ai_gable_sqft,
          _ai_dormer_sqft: totals._ai_dormer_sqft,
        },
      };
    });
    setWallsDirty(true);
  };

  // Edit any of the linear-measurement fields (eaves, rakes, starter,
  // corners, opening perimeter) inline. ISS soffit/gutter/etc. and the
  // siding-flow soffit/J-channel rows all derive their qty from these,
  // so a one-line override here propagates everywhere through the
  // /measure/map refresh on Apply.
  const setMeasurementField = (key, val) => {
    setPreview((p) => {
      if (!p?.measurements) return p;
      return {
        ...p,
        measurements: {
          ...p.measurements,
          [key]: val === "" ? 0 : Number(val),
        },
      };
    });
    setWallsDirty(true);
  };


  // ------------------------------------------------------------------
  // Server-side session persistence (Iter 50).
  // ------------------------------------------------------------------
  // On first modal open for this estimate, check for an existing session
  // and offer the contractor a Resume / Start Over choice. Without an
  // estimateId we just skip persistence entirely (e.g. ISS new-quote
  // flow before the doc has been saved).
  const [sessionChecked, setSessionChecked] = useState(false);
  useEffect(() => {
    if (!estimateId || !open || sessionChecked) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/measure/sessions/${estimateId}`);
        if (cancelled) return;
        // If the modal already has fresh state (user just selected files
        // before we finished the GET), don't clobber. Otherwise prompt.
        const hasFreshState = photoUrls.length > 0 || preview != null;
        if (!hasFreshState && (data.photo_urls?.length || data.preview)) {
          setResumePrompt(true);
          // Iter 79j.64 — Fix 2: capture WHAT the server holds so the
          // recovery banner can be specific instead of generic.
          const pa = data.photo_annotations || {};
          setPendingSessionMeta({
            photos: data.photo_urls?.length || 0,
            hasResult: !!data.preview,
            annotated: Object.keys(pa).filter(
              (k) => !k.startsWith("_") && pa[k] && Object.keys(pa[k]).length > 0
            ).length,
          });
          // Stash for the Resume button to consume.
          window.__aiMeasurePendingSession = data;
        }
      } catch {
        // 404 — no session, normal first run.
      } finally {
        if (!cancelled) setSessionChecked(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [estimateId, open, sessionChecked, photoUrls.length, preview]);

  // Iter 78z — Load saved profile annotations for this estimate.
  useEffect(() => {
    if (!estimateId || !open) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/estimates/${estimateId}/profile-annotations`);
        if (!cancelled) setSavedProfileAnnotations(data?.annotations || {});
      } catch {
        // No annotations yet — that's fine
      }
    })();
    return () => { cancelled = true; };
  }, [estimateId, open]);

  // Iter 57r — Resume support. On modal open, fetch the most recent
  // AI Measure run for this estimate. If it's still "running" or
  // finished within the last 30 min, set `lastRun` so the banner
  // surfaces. The actual Resume / Restore button click is wired below.
  useEffect(() => {
    if (!estimateId || !open) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/measure/ai-measure/latest-for-estimate/${estimateId}`);
        if (cancelled) return;
        const r = data?.run || null;
        if (!r) { setLastRun(null); return; }
        // Only surface fresh runs (< 30 min) so we don't nag the
        // contractor about ancient runs they already applied.
        if (r.status === "running" || (r.age_seconds || 0) < 30 * 60) {
          setLastRun(r);
        } else {
          setLastRun(null);
        }
      } catch {
        setLastRun(null);
      }
    })();
    return () => { cancelled = true; };
  }, [estimateId, open]);

  // Iter 57r — handler: resume polling an in-flight run.
  const _applyAIResult = (data, status) => {
    // Resume path: load the preview directly. The full per-wall
    // recompute + auto-elevation-tagging that the fresh-run path
    // performs assumes the contractor was watching the run live; on
    // resume we trust whatever Claude returned and let them re-edit.
    // Iter 79j.37 — Thread the poll `status` payload's per-photo
    // extractions + pipeline label into the preview object so the
    // Debug view can show ACTUAL Phase A data.
    // Iter 79j.52 — Stamp run_id into the preview so the session
    // persistence flow saves it, and so a resumed failed session
    // can wire the Retry Reconciliation button back to the correct
    // run doc.
    const runIdForPreview = status?.run_id || currentRunId || data?.run_id || null;
    const enriched = status
      ? { ...data, raw_per_photo: status.raw_per_photo, pipeline: status.pipeline, run_id: runIdForPreview }
      : { ...data, run_id: runIdForPreview };
    setPreview(enriched);
  };

  // Iter 79j.51 — Reconcile-only retry. When Phase A succeeded but
  // Phase B (LLM reconciliation) 502'd on the proxy, we can re-run
  // JUST Phase B against the saved raw_per_photo — costing pennies
  // instead of paying for vision extraction again. Polls the same
  // run_id (backend re-uses the run doc, flips status back to
  // running / stage=reconciling).
  const retryReconcileOnly = async (runId) => {
    if (!runId) {
      toast.error("No run to reconcile — try Retry Run instead");
      return;
    }
    setBusy(true);
    setBusyStage("reconciling");
    setRunError(null);
    setRunErrorMeta(null);
    const t0 = Date.now();
    try {
      const launch = await api.post(`/measure/ai-measure/reconcile-only/${runId}`);
      if (!launch?.data?.run_id) throw new Error("Backend didn't accept the reconcile-only retry");
      let result = null;
      let finalStatus = null;
      // Phase B alone should finish in ~3 min; give it 4 min budget.
      for (let i = 0; i < 80; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        let statusResp;
        try {
          statusResp = await api.get(`/measure/ai-measure/status/${runId}`);
        } catch (e) {
          if (i >= 5) console.warn("reconcile-only status poll failed", e?.message);
          continue;
        }
        const s = statusResp?.data || {};
        if (s.stage && s.stage !== busyStage) setBusyStage(s.stage);
        if (s.phase_a_progress) setPhotoProgress(s.phase_a_progress);
        if (s.status === "error") throw new Error(s.error || "Reconciliation retry failed");
        if (s.status === "done") { result = s.result; finalStatus = s; break; }
      }
      if (!result) throw new Error("Reconciliation retry timed out — the server may still be finishing in the background");
      _applyAIResult(result, finalStatus);
      toast.success("Reconciliation retry complete · measurements applied");
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Reconciliation retry failed";
      setRunError(String(msg));
      setRunErrorMeta({
        stage: "reconciling",
        elapsedMs: Date.now() - t0,
        kind: e?.response?.status === 502 ? "BadGateway" : "ReconcileRetryFailed",
      });
    } finally {
      setBusy(false);
      setBusyStage("");
    }
  };

  // Iter 78z+ — Re-fire AI Measure using cached photo bytes server-side
  // (no re-upload). Triggered from ProfileAnnotator's "Save & Re-run".
  // Mirrors `resumeRunPolling` but kicks off a fresh worker first.
  const rerunWithAnnotations = async () => {
    if (!currentRunId) {
      toast.error("No previous AI Measure run to re-fire — upload photos first");
      return;
    }
    setBusy(true);
    setBusyStage("starting");
    try {
      // Iter 79j.35 — Pass the current "Powered by" dropdown selection
      // so Re-Run honors the model the contractor picked. Prior version
      // silently reused the original run's model, defeating A/B testing.
      // Iter 79j.67(a) — also pass the CURRENT calibration values.
      // Legacy run docs predate calibration persistence, and the
      // contractor may have updated the Calibrate popover between runs —
      // body values win over the previous run's stored ones.
      const rerunBody = {
        ...(modelChoice ? { model_choice: modelChoice } : {}),
        ...(brickCourse && parseFloat(brickCourse) > 0
          ? { brick_course_in: parseFloat(brickCourse) } : {}),
        ...(sidingExposure && parseFloat(sidingExposure) > 0
          ? { siding_exposure_in: parseFloat(sidingExposure) } : {}),
      };
      const launch = await api.post(
        `/measure/ai-measure/rerun/${currentRunId}`,
        rerunBody,
      );
      const newRunId = launch?.data?.run_id;
      if (!newRunId) throw new Error("Backend didn't return a new run_id");
      setCurrentRunId(newRunId);
      setBusyStage(launch?.data?.stage || "starting");
      // Poll the new run to completion. Iter 79j.48 — bumped 100→200
      // iterations (300s→600s) so client budget exceeds server worst
      // case (Phase A 300s + drain 5s + Phase B 180s ≈ 485s).
      let result = null;
      let finalStatus = null;
      for (let i = 0; i < 200; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        let statusResp;
        try {
          statusResp = await api.get(`/measure/ai-measure/status/${newRunId}`);
        } catch (e) {
          if (i >= 5) console.warn("ai-measure rerun status poll failed", e?.message);
          continue;
        }
        const s = statusResp?.data || {};
        if (s.stage && s.stage !== busyStage) setBusyStage(s.stage);
        if (s.phase_a_progress) setPhotoProgress(s.phase_a_progress);
        if (s.status === "error") throw new Error(s.error || "AI measure re-run failed");
        if (s.status === "done") { result = s.result; finalStatus = s; break; }
      }
      if (!result) throw new Error("Re-run did not complete within 10 minutes — the server may still be finishing in the background");
      _applyAIResult(result, finalStatus);
      toast.success("Re-run complete · annotations applied to materials list");
    } catch (e) {
      toast.error(e?.response?.data?.detail || e?.message || "Re-run failed");
    } finally {
      setBusy(false);
      setBusyStage("");
    }
  };

  const resumeRunPolling = async () => {
    if (!lastRun || !lastRun.run_id) return;
    setBusy(true);
    setBusyStage(lastRun.stage || "running");
    setCurrentRunId(lastRun.run_id);
    // Restore the photo grid from the saved photo_paths so the UI
    // matches the run the worker is processing.
    if (lastRun.photo_paths) {
      const paths = String(lastRun.photo_paths).split(",").map((s) => s.trim()).filter(Boolean);
      if (paths.length) setPhotoUrls(paths);
    }
    setLastRun(null);
    try {
      let result = null;
      let finalStatus = null;
      for (let i = 0; i < 200; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        let statusResp;
        try {
          statusResp = await api.get(`/measure/ai-measure/status/${lastRun.run_id}`);
        } catch {
          continue;
        }
        const s = statusResp?.data || {};
        if (s.stage && s.stage !== busyStage) setBusyStage(s.stage);
        if (s.phase_a_progress) setPhotoProgress(s.phase_a_progress);
        if (s.status === "error") throw new Error(s.error || "AI measure failed");
        if (s.status === "done") { result = s.result; finalStatus = s; break; }
      }
      if (!result) throw new Error("Resume timed out — the server may still be finishing in the background");
      // Mimic the same downstream flow as a normal run completion.
      _applyAIResult(result, finalStatus);
      toast.success("AI Measure resumed — preview loaded");
    } catch (e) {
      toast.error(e?.message || "Resume failed");
    } finally {
      setBusy(false);
      setBusyStage("");
    }
  };

  // Iter 57r — handler: restore the preview from a finished run.
  const restoreLastRun = () => {
    if (!lastRun || !lastRun.result) return;
    if (lastRun.photo_paths) {
      const paths = String(lastRun.photo_paths).split(",").map((s) => s.trim()).filter(Boolean);
      if (paths.length) setPhotoUrls(paths);
    }
    setCurrentRunId(lastRun.run_id);
    _applyAIResult(lastRun.result, lastRun);
    setLastRun(null);
    toast.success("Last AI run restored — preview loaded");
  };

  // Debounced autosave: any time the persisted state changes, push to
  // /measure/sessions. 1 second debounce keeps wall-edit keystrokes from
  // hammering the backend.
  useEffect(() => {
    if (!estimateId || !open || !sessionChecked) return;
    // Skip empty initial state to avoid creating an empty session doc.
    if (!photoUrls.length && !preview) return;
    // Iter 79j.29 — Do NOT clobber a session that already has photos
    // with an empty photo_urls array when a preview exists. This was
    // the root cause of the "Re-Run does nothing" bug — an empty
    // photo_urls + non-null preview mismatch poisoned the session so
    // Resume rehydrated 0 photos and Re-Run silently bailed.
    if (!photoUrls.length && preview) return;
    // Iter 79j.53 — HARD GUARD: never persist a preview that carries a
    // `_reconciliation_error`. A failed reconcile attempt would
    // otherwise silently clobber the last-good preview on the next
    // debounced autosave and bury the working reconciled house. The
    // run doc (ai_measure_runs) is authoritative for the retry
    // target; the session's job is to remember successful state
    // only. If the current preview is a failure state, skip the
    // autosave entirely — the last-good session preview stays put.
    if (preview && preview?.raw_ai?._reconciliation_error) {
      return;
    }
    const t = setTimeout(() => {
      api
        .put(`/measure/sessions/${estimateId}`, {
          estimate_id: estimateId,
          photo_urls: photoUrls,
          reference_dim: refDim,
          brick_course_in: brickCourse && parseFloat(brickCourse) > 0 ? parseFloat(brickCourse) : null,
          siding_exposure_in: sidingExposure && parseFloat(sidingExposure) > 0 ? parseFloat(sidingExposure) : null,
          wall_height: wallHeight,
          siding_pct: sidingPct,
          overhang_in: Number(overhangIn ?? 12),
          preview,
          // Iter 56f: persist per-photo annotations so they survive
          // page navigation / refresh too. Previously these were
          // dropped on close because they weren't in the payload —
          // contractors lost all their pin / scale / mask work.
          photo_annotations: photoAnnotations,
        })
        .catch(() => {
          // Non-fatal: autosave failures are silent so they don't
          // interrupt the contractor's flow. Local state is still good.
        });
    }, 1000);
    return () => clearTimeout(t);
  }, [estimateId, open, sessionChecked, photoUrls, refDim, wallHeight, sidingPct, overhangIn, preview, photoAnnotations]);


  const resumeSession = async () => {
    const data = window.__aiMeasurePendingSession;
    if (!data) {
      setResumePrompt(false);
      return;
    }
    // Iter 79j.29 — if the session's photo_urls is empty but a preview
    // exists, the session was clobbered by an earlier autosave bug.
    // Fall back to the last completed run doc's photo_paths so the
    // contractor's grid + Re-Run still work.
    let urls = data.photo_urls || [];
    if ((!urls || urls.length === 0) && data.preview) {
      try {
        const r = await api.get(`/measure/ai-measure/history/${estimateId}`, { params: { limit: 1 } });
        const last = r.data?.runs?.[0];
        const paths = (last?.photo_paths || "").split(",").map((s) => s.trim()).filter(Boolean);
        if (paths.length) {
          urls = paths;
          toast.success(`Recovered ${paths.length} photos from the last run`);
        }
      } catch {
        // Non-fatal — the loud banner below handles the "no photos" case.
      }
    }
    setPhotoUrls(urls);
    setRefDim(data.reference_dim || "");
    // Iter 79j.67(a) — restore contractor calibration on session resume;
    // without this a recovered session re-runs with no exposure and
    // course counting never fires.
    if (data.brick_course_in != null) setBrickCourse(String(data.brick_course_in));
    if (data.siding_exposure_in != null) setSidingExposure(String(data.siding_exposure_in));
    setWallHeight(data.wall_height || "");
    setSidingPct(data.siding_pct || "");
    if (data.preview) setPreview(data.preview);
    if (data.photo_annotations) setPhotoAnnotations(data.photo_annotations);
    // Iter 79j.52 — If the resumed preview carries a stale
    // reconciliation failure, hoist it into `runError` so the
    // top-level failure banner (with the Retry Reconciliation
    // button) surfaces, the 3D tab suppresses its placeholder
    // render, and the Apply button disables. Without this the UI
    // silently restored a preview whose raw_ai._reconciliation_error
    // was set but ONLY the run-time (fresh-run) error path could
    // render the banner.
    // Iter 79j.53 — Mark the error as HISTORIC (origin="resume") so
    // the banner reads "Prior reconciliation failed" and does NOT
    // display "Elapsed: 0s" as if a fresh call just returned. This
    // was misleading contractors into thinking Resume auto-fired a
    // retry. Resume is read-only — it never calls Phase B; retries
    // are always explicit user clicks.
    const reconErr = data?.preview?.raw_ai?._reconciliation_error;
    const resumedRunId = data?.preview?.run_id || null;
    // Iter 79j.52b — Session self-heal on Resume. If the persisted
    // preview says reconciliation failed, but the LATEST run doc on
    // the server has a successful reconciliation (typically because a
    // retry ran after the session was persisted), replace the stale
    // failure with the fresh good result AND overwrite the session
    // doc so subsequent resumes stay healed. Falls back to the
    // existing "Prior reconciliation failed" banner if no fresher
    // good run exists.
    let didSelfHeal = false;
    if (reconErr) {
      try {
        const { data: freshData } = await api.get(
          `/measure/ai-measure/latest-for-estimate/${estimateId}`,
        );
        const freshRun = freshData?.run;
        const freshResult = freshRun?.result;
        const freshHasError = !!freshResult?.raw_ai?._reconciliation_error;
        const freshOk = freshRun?.status === "done"
          && freshResult
          && freshResult.raw_ai
          && !freshHasError;
        if (freshOk) {
          const healedPreview = { ...freshResult, run_id: freshRun.run_id };
          setPreview(healedPreview);
          setCurrentRunId(freshRun.run_id);
          setRunError(null);
          setRunErrorMeta(null);
          // Persist the self-heal so a page navigation + Resume later
          // doesn't re-summon the stale failure banner.
          try {
            await api.put(`/measure/sessions/${estimateId}`, {
              estimate_id: estimateId,
              photo_urls: urls,
              reference_dim: data.reference_dim || "",
              brick_course_in: data.brick_course_in ?? null,
              siding_exposure_in: data.siding_exposure_in ?? null,
              wall_height: data.wall_height || "",
              siding_pct: data.siding_pct || "",
              overhang_in: Number(data.overhang_in ?? 12),
              preview: healedPreview,
              photo_annotations: data.photo_annotations || {},
            });
          } catch {
            // Non-fatal — next debounced autosave will retry.
          }
          toast.success(
            "Resumed — session self-healed from a newer successful reconciliation",
          );
          didSelfHeal = true;
        }
      } catch {
        // Latest-run lookup failed (network / 404). Fall through to
        // the "Prior reconciliation failed" banner path.
      }
      if (!didSelfHeal) {
        setRunError(String(reconErr));
        setRunErrorMeta({
          stage: "reconciling",
          elapsedMs: null,
          kind: "PriorFailure",
          origin: "resume",
        });
        if (resumedRunId) setCurrentRunId(resumedRunId);
      }
    } else if (resumedRunId) {
      // Non-failure resume: still remember the run id so a manual
      // Retry Reconciliation (if the user opens it later) has the
      // right target.
      setCurrentRunId(resumedRunId);
    }
    setResumePrompt(false);
    delete window.__aiMeasurePendingSession;
    if (urls.length > 0 && !didSelfHeal) {
      toast.success("Resumed your last AI Measure session");
    }
  };

  const startOver = async () => {
    setResumePrompt(false);
    setPendingSessionMeta(null);
    setPreview(null);
    setPhotoUrls([]);
    setFiles([]);
    setRefDim("");
    setWallHeight("");
    setSidingPct("");
    setWallsDirty(false);
    setPhotoAnnotations({});
    delete window.__aiMeasurePendingSession;
    if (estimateId) {
      try {
        await api.delete(`/measure/sessions/${estimateId}`);
      } catch {
        // ignore
      }
    }
  };

  // Iter 79j.52a — Dismiss handler for the run-error banner. Behavior
  // depends on WHAT kind of error is on screen:
  //   • Reconciliation-failure preview (either resumed or fresh):
  //     downgrade the session to PHOTOS-ONLY. That means:
  //       - clear the failed preview from local state,
  //       - clear currentRunId (per Howard 2026-07-06: dismiss = clean
  //         slate; Debug View still holds the run history server-side),
  //       - IMMEDIATELY PUT the session with preview=null so the next
  //         Resume doesn't restore the failed banner (the debounced
  //         autosave alone would leave a race window on navigation).
  //     Photos, ref dim, wall height, siding % and annotations are
  //     preserved so the contractor can just click Run AI Measure again
  //     without re-uploading a thing.
  //   • Any other error kind (budget, generic fresh-run failure):
  //     just clear the local banner state — nothing on the session
  //     needs to change because those errors never wrote a failed
  //     preview (the autosave guard on line 703 prevented it).
  const dismissRunError = async () => {
    const hasReconcileFailure = !!(preview && preview?.raw_ai?._reconciliation_error);
    setRunError(null);
    setRunErrorMeta(null);
    if (!hasReconcileFailure) return;   // budget / fresh-error: nothing to persist
    setPreview(null);
    setCurrentRunId(null);
    if (!estimateId) return;
    try {
      await api.put(`/measure/sessions/${estimateId}`, {
        estimate_id: estimateId,
        photo_urls: photoUrls,
        reference_dim: refDim,
        brick_course_in: brickCourse && parseFloat(brickCourse) > 0 ? parseFloat(brickCourse) : null,
        siding_exposure_in: sidingExposure && parseFloat(sidingExposure) > 0 ? parseFloat(sidingExposure) : null,
        wall_height: wallHeight,
        siding_pct: sidingPct,
        overhang_in: Number(overhangIn ?? 12),
        preview: null,
        photo_annotations: photoAnnotations,
      });
    } catch {
      // Non-fatal — local state is already clean; the next debounced
      // autosave will retry the persistence.
    }
  };


  // Upload-on-select. Photos hit /api/uploads immediately so they're
  // safe across page refreshes; only the resulting server URLs go into
  // photoUrls. The transient `files` list lives just long enough to
  // show previews during upload.
  const pickFiles = async (e) => {
    const arr = Array.from(e.target.files || []).slice(0, 9 - photoUrls.length);
    if (!arr.length) return;
    setFiles((prev) => [...prev, ...arr]);
    // Parallel uploads.
    const uploaded = await Promise.all(
      arr.map(async (f) => {
        try {
          const fd = new FormData();
          fd.append("file", f);
          const { data } = await api.post("/uploads", fd, {
            headers: { "Content-Type": "multipart/form-data" },
            timeout: 60000,
          });
          return data.name; // store the bare filename
        } catch (err) {
          toast.error(`Upload failed for ${f.name}`);
          return null;
        }
      })
    );
    const ok = uploaded.filter(Boolean);
    setPhotoUrls((prev) => [...prev, ...ok]);
    // Drop the local File objects now that the URLs are persisted.
    setFiles((prev) => prev.filter((f) => !arr.includes(f)));
  };

  // Iter 57: Guided capture wizard. After the wizard completes,
  // upload all files at once and pre-tag each photo's elevation
  // (front / back / left / right) so Claude doesn't have to guess.
  const [wizardOpen, setWizardOpen] = useState(false);
  // Iter 79h (Phase 3) — auto-run trigger. When the wizard finishes
  // with `autoRun: true` we set this flag; a useEffect below fires
  // runMeasure() as soon as the just-uploaded photo names have landed
  // in the photoUrls state (React state updates are batched, so we
  // can't call runMeasure synchronously from handleWizardComplete —
  // it'd read the stale array from closure). The effect resets the
  // flag immediately after firing so retries require an explicit
  // action from the contractor.
  const [autoRunPending, setAutoRunPending] = useState(false);
  const autoRunBaselineRef = useRef(0);
  const handleWizardComplete = async ({ photos, autoRun }) => {
    if (!photos?.length) return;
    const room = 9 - photoUrls.length;
    if (room <= 0) {
      toast.error("Already at 8 photos — remove some before importing wizard captures");
      return;
    }
    const batch = photos.slice(0, room);
    setFiles((prev) => [...prev, ...batch.map((p) => p.file)]);
    // Iter 79f — wizard uploads each photo inline (right after capture)
    // so most photos arrive here with a pre-populated `name` field and
    // don't need to hit /api/uploads again. Fall back to a re-upload
    // if the inline upload failed (e.g. flaky connection) — the parent
    // still owns the retry path.
    const uploaded = await Promise.all(
      batch.map(async (p) => {
        if (p.name) {
          return {
            name: p.name,
            elevation: p.elevation,
            annotations: p.annotations || null,
            file: p.file,
          };
        }
        try {
          const fd = new FormData();
          fd.append("file", p.file);
          const { data } = await api.post("/uploads", fd, {
            headers: { "Content-Type": "multipart/form-data" },
            timeout: 60000,
          });
          return {
            name: data.name,
            elevation: p.elevation,
            annotations: p.annotations || null,
            file: p.file,
          };
        } catch (err) {
          toast.error(`Upload failed for ${p.file.name}`);
          return null;
        }
      }),
    );
    const ok = uploaded.filter(Boolean);
    setPhotoUrls((prev) => [...prev, ...ok.map((u) => u.name)]);
    // Apply BOTH the elevation tags AND any per-photo annotations the
    // contractor recorded inline in the wizard so Claude gets ground
    // truth in one shot (elevation label + scale ref + zones + tagged
    // windows + profile boxes).
    setPhotoAnnotations((prev) => {
      const next = { ...prev };
      ok.forEach(({ name, elevation, annotations }) => {
        const merged = { ...(next[name] || {}), elevation };
        if (annotations) {
          if (annotations.reference !== undefined) merged.reference = annotations.reference;
          if (annotations.windowReference !== undefined) merged.windowReference = annotations.windowReference;
          if (annotations.zones !== undefined) merged.zones = annotations.zones;
          if (annotations.targetPin !== undefined) merged.targetPin = annotations.targetPin;
          if (annotations.windows !== undefined) merged.windows = annotations.windows;
          if (annotations.profileBoxes !== undefined) merged.profileBoxes = annotations.profileBoxes;
        }
        next[name] = merged;
      });
      return next;
    });
    // Iter 79j.18 — CRITICAL fix: persist profile boxes from the
    // Guided Capture Wizard to the estimate's `profile_annotations`
    // in Mongo. Previously the wizard's `handleAnnotateSave` only
    // stored payloads in local wizard state — they never reached the
    // AI Measure worker, so a contractor's shake polygon drawn during
    // guided capture produced ZERO shake ft² in the final quote. This
    // block extracts profileBoxes from each just-uploaded photo,
    // transforms them into the backend shape (identical to the
    // AIMeasureButton's per-photo save path), and PUTs the merged
    // annotations bundle. Keyed by photo INDEX (post-append) so it
    // stays in sync with `apply_annotations_to_breakdown`'s expected
    // shape.
    if (estimateId) {
      const baseIdx = photoUrls.length; // pre-append offset
      setSavedProfileAnnotations((prev) => {
        const next = { ...(prev || {}) };
        const refs = { ...((prev && prev._scale_refs) || {}) };
        ok.forEach(({ elevation, annotations }, i) => {
          const idx = baseIdx + i;
          const boxes = annotations?.profileBoxes || [];
          if (!boxes.length) return;
          const dims = annotations?.imageDims;
          const naturalW = dims?.w || 1;
          const naturalH = dims?.h || 1;
          const boxesForBackend = boxes.map((b) => {
            const xs = b.points.map((p) => p.x);
            const ys = b.points.map((p) => p.y);
            const minX = Math.min(...xs), minY = Math.min(...ys);
            const maxX = Math.max(...xs), maxY = Math.max(...ys);
            return {
              shape: b.shape,
              elevation_label: elevation || "other",
              profile: b.profile,
              location: b.location,
              sqft: b.sqft,
              callout: b.note || "",
              ...(b.shape === "polygon"
                ? { points: b.points.map((p) => ({ x_norm: p.x / naturalW, y_norm: p.y / naturalH })) }
                : {
                    x_norm: minX / naturalW,
                    y_norm: minY / naturalH,
                    w_norm: (maxX - minX) / naturalW,
                    h_norm: (maxY - minY) / naturalH,
                  }),
            };
          });
          next[String(idx)] = boxesForBackend;
          // Persist the wall scale anchor too so the backend safety-
          // net can recompute polygon sqft server-side if a box's
          // sqft slipped through as the sentinel 50.
          //
          // Iter 79j.63 — Write BOTH schemas in a single ref entry:
          //   • NEW (p1_*_norm, p2_*_norm, inches) — what this writer
          //     historically produced; used by any consumer that
          //     resolves the ref against loaded image dimensions at
          //     render time.
          //   • OLD (px_height, real_ft, img_w, img_h) — what
          //     `profile_callouts._recompute_box_sqft` on the backend
          //     AND `ProfileAnnotator`'s display path both expect.
          //     Missing this shape triggered the Jul 7 2026 crash
          //     (`scaleRef.real_ft.toFixed(2)` on undefined).
          // Writing both is idempotent + <100 bytes and eliminates the
          // schema mismatch class of bug for future consumers.
          const ref = annotations?.reference;
          if (ref && Array.isArray(ref?.p1) === false && ref?.p1 && ref?.p2 && ref?.inches) {
            const dxPx = (ref.p2.x - ref.p1.x);
            const dyPx = (ref.p2.y - ref.p1.y);
            const pxHeight = Math.sqrt(dxPx * dxPx + dyPx * dyPx);
            const realFt = Number(ref.inches) / 12;
            refs[String(idx)] = {
              // NEW shape
              p1_x_norm: ref.p1.x / naturalW,
              p1_y_norm: ref.p1.y / naturalH,
              p2_x_norm: ref.p2.x / naturalW,
              p2_y_norm: ref.p2.y / naturalH,
              inches: ref.inches,
              // OLD shape — mirror for backend + ProfileAnnotator
              px_height: pxHeight > 0 ? pxHeight : 0,
              real_ft: realFt > 0 ? realFt : 0,
              img_w: naturalW,
              img_h: naturalH,
            };
          }
        });
        next._scale_refs = refs;
        // Fire-and-forget PUT — non-fatal if the network hiccups.
        api.put(`/estimates/${estimateId}/profile-annotations`, { annotations: next })
          .catch((err) => console.warn("wizard profile-annotations persist failed:", err?.message));
        return next;
      });
    }
    setFiles((prev) => prev.filter((f) => !batch.find((b) => b.file === f)));
    const annotatedCount = ok.filter((u) => u.annotations).length;
    const annotatedNote = annotatedCount > 0 ? ` (${annotatedCount} annotated)` : "";
    toast.success(`${ok.length} photo${ok.length !== 1 ? "s" : ""} added & elevation-tagged from wizard${annotatedNote}`);
    // Iter 79h (Phase 3) — arm the auto-run effect. The effect watches
    // for photoUrls to grow beyond the pre-wizard baseline so it fires
    // once the state has actually settled with the new URLs (not
    // before). If no photos actually uploaded successfully we skip.
    if (autoRun && ok.length > 0) {
      autoRunBaselineRef.current = photoUrls.length;
      setAutoRunPending(true);
    }
  };

  // Iter 79h (Phase 3) — auto-run effect. Runs the AI Measure call as
  // soon as (a) the wizard flagged autoRun, (b) the just-uploaded photo
  // names have landed in photoUrls (grew beyond baseline), (c) we're
  // not already running. Toast-nudges the contractor so it doesn't
  // feel like a surprise kick.
  useEffect(() => {
    if (!autoRunPending) return;
    if (busy) return;
    if (photoUrls.length <= autoRunBaselineRef.current) return;
    setAutoRunPending(false);
    toast.info("Wizard finished — launching AI Measure…");
    // Fire on the next tick so the toast renders first.
    setTimeout(() => { runMeasure(); }, 250);
  }, [autoRunPending, photoUrls, busy]);

  // Iter 56c: pull a free Esri aerial tile for the estimate's address
  // and add it as an 8th photo. The endpoint resolves the address →
  // lat/lon → satellite JPEG and writes the file straight into the same
  // UPLOAD_DIR /api/uploads uses, so we just append the filename to
  // photoUrls and auto-tag it as "aerial" so Claude knows what it is.
  const fetchSatellite = async () => {
    if (satBusy) return;
    if (!address || !String(address).trim()) {
      toast.error("Fill in the Address in Job Information first — I need it to find the property");
      return;
    }
    if (photoUrls.length >= 9) {
      toast.error("Already at 9 photos — remove one to add the aerial view");
      return;
    }
    setSatBusy(true);
    try {
      const fd = new FormData();
      fd.append("address", address);
      const { data } = await api.post("/measure/satellite-tile", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 30000,
      });
      const name = data?.filename;
      if (!name) throw new Error("No filename in response");
      setPhotoUrls((prev) => [...prev, name]);
      setPhotoAnnotations((prev) => ({
        ...prev,
        [name]: { ...(prev[name] || {}), elevation: "aerial" },
      }));
      toast.success(`Aerial view added · ${(data.bytes / 1024).toFixed(0)} KB`);
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || "Satellite fetch failed";
      toast.error(detail);
    } finally {
      setSatBusy(false);
    }
  };

  const removePhoto = (idx) => {    setPhotoUrls((prev) => prev.filter((_, i) => i !== idx));
  };

  // Iter 79j.64 — Fix 3: proceed handler for the destructive-action
  // confirm modal. "start_over" and "start_fresh" both wipe the local
  // state AND delete the server session; "remove_photo" drops one photo.
  const proceedDestructive = () => {
    const dc = destructiveConfirm;
    setDestructiveConfirm(null);
    if (!dc) return;
    if (dc.kind === "remove_photo") {
      removePhoto(dc.idx);
      return;
    }
    startOver();
  };

  // Iter 79i (Phase 4) — Missing-wall warning modal. Before firing
  // runMeasure we check which of the 4 primary walls (front/back/left/
  // right) have at least one tagged photo. Corner shots (front-left,
  // rear-right, etc.) count as covering both adjacent primary walls
  // since the AI can read both elevations from a 45° corner. If fewer
  // than 4 primary walls are covered, we open a modal so the contractor
  // can go back and capture the missing ones — or bypass with "Run
  // anyway" if they have a valid reason (e.g. inaccessible side yard).
  const [missingWallsModal, setMissingWallsModal] = useState(null);
  // Iter 79j.29 — inline "no photos" banner shown when Re-Run is
  // clicked with an empty photo grid. Auto-clears on next successful
  // upload or run.
  const [noPhotosBanner, setNoPhotosBanner] = useState(false);
  // Iter 79j.30 — persistent inline error banner shown when a run
  // fails. Sonner toasts are hidden behind the modal and auto-dismiss
  // in 4s — for a $-affecting failure like budget-exceeded that's not
  // enough. Cleared automatically on the next successful run.
  const [runError, setRunError] = useState(null);
  // Iter 79j.44 — Additional context for the persistent error banner.
  // Stage tells the user which phase failed (Phase A extraction,
  // Phase B reconcile, or upstream) and elapsed lets them judge
  // whether it looks like a timeout vs a fast failure.
  const [runErrorMeta, setRunErrorMeta] = useState(null); // { stage, elapsedMs, kind }
  const runStartTsRef = useRef(0);
  // Iter 79j.45 — AI service health ping. `aiHealth` is the last
  // response from GET /api/measure/ai-measure/health. Cached on the
  // client for 45s (matching the server-side TTL) so we ping at most
  // once every 45s across all sources (modal-open, Run-click).
  //
  // Rules (per Howard):
  //   1. Never ping on every render. Only on modal-open + Run-click.
  //   2. Distinguish outcomes — do NOT collapse every failure into
  //      "budget exhausted".
  //   3. A broken health check must NOT hard-lock Run. `ambiguous`
  //      keeps the Run button enabled with a soft warning banner.
  const [aiHealth, setAiHealth] = useState(null); // {status, detail, checked_at, cached}
  const aiHealthLastRef = useRef(0);
  const AI_HEALTH_CLIENT_TTL_MS = 45_000;
  const refreshAiHealth = async ({ force = false } = {}) => {
    const now = Date.now();
    if (!force && aiHealth && (now - aiHealthLastRef.current) < AI_HEALTH_CLIENT_TTL_MS) {
      return aiHealth; // still fresh — no network call
    }
    try {
      const { data } = await api.get("/measure/ai-measure/health");
      aiHealthLastRef.current = Date.now();
      setAiHealth(data);
      return data;
    } catch (e) {
      // If the health endpoint itself is broken, treat as ambiguous
      // so the Run button STAYS ENABLED. A broken health check must
      // never be able to disable the product.
      const fallback = {
        status: "ambiguous",
        detail: "Couldn't reach the AI health check. You can still run — proceed with caution.",
        raw_error: e?.message || String(e),
      };
      aiHealthLastRef.current = Date.now();
      setAiHealth(fallback);
      return fallback;
    }
  };
  // Iter 79j.46 — Event-driven auto-recovery. When the modal is open
  // AND health is red (budget_exceeded / unavailable), listen for the
  // browser tab regaining focus or visibility — that's the "went to
  // the billing page, topped up, came back" moment. Do NOT poll while
  // green: a healthy button has nothing to learn from a ping.
  const isHealthRed =
    aiHealth?.status === "budget_exceeded" || aiHealth?.status === "unavailable";

  // Iter 79j.45 — Ping AI service health when the modal opens. If a
  // fresh ping is already in the 45s window, this call short-circuits
  // to the cached value (no network hit). We don't await — the health
  // flag flips the Run button state as soon as the response lands,
  // but the rest of the modal renders immediately.
  useEffect(() => {
    if (!open) return;
    refreshAiHealth();
  }, [open]);

  // Iter 79j.46 — Auto-recovery event listeners. Only wired up while
  // the modal is open AND health is red. Detaches immediately when
  // either condition flips — a green button gets no listeners, so a
  // healthy user pays zero cost.
  useEffect(() => {
    if (!open || !isHealthRed) return;
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        refreshAiHealth({ force: true });
      }
    };
    const onFocus = () => refreshAiHealth({ force: true });
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onFocus);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onFocus);
    };
  }, [open, isHealthRed]);

  // Iter 79j.46 — Slow-backoff timer, ONLY while the modal is open
  // AND the status is red. Backoff schedule: 60s → 2min → 5min, then
  // stays at 5min. Any status change (red → green, red → different
  // red variant) cancels the timer and restarts fresh. This gives a
  // topped-up budget a chance to recover without the user re-clicking
  // Run, but never fires while green (nothing to learn).
  const backoffTimerRef = useRef(null);
  const backoffStepRef = useRef(0);
  useEffect(() => {
    // Clear any prior timer on every effect run.
    if (backoffTimerRef.current) {
      clearTimeout(backoffTimerRef.current);
      backoffTimerRef.current = null;
    }
    if (!open || !isHealthRed) {
      backoffStepRef.current = 0;
      return undefined;
    }
    const schedule = [60_000, 120_000, 300_000]; // 60s → 2min → 5min → stays 5min
    const tick = () => {
      const idx = Math.min(backoffStepRef.current, schedule.length - 1);
      backoffStepRef.current += 1;
      backoffTimerRef.current = setTimeout(async () => {
        // Only ping if we're still red AND the modal is still open.
        // Otherwise this callback is a no-op that lets React GC the timer.
        if (!open) return;
        const latest = await refreshAiHealth({ force: true });
        if (
          open &&
          (latest?.status === "budget_exceeded" || latest?.status === "unavailable")
        ) {
          tick();
        } else {
          backoffStepRef.current = 0;
        }
      }, schedule[idx]);
    };
    tick();
    return () => {
      if (backoffTimerRef.current) {
        clearTimeout(backoffTimerRef.current);
        backoffTimerRef.current = null;
      }
    };
  }, [open, isHealthRed]);

  const primaryWallsCovered = () => {
    const covered = new Set();
    // Iter 79j.35 — Two sources of elevation tags:
    // 1. `photoAnnotations` — contractor-set (via the ProfileAnnotator or
    //    the elevation dropdown on each thumbnail).
    // 2. `preview.measurements._ai_photos` — Claude's per-photo
    //    classification from the most recent run. These are the tags
    //    the contractor SEES as colored badges on each photo thumbnail
    //    (front, back, front-right, aerial, etc). Prior versions of
    //    this guard only read source #1, so hitting Re-run on a run
    //    whose photos had Claude-classified elevations (but no
    //    contractor overrides) triggered a false "0 of 4 walls
    //    captured" modal.
    const aiPhotos = preview?.measurements?._ai_photos || preview?.raw_ai?.photos || [];
    photoUrls.forEach((name, idx) => {
      const eManual = (photoAnnotations[name]?.elevation || "").toLowerCase();
      const eAi = (aiPhotos[idx]?.elevation || "").toLowerCase();
      const e = eManual || eAi;
      if (!e) return;
      if (e === "front" || e === "front-left" || e === "front-right") covered.add("front");
      if (e === "back" || e === "rear-left" || e === "rear-right") covered.add("back");
      if (e === "left" || e === "front-left" || e === "rear-left") covered.add("left");
      if (e === "right" || e === "front-right" || e === "rear-right") covered.add("right");
    });
    return covered;
  };
  const missingPrimaryWalls = () => {
    const c = primaryWallsCovered();
    return ["front", "back", "left", "right"].filter((w) => !c.has(w));
  };

  const runMeasure = async (opts = {}) => {
    if (!photoUrls.length) {
      // Iter 79j.29 — LOUD failure. Sonner toasts aren't visible when
      // the main modal covers the screen, so we also flash an inline
      // banner state that blocks further clicks until the contractor
      // re-uploads. Prior behavior was a silent no-op that looked
      // exactly like "the Re-Run button is broken".
      toast.error("Add at least one photo before running");
      setNoPhotosBanner(true);
      return;
    }
    setNoPhotosBanner(false);
    // Iter 79j.60 — Reset the per-photo HUD on every fresh run so the
    // previous run's failed dots don't linger into a new attempt.
    setPhotoProgress(null);
    // Iter 79i — pre-flight guardrail. Skip if the caller passes
    // `bypassMissingWallsGuard: true` (from the "Run anyway" button in
    // the missing-walls modal). Iter 79j.20: switched from a state
    // sentinel to an explicit param because setTimeout captured the
    // stale `missingWallsModal` value from the render at click time,
    // so the guard re-fired on the "bypassed" run and the modal
    // reappeared with nothing happening.
    if (!opts.bypassMissingWallsGuard) {
      const missing = missingPrimaryWalls();
      if (missing.length > 0) {
        setMissingWallsModal({ missing });
        return;
      }
    }
    setMissingWallsModal(null);
    // Iter 79j.45 — Health gate. Refresh the AI service health right
    // before dispatching (may serve from cache if <45s old). Only two
    // outcomes hard-block the run: `budget_exceeded` and `unavailable`.
    // `ambiguous` and any other value proceed — a broken health check
    // must NEVER be able to lock the Run button.
    const health = await refreshAiHealth();
    if (health?.status === "budget_exceeded") {
      setRunError(
        "Universal Key budget is exhausted. Open Profile → Universal Key → " +
        "Add Balance (or enable Auto Top-up), then retry the run."
      );
      setRunErrorMeta({ stage: "preflight", elapsedMs: 0, kind: "BudgetExceeded" });
      return;
    }
    if (health?.status === "unavailable") {
      setRunError(
        (health?.detail || "AI service is not responding right now.") +
        " Retry in a minute."
      );
      setRunErrorMeta({ stage: "preflight", elapsedMs: 0, kind: "ServiceUnavailable" });
      return;
    }
    setBusy(true);
    setPreview(null);
    setRunError(null);
    setRunErrorMeta(null);
    runStartTsRef.current = Date.now();
    // Iter 79j.44 — Mutable stage tracker hoisted OUTSIDE try so the
    // catch can read it. React's `busyStage` state is captured in the
    // render closure and does NOT reflect setBusyStage() calls made
    // inside this async function.
    let liveStage = "starting";
    try {
      const fd = new FormData();

      // Iter 56: photo annotations. For each photo that has annotations
      // (scale anchor, no-siding zones, or elevation tag), we render an
      // annotated PNG client-side and upload it as a fresh file. The
      // un-annotated photos stay referenced by their existing
      // /api/uploads path for free.
      const annotatedFiles = [];   // [{ name (original), file }]
      const passThroughUrls = [];  // original photoUrls that have no annot
      const elevations = {};       // { originalName: elevation }
      // Iter 57j — track per-photo elevation aligned to backend order
      // (photo_paths first, then files). Empty strings preserve slot
      // alignment when an elevation is unknown.
      const passThroughElevs = [];
      const annotatedElevs = [];
      for (const name of photoUrls) {
        const a = photoAnnotations[name];
        if (annotEmpty(a)) {
          passThroughUrls.push(name);
          passThroughElevs.push((a && a.elevation) || "");
          continue;
        }
        try {
          const blob = await renderAnnotated(`/api/uploads/${name}`, a);
          const file = new File([blob], `annotated-${name.replace(/\.\w+$/, "")}.jpg`, { type: "image/jpeg" });
          annotatedFiles.push({ name, file });
          annotatedElevs.push(a.elevation || "");
          if (a.elevation) elevations[name] = a.elevation;
        } catch (e) {
          // Render failed (e.g. CORS) — fall back to the original photo
          // path. Still pass the structured description as text so
          // Claude has at least that.
          console.warn("annotate render failed for", name, e);
          passThroughUrls.push(name);
          passThroughElevs.push((a && a.elevation) || "");
        }
      }
      if (passThroughUrls.length) {
        fd.append("photo_paths", passThroughUrls.join(","));
      }
      for (const { file } of annotatedFiles) {
        fd.append("files", file);
      }

      // Reference dim + structured annotation description go into the
      // SAME reference_dim field — Claude reads it as contractor-
      // provided context inside the user prompt.
      const refBits = [];
      if (refDim) refBits.push(refDim);
      if (wallHeight) refBits.push(`average wall height = ${wallHeight} ft`);
      if (sidingPct) refBits.push(`siding covers ~${sidingPct}% of total wall area (rest is brick / stone / garage / etc.)`);
      // Build a per-photo description from the annotations so Claude has
      // BOTH visual (burned-in marks) and structured (text) cues.
      const annotEntries = photoUrls
        .map((name) => ({ photoName: name, ...(photoAnnotations[name] || {}) }))
        .filter((e) => !annotEmpty(e));
      const annotText = describeAnnotations(annotEntries);
      if (annotText) refBits.push(`Pre-AI photo annotations:\n${annotText}`);
      const refCombined = refBits.join("; ");
      if (refCombined) fd.append("reference_dim", refCombined);
      if (address) fd.append("address", address);
      fd.append("kind", kind || "siding");
      // Soffit pieces are computed server-side using this overhang.
      fd.append("overhang_in", String(overhangIn ?? 12));
      // Iter 57g — pass the contractor's course-counting overrides
      // (blank = use Claude's defaults). Backend feeds these into the
      // prompt as additional sizing context.
      if (brickCourse && parseFloat(brickCourse) > 0) {
        fd.append("brick_course_in", String(parseFloat(brickCourse)));
      }
      if (sidingExposure && parseFloat(sidingExposure) > 0) {
        fd.append("siding_exposure_in", String(parseFloat(sidingExposure)));
      }
      // Iter 79j.44 — Deep Dormer Scan is a no-op now; Phase A/B
      // owns dormer detection. Don't append the flag — cleaner
      // request payload.
      // Elevation tags aligned with the backend photo order
      // (photo_paths first, then files). Kept for elevation hints
      // (front/right/back/left) that Phase A uses to seed extraction.
      const elevTagList = [...passThroughElevs, ...annotatedElevs];
      if (elevTagList.length) {
        fd.append("elevation_tags", elevTagList.join(","));
      }
      // Iter 79j.15 — A/B model choice. Contractor-selectable via the
      // dropdown next to the Run AI Measure button. Blank/unknown =
      // backend default (Opus 4.5).
      if (modelChoice) {
        fd.append("model_choice", modelChoice);
      }
      // Iter 57r — link the run to this estimate so a later modal open
      // can offer to Resume / Restore the most recent run for this job.
      if (estimateId) {
        fd.append("estimate_id", estimateId);
      }
      // Iter 57q — async launcher + polling. The backend used to do
      // all the Claude work synchronously in a single 60–120 s
      // request which hit the Kubernetes ingress timeout on 8-photo
      // houses. Now we POST → get `run_id` in <300 ms → poll
      // `/measure/ai-measure/status/{run_id}` every 3 s until status
      // is "done" or "error". Timeouts are no longer possible.
      const launch = await api.post("/measure/ai-measure", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,   // 60 s is generous for just uploading the photos
      });
      const runId = launch?.data?.run_id;
      if (!runId) {
        throw new Error("Backend didn't return a run_id");
      }
      setCurrentRunId(runId);
      setBusyStage(launch?.data?.stage || "starting");
      liveStage = launch?.data?.stage || "starting";
      // Iter 79j.48 — Poll until done. Client budget MUST comfortably
      // exceed the server's legitimate worst case so a run the server
      // is about to finish never gets phantom-failed as a client
      // timeout. Server worst case with two-phase pipeline:
      //   Phase A total cap (300s) + drain (5s) + Phase B (~180s) ≈ 485s
      // Client: 200 polls × 3s ≈ 600s → 115s cushion.
      //
      // We also track `lastUpdatedAt` (server-side heartbeat via the
      // run doc's `updated_at`). If the server IS still progressing
      // when the client is about to give up (updated_at within last
      // 30s), we grant an additional grace-poll window instead of
      // wasting a run that would have completed in the next 5-10s.
      let result = null;
      let finalStatus = null;
      let lastUpdatedAtSeen = null;
      const MAX_POLLS = 200;         // 200 × 3s = 600s hard ceiling
      const GRACE_POLLS = 40;        // +120s if the server is still alive at the end
      let extraGraceGranted = false;
      let i = 0;
      while (i < MAX_POLLS) {
        await new Promise((r) => setTimeout(r, 3000));
        let statusResp;
        try {
          statusResp = await api.get(`/measure/ai-measure/status/${runId}`);
        } catch (e) {
          // Transient network blip — just retry on the next tick.
          if (i >= 5) console.warn("ai-measure status poll failed", e?.message);
          i += 1;
          continue;
        }
        const s = statusResp?.data || {};
        if (s.stage && s.stage !== liveStage) {
          liveStage = s.stage;
          setBusyStage(s.stage);
        }
        if (s.phase_a_progress) setPhotoProgress(s.phase_a_progress);
        // Heartbeat: the /status endpoint returns `elapsed_ms` computed
        // from `updated_at`. We only care whether the doc is still
        // being written to — a stalled heartbeat suggests the worker
        // died silently and grace polls would just delay the failure.
        if (typeof s.elapsed_ms === "number") {
          lastUpdatedAtSeen = { at: Date.now(), elapsedMs: s.elapsed_ms };
        }
        if (s.status === "error") {
          // Iter 79j.44 — Include stage/kind so the persistent banner
          // can tell the user WHICH phase died. `s.error` is now
          // guaranteed non-empty by the backend.
          const err = new Error(s.error || "AI measure failed (no error message from backend)");
          err._stage = s.stage || liveStage || "unknown";
          err._kind = s.error_kind || "";
          throw err;
        }
        if (s.status === "done") {
          result = s.result;
          finalStatus = s;
          break;
        }
        i += 1;
        // If we're at the tail of the normal budget AND the server
        // heartbeat is fresh (worker still writing), extend once with
        // a bounded grace window — a run about to finish is worth 2
        // extra minutes over a phantom "client timeout" failure.
        if (i === MAX_POLLS && !extraGraceGranted && lastUpdatedAtSeen &&
            (Date.now() - lastUpdatedAtSeen.at) < 30_000) {
          extraGraceGranted = true;
          console.info("[ai-measure] client-poll: server heartbeat still fresh — granting +120s grace");
          setBusyStage(liveStage + " (finishing…)");
          i = MAX_POLLS - GRACE_POLLS;
        }
      }
      if (!result) {
        // Iter 79j.44 — Stamp the last-known server stage on the
        // client-side timeout error so the banner never shows
        // "Phase: UNKNOWN" for a poll that stalled mid-Phase-A.
        // Iter 79j.48 — Copy now names the ACTUAL timeout (10 min +
        // grace) and hints that the server may still be running.
        const elapsedMin = Math.round((MAX_POLLS * 3) / 60);
        const err = new Error(
          `AI measure did not complete within ${elapsedMin} minutes — the server may still ` +
          `be finishing this run in the background. Check the estimate again in a minute ` +
          `or re-run with fewer photos.`
        );
        err._stage = liveStage || "unknown";
        err._kind = "ClientPollTimeout";
        throw err;
      }
      const data = result;
      // Iter 79j.37 — Thread per-photo extractions + pipeline flag
      // into the preview object so the Debug view can show them.
      if (finalStatus) {
        data.raw_per_photo = finalStatus.raw_per_photo;
        data.pipeline = finalStatus.pipeline;
      }
      // Iter 57: trust the walls. Claude occasionally returns
      // siding_pct_this_wall in a way the aggregator can't recover
      // (e.g. 0.5 meaning 50% but post-clamp becomes 0.5%, deflating
      // siding_sqft by 100×). The wall table totals — computed from
      // width × eave height directly — are the honest geometry. Apply
      // recomputeFromWalls right away so measurements.siding_sqft
      // matches what the contractor sees in the Wall Breakdown.
      if (data?.raw_ai?.walls?.length) {
        const totals = recomputeFromWalls(data.raw_ai.walls);
        // Iter 58: force all LF / count fields back to whatever Claude
        // just returned. Previously stale edits from the Linear
        // Measurements panel (or a restored session with overrides)
        // could leak through and produce mismatches like
        // raw_ai.eaves_lf=72 but measurements.eaves_lf=5.
        const r = data.raw_ai;
        data.measurements = {
          ...data.measurements,
          siding_sqft: totals.siding_sqft,
          siding_with_openings_sqft: totals.siding_sqft,
          _ai_gable_sqft: totals._ai_gable_sqft,
          _ai_dormer_sqft: totals._ai_dormer_sqft,
          eaves_lf: Number(r.eaves_lf) || data.measurements.eaves_lf || 0,
          rakes_lf: Number(r.rakes_lf) || data.measurements.rakes_lf || 0,
          starter_lf:
            Number(r.starter_lf) ||
            Number(r.eaves_lf) ||
            data.measurements.starter_lf ||
            0,
          outside_corner_lf:
            Number(r.outside_corner_lf) ||
            data.measurements.outside_corner_lf ||
            0,
          inside_corner_lf:
            Number(r.inside_corner_lf) ||
            data.measurements.inside_corner_lf ||
            0,
        };
        // Lines came back from the backend with the OLD tiny qty — flag
        // dirty so Apply re-runs /measure/map with the corrected
        // measurements. ISS apply already re-derives from measurements
        // directly, so that path is fine without /measure/map.
        setWallsDirty(true);
      } else {
        setWallsDirty(false);
      }
      setPreview(data);
      setRunError(null);   // Iter 79j.30 — clear any prior failure banner
      setRunErrorMeta(null);
      // Iter 57: auto-apply Claude's per-photo elevation guesses to
      // any photo that isn't already explicitly tagged. Saves the
      // contractor 4-8 dropdown taps per measurement. Manual tags
      // always win — we only fill blanks.
      const aiPhotos = data?.measurements?._ai_photos || data?.raw_ai?.photos || [];
      if (aiPhotos.length > 0 && photoUrls.length > 0) {
        setPhotoAnnotations((prev) => {
          const next = { ...prev };
          let autoTagged = 0;
          aiPhotos.forEach((ap) => {
            const idx = Number(ap?.index);
            if (!Number.isFinite(idx) || idx < 0 || idx >= photoUrls.length) return;
            const name = photoUrls[idx];
            const claudeElev = ap?.elevation;
            if (!claudeElev) return;
            const cur = next[name] || {};
            if (cur.elevation && cur.elevation !== "") return; // user tag wins
            const conf = Number(ap?.elevation_confidence) || 0;
            if (conf < 40) return; // skip very low-confidence guesses
            next[name] = { ...cur, elevation: claudeElev, _auto: true };
            autoTagged += 1;
          });
          if (autoTagged > 0) {
            toast.success(`Auto-tagged ${autoTagged} elevation${autoTagged > 1 ? "s" : ""} from AI`);
          }
          return next;
        });
      }
    } catch (e) {
      // Iter 79j.30 — Toasts get covered by the modal + auto-dismiss.
      // Surface the error as a persistent inline banner. Budget
      // exceeded is common enough (Emergent LLM Key runs out) that it
      // gets its own recognizable copy + link to the fix.
      // Iter 79j.44 — Capture stage + elapsed so the banner tells the
      // user WHICH phase failed and how long it took. Drop the
      // transient toast since the modal-body banner is persistent and
      // Retry-actionable.
      const msg = e?.response?.data?.detail || e?.message || "AI measure failed";
      const elapsedMs = runStartTsRef.current ? Date.now() - runStartTsRef.current : 0;
      setRunError(String(msg));
      setRunErrorMeta({
        stage: e?._stage || liveStage || busyStage || "unknown",
        elapsedMs,
        kind: e?._kind || "",
      });
    } finally {
      setBusy(false);
      setBusyStage("");
    }
  };

  const apply = async () => {
    if (!preview?.measurements) return;
    // Iter 79j.51 — Zero-data safety net. Distinct from the orphan-wall
    // partial-data warning below. When Phase B (reconciliation) fails
    // entirely, the aggregator still emits a placeholder measurements
    // object with 0 walls / 0 openings. Applying that writes silently-
    // wrong data (extrapolated outside-corner LF from a nonexistent
    // footprint) into the customer quote. Hard-block, don't warn.
    // Iter 79j.52 — Signals live in `raw_ai` (walls/dormers/openings
    // arrays) and `measurements.siding_sqft` / `eaves_lf`, NOT in
    // `measurements.walls` (which was never populated). The prior
    // predicate was permanently false-positive-blocking successful
    // runs; the runtime guard would trigger even when reconciliation
    // succeeded. Trust siding sqft + raw_ai geometry counts instead.
    const ra = preview?.raw_ai || {};
    if (ra._reconciliation_error) {
      toast.error(
        "Reconciliation failed — Apply is disabled. " +
        "Use Retry Reconciliation on the failed run first."
      );
      return;
    }
    const m = preview?.measurements || {};
    const raWalls = Array.isArray(ra.walls) ? ra.walls.length : 0;
    const raDormers = Array.isArray(ra.dormers) ? ra.dormers.length : 0;
    const raOpenings = Array.isArray(ra.openings) ? ra.openings.length : 0;
    const sidingSqft = Number(m.siding_sqft || 0);
    const eavesLf = Number(m.eaves_lf || 0);
    const hasReconciledFootprint =
      raWalls > 0 || raDormers > 0 || raOpenings > 0 || sidingSqft > 0 || eavesLf > 0;
    if (!hasReconciledFootprint) {
      toast.error(
        "Reconciliation produced no measurement — Apply is disabled. " +
        "Use Retry Reconciliation on the failed run first."
      );
      return;
    }
    // Iter 79j.44 — Orphan-wall safety net. If Phase A left one of the
    // 4 cardinal walls with no direct-view coverage, warn the user
    // BEFORE writing numbers into the estimate. Their dimensions are
    // extrapolated, so a silent Apply lets un-measured walls slip into
    // a customer-facing quote. Bypass via ?window.confirm().
    const orphaned = preview?.measurements?._ai_orphaned_walls || [];
    if (orphaned.length > 0) {
      const ok = window.confirm(
        `This takeoff has unmeasured walls: ${orphaned.join(", ")}.\n\n` +
        `Their dimensions are extrapolated from the walls Claude could see. ` +
        `Apply anyway? (You can also close this dialog, re-shoot the ` +
        `flagged elevations, and Re-Run first.)`
      );
      if (!ok) return;
    }
    setBusy(true);
    try {
      let toApply = preview;
      // If the contractor edited wall geometry, refresh the line items
      // via /measure/map so Charter Oak qty etc. reflect the override
      // before the page merges them into the estimate.
      if (wallsDirty) {
        try {
          const { data } = await api.post("/measure/map", {
            measurements: preview.measurements,
          });
          toApply = { ...preview, lines: data.lines || preview.lines };
        } catch {
          // Non-fatal: fall back to original lines if /measure/map fails.
        }
      }

      // Shared swap routine: pull `swapSqft` ft² out of the headline
      // siding line and add it as a separate shake line. Used for both
      // the gable and dormer toggles below.
      const swapSidingToShake = (currentToApply, swapSqft, sku) => {
        if (!sku || swapSqft <= 0) return currentToApply;
        const isLp = sku.startsWith("LP");
        const tab = isLp ? "lp_smart" : "vinyl";
        const section = isLp ? "LP Smart Siding" : "Vinyl Siding";
        const unit = isLp ? "PCS" : "SQ";
        const qty = isLp ? Math.ceil(swapSqft / 4) : Math.ceil(swapSqft / 100);
        const deductSq = Math.ceil(swapSqft / 100);
        const lines = (currentToApply.lines || []).map((ln) => ({ ...ln }));
        const sidingPrefix = isLp ? "LP Smart Side" : "Charter Oak";
        const idx = lines.findIndex(
          (l) => (l.tab || "vinyl") === tab && (l.name || "").startsWith(sidingPrefix)
        );
        if (idx >= 0) {
          lines[idx] = {
            ...lines[idx],
            qty: Math.max(0, (Number(lines[idx].qty) || 0) - deductSq),
          };
        }
        const existing = lines.findIndex(
          (l) => (l.tab || "vinyl") === tab && l.name === sku
        );
        if (existing >= 0) {
          lines[existing] = {
            ...lines[existing],
            qty: (Number(lines[existing].qty) || 0) + qty,
          };
        } else {
          lines.push({ tab, section, name: sku, unit, qty, mat: 0, lab: 0 });
        }
        return { ...currentToApply, lines };
      };

      const gableSqft = preview?.measurements?._ai_gable_sqft || 0;
      const dormerSqft = preview?.measurements?._ai_dormer_sqft || 0;
      if (quoteGablesAsShake && gableSqft > 0) {
        toApply = swapSidingToShake(toApply, gableSqft, shakeSku);
      }
      if (quoteDormersAsShake && dormerSqft > 0) {
        toApply = swapSidingToShake(toApply, dormerSqft, dormerShakeSku);
      }

      // Iter 78s — stash the rendered elevation drawings (with any
      // contractor nudges + roof overrides) on `measurements._ai_elevations`
      // so the customer Quote PDF can embed them as HOVER-style takeoff
      // sheets. The shape is the same one `ElevationDrawing` consumes.
      try {
        const elevs = buildElevationsFromAIMeasure({
          walls: preview.raw_ai?.walls,
          openings: preview.raw_ai?.openings,
          avg_wall_height_ft: preview.measurements?._ai_avg_wall_height_ft,
        });
        const edits = preview.measurements?._ai_elevation_edits || {};
        const merged = elevs.map((e) => {
          const editsForElev = edits[e.label] || {};
          const opEdits = editsForElev.openings || {};
          return {
            ...e,
            roof_style: editsForElev.roof_style || e.roof_style,
            openings: e.openings.map((op) =>
              opEdits[op.id]
                ? { ...op, x_pct: opEdits[op.id].x_pct, y_pct: opEdits[op.id].y_pct }
                : op
            ),
          };
        });
        if (merged.length) {
          // Iter 78u — write to source-keyed bucket so Compare modal can
          // surface drift across multiple measurement sources. Keep
          // `_ai_elevations` populated with the most recent set (used by
          // the customer Quote PDF).
          const prevBySource =
            toApply.measurements?._ai_elevations_by_source || {};
          toApply = {
            ...toApply,
            measurements: {
              ...(toApply.measurements || {}),
              _ai_elevations: merged,
              _ai_elevations_by_source: { ...prevBySource, ai_photo: merged },
            },
          };
        }
      } catch {
        /* non-fatal */
      }

      // Pass the full preview {measurements, lines, vero_openings, raw_ai}
      // so the page can choose how to merge. ISS uses just measurements;
      // siding/windows merge `lines` directly.
      await onApply(toApply);
      toast.success("AI measurements applied — verify all quantities before quoting");
      // Iter 56g: KEEP + FLUSH the session after Apply.
      // Previously (Iter 50) we deleted the session on Apply. That made
      // logout/login lose everything (photos, annotations, target pin,
      // wall edits) even though re-applying is idempotent. Now we
      // proactively SAVE the session before closing so even a quick
      // Apply (< 1s after AI Measure) gets persisted ahead of the
      // debounced autosave. Session is cleared only by Start Over.
      if (estimateId) {
        try {
          await api.put(`/measure/sessions/${estimateId}`, {
            estimate_id: estimateId,
            photo_urls: photoUrls,
            reference_dim: refDim,
            brick_course_in: brickCourse && parseFloat(brickCourse) > 0 ? parseFloat(brickCourse) : null,
            siding_exposure_in: sidingExposure && parseFloat(sidingExposure) > 0 ? parseFloat(sidingExposure) : null,
            wall_height: wallHeight,
            siding_pct: sidingPct,
            overhang_in: Number(overhangIn ?? 12),
            preview,
            photo_annotations: photoAnnotations,
          });
        } catch {
          // non-fatal — local state still good; the next autosave will
          // catch up if the modal stays open.
        }
      }
      // Close the modal but KEEP local state — re-opening AI Measure
      // lets the contractor add more photos / refine more values without
      // starting over. State is wiped only when the user explicitly
      // cancels via the "Start Over" button.
      setOpen(false);
      // Iter 79j.63 — Same re-arm as closeAll(). Apply also closes the
      // modal; if local state is later cleared before the user
      // reopens, we want the session-check effect to re-fire and
      // surface the Resume banner from the freshly-persisted server
      // doc. Symmetric with closeAll — every path that flips
      // `open=false` must reset the latch.
      setSessionChecked(false);
    } catch (e) {
      toast.error(e.message || "Apply failed");
    } finally {
      setBusy(false);
    }
  };

  const closeAll = () => {
    if (busy) return;
    // "Cancel" / X button: just hide the modal. State (photos, AI result,
    // refinements) is preserved so re-opening picks up where we left off.
    //
    // Iter 56f: flush the autosave IMMEDIATELY before closing. The 1-second
    // debounce was getting cancelled if the contractor closed the modal
    // within 1s of uploading photos / saving annotations — those changes
    // would silently never reach MongoDB and the "Resume" prompt wouldn't
    // appear when the contractor came back. Fire-and-forget; local state
    // is the source of truth either way.
    // Iter 79j.53 — Never persist a failed preview on close. Same
    // guard as the debounced autosave: the run doc is the retry
    // target, the session's job is to remember success only. A
    // failed preview on close would silently overwrite the last-good
    // one and bury a reconciled house.
    const previewIsFailure = !!(preview && preview?.raw_ai?._reconciliation_error);
    if (estimateId && (photoUrls.length > 0 || preview != null) && !previewIsFailure) {
      api
        .put(`/measure/sessions/${estimateId}`, {
          estimate_id: estimateId,
          photo_urls: photoUrls,
          reference_dim: refDim,
          brick_course_in: brickCourse && parseFloat(brickCourse) > 0 ? parseFloat(brickCourse) : null,
          siding_exposure_in: sidingExposure && parseFloat(sidingExposure) > 0 ? parseFloat(sidingExposure) : null,
          wall_height: wallHeight,
          siding_pct: sidingPct,
          overhang_in: Number(overhangIn ?? 12),
          preview,
          photo_annotations: photoAnnotations,
        })
        .catch(() => { /* non-fatal */ });
    }
    setOpen(false);
    // Iter 79j.63 — Re-arm the session-check latch on close so the
    // next modal open re-fetches the server session doc. Before this
    // fix, `sessionChecked` stayed `true` for the lifetime of the
    // mount, meaning any transient local-state loss (photoUrls
    // silently cleared to [] by some code path, e.g. the Jul 7 2026
    // Refine on Photo incident on EST-910869) became unrecoverable:
    // close+reopen the modal, sessionChecked was still true, GET
    // /measure/sessions was skipped, resumePrompt stayed false, the
    // Resume banner never appeared even though the DB doc was intact.
    // Resetting here means the next open always re-syncs against the
    // server — the DB is the source of truth for cross-open recovery.
    setSessionChecked(false);
  };

  const conf = preview?.measurements?._ai_scale_confidence || "low";
  const confColor =
    conf === "high"
      ? "text-[var(--success)] border-[var(--success)] bg-green-50"
      : conf === "medium"
      ? "text-[#D97706] border-[#D97706] bg-[var(--hint-bg)]"
      : "text-[var(--danger-text)] border-[#DC2626] bg-red-50";

  return (
    <div data-testid="ai-measure" className="w-full">
      <button
        type="button"
        className="w-full justify-center px-3 py-1.5 bg-[var(--surface)] text-[var(--ai)] border border-[var(--ai)] hover:bg-[var(--surface-muted)] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50"
        onClick={() => setOpen(true)}
        data-testid="ai-measure-btn"
        title={preview ? "Resume AI measure session — add more photos or refine" : "AI photo measure — upload 2-8 phone photos of the house (+ optional aerial)"}
      >
        <Sparkles className="w-3.5 h-3.5" />
        {preview ? "AI Measure (Resume)" : "AI Measure"}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
          onClick={closeAll}
          data-testid="ai-measure-backdrop"
        >
          <div
            className="bg-[var(--surface)] max-w-2xl w-full max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
            data-testid="ai-measure-modal"
          >
            {/* Iter 79j.57c — Onboarding checklist overlay. Opens the
                first time a user reaches AI Measure (localStorage
                remembers the dismissal) and can be re-opened from the
                purple "Tips" button in the header. Explains Howard's
                marker SOP so 8-photo runs don't ship with corners-only
                markers (which the reconciler treats as amber). */}
            {showOnboarding && (
              <div
                className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-6"
                onClick={dismissOnboarding}
                data-testid="ai-measure-onboarding-backdrop"
              >
                <div
                  className="bg-[var(--surface)] max-w-lg w-full flex flex-col shadow-2xl border border-[var(--border)]"
                  onClick={(e) => e.stopPropagation()}
                  data-testid="ai-measure-onboarding-modal"
                >
                  <div className="bg-[var(--ai)] text-white px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <HelpCircle className="w-4 h-4" />
                      <div className="font-bold uppercase tracking-wider text-[11px]">
                        Photo checklist — read this once
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={dismissOnboarding}
                      className="text-white/90 hover:text-white"
                      aria-label="Close onboarding"
                      data-testid="ai-measure-onboarding-close"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="p-5 space-y-3 text-[12px] text-[var(--ink)] leading-relaxed">
                    {/* Iter 79j.61 — Quantified contextual warning.
                        Appears at the top of the checklist only when
                        the modal was auto-opened because the user has
                        photos but no scale refs (Howard 2026-07-07:
                        "quantified warnings get obeyed; vague ones
                        get dismissed"). */}
                    {unanchoredNudgeActive && (
                      <div
                        className="p-3 border border-[#F59E0B] bg-[#FEF3C7] text-[#78350F] text-[12px]"
                        data-testid="ai-measure-onboarding-unanchored-nudge"
                      >
                        <div className="font-bold uppercase tracking-wider text-[10px] mb-1 text-[#B45309]">
                          Your uploaded photos have no reference markers
                        </div>
                        Photos without reference markers can drift <b>25–90% on dormers
                        and upper features</b>. Add a <b>WALL REF</b> or <b>WIN REF</b> to
                        each elevation for tape-grade accuracy.
                      </div>
                    )}
                    <p className="text-[var(--ink-2)]">
                      The AI measures from what it can <b>see and scale</b>. Follow this
                      checklist and 4–6 photos will beat 10 sloppy ones:
                    </p>
                    <ul className="space-y-2.5">
                      <li className="flex items-start gap-2" data-testid="ai-measure-onboarding-tip-markers">
                        <Check className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <b>3 markers per elevation.</b> Left side, right side, and a wall
                          reference dimension (a taped 4&apos;&nbsp;or&nbsp;5&apos; strip works). The
                          reconciler uses the two edge markers to check for lens distortion
                          and the wall-ref to lock scale.
                        </span>
                      </li>
                      <li className="flex items-start gap-2" data-testid="ai-measure-onboarding-tip-dormers">
                        <Check className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <b>One marker per dormer face.</b> Stand square to the dormer if you
                          can. Without a direct read, width is back-solved from the window
                          and comes in <span className="text-[#F59E0B] font-bold">amber</span>.
                        </span>
                      </li>
                      {/* Iter 79j.69 — SOP line from the red-house exam
                          (right wall: shrubs hid the bottom courses, count
                          declined, cross-plane fallback read +1.5 ft). */}
                      <li className="flex items-start gap-2" data-testid="ai-measure-onboarding-tip-short-walls">
                        <Check className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <b>Short or cluttered walls:</b> shoot straight-on and close enough
                          that the bottom siding courses are visible — the AI counts courses
                          to verify height, and it can&apos;t count what shrubs hide.
                        </span>
                      </li>
                      <li className="flex items-start gap-2" data-testid="ai-measure-onboarding-tip-corners">
                        <Check className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <b>Never rely on corner shots as your primary read.</b> Corners get
                          the reconciler mixed up on which wall belongs to which elevation.
                          Fine as a supplement — <i>never</i> as the only view of a wall.
                        </span>
                      </li>
                      <li className="flex items-start gap-2" data-testid="ai-measure-onboarding-tip-elevations">
                        <Check className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <b>All 4 elevations.</b> Front, right, back, left. Any missing wall
                          is flagged in the result and comes in as an estimate, not a
                          measurement.
                        </span>
                      </li>
                      <li className="flex items-start gap-2" data-testid="ai-measure-onboarding-tip-aerial">
                        <Check className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <b>Add the free aerial view.</b> One click, no extra cost — it
                          confirms footprint and catches walls the ground photos miss.
                        </span>
                      </li>
                      <li className="flex items-start gap-2" data-testid="ai-measure-onboarding-tip-reference">
                        <Check className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <b>Reference dimension counts for a lot.</b> A single accurate
                          reference (a wall width you measured, or a standard 3&apos;0&quot; door
                          you know) flips scale confidence from LOW to HIGH.
                        </span>
                      </li>
                    </ul>
                    <div className="text-[10px] text-[var(--muted)] italic pt-1 border-t border-[var(--border)]">
                      You can re-open this checklist any time from the <b>Tips</b> button in
                      the AI Measure header.
                    </div>
                  </div>
                  <div className="px-5 py-3 border-t border-[var(--border)] flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={dismissOnboarding}
                      className="px-4 py-2 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-[11px] font-bold uppercase tracking-wider inline-flex items-center gap-1.5"
                      data-testid="ai-measure-onboarding-dismiss"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Got it, don&apos;t show again
                    </button>
                  </div>
                </div>
              </div>
            )}
            {/* Iter 79j.57d — Re-run confirmation. Only appears when a
                successful reconciliation exists; specific stats make
                the warning concrete instead of generic. */}
            {rerunConfirm && (() => {
              const ra = preview?.raw_ai || {};
              const dormers = Array.isArray(ra.dormers)
                ? ra.dormers
                : (ra.dormer ? [ra.dormer] : []);
              const sidingSqft = Math.round(preview?.measurements?.siding_sqft || 0);
              const wallCount = Array.isArray(ra.walls) ? ra.walls.length : 0;
              const openingCount = Array.isArray(ra.openings) ? ra.openings.length : 0;
              return (
                <div
                  className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-6"
                  onClick={() => setRerunConfirm(false)}
                  data-testid="ai-measure-rerun-confirm-backdrop"
                >
                  <div
                    className="bg-[var(--surface)] max-w-md w-full flex flex-col shadow-2xl border border-[#F59E0B]"
                    onClick={(e) => e.stopPropagation()}
                    data-testid="ai-measure-rerun-confirm-modal"
                  >
                    <div className="bg-[#FEF3C7] px-4 py-3 flex items-center gap-2 border-b border-[#F59E0B]">
                      <AlertTriangle className="w-4 h-4 text-[#B45309]" />
                      <div className="font-bold uppercase tracking-wider text-[11px] text-[#78350F]">
                        Replace the active reconciled result?
                      </div>
                    </div>
                    <div className="p-5 space-y-3 text-[12px] text-[var(--ink)] leading-relaxed">
                      <p>
                        This estimate has a <b>successful reconciled run</b> —{" "}
                        <b data-testid="ai-measure-rerun-confirm-walls">{wallCount} walls</b>,{" "}
                        <b data-testid="ai-measure-rerun-confirm-dormers">{dormers.length} dormer{dormers.length === 1 ? "" : "s"}</b>,{" "}
                        <b data-testid="ai-measure-rerun-confirm-openings">{openingCount} openings</b>
                        {sidingSqft > 0 && (
                          <>, <b data-testid="ai-measure-rerun-confirm-siding">{sidingSqft} sqft siding</b></>
                        )}.
                      </p>
                      <p className="text-[var(--ink-2)]">
                        Re-running will <b>replace it as the active result</b>. The prior run
                        stays in Debug View history — but this estimate&apos;s applied
                        measurements, line items and 3D render will switch to the new one.
                      </p>
                      {dormers.length > 0 && (
                        <ul className="text-[11px] text-[var(--muted)] list-disc pl-5 space-y-0.5" data-testid="ai-measure-rerun-confirm-dormer-list">
                          {dormers.map((d, i) => (
                            <li key={i}>
                              Dormer {i + 1}: face <b className="text-[var(--ink-2)]">{d.face || "—"}</b>,
                              width <b className="text-[var(--ink-2)]">{d.width_ft != null ? `${Number(d.width_ft).toFixed(1)} ft` : "—"}</b>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                    <div className="px-5 py-3 border-t border-[var(--border)] flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setRerunConfirm(false)}
                        className="px-4 py-2 bg-[var(--surface)] text-[var(--ink-2)] border border-[var(--border)] hover:bg-[var(--surface-muted)] text-[11px] font-bold uppercase tracking-wider"
                        data-testid="ai-measure-rerun-confirm-cancel"
                      >
                        Keep current
                      </button>
                      <button
                        type="button"
                        onClick={() => { setRerunConfirm(false); runMeasure(); }}
                        className="px-4 py-2 bg-[#B45309] text-white hover:bg-[#92400E] text-[11px] font-bold uppercase tracking-wider inline-flex items-center gap-1.5"
                        data-testid="ai-measure-rerun-confirm-proceed"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        Yes, replace
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()}
            {/* Iter 79j.64 — Fix 3: destructive-action confirm. Guards
                Start Over, Start Fresh (recovery banner) and per-photo
                Remove with a SPECIFIC data-loss statement — not a
                generic "are you sure". */}
            {destructiveConfirm && (() => {
              const dc = destructiveConfirm;
              const isPhoto = dc.kind === "remove_photo";
              const isFresh = dc.kind === "start_fresh";
              // What exactly gets destroyed:
              const localPhotos = photoUrls.length;
              const localMarkers = photoUrls.filter((n) => !annotEmpty(photoAnnotations[n])).length;
              const serverPhotos = pendingSessionMeta?.photos || 0;
              const serverHasResult = !!pendingSessionMeta?.hasResult;
              const serverMarkers = pendingSessionMeta?.annotated || 0;
              const photoAnnot = isPhoto ? (photoAnnotations[dc.name] || {}) : {};
              const photoHasMarkers = isPhoto && !annotEmpty(photoAnnot);
              const title = isPhoto
                ? `Remove photo ${dc.idx + 1} of ${localPhotos}?`
                : isFresh
                  ? "Permanently delete the saved session?"
                  : "Wipe this AI Measure session?";
              return (
                <div
                  className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-6"
                  onClick={() => setDestructiveConfirm(null)}
                  data-testid="ai-measure-destructive-confirm-backdrop"
                >
                  <div
                    className="bg-[var(--surface)] max-w-md w-full flex flex-col shadow-2xl border border-[#DC2626]"
                    onClick={(e) => e.stopPropagation()}
                    data-testid="ai-measure-destructive-confirm-modal"
                  >
                    <div className="bg-[#FEE2E2] px-4 py-3 flex items-center gap-2 border-b border-[#DC2626]">
                      <AlertTriangle className="w-4 h-4 text-[#B91C1C]" />
                      <div className="font-bold uppercase tracking-wider text-[11px] text-[#7F1D1D]">
                        {title}
                      </div>
                    </div>
                    <div className="p-5 space-y-3 text-[12px] text-[var(--ink)] leading-relaxed" data-testid="ai-measure-destructive-confirm-details">
                      {isPhoto ? (
                        <p>
                          This deletes the photo from the session
                          {photoHasMarkers && (
                            <> — <b>including the markers you drew on it</b>
                            {photoAnnot.reference ? " (wall reference bar)" : ""}
                            {photoAnnot.windowReference ? " (window reference)" : ""}</>
                          )}
                          . You&apos;ll need to re-upload and re-mark it to get it back.
                        </p>
                      ) : isFresh ? (
                        <p>
                          The server session holds{" "}
                          <b>{serverPhotos} photo{serverPhotos === 1 ? "" : "s"}</b>
                          {serverHasResult && <>, <b>a reconciled AI result</b></>}
                          {serverMarkers > 0 && <>, <b>markers on {serverMarkers} photo{serverMarkers === 1 ? "" : "s"}</b></>}
                          . Start Fresh <b>permanently deletes all of it from the server</b> — there is no undo.
                          If you want that work, click Cancel and hit Resume instead.
                        </p>
                      ) : (
                        <p>
                          This wipes{" "}
                          <b>{localPhotos} uploaded photo{localPhotos === 1 ? "" : "s"}</b>
                          {preview != null && <>, <b>the current AI result</b></>}
                          {localMarkers > 0 && <>, <b>markers on {localMarkers} photo{localMarkers === 1 ? "" : "s"}</b></>}
                          {" "}and <b>deletes the saved session from the server</b>. Prior runs stay in
                          Debug View history, but this working session cannot be recovered.
                        </p>
                      )}
                    </div>
                    <div className="px-5 py-3 border-t border-[var(--border)] flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setDestructiveConfirm(null)}
                        className="px-4 py-2 bg-[var(--surface)] text-[var(--ink-2)] border border-[var(--border)] hover:bg-[var(--surface-muted)] text-[11px] font-bold uppercase tracking-wider"
                        data-testid="ai-measure-destructive-confirm-cancel"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={proceedDestructive}
                        className="px-4 py-2 bg-[#DC2626] text-white hover:bg-[#B91C1C] text-[11px] font-bold uppercase tracking-wider inline-flex items-center gap-1.5"
                        data-testid="ai-measure-destructive-confirm-proceed"
                      >
                        <X className="w-3.5 h-3.5" />
                        {isPhoto ? "Yes, remove photo" : "Yes, delete it"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()}
            <div className="bg-gradient-to-r from-[#7C3AED] to-[#A855F7] text-white px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5" />
                <div>
                  <div className="font-heading text-lg">AI Photo Measure</div>
                  <div className="text-xs opacity-90 mt-0.5">
                    Upload 2-8 phone photos · + free aerial · Claude Opus 4.5
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* Iter 79j.57c — Re-open the onboarding checklist on
                    demand. Small, unobtrusive; the checklist itself
                    only auto-opens the FIRST time (localStorage). */}
                <button
                  type="button"
                  className="text-white/90 hover:text-white p-1 inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold"
                  onClick={() => setShowOnboarding(true)}
                  data-testid="ai-measure-open-onboarding"
                  title="Show the photo-capture checklist"
                >
                  <HelpCircle className="w-4 h-4" />
                  Tips
                </button>
                <button
                  type="button"
                  className="text-white/90 hover:text-white"
                  onClick={closeAll}
                  aria-label="Close"
                  data-testid="ai-measure-close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="overflow-y-auto flex-1 p-5">
              {/* Iter 79j.45 — Soft health-warning banner. Only shown
                  when the health ping returned `ambiguous` (unknown
                  response format). The Run button STAYS enabled — a
                  broken health check must not lock the product. */}
              {aiHealth?.status === "ambiguous" && (
                <div
                  className="mb-4 p-3 border border-[#F59E0B] bg-[#FEF3C7] text-[#78350F] text-[11px] flex items-start gap-2"
                  data-testid="ai-measure-health-warning-banner"
                >
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-[var(--warning-text)]" />
                  <div className="flex-1">
                    <div className="font-bold uppercase tracking-wider text-[10px] mb-1">
                      AI health check inconclusive
                    </div>
                    <div className="whitespace-pre-wrap break-words">
                      {aiHealth.detail || "Health check returned an unexpected response — you can still run, but if the run fails, check the LLM proxy."}
                    </div>
                  </div>
                </div>
              )}
              {/* Iter 79j.30 — persistent run-error banner shown at the
                  very top of the modal body (above Resume) so a budget-
                  exceeded or worker failure ALWAYS surfaces, even when
                  the user has no preview yet. Budget errors get their
                  own actionable copy pointing at Profile → Universal Key. */}
              {runError && (
                <div
                  className="mb-4 p-3 border border-[var(--danger)] bg-[#FEE2E2] text-[#7F1D1D] text-[11px] flex items-start gap-2"
                  data-testid="ai-measure-run-error-banner"
                >
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-[var(--danger-text)]" />
                  <div className="flex-1">
                    <div className="font-bold uppercase tracking-wider text-[10px] mb-1 flex items-center justify-between">
                      <span>{
                        /Budget/i.test(runError)
                          ? "Universal Key budget exhausted"
                          : (runErrorMeta?.origin === "resume"
                              ? "Prior reconciliation failed"
                              : "AI Measure failed")
                      }</span>
                      <button
                        type="button"
                        className="text-[10px] font-normal text-[#7F1D1D] underline hover:no-underline"
                        onClick={dismissRunError}
                        data-testid="ai-measure-run-error-dismiss"
                      >
                        dismiss
                      </button>
                    </div>
                    {/Budget/i.test(runError) ? (
                      <div>
                        Your Emergent LLM Key balance is spent. Open the platform menu
                        in the top-right and go to <b>Profile → Universal Key → Add Balance</b>
                        {" "}(or toggle Auto Top-up). Once topped up, click Run AI Measure
                        again — nothing on this estimate is lost.
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap break-words">
                        {runErrorMeta?.origin === "resume" && (
                          <div className="mb-1 italic text-[#7F1D1D] opacity-80">
                            Restored from a previous session — no fresh call was made.
                            Click Retry Reconciliation below to try Phase B again.
                          </div>
                        )}
                        {runError}
                      </div>
                    )}
                    {/* Iter 79j.44 — Phase / elapsed / retry footer.
                        Never let a failed run disappear in a toast: we
                        stamp the stage the pipeline was in, wall-clock
                        elapsed since the user clicked Run, and give a
                        one-click Retry. */}
                    {runErrorMeta && (
                      <div className="mt-2 flex items-center gap-3 text-[10px] uppercase tracking-wider text-[#7F1D1D] opacity-80">
                        <span data-testid="ai-measure-run-error-stage">
                          Phase: <b>{runErrorMeta.stage || "unknown"}</b>
                        </span>
                        {runErrorMeta.elapsedMs != null && (
                          <span data-testid="ai-measure-run-error-elapsed">
                            Elapsed: <b>{Math.round((runErrorMeta.elapsedMs || 0) / 1000)}s</b>
                          </span>
                        )}
                        {runErrorMeta.kind && (
                          <span data-testid="ai-measure-run-error-kind">
                            Kind: <b>{runErrorMeta.kind}</b>
                          </span>
                        )}
                        {runErrorMeta.origin === "resume" && (
                          <span data-testid="ai-measure-run-error-origin">
                            Origin: <b>resumed session</b>
                          </span>
                        )}
                      </div>
                    )}
                    <div className="mt-2 flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => { setRunError(null); setRunErrorMeta(null); runMeasure(); }}
                        disabled={busy || photoUrls.length === 0}
                        className="px-3 py-1.5 bg-[#7F1D1D] text-white hover:bg-[#991B1B] text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                        data-testid="ai-measure-run-error-retry"
                      >
                        <RotateCcw className="w-3 h-3" /> Retry Run
                      </button>
                      {/* Iter 79j.51 — Reconcile-only retry button.
                          Only shown when the run failure was in Phase B
                          (reconciliation) AND we have a currentRunId
                          whose raw_per_photo is still on disk. Runs
                          Phase B alone against the saved extractions —
                          skips paying for Phase A vision again. */}
                      {currentRunId && /reconcil|BadGateway|502|Phase\s*B/i.test(runError || "") && (
                        <button
                          type="button"
                          onClick={() => retryReconcileOnly(currentRunId)}
                          disabled={busy}
                          className="px-3 py-1.5 bg-[#7F1D1D] text-white hover:bg-[#991B1B] text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                          data-testid="ai-measure-reconcile-only-retry"
                          title="Retry ONLY Phase B (reconciliation). Keeps Phase A's vision output — costs pennies instead of a full re-run."
                        >
                          <RotateCcw className="w-3 h-3" /> Retry Reconciliation
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
              {resumePrompt && (
                <div
                  className="mb-4 border-2 border-[#F59E0B] bg-[#FFFBEB]"
                  data-testid="ai-measure-resume-banner"
                >
                  {/* Iter 79j.64 — Fix 2: LOUD recovery banner. Fires when
                      the server holds a saved session but this device's
                      memory is empty — the exact state where a stray
                      "Start fresh" click destroys real work. Names the
                      specific contents so the choice is informed. */}
                  <div className="bg-[#F59E0B] px-3 py-1.5 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-white" />
                    <span className="text-white font-bold uppercase tracking-wider text-[11px]">
                      Saved work found on the server
                    </span>
                  </div>
                  <div className="p-3 flex items-center justify-between gap-3 flex-wrap">
                    <div className="text-xs text-[#78350F] leading-relaxed" data-testid="ai-measure-recovery-details">
                      This device has nothing loaded, but the server holds your saved AI Measure session:{" "}
                      <b>{pendingSessionMeta?.photos || 0} photo{(pendingSessionMeta?.photos || 0) === 1 ? "" : "s"}</b>
                      {pendingSessionMeta?.hasResult && <>, <b>a reconciled AI result</b></>}
                      {(pendingSessionMeta?.annotated || 0) > 0 && (
                        <>, <b>markers on {pendingSessionMeta.annotated} photo{pendingSessionMeta.annotated === 1 ? "" : "s"}</b></>
                      )}
                      . <b>Resume</b> restores everything. <b>Start fresh</b> permanently deletes it.
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={resumeSession}
                        className="px-4 py-2 bg-[#0EA5E9] text-white hover:bg-[#0284C7] text-xs font-bold uppercase tracking-wider flex items-center gap-1"
                        data-testid="ai-measure-resume-btn"
                      >
                        <RotateCcw className="w-3 h-3" /> Resume
                      </button>
                      <button
                        type="button"
                        onClick={() => setDestructiveConfirm({ kind: "start_fresh" })}
                        className="px-3 py-2 bg-[var(--surface)] text-[var(--danger-text)] border border-[#DC2626] hover:bg-red-50 text-xs font-bold uppercase tracking-wider"
                        data-testid="ai-measure-discard-btn"
                      >
                        Start fresh
                      </button>
                    </div>
                  </div>
                </div>
              )}
              {/* Iter 79j.60 — Live per-photo HUD. Contractor-plain
                  language ONLY — the strip says "photo 3 didn't
                  complete", not "wave 2 timed out". Renders while a
                  Phase A run is in flight AND briefly after it
                  finishes so the failed dots stay visible next to
                  the gap banner below. Cleared on the next Run. */}
              {photoProgress && photoProgress.total > 0 && (() => {
                const status = photoProgress.photo_status || {};
                const total = photoProgress.total;
                const failedList = [];
                const okList = [];
                const pendingList = [];
                let inFlightList = [];
                for (let i = 0; i < total; i += 1) {
                  const st = status[String(i)];
                  if (st === "failed") failedList.push(i);
                  else if (st === "ok") okList.push(i);
                  else pendingList.push(i);
                }
                // Contractor-plain status line: prefer failures (they
                // are the actionable news) over throughput counts.
                let statusLine;
                if (failedList.length > 0 && (okList.length + failedList.length) === total) {
                  statusLine = failedList.length === 1
                    ? `Photo ${failedList[0] + 1} didn't complete — you can re-shoot it later.`
                    : `Photos ${failedList.map((n) => n + 1).join(", ")} didn't complete — you can re-shoot them later.`;
                } else if (failedList.length > 0) {
                  const doneStr = failedList.length === 1
                    ? `Photo ${failedList[0] + 1} didn't complete.`
                    : `Photos ${failedList.map((n) => n + 1).join(", ")} didn't complete.`;
                  statusLine = `Reading photos… ${doneStr} Continuing with the rest.`;
                } else if (okList.length === total) {
                  statusLine = `All ${total} photos read.`;
                } else if (okList.length > 0) {
                  // Guess in-flight = the smallest pending index (first
                  // photo of the current wave). Simple heuristic —
                  // contractor-plain "reading photo N".
                  inFlightList = pendingList.slice(0, Math.max(1, Math.min(pendingList.length, photoProgress.concurrency || 2)));
                  const inFlightStr = inFlightList.length === 1
                    ? `photo ${inFlightList[0] + 1}`
                    : `photos ${inFlightList.map((n) => n + 1).join(" & ")}`;
                  statusLine = `Read ${okList.length} of ${total} · working on ${inFlightStr}…`;
                } else {
                  statusLine = `Reading photos 1–${total}…`;
                }
                return (
                  <div
                    className="mb-4 p-3 border border-[var(--border)] bg-[var(--surface-muted)]"
                    data-testid="ai-measure-photo-hud"
                  >
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)] mb-1.5">
                      Photo progress
                    </div>
                    <div className="flex flex-wrap gap-1.5 items-center mb-2" data-testid="ai-measure-photo-hud-dots">
                      {Array.from({ length: total }).map((_, i) => {
                        const st = status[String(i)];
                        let dotCls;
                        let dotLabel;
                        if (st === "ok") {
                          dotCls = "bg-[var(--success)] text-white";
                          dotLabel = `Photo ${i + 1}: read`;
                        } else if (st === "failed") {
                          dotCls = "bg-[#B45309] text-white";
                          dotLabel = `Photo ${i + 1}: didn't complete`;
                        } else if (inFlightList.includes(i)) {
                          dotCls = "bg-[var(--ai)] text-white animate-pulse";
                          dotLabel = `Photo ${i + 1}: reading now`;
                        } else {
                          dotCls = "bg-[var(--border)] text-[var(--muted)]";
                          dotLabel = `Photo ${i + 1}: pending`;
                        }
                        return (
                          <span
                            key={i}
                            className={`inline-flex items-center justify-center min-w-[22px] h-[22px] px-1.5 text-[10px] font-bold ${dotCls}`}
                            title={dotLabel}
                            data-testid={`ai-measure-photo-hud-dot-${i}`}
                            data-status={st || (inFlightList.includes(i) ? "in_progress" : "pending")}
                          >
                            {i + 1}
                          </span>
                        );
                      })}
                    </div>
                    <div
                      className="text-[11px] text-[var(--ink-2)]"
                      data-testid="ai-measure-photo-hud-status-line"
                    >
                      {statusLine}
                    </div>
                  </div>
                );
              })()}
              {/* Iter 79j.62 — Marker Coverage Tile. Read-only 4-cell
                  grid (front / right / back / left) that lights green
                  when the elevation has ≥1 `_scale_refs` entry, red
                  when it doesn't, and amber when a dormer pin sits on
                  a ref-less elevation (that's the specific accuracy
                  risk the 79j.61 plumbing quantifies). Same data
                  source as the contextual nudge — `photoAnnotations`
                  — no new state or network. Persistent so contractors
                  see the accuracy contract at every stage (upload,
                  running, results). */}
              {photoUrls.length > 0 && (() => {
                // Iter 79j.63 — Coverage tile rewired to read the SESSION
                // shape of `photoAnnotations` (keyed by photo name,
                // entries are `{elevation, reference, windowReference,
                // zones, ...}`) — NOT the ProfileAnnotator shape (keyed
                // by index string, entries are arrays of boxes).
                //
                // The original Iter 79j.61 tile iterated the wrong
                // shape and skipped every entry via
                // `Array.isArray(boxes)`, so all 4 cardinals rendered
                // "No coverage yet" even when the contractor had
                // placed all 8 WALL_REFs + 8 WIN_REFs. The Jul 7 2026
                // Red-House incident surfaced this — the operator's
                // 324/444/324/etc. refs were present verbatim in the
                // session doc but the tile insisted no coverage
                // existed. This is a pure display bug, not data loss.
                const cardinals = ["front", "right", "back", "left"];
                // A cardinal is "covered" if ANY photo whose elevation
                // matches (or contains) that cardinal has a wall or
                // window reference. Corner photos (front-right,
                // rear-left, etc.) count toward BOTH cardinals they
                // border — a well-placed WIN_REF on a front-right shot
                // supplies scale for both front and right dormers.
                const matchesCardinal = (elev, card) => {
                  if (!elev) return false;
                  const e = String(elev).toLowerCase();
                  if (e === card) return true;
                  // corner photos like "front-right" match both parts
                  return e.split(/[-_/ ]/).includes(card);
                };
                const cellFor = (card) => {
                  let hasRef = false;
                  let hasWinRef = false;
                  let hasPin = false;
                  for (const [name, entry] of Object.entries(photoAnnotations || {})) {
                    if (name.startsWith("_")) continue;
                    if (!entry || typeof entry !== "object") continue;
                    if (!matchesCardinal(entry.elevation, card)) continue;
                    hasPin = true; // photo has this elevation tagged
                    if (entry.reference && entry.reference.inches > 0) hasRef = true;
                    if (entry.windowReference && entry.windowReference.inches > 0) hasWinRef = true;
                  }
                  if (hasRef) return { state: "green", label: `Wall ref set` };
                  if (hasWinRef) return { state: "green", label: `Win ref set` };
                  if (hasPin) return { state: "red", label: "Pinned, no marker" };
                  return { state: "grey", label: "No coverage yet" };
                };
                const cells = cardinals.map((c) => ({ elev: c, ...cellFor(c) }));
                const anyAmber = cells.some((c) => c.state === "amber");
                const anyRedOrGrey = cells.some((c) => c.state === "red" || c.state === "grey");
                return (
                  <div
                    className="mb-4 border border-[var(--border)] bg-[var(--surface-muted)]"
                    data-testid="ai-measure-marker-coverage"
                  >
                    <div className="px-3 py-1.5 border-b border-[var(--border)] flex items-center justify-between gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
                        Reference marker coverage
                      </span>
                      <span
                        className="text-[10px] text-[var(--muted)]"
                        data-testid="ai-measure-marker-coverage-summary"
                      >
                        {anyAmber
                          ? "Dormer pinned without a marker — widths will drift 25–90%"
                          : anyRedOrGrey
                          ? "Some elevations missing markers — accuracy risk on those"
                          : "All 4 elevations anchored · tape-grade"}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-1.5 p-2">
                      {cells.map((c) => {
                        let cls;
                        let dotCls;
                        if (c.state === "green" || c.state === "green_dormer") {
                          cls = "border-[var(--success)] bg-[var(--success)]/10 text-[#065F46]";
                          dotCls = "bg-[var(--success)]";
                        } else if (c.state === "amber") {
                          cls = "border-[#F59E0B] bg-[#FEF3C7] text-[#78350F]";
                          dotCls = "bg-[#B45309]";
                        } else if (c.state === "red") {
                          cls = "border-[var(--danger)] bg-[var(--danger)]/10 text-[#7F1D1D]";
                          dotCls = "bg-[var(--danger)]";
                        } else {
                          cls = "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]";
                          dotCls = "bg-[var(--border)]";
                        }
                        return (
                          <div
                            key={c.elev}
                            className={`border ${cls} p-1.5 flex flex-col items-start gap-0.5`}
                            data-testid={`ai-measure-marker-coverage-cell-${c.elev}`}
                            data-state={c.state}
                            title={`${c.elev.toUpperCase()} — ${c.label}`}
                          >
                            <div className="flex items-center gap-1.5">
                              <span className={`w-1.5 h-1.5 rounded-full ${dotCls}`} aria-hidden />
                              <span className="text-[10px] font-bold uppercase tracking-wider">{c.elev}</span>
                            </div>
                            <div className="text-[9px] leading-tight">{c.label}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}
              {/* Iter 57r — Resume last AI run banner */}
              {lastRun && (lastRun.status === "running" || (lastRun.status === "done" && lastRun.result) || lastRun.status === "error") && (
                <div
                  className="mb-4 p-3 border border-[var(--ai)] bg-purple-50 flex items-center justify-between gap-3 flex-wrap"
                  data-testid="ai-measure-resume-run-banner"
                >
                  <div className="text-xs text-[#581C87]">
                    <span className="font-bold uppercase tracking-wider text-[10px] mr-2">
                      {lastRun.status === "running" ? "AI run in progress" : lastRun.status === "error" ? "Last AI run failed" : "Recent AI run"}
                    </span>
                    {lastRun.status === "running" && (
                      <>
                        {lastRun.photo_count || 0} photo{(lastRun.photo_count || 0) === 1 ? "" : "s"} —
                        started {Math.round((lastRun.age_seconds || 0))}s ago, currently <b>{lastRun.stage || "running"}</b>.
                        Reconnect to keep watching progress.
                      </>
                    )}
                    {lastRun.status === "done" && (
                      <>
                        Finished {Math.round((lastRun.age_seconds || 0) / 60)} min ago on {lastRun.photo_count || 0} photo{(lastRun.photo_count || 0) === 1 ? "" : "s"}.
                        Restore the preview without re-running Claude.
                      </>
                    )}
                    {lastRun.status === "error" && (
                      <>
                        {lastRun.error || "Worker crashed"} — try a smaller photo set.
                      </>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {lastRun.status === "running" && (
                      <button
                        type="button"
                        onClick={resumeRunPolling}
                        className="px-3 py-1.5 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-xs font-bold uppercase tracking-wider flex items-center gap-1"
                        data-testid="ai-measure-resume-run-btn"
                      >
                        <Loader2 className="w-3 h-3 animate-spin" /> Reconnect
                      </button>
                    )}
                    {lastRun.status === "done" && (
                      <button
                        type="button"
                        onClick={restoreLastRun}
                        className="px-3 py-1.5 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-xs font-bold uppercase tracking-wider flex items-center gap-1"
                        data-testid="ai-measure-restore-run-btn"
                      >
                        <Check className="w-3 h-3" /> Restore preview
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setLastRun(null)}
                      className="px-3 py-1.5 bg-[var(--surface)] text-[var(--ink-2)] border border-[var(--border)] hover:bg-[var(--surface-muted)] text-xs font-bold uppercase tracking-wider"
                      data-testid="ai-measure-dismiss-run-btn"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              )}
              {/* Warning banner — set expectations honestly */}
              <div className="border border-[var(--hint-line)] bg-[var(--hint-bg)] px-3 py-2 mb-4 text-xs text-[var(--hint-ink-2)] flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  AI photo measurement is an <strong>estimate, not a survey</strong>.
                  Upload <strong>all 4 elevations</strong> (front, back, left, right) for best
                  accuracy — Claude will only count walls it can actually see and will
                  flag any missing sides in the result.
                </div>
              </div>

              {!preview && (
                <>
                  {/* File picker */}
                  <label className="block mb-3">
                    <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-1">
                      Photos (2-8 + aerial)
                    </div>
                    <div className="border-2 border-dashed border-[var(--border)] rounded-sm px-4 py-6 text-center hover:border-[var(--ai)] transition-colors cursor-pointer">
                      <input
                        ref={fileRef}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        capture="environment"
                        multiple
                        className="hidden"
                        onChange={pickFiles}
                        data-testid="ai-measure-file-input"
                      />
                      <Camera className="w-8 h-8 mx-auto mb-2 text-[var(--ai)]" />
                      <button
                        type="button"
                        onClick={() => fileRef.current?.click()}
                        className="text-sm font-bold text-[var(--ai)] uppercase tracking-wider"
                        disabled={photoUrls.length >= 9}
                      >
                        {photoUrls.length > 0 ? "Add more photos" : "Choose / Take Photos"}
                      </button>
                      <div className="text-[10px] text-[var(--muted)] mt-1">
                        Tip: front, back, left, right elevations + any tricky corners
                      </div>
                      {/* Iter 57: HOVER-style guided capture wizard. Walks
                          contractor through 8 standard positions and
                          auto-tags each photo's elevation as it captures.
                          Biggest single accuracy lever — eliminates the
                          "garbage in" problem at the source. */}
                      <div className="mt-2">
                        <button
                          type="button"
                          onClick={() => setCalibPrepOpen(true)}
                          disabled={photoUrls.length >= 9}
                          className="px-3 py-1.5 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1.5 disabled:opacity-50"
                          data-testid="ai-measure-wizard-btn"
                          title="HOVER-style step-by-step capture — walks you through 8 elevation positions, auto-tags each photo"
                        >
                          <Sparkles className="w-3 h-3" />
                          Guided Capture (recommended)
                        </button>
                      </div>
                      {/* Iter 56c: free aerial view via Esri World Imagery.
                          Auto-fetches a top-down photo of the property
                          from the estimate address — dramatically
                          sharpens eaves/rakes since rooflines read much
                          cleaner from above. No API key required.
                          Iter 56d: button stays visible even when the
                          address is missing so contractors can see the
                          option exists; clicking it without an address
                          gives a helpful toast pointing them to the
                          right field. */}
                      <div className="mt-2">
                        <button
                          type="button"
                          onClick={fetchSatellite}
                          disabled={satBusy || photoUrls.length >= 9}
                          className="px-3 py-1.5 bg-[var(--surface)] text-[#0EA5E9] border border-[#0EA5E9] hover:bg-[#F0F9FF] text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1.5 disabled:opacity-50"
                          data-testid="ai-measure-satellite-btn"
                          title={address ? "Fetch a free top-down satellite view from Esri World Imagery" : "Fill in the Address field in Job Information first"}
                        >
                          {satBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          {satBusy ? "Fetching aerial…" : "Add aerial view (free)"}
                        </button>
                        {!address && (
                          <div className="text-[10px] text-[var(--muted)] mt-1">
                            Address required — fill in <b>Address</b> in Job Information first.
                          </div>
                        )}
                      </div>
                      {(photoUrls.length > 0 || files.length > 0) && (
                        <div className="mt-3 text-xs text-[var(--ink-2)] flex items-center justify-center gap-2 flex-wrap" data-testid="ai-measure-file-count">
                          <span>
                            {photoUrls.length} uploaded
                            {files.length > 0 && ` · ${files.length} uploading…`}
                          </span>
                        </div>
                      )}
                      {photoUrls.length > 0 && (
                        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2" data-testid="ai-measure-photo-grid">
                          {photoUrls.map((name, i) => {
                            const annot = photoAnnotations[name] || {};
                            const hasRef = !!annot.reference;
                            const hasWinRef = !!annot.windowReference;
                            const zoneCount = (annot.zones || []).length;
                            const elev = annot.elevation || "";
                            // Iter 57o — when an AI Measure run has
                            // produced an openings_schedule with bboxes,
                            // overlay HOVER-style labeled callouts on
                            // each photo. Same look as the PDF, but in
                            // the live preview so the contractor can
                            // catch a misplaced label and edit BEFORE
                            // generating the report.
                            const aiSched = (preview && (
                              preview.measurements?._ai_openings_schedule ||
                              preview.raw_ai?.openings_schedule || []
                            )) || [];
                            const photoCallouts = [];
                            const seenKeys = new Set();
                            for (const row of aiSched) {
                              for (const loc of (row.locations || [])) {
                                if (Number(loc.photo_idx) !== i) continue;
                                const bb = loc.bbox || {};
                                const bx = Number(bb.x), by = Number(bb.y);
                                const bw = Number(bb.w || 0), bh = Number(bb.h || 0);
                                if (!(bx >= 0 && bx <= 1 && by >= 0 && by <= 1 && bw > 0 && bh > 0 && bx + bw <= 1.001 && by + bh <= 1.001)) continue;
                                const key = `${bx.toFixed(3)},${by.toFixed(3)},${bw.toFixed(3)},${bh.toFixed(3)}`;
                                if (seenKeys.has(key)) continue;
                                seenKeys.add(key);
                                const wi = Math.round(Number(row.width_in) || 0);
                                const hi = Math.round(Number(row.height_in) || 0);
                                const t = String(row.type || "window").toLowerCase();
                                const style = String(row.style || "");
                                let label = `${wi}×${hi}`;
                                if (t === "garage_door") label = `${wi}×${hi} Garage`;
                                else if (t === "entry_door") label = `${wi}×${hi} Entry`;
                                else if (t === "patio_door") label = `${wi}×${hi} Patio`;
                                else {
                                  let short = "";
                                  if (/Double Hung|Twin Double/i.test(style)) short = "DH";
                                  else if (/Single Hung/i.test(style)) short = "SH";
                                  else if (/Casement/i.test(style)) short = "CS";
                                  else if (/Slider/i.test(style)) short = "SL";
                                  else if (/Picture/i.test(style)) short = "PIC";
                                  else if (/Awning/i.test(style)) short = "AW";
                                  else if (/Hopper/i.test(style)) short = "HP";
                                  if (short) label = `${short} ${label}`;
                                }
                                const labelY = by > 0.07 ? by - 0.025 : by + 0.005;
                                const lcx = bx + bw / 2;
                                const lblFs = 3.0;
                                const bgW = Math.min(0.98 - lcx + 0.5, Math.max(0.10, label.length * lblFs * 0.0048));
                                const bgX = Math.max(0.005, Math.min(1 - bgW - 0.005, lcx - bgW / 2));
                                photoCallouts.push(
                                  <g key={key}>
                                    <rect x={bx * 100} y={by * 100} width={bw * 100} height={bh * 100}
                                          fill="none" stroke="#FACC15" strokeWidth={0.6} />
                                    <rect x={bgX * 100} y={labelY * 100} width={bgW * 100} height={lblFs + 0.6}
                                          fill="#09090B" />
                                    <text x={(bgX + bgW / 2) * 100} y={labelY * 100 + lblFs * 0.85}
                                          textAnchor="middle" fontSize={lblFs} fontWeight={700} fill="#FACC15">
                                      {label}
                                    </text>
                                  </g>
                                );
                              }
                            }
                            return (
                              <div key={name} className="relative border border-[var(--border)] overflow-hidden bg-[var(--surface-muted)]">
                                <div className="relative aspect-video">
                                  <img
                                    src={`/api/uploads/${name}`}
                                    alt={`Photo ${i + 1}`}
                                    className="w-full h-full object-cover"
                                  />
                                  {photoCallouts.length > 0 && (
                                    <svg
                                      viewBox="0 0 100 100"
                                      preserveAspectRatio="none"
                                      className="absolute inset-0 w-full h-full pointer-events-none"
                                      data-testid={`ai-measure-photo-callouts-${i}`}
                                    >
                                      {photoCallouts}
                                    </svg>
                                  )}
                                  <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); setDestructiveConfirm({ kind: "remove_photo", idx: i, name }); }}
                                    className="absolute top-0.5 right-0.5 bg-[var(--bar-bg)] text-white w-5 h-5 flex items-center justify-center text-xs hover:bg-[#DC2626]"
                                    data-testid={`ai-measure-photo-remove-${i}`}
                                    title="Remove this photo"
                                  >×</button>
                                  {/* Status badges */}
                                  <div className="absolute bottom-0.5 left-0.5 flex gap-1 flex-wrap">
                                    {elev && elev !== "" && (
                                      <span className="bg-[var(--ai)] text-white text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold">
                                        {elev}
                                      </span>
                                    )}
                                    {hasRef && (
                                      <span className="bg-[#DC2626] text-white text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold">
                                        Wall ✓
                                      </span>
                                    )}
                                    {hasWinRef && (
                                      <span className="bg-[#2563EB] text-white text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold" data-testid={`ai-measure-photo-winref-badge-${i}`}>
                                        Win ✓
                                      </span>
                                    )}
                                    {annot.targetPin && (
                                      <span className="bg-[var(--success)] text-white text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold">
                                        Pin ✓
                                      </span>
                                    )}
                                    {zoneCount > 0 && (
                                      <span className="bg-[#B45309] text-white text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold">
                                        {zoneCount} mask{zoneCount > 1 ? "s" : ""}
                                      </span>
                                    )}
                                    {(annot.windows?.length || 0) > 0 && (
                                      <span className="bg-[#FBBF24] text-[var(--warning-text)] text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold border border-[#92400E]" data-testid={`ai-measure-photo-windows-badge-${i}`}>
                                        {annot.windows.length} win
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="p-1.5 space-y-1 border-t border-[var(--border)] bg-[var(--surface)]">
                                  <select
                                    className="input h-7 text-[11px] w-full"
                                    value={elev}
                                    onChange={(e) => setPhotoAnnotations((prev) => ({
                                      ...prev,
                                      [name]: { ...(prev[name] || {}), elevation: e.target.value },
                                    }))}
                                    data-testid={`ai-measure-photo-elev-${i}`}
                                  >
                                    {ELEVATION_OPTIONS.map((o) => (
                                      <option key={o.key} value={o.key}>{o.label}</option>
                                    ))}
                                  </select>
                                  <button
                                    type="button"
                                    onClick={() => setAnnotateOpenFor(name)}
                                    className="w-full px-2 py-1 bg-[var(--surface)] text-[var(--ai)] border border-[var(--ai)] hover:bg-[#FAF5FF] text-[10px] font-bold uppercase tracking-wider flex items-center justify-center gap-1"
                                    data-testid={`ai-measure-photo-annotate-${i}`}
                                    title="Mark a reference scale anchor and/or no-siding zones BEFORE sending to AI"
                                  >
                                    <Wand2 className="w-2.5 h-2.5" />
                                    {hasRef || zoneCount > 0 ? "Edit annotations" : "Annotate"}
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </label>

                </>
              )}

              {/* Result preview */}
              {preview && (
                <>
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 border ${confColor}`} data-testid="ai-measure-confidence">
                      Confidence: {conf}
                    </span>
                    {preview.model && (
                      <span
                        className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 border border-[var(--ai)] text-[var(--ai)] bg-[#FAF5FF]"
                        data-testid="ai-measure-model-badge"
                        title={`Ran on ${preview.model_provider || ""} · ${preview.model}`}
                      >
                        {(() => {
                          // Compact label from the full model id.
                          const m = String(preview.model).toLowerCase();
                          if (m.includes("opus-4-5")) return "Opus 4.5";
                          if (m.includes("opus-4-8")) return "Opus 4.8";
                          if (m.includes("sonnet-4-6")) return "Sonnet 4.6";
                          if (m.includes("fable-5")) return "Fable 5";
                          if (m.includes("gemini-3.5")) return "Gemini 3.5 Flash";
                          if (m.includes("gemini-3.1")) return "Gemini 3.1 Pro";
                          if (m.includes("gemini-3-flash")) return "Gemini 3 Flash";
                          if (m.includes("gpt-5.5")) return "GPT-5.5";
                          if (m.includes("gpt-5.4")) return "GPT-5.4";
                          return preview.model;
                        })()}
                      </span>
                    )}
                    <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
                      Reference: {preview.measurements._ai_reference_used || "none"}
                    </span>
                    {preview.measurements._ai_story_count != null && (
                      <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
                        {preview.measurements._ai_story_count}-story
                      </span>
                    )}
                    {preview.measurements._ai_avg_wall_height_ft != null && (
                      <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
                        wall ht {preview.measurements._ai_avg_wall_height_ft} ft
                      </span>
                    )}
                    {preview.measurements._ai_siding_coverage_pct != null && (
                      <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
                        siding {preview.measurements._ai_siding_coverage_pct}%
                      </span>
                    )}
                  </div>

                  {/* Iter 79j.16 — Model Comparison panel. Renders only
                      when 2+ runs on this estimate have used at least 2
                      DIFFERENT models — nothing to compare otherwise. */}
                  {(() => {
                    const uniqueModels = new Set(modelHistory.map((r) => r.model_choice));
                    if (modelHistory.length < 2 || uniqueModels.size < 2) return null;
                    const MODEL_LABELS = {
                      "claude-opus-4-5":     "Opus 4.5",
                      "claude-opus-4-8":     "Opus 4.8",
                      "claude-sonnet-4-6":   "Sonnet 4.6",
                      "claude-fable-5":      "Fable 5",
                      "gemini-3.5-flash":    "Gemini 3.5 Flash",
                      "gemini-3.1-pro":      "Gemini 3.1 Pro",
                      "gpt-5.5":             "GPT-5.5",
                      "gpt-5.4":             "GPT-5.4",
                    };
                    const fmtCost = (c) => (c == null ? "—" : `$${c.toFixed(3)}`);
                    const totalCost = modelHistory.reduce((sum, r) => sum + (r.cost_estimate_usd || 0), 0);
                    const fmtElapsed = (ms) => {
                      if (!ms) return "—";
                      if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`;
                      return `${(ms / 60000).toFixed(1)}m`;
                    };
                    return (
                      <div className="mb-3 border border-[var(--ai)] bg-[#FAF5FF]" data-testid="ai-measure-model-comparison">
                        <div className="px-3 py-1.5 border-b border-[var(--ai)] bg-[var(--ai)] text-white text-[10px] uppercase tracking-wider font-bold flex items-center justify-between gap-2 flex-wrap">
                          <span>Model Comparison · last {modelHistory.length} runs on this estimate</span>
                          <span className="text-[10px] font-normal flex items-center gap-2">
                            <span className="bg-white/20 px-2 py-0.5 rounded-sm" title="Approximate USD spent A/B testing on this house across all listed runs">
                              A/B spend: <span className="font-bold font-mono-num tabular-nums">${totalCost.toFixed(3)}</span>
                            </span>
                            <span className="opacity-80">Higher = winner</span>
                          </span>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-[11px]">
                            <thead>
                              <tr className="border-b border-[#E9D5FF] bg-[var(--surface)]">
                                <th className="text-left px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Model</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Conf</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Windows</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Doors</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Walls</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Siding ft²</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Eaves LF</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Time</th>
                                <th className="text-right px-2 py-1.5 font-bold text-[var(--muted)] uppercase tracking-wider text-[9px]">Cost</th>
                              </tr>
                            </thead>
                            <tbody>
                              {modelHistory.map((r, i) => (
                                <tr key={r.run_id} className={i === 0 ? "bg-[var(--ai-soft)] font-medium" : "bg-[var(--surface)]"}>
                                  <td className="px-2 py-1.5 font-bold text-[var(--ink)]">
                                    {MODEL_LABELS[r.model_choice] || r.model_choice}
                                    {i === 0 && <span className="ml-1 text-[8px] uppercase text-[var(--ai)]">(latest)</span>}
                                  </td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums">{r.confidence != null ? r.confidence : "—"}</td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums">{r.window_count}</td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums">{r.door_count}</td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums">{r.wall_count}</td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums">{Math.round(r.siding_sqft || 0).toLocaleString()}</td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums">{Math.round(r.eaves_lf || 0)}</td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums text-[var(--muted)]">{fmtElapsed(r.elapsed_ms)}</td>
                                  <td className="px-2 py-1.5 text-right font-mono-num tabular-nums text-[var(--muted)]">{fmtCost(r.cost_estimate_usd)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <div className="px-3 py-1.5 border-t border-[#E9D5FF] bg-[var(--surface)] text-[9px] text-[var(--muted)] italic">
                          Cost is an approximation using published list prices · Compare Conf + counts vs your ground-truth field measurement.
                        </div>
                      </div>
                    );
                  })()}
                  {preview.measurements._ai_story_count_reasoning && (
                    <div className="text-[11px] text-[var(--muted)] mb-2 italic">
                      Story count: {preview.measurements._ai_story_count_reasoning}
                    </div>
                  )}
                  {((preview.measurements._ai_gable_sqft || 0) > 0 ||
                    (preview.measurements._ai_dormer_sqft || 0) > 0) && (
                    <div className="text-[11px] text-[var(--muted)] mb-2 italic" data-testid="ai-measure-geometry-breakdown">
                      Geometry: rectangular walls
                      {(preview.measurements._ai_gable_sqft || 0) > 0 && (
                        <> · gable triangles add <span className="font-bold not-italic">{preview.measurements._ai_gable_sqft} ft²</span></>
                      )}
                      {(preview.measurements._ai_dormer_sqft || 0) > 0 && (
                        <> · dormer faces add <span className="font-bold not-italic">{preview.measurements._ai_dormer_sqft} ft²</span></>
                      )}
                      {" "}— if this doesn&apos;t match the photos, lower the affected wall&apos;s height_ft.
                    </div>
                  )}
                  {preview.measurements._ai_notes && (
                    <div className="text-xs text-[var(--ink-2)] mb-3 italic border-l-2 border-[var(--ai)] pl-3" data-testid="ai-measure-notes">
                      {preview.measurements._ai_notes}
                    </div>
                  )}
                  {/* Iter 79j.22 — Preview / 3D Model tab toggle. Auto-lands
                      on Preview each new run; contractor can flip to 3D
                      Model to sanity-check the parametric geometry
                      Claude/Gemini inferred (pitch, eave, wall widths,
                      opening layout). All estimate line quantities remain
                      SSOT — the 3D side panel READS from preview.lines,
                      never re-computes.  */}
                  <div className="flex items-center gap-1 mb-3 border-b border-[var(--border)]">
                    <button
                      type="button"
                      onClick={() => setPreviewTab("preview")}
                      className={`px-3 py-2 text-[11px] font-bold uppercase tracking-wider border-b-2 transition-colors ${
                        previewTab === "preview"
                          ? "border-[var(--ai)] text-[var(--ai)]"
                          : "border-transparent text-[var(--muted)] hover:text-[var(--ink)]"
                      }`}
                      data-testid="ai-measure-preview-tab"
                    >
                      Preview
                    </button>
                    <button
                      type="button"
                      onClick={() => setPreviewTab("3d")}
                      className={`px-3 py-2 text-[11px] font-bold uppercase tracking-wider border-b-2 transition-colors flex items-center gap-1.5 ${
                        previewTab === "3d"
                          ? "border-[var(--ai)] text-[var(--ai)]"
                          : "border-transparent text-[var(--muted)] hover:text-[var(--ink)]"
                      }`}
                      data-testid="ai-measure-3d-tab"
                    >
                      3D Model
                      <span className="text-[9px] px-1.5 py-0.5 bg-[#F3F4F6] text-[var(--ai)] tracking-normal">BETA</span>
                    </button>
                  </div>

                  {/* Iter 79j.29 — photos-lost banner. When preview
                      exists but the photo grid is empty (typically an
                      older run whose upload names were never persisted),
                      the Re-Run button is disabled and the contractor
                      can't tell why. Explicit inline banner spells it
                      out and points to the upload input. */}
                  {photoUrls.length === 0 && (
                    <div
                      className="mb-3 p-3 bg-[#FEF3C7] border border-[#F59E0B] text-[#78350F] text-[11px] flex items-start gap-2"
                      data-testid="ai-measure-photos-lost-banner"
                    >
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-[var(--warning-text)]" />
                      <div className="flex-1">
                        <div className="font-bold uppercase tracking-wider text-[10px] mb-0.5">Photos missing</div>
                        <div>
                          The measurements below are from an older run whose photo files
                          were not persisted. <b>Re-upload the same photos above</b> to
                          enable Re-Run · Refine on Photo · A/B model comparison. Nothing
                          in the current takeoff will be lost.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Iter 79j.43 — Empty-photo warning banner. When the
                      two-phase Phase A returned nothing (twice, after
                      the auto-retry), name the affected photo(s) and
                      which walls now have no direct-view coverage.
                      A dead photo must NEVER fail silently. */}
                  {(preview?.measurements?._ai_empty_photos?.length > 0
                    || preview?.measurements?._ai_orphaned_walls?.length > 0
                    || preview?.measurements?._ai_pin_gap_hints?.length > 0) && (
                    <div
                      className="mb-3 p-3 bg-[#FEF3C7] border border-[#F59E0B] text-[#78350F] text-[11px] flex items-start gap-2"
                      data-testid="ai-measure-empty-photos-banner"
                    >
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-[var(--warning-text)]" />
                      <div className="flex-1">
                        <div className="font-bold uppercase tracking-wider text-[10px] mb-1">
                          AI extraction gaps detected
                        </div>
                        {preview?.measurements?._ai_empty_photos?.length > 0 && (
                          <div className="mb-1" data-testid="ai-measure-empty-photos-list">
                            <b>{preview.measurements._ai_empty_photos.length} photo{preview.measurements._ai_empty_photos.length === 1 ? "" : "s"} returned no useful data</b> after an automatic retry:
                            <ul className="list-disc list-inside mt-0.5 ml-1">
                              {preview.measurements._ai_empty_photos.map((p, i) => (
                                <li key={i}>
                                  Photo #{Number(p.photo_idx) + 1}
                                  {p.reason ? ` — ${p.reason}` : ""}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {preview?.measurements?._ai_orphaned_walls?.length > 0 && (
                          <div className="mb-1" data-testid="ai-measure-orphaned-walls">
                            <b>Walls with no direct-view coverage:</b>{" "}
                            {preview.measurements._ai_orphaned_walls.join(", ")}.
                            Their dimensions are extrapolated — capture a
                            direct side shot of each and Re-Run before quoting.
                          </div>
                        )}
                        {/* Iter 79j.59 — Contractor-pin gap-signal.
                            When user pins tag a feature on an elevation
                            the reconciled output couldn't cover, we
                            promote that mismatch from the trace into
                            the banner. Each hint carries an actionable
                            re-shoot elevation — no bare warnings. */}
                        {preview?.measurements?._ai_pin_gap_hints?.length > 0 && (
                          <div className="mb-1" data-testid="ai-measure-pin-gap-hints">
                            <b>Your pins suggest coverage the AI didn&apos;t confirm:</b>
                            <ul className="list-disc list-inside mt-0.5 ml-1">
                              {preview.measurements._ai_pin_gap_hints.map((h, i) => (
                                <li
                                  key={`${h.kind}-${h.elevation}-${i}`}
                                  data-testid={`ai-measure-pin-gap-hint-${h.kind}-${h.elevation}`}
                                >
                                  {h.message}
                                  {Array.isArray(h.source_photo_idxs) && h.source_photo_idxs.length > 0 && (
                                    <span className="text-[10px] text-[var(--muted)] ml-1">
                                      (pin
                                      {h.source_photo_idxs.length === 1 ? " on " : "s on "}
                                      photo{h.source_photo_idxs.length === 1 ? "" : "s"}
                                      {" "}
                                      {h.source_photo_idxs.map((n) => `#${n + 1}`).join(", ")})
                                    </span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <div className="text-[var(--warning-text)]">
                          Re-shoot the flagged photos (or delete them and re-upload)
                          then click <b>Re-Run</b> below.
                        </div>
                      </div>
                    </div>
                  )}

                  {previewTab === "3d" && (
                    <div className="mb-4" data-testid="ai-measure-3d-panel">
                      {(() => {
                        // Iter 79j.52 — Never draw a placeholder house
                        // when reconciliation failed or produced zero
                        // geometry. Different failure semantics need
                        // different UI: an empty box implies "we
                        // measured a tiny house", the incomplete
                        // banner correctly reads "we didn't measure".
                        const ra = preview?.raw_ai || {};
                        const failed = !!ra._reconciliation_error;
                        const wallsN = Array.isArray(ra.walls) ? ra.walls.length : 0;
                        const dormersN = Array.isArray(ra.dormers) ? ra.dormers.length : 0;
                        const empty = !failed && wallsN === 0 && dormersN === 0;
                        if (failed || empty) {
                          return (
                            <div
                              className="p-4 border border-dashed border-[var(--danger)] bg-[#FEE2E2] text-[#7F1D1D] text-[11px]"
                              data-testid="ai-measure-3d-empty-state"
                            >
                              <div className="font-bold uppercase tracking-wider text-[10px] mb-2 flex items-center gap-1.5">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                Measurement incomplete — reconciliation failed
                              </div>
                              <div className="mb-3 whitespace-pre-wrap break-words">
                                {failed
                                  ? String(ra._reconciliation_error)
                                  : "Phase B produced no walls or dormers — nothing to render in 3D. Retry reconciliation on the saved Phase A extractions before applying."}
                              </div>
                              {currentRunId && (
                                <button
                                  type="button"
                                  onClick={() => retryReconcileOnly(currentRunId)}
                                  disabled={busy}
                                  className="px-3 py-1.5 bg-[#7F1D1D] text-white hover:bg-[#991B1B] text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                                  data-testid="ai-measure-3d-retry-reconciliation"
                                  title="Retry ONLY Phase B (reconciliation). Keeps Phase A's vision output."
                                >
                                  <RotateCcw className="w-3 h-3" /> Retry Reconciliation
                                </button>
                              )}
                            </div>
                          );
                        }
                        return <HouseModel3D preview={preview} estimate={estimate} runId={currentRunId} />;
                      })()}
                    </div>
                  )}

                  {previewTab === "preview" && (
                  <>
                  {/* Iter 78z (P1.3 + Cross-Check) — Per-Elevation Breakdown,
                      "+ Add Accent", and "🔁 Re-check with AI" button */}
                  <PerElevationBreakdownCard
                    measurements={preview.measurements || {}}
                    runId={currentRunId}
                    onUpdate={({ measurements: newMeas, lines: newLines }) => {
                      setPreview((p) => p && ({
                        ...p,
                        measurements: newMeas,
                        ...(newLines ? { lines: newLines } : {}),
                      }));
                    }}
                  />
                  {/* Iter 79j.12 — Elevation Drawings block removed per
                      Howard's feedback (2026-02-28): the auto-generated 2D
                      diagrams often didn't match the actual house
                      structure closely enough and hinted at inaccuracy
                      to the contractor. Wall breakdown table below still
                      shows the same underlying data. */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                    {Object.entries(preview.measurements)
                      .filter(([k, v]) => !k.startsWith("_") && v !== 0 && v !== null && v !== undefined)
                      .map(([k, v]) => (
                        <div key={k} data-testid={`ai-measure-stat-${k}`}>
                          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{KEY_LABELS[k] || k}</div>
                          <div className="font-mono-num text-sm font-bold text-[var(--ink)]">
                            {fmt(v)} {unitOf(k)}
                          </div>
                        </div>
                      ))}
                  </div>
                  {preview.raw_ai?.walls?.length > 0 && (
                    <details className="text-xs mb-3" open>
                      <summary className="cursor-pointer text-[var(--ai)] font-bold uppercase tracking-wider">
                        Wall breakdown ({preview.raw_ai.walls.length}) — tap to edit
                      </summary>
                      <div className="text-[11px] text-[var(--muted)] mt-2 italic">
                        If the AI got the geometry wrong (e.g. called a 1-story dormer a 2-story wall),
                        edit the numbers below. Siding ft² updates live. Apply re-runs the line math.
                      </div>
                      <table className="w-full mt-2 text-xs" data-testid="ai-measure-wall-table">
                        <thead className="text-left text-[var(--muted)] uppercase tracking-wider text-[10px]">
                          <tr>
                            <th>Wall</th>
                            <th>W (ft)</th>
                            <th>H eave (ft)</th>
                            <th>Gable h (ft)</th>
                            <th>Dormer (ft²)</th>
                            <th>Gable ft²</th>
                            <th>Total ft²</th>
                            <th title="Claude's per-wall confidence — green = high, amber = medium, red = low. Verify low/medium walls in the field.">Conf</th>
                          </tr>
                        </thead>
                        <tbody>
                          {preview.raw_ai.walls.map((w, i) => {
                            const width = Number(w.width_ft) || 0;
                            const eave = Number(w.height_ft) || 0;
                            const gable = Number(w.gable_triangle_height_ft) || 0;
                            const dormer = Number(w.dormer_face_sqft) || 0;
                            const gableArea = 0.5 * width * gable;
                            const area = width * eave + gableArea + dormer;
                            const confScore = Math.round(Number(w.confidence) || 0);
                            const confTier = confScore >= 80 ? "high" : confScore >= 60 ? "med" : confScore >= 30 ? "low" : "guess";
                            const confChip = {
                              high:  { bg: "bg-[var(--success)]", label: "HIGH" },
                              med:   { bg: "bg-[#CA8A04]", label: "MED" },
                              low:   { bg: "bg-[var(--brand-hover)]", label: "LOW" },
                              guess: { bg: "bg-[#DC2626]", label: "GUESS" },
                            }[confTier];
                            return (
                              <tr key={i} className="border-b border-[var(--bg-app)]">
                                <td className="py-1 font-bold text-[var(--ink-2)] uppercase tracking-wider text-[10px]">{w.label}</td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.5"
                                    className="w-16 px-1 py-0.5 border border-[var(--border)] font-mono-num text-xs"
                                    value={width}
                                    onChange={(e) => setWall(i, "width_ft", e.target.value)}
                                    data-testid={`ai-measure-wall-w-${i}`}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.5"
                                    className="w-16 px-1 py-0.5 border border-[var(--border)] font-mono-num text-xs"
                                    value={eave}
                                    onChange={(e) => setWall(i, "height_ft", e.target.value)}
                                    data-testid={`ai-measure-wall-h-${i}`}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.5"
                                    min="0"
                                    className="w-16 px-1 py-0.5 border border-[var(--border)] font-mono-num text-xs"
                                    value={gable}
                                    onChange={(e) => setWall(i, "gable_triangle_height_ft", e.target.value)}
                                    data-testid={`ai-measure-wall-gable-${i}`}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="1"
                                    min="0"
                                    className="w-16 px-1 py-0.5 border border-[var(--border)] font-mono-num text-xs"
                                    value={dormer}
                                    onChange={(e) => setWall(i, "dormer_face_sqft", e.target.value)}
                                    data-testid={`ai-measure-wall-dormer-${i}`}
                                  />
                                  {/* Iter 79j.66 — the ft² alone forces the
                                      contractor to know the face-area formula.
                                      Expose the matched dormer's W × knee (the
                                      same fields the 3D sidebar shows); edits
                                      rescale the ft² automatically. */}
                                  {(preview.raw_ai.dormers || [])
                                    .map((d, j) => ({ d, j }))
                                    .filter(({ d }) => (d.face || "").toLowerCase() === (w.label || "").toLowerCase())
                                    .map(({ d, j }) => (
                                      <div
                                        key={j}
                                        className="flex items-center gap-0.5 mt-0.5 text-[9px] text-[var(--muted)]"
                                        title="Dormer width × knee-wall height (ft) — same fields as the 3D sidebar. Editing rescales the face ft² using the AI's geometry factor, and the 3D model follows."
                                        data-testid={`ai-measure-wall-dormer-dims-${i}-${j}`}
                                      >
                                        <input
                                          type="number"
                                          step="0.5"
                                          min="0"
                                          className="w-11 px-1 py-0.5 border border-[var(--border)] font-mono-num text-[10px]"
                                          value={Number(d.width_ft) || 0}
                                          onChange={(e) => setDormerDims(j, i, "width_ft", e.target.value)}
                                          data-testid={`ai-measure-wall-dormer-w-${i}-${j}`}
                                        />
                                        <span>×</span>
                                        <input
                                          type="number"
                                          step="0.25"
                                          min="0"
                                          className="w-11 px-1 py-0.5 border border-[var(--border)] font-mono-num text-[10px]"
                                          value={Number(d.knee_wall_height_ft) || 0}
                                          onChange={(e) => setDormerDims(j, i, "knee_wall_height_ft", e.target.value)}
                                          data-testid={`ai-measure-wall-dormer-knee-${i}-${j}`}
                                        />
                                        <span className="uppercase tracking-wider">w×knee</span>
                                      </div>
                                    ))}
                                </td>
                                <td className="font-mono-num font-bold text-[var(--ai)]" data-testid={`ai-measure-wall-gable-ft2-${i}`}>
                                  {gableArea > 0 ? gableArea.toFixed(0) : "—"}
                                </td>
                                <td className="font-mono-num font-bold">{area.toFixed(0)}</td>
                                <td
                                  className="text-center"
                                  title={(w.confidence_reasoning || "") + (confScore ? ` · score ${confScore}/100` : "")}
                                  data-testid={`ai-measure-wall-conf-${i}`}
                                >
                                  {confScore > 0 ? (
                                    <span className={`inline-block ${confChip.bg} text-white text-[9px] font-bold px-1.5 py-0.5 rounded-sm tracking-wider`}>
                                      {confChip.label} {confScore}
                                    </span>
                                  ) : (
                                    <span className="text-[var(--muted)]">—</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                          {/* Totals row — emphasizes the gable ft² so the
                              contractor can spec shake siding for those
                              areas if the homeowner wants it. */}
                          {(() => {
                            const totalGable = preview.raw_ai.walls.reduce((a, w) => {
                              const ww = Number(w.width_ft) || 0;
                              const gh = Number(w.gable_triangle_height_ft) || 0;
                              return a + 0.5 * ww * gh;
                            }, 0);
                            const totalArea = preview.raw_ai.walls.reduce((a, w) => {
                              const ww = Number(w.width_ft) || 0;
                              const eh = Number(w.height_ft) || 0;
                              const gh = Number(w.gable_triangle_height_ft) || 0;
                              const dr = Number(w.dormer_face_sqft) || 0;
                              return a + ww * eh + 0.5 * ww * gh + dr;
                            }, 0);
                            return (
                              <tr className="border-t-2 border-[var(--border-strong)]" data-testid="ai-measure-wall-totals">
                                <td colSpan={5} className="py-1 text-[10px] uppercase tracking-wider font-bold text-[var(--ink-2)] text-right">
                                  Totals
                                </td>
                                <td className="font-mono-num font-bold text-[var(--ai)]" data-testid="ai-measure-total-gable-ft2">
                                  {totalGable > 0 ? totalGable.toFixed(0) : "—"}
                                </td>
                                <td className="font-mono-num font-bold">{totalArea.toFixed(0)}</td>
                                <td>&nbsp;</td>
                              </tr>
                            );
                          })()}
                        </tbody>
                      </table>
                      {preview.raw_ai.walls.some((w) => Number(w.gable_triangle_height_ft) > 0) && (
                        <>
                          <div className="text-[11px] text-[var(--ai)] mt-2 inline-flex items-start gap-1" data-testid="ai-measure-gable-shake-hint">
                            <Lightbulb aria-hidden="true" className="w-3 h-3 mt-0.5 flex-shrink-0" />
                            <span>Gable ft² is broken out so you can quote shake / scallop siding for those triangles if the homeowner wants a different look up top.</span>
                          </div>
                          <label className="mt-2 flex items-center gap-2 cursor-pointer p-2 border border-[var(--border)] hover:border-[var(--ai)] transition-colors">
                            <input
                              type="checkbox"
                              checked={quoteGablesAsShake}
                              onChange={(e) => setQuoteGablesAsShake(e.target.checked)}
                              data-testid="ai-measure-quote-gables-shake"
                            />
                            <span className="text-xs font-bold uppercase tracking-wider text-[var(--ink-2)]">
                              Quote gables as shake
                            </span>
                            {quoteGablesAsShake && (
                              <select
                                value={shakeSku}
                                onChange={(e) => setShakeSku(e.target.value)}
                                className="ml-2 px-1 py-0.5 border border-[var(--border)] text-xs"
                                data-testid="ai-measure-shake-sku"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <option value={'Pelican Bay Shakes 9"'}>Pelican Bay Shakes 9&quot; (vinyl)</option>
                                <option value={'LP Strand Shake 3/8" x 12" x 4\''}>LP Strand Shake 3/8&quot; × 12&quot; × 4&apos;</option>
                              </select>
                            )}
                          </label>
                          {quoteGablesAsShake && (
                            <div className="text-[10px] text-[var(--ink-2)] mt-1 ml-7" data-testid="ai-measure-shake-preview">
                              On Apply: <span className="font-bold">{shakeSku}</span> qty = {shakeSku.startsWith("LP") ? Math.ceil((preview?.measurements?._ai_gable_sqft || 0) / 4) + " PCS" : Math.ceil((preview?.measurements?._ai_gable_sqft || 0) / 100) + " SQ"} · main siding reduced by {Math.ceil((preview?.measurements?._ai_gable_sqft || 0) / 100)} SQ
                            </div>
                          )}
                        </>
                      )}
                      {wallsDirty && (
                        <div className="text-[10px] text-[var(--brand-text)] uppercase tracking-wider font-bold mt-2" data-testid="ai-measure-walls-dirty">
                          ✎ Edited — line items will refresh on Apply
                        </div>
                      )}
                      {preview.raw_ai.walls.some((w) => Number(w.dormer_face_sqft) > 0) && (
                        <>
                          <label className="mt-2 flex items-center gap-2 cursor-pointer p-2 border border-[var(--border)] hover:border-[var(--ai)] transition-colors">
                            <input
                              type="checkbox"
                              checked={quoteDormersAsShake}
                              onChange={(e) => setQuoteDormersAsShake(e.target.checked)}
                              data-testid="ai-measure-quote-dormers-shake"
                            />
                            <span className="text-xs font-bold uppercase tracking-wider text-[var(--ink-2)]">
                              Quote dormers as shake
                            </span>
                            {quoteDormersAsShake && (
                              <select
                                value={dormerShakeSku}
                                onChange={(e) => setDormerShakeSku(e.target.value)}
                                className="ml-2 px-1 py-0.5 border border-[var(--border)] text-xs"
                                data-testid="ai-measure-dormer-shake-sku"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <option value={'Pelican Bay Shakes 9"'}>Pelican Bay Shakes 9&quot; (vinyl)</option>
                                <option value={'LP Strand Shake 3/8" x 12" x 4\''}>LP Strand Shake 3/8&quot; × 12&quot; × 4&apos;</option>
                              </select>
                            )}
                          </label>
                          {quoteDormersAsShake && (
                            <div className="text-[10px] text-[var(--ink-2)] mt-1 ml-7" data-testid="ai-measure-dormer-shake-preview">
                              On Apply: <span className="font-bold">{dormerShakeSku}</span> qty = {dormerShakeSku.startsWith("LP") ? Math.ceil((preview?.measurements?._ai_dormer_sqft || 0) / 4) + " PCS" : Math.ceil((preview?.measurements?._ai_dormer_sqft || 0) / 100) + " SQ"} · main siding reduced by {Math.ceil((preview?.measurements?._ai_dormer_sqft || 0) / 100)} SQ
                            </div>
                          )}
                        </>
                      )}
                    </details>
                  )}

                  {/* Iter 57: HOVER-style extras.
                      • Missing-elevations banner — warn if Claude didn't see all 4 walls
                      • Openings schedule — collapsed grouped view (elevation × type × size)
                      • Double-count check — Claude's reconciliation note */}
                  {(preview.measurements?._ai_missing_elevations?.length ?? 0) > 0 && (
                    <div
                      className="border border-[#F59E0B] bg-[#FEF3C7] px-3 py-2 mb-3 text-xs text-[#78350F] flex items-start gap-2"
                      data-testid="ai-measure-missing-elevs"
                    >
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <div>
                        Claude couldn&apos;t see these elevations —
                        add photos to capture them: {" "}
                        <strong>
                          {preview.measurements._ai_missing_elevations
                            .map((e) => e.toUpperCase())
                            .join(", ")}
                        </strong>
                        .
                      </div>
                    </div>
                  )}

                  {/* Iter 57o — Labeled photos preview. Surfaces the
                      bbox callouts (yellow boxes + labels) on each photo
                      so the contractor can spot-check Claude's
                      per-opening placements BEFORE generating the PDF. */}
                  {(() => {
                    const schedule = preview.measurements?._ai_openings_schedule
                      || preview.raw_ai?.openings_schedule || [];
                    const totalLocs = schedule.reduce(
                      (n, r) => n + (Array.isArray(r.locations) ? r.locations.length : 0), 0
                    );
                    if (totalLocs === 0 || photoUrls.length === 0) return null;
                    return (
                      <details className="text-xs mb-3" open data-testid="ai-measure-labeled-photos">
                        <summary className="cursor-pointer text-[var(--ai)] font-bold uppercase tracking-wider">
                          Labeled photos — {totalLocs} opening{totalLocs === 1 ? "" : "s"} tagged by Claude
                        </summary>
                        <div className="text-[11px] text-[var(--muted)] mt-2 italic">
                          Same yellow boxes + labels appear on the photos in the downloaded measurement PDF. If one looks wrong, edit the opening size/style in the Openings schedule below — the label updates automatically.
                        </div>
                        <div className="mt-2 grid grid-cols-2 gap-2">
                          {photoUrls.map((name, i) => {
                            // Build the callouts for THIS photo, same
                            // logic as the upload-grid overlay above.
                            const photoCallouts = [];
                            const seenKeys = new Set();
                            for (const row of schedule) {
                              for (const loc of (row.locations || [])) {
                                if (Number(loc.photo_idx) !== i) continue;
                                const bb = loc.bbox || {};
                                const bx = Number(bb.x), by = Number(bb.y);
                                const bw = Number(bb.w || 0), bh = Number(bb.h || 0);
                                if (!(bx >= 0 && bx <= 1 && by >= 0 && by <= 1 && bw > 0 && bh > 0 && bx + bw <= 1.001 && by + bh <= 1.001)) continue;
                                const key = `${bx.toFixed(3)},${by.toFixed(3)},${bw.toFixed(3)},${bh.toFixed(3)}`;
                                if (seenKeys.has(key)) continue;
                                seenKeys.add(key);
                                const wi = Math.round(Number(row.width_in) || 0);
                                const hi = Math.round(Number(row.height_in) || 0);
                                const t = String(row.type || "window").toLowerCase();
                                const style = String(row.style || "");
                                let label = `${wi}×${hi}`;
                                if (t === "garage_door") label = `${wi}×${hi} Garage`;
                                else if (t === "entry_door") label = `${wi}×${hi} Entry`;
                                else if (t === "patio_door") label = `${wi}×${hi} Patio`;
                                else {
                                  let short = "";
                                  if (/Double Hung|Twin Double/i.test(style)) short = "DH";
                                  else if (/Single Hung/i.test(style)) short = "SH";
                                  else if (/Casement/i.test(style)) short = "CS";
                                  else if (/Slider/i.test(style)) short = "SL";
                                  else if (/Picture/i.test(style)) short = "PIC";
                                  else if (/Awning/i.test(style)) short = "AW";
                                  else if (/Hopper/i.test(style)) short = "HP";
                                  if (short) label = `${short} ${label}`;
                                }
                                const labelY = by > 0.07 ? by - 0.025 : by + 0.005;
                                const lcx = bx + bw / 2;
                                const lblFs = 3.0;
                                const bgW = Math.min(0.98 - lcx + 0.5, Math.max(0.10, label.length * lblFs * 0.0048));
                                const bgX = Math.max(0.005, Math.min(1 - bgW - 0.005, lcx - bgW / 2));
                                photoCallouts.push(
                                  <g key={key}>
                                    <rect x={bx * 100} y={by * 100} width={bw * 100} height={bh * 100}
                                          fill="none" stroke="#FACC15" strokeWidth={0.6} />
                                    <rect x={bgX * 100} y={labelY * 100} width={bgW * 100} height={lblFs + 0.6}
                                          fill="#09090B" />
                                    <text x={(bgX + bgW / 2) * 100} y={labelY * 100 + lblFs * 0.85}
                                          textAnchor="middle" fontSize={lblFs} fontWeight={700} fill="#FACC15">
                                      {label}
                                    </text>
                                  </g>
                                );
                              }
                            }
                            const meta = (preview.measurements?._ai_photos || preview.raw_ai?.photos || [])
                              .find((p) => Number(p.index) === i) || {};
                            const elev = (meta.elevation || "").toUpperCase();
                            return (
                              <div key={name} className="relative border border-[var(--border)] bg-[var(--surface-muted)]" data-testid={`ai-measure-labeled-photo-${i}`}>
                                <div className="relative aspect-video overflow-hidden">
                                  <img
                                    src={`/api/uploads/${name}`}
                                    alt={`Labeled photo ${i + 1}`}
                                    className="w-full h-full object-cover"
                                  />
                                  {photoCallouts.length > 0 && (
                                    <svg
                                      viewBox="0 0 100 100"
                                      preserveAspectRatio="none"
                                      className="absolute inset-0 w-full h-full pointer-events-none"
                                    >
                                      {photoCallouts}
                                    </svg>
                                  )}
                                  {elev && (
                                    <span className="absolute top-1 left-1 bg-[var(--ai)] text-white text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold">
                                      {elev}
                                    </span>
                                  )}
                                  <span className="absolute bottom-1 right-1 bg-[#FACC15] text-[var(--ink)] text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold" data-testid={`ai-measure-labeled-photo-count-${i}`}>
                                    {photoCallouts.length} tag{photoCallouts.length === 1 ? "" : "s"}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </details>
                    );
                  })()}

                  {(preview.measurements?._ai_openings_schedule?.length ?? 0) > 0 && (
                    <details className="text-xs mb-3" open data-testid="ai-measure-openings-schedule">
                      <summary className="cursor-pointer text-[var(--ai)] font-bold uppercase tracking-wider">
                        Openings schedule — grouped by elevation × size
                      </summary>
                      <div className="text-[11px] text-[var(--muted)] mt-2 italic">
                        Each elevation is grouped together with a colored chip and total count so it&apos;s easy to verify against the house. Sizes are listed underneath.
                      </div>
                      {/* Iter 57c — Option B: rows grouped by elevation
                          with a colored chip + total opening count per
                          group. Kills the visual confusion of seeing
                          "LEFT, LEFT, LEFT" repeated. */}
                      {(() => {
                        const ELEVATION_COLORS = {
                          front:  { bg: "bg-[#3B82F6]", soft: "bg-[#EFF6FF]", text: "text-[#1E40AF]" },
                          back:   { bg: "bg-[var(--success)]", soft: "bg-[#F0FDF4]", text: "text-[#166534]" },
                          left:   { bg: "bg-[var(--brand-hover)]", soft: "bg-[#FFF7ED]", text: "text-[#9A3412]" },
                          right:  { bg: "bg-[var(--ai)]", soft: "bg-[#FAF5FF]", text: "text-[#5B21B6]" },
                          other:  { bg: "bg-[var(--ink-2)]", soft: "bg-[var(--surface-muted)]", text: "text-[#27272A]" },
                        };
                        const schedule = preview.measurements._ai_openings_schedule || [];
                        // Group by elevation in a fixed display order.
                        const order = ["front", "back", "left", "right", "other"];
                        const groups = {};
                        schedule.forEach((o) => {
                          const elev = (o.elevation || "other").toLowerCase();
                          const k = order.includes(elev) ? elev : "other";
                          if (!groups[k]) groups[k] = [];
                          groups[k].push(o);
                        });
                        const orderedGroups = order
                          .filter((k) => groups[k]?.length)
                          .map((k) => [k, groups[k]]);

                        return (
                          <div className="mt-2" data-testid="ai-measure-openings-grouped">
                            {/* Tiny house diagram so the colors map to spatial position */}
                            <div className="flex items-center justify-center gap-3 py-2 mb-2 border-y border-[var(--border)]" data-testid="ai-measure-elevation-legend">
                              <svg width="56" height="56" viewBox="0 0 56 56" className="flex-shrink-0">
                                <rect x="14" y="14" width="28" height="28" fill="#FAFAFA" stroke="#A1A1AA" strokeWidth="1" />
                                <rect x="14" y="11" width="28" height="3" fill="#3B82F6" />
                                <rect x="14" y="42" width="28" height="3" fill="#16A34A" />
                                <rect x="11" y="14" width="3" height="28" fill="#EA580C" />
                                <rect x="42" y="14" width="3" height="28" fill="#7C3AED" />
                                <text x="28" y="9" fontSize="6" fill="#3B82F6" textAnchor="middle" fontWeight="700">FRONT</text>
                                <text x="28" y="52" fontSize="6" fill="#16A34A" textAnchor="middle" fontWeight="700">BACK</text>
                                <text x="8" y="30" fontSize="5" fill="#EA580C" textAnchor="middle" fontWeight="700" transform="rotate(-90 8 30)">LEFT</text>
                                <text x="48" y="30" fontSize="5" fill="#7C3AED" textAnchor="middle" fontWeight="700" transform="rotate(90 48 30)">RIGHT</text>
                              </svg>
                              <div className="text-[10px] text-[var(--muted)] uppercase tracking-wider">
                                Color = which side of the house
                              </div>
                            </div>
                            {orderedGroups.map(([elev, items]) => {
                              const color = ELEVATION_COLORS[elev] || ELEVATION_COLORS.other;
                              const totalCount = items.reduce((sum, o) => sum + (Number(o.count) || 0), 0);
                              return (
                                <div
                                  key={elev}
                                  className="mb-2"
                                  data-testid={`ai-measure-opening-group-${elev}`}
                                >
                                  <div className={`${color.soft} flex items-center gap-2 px-2 py-1.5 border-l-4 ${color.bg.replace("bg-", "border-")}`}>
                                    <span className={`${color.bg} text-white text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider`}>
                                      {elev}
                                    </span>
                                    <span className={`text-[11px] font-bold ${color.text}`}>
                                      {totalCount} opening{totalCount !== 1 ? "s" : ""}
                                    </span>
                                    <span className="text-[10px] text-[var(--muted)] ml-2 italic">
                                      {items.map((o) => {
                                        const sz = o.size_label || `${Math.round(Number(o.width_in) || 0)}×${Math.round(Number(o.height_in) || 0)} in`;
                                        const st = (o.style || "").trim();
                                        return st ? `${st} ${sz}×${o.count}` : `${sz}×${o.count}`;
                                      }).join(" · ")}
                                    </span>
                                  </div>
                                  <table className="w-full text-xs border-b border-[var(--border)]">
                                    <tbody>
                                      {items.map((o, i) => {
                                        const isWindow = (o.type || "").toLowerCase() === "window";
                                        const styleVal = o.style || "";
                                        const styleConf = Number(o.style_confidence) || 0;
                                        const confChip = styleConf >= 80 ? "bg-[var(--success)]" : styleConf >= 60 ? "bg-[#CA8A04]" : styleConf >= 30 ? "bg-[var(--brand-hover)]" : "bg-[#DC2626]";
                                        const sizeLabel = o.size_label || `${Math.round(Number(o.width_in) || 0)}×${Math.round(Number(o.height_in) || 0)} in`;
                                        return (
                                          <tr key={i} className="hover:bg-[var(--surface-muted)]" data-testid={`ai-measure-opening-row-${elev}-${i}`}>
                                            <td className="py-1 pl-4 capitalize text-[var(--ink-2)]" style={{ width: "22%" }}>
                                              {(o.type || "—").replace(/_/g, " ")}
                                            </td>
                                            <td className="font-mono-num text-[#27272A]" style={{ width: "20%" }}>
                                              {sizeLabel}
                                            </td>
                                            <td className="py-1" style={{ width: "45%" }}>
                                              {isWindow ? (
                                                <div className="flex items-center gap-1">
                                                  <select
                                                    value={styleVal}
                                                    onChange={(e) => updateOpeningStyle(elev, o.type, o.size_label, o.width_in, o.height_in, e.target.value)}
                                                    className="text-xs border border-[var(--border)] px-1 py-0.5 bg-[var(--surface)] hover:border-[var(--ai)] cursor-pointer w-full max-w-[180px]"
                                                    data-testid={`ai-measure-opening-style-${elev}-${i}`}
                                                    title={styleVal ? `Claude's guess: ${styleVal} (${styleConf}% confident). Change if wrong — this flows to the customer PDF and the Vero quote.` : "Pick a window style — flows to the customer PDF and the Vero quote"}
                                                  >
                                                    {WINDOW_STYLES.map((s) => (
                                                      <option key={s.value} value={s.value}>{s.label}</option>
                                                    ))}
                                                  </select>
                                                  {styleVal && styleConf > 0 && (
                                                    <span
                                                      className={`${confChip} text-white text-[8px] font-bold px-1 rounded-sm tracking-wider`}
                                                      title={`Claude is ${styleConf}% confident on this style`}
                                                    >
                                                      {styleConf}
                                                    </span>
                                                  )}
                                                </div>
                                              ) : (
                                                <span className="text-[var(--muted)] italic text-[11px]">—</span>
                                              )}
                                            </td>
                                            <td className="font-mono-num font-bold text-right pr-2" style={{ width: "13%" }}>
                                              ×{Number(o.count) || 0}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })()}
                    </details>
                  )}

                  {preview.measurements?._ai_double_count_check && (
                    <div
                      className="text-[11px] text-[var(--ink-2)] italic border-l-2 border-[#0EA5E9] pl-3 mb-3"
                      data-testid="ai-measure-double-count"
                    >
                      <span className="not-italic font-bold text-[#0EA5E9] mr-1">Cross-check:</span>
                      {preview.measurements._ai_double_count_check}
                    </div>
                  )}
                  {preview.measurements && (
                    <details className="text-xs mb-3" open data-testid="ai-measure-lf-table">
                      <summary className="cursor-pointer text-[var(--ai)] font-bold uppercase tracking-wider">
                        Linear measurements — tap to edit
                      </summary>
                      <div className="text-[11px] text-[var(--muted)] mt-2 italic">
                        If the AI under-counted (often because not every elevation was photographed),
                        type the real numbers. ISS soffit / gutter / capping qty re-derives from these on Apply.
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2">
                        {[
                          ["eaves_lf", "Eaves LF"],
                          ["rakes_lf", "Rakes LF"],
                          ["starter_lf", "Starter LF"],
                          ["outside_corner_lf", "Outside corner LF"],
                          ["inside_corner_lf", "Inside corner LF"],
                          ["opening_perimeter_lf", "Opening perimeter LF"],
                          ["window_count", "Window count"],
                          ["entry_door_count", "Entry door count"],
                          ["patio_door_count", "Patio door count"],
                          ["garage_door_count", "Garage door count"],
                        ].map(([key, label]) => (
                          <label key={key} className="flex flex-col text-[10px] text-[var(--muted)] uppercase tracking-wider">
                            <span className="mb-1">{label}</span>
                            <input
                              type="number"
                              step={key.endsWith("_count") ? "1" : "0.5"}
                              min="0"
                              value={Number(preview.measurements[key] || 0)}
                              onChange={(e) => setMeasurementField(key, e.target.value)}
                              className="px-2 py-1 border border-[var(--border)] font-mono-num text-sm text-[var(--ink)] normal-case"
                              data-testid={`ai-measure-lf-${key}`}
                            />
                          </label>
                        ))}
                      </div>
                    </details>
                  )}

                  {/* Iter 56: Raw AI JSON for debugging — collapsed by
                      default. Useful when the numbers look wrong and we
                      need to see exactly what Claude returned. */}
                  {(preview.raw_ai || preview.measurements) && (
                    <details className="text-xs mb-3" data-testid="ai-measure-raw-debug">
                      <summary className="cursor-pointer text-[var(--muted)] font-bold uppercase tracking-wider text-[10px] inline-flex items-center gap-1">
                        <ScanSearch aria-hidden="true" className="w-3 h-3" /> Show raw AI output (debug)
                      </summary>
                      <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                        <div>
                          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-1">
                            raw_ai (what Claude returned)
                          </div>
                          <pre className="bg-[var(--bar-bg)] text-[#22D3EE] p-2 text-[10px] overflow-auto max-h-64 whitespace-pre-wrap break-all" data-testid="ai-measure-raw-ai-json">
{JSON.stringify(preview.raw_ai || {}, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-1">
                            measurements (post-aggregator)
                          </div>
                          <pre className="bg-[var(--bar-bg)] text-[#A78BFA] p-2 text-[10px] overflow-auto max-h-64 whitespace-pre-wrap break-all" data-testid="ai-measure-measurements-json">
{JSON.stringify(preview.measurements || {}, null, 2)}
                          </pre>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            JSON.stringify(
                              { raw_ai: preview.raw_ai, measurements: preview.measurements },
                              null,
                              2,
                            ),
                          );
                          toast.success("Raw AI output copied to clipboard");
                        }}
                        className="mt-2 px-2 py-1 text-[10px] font-bold uppercase tracking-wider bg-[var(--surface)] border border-[var(--border)] hover:bg-[var(--surface-muted)]"
                        data-testid="ai-measure-copy-raw"
                      >
                        Copy to clipboard
                      </button>
                    </details>
                  )}


                  </>
                  )}
                </>
              )}
            </div>

            <div className="border-t border-[var(--border)] px-5 py-4 flex flex-col md:flex-row md:justify-between md:items-center gap-3 relative">
              {/* Iter 57h — inline calibration popover. Hidden by default;
                  pops up just above the Run button when the contractor
                  hits the "Calibrate window sizing" link. Stays out of
                  the way for the 80% of jobs that don't need it. */}
              {calibOpen && (
                <div
                  className="absolute bottom-full right-5 mb-2 bg-[var(--surface)] border border-[var(--ai)] shadow-xl p-3 min-w-[280px] z-10"
                  data-testid="ai-measure-course-sizing"
                  onMouseLeave={() => { /* keep open on hover-leave — user explicitly closes */ }}
                >
                  <div className="flex items-start justify-between mb-2 gap-2">
                    <div className="text-[10px] uppercase tracking-wider text-[var(--ai)] font-bold leading-tight">
                      Calibrate window sizing
                      <div className="text-[9px] text-[var(--muted)] font-normal mt-0.5">
                        Tell Claude the brick course or siding row height. Optional — leave blank for defaults.
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setCalibOpen(false)}
                      className="text-[var(--muted)] hover:text-[var(--ink)]"
                      title="Close"
                      data-testid="ai-measure-course-sizing-close"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <label className="block">
                      <span className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold">Brick course (in)</span>
                      <input
                        type="number"
                        step="0.25"
                        min="0"
                        className="input text-sm"
                        placeholder="8 = standard"
                        value={brickCourse}
                        onChange={(e) => setBrickCourse(e.target.value)}
                        data-testid="ai-measure-brick-course"
                      />
                    </label>
                    <label className="block">
                      <span className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold">Siding exposure (in)</span>
                      <input
                        type="number"
                        step="0.25"
                        min="0"
                        className="input text-sm"
                        placeholder="D5=5, D6=6, CI=7"
                        value={sidingExposure}
                        onChange={(e) => setSidingExposure(e.target.value)}
                        data-testid="ai-measure-siding-exposure"
                      />
                    </label>
                  </div>
                  <div className="text-[9px] text-[var(--muted)] mt-2 italic">
                    Backend snaps every window to nearest standard size after Claude runs, regardless.
                  </div>
                  {/* Iter 79j.44 — Deep Dormer Scan removed. Two-phase
                      Phase A/B now owns dormer detection end-to-end
                      via the `dormers[]` array with per-face provenance.
                      The legacy roofline-crop scan was injecting corrupt
                      data (null opening_ids, wrong-wall face SF crediting,
                      hits on nonexistent walls). UI + request flag gone. */}
                </div>
              )}
              <div className="text-[10px] text-[var(--muted)] flex flex-wrap items-center gap-x-3 gap-y-1 shrink-0">
                <span className="whitespace-nowrap">Powered by</span>
                {/* Iter 79j.15 — A/B model picker. Compact select so
                    contractors can flip models per-run without leaving
                    the modal. Persisted in localStorage. */}
                <select
                  value={modelChoice}
                  onChange={(e) => setModelChoice(e.target.value)}
                  className="text-[10px] font-bold uppercase tracking-wider bg-[var(--surface)] border border-[var(--border)] px-1 py-0.5 focus:outline-none focus:border-[var(--ai)]"
                  data-testid="ai-measure-model-select"
                  title="Which vision model runs the measurement pass. Opus 4.5 is the current default; try Gemini 3.5 Flash or GPT-5.5 to A/B accuracy vs cost."
                >
                  <option value="claude-opus-4-5">Claude Opus 4.5</option>
                  <option value="claude-opus-4-8">Claude Opus 4.8</option>
                  <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
                  <option value="claude-fable-5">Claude Fable 5</option>
                  <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                  <option value="gemini-3.1-pro">Gemini 3.1 Pro</option>
                  <option value="gpt-5.5">GPT-5.5</option>
                  <option value="gpt-5.4">GPT-5.4</option>
                </select>
                <button
                  type="button"
                  onClick={() => setCalibOpen((v) => !v)}
                  className={`text-[10px] uppercase tracking-wider font-bold flex items-center gap-1 whitespace-nowrap ${
                    (brickCourse || sidingExposure) ? "text-[var(--ai)]" : "text-[var(--muted)] hover:text-[var(--ai)]"
                  }`}
                  data-testid="ai-measure-course-sizing-toggle"
                  title="Tell Claude the brick course or siding row height (optional)"
                >
                  <Ruler className="w-3 h-3" />
                  {(brickCourse || sidingExposure) ? "Calibration on" : "Calibrate window sizing"}
                </button>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2 min-w-0 [&_button]:whitespace-nowrap">
                <button
                  type="button"
                  className="px-3 py-2 bg-[var(--surface)] text-[var(--ink-2)] border border-[var(--border)] hover:bg-[var(--bg-app)] text-xs font-bold uppercase tracking-wider"
                  onClick={closeAll}
                  disabled={busy}
                  data-testid="ai-measure-cancel"
                >
                  Close
                </button>
                {(preview || photoUrls.length > 0 || files.length > 0) && (
                  <button
                    type="button"
                    className="px-3 py-2 bg-[var(--surface)] text-[var(--danger-text)] border border-[#DC2626] hover:bg-red-50 text-xs font-bold uppercase tracking-wider"
                    onClick={() => setDestructiveConfirm({ kind: "start_over" })}
                    disabled={busy}
                    data-testid="ai-measure-start-over"
                    title="Wipe photos + AI result and start fresh"
                  >
                    Start Over
                  </button>
                )}
                {preview && estimateId && (
                  <button
                    type="button"
                    onClick={downloadReportPdf}
                    disabled={reportBusy || busy}
                    className="px-3 py-2 bg-[var(--surface)] text-[#0EA5E9] border border-[#0EA5E9] hover:bg-[#F0F9FF] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50"
                    data-testid="ai-measure-report-pdf-btn"
                    title="Download a branded HOVER-style measurement report (photos + confidence chips + openings schedule)"
                  >
                    {reportBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                    {reportBusy ? "Generating…" : "Report PDF"}
                  </button>
                )}
                {!preview ? (
                  <>
                    {photoUrls.length > 0 && estimateId && (
                      <button
                        type="button"
                        onClick={() => setProfileAnnotatorOpen(true)}
                        disabled={busy}
                        className="px-3 py-2 bg-[var(--surface)] text-[var(--brand-text)] border border-[var(--brand)] hover:bg-[#FFF7ED] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50 mr-1"
                        data-testid="ai-measure-tag-profiles-btn"
                        title="Draw boxes to tag Shake / B&B / etc. — guarantees those materials hit the quote"
                      >
                        Tag Profiles
                        {Object.entries(savedProfileAnnotations).filter(([k, v]) => !k.startsWith("_") && Array.isArray(v) && v.length > 0).length > 0 && (
                          <span className="bg-[var(--brand)] text-[var(--on-brand)] px-1 py-0 text-[9px]">
                            {Object.entries(savedProfileAnnotations).reduce((a, [k, v]) => a + (k.startsWith("_") ? 0 : (Array.isArray(v) ? v.length : 0)), 0)}
                          </span>
                        )}
                      </button>
                    )}
                    {(() => {
                      // Iter 79j.45 / 79j.46 — Health-aware Run button.
                      // Order of precedence: busy > uploading > health
                      // outage > normal. `ambiguous` NEVER disables the
                      // button — soft warning only, per rule (3): a
                      // broken health check must not lock the product.
                      //
                      // Iter 79j.46 — Red state is CLICKABLE. Clicking
                      // fires a forced health re-ping (bypasses the
                      // 45s client cache) so the user has a manual
                      // escape hatch: top up in a new tab → click the
                      // red button → tab focus event ALREADY fires a
                      // ping, but the manual click is the belt to
                      // that suspenders.
                      const budgetOut = aiHealth?.status === "budget_exceeded";
                      const svcOut = aiHealth?.status === "unavailable";
                      const isRed = budgetOut || svcOut;
                      let label;
                      if (busy) {
                        label = busyStage === "claude" ? "Claude vision…"
                          : busyStage === "dormer_scan" ? "Deep dormer scan…"
                          : busyStage === "aggregating" ? "Aggregating walls…"
                          : busyStage === "mapping" ? "Mapping to catalog…"
                          : busyStage === "starting" ? "Starting…"
                          : "Analyzing…";
                      } else if (files.length > 0) {
                        label = "Uploading…";
                      } else if (budgetOut) {
                        label = "Budget exhausted — click to re-check";
                      } else if (svcOut) {
                        label = "AI service unavailable — click to re-check";
                      } else {
                        label = "Run AI Measure";
                      }
                      const cls = isRed
                        ? "px-3 py-2 bg-[var(--danger)] text-white hover:bg-[#B91C1C] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 cursor-pointer disabled:opacity-70"
                        : "px-3 py-2 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50";
                      const onClickHandler = isRed
                        ? () => refreshAiHealth({ force: true })
                        : runMeasure;
                      return (
                        <button
                          type="button"
                          onClick={onClickHandler}
                          // Iter 79j.46 — Red state stays clickable for
                          // the re-check escape hatch. Only truly
                          // disabled during a live run / upload / with
                          // zero photos. `data-health-status` lets QA
                          // & automation drive the recovery path.
                          disabled={busy || photoUrls.length === 0 || files.length > 0}
                          className={cls}
                          data-testid="ai-measure-run-btn"
                          data-health-status={aiHealth?.status || "unknown"}
                          title={isRed ? "Click to re-check the AI service health" : undefined}
                        >
                          {busy
                            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            : isRed
                              ? <RotateCcw className="w-3.5 h-3.5" />
                              : <Upload className="w-3.5 h-3.5" />}
                          {label}
                        </button>
                      );
                    })()}
                  </>
                ) : (
                  <>
                    {/* Advanced tools toggle — gates Refine on Photo.
                        Pre-AI annotations (Iter 56) cover most use cases;
                        Refine is the manual-measure escape hatch. */}
                    <button
                      type="button"
                      onClick={() => setShowAdvanced((v) => !v)}
                      className={`px-2 py-2 text-[10px] font-bold uppercase tracking-wider border ${
                        showAdvanced
                          ? "bg-[var(--surface-muted)] text-[var(--ink-2)] border-[var(--muted)]"
                          : "bg-[var(--surface)] text-[var(--muted)] border-[var(--border)] hover:text-[var(--ink-2)]"
                      } mr-1`}
                      data-testid="ai-measure-advanced-toggle"
                      title="Show / hide the Refine on Photo manual-measure tool"
                    >
                      {showAdvanced ? "Hide" : "Advanced"}
                    </button>
                    {/* Iter 79j.16 — Re-run button so contractors can
                        A/B a different model on the SAME photos without
                        hitting Start Over. Uses the current model in
                        the "Powered by" dropdown. */}
                    <button
                      type="button"
                      onClick={attemptRerun}
                      disabled={busy || photoUrls.length === 0 || files.length > 0}
                      className="px-3 py-2 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50"
                      data-testid="ai-measure-rerun-btn"
                      title="Run the measure again — usually with a different model in the Powered by dropdown to A/B compare accuracy"
                    >
                      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                      {busy
                        ? (busyStage === "claude" ? "Vision…"
                          : busyStage === "dormer_scan" ? "Dormer scan…"
                          : busyStage === "aggregating" ? "Aggregating…"
                          : busyStage === "mapping" ? "Mapping…"
                          : busyStage === "starting" ? "Starting…"
                          : "Running…")
                        : "Re-run"}
                    </button>
                    {/* Merge-mode picker — controls how Refine on Photo
                        deltas roll into the AI's aggregate measurements.
                        Add accumulates LFs/counts across per-elevation
                        refines; Max keeps the larger of the two; Replace
                        is the legacy overwrite. */}
                    {showAdvanced && (
                    <div className="flex items-center gap-1 mr-1 border border-[var(--border)] rounded-sm overflow-hidden" data-testid="refine-merge-mode">
                      <span className="px-2 py-2 text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold bg-[var(--surface-muted)]" title="How to merge values from Refine on Photo into the AI aggregate">
                        Refine merge
                      </span>
                      {[
                        { key: "add",     label: "+ Add",   hint: "Refines ADD to the aggregate — best when measuring each elevation separately" },
                        { key: "max",     label: "Max",    hint: "Keep the larger of the AI value vs the refined value — never lowers your totals" },
                        { key: "replace", label: "Replace", hint: "Refined value wins — overwrites the AI aggregate (legacy behavior)" },
                      ].map((m) => (
                        <button
                          key={m.key}
                          type="button"
                          onClick={() => setRefineMergeMode(m.key)}
                          className={`px-2 py-2 text-[10px] font-bold uppercase tracking-wider transition ${
                            refineMergeMode === m.key
                              ? "bg-[#0EA5E9] text-white"
                              : "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]"
                          }`}
                          data-testid={`refine-merge-${m.key}`}
                          title={m.hint}
                        >
                          {m.label}
                        </button>
                      ))}
                    </div>
                    )}
                    {showAdvanced && (
                    <button
                      type="button"
                      onClick={() => setRefineOpen(true)}
                      disabled={busy}
                      className="px-3 py-2 bg-[var(--surface)] text-[#0EA5E9] border border-[#0EA5E9] hover:bg-[var(--surface-muted)] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50"
                      data-testid="ai-measure-refine-btn"
                      title="Pick one of your photos and tap-measure. Merge mode controls whether refines ADD, take MAX, or REPLACE the AI aggregate."
                    >
                      <Ruler className="w-3.5 h-3.5" />
                      Refine on Photo
                    </button>
                    )}
                    {/* Iter 79j.36 — Debug view button. Advanced-only.
                        Opens a two-column modal: per-photo raw
                        observations on the left, reconciled house
                        JSON with provenance on the right. Only
                        useful once a preview is loaded — pre-preview
                        state is diagnosed with the upload grid
                        itself. */}
                    {showAdvanced && preview && (
                      <button
                        type="button"
                        onClick={() => setDebugOpen(true)}
                        className="px-3 py-2 bg-[var(--surface)] text-[var(--ai)] border border-[var(--ai)] hover:bg-[var(--ai-soft)] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5"
                        data-testid="ai-measure-debug-btn"
                        title="Show per-photo raw observations and the reconciled house JSON with provenance"
                      >
                        <Bug className="w-3.5 h-3.5" />
                        Debug
                      </button>
                    )}
                    {/* Iter 78z+++ — Tag Profiles also accessible from
                        the preview footer so contractors can correct
                        a missed Shake / B&B / dormer AFTER seeing the
                        AI's first pass. Mirrors the pre-run button. */}
                    {photoUrls.length > 0 && estimateId && (
                      <button
                        type="button"
                        onClick={() => setProfileAnnotatorOpen(true)}
                        disabled={busy}
                        className="px-3 py-2 bg-[var(--surface)] text-[var(--brand-text)] border border-[var(--brand)] hover:bg-[#FFF7ED] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50 mr-1"
                        data-testid="ai-measure-tag-profiles-btn-preview"
                        title="Draw boxes to tag Shake / B&B / Dormer — guarantees those materials hit the quote even if AI missed them"
                      >
                        Tag Profiles
                        {Object.entries(savedProfileAnnotations).filter(([k, v]) => !k.startsWith("_") && Array.isArray(v) && v.length > 0).length > 0 && (
                          <span className="bg-[var(--brand)] text-[var(--on-brand)] px-1 py-0 text-[9px]">
                            {Object.entries(savedProfileAnnotations).reduce((a, [k, v]) => a + (k.startsWith("_") ? 0 : (Array.isArray(v) ? v.length : 0)), 0)}
                          </span>
                        )}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() =>
                        printTakeoff({
                          source: "AI Photo Measure",
                          measurements: preview?.measurements || {},
                          lines: preview?.lines || [],
                          openings:
                            preview?.measurements?._ai_openings ||
                            preview?.raw_ai?.openings ||
                            [],
                          est: {
                            customer_name: "",
                            address: address || "",
                            estimate_number: estimateId ? estimateId.slice(0, 8) : "Draft",
                          },
                          kind: kind || "siding",
                        })
                      }
                      disabled={busy || !preview}
                      className="px-3 py-2 bg-[var(--surface)] text-[#0EA5E9] border border-[#0EA5E9] hover:bg-[#F0F9FF] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50"
                      data-testid="ai-measure-print-btn"
                      title="Print this AI takeoff preview"
                    >
                      <Printer className="w-3.5 h-3.5" /> Print
                    </button>
                    <button
                      type="button"
                      onClick={apply}
                      disabled={busy || (() => {
                        // Iter 79j.52 — Visually mirror the runtime
                        // hard-block in apply(). Signals live in
                        // raw_ai (walls/dormers/openings arrays) and
                        // measurements.siding_sqft / eaves_lf — NOT
                        // in measurements.walls (that field is never
                        // populated by the aggregator).
                        const ra = preview?.raw_ai || {};
                        if (ra._reconciliation_error) return true;
                        const raWalls = Array.isArray(ra.walls) ? ra.walls.length : 0;
                        const raDormers = Array.isArray(ra.dormers) ? ra.dormers.length : 0;
                        const raOpenings = Array.isArray(ra.openings) ? ra.openings.length : 0;
                        const m = preview?.measurements || {};
                        const sidingSqft = Number(m.siding_sqft || 0);
                        const eavesLf = Number(m.eaves_lf || 0);
                        const hasFootprint =
                          raWalls > 0 || raDormers > 0 || raOpenings > 0 ||
                          sidingSqft > 0 || eavesLf > 0;
                        return !hasFootprint;
                      })()}
                      className="px-3 py-2 bg-[var(--brand)] text-[var(--on-brand)] hover:bg-[var(--brand-hover)] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                      data-testid="ai-measure-apply-btn"
                      title={preview?.raw_ai?._reconciliation_error
                        ? "Reconciliation failed — nothing to apply. Retry Phase B first."
                        : "Apply the AI takeoff to the estimate"}
                    >
                      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                      {busy ? "Saving…" : "Apply Measurements"}
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Iter 56: pre-AI annotation modal. Lets the contractor mark a
          reference scale anchor + no-siding zones on each photo BEFORE
          submitting to Claude. The annotations are burned into the
          rendered image in runMeasure() and described as text alongside. */}
      <PhotoAnnotateModal
        open={!!annotateOpenFor}
        onClose={() => setAnnotateOpenFor(null)}
        photoUrl={annotateOpenFor ? `/api/uploads/${annotateOpenFor}` : null}
        elevation={
          annotateOpenFor
            ? (photoAnnotations[annotateOpenFor]?.elevation || "")
            : ""
        }
        reference={
          annotateOpenFor ? (photoAnnotations[annotateOpenFor]?.reference || null) : null
        }
        windowReference={
          annotateOpenFor ? (photoAnnotations[annotateOpenFor]?.windowReference || null) : null
        }
        zones={
          annotateOpenFor ? (photoAnnotations[annotateOpenFor]?.zones || []) : []
        }
        targetPin={
          annotateOpenFor ? (photoAnnotations[annotateOpenFor]?.targetPin || null) : null
        }
        windows={
          annotateOpenFor ? (photoAnnotations[annotateOpenFor]?.windows || []) : []
        }
        profileBoxes={
          annotateOpenFor ? (photoAnnotations[annotateOpenFor]?.profileBoxes || []) : []
        }
        onSave={({ reference, windowReference, zones, targetPin, windows, profileBoxes, imageDims }) => {
          if (!annotateOpenFor) return;
          setPhotoAnnotations((prev) => ({
            ...prev,
            [annotateOpenFor]: {
              ...(prev[annotateOpenFor] || {}),
              reference,
              windowReference,
              zones,
              targetPin,
              windows,
              profileBoxes,
            },
          }));
          // Iter 78z+++ — push the new in-modal profile boxes into the
          // estimate-level annotations object so the worker treats them
          // as ground-truth on Run / Re-run. Keyed by photo INDEX to
          // match the backend (apply_annotations_to_breakdown).
          const idx = photoUrls.indexOf(annotateOpenFor);
          if (idx >= 0) {
            const naturalW = imageDims?.w || 1;
            const naturalH = imageDims?.h || 1;
            const elev = photoAnnotations[annotateOpenFor]?.elevation || "other";
            const boxesForBackend = (profileBoxes || []).map((b) => {
              const xs = b.points.map((p) => p.x);
              const ys = b.points.map((p) => p.y);
              const minX = Math.min(...xs), minY = Math.min(...ys);
              const maxX = Math.max(...xs), maxY = Math.max(...ys);
              return {
                shape: b.shape,
                elevation_label: elev,
                profile: b.profile,
                location: b.location,
                sqft: b.sqft,
                callout: b.note || "",
                ...(b.shape === "polygon"
                  ? {
                      points: b.points.map((p) => ({ x_norm: p.x / naturalW, y_norm: p.y / naturalH })),
                    }
                  : {
                      x_norm: minX / naturalW,
                      y_norm: minY / naturalH,
                      w_norm: (maxX - minX) / naturalW,
                      h_norm: (maxY - minY) / naturalH,
                    }),
              };
            });
            // Build a fresh scale_ref from the wall anchor for backend
            // sqft recompute parity.
            //
            // Iter 79j.63 — Write BOTH schemas so future consumers
            // reading either shape work. See wizard-path counterpart
            // for the full rationale.
            const ref = reference;
            let scaleRef = null;
            if (ref && ref.p1 && ref.p2 && ref.inches > 0) {
              const dx = ref.p2.x - ref.p1.x;
              const dy = ref.p2.y - ref.p1.y;
              const dist = Math.sqrt(dx * dx + dy * dy);
              if (dist > 0) {
                scaleRef = {
                  // OLD shape (backend + ProfileAnnotator display)
                  px_height: dist,
                  real_ft: ref.inches / 12,
                  img_w: naturalW,
                  img_h: naturalH,
                  // NEW shape (parity with wizard writer)
                  p1_x_norm: ref.p1.x / naturalW,
                  p1_y_norm: ref.p1.y / naturalH,
                  p2_x_norm: ref.p2.x / naturalW,
                  p2_y_norm: ref.p2.y / naturalH,
                  inches: ref.inches,
                };
              }
            }
            setSavedProfileAnnotations((prev) => {
              const next = { ...(prev || {}) };
              next[String(idx)] = boxesForBackend;
              const refs = { ...((prev && prev._scale_refs) || {}) };
              if (scaleRef) refs[String(idx)] = scaleRef;
              else delete refs[String(idx)];
              next._scale_refs = refs;
              // Iter 79j.14 — persist to backend so the Run AI Measure
              // worker can read the profile boxes from the estimate doc.
              // Previous local-only state meant shake polygons drawn in
              // the guided flow never reached Claude / the sqft router,
              // so Apply Measurements didn't move the ft² into the
              // SHAKE / B&B / etc. profile SKUs. Fire-and-forget PUT;
              // failure is non-fatal (annotations stay in local state
              // for this session, but log so we can debug).
              if (estimateId) {
                api.put(`/estimates/${estimateId}/profile-annotations`, { annotations: next })
                  .catch((err) => console.warn("profile-annotations persist failed:", err?.message));
              }
              return next;
            });
          }
          toast.success("Annotations saved · Claude will see them when you Run AI Measure");
        }}
        onOpenProfileAnnotator={
          estimateId
            ? () => {
                // Iter 78z+++ — Profile button inside the annotate modal.
                // Close the per-photo modal and open the cross-photo
                // Tag Profiles tool (LAP / SHAKE / B&B / Stone / Brick
                // / dormer routing). User keeps using AI Measure photos.
                setProfileAnnotatorOpen(true);
              }
            : undefined
        }
      />
      {/* Child modal: tap-on-photo refinement. Overrides any subset of
          the AI measurements with hand-measured values. The AI photos
          are handed down via prefillUrls (session-persistent server
          URLs) so the user can skip the re-upload step. */}
      <PhotoMeasureButton
        hideTrigger
        externalOpen={refineOpen}
        onExternalClose={() => setRefineOpen(false)}
        prefillUrls={photoUrls}
        onApply={async ({ measurements: refined }) => {
          // Iter 55: Merge ONLY the linear / count fields. The
          // `siding_sqft` from PhotoMeasureButton is partial (only the
          // walls the contractor tapped this session) and would clobber
          // the AI's full-house geometry. Siding stays anchored to the
          // editable Wall Breakdown table.
          //
          // The merge MODE (add / max / replace) lets the contractor pick
          // semantics. Default = "add" so refining each elevation in turn
          // accumulates LFs and counts naturally. Mode is selectable
          // inside the Refine on Photo modal header.
          const MERGEABLE_KEYS = new Set([
            "eaves_lf",
            "rakes_lf",
            "starter_lf",
            "outside_corner_lf",
            "inside_corner_lf",
            "opening_perimeter_lf",
            "opening_count",
            "window_count",
            "entry_door_count",
            "patio_door_count",
            "garage_door_count",
          ]);
          const mergeOne = (prev, refinedVal) => {
            const p = Number(prev) || 0;
            const r = Number(refinedVal) || 0;
            if (refineMergeMode === "add") return p + r;
            if (refineMergeMode === "max") return Math.max(p, r);
            return r; // "replace"
          };
          const diffs = []; // [{ key, prev, refined, after }]
          setPreview((prev) => {
            if (!prev) return prev;
            const next = { ...prev.measurements };
            for (const [k, v] of Object.entries(refined || {})) {
              if (!MERGEABLE_KEYS.has(k)) continue;
              const num = Number(v) || 0;
              if (num <= 0) continue;
              const before = Number(next[k] || 0);
              const after = mergeOne(before, num);
              if (after !== before) {
                next[k] = after;
                diffs.push({ key: k, prev: before, refined: num, after });
              }
            }
            return { ...prev, measurements: next };
          });
          setWallsDirty(true);
          setRefineOpen(false);
          // Surface the actual deltas so the contractor can see what
          // moved. e.g. "+ eaves 40 → 176, + windows 3 → 14" on Add mode.
          if (diffs.length) {
            const sample = diffs.slice(0, 3).map((d) =>
              `${d.key.replace(/_/g, " ")} ${d.prev}→${d.after}`
            ).join(", ");
            const more = diffs.length > 3 ? ` (+${diffs.length - 3} more)` : "";
            toast.success(`Refined (${refineMergeMode}): ${sample}${more} · siding ft² unchanged`);
          } else {
            toast.success(`Refine applied — no changes vs ${refineMergeMode} mode · siding ft² unchanged`);
          }
        }}
      />
      <GuidedCaptureWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onComplete={handleWizardComplete}
      />

      {/* Iter 79j.11 — Pre-Guided-Capture calibration prompt. Fires
          when the contractor taps "Guided Capture" so they set the
          CURRENT siding exposure BEFORE the first photo. Chips route
          to sidingExposure (or brickCourse for the Brick chip).
          Skip is allowed — some jobs the contractor genuinely can't
          eyeball the row height. */}
      {calibPrepOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4" data-testid="calib-prep-modal">
          <div className="bg-[var(--surface)] max-w-md w-full shadow-2xl border border-[var(--ai)]">
            <div className="bg-[var(--ai)] px-4 py-3 flex items-start justify-between gap-3">
              <div>
                <div className="text-white text-sm font-heading font-bold uppercase tracking-wider">Calibrate window sizing</div>
                <div className="text-white/80 text-[11px] mt-0.5 leading-snug">
                  What&apos;s currently on this house? Claude uses this to size windows accurately. Pick the closest match to what you see on the walls right now (not the scope).
                </div>
              </div>
              <button type="button" onClick={() => setCalibPrepOpen(false)}
                      className="text-white/80 hover:text-white" title="Close">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold">Current siding on the house</div>
              <div className="grid grid-cols-3 gap-1.5">
                {[
                  { label: "Vinyl D4",    val: "4",  field: "siding" },
                  { label: "Vinyl D5",    val: "5",  field: "siding" },
                  { label: "Vinyl D6",    val: "6",  field: "siding" },
                  { label: "Vinyl D7",    val: "7",  field: "siding" },
                  { label: "Ascend CI",   val: "7",  field: "siding" },
                  { label: 'LP 8" Lap',   val: "8",  field: "siding" },
                  { label: 'Cedar 4"',    val: "4",  field: "siding" },
                  { label: "Brick",       val: "8",  field: "brick"  },
                ].map((c) => {
                  const active = c.field === "siding"
                    ? sidingExposure === c.val && !brickCourse
                    : brickCourse === c.val && !sidingExposure;
                  return (
                    <button
                      key={c.label}
                      type="button"
                      onClick={() => {
                        if (c.field === "siding") {
                          setSidingExposure(c.val);
                          setBrickCourse("");
                        } else {
                          setBrickCourse(c.val);
                          setSidingExposure("");
                        }
                      }}
                      className={`px-2 py-2 text-[10px] font-bold uppercase tracking-wider border ${
                        active ? "bg-[var(--ai)] text-white border-[var(--ai)]" : "bg-[var(--surface)] text-[var(--ink-2)] border-[var(--border)] hover:bg-[var(--bg-app)]"
                      }`}
                      data-testid={`calib-prep-chip-${c.label.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
                    >
                      {c.label}
                      <div className={`text-[9px] font-normal mt-0.5 ${active ? "text-white/80" : "text-[var(--bar-muted)]"}`}>
                        {c.val}&quot; {c.field === "brick" ? "course" : "exposure"}
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="pt-2 border-t border-[var(--border)] space-y-1">
                <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold">Or enter exposure directly (in)</div>
                <input
                  type="number"
                  step="0.25"
                  min="0"
                  className="w-full px-3 py-2 border border-[var(--border)] text-sm focus:outline-none focus:border-[var(--ai)]"
                  placeholder='e.g. 4.5" cedar shake'
                  value={sidingExposure}
                  onChange={(e) => { setSidingExposure(e.target.value); if (e.target.value) setBrickCourse(""); }}
                  data-testid="calib-prep-siding-input"
                />
              </div>

              {(sidingExposure || brickCourse) && (
                <div className="text-[11px] text-[var(--success)] font-bold flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5" />
                  Calibration set — Claude will cross-check window heights against this.
                </div>
              )}
            </div>
            <div className="border-t border-[var(--border)] px-4 py-3 flex justify-between items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setSidingExposure("");
                  setBrickCourse("");
                  setCalibPrepOpen(false);
                  setWizardOpen(true);
                }}
                className="px-3 py-2 bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] hover:bg-[var(--bg-app)] text-xs font-bold uppercase tracking-wider"
                data-testid="calib-prep-skip"
                title="Proceed without calibration — Claude will still snap to standard window sizes"
              >
                Skip · I&apos;ll eyeball it
              </button>
              <button
                type="button"
                onClick={() => {
                  setCalibPrepOpen(false);
                  setWizardOpen(true);
                }}
                disabled={!sidingExposure && !brickCourse}
                className="px-4 py-2 bg-[var(--success)] text-white hover:bg-[#15803D] text-xs font-bold uppercase tracking-wider disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                data-testid="calib-prep-start"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Start Capture →
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Iter 79j.36 — Extraction Debug modal (Advanced only). */}
      {debugOpen && (
        <AIExtractionDebugModal
          preview={preview}
          photoUrls={photoUrls}
          estimateId={estimateId}
          onClose={() => setDebugOpen(false)}
        />
      )}
      {/* Iter 78z — Profile Annotator (Tag Shake / B&B / etc.)
          Iter 79j.63 — Wrapped in an ErrorBoundary. Any render crash
          inside the annotator (e.g. the Jul 7 2026 scale_ref schema
          mismatch that crashed via `.toFixed` on undefined) now
          surfaces a recoverable dialog instead of unmounting the
          entire estimate editor. */}
      {profileAnnotatorOpen && estimateId && (
        <AnnotatorErrorBoundary onClose={() => setProfileAnnotatorOpen(false)}>
          <ProfileAnnotator
            estimateId={estimateId}
            photos={photoUrls.map((name, i) => ({
              url: `/api/uploads/${name}`,
              label: photoAnnotations[name]?.elevation || `#${i + 1}`,
            }))}
            initialAnnotations={savedProfileAnnotations}
            defaultElevationByIdx={photoUrls.map((name) => photoAnnotations[name]?.elevation || "other")}
            /* Iter 78z+++ — thread the Wall Scale Anchor from PhotoAnnotateModal
               so the contractor doesn't have to set scale twice. */
            wallScaleRefByPhotoKey={Object.fromEntries(
              photoUrls.map((name, i) => [String(i), photoAnnotations[name]?.reference || null])
            )}
            onClose={() => setProfileAnnotatorOpen(false)}
            onSaved={(saved) => {
              setSavedProfileAnnotations(saved);
            }}
            onSaveAndRerun={currentRunId ? async () => {
              rerunWithAnnotations();
            } : null}
          />
        </AnnotatorErrorBoundary>
      )}
      {/* Iter 79i (Phase 4) — Missing-wall pre-flight modal. Fires
          before runMeasure() if fewer than 4 primary walls are covered.
          Contractor can go back to capture more OR click "Run anyway"
          to bypass (which sets the bypass flag so the modal doesn't
          re-fire on retry). */}
      {missingWallsModal && missingWallsModal !== "bypassed" && (
        <div
          className="fixed inset-0 z-[60] bg-[var(--bar-bg)]/70 flex items-center justify-center p-4"
          data-testid="ai-measure-missing-walls-modal"
        >
          <div className="bg-[var(--surface)] max-w-md w-full p-6 shadow-2xl">
            <div className="text-xs uppercase tracking-wider text-[var(--brand-text)] font-bold mb-2">
              ⚠️ Missing walls
            </div>
            <h3 className="text-lg font-bold text-[var(--ink)] mb-2">
              Only {4 - missingWallsModal.missing.length} of 4 primary walls captured
            </h3>
            <p className="text-sm text-[var(--ink-2)] mb-3">
              Missing: <b className="text-[var(--brand-text)]">{missingWallsModal.missing.join(", ")}</b>
            </p>
            <p className="text-sm text-[var(--ink-2)] mb-4">
              AI Measure will estimate the missing walls from photos of adjacent
              elevations, which drops accuracy by 10-20%. If the side yard is
              inaccessible, run anyway — otherwise, add the missing shots.
            </p>
            <div className="flex flex-wrap gap-2 justify-end">
              <button
                type="button"
                onClick={() => {
                  setMissingWallsModal(null);
                  setWizardOpen(true);
                }}
                className="px-3 py-2 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-xs font-bold uppercase tracking-wider"
                data-testid="ai-measure-missing-walls-open-wizard"
              >
                Capture missing walls
              </button>
              <button
                type="button"
                onClick={() => {
                  setMissingWallsModal(null);
                  // Iter 79j.20 — explicit bypass param instead of the
                  // "bypassed" state sentinel. Avoids the stale-closure
                  // bug where setTimeout captured the old runMeasure
                  // and re-fired the guard.
                  runMeasure({ bypassMissingWallsGuard: true });
                }}
                className="px-3 py-2 bg-[var(--surface)] border border-[var(--border)] text-[var(--muted)] hover:bg-[var(--surface-muted)] text-xs font-bold uppercase tracking-wider"
                data-testid="ai-measure-missing-walls-run-anyway"
              >
                Run anyway
              </button>
              <button
                type="button"
                onClick={() => setMissingWallsModal(null)}
                className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--muted)] hover:text-[var(--muted)]"
                data-testid="ai-measure-missing-walls-cancel"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
