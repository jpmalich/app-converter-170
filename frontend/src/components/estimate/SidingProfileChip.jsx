// PROFILE SELECTION WORKS ON EVERY DOOR (Howard ruled 2026-08-09):
// blueprint, Hover, or photo — the siding profile is chosen ON THE
// ESTIMATE, never gated behind a measurement run, an elevation render,
// or any door-specific artifact. And A DEFAULTED PROFILE PRINTS AS
// DEFAULTED: until the contractor chooses, the card says the profile
// was assumed, names it, and points here.
// The swap MOVES the derived quantity to the chosen row and leaves an
// accounting note on both rows — a removal with no accounting fails.
import React, { useState } from "react";
import { Layers, AlertTriangle, Check } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useT } from "@/lib/i18n";
import SurfaceAccessChip from "@/components/estimate/SurfaceAccessChip";

const SECTION = "Vinyl Siding";
const DEFAULT_NAME = 'Charter Oak Standard color Dutch Lap 4.5" .046';

export const SidingProfileChip = ({ est, catalog, update, save }) => {
  const t = useT();
  const [open, setOpen] = useState(false);
  // Non-siding estimates: the profile control does not apply here (the
  // whole kind uses a different picker). Not a gate to explain.
  if (!est || (est.kind || "siding") !== "siding") return null;
  const lines = (est.lines || []).filter(
    (l) => (l.tab || "vinyl") === "vinyl" && l.section === SECTION
  );
  const choice = est.siding_profile_choice || null;
  const chosenLine = choice ? lines.find((l) => l.name === choice.name) : null;
  const defaultLine = lines.find((l) => l.name === DEFAULT_NAME);
  const carrier = lines.find((l) => (l.qty || 0) > 0) || defaultLine;
  // P0 chip (Howard ruled 2026-08-13 pro-quotes reply 3): a SurfaceAccessChip
  // stands in when no carrier line exists (blueprint/HOVER-sourced estimates
  // without a vinyl-siding takeoff yet). Names the state and the way out.
  if (!carrier) {
    return (
      <SurfaceAccessChip
        state="Siding profile — needs a takeoff with vinyl-siding rows"
        wayOut="apply a takeoff that carries a vinyl-siding row, then choose the profile here"
        testid="sp-chip-no-carrier"
        className="mb-2"
      />
    );
  }
  const stale = !!(choice && (!chosenLine || (chosenLine.qty || 0) === 0) && carrier && carrier.name !== choice.name);
  const defaulted = !choice && carrier.name === DEFAULT_NAME && (carrier.qty || 0) > 0;

  const options = (() => {
    const sec = (catalog || []).find((s) => s.title === SECTION);
    return sec ? sec.items || [] : [];
  })();

  const choose = async (name) => {
    const stamp = { name, at: new Date().toISOString() };
    let nextLines;
    if (name === carrier.name) {
      nextLines = (est.lines || []).map((l) =>
        l === carrier
          ? { ...l, note: `${(l.note || "").replace(/ · PROFILE DEFAULTED[^·]*/, "")} · PROFILE CHOSEN`.trim() }
          : l
      );
    } else {
      const qty = carrier.qty || 0;
      const rawQty = carrier.raw_qty ?? null;
      const baseNote = (carrier.note || "").replace(/ · PROFILE DEFAULTED[^·]*/, "").trim();
      let placed = false;
      nextLines = (est.lines || []).map((l) => {
        if (l === carrier) {
          return { ...l, qty: 0, raw_qty: 0, qty_src: "human",
                   note: `${baseNote} · PROFILE MOVED → ${name} (qty ${qty} carried over)`.trim() };
        }
        if ((l.tab || "vinyl") === "vinyl" && l.section === SECTION && l.name === name) {
          placed = true;
          return { ...l, qty, raw_qty: rawQty, qty_src: "human",
                   note: `${baseNote} · PROFILE CHOSEN — qty moved from ${carrier.name}`.trim() };
        }
        return l;
      });
      if (!placed) {
        const it = options.find((o) => o.name === name) || {};
        nextLines = [...nextLines, {
          tab: "vinyl", section: SECTION, name, unit: it.unit || "SQ",
          mat: it.mat, lab: it.lab, qty, raw_qty: rawQty, qty_src: "human",
          note: `${baseNote} · PROFILE CHOSEN — qty moved from ${carrier.name}`.trim(),
        }];
      }
    }
    update({ lines: nextLines, siding_profile_choice: stamp });
    await save({ ...est, lines: nextLines, siding_profile_choice: stamp });
    setOpen(false);
  };

  return (
    <div className="mb-2">
      {defaulted && (
        <button type="button" onClick={() => setOpen(true)} data-testid="sp-chip-defaulted"
          className="w-full flex items-start gap-1.5 border px-2 py-1.5 text-left text-[11px] leading-snug bg-[#FFFBEB] text-[#92400E] border-[#FCD34D] hover:bg-[#FEF3C7]">
          <AlertTriangle className="w-3.5 h-3.5 mt-[1px] shrink-0" />
          <span>{t("sp.defaulted", { name: carrier.name, qty: String(carrier.qty || 0) })}</span>
        </button>
      )}
      {choice && !stale && (
        <button type="button" onClick={() => setOpen(true)} data-testid="sp-chip-chosen"
          className="w-full flex items-start gap-1.5 border px-2 py-1.5 text-left text-[11px] leading-snug bg-[var(--surface-muted)] text-[var(--ink-2)] border-[var(--border)] hover:bg-[var(--surface)]">
          <Check className="w-3.5 h-3.5 mt-[1px] shrink-0" />
          <span>{t("sp.chosen", { name: choice.name })}</span>
        </button>
      )}
      {stale && (
        <button type="button" onClick={() => setOpen(true)} data-testid="sp-chip-stale"
          className="w-full flex items-start gap-1.5 border px-2 py-1.5 text-left text-[11px] leading-snug bg-[#FEF2F2] text-[#B91C1C] border-[#FCA5A5] hover:bg-[#FEE2E2]">
          <AlertTriangle className="w-3.5 h-3.5 mt-[1px] shrink-0" />
          <span>{t("sp.stale", { name: choice.name, carrier: carrier.name })}</span>
        </button>
      )}
      {!defaulted && !choice && (
        <button type="button" onClick={() => setOpen(true)} data-testid="sp-choose-btn"
          className="flex items-center gap-1.5 border px-2 py-1 text-[11px] bg-[var(--surface-muted)] border-[var(--border)] hover:bg-[var(--surface)]">
          <Layers className="w-3.5 h-3.5" />
          <span>{t("sp.choose")}</span>
        </button>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-sm">{t("sp.pickTitle")}</DialogTitle>
          </DialogHeader>
          <div className="max-h-[50vh] overflow-y-auto space-y-1">
            {options.map((it, i) => (
              <button key={it.name} type="button" onClick={() => choose(it.name)}
                data-testid={`sp-option-${i}`}
                className={`w-full flex items-center justify-between gap-2 border px-2 py-1.5 text-left text-[12px] hover:bg-[var(--surface-muted)] ${
                  it.name === carrier.name ? "border-[var(--ink-2)]" : "border-[var(--border)]"}`}>
                <span>{it.name}</span>
                <span className="font-mono-num shrink-0">
                  ${Number((it.mat || 0) + (it.lab || 0)).toFixed(2)}/{it.unit || "SQ"}
                </span>
              </button>
            ))}
            {options.length === 0 && (
              <div className="text-[11px] text-[var(--muted)]" data-testid="sp-no-options">{t("sp.none")}</div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SidingProfileChip;
