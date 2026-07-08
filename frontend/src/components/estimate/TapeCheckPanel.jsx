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
import { Ruler, Loader2, ChevronDown, ChevronRight, Check, AlertTriangle, X } from "lucide-react";
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

export default function TapeCheckPanel({ estimateId, runId, facades, dormers }) {
  const [expanded, setExpanded] = useState(false);
  const [tape, setTape] = useState({ front: "", back: "", left: "", right: "" });
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
        setTape({
          front: w.front ?? "", back: w.back ?? "",
          left: w.left ?? "", right: w.right ?? "",
        });
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
        walls: Object.fromEntries(WALLS.map((k) => [k, tape[k] === "" ? null : Number(tape[k])])),
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
                <span data-testid={`tape-check-verdict-${w}`}>
                  <VerdictChip verdict={row?.verdict} delta={row?.delta} />
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
          </div>
          {history.length > 0 && (
            <div className="pt-1 space-y-1" data-testid="tape-check-history">
              <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] font-bold">Accuracy history</div>
              {history.slice(0, 8).map((h) => (
                <div key={h.run_id + h.scored_at} className="flex items-center justify-between text-[10px] text-[var(--ink-2)]">
                  <span className="font-mono-num tabular-nums">{(h.scored_at || "").slice(0, 10)}</span>
                  <span className="truncate mx-1 text-[var(--muted)]" style={{ maxWidth: "6rem" }}>{h.model}</span>
                  <span className="font-mono-num tabular-nums">
                    <b>{h.accuracy_pct}%</b>
                    <span className="text-[#16A34A] ml-1">{h.passes}✓</span>
                    <span className="text-[#B45309] ml-0.5">{h.ambers}⚠</span>
                    <span className="text-[#B91C1C] ml-0.5">{h.fails}✗</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
