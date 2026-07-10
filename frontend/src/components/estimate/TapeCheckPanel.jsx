// Iter 79j.65 — Tape Check panel: persistent per-wall ground truth +
// accumulating accuracy history.
//
// The contractor tapes each wall / dormer once; values persist on the
// estimate (`estimates.tape_check`) as ground-truth fixtures — not
// transient scoring inputs. Every AI Measure run can be scored against
// the tape: per-wall Δ, pass/amber/fail chips, and a house-level
// accuracy % that accumulates in a history table (the accuracy
// artifact for supplier pitches).
//
// Verdicts (backend-computed): |Δ| ≤ 0.5 ft pass · ≤ 1.0 amber · > 1.0 fail.
import React, { useEffect, useState } from "react";
import { Ruler, Loader2, ChevronDown, ChevronRight, Check, AlertTriangle, X, FileText } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const WALLS = ["front", "back", "left", "right"];

const VerdictChip = ({ verdict, delta }) => {
  if (!verdict) return null;
  const cfg = {
    pass: { bg: "#DCFCE7", fg: "#166534", bd: "#16A34A", Icon: Check },
    amber: { bg: "#FEF3C7", fg: "#92400E", bd: "#F59E0B", Icon: AlertTriangle },
    fail: { bg: "#FEE2E2", fg: "#991B1B", bd: "#DC2626", Icon: X },
  }[verdict];
  return (
    <span
      className="inline-flex items-center gap-0.5 text-[9px] font-bold px-1 py-0.5 border font-mono-num tabular-nums"
      style={{ background: cfg.bg, color: cfg.fg, borderColor: cfg.bd }}
    >
      <cfg.Icon className="w-2.5 h-2.5" />
      {delta > 0 ? "+" : ""}{delta}
    </span>
  );
};

// Iter 79j.68 — measurement mode per wall (from the scored run's trace).
// Over multiple houses this tag shows which mode earns its keep — the
// evidence base for making exposure entry a required capture step.
const MODE_CFG = {
  count: { label: "count", title: "Count-derived: lap courses × contractor exposure — plane-correct by construction", fg: "#166534", bg: "#DCFCE7" },
  pixel: { label: "px", title: "Pixel-derived: scaled from a reference bar's px-per-inch", fg: "#475569", bg: "#F1F5F9" },
  "cross-plane": { label: "x-plane", title: "Cross-plane scale: vertical ref borrowed from a different wall plane — verify (control case: same plane = exact; cross-plane = +45%)", fg: "#92400E", bg: "#FEF3C7" },
};

// Iter 79j.77 — accuracy trend sparkline. Floor: renders ONLY with ≥3
// scored runs (2 points is a line, not a trend) and always sits next to
// the current score, never alone.
const AccuracySparkline = ({ history }) => {
  if (!history || history.length < 3) return null;
  const pts = history.slice().reverse().map((h) => h.accuracy_pct); // chronological
  const W = 56, H = 14, PAD = 2;
  const lo = Math.min(...pts), hi = Math.max(...pts);
  const span = hi - lo || 1;
  const xy = pts.map((v, i) => [
    PAD + (i * (W - 2 * PAD)) / (pts.length - 1),
    H - PAD - ((v - lo) / span) * (H - 2 * PAD),
  ]);
  const d = xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [lx, ly] = xy[xy.length - 1];
  const trendUp = pts[pts.length - 1] >= pts[0];
  return (
    <svg
      width={W} height={H} viewBox={`0 0 ${W} ${H}`}
      className="inline-block align-middle"
      data-testid="tape-check-sparkline"
      aria-label={`Accuracy trend across ${pts.length} runs: ${pts.join("%, ")}%`}
    >
      <title>{pts.map((p) => `${p}%`).join(" → ")}</title>
      <polyline points={d} fill="none" stroke={trendUp ? "#16A34A" : "#DC2626"} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="1.8" fill={trendUp ? "#16A34A" : "#DC2626"} />
    </svg>
  );
};

const ModeTag = ({ mode }) => {
  const cfg = MODE_CFG[mode];
  if (!cfg) return null;
  return (
    <span
      className="text-[8px] font-bold uppercase tracking-wider px-1 py-0.5"
      style={{ color: cfg.fg, background: cfg.bg }}
      title={cfg.title}
    >
      {cfg.label}
    </span>
  );
};

