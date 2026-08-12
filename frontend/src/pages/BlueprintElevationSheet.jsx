import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { SheetSvg } from "@/pages/ElevationSheet";

/* BLUEPRINT ELEVATION — PHASE 1 (Howard ordered 2026-08-10).
   SYNTHETIC elevation rendered from the blueprint model via
   GET /estimates/:id/blueprint-elevation/:which — reuses SheetSvg
   UNCHANGED (same sheet contract as the photo door). Honesty carries
   onto the drawing: a wall the read cannot draw shows a hatched
   NEEDS-YOUR-TAPE panel instead of a guessed rectangle. */

const SHEETS = ["front", "left", "back", "right"];

export default function BlueprintElevationSheet() {
  const { id, which = "front" } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    setData(null);
    setErr("");
    if (!SHEETS.includes(which)) {
      setErr("Unknown elevation");
      return;
    }
    api.get(`/estimates/${id}/blueprint-elevation/${which}`)
      .then(({ data }) => setData(data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load sheet"));
  }, [id, which]);

  if (err) return <div className="p-8 text-sm" data-testid="bp-elevation-error">{err}</div>;
  if (!data) return <div className="p-8 text-sm" data-testid="bp-elevation-loading">Rendering blueprint sheet…</div>;

  const drawable = data.wall && data.wall.width_ft != null && data.wall.height_ft != null;

  return (
    <div className="min-h-screen bg-[#e8eaee] py-6 flex flex-col items-center" data-testid="bp-elevation-page">
      <div className="mb-3 flex items-center gap-4 print:hidden">
        {/* Ruled 2026-08-11 send-3: "Back to takeoff" first — the sheet
            is opened while grading a read; the takeoff is one level
            back, the estimate two levels. */}
        <Link
          to={`/estimate/${id}?open=takeoff`}
          className="text-xs underline font-bold"
          data-testid="bp-elevation-back-to-takeoff"
        >
          ← Back to the takeoff
        </Link>
        <Link to={`/estimate/${id}`} className="text-xs underline" data-testid="bp-elevation-back">← Back to estimate</Link>
        {SHEETS.map((s) => (
          <Link key={s} to={`/estimate/${id}/blueprint-elevation/${s}`}
            className={`text-xs underline ${s === which ? "font-bold" : ""}`}
            data-testid={`bp-elevation-nav-${s}`}>{s}</Link>
        ))}
        <button type="button" className="text-xs underline" onClick={() => window.print()} data-testid="bp-elevation-print">Print</button>
      </div>
      <div className="mb-2 px-3 py-1.5 bg-[#1a2332] text-white text-[11px] rounded" data-testid="bp-elevation-synthetic-note">
        {data.synthetic_note}
      </div>
      {data.hatch_needs_tape && (
        <div className="mb-3 max-w-2xl w-full border-2 border-dashed border-amber-600 bg-amber-50 text-amber-900 text-xs font-bold px-4 py-3 rounded"
          style={{ backgroundImage: "repeating-linear-gradient(45deg, transparent, transparent 8px, rgba(180,83,9,0.08) 8px, rgba(180,83,9,0.08) 16px)" }}
          data-testid="bp-elevation-needs-tape">
          NEEDS YOUR TAPE — {data.hatch_needs_tape}
        </div>
      )}
      {drawable ? (
        <SheetSvg data={data} />
      ) : (
        <div className="max-w-2xl w-full border border-[#c9ced8] bg-white p-6 text-sm" data-testid="bp-elevation-not-drawable">
          <div className="font-bold mb-2">{data.sheet_code} · {which.toUpperCase()} — NOT DRAWN</div>
          <div className="text-xs text-[#5a6472]">
            The blueprint read does not carry enough evidenced geometry to draw this wall honestly.
            Nothing is guessed onto a drawing. {data.geometry_basis?.walls}
          </div>
        </div>
      )}
      {/* PHASE 2 disclosures (Howard ruled 2026-08-11 send-5 item 3):
          renderer-only — the reads behind these were never wrong.
          Every panel below is a disclosure of what the read carries
          that the SVG cannot fit inside one drawing. */}
      {(data.wall?.segments || data.wall?.step_note) && (
        <div className="mt-3 max-w-2xl w-full border border-[#c9ced8] bg-white p-4 text-xs" data-testid="bp-elevation-segments-panel">
          <div className="font-bold text-[11px] uppercase tracking-wider mb-2">Stepped wall — segments</div>
          {data.wall.step_note && (
            <div className="text-[11px] text-[#3a4453] mb-2">{data.wall.step_note}</div>
          )}
          {Array.isArray(data.wall.segments) && (
            <ul className="space-y-1">
              {data.wall.segments.map((seg, i) => (
                <li key={i} className="flex items-baseline gap-2" data-testid={`bp-elevation-segment-${i}`}>
                  <span className="font-mono-num font-bold w-40">{seg.name}</span>
                  <span className="font-mono-num">{seg.width_label} × {seg.height_label}</span>
                  {seg.needs_tape && (
                    <span className="text-amber-800 font-bold text-[10px]">⚠ NEEDS YOUR TAPE</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {Array.isArray(data.wall?.area_components) && data.wall.area_components.length > 0 && (
        <div className="mt-3 max-w-2xl w-full border border-[#c9ced8] bg-white p-4 text-xs" data-testid="bp-elevation-area-panel">
          <div className="font-bold text-[11px] uppercase tracking-wider mb-2">Wall area — gable-honest</div>
          <ul className="space-y-1">
            {data.wall.area_components.map((c, i) => (
              <li key={i} className="flex items-baseline gap-2 font-mono-num">
                <span className="w-40">{c.name}</span>
                <span>{c.sqft} sqft</span>
                <span className="text-[10px] text-[#5a6472]">({c.kind})</span>
              </li>
            ))}
          </ul>
          {typeof data.wall.area_sqft === "number" && (
            <div className="mt-2 font-bold font-mono-num" data-testid="bp-elevation-area-total">
              total (known): {data.wall.area_sqft} sqft
            </div>
          )}
          {Array.isArray(data.wall.area_missing) && data.wall.area_missing.length > 0 && (
            <div className="mt-2 text-[11px] text-amber-800" data-testid="bp-elevation-area-missing">
              <div className="font-bold uppercase tracking-wider">Missing (needs tape / not derivable):</div>
              <ul className="list-disc pl-4">
                {data.wall.area_missing.map((m, i) => (<li key={i}>{m}</li>))}
              </ul>
            </div>
          )}
        </div>
      )}
      {Array.isArray(data.wall?.wing_triangle_notes) && data.wall.wing_triangle_notes.length > 0 && (
        <div className="mt-3 max-w-2xl w-full border border-[#c9ced8] bg-white p-4 text-xs" data-testid="bp-elevation-wing-triangles">
          <div className="font-bold text-[11px] uppercase tracking-wider mb-2">Wing gables attributed to this wall</div>
          <ul className="space-y-2">
            {data.wall.wing_triangle_notes.map((w, i) => (
              <li key={i} className="border-l-2 border-[#c9ced8] pl-2" data-testid={`bp-elevation-wing-triangle-${i}`}>
                <div className="font-mono-num font-bold">plane: {w.plane} · count: {w.count}</div>
                <div className="font-mono-num">base: {w.base_ft ? `${w.base_ft} ft` : "—"} · <span className="text-[10px]">source: {w.base_source}</span></div>
                <div className="font-mono-num">height: <span className="text-amber-800">{w.height_source}</span></div>
                <div className="text-[10px] text-[#5a6472]">{w.note}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.porch_note && (
        <div className="mt-3 max-w-2xl w-full border border-[#c9ced8] bg-white p-4 text-xs" data-testid="bp-elevation-porch-note">
          <div className="font-bold text-[11px] uppercase tracking-wider mb-2">Porch</div>
          <div className="font-mono-num">ceiling: {data.porch_note.ceiling_sqft || "—"} sqft</div>
          <div className="text-[11px] text-[#5a6472] mt-1">{data.porch_note.attachment_wall_source}</div>
          <div className="text-[10px] text-amber-800 mt-1 italic">{data.porch_note.phase_1_status}</div>
        </div>
      )}
    </div>
  );
}
