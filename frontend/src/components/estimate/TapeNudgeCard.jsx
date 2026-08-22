// SEND-109 — THE TAPE-ENTRY NUDGE (the refusal coach reaching the
// material that motivated Ruling V).
// Renders on any estimate whose gutter rows REFUSE for want of a
// verified wall height (not_derivable_code = RULING_V_NO_VERIFIED_HEIGHT).
// One field tape — FIRST FLOOR → TOP OF PLATE, the derivation band —
// un-refuses every one of them on the next re-derive.
// Doctrine held: ECHO BEFORE COMMIT (a misparsed tape is a fabricated
// measurement wearing the best provenance in the system); the tape lands
// through the real door (POST /pdf-overlay/tape), then the shared rebuild
// runs through /rederive and the surface refreshes.
import React, { useMemo, useState } from "react";
import { Loader2, Ruler } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const RULING_V_CODE = "RULING_V_NO_VERIFIED_HEIGHT";
const FACES = ["front", "back", "left", "right"];

export default function TapeNudgeCard({ est, onRederived }) {
  const refused = useMemo(
    () =>
      (est?.lines || []).filter(
        (l) =>
          l?.not_derivable_code === RULING_V_CODE ||
          // rows stored before the machine code existed: the only refusal
          // source on the gutter section is Ruling V (verified-height want)
          (l?.not_derivable && l?.section === "Seamless Gutter")
      ),
    [est?.lines]
  );
  const [face, setFace] = useState("front");
  const [text, setText] = useState("");
  const [echo, setEcho] = useState(null);
  const [busy, setBusy] = useState(false);

  if (!refused.length) return null;

  const checkTape = async () => {
    if (!text.trim()) return;
    setBusy(true);
    setEcho(null);
    try {
      const { data } = await api.post(`/estimates/${est.id}/pdf-overlay/tape/parse`, { text });
      if (!data.ok) {
        toast.error(data.reason || "Could not read that tape — try 9'-2\" or 9.17");
      } else {
        setEcho(data);
      }
    } catch {
      toast.error("Tape check failed — try again.");
    } finally {
      setBusy(false);
    }
  };

  const commitTape = async () => {
    setBusy(true);
    try {
      await api.post(`/estimates/${est.id}/pdf-overlay/tape`, {
        face_id: face,
        text,
        ref_from: "first_floor_line",
        ref_to: "top_of_plate_line",
      });
      await api.post(`/estimates/${est.id}/rederive`, {});
      toast.success(`Tape recorded on ${face} — re-derived. Refused rows resolve from your tape.`);
      setEcho(null);
      setText("");
      onRederived?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not commit the tape — try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      data-testid="ruling-v-tape-nudge"
      className="card p-4 mb-4 border border-amber-400/50 bg-amber-50/60"
    >
      <div className="flex items-start gap-3">
        <Ruler className="w-5 h-5 mt-0.5 text-amber-600 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-[var(--ink-1,#1a1a1a)]">
            {refused.length} gutter {refused.length === 1 ? "row is" : "rows are"} refusing —
            they need one verified wall height
          </div>
          <div className="text-xs text-[var(--ink-2,#555)] mt-1">
            {refused.map((l) => l.name).join(" · ")} — no tape and no derived
            plate chain on this job. One field tape (FIRST FLOOR → TOP OF
            PLATE) un-refuses all of them. Nothing is guessed in the meantime.
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <select
              data-testid="tape-nudge-face-select"
              className="border rounded px-2 py-1.5 text-sm bg-white"
              value={face}
              onChange={(e) => { setFace(e.target.value); setEcho(null); }}
              disabled={busy}
            >
              {FACES.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
            <input
              data-testid="tape-nudge-input"
              className="border rounded px-2 py-1.5 text-sm w-32 bg-white"
              placeholder={'e.g. 9\'-2"'}
              value={text}
              onChange={(e) => { setText(e.target.value); setEcho(null); }}
              disabled={busy}
            />
            {!echo ? (
              <button
                data-testid="tape-nudge-check-btn"
                className="btn btn-sm bg-amber-600 hover:bg-amber-700 text-white rounded px-3 py-1.5 text-sm inline-flex items-center gap-1.5 disabled:opacity-50"
                onClick={checkTape}
                disabled={busy || !text.trim()}
              >
                {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                Check tape
              </button>
            ) : (
              <>
                <span data-testid="tape-nudge-echo" className="text-xs font-mono text-amber-800">
                  {echo.echo} → {echo.value_ft} ft on {face}
                </span>
                <button
                  data-testid="tape-nudge-commit-btn"
                  className="btn btn-sm bg-emerald-700 hover:bg-emerald-800 text-white rounded px-3 py-1.5 text-sm inline-flex items-center gap-1.5 disabled:opacity-50"
                  onClick={commitTape}
                  disabled={busy}
                >
                  {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  Commit tape &amp; re-derive
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
