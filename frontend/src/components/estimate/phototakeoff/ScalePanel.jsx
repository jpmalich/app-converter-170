// SEND-142 (Howard ruled 2026-08-27) — THE RAIL SPLIT. The editor's right
// column was one 300-line block; it is now three panels in three files.
// SAME DATA, SAME BUTTONS, SAME confirm / refuse / pull-in. No new field,
// no new formula, no new call: every figure still arrives from the server's
// own quantities and every decision still lives in the editor.
import React from "react";
import { AlertTriangle, Ruler } from "lucide-react";

export const ScalePanel = ({
  sc, scale, qty, setTool, setScaleDraft, clearScale,
  tapeFt, setTapeFt, tapeIn, setTapeIn, commitTape,
}) => (
  <>
            {/* SCALE */}
            <div className="p-3 border-b border-[var(--border)]">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1 flex items-center gap-1"><Ruler className="w-3 h-3" /> Scale — this photo only</div>
              {sc ? (
                <div className="text-[11px] font-bold text-[var(--success)]" data-testid="photo-takeoff-scale-basis">
                  ✓ {sc.basis === "tape" ? "TAPE GOVERNS" : "TWO-TAP ANCHOR"} — {(sc.ipp * 12).toFixed(3)} ft per 12 px span
                  {scale?.tape_inches && scale?.anchor?.inches ? " · the anchor figure is kept, the tape wins" : ""}
                </div>
              ) : (
                <div className="text-[11px] font-bold text-[var(--warning-text)] flex items-start gap-1" data-testid="photo-takeoff-scale-refusal">
                  <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  {qty?.scale_refusal || "No scale on this photo — no quantity, and no zero is shown in its place."}
                </div>
              )}
              <div className="flex items-center gap-1 mt-2">
                <button type="button" onClick={() => { setTool("scale"); setScaleDraft(null); }}
                  className="px-2 py-1 border border-[var(--ai)] text-[var(--ai)] text-[10px] font-bold uppercase"
                  data-testid="photo-takeoff-scale-start">two-tap span</button>
                {scale && (
                  <button type="button" onClick={clearScale} className="px-2 py-1 border border-[var(--border)] text-[10px] font-bold uppercase text-[var(--muted)]" data-testid="photo-takeoff-scale-clear">clear</button>
                )}
              </div>
              {scale?.anchor && (
                <div className="mt-2">
                  <div className="text-[9px] uppercase tracking-wider font-bold text-[var(--muted)]">Tape figure for that same span — the tape wins</div>
                  <div className="flex items-center gap-1 mt-1">
                    <input value={tapeFt} onChange={(e) => setTapeFt(e.target.value)} placeholder="ft" inputMode="decimal"
                      className="w-14 border border-[var(--border)] px-1.5 py-1 text-[11px]" data-testid="photo-takeoff-tape-ft" />
                    <input value={tapeIn} onChange={(e) => setTapeIn(e.target.value)} placeholder="in" inputMode="decimal"
                      className="w-14 border border-[var(--border)] px-1.5 py-1 text-[11px]" data-testid="photo-takeoff-tape-in" />
                    <button type="button" onClick={commitTape} className="px-2 py-1 bg-[var(--ai)] text-white text-[10px] font-bold uppercase" data-testid="photo-takeoff-tape-commit">set tape</button>
                  </div>
                </div>
              )}
            </div>
  </>
);

export default ScalePanel;
