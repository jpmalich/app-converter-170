// GuidedCaptureWizard — HOVER-style step-by-step photo capture.
//
// The "garbage-in problem" is the #1 root cause of bad AI measurements.
// Contractors snap whatever they have on their phone and upload all at
// once, missing elevations or shooting at bad angles. This wizard fixes
// that by walking them through a fixed sequence of 8 standard positions
// (the same sequence HOVER uses), auto-tagging each photo with the
// matching elevation as it's captured, and gating progress on actually
// HAVING a photo in each slot. The contractor can skip any slot, but
// missing slots produce a visible "MISSING" tag at the end so Claude
// gets explicit signal in `missing_elevations`.
//
// Iter 79f (Feb 2026) — Phase 1 of Howard's guided-flow ask: interleave
// annotation between captures instead of forcing the contractor to
// annotate all 8 photos at the end. After each capture we upload the
// photo to the server (so it's safe even if the wizard is closed
// mid-flow) and offer "Annotate this photo now?" — clicking Annotate
// opens PhotoAnnotateModal on that just-captured photo, pre-tagged with
// the elevation label so the contractor knows what wall they're on. On
// modal close, wizard advances to the next capture step.
//
// Layout: full-screen modal on mobile, large central card on desktop.
// Each step shows a diagram (text-only ASCII for now — can swap to SVG
// later), the standing position instructions, a Camera/Choose button,
// thumbnail preview once a photo is captured, and Next/Skip controls.
//
// Output: parent gets onComplete({ photos: [{ file, elevation, key,
// name, annotations }, ...] }) — `name` is the server filename (skip
// re-upload) and `annotations` is the per-photo tag payload from
// PhotoAnnotateModal (elevation + scale ref + zones + windows +
// profileBoxes).
import React, { useEffect, useRef, useState } from "react";
import { Camera, X, Check, ChevronRight, ChevronLeft, SkipForward, Tags, Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import PhotoAnnotateModal from "@/components/estimate/PhotoAnnotateModal";

// 8 standard capture positions. HOVER uses this exact sequence — it
// gives each wall TWO photos from different angles (corner shots show
// two elevations each), maximising the AI's reconciliation signal.
const STEPS = [
  {
    key: "front-center",
    elevation: "front",
    title: "Front · stand 25-30 ft back",
    hint: "Center the house. Try to get the WHOLE front in frame — eaves and ground both visible.",
    diagram: "🏠 ← YOU (25-30 ft)",
  },
  {
    key: "front-left",
    elevation: "front-left",
    title: "Front-Left Corner",
    hint: "Step to the front-left corner. Frame the front wall AND the left wall at ~45°. Get the corner trim and both walls' bottom courses in frame — this corner's course count is cross-checked against the front and left wall shots.",
    diagram: "🏠     ↙ YOU",
  },
  {
    key: "left",
    elevation: "left",
    title: "Left side · stand 25 ft back",
    hint: "Walk to the LEFT side of the house. Center the left elevation.",
    diagram: "YOU →  🏠",
  },
  {
    key: "rear-left",
    elevation: "rear-left",
    title: "Rear-Left Corner",
    hint: "Step to the rear-left corner. Frame the left wall AND the back wall at ~45°. Get the corner trim and both walls' bottom courses in frame — this corner's course count is cross-checked against the left and back wall shots.",
    diagram: "↘ YOU\n🏠",
  },
  {
    key: "rear",
    elevation: "back",
    title: "Back · stand 25 ft back",
    hint: "Now the BACK of the house. Center the rear elevation.",
    diagram: "YOU\n ↓\n🏠",
  },
  {
    key: "rear-right",
    elevation: "rear-right",
    title: "Rear-Right Corner",
    hint: "Step to the rear-right corner. Frame the back wall AND the right wall at ~45°. Get the corner trim and both walls' bottom courses in frame — this corner's course count is cross-checked against the back and right wall shots.",
    diagram: "    YOU ↙\n🏠",
  },
  {
    key: "right",
    elevation: "right",
    title: "Right side · stand 25 ft back",
    hint: "Walk to the RIGHT side of the house. Center the right elevation.",
    diagram: "🏠 ← YOU",
  },
  {
    key: "front-right",
    elevation: "front-right",
    title: "Front-Right Corner",
    hint: "Last one — step to the front-right corner. Frame the front wall AND the right wall at ~45°. Get the corner trim and both walls' bottom courses in frame — this corner's course count is cross-checked against the front and right wall shots.",
    diagram: "🏠   ↘ YOU",
  },
  // Iter 79i (Phase 4) — Optional aerial/satellite step. Contractor
  // takes a screenshot of Google Maps satellite / a drone shot and
  // drops a target-pin so Claude knows WHICH house to measure when
  // neighbors are close. Uses the existing PhotoAnnotateModal in
  // MODE_TARGET (auto-selected when elevation="aerial").
  {
    key: "aerial",
    elevation: "aerial",
    title: "Aerial / satellite (optional)",
    hint: "Screenshot Google Maps satellite view or drop a drone shot. Then tap two corners around your house to help Claude isolate it from neighbors.",
    diagram: "🛰️  ⬇  🏠",
  },
];

// Iter 79i (Phase 4) — save/resume constants. Wizard state is
// persisted to localStorage so a locked iPad or an accidental tab
// close doesn't nuke 5 minutes of work.
const RESUME_STORAGE_KEY = "guidedCaptureResume";
const RESUME_MAX_AGE_MS = 6 * 60 * 60 * 1000; // 6 hours — same job, same day.
const PRIMARY_WALLS = ["front", "back", "left", "right"];

// Iter 79i — persist a compact snapshot to localStorage.
function persistResume(captured, stepIdx) {
  try {
    const compact = {};
    for (const [key, c] of Object.entries(captured)) {
      // Only persist photos that made it up to the server — File +
      // blob-URL don't survive a page refresh.
      if (!c?.name) continue;
      compact[key] = {
        name: c.name,
        elevation: c.elevation,
        annotations: c.annotations || null,
        annotated: !!c.annotated,
      };
    }
    if (Object.keys(compact).length === 0) {
      localStorage.removeItem(RESUME_STORAGE_KEY);
      return;
    }
    localStorage.setItem(
      RESUME_STORAGE_KEY,
      JSON.stringify({ captured: compact, stepIdx, ts: Date.now() }),
    );
  } catch {
    /* localStorage disabled — silent no-op */
  }
}

function readResume() {
  try {
    const raw = localStorage.getItem(RESUME_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.captured || !parsed.ts) return null;
    if (Date.now() - parsed.ts > RESUME_MAX_AGE_MS) {
      localStorage.removeItem(RESUME_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function clearResume() {
  try { localStorage.removeItem(RESUME_STORAGE_KEY); } catch {
    /* localStorage disabled */
  }
}

export default function GuidedCaptureWizard({ open, onClose, onComplete }) {
  const fileRef = useRef();
  const [stepIdx, setStepIdx] = useState(0);
  // captured: { [key]: { file, previewUrl, elevation, name?, uploading?,
  //                      annotations?, annotated? } | null }
  //   name         — server filename once /api/uploads returns
  //   uploading    — true while the POST is in flight (Annotate button is
  //                  disabled until the URL is ready)
  //   annotations  — payload from PhotoAnnotateModal.onSave, or null
  //   annotated    — true after the annotator was opened + saved
  const [captured, setCaptured] = useState({});
  // Iter 79f — annotator state. When the contractor clicks "Annotate
  // this photo" we open PhotoAnnotateModal on the current step's photo.
  const [annotateOpen, setAnnotateOpen] = useState(false);
  // Iter 79g (Phase 2) — Fast Track mode: contractor toggles this if they
  // want to capture all 8 photos first and annotate later (from the
  // main AI Measure screen). Persisted per-browser so their preference
  // sticks across sessions. Default OFF (annotate-now is recommended).
  const [fastTrack, setFastTrack] = useState(() => {
    try {
      return localStorage.getItem("guidedCaptureFastTrack") === "1";
    } catch { return false; }
  });
  const toggleFastTrack = () => {
    setFastTrack((v) => {
      const next = !v;
      try { localStorage.setItem("guidedCaptureFastTrack", next ? "1" : "0"); } catch {
        /* localStorage disabled — silent no-op */
      }
      return next;
    });
  };
  // Iter 79i (Phase 4) — resume-prompt state. Set once on mount if a
  // recent (< 6h) snapshot exists in localStorage. Contractor picks
  // Resume (loads the snapshot) or Start Over (clears + fresh state).
  const [resumeCandidate, setResumeCandidate] = useState(null);
  useEffect(() => {
    if (!open) return;
    // Only check on wizard OPEN — not on every render. Guard against
    // re-prompting after they've already chosen.
    if (Object.keys(captured).length > 0) return;
    const found = readResume();
    if (found && Object.keys(found.captured || {}).length > 0) {
      setResumeCandidate(found);
    }
  }, [open]);

  // Iter 79i — persist a compact snapshot to localStorage every time
  // `captured` changes. Save-on-write keeps the resume snapshot
  // continuously fresh so a screen-lock in the middle of step 5 still
  // captures work through step 4.
  useEffect(() => {
    if (!open) return;
    if (Object.keys(captured).length === 0) return;
    persistResume(captured, stepIdx);
  }, [captured, stepIdx, open]);

  const applyResume = () => {
    if (!resumeCandidate) return;
    const restored = {};
    for (const [key, c] of Object.entries(resumeCandidate.captured || {})) {
      restored[key] = {
        // No File / previewUrl on resume — the photo is already
        // server-hosted at /api/uploads/{name}, so the wizard shows
        // it via the same URL the parent will consume at finish().
        file: null,
        previewUrl: `/api/uploads/${c.name}`,
        elevation: c.elevation,
        name: c.name,
        uploading: false,
        annotations: c.annotations || null,
        annotated: !!c.annotated,
      };
    }
    setCaptured(restored);
    setStepIdx(Math.min(resumeCandidate.stepIdx ?? 0, STEPS.length - 1));
    setResumeCandidate(null);
  };
  const dismissResume = () => {
    clearResume();
    setResumeCandidate(null);
  };

  if (!open) return null;
  const step = STEPS[stepIdx];
  const taken = captured[step.key];

  const handlePick = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    setCaptured((prev) => ({
      ...prev,
      [step.key]: {
        file: f,
        previewUrl: url,
        elevation: step.elevation,
        uploading: true,
        name: null,
        annotations: null,
        annotated: false,
      },
    }));
    if (e.target) e.target.value = "";
    // Iter 79f — upload immediately so PhotoAnnotateModal has a stable
    // server URL to render (blob URLs don't survive a wizard close). If
    // upload fails we mark the step as not-uploaded and hide the
    // Annotate button; the contractor can still Next/Skip and the
    // parent will retry the upload from the File object on wizard
    // complete.
    (async () => {
      try {
        const fd = new FormData();
        fd.append("file", f);
        const { data } = await api.post("/uploads", fd, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 60000,
        });
        setCaptured((prev) => {
          const cur = prev[step.key];
          if (!cur || cur.file !== f) return prev; // retook already
          return { ...prev, [step.key]: { ...cur, name: data?.name || null, uploading: false } };
        });
        // Iter 79j (Feb 2026) — auto-fire the guided annotator as soon
        // as the upload settles. This delivers Howard's ask directly:
        // "contractor takes photo, after photo taken the app
        // automatically fires the annotate button". Skipping the
        // manual gate button is fine — the annotator itself now has
        // an "Exit guided mode" link for anyone who wants to bypass.
        // Skip for the aerial step (elevation === "aerial") since
        // aerial uses Target Pin, not the 5-step wall/window flow.
        if (!fastTrack && step.elevation !== "aerial") {
          setTimeout(() => setAnnotateOpen(true), 100);
        }
      } catch {
        setCaptured((prev) => {
          const cur = prev[step.key];
          if (!cur || cur.file !== f) return prev;
          return { ...prev, [step.key]: { ...cur, uploading: false } };
        });
        toast.error("Upload failed for this photo — you can still Next/Skip, we'll retry at the end.");
      }
    })();
  };
  const retake = () => {
    if (taken?.previewUrl) URL.revokeObjectURL(taken.previewUrl);
    setCaptured((prev) => {
      const next = { ...prev };
      delete next[step.key];
      return next;
    });
    fileRef.current?.click();
  };

  // Iter 79f — annotator handlers. Open the existing PhotoAnnotateModal
  // on this step's uploaded photo. On save, stash the annotation
  // payload per step-key so it can be handed back to the parent (which
  // applies it to photoAnnotations[name] and hands it to the AI Measure
  // worker as ground-truth hints).
  const openAnnotate = () => {
    if (!taken?.name) {
      toast.error("Photo is still uploading — try again in a sec.");
      return;
    }
    setAnnotateOpen(true);
  };
  const handleAnnotateSave = (payload) => {
    setCaptured((prev) => {
      const cur = prev[step.key];
      if (!cur) return prev;
      return { ...prev, [step.key]: { ...cur, annotations: payload, annotated: true } };
    });
    setAnnotateOpen(false);
  };
  const next = () => {
    if (stepIdx < STEPS.length - 1) setStepIdx((i) => i + 1);
    else finish({ autoRun: false });
  };
  const skip = () => {
    if (stepIdx < STEPS.length - 1) setStepIdx((i) => i + 1);
    else finish({ autoRun: false });
  };
  const back = () => setStepIdx((i) => Math.max(0, i - 1));
  const finish = ({ autoRun = false } = {}) => {
    const photos = STEPS.map((s) => {
      const c = captured[s.key];
      if (!c) return null;
      return {
        file: c.file,
        elevation: c.elevation,
        key: s.key,
        // Iter 79f — hand the server filename + per-photo annotations
        // back to the parent so it can skip the re-upload path and
        // apply the annotations to photoAnnotations[name].
        name: c.name || null,
        annotations: c.annotations || null,
      };
    }).filter(Boolean);
    // Release object URLs — parent only needs the File objects from here
    STEPS.forEach((s) => {
      const c = captured[s.key];
      if (c?.previewUrl) URL.revokeObjectURL(c.previewUrl);
    });
    // Iter 79h (Phase 3) — pass `autoRun` up so the parent knows to
    // fire the AI Measure run immediately after uploads settle (see
    // AIMeasureButton.handleWizardComplete + auto-run effect).
    onComplete?.({ photos, autoRun });
    onClose?.();
    // Iter 79i (Phase 4) — success path: purge the resume snapshot so
    // reopening the wizard on this device won't offer a stale prompt.
    clearResume();
    setCaptured({});
    setStepIdx(0);
  };
  const cancel = () => {
    STEPS.forEach((s) => {
      const c = captured[s.key];
      if (c?.previewUrl) URL.revokeObjectURL(c.previewUrl);
    });
    setCaptured({});
    setStepIdx(0);
    onClose?.();
  };

  const captureCount = Object.keys(captured).length;
  const annotateCount = Object.values(captured).filter((c) => c?.annotated).length;
  const progressPct = ((stepIdx + 1) / STEPS.length) * 100;

  return (
    <div
      className="fixed inset-0 z-50 bg-[var(--bar-bg)]/70 flex items-center justify-center p-4"
      data-testid="guided-capture-wizard"
    >
      {/* Iter 79i (Phase 4) — Resume prompt. Shown once on wizard open
          when a recent (< 6h) snapshot exists in localStorage. Restore
          uses only server-hosted photo URLs — no File objects are
          persisted, so anything that was mid-upload is lost, but the
          already-uploaded photos (and their annotations) come right
          back to where the contractor left off. */}
      {resumeCandidate && (
        <div
          className="absolute inset-0 z-10 bg-[var(--bar-bg)]/80 flex items-center justify-center p-4"
          data-testid="guided-capture-resume-prompt"
        >
          <div className="bg-[var(--surface)] max-w-md w-full p-6 shadow-2xl">
            <div className="text-xs uppercase tracking-wider text-[#0EA5E9] font-bold mb-2">
              Resume your session?
            </div>
            <h3 className="text-lg font-bold text-[var(--ink)] mb-2">
              {Object.keys(resumeCandidate.captured || {}).length} photo
              {Object.keys(resumeCandidate.captured || {}).length !== 1 ? "s" : ""} from earlier
            </h3>
            <p className="text-sm text-[var(--ink-2)] mb-4">
              Looks like you started a Guided Capture on this device recently.
              Restore where you left off, or start fresh?
            </p>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={dismissResume}
                className="px-3 py-2 text-xs font-bold uppercase tracking-wider text-[var(--muted)] hover:text-[var(--ink-2)]"
                data-testid="guided-capture-resume-start-over"
              >
                Start over
              </button>
              <button
                type="button"
                onClick={applyResume}
                className="px-4 py-2 bg-[var(--success)] text-white hover:bg-[#15803D] text-xs font-bold uppercase tracking-wider"
                data-testid="guided-capture-resume-btn"
              >
                Resume
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="bg-[var(--surface)] w-full max-w-2xl rounded-sm shadow-2xl overflow-hidden flex flex-col max-h-[95vh]">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#0EA5E9] to-[#7C3AED] text-white px-5 py-4 flex items-center gap-3">
          <Camera className="w-5 h-5 flex-shrink-0" />
          <div className="flex-1">
            <div className="text-xs uppercase tracking-wider opacity-90">Guided Capture · HOVER-style</div>
            <div className="text-base font-bold" data-testid="guided-capture-header-tally">
              Step {stepIdx + 1} of {STEPS.length} · {captureCount} captured
              {annotateCount > 0 && (
                <span className="ml-1 text-[#DBEAFE]">· {annotateCount} annotated</span>
              )}
            </div>
          </div>
          <button
            onClick={cancel}
            className="text-white/80 hover:text-white"
            data-testid="guided-capture-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-[var(--bg-app)]">
          <div
            className="h-full bg-[var(--ai)] transition-all duration-300"
            style={{ width: `${progressPct}%` }}
            data-testid="guided-capture-progress"
          />
        </div>

        {/* Step dots — Iter 79f: annotated steps get a distinct
            ring so contractor sees at a glance which elevations still
            need annotations. */}
        <div className="flex justify-center gap-1.5 py-2 bg-[var(--surface-muted)] border-b border-[var(--border)]">
          {STEPS.map((s, i) => {
            const cap = captured[s.key];
            const done = !!cap;
            const annotated = !!cap?.annotated;
            const active = i === stepIdx;
            const bg = active
              ? "bg-[var(--ai)] text-white ring-2 ring-[var(--ai)]/30 ring-offset-1"
              : annotated
                ? "bg-[var(--success)] text-white ring-2 ring-[#0EA5E9]/60"
                : done
                  ? "bg-[var(--success)] text-white"
                  : "bg-[var(--table-header)] text-[var(--muted)] hover:bg-[#D4D4D8]";
            return (
              <button
                key={s.key}
                onClick={() => setStepIdx(i)}
                className={`w-6 h-6 rounded-full text-[10px] font-bold transition ${bg}`}
                title={`${s.title}${annotated ? " · annotated" : done ? " · captured" : ""}`}
                data-testid={`guided-capture-dot-${i}`}
              >
                {done ? "✓" : i + 1}
              </button>
            );
          })}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Iter 79g — Fast Track toggle. Recommended default is
              Annotate-now (better AI accuracy per photo), but power
              users who prefer to capture in one sweep and annotate at
              the end can flip this on. Preference persists to
              localStorage. */}
          <div className="flex items-center gap-2 mb-4 text-xs">
            <button
              type="button"
              onClick={toggleFastTrack}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 border font-bold uppercase tracking-wider transition ${
                fastTrack
                  ? "bg-[var(--surface)] border-[var(--border)] text-[var(--muted)] hover:bg-[var(--surface-muted)]"
                  : "bg-[var(--ai)] border-[var(--ai)] text-white"
              }`}
              data-testid="guided-capture-annotate-now-toggle"
              title="Show the Annotate button after each capture (recommended — better AI accuracy per photo)"
            >
              <Tags className="w-3 h-3" /> Annotate now
            </button>
            <button
              type="button"
              onClick={toggleFastTrack}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 border font-bold uppercase tracking-wider transition ${
                fastTrack
                  ? "bg-[var(--brand)] border-[var(--brand)] text-[var(--on-brand)]"
                  : "bg-[var(--surface)] border-[var(--border)] text-[var(--muted)] hover:bg-[var(--surface-muted)]"
              }`}
              data-testid="guided-capture-fast-track-toggle"
              title="Capture all photos first, then annotate them together at the end from the main AI Measure screen"
            >
              <Zap aria-hidden="true" className="w-3 h-3" /> Fast Track
            </button>
            <span className="text-[10px] text-[var(--muted)] italic ml-1">
              {fastTrack
                ? "Fast Track: photos only — annotate later"
                : "Best for accuracy — annotate each wall as you capture it"}
            </span>
          </div>

          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold">
            Elevation: <span className="text-[var(--ai)]">{step.elevation}</span>
          </div>
          <h2 className="text-xl font-bold text-[var(--ink)] mt-1 mb-2" data-testid="guided-capture-step-title">
            {step.title}
          </h2>
          <p className="text-sm text-[var(--ink-2)] mb-2">{step.hint}</p>
          <p
            className="text-[11px] text-[#92400E] bg-[#FEF3C7] border border-[#FCD34D] px-2 py-1.5 mb-4"
            data-testid="guided-capture-corner-pair-note"
          >
            <b>Shoot each corner from both walls.</b> Course counts anchor at corners, and only
            matching same-corner counts from two photos earn the enumerated (tape-provable) tier —
            everything else stays an amber estimate.
          </p>

          {/* Diagram */}
          <div className="bg-[var(--surface-muted)] border border-[var(--border)] py-6 px-4 mb-4 text-center font-mono-num text-2xl whitespace-pre leading-relaxed">
            {step.diagram}
          </div>

          {/* Capture / preview */}
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            className="hidden"
            onChange={handlePick}
            data-testid={`guided-capture-input-${stepIdx}`}
          />

          {!taken ? (
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="w-full border-2 border-dashed border-[var(--ai)] hover:bg-[#FAF5FF] py-8 flex flex-col items-center gap-2 transition-colors"
              data-testid="guided-capture-take-btn"
            >
              <Camera className="w-10 h-10 text-[var(--ai)]" />
              <div className="text-sm font-bold uppercase tracking-wider text-[var(--ai)]">
                Take / Choose Photo
              </div>
              <div className="text-xs text-[var(--muted)]">
                Phone camera or photo library
              </div>
            </button>
          ) : (
            <div className="relative border-2 border-[var(--success)]">
              <img
                src={taken.previewUrl}
                alt={`Step ${stepIdx + 1} preview`}
                className="w-full max-h-80 object-contain bg-[var(--bar-bg)]"
                data-testid={`guided-capture-preview-${stepIdx}`}
              />
              <div className="absolute top-2 left-2 bg-[var(--success)] text-white text-xs font-bold uppercase tracking-wider px-2 py-1 flex items-center gap-1">
                <Check className="w-3 h-3" /> Captured · {step.elevation}
              </div>
              <button
                onClick={retake}
                className="absolute top-2 right-2 bg-white/95 text-[var(--ink-2)] text-xs font-bold uppercase tracking-wider px-2 py-1 hover:bg-[var(--surface)]"
                data-testid="guided-capture-retake-btn"
              >
                Retake
              </button>
            </div>
          )}

          {/* Iter 79f — Annotate-this-photo gate. Appears once the photo
              is uploaded (photoUrl is stable + PhotoAnnotateModal can
              render). Skipping is always fine — annotations improve
              Claude's accuracy but aren't required. Iter 79g: hidden
              when Fast Track mode is on (contractor annotates at the
              end instead). */}
          {taken && !fastTrack && (
            <div className="mt-4 bg-[var(--surface-muted)] border border-[var(--border)] p-4">
              <div className="text-xs uppercase tracking-wider text-[var(--muted)] font-bold mb-1">
                Annotate this photo?
              </div>
              <div className="text-sm text-[var(--ink-2)] mb-3">
                Mark Wall · Window · Mask · Style · Profile · Calibrate so Claude
                gets ground truth instead of guessing. Takes 20-40 seconds.
              </div>
              <div className="flex flex-wrap gap-2 items-center">
                <button
                  type="button"
                  onClick={openAnnotate}
                  disabled={taken.uploading || !taken.name}
                  className="px-3 py-2 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-40"
                  data-testid="guided-capture-annotate-btn"
                >
                  {taken.uploading ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Uploading…</>
                  ) : taken.annotated ? (
                    <><Tags className="w-3.5 h-3.5" /> Edit annotations</>
                  ) : (
                    <><Tags className="w-3.5 h-3.5" /> Annotate {step.elevation}</>
                  )}
                </button>
                {taken.annotated && (
                  <span
                    className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[var(--success)]"
                    data-testid="guided-capture-annotated-badge"
                  >
                    <Check className="w-3.5 h-3.5" /> Annotated
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[var(--border)] px-5 py-3 flex justify-between items-center bg-[var(--surface)]">
          <button
            type="button"
            onClick={back}
            disabled={stepIdx === 0}
            className="px-3 py-2 text-xs font-bold uppercase tracking-wider text-[var(--ink-2)] disabled:opacity-30 flex items-center gap-1"
            data-testid="guided-capture-back-btn"
          >
            <ChevronLeft className="w-3.5 h-3.5" /> Back
          </button>
          <div className="flex gap-2">
            {!taken && (
              <button
                type="button"
                onClick={skip}
                className="px-3 py-2 bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] hover:bg-[var(--surface-muted)] text-xs font-bold uppercase tracking-wider flex items-center gap-1"
                data-testid="guided-capture-skip-btn"
                title="Skip this step — fewer photos = lower AI accuracy"
              >
                <SkipForward className="w-3.5 h-3.5" /> Skip
              </button>
            )}
            {stepIdx < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={next}
                disabled={!taken}
                className="px-4 py-2 bg-[var(--ai)] text-white hover:bg-[#6D28D9] text-xs font-bold uppercase tracking-wider flex items-center gap-1 disabled:opacity-40"
                data-testid="guided-capture-next-btn"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              // Iter 79h (Phase 3) — two end-of-wizard actions:
              //  1) PRIMARY green: "Done · Run AI Measure →" auto-fires
              //     the run after uploads settle. Removes the "hunt for
              //     the Run button" step Howard called out.
              //  2) SECONDARY grey link: "or just save photos" for
              //     contractors who want to review/tweak before Claude
              //     burns tokens (e.g. add a bulk-annotate pass first).
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => finish({ autoRun: false })}
                  disabled={captureCount === 0}
                  className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--muted)] hover:text-[var(--ink-2)] underline underline-offset-2 disabled:opacity-30"
                  data-testid="guided-capture-finish-save-only-btn"
                  title="Save photos without running AI Measure — you can trigger it manually later"
                >
                  Save photos only
                </button>
                <button
                  type="button"
                  onClick={() => finish({ autoRun: true })}
                  disabled={captureCount === 0}
                  className="px-4 py-2 bg-[var(--success)] text-white hover:bg-[#15803D] text-xs font-bold uppercase tracking-wider flex items-center gap-1 disabled:opacity-40"
                  data-testid="guided-capture-finish-run-btn"
                >
                  <Check className="w-3.5 h-3.5" /> Done · Run AI Measure
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Iter 79f — inline annotator. Opens on the current step's
          uploaded photo, pre-tagged with the elevation label. On save,
          the annotations get stashed per step-key in `captured[key].
          annotations` and handed to the parent at wizard finish.
          Iter 79j — Now runs in guidedFlow mode: 5-step banner walks
          the contractor through Wall → Window → Mask → Style →
          Profile, then auto-advances to the next capture step. */}
      {annotateOpen && taken?.name && (
        <PhotoAnnotateModal
          open={annotateOpen}
          onClose={() => setAnnotateOpen(false)}
          photoUrl={`/api/uploads/${taken.name}`}
          elevation={step.elevation}
          reference={taken.annotations?.reference || null}
          windowReference={taken.annotations?.windowReference || null}
          zones={taken.annotations?.zones || []}
          targetPin={taken.annotations?.targetPin || null}
          windows={taken.annotations?.windows || []}
          profileBoxes={taken.annotations?.profileBoxes || []}
          onSave={handleAnnotateSave}
          guidedFlow={{
            // Default 5-step sequence baked into PhotoAnnotateModal;
            // pass steps here only to customize.
            onFinish: () => {
              // Iter 79j — on last-step "Save & Continue", advance to
              // the next capture step immediately so the contractor
              // flows: capture → annotate → capture → annotate → …
              // Landing on the last STEPS entry (aerial) fires the
              // Done button chrome instead.
              if (stepIdx < STEPS.length - 1) {
                setStepIdx((i) => i + 1);
              }
            },
            onExit: () => {
              // Contractor wants full manual control — swap modal back
              // to classic mode by clearing our guided-flow flag. Since
              // guidedFlow is derived from the prop, we simulate by
              // closing the modal (contractor can re-open with the
              // header controls) — cleanest exit without re-rendering.
              setAnnotateOpen(false);
              toast.info("Guided mode off — use the header buttons to reopen the annotator manually.");
            },
          }}
        />
      )}
    </div>
  );
}
