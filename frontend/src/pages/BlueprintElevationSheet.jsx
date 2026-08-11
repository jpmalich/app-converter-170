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
    </div>
  );
}
