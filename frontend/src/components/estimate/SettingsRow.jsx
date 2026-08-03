import React from "react";
import { useT } from "@/lib/i18n";
import { recomputeWasteQtys, recomputeAllWaste } from "@/lib/wasteLogic";
import PorchCeilingsCard from "./PorchCeilingsCard";
import api from "@/lib/api";
import { toast } from "sonner";

/* WALL-HEIGHT ONE-TAP (authorized 2026-07-27): estimate-page field that
   tapes B&B wall heights straight into the batten_wall_heights checklist —
   closing it feeds the batten +height term and retires the standing flag. */
function WallHeightTapeField({ est }) {
  const entry = (est?.lp_flag_checklist || {})["batten_wall_heights"] || {};
  const [val, setVal] = React.useState("");
  const [state, setState] = React.useState(entry.status === "closed" ? "closed" : "open");
  const [savedTotal, setSavedTotal] = React.useState(() => {
    const hs = (entry.values || {}).wall_heights_ft || [];
    return hs.reduce((a, b) => a + Number(b || 0), 0);
  });
  const save = async () => {
    const hs = String(val || "").split(/[,\s]+/).map(Number).filter((n) => n > 0);
    if (!hs.length) { toast.error("Enter taped wall heights in feet, e.g. 9, 9, 18.5"); return; }
    try {
      await api.post(`/estimates/${est.id}/flag-checklist`, {
        code: "batten_wall_heights", action: "close",
        values: { wall_heights_ft: hs },
      });
      setState("closed");
      setSavedTotal(hs.reduce((a, b) => a + b, 0));
      toast.success("Wall heights taped — batten height term feeds the next derivation; flag cleared");
      window.dispatchEvent(new CustomEvent("lp-flag-checklist-changed"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not save wall heights");
    }
  };
  const reopen = async () => {
    try {
      await api.post(`/estimates/${est.id}/flag-checklist`, {
        code: "batten_wall_heights", action: "reopen",
      });
      setState("open");
      toast.success("Flag reopened — batten height term back to 0 pending tape");
      window.dispatchEvent(new CustomEvent("lp-flag-checklist-changed"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not reopen the flag");
    }
  };
  return (
    <div className="mt-4 pt-4 border-t border-[var(--border)]">
      <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
        B&amp;B wall heights (taped) — ORDER stage, not needed to quote
      </div>
      {state === "closed" ? (
        <div className="text-sm" data-testid="wall-height-closed">
          <span className="text-[var(--ink-2)]">Taped — {savedTotal.toFixed(1)} ft total feeds the batten height term.</span>
          <button type="button" className="ml-2 underline text-[11px] uppercase font-bold" onClick={reopen} data-testid="wall-height-reopen">
            Reopen
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <input
            className="input h-9 text-sm w-56"
            placeholder="heights ft, e.g. 9, 9, 18.5, 9"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            data-testid="wall-height-input"
          />
          <button type="button" className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider border border-[var(--border)]" onClick={save} data-testid="wall-height-save">
            Tape it
          </button>
        </div>
      )}
      <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
        Quote sells from the derived (HOVER-SCHEDULE) height — enter taped heights at the house before material order. Taped supersedes derived, reversible; battens re-derive live
      </p>
    </div>
  );
}

export default function SettingsRow({ est, update, save }) {
  const t = useT();
  // TRADE-SPEC SAVE PATH (silent-strip fix, Howard's UI pass 2026-07-30):
  // specs save IMMEDIATELY (no debounce race) and then tell the LP
  // package panel to re-derive so the rename/count is visible live.
  const saveSpec = async (patch) => {
    update(patch);
    if (save) {
      await save({ ...est, ...patch });
      window.dispatchEvent(new Event("lp-flag-checklist-changed"));
      // ONE SHARED REBUILD (ruled 2026-07-31): siding-kind specs re-derive
      // server-side through the same emitter LP uses. The patch rides the
      // call so the rebuild never reads a stale autosave.
      if (est.kind === "siding") {
        try {
          const { data } = await api.post(`/estimates/${est.id}/rederive`, {
            trigger: "spec-save", ...patch,
          });
          if (Array.isArray(data?.lines)) update({ lines: data.lines });
        } catch (e) {
          /* 409 = no measurements yet — spec saved; derives on import */
          if (e?.response?.status !== 409) console.warn("spec-save rederive failed", e);
        }
      }
    }
  };
  // Manual trigger (Howard ruled 2026-07-31): a rule change landing AFTER
  // import reaches a stored estimate only through a control the
  // contractor can press — nothing automatic fires when no spec moved.
  const rederiveNow = async () => {
    try {
      const { data } = await api.post(`/estimates/${est.id}/rederive`, { trigger: "manual" });
      if (Array.isArray(data?.lines)) update({ lines: data.lines });
      const kept = (data?.human_preserved || []).length;
      toast.success(
        `Re-derived from stored measurements${kept ? ` — ${kept} hand-typed qty preserved (yours · derived shown)` : ""}`
      );
      window.dispatchEvent(new Event("lp-flag-checklist-changed"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Re-derive failed");
    }
  };
  const mode = est.pricing_mode || "margin";
  const isMargin = mode === "margin";
  // Iter 78 — Waste % change recomputes line.qty for any cut-prone line
  // that carries a stored raw_qty (i.e. came from a HOVER/Blueprint
  // import). Lines entered manually are untouched.
  const updateWastePct = (newPct) => {
    const lines = recomputeWasteQtys(est?.lines, newPct);
    update({ waste_pct: newPct, lines });
  };
  // Iter 78b — Retroactive recompute for legacy estimates where lines
  // were stored before the cut-prone classifier was fixed. Treats every
  // cut-prone line's current qty as the raw value, stamps raw_qty, and
  // recomputes qty against the current waste %. Gated by confirm() so
  // manual edits don't get clobbered by accident.
  const recomputeAllNow = () => {
    const pct = Number(est?.waste_pct) || 0;
    const count = (est?.lines || []).filter((l) => {
      if (!l) return false;
      const hasRaw = l.raw_qty != null && Number(l.raw_qty) > 0;
      return !hasRaw; // candidate lines that would be stamped
    }).length;
    const ok = window.confirm(
      `Re-bake ${pct}% waste into every cut-prone line on this estimate.\n\n` +
      `This treats each line's current qty as the raw measurement, then ` +
      `applies the waste %.\n\n` +
      `${count} line(s) without a stored raw_qty will be updated. ` +
      `Lines already imported with raw_qty are also recomputed (same ` +
      `effect as changing the % field).\n\n` +
      `Heads-up: any manual qty edits on cut-prone lines (siding, soffit, ` +
      `J-channel, trim, corners, starter) will be treated as raw and bumped ` +
      `by ${pct}%. Continue?`
    );
    if (!ok) return;
    update({ lines: recomputeAllWaste(est?.lines, pct) });
  };
  // Live preview of the multiplier so the contractor knows what %  actually does
  const pct = Math.min(Number(est.margin_pct) || 0, 99);
  const effectiveMultiplier = isMargin
    ? 1 / (1 - pct / 100)
    : 1 + pct / 100;
  // Windows-kind estimates price each opening individually (Vero W×H +
  // Mezzo W×H + per-line install qty), so the % siding waste factor
  // doesn't apply. Hide the card and let Sales Tax + Profit fill the row.
  const showWaste = est.kind !== "windows";

  return (
    <section className={`grid grid-cols-1 ${showWaste ? "lg:grid-cols-3" : "lg:grid-cols-2"} gap-6 mb-6`}>
      {showWaste && (
        <div className="card p-5" data-testid="waste-factor-card">
          <div className="section-tag mb-3">{t("est.wasteFactor")}</div>
          <div className="flex items-baseline gap-2">
            <input
              className="input num w-24"
              type="number"
              step="0.5"
              value={est.waste_pct || 0}
              onChange={(e) => updateWastePct(Number(e.target.value) || 0)}
              data-testid="waste-pct"
            />
            <span className="text-[var(--ink-2)]">{t("est.wasteSuffix")}</span>
          </div>
          <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
            {t("est.wasteHint")}
          </p>
          {/* Iter 78 — Waste is now baked directly into line qty on HOVER /
              Blueprint imports for siding, soffit, J-channel, finish trim,
              corners + starter. Changing the % here recomputes those line
              qtys (raw × 1+waste). Manual lines are untouched. */}
          <p className="mt-1 text-[10px] uppercase tracking-wider text-[var(--success)] font-bold">
            Baked into line qty on import — change % to recompute
          </p>
          {/* Iter 78b — Retroactive recompute button for legacy lines.
              Useful on estimates created before the Iter 78a LP
              cut-prone-classifier fix landed, where qty was stored
              raw and raw_qty=null. One-tap fix that doesn't require
              re-uploading the blueprint. */}
          <button
            type="button"
            className="mt-2 px-3 py-1.5 bg-[var(--surface)] text-[var(--ai)] border border-[var(--ai)] hover:bg-[#FAF5FF] text-[10px] font-bold uppercase tracking-wider"
            onClick={recomputeAllNow}
            data-testid="recompute-all-waste-btn"
            title="Stamp raw_qty + recompute every cut-prone line at the current waste %"
          >
            Recompute waste on existing lines
          </button>
          {/* Iter 78 — LP soffit steering (LP-only). Backend's HOVER spec
              splits LP soffit into Vented (eaves) + Closed (rakes) by
              surface. This knob lets Howard collapse to all-vented or
              all-closed for jobs that only use one style. */}
          {est.kind === "lp_smart" && (
            <div className="mt-4 pt-4 border-t border-[var(--border)]">
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
                LP Soffit type
              </div>
              <select
                className="input h-9 text-sm"
                value={est.lp_soffit_type || "mix"}
                onChange={(e) => update({ lp_soffit_type: e.target.value })}
                data-testid="lp-soffit-type"
              >
                <option value="mix">Mix — Vented on eaves, Closed on rakes (default)</option>
                <option value="vented">Vented — all soffit qty as Vented (38 Series Vented)</option>
                <option value="closed">Closed — all soffit qty as Closed (38 Series Closed)</option>
              </select>
              <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                Applied on HOVER / Blueprint import — collapses or splits the two soffit lines automatically
              </p>
              <WallHeightTapeField est={est} />
            </div>
          )}
          {/* COLOR TIER dropdown REMOVED (Howard ruled 2026-08-02): the
              tier now DERIVES per row from each row's own Material Colors
              picker — one decision, one control. The derived tier shows
              read-only next to each color picker in Job Info. */}
          {/* TRADE-SPEC GROUP (Howard ruled 2026-07-29): roofline + install
              specs the contractor supplies — eave overhang, fascia width,
              shake reveal, batten spacing, porch ceilings. SPECS, not
              CHECKS: the contractor telling the app what he is installing.
              Defaults apply silently — no gate, no flag — the material
              list prints the chosen value on the line. New specs join this
              box; they do not get their own panels. */}
          <div className="mt-4 pt-4 border-t border-[var(--border)]" data-testid="trade-spec-group">
            <div className="flex items-center justify-between mb-2">
              <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold">
                Trade specs
              </div>
              <button
                type="button"
                className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider border border-[var(--border)] hover:bg-[var(--bg-app)]"
                onClick={rederiveNow}
                data-testid="rederive-now-btn"
                title="Replay the current derivation rules over the stored measurements — pulls in rule changes that landed after import. Hand-typed quantities always survive."
              >
                Re-derive material list
              </button>
            </div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2 mt-3">
              {t("est.overhang")}
            </div>
            <div className="flex items-baseline gap-2">
              <input
                className="input num w-24"
                type="number"
                step="1"
                min="0"
                value={est.overhang_in ?? 12}
                onChange={(e) => update({ overhang_in: Number(e.target.value) || 0 })}
                data-testid="overhang-in"
              />
              <span className="text-[var(--ink-2)]">in</span>
            </div>
            <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
              {t("est.overhangHint")}
            </p>
            {(est.kind === "lp_smart" || est.kind === "siding") && (
              /* FASCIA WIDTH (ruled 2026-07-29; R1 extended to siding-kind
                 2026-07-31): on LP it picks the 440 board width; on
                 Vinyl/Ascend it governs the .019 coil divisor — ≤10" the
                 24" roll rips lengthwise for 100 LF, over 10" it covers
                 50 LF. Same spec, every family. */
              <div className="mt-4 pt-4 border-t border-[var(--border)]">
                <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
                  {est.kind === "lp_smart" ? "Fascia width — 440 Series" : "Fascia width"}
                </div>
                <select
                  className="input h-9 text-sm"
                  value={est.fascia_width_in ?? 8}
                  onChange={(e) => saveSpec({ fascia_width_in: Number(e.target.value) })}
                  data-testid="fascia-width-select"
                >
                  <option value={4}>4"</option>
                  <option value={6}>6"</option>
                  <option value={8}>8" (default)</option>
                  <option value={10}>10"</option>
                  <option value={12}>12"</option>
                </select>
                <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                  {est.kind === "lp_smart"
                    ? 'Contractor call-out — no derivation. Picks the 440 board width; the material list prints the width on the line. Re-derives live.'
                    : 'Governs .019 coil coverage: ≤10" the 24" roll rips in half for 100 LF/roll; over 10" one roll covers 50 LF. Re-derives live.'}
                </p>
              </div>
            )}
            {est.kind === "lp_smart" && (
              <>
                {/* BATTEN SPACING (ruled 2026-07-29): 12/16/24 o.c., default
                    12" — 8" retired. The batten line note names the delta
                    when spacing moves off default. */}
                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
                    Batten spacing
                  </div>
                  <select
                    className="input h-9 text-sm"
                    value={est.batten_spacing_in ?? 12}
                    onChange={(e) => saveSpec({ batten_spacing_in: Number(e.target.value) })}
                    data-testid="batten-spacing-select"
                  >
                    <option value={12}>12" o.c. (default)</option>
                    <option value={16}>16" o.c.</option>
                    <option value={24}>24" o.c.</option>
                  </select>
                  <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    Every 48" seam lands on a batten. The 190 Series line note names the spacing
                    and the piece delta vs the 12" default when it moves.
                  </p>
                </div>
                {/* PANEL SIZE (ruled 2026-07-30): 4×10 default (40 ft²) vs
                    4×8 (32 ft²) — changes COUNT and SKU. */}
                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
                    Panel size — 38 Series B&B
                  </div>
                  <select
                    className="input h-9 text-sm"
                    value={est.panel_size ?? "4x10"}
                    onChange={(e) => saveSpec({ panel_size: e.target.value })}
                    data-testid="panel-size-select"
                  >
                    <option value="4x10">4' × 10' (default, 40 ft²)</option>
                    <option value="4x8">4' × 8' (32 ft²)</option>
                  </select>
                  <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    Changes the panel COUNT and the SKU — 4×8 coverage is 32 ft². Re-derives live.
                  </p>
                </div>
                {/* WRAP TRIM WIDTH (ruled 2026-07-30): 540 Series width —
                    name-only, counts unchanged. */}
                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
                    Wrap trim width — 540 Series
                  </div>
                  <select
                    className="input h-9 text-sm"
                    value={est.wrap_trim_width_in ?? 4}
                    onChange={(e) => saveSpec({ wrap_trim_width_in: Number(e.target.value) })}
                    data-testid="wrap-trim-width-select"
                  >
                    <option value={4}>4" (default)</option>
                    <option value={6}>6"</option>
                    <option value={8}>8"</option>
                    <option value={10}>10"</option>
                    <option value={12}>12"</option>
                  </select>
                  <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    Changes ONLY the 540 SKU name (wrap + ISC + frieze scope) — counts stay
                    whole-stick ÷16. Re-derives live.
                  </p>
                </div>
                {/* SHAKE REVEAL (register #4 ruled 2026-07-28): bounded
                    7"–10", default 7" — LP install instructions. */}
                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-2">
                    Shake reveal
                  </div>
                  <div className="flex items-baseline gap-2">
                    <input
                      className="input num w-24"
                      type="number"
                      step="0.125"
                      min="7"
                      max="10"
                      value={est.shake_reveal_in ?? 7}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        if (v >= 7 && v <= 10) saveSpec({ shake_reveal_in: v });
                      }}
                      data-testid="shake-reveal-in"
                    />
                    <span className="text-[var(--ink-2)]">in</span>
                  </div>
                  <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    Bounded 7"–10", default 7" — LP install instructions: "540 Series Trim is recommended
                    when the shake reveal selected ranges between a maximum of 10 inches to a minimum of
                    7 inches". Coverage = 4' × reveal ÷ 12 (panel max 9-7/8"); sealed 15% shake waste applies on top.
                  </p>
                </div>
              </>
            )}
            {/* PHOTO FILL-IN BOXES (Howard ruled 2026-08-01, Three Doors
                step 6): four, PHOTO DOOR ONLY — soffit ft², drip edge LF,
                total trim ft², frieze presence-toggle. Gated on the
                applied blob's door identity: Hover measures these and
                blueprints print them, so the boxes never render there
                (finding 6 — never ask for a number the source gave).
                A box only fills a hole; it never overrides a measured
                value. Frieze is a toggle — its LF derives from the
                measured eave/rake runs, no re-typing. */}
            {est.hover_measurements?._source === "photo" && (() => {
              const pm = est.hover_measurements || {};
              const eaves = Number(pm.eaves_lf) || 0;
              const rakes = Number(pm.rakes_lf) || 0;
              return (
                <div className="mt-4 pt-4 border-t border-[var(--border)]" data-testid="photo-fillins-group">
                  <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold mb-1">
                    Photo fill-ins — what the photos can't see
                  </div>
                  <p className="mb-3 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    Photo door only. A box fills the hole the photos leave — it never
                    overrides a measured value. An UNSET box BLOCKS the quote (scope
                    not set — never $0). Type 0 if the house truly has none. Re-derives live.
                  </p>
                  {[
                    { key: "photo_soffit_sqft", label: "Soffit", unit: "ft²", tid: "photo-soffit-sqft" },
                    { key: "photo_drip_edge_lf", label: "Drip edge", unit: "LF", tid: "photo-drip-edge-lf" },
                    { key: "photo_total_trim_sqft", label: "Total trim", unit: "ft²", tid: "photo-total-trim-sqft" },
                  ].map((f) => (
                    <div key={f.key} className="flex items-center gap-2 mb-2">
                      <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold w-24">{f.label}</span>
                      <input
                        className="input num w-24 h-9"
                        type="number"
                        min="0"
                        step="1"
                        value={est[f.key] ?? ""}
                        onChange={(e) => update({ [f.key]: e.target.value === "" ? null : Number(e.target.value) })}
                        onBlur={() => { if (est[f.key] != null) saveSpec({ [f.key]: Number(est[f.key]) }); }}
                        data-testid={f.tid}
                      />
                      <span className="text-[var(--ink-2)] text-sm">{f.unit}</span>
                      {est[f.key] == null && (
                        <span className="text-[9px] font-bold uppercase tracking-wider text-[#B45309] bg-[#FEF3C7] border border-[#F59E0B] px-1.5 py-0.5" data-testid={`${f.tid}-unset`}>
                          Not set — blocks quote
                        </span>
                      )}
                    </div>
                  ))}
                  <div className="flex items-center gap-2 mt-3">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-bold w-24">Frieze board?</span>
                    <div className="inline-flex border border-[var(--border)] overflow-hidden text-[11px] font-bold uppercase tracking-wider">
                      <button
                        type="button"
                        className={`px-3 py-1.5 transition ${est.photo_frieze_present === true
                          ? "bg-[var(--bar-bg)] text-white"
                          : "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]"}`}
                        onClick={() => saveSpec({ photo_frieze_present: true })}
                        data-testid="photo-frieze-yes"
                      >
                        Yes
                      </button>
                      <button
                        type="button"
                        className={`px-3 py-1.5 transition border-l border-[var(--border)] ${est.photo_frieze_present === false
                          ? "bg-[var(--bar-bg)] text-white"
                          : "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]"}`}
                        onClick={() => saveSpec({ photo_frieze_present: false })}
                        data-testid="photo-frieze-no"
                      >
                        No
                      </button>
                    </div>
                    {est.photo_frieze_present == null && (
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[#B45309] bg-[#FEF3C7] border border-[#F59E0B] px-1.5 py-0.5" data-testid="photo-frieze-unset">
                        Not set — blocks quote
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    Yes/No only — frieze LF derives from the measured runs
                    (level = eaves {eaves.toFixed(0)} LF · sloped = rakes {rakes.toFixed(0)} LF).
                    You never re-type a number the engine already has.
                  </p>
                </div>
              );
            })()}
            {/* Iter 78aj — Porch ceilings live in the trade-spec box; the
                total sqft is summed into the same soffit formula. */}
            <PorchCeilingsCard
              value={est.porch_ceilings || []}
              onChange={(next) => update({ porch_ceilings: next })}
            />
          </div>
        </div>
      )}
      <div className="card p-5">
        <div className="section-tag mb-3">{t("est.salesTax")}</div>
        <label className="flex items-center gap-3 mb-3 text-sm">
          <input
            type="checkbox"
            checked={!!est.tax_enabled}
            onChange={(e) => update({ tax_enabled: e.target.checked })}
            data-testid="tax-toggle"
          />
          <span>{t("est.applyTaxOnMaterial")}</span>
        </label>
        <div className="flex items-baseline gap-2">
          <input
            className="input num w-24"
            type="number"
            step="0.01"
            disabled={!est.tax_enabled}
            value={est.tax_rate || 0}
            onChange={(e) => update({ tax_rate: Number(e.target.value) || 0 })}
            data-testid="tax-rate"
          />
          <span className="text-[var(--ink-2)]">%</span>
        </div>
      </div>
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="section-tag">{t("est.profit")}</div>
          <div
            className="inline-flex border border-[var(--border)] rounded-sm overflow-hidden text-[11px] font-bold uppercase tracking-wider"
            data-testid="pricing-mode-toggle"
          >
            <button
              type="button"
              className={`px-3 py-1.5 transition ${
                isMargin
                  ? "bg-[var(--bar-bg)] text-white"
                  : "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]"
              }`}
              onClick={() => update({ pricing_mode: "margin" })}
              data-testid="pricing-mode-margin"
            >
              {t("est.margin")}
            </button>
            <button
              type="button"
              className={`px-3 py-1.5 transition border-l border-[var(--border)] ${
                !isMargin
                  ? "bg-[var(--bar-bg)] text-white"
                  : "bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[var(--bg-app)]"
              }`}
              onClick={() => update({ pricing_mode: "markup" })}
              data-testid="pricing-mode-markup"
            >
              {t("est.markup")}
            </button>
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <input
            className="input num w-24"
            type="number"
            step="1"
            min="0"
            max={isMargin ? 99 : undefined}
            value={est.margin_pct || 0}
            onChange={(e) => update({ margin_pct: Number(e.target.value) || 0 })}
            data-testid="margin-pct"
          />
          <span className="text-[var(--ink-2)]">
            {isMargin ? t("est.marginSuffix") : t("est.markupSuffix")}
          </span>
        </div>
        <input
          type="range"
          min="0"
          max={isMargin ? 95 : 100}
          step="1"
          value={est.margin_pct || 0}
          onChange={(e) => update({ margin_pct: Number(e.target.value) || 0 })}
          className="w-full accent-[var(--brand)]"
          data-testid="margin-slider"
        />
        <div className="mt-2 text-[11px] text-[var(--muted)] font-mono-num">
          {isMargin ? (
            <>
              Sell = Base ÷ (1 − {pct}%) ={" "}
              <span className="text-[var(--ink)] font-bold">
                ×{effectiveMultiplier.toFixed(3)}
              </span>
            </>
          ) : (
            <>
              Sell = Base × (1 + {pct}%) ={" "}
              <span className="text-[var(--ink)] font-bold">
                ×{effectiveMultiplier.toFixed(3)}
              </span>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
