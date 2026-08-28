// SEND-142 (Howard ruled 2026-08-27) — THE RAIL SPLIT. The editor's right
// column was one 300-line block; it is now three panels in three files.
// SAME DATA, SAME BUTTONS, SAME confirm / refuse / pull-in. No new field,
// no new formula, no new call: every figure still arrives from the server's
// own quantities and every decision still lives in the editor.
import React from "react";

import { CATEGORIES, SIDING } from "./marks";

export const QuantitiesPanel = ({ qty }) => (
  <>
            {/* QUANTITIES */}
            <div className="p-3 border-b border-[var(--border)]">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">Live quantities — confirmed marks only</div>
              {/* NAME THE PLANE (SEND-136). Printed wherever the quantity
                  appears. UNKNOWN is the honest starting state — never a
                  default that reads as square-on. */}
              <div className="mb-1.5 p-1.5 border text-[10px] leading-snug"
                style={{
                  borderColor: qty?.plane_basis === "SQUARE-ON" ? "var(--success)" : qty?.plane_basis === "OBLIQUE" ? "#DC2626" : "#F59E0B",
                  background: qty?.plane_basis === "SQUARE-ON" ? "#ECFDF5" : qty?.plane_basis === "OBLIQUE" ? "#FEF2F2" : "#FEF3C7",
                }}
                data-testid="photo-takeoff-plane-basis">
                <b className="uppercase tracking-wider">Plane: {qty?.plane_basis || "UNKNOWN"}</b>
                <div className="mt-0.5 text-[var(--ink-2)]">{qty?.plane_basis_reason || "reading this photo's marks…"}</div>
              </div>
              <div className="grid grid-cols-2 gap-1 text-[11px]">
                <div>Siding</div><div className="font-bold text-right" data-testid="photo-takeoff-qty-siding">{qty?.siding_sqft ?? "—"} {qty?.siding_sqft != null ? "ft²" : ""}</div>
                <div>Non-siding</div><div className="font-bold text-right" data-testid="photo-takeoff-qty-nonsiding">{qty?.non_siding_sqft ?? "—"} {qty?.non_siding_sqft != null ? "ft²" : ""}</div>
                <div>Openings</div><div className="font-bold text-right" data-testid="photo-takeoff-qty-opening-count">{qty?.opening_count ?? "—"}</div>
                <div>Opening ft²</div><div className="font-bold text-right" data-testid="photo-takeoff-qty-opening-sqft">{qty?.opening_sqft ?? "—"}</div>
                {/* SEND-139 — the gable and dormer lanes. A lane with
                    nothing measured shows an em dash, never a 0. */}
                <div>Gable ft²</div><div className="font-bold text-right" data-testid="photo-takeoff-qty-gable">{qty?.gable_sqft ?? "—"} {qty?.gable_sqft != null ? "ft²" : ""}</div>
                <div>Dormer face ft²</div><div className="font-bold text-right" data-testid="photo-takeoff-qty-dormer-face">{qty?.dormer_face_sqft ?? "—"} {qty?.dormer_face_sqft != null ? "ft²" : ""}</div>
                <div>Dormer cheeks ft²</div><div className="font-bold text-right" data-testid="photo-takeoff-qty-dormer-cheeks">{qty?.dormer_cheek_sqft ?? "—"} {qty?.dormer_cheek_sqft != null ? "ft²" : ""}</div>
              </div>
              {qty?.gable_basis_note && (
                <div className="mt-1.5 text-[9px] text-[var(--success)] font-bold leading-snug" data-testid="photo-takeoff-gable-basis">
                  {qty.gable_basis_note}
                </div>
              )}
              {qty?.non_siding_by_category && (
                <div className="mt-1.5 flex flex-wrap gap-1" data-testid="photo-takeoff-qty-by-category">
                  {Object.entries(qty.non_siding_by_category).map(([k, v]) => (
                    <span key={k} className="text-[9px] font-bold px-1.5 py-0.5" style={{ background: `${CATEGORIES.find((c) => c.key === k)?.color || "#DC2626"}22`, color: CATEGORIES.find((c) => c.key === k)?.color || "#DC2626" }}>{k} {v} ft²</span>
                  ))}
                </div>
              )}
              {qty?.siding_by_product && (
                <div className="mt-1.5 flex flex-wrap gap-1" data-testid="photo-takeoff-qty-by-product">
                  {Object.entries(qty.siding_by_product).map(([k, v]) => (
                    <span key={k} className="text-[9px] font-bold px-1.5 py-0.5" style={{ background: `${SIDING}22`, color: SIDING }}>{k} · {v} ft²</span>
                  ))}
                  {qty.siding_no_product_sqft != null && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 bg-[#FEF3C7] text-[var(--warning-text)]">no product assigned · {qty.siding_no_product_sqft} ft²</span>
                  )}
                </div>
              )}
              {[qty?.provisional_note, qty?.openings_note, qty?.openings_without_extent_note,
                qty?.guidance_confirmed_note, ...(qty?.gable_refusals || []),
                ...(qty?.gable_pitch_warnings || []), ...(qty?.dormer_refusals || []),
                ...(qty?.product_basis_notes || [])].filter(Boolean).map((n, i) => (
                <div key={i} className="mt-1.5 text-[10px] text-[var(--warning-text)] leading-snug" data-testid={`photo-takeoff-refusal-${i}`}>· {n}</div>
              ))}
            </div>
  </>
);

export default QuantitiesPanel;