export default function TapeCheckPanel({ estimateId, runId, facades, dormers }) {
  const [expanded, setExpanded] = useState(false);
  const [tape, setTape] = useState({ front: "", back: "", left: "", right: "" });
  // Iter 79j.76 — stepped walls: on unfinished-grade new construction the
  // siding start-line staircases, so a wall can carry two corner-to-corner
  // readings. start line (grade / foundation top / brick ledge / siding
  // start) is recorded so counts with different references don't fight.
  const [tape2, setTape2] = useState({ front: "", back: "", left: "", right: "" });
  const [steppedW, setSteppedW] = useState({ front: false, back: false, left: false, right: false });
  const [startRef, setStartRef] = useState("");
  const [tapeDormers, setTapeDormers] = useState({}); // face → width string
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!estimateId) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/estimates/${estimateId}/tape-check`);
        if (cancelled) return;
        const w = data.walls || {};
        const t1 = {}, t2 = {}, st = {};
        let sr = "";
        WALLS.forEach((k) => {
          const v = w[k];
          if (v && typeof v === "object") {
            const segs = v.segments || [];
            t1[k] = segs[0]?.height_ft ?? "";
            t2[k] = segs[1]?.height_ft ?? "";
            st[k] = segs.length > 1;
            if (v.start_ref) sr = v.start_ref;
          } else {
            t1[k] = v ?? "";
            t2[k] = "";
            st[k] = false;
          }
        });
        setTape(t1); setTape2(t2); setSteppedW(st);
        if (sr) setStartRef(sr);
        const dd = {};
        (data.dormers || []).forEach((d) => { dd[d.face] = d.width_ft; });
        setTapeDormers(dd);
        setHistory((data.history || []).slice().reverse());
        if ((data.history || []).length > 0 || Object.values(w).some((v) => v != null)) {
          setExpanded(true);
        }
      } catch { /* no estimate / no tape yet */ }
      finally { if (!cancelled) setLoaded(true); }
    })();
    return () => { cancelled = true; };
  }, [estimateId]);

  // The 3D model migrates dormer faces to slope-relative ("slope-left");
  // tape storage + backend scoring use the raw AI vocabulary ("left").
  // Strip the prefix so keys line up.
  const normFace = (f) => (f || "").toLowerCase().replace(/^slope-/, "");
  const dormerFaces = (dormers || []).map((d) => normFace(d.face)).filter(Boolean);
  const latest = history[0] || null;

  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/estimates/${estimateId}/tape-check`, {
        walls: Object.fromEntries(WALLS.map((k) => {
          if (tape[k] === "") return [k, null];
          const seg1 = { height_ft: Number(tape[k]) };
          if (steppedW[k] && tape2[k] !== "") {
            const obj = { segments: [seg1, { height_ft: Number(tape2[k]) }] };
            if (startRef) obj.start_ref = startRef;
            return [k, obj];
          }
          if (startRef) return [k, { segments: [seg1], start_ref: startRef }];
          return [k, Number(tape[k])];
        })),
        dormers: Object.entries(tapeDormers)
          .filter(([, v]) => v !== "" && v != null)
          .map(([face, width_ft]) => ({ face, width_ft: Number(width_ft) })),
      });
      toast.success("Tape values saved — they persist on this estimate");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save tape values");
    } finally { setBusy(false); }
  };

  const score = async () => {
    setBusy(true);
    try {
      await save();
      const { data } = await api.post(`/estimates/${estimateId}/tape-check/score`, { run_id: runId || null });
      setHistory((prev) => [data.entry, ...prev.filter((h) => h.run_id !== data.entry.run_id)]);
      toast.success(`Run scored: ${data.entry.accuracy_pct}% accuracy`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to score run");
    } finally { setBusy(false); }
  };

  const downloadReport = async () => {
    setBusy(true);
    try {
      const { data } = await api.get(`/estimates/${estimateId}/tape-check/report-pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "accuracy-report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to build the accuracy report");
    } finally { setBusy(false); }
  };

  if (!estimateId) return null;
  return (
    <div className="p-3 bg-[var(--surface)] border border-[var(--border)] space-y-2" data-testid="tape-check-panel">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between text-left"
        data-testid="tape-check-toggle"
      >
        <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold inline-flex items-center gap-1.5">
          <Ruler className="w-3 h-3" /> Tape Check — ground truth
        </span>
        <span className="inline-flex items-center gap-2">
          <AccuracySparkline history={history} />
          {latest && (
            <span className="text-[10px] font-bold font-mono-num tabular-nums text-[var(--ink)]" data-testid="tape-check-accuracy">
              {latest.accuracy_pct}%
            </span>
          )}
          {expanded ? <ChevronDown className="w-3 h-3 text-[var(--muted)]" /> : <ChevronRight className="w-3 h-3 text-[var(--muted)]" />}
        </span>
      </button>
      {expanded && loaded && (
        <>
          <div className="text-[10px] text-[var(--muted)] leading-snug">
            Enter taped eave heights (ft). Values persist on this estimate and every run scores against them.
            Use <b>⇢</b> when a wall's start-line steps (stepped foundation) — the AI scores against the segment range.
          </div>
          <div className="flex items-center gap-2 text-[10px]">
            <span className="text-[var(--muted)] uppercase text-[9px] font-bold tracking-wider">Start line</span>
            <select
              value={startRef}
              onChange={(e) => setStartRef(e.target.value)}
              className="px-1 py-0.5 border border-[var(--border)] text-[10px] bg-white"
              data-testid="tape-check-start-ref"
            >
              <option value="">— not recorded —</option>
              <option value="grade">grade</option>
              <option value="foundation_top">foundation top</option>
              <option value="brick_ledge">brick ledge</option>
              <option value="siding_start">siding start</option>
            </select>
          </div>
          {WALLS.map((w) => {
            const f = (facades || []).find((x) => x.id === w);
            const row = latest?.walls?.[w];
            return (
              <div key={w} className="flex items-center gap-2 text-[11px]">
                <span className="text-[var(--muted)] w-12 uppercase text-[9px] font-bold tracking-wider">{w}</span>
                <span className="w-14 font-mono-num tabular-nums text-[var(--ink-2)]" title="AI read">
                  {f ? `${Number(f.eaveHeight).toFixed(1)}′` : "—"}
                </span>
                <input
                  type="number" step="0.01" min="1" max="60"
                  placeholder="tape"
                  value={tape[w]}
                  onChange={(e) => setTape((t) => ({ ...t, [w]: e.target.value }))}
                  className="w-18 px-1.5 py-0.5 border border-[var(--border)] font-mono-num text-right text-[11px]"
                  style={{ width: "4.5rem" }}
                  data-testid={`tape-check-input-${w}`}
                />
                <button
                  type="button"
                  onClick={() => setSteppedW((s) => ({ ...s, [w]: !s[w] }))}
                  className={`px-1 py-0.5 text-[10px] border ${steppedW[w] ? "bg-[var(--ai)] text-white border-[var(--ai)]" : "text-[var(--muted)] border-[var(--border)]"}`}
                  title="Stepped wall — add a second corner-to-corner reading"
                  data-testid={`tape-check-stepped-toggle-${w}`}
                >
                  ⇢
                </button>
                {steppedW[w] && (
                  <input
                    type="number" step="0.01" min="1" max="60"
                    placeholder="seg 2"
                    value={tape2[w]}
                    onChange={(e) => setTape2((t) => ({ ...t, [w]: e.target.value }))}
                    className="px-1.5 py-0.5 border border-[var(--border)] font-mono-num text-right text-[11px]"
                    style={{ width: "4.5rem" }}
                    data-testid={`tape-check-input2-${w}`}
                  />
                )}
                <span data-testid={`tape-check-verdict-${w}`} className="inline-flex items-center gap-1">
                  {row?.imputed ? (
                    <span
                      className="text-[9px] font-bold px-1 py-0.5 border"
                      style={{ background: "#F1F5F9", color: "#475569", borderColor: "#CBD5E1" }}
                      title="No valid AI read for this wall in the scored run — the pipeline imputed a placeholder. Excluded from scoring."
                      data-testid={`tape-check-imputed-${w}`}
                    >
                      unread
                    </span>
                  ) : (
                    <VerdictChip verdict={row?.verdict} delta={row?.delta} />
                  )}
                  {row?.stepped && (
                    <span className="text-[9px] text-[var(--muted)]" title={`scored against range ${Math.min(...(row.tape_segments || [0]))}–${Math.max(...(row.tape_segments || [0]))} ft`}>
                      ⇢ range
                    </span>
                  )}
                  {row?.mode && <span data-testid={`tape-check-mode-${w}`}><ModeTag mode={row.mode} /></span>}
                </span>
              </div>
            );
          })}
          {dormerFaces.map((face) => {
            const row = (latest?.dormers || []).find((d) => d.face === face);
            return (
              <div key={face} className="flex items-center gap-2 text-[11px]">
                <span className="text-[var(--muted)] w-12 uppercase text-[9px] font-bold tracking-wider" title="Dormer width">{face} drm</span>
                <span className="w-14 font-mono-num tabular-nums text-[var(--ink-2)]">
                  {(() => { const d = (dormers || []).find((x) => normFace(x.face) === face); return d?._aiWidthFt != null ? `${Number(d._aiWidthFt).toFixed(1)}′` : "—"; })()}
                </span>
                <input
                  type="number" step="0.01" min="1" max="60"
                  placeholder="tape"
                  value={tapeDormers[face] ?? ""}
                  onChange={(e) => setTapeDormers((t) => ({ ...t, [face]: e.target.value }))}
                  className="px-1.5 py-0.5 border border-[var(--border)] font-mono-num text-right text-[11px]"
                  style={{ width: "4.5rem" }}
                  data-testid={`tape-check-dormer-input-${face}`}
                />
                <span data-testid={`tape-check-dormer-verdict-${face}`}>
                  <VerdictChip verdict={row?.verdict} delta={row?.delta} />
                </span>
              </div>
            );
          })}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={save}
              disabled={busy}
              className="px-2.5 py-1 bg-[var(--surface)] text-[var(--ink-2)] border border-[var(--border)] hover:bg-[var(--surface-muted)] text-[10px] font-bold uppercase tracking-wider disabled:opacity-50"
              data-testid="tape-check-save"
            >
              Save tape
            </button>
            <button
              type="button"
              onClick={score}
              disabled={busy}
              className="px-2.5 py-1 bg-[var(--ai)] text-white hover:opacity-90 text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1 disabled:opacity-50"
              data-testid="tape-check-score"
            >
              {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
              Score this run
            </button>
            {history.length > 0 && (
              <button
                type="button"
                onClick={downloadReport}
                disabled={busy}
                className="px-2.5 py-1 bg-[var(--surface)] text-[var(--ink-2)] border border-[var(--border)] hover:bg-[var(--surface-muted)] text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1 disabled:opacity-50"
                title="Accuracy report PDF — development-fixture curve labeled as methodology exhibit; held-out blind runs are the only accuracy claim"
                data-testid="tape-check-report-pdf"
              >
                <FileText className="w-3 h-3" />
                Accuracy PDF
              </button>
            )}
          </div>
          {history.length > 0 && (
            <div className="pt-1 space-y-1" data-testid="tape-check-history">
              <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold">Accuracy history</div>
              {history.slice(0, 8).map((h) => (
                <div key={h.run_id + h.scored_at} className="text-[10px] text-[var(--ink-2)]">
                  <div className="flex items-center justify-between">
                    <span className="font-mono-num tabular-nums">{(h.scored_at || "").slice(0, 10)}</span>
                    <span className="truncate mx-1 text-[var(--muted)]" style={{ maxWidth: "6rem" }}>{h.model}</span>
                    <span className="font-mono-num tabular-nums">
                      <b>{h.accuracy_pct}%</b>
                      <span className="text-[#16A34A] ml-1">{h.passes}✓</span>
                      <span className="text-[#B45309] ml-0.5">{h.ambers}⚠</span>
                      <span className="text-[#B91C1C] ml-0.5">{h.fails}✗</span>
                    </span>
                  </div>
                  {/* Iter 79j.68 — per-wall measurement mode. Legacy
                      entries (scored before modes existed) skip this. */}
                  {Object.values(h.walls || {}).some((r) => r.mode) && (
                    <div className="flex items-center gap-1 mt-0.5 pl-1" data-testid={`tape-check-history-modes-${h.run_id}`}>
                      {WALLS.filter((w) => h.walls?.[w]).map((w) => (
                        <span key={w} className="inline-flex items-center gap-0.5">
                          <span className="text-[8px] uppercase text-[var(--muted)]">{w[0]}</span>
                          <ModeTag mode={h.walls[w].mode} />
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
