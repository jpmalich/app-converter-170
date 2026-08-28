// SEND-142 (Howard ruled 2026-08-27) — THE RAIL SPLIT. The editor's right
// column was one 300-line block; it is now three panels in three files.
// SAME DATA, SAME BUTTONS, SAME confirm / refuse / pull-in. No new field,
// no new formula, no new call: every figure still arrives from the server's
// own quantities and every decision still lives in the editor.
import React from "react";
import { Ban, Check, Download, Move, Trash2 } from "lucide-react";

import { GABLE_PITCH_PRESETS, pitchOutOfRange } from "@/lib/gableMath";
import { DORMER, GABLE, kindLabel, markColor } from "./marks";

export const MarksPanel = ({
  marks, selectedId, setSelectedId, busy, products, productsNote,
  sqftOf, qtyCell, receiptFor, gDims, ft2,
  patchMark, delMark, importAnnotations, toggleSymmetric, applyGablePitch,
}) => (
  <>
            {/* MARKS */}
            <div className="p-3 flex-1">
              <div className="flex items-center justify-between mb-1.5">
                <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)]">Marks ({marks.length})</div>
                <button type="button" onClick={importAnnotations} disabled={busy}
                  className="inline-flex items-center gap-1 px-2 py-1 border border-[var(--border)] text-[9px] font-bold uppercase text-[var(--ink-2)] disabled:opacity-50"
                  data-testid="photo-takeoff-import-btn"><Download className="w-3 h-3" /> pull in what I already drew</button>
              </div>
              {marks.length === 0 && (
                <div className="text-[11px] text-[var(--muted)] italic" data-testid="photo-takeoff-marks-empty">
                  No marks on this photo yet — pick a tool and trace the wall.
                </div>
              )}
              {marks.map((m) => {
                const a = sqftOf(m);
                return (
                  <div key={m.id}
                    className={`border p-1.5 mb-1 cursor-pointer ${m.id === selectedId ? "border-[var(--ai)]" : "border-[var(--border)]"}`}
                    onClick={() => setSelectedId(m.id === selectedId ? null : m.id)}
                    data-testid={`photo-takeoff-mark-row-${m.id}`}>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[11px] font-bold" style={{ color: markColor(m) }}>{kindLabel(m)}</span>
                      <span className="text-[10px] font-bold">
                        {qtyCell(m, a)}
                      </span>
                    </div>
                    <div className="text-[9px] uppercase tracking-wider font-bold" style={{ color: m.status === "confirmed" ? "var(--success)" : m.status === "refused" ? "var(--muted)" : "var(--warning-text)" }}>
                      {m.status}
                    </div>
                    {/* PROVENANCE NEVER LAUNDERS — the badge says which the
                        mark carries, and a confirm does not rewrite it. */}
                    <div className="text-[9px] font-bold uppercase tracking-wider" data-testid={`photo-takeoff-origin-${m.id}`}
                      style={{ color: m.origin === "ai_proposal" ? "var(--ai)" : m.status === "confirmed" && m.confirmed_after_ai_read ? "var(--success)" : "var(--warning-text)" }}>
                      {m.origin === "ai_proposal" ? "AI PROPOSAL"
                        : m.confirmed_after_ai_read ? "EVIDENCE"
                          : m.status === "confirmed" ? "GUIDANCE-CONFIRMED" : "GUIDANCE"}
                      {m.origin === "imported_annotation" ? " · imported" : ""}
                    </div>
                    {(m.confirmed_basis || m.basis) && (
                      <div className="text-[9px] text-[var(--muted)] leading-snug" data-testid={`photo-takeoff-basis-${m.id}`}>
                        {m.confirmed_basis || m.basis}
                      </div>
                    )}
                    {m.style && <div className="text-[9px] text-[var(--ink-2)]">{m.style}{m.height_in ? ` · ${m.height_in}" h` : ""}{m.width_in ? ` · ${m.width_in}" w` : ""}</div>}
                    {m.product && (
                      <div className="text-[9px] text-[var(--ink-2)]" data-testid={`photo-takeoff-product-of-${m.id}`}>
                        product: {m.product}
                        {m.confirmed_under_product && m.confirmed_under_product !== m.product
                          ? ` · confirmed under ${m.confirmed_under_product} — the geometry did not change; the output did` : ""}
                      </div>
                    )}
                    {m.refused_reason && <div className="text-[9px] text-[var(--muted)] leading-snug">{m.refused_reason}</div>}
                    {/* SEND-140 — THE REFUSAL RECEIPT. One contractor
                        sentence, written by the server from the ACTUAL
                        missing field, saying what to tape. A measured
                        gable and a counted cheek carry none. */}
                    {receiptFor(m.id) && (
                      <div className="mt-0.5 text-[10px] font-bold text-[var(--warning-text)] leading-snug"
                        data-testid={`photo-takeoff-receipt-${m.id}`}>
                        {receiptFor(m.id)}
                      </div>
                    )}
                    <div className="flex items-center gap-1 mt-1">
                      <button type="button" onClick={(e) => { e.stopPropagation(); patchMark(m.id, { status: "confirmed" }); }}
                        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 border border-[var(--success)] text-[var(--success)] text-[9px] font-bold uppercase"
                        data-testid={`photo-takeoff-confirm-${m.id}`}><Check className="w-3 h-3" /> confirm</button>
                      <button type="button" onClick={(e) => { e.stopPropagation(); patchMark(m.id, { status: "refused", refused_reason: "refused by the contractor" }); }}
                        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 border border-[var(--border)] text-[var(--muted)] text-[9px] font-bold uppercase"
                        data-testid={`photo-takeoff-refuse-${m.id}`}><Ban className="w-3 h-3" /> refuse</button>
                      <button type="button" onClick={(e) => { e.stopPropagation(); setSelectedId(m.id); }}
                        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 border border-[var(--border)] text-[var(--ink-2)] text-[9px] font-bold uppercase"
                        data-testid={`photo-takeoff-adjust-${m.id}`}><Move className="w-3 h-3" /> adjust</button>
                      <button type="button" onClick={(e) => { e.stopPropagation(); delMark(m.id); }}
                        className="ml-auto text-[var(--danger)]" data-testid={`photo-takeoff-delete-${m.id}`}><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                    {m.id === selectedId && (
                      <div className="mt-1.5 pt-1.5 border-t border-[var(--border)]" onClick={(e) => e.stopPropagation()}>
                        {m.kind === "gable" || m.kind === "dormer" ? (
                          /* SEND-139 — THE ANNOTATOR'S OWN FIELDS, PORTED.
                             Gable: symmetric + pitch (preset or typed).
                             Dormer: typed depth for the cheeks. Nothing
                             new was invented for either tool. */
                          (() => {
                            const d = gDims(m);
                            if (m.kind === "gable") {
                              return (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-bold" style={{ color: GABLE }} data-testid={`photo-takeoff-gable-dims-${m.id}`}>
                                    {d && d.baseFt !== undefined
                                      ? `${d.baseFt.toFixed(1)} ft × ${d.riseFt.toFixed(1)} ft rise · ½ × w × rise = ${ft2(d.grossAreaFt)}`
                                      : "no scale on this photo — width and rise have no feet, so there is no area (refused, not 0)"}
                                    {d?.pitch != null ? ` · pitch ${d.pitch}/12` : ""}
                                  </div>
                                  {d && pitchOutOfRange(d.pitch) && (
                                    <div className="text-[9px] font-bold text-[var(--warning-text)]" data-testid={`photo-takeoff-gable-pitch-warning-${m.id}`}>
                                      pitch {d.pitch}/12 is outside the usual 3/12–18/12 range — check the tapped points
                                    </div>
                                  )}
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <label className="flex items-center gap-1 text-[10px]">
                                      <input type="checkbox" checked={!!m.symmetric}
                                        onChange={() => toggleSymmetric(m)}
                                        data-testid={`photo-takeoff-gable-symmetric-${m.id}`} />
                                      Symmetric gable
                                    </label>
                                    <select value={GABLE_PITCH_PRESETS.includes(m.pitch_set) ? String(m.pitch_set) : ""}
                                      onChange={(e) => { const v = Number(e.target.value); if (v) applyGablePitch(m, v); }}
                                      className="text-[10px] border border-[var(--border)] px-1 py-0.5"
                                      title="Selecting a pitch moves the peak (rise = base/2 × pitch/12). Dragging the peak re-derives the pitch."
                                      data-testid={`photo-takeoff-gable-pitch-${m.id}`}>
                                      <option value="">pitch {d?.pitch != null ? `${d.pitch}/12` : "—"}</option>
                                      {GABLE_PITCH_PRESETS.map((v) => <option key={v} value={v}>{v}/12</option>)}
                                    </select>
                                    <input type="number" min="1" max="24" step="0.5" placeholder="custom"
                                      className="w-16 text-[10px] border border-[var(--border)] px-1 py-0.5"
                                      onKeyDown={(e) => { if (e.key === "Enter") { const v = Number(e.target.value); if (v > 0) applyGablePitch(m, v); } }}
                                      data-testid={`photo-takeoff-gable-pitch-custom-${m.id}`} />
                                  </div>
                                  <div className="text-[9px] text-[var(--muted)]">
                                    Moving the peak or the eaves is a geometry change — a confirmed gable goes back to provisional and is re-confirmed.
                                  </div>
                                </div>
                              );
                            }
                            return (
                              <div className="space-y-1">
                                <div className="text-[10px] font-bold" style={{ color: DORMER }} data-testid={`photo-takeoff-dormer-dims-${m.id}`}>
                                  {d && d.widthFt !== undefined
                                    ? `${d.widthFt.toFixed(1)} ft × ${d.heightFt.toFixed(1)} ft = ${ft2(d.grossAreaFt)} face`
                                    : "no scale on this photo — no feet, no area (refused, not 0)"}
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <label className="text-[10px] text-[var(--muted)] font-bold" htmlFor={`ptd-${m.id}`}>Depth (ft)</label>
                                  <input id={`ptd-${m.id}`} type="number" min="0" step="0.1" inputMode="decimal"
                                    defaultValue={m.depth_ft ?? ""}
                                    onBlur={(e) => { const v = parseFloat(e.target.value); if (v > 0 && v !== m.depth_ft) patchMark(m.id, { depth_ft: v }); }}
                                    className="w-16 text-[10px] border border-[var(--border)] px-1 py-0.5"
                                    data-testid={`photo-takeoff-dormer-depth-${m.id}`} />
                                  {m.depth_ft && d?.heightFt !== undefined ? (
                                    <span className="text-[10px] font-bold" style={{ color: DORMER }} data-testid={`photo-takeoff-dormer-cheeks-${m.id}`}>
                                      + cheeks 2 × {d.heightFt.toFixed(1)}×{Number(m.depth_ft).toFixed(1)} = {ft2(2 * d.heightFt * Number(m.depth_ft))}
                                    </span>
                                  ) : (
                                    <span className="text-[10px] font-bold text-[var(--warning-text)]" data-testid={`photo-takeoff-dormer-cheeks-refused-${m.id}`}>
                                      cheeks REFUSED — depth is measured on the roof, never read off the photo. No default depth.
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })()
                        ) : m.kind === "opening" ? (
                          <div className="flex flex-wrap items-center gap-1">
                            <input defaultValue={m.style || ""} placeholder="window style"
                              onBlur={(e) => { const v = e.target.value.trim(); if (v !== (m.style || "")) patchMark(m.id, { style: v }); }}
                              className="flex-1 min-w-[110px] border border-[var(--border)] px-1.5 py-1 text-[10px]"
                              data-testid="photo-takeoff-style-input" />
                            <input defaultValue={m.height_in ?? ""} placeholder="h in" inputMode="decimal"
                              onBlur={(e) => { const v = parseFloat(e.target.value); if (v > 0 && v !== m.height_in) patchMark(m.id, { height_in: v }); }}
                              className="w-14 border border-[var(--border)] px-1.5 py-1 text-[10px]"
                              data-testid="photo-takeoff-height-in" />
                            <input defaultValue={m.width_in ?? ""} placeholder="w in" inputMode="decimal"
                              onBlur={(e) => { const v = parseFloat(e.target.value); if (v > 0 && v !== m.width_in) patchMark(m.id, { width_in: v }); }}
                              className="w-14 border border-[var(--border)] px-1.5 py-1 text-[10px]"
                              data-testid="photo-takeoff-width-in" />
                            <span className="text-[9px] text-[var(--muted)] w-full">Style and height are GUIDANCE for the read — the ft² comes from the box you drew and this photo's scale.</span>
                          </div>
                        ) : (
                          <div>
                            <select value={m.product || ""} disabled={products.length === 0}
                              onChange={(e) => patchMark(m.id, { product: e.target.value })}
                              className="w-full border border-[var(--border)] px-1.5 py-1 text-[10px] disabled:opacity-50"
                              data-testid="photo-takeoff-product-select">
                              <option value="">{products.length ? "— no product assigned —" : "— none on this job —"}</option>
                              {products.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
                            </select>
                            <span className="text-[9px] text-[var(--muted)]">
                              {products.length
                                ? "Changing the product does NOT redraw or unconfirm the zone — the swap is recorded with the ft² at that moment."
                                : (productsNote || "no body-siding product on this job yet")}
                            </span>
                            {(m.product_history || []).length > 0 && (
                              <div className="mt-1 text-[9px] text-[var(--muted)]" data-testid={`photo-takeoff-product-history-${m.id}`}>
                                {m.product_history.map((h, i) => (
                                  <div key={i}>{h.from || "—"} → {h.to || "—"} · {h.sqft_at_swap ?? "—"} ft² · {String(h.at).slice(0, 16).replace("T", " ")} · {h.by || "unknown"}</div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
  </>
);

export default MarksPanel;
