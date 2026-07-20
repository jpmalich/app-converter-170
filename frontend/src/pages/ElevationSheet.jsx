import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";

/* Dimensioned 2D Elevation Sheet — LIVE RENDER, EL-1..EL-4 (front/left/back/right).
   Replicates approved mock v3 anatomy; every value is DATA-BOUND from
   GET /estimates/:id/elevation-sheet/:which (no hand-typed constants).
   Stepped walls: EACH tape segment draws its own basis line — step location
   is NOT TAPED (indicative). Chase: annotated, never scale-rendered.
   CHANNELS: linework color = COMPONENT CLASS · chips/boxes = SOURCE/STATUS. */

const C = {
  ink: "#1a2332", muted: "#5a6472", siding: "#475569", trim: "#DC2626",
  osc: "#0D9488", isc: "#DB2777", fascia: "#0EA5E9", soffit: "#6B4423",
  starter: "#1F2937", band: "#86198F", green: "#0d7a3f", amber: "#b45309",
};

const SHEETS = ["front", "left", "back", "right"];

const Chip = ({ x, y, w, label, kind }) => {
  const styles = {
    taped: { fill: C.green, text: "#fff" },
    "taped-derived": { fill: C.green, text: "#fff", dash: true },
    "ai-ok": { fill: "#fff", text: C.green, stroke: C.green },
    "ai-warn": { fill: C.amber, text: "#fff" },
    est: { fill: "#fff", text: C.amber, stroke: C.amber, dash: true },
  }[kind] || { fill: "#fff", text: C.ink, stroke: C.ink };
  return (
    <g>
      <rect x={x} y={y} width={w} height={16} rx={8} fill={styles.fill}
        stroke={styles.stroke || (styles.dash ? "#fff" : "none")}
        strokeWidth={styles.stroke || styles.dash ? 1.2 : 0}
        strokeDasharray={styles.dash ? "3 2" : undefined} />
      <text x={x + w / 2} y={y + 11.5} fontSize="8" textAnchor="middle"
        fill={styles.text} fontWeight="bold">{label}</text>
    </g>
  );
};

const tagKind = (tag) =>
  tag === "TAPED" ? "taped" : tag === "TAPED-DERIVED" ? "taped-derived"
    : tag === "AI-READ ✓" ? "ai-ok" : tag === "AI-READ ⚠" ? "ai-warn" : "est";

export default function ElevationSheet() {
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
    api.get(`/estimates/${id}/elevation-sheet/${which}`)
      .then(({ data }) => setData(data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load sheet"));
  }, [id, which]);

  if (err) return <div className="p-8 text-sm" data-testid="elevation-sheet-error">{err}</div>;
  if (!data) return <div className="p-8 text-sm" data-testid="elevation-sheet-loading">Rendering sheet…</div>;

  return (
    <div className="min-h-screen bg-[#e8eaee] py-6 flex flex-col items-center" data-testid="elevation-sheet-page">
      <div className="mb-3 flex items-center gap-4 print:hidden">
        <Link to={`/estimate/${id}`} className="text-xs underline" data-testid="elevation-sheet-back">← Back to estimate</Link>
        <button type="button" className="text-xs underline" onClick={() => window.print()} data-testid="elevation-sheet-print">Print</button>
        <Link to={`/estimate/${id}/elevation-sheets/print`} className="text-xs underline" data-testid="elevation-sheet-print-all">Print all 4 sheets</Link>
      </div>
      <SheetSvg data={data} />
    </div>
  );
}

// Reusable sheet renderer — ONE SVG per sheet payload. The print package
// (`ElevationSheetsPrint`) reuses this verbatim, so printed sheets are
// IDENTICAL to the on-screen sheets by construction.
export function SheetSvg({ data }) {
  const W = data.wall;
  const segList = W.segments || null;
  const stepped = !!(segList && segList.length > 1);
  const gableFt = W.gable_triangle_ft || 0;
  // ── drawing math (auto-fit BOTH axes, spec §5) ───────────────────
  const wallBottom = 520, drawable = 820.8, maxDrawH = 300;
  const ppf = Math.min(drawable / W.width_ft, maxDrawH / (W.height_ft + gableFt));
  const wallW = W.width_ft * ppf;
  const wallX = 90 + (drawable - wallW) / 2;
  const wallRight = wallX + wallW;
  const wallTop = wallBottom - W.height_ft * ppf;
  // stepped: seg[0] left half, seg[1] right half — step at midpoint is
  // INDICATIVE ONLY (location untaped), annotated on-sheet
  const stepX = stepped ? wallX + wallW / 2 : null;
  const segTopY = stepped
    ? segList.map((s) => wallBottom - s.height_ft * ppf)
    : [wallTop];
  const topRefY = Math.min(...segTopY);
  const apexY = topRefY - gableFt * ppf;
  const ovFt = (W.overhang_in || 12) / 12;
  const scaleInPerFt = ppf / 96;
  const fracs = [[1 / 8, '1/8"'], [5 / 32, '5/32"'], [3 / 16, '3/16"'], [1 / 4, '1/4"'], [3 / 8, '3/8"']];
  const scaleLabel = fracs.reduce((a, b) =>
    Math.abs(b[0] - scaleInPerFt) < Math.abs(a[0] - scaleInPerFt) ? b : a)[1];

  // wall outline: rectangle, or stepped polygon (per-segment tops)
  const outline = stepped
    ? `M ${wallX} ${wallBottom} L ${wallX} ${segTopY[0]} L ${stepX} ${segTopY[0]} L ${stepX} ${segTopY[1]} L ${wallRight} ${segTopY[1]} L ${wallRight} ${wallBottom} Z`
    : null;

  // course hatch (true courses — field-countable), per segment on steps
  const courseLines = [];
  if (W.exposure_in) {
    const halves = stepped
      ? segList.map((s, i) => ({ courses: s.courses, top: segTopY[i],
          x1: i === 0 ? wallX : stepX, x2: i === 0 ? stepX : wallRight }))
      : (W.courses ? [{ courses: W.courses, top: wallTop, x1: wallX, x2: wallRight }] : []);
    for (const h of halves) {
      for (let i = 1; i < h.courses; i++) {
        const y = wallBottom - i * (W.exposure_in / 12) * ppf;
        if (y > h.top + 2) courseLines.push({ y, x1: h.x1 + 1.5, x2: h.x2 - 1.5 });
      }
    }
  }

  // clad-surface siding marker (ruled 2026-07-19): every clad shape carries
  // the wall's course hatch. Outline = basis channel; fill = component.
  const hatchYs = [];
  if (W.exposure_in) {
    const step = (W.exposure_in / 12) * ppf;
    for (let y = wallBottom - step; y > 60; y -= step) hatchYs.push(y);
  }

  // openings geometry (sill-less openings draw dashed at mid-band — the
  // vertical position is NOT derivable without a door anchor)
  const ops = (data.openings || []).map((o) => {
    if (o.center_ft == null || !o.width_in || !o.height_in) return { ...o, drawable: false };
    const w = (o.width_in / 12) * ppf;
    const h = (o.height_in / 12) * ppf;
    const x = wallX + o.center_ft * ppf - w / 2;
    const noSill = o.sill_in == null;
    const bottom = noSill
      ? (wallBottom + topRefY) / 2 + h / 2
      : wallBottom - (o.sill_in / 12) * ppf;
    return { ...o, drawable: true, noSill, x, y: bottom - h, w, h, cx: wallX + o.center_ft * ppf };
  });

  // opening-center dimension chain segments
  const chain = [wallX, ...ops.filter((o) => o.drawable).map((o) => o.cx), wallRight];
  const segs = [];
  for (let i = 1; i < chain.length; i++) {
    const ft = (chain[i] - chain[i - 1]) / ppf;
    segs.push({ x: (chain[i] + chain[i - 1]) / 2, label: fmtFt(ft) });
  }

  const dev = data.deviation;
  const chase = data.chase;
  const collisions = data.collisions || [];
  const anyCollision = ops.some((o) => o.collision);
  const bubbleY = Math.max(topRefY - 55, 208);
  const chaseBoxH = chase && chase.ai_band ? 62 : 58;
  const collisionBoxY = chase ? 150 + chaseBoxH + 6 : 150;
  // chase locator glyph (BACK) — dims TAPED to scale; position ratified
  // door-relative (ruled 2026-07-19) or bound from run chase-corner
  // reads. COLLISION GUARD: a suppressed chase draws NO geometry — the
  // deviation-style callout + wall-data note carry it instead.
  const chaseG = chase && !chase.suppressed && chase.center_ft != null
    ? {
        cx: wallX + chase.center_ft * ppf,
        w: chase.width_in ? (chase.width_in / 12) * ppf : 26,
        top: chase.height_in ? wallBottom - (chase.height_in / 12) * ppf : wallTop - 34,
        taped: !!chase.width_in,
      }
    : null;
  // annotation labels stay legible: fascia label re-centers on the wider
  // clear span when the chase occludes the wall band (occlusion rule)
  const fasciaLabelX = chaseG
    ? ((wallRight - (chaseG.cx + chaseG.w / 2)) > ((chaseG.cx - chaseG.w / 2) - wallX)
        ? (chaseG.cx + chaseG.w / 2 + wallRight) / 2
        : (wallX + chaseG.cx - chaseG.w / 2) / 2)
    : (wallX + wallRight) / 2;
  // chase PROFILE (sides) — dims TAPED, anchored at the back corner
  const prof = data.chase_profile;
  const profW = prof ? (prof.depth_in / 12) * ppf : 0;
  const profTop = prof ? wallBottom - (prof.height_in / 12) * ppf : 0;
  const profX = prof ? (data.sheet === "left" ? wallX - profW : wallRight) : 0;
  // seg basis lines step outward past the profile when it occupies a side
  const dimOffL = prof && data.sheet === "left" ? profW : 0;
  const dimOffR = prof && data.sheet === "right" ? profW : 0;
  // chase CAP over ridge (front) — render only when geometry supports it
  const cap = data.chase_cap && data.chase_cap.visible ? data.chase_cap : null;
  const capG = cap
    ? {
        cx: wallX + cap.center_ft * ppf,
        w: cap.width_in ? (cap.width_in / 12) * ppf : 40,
        capY: wallBottom - cap.cap_ft * ppf,
        ridgeMaxY: wallBottom - cap.ridge_max_ft * ppf,
        ridgeMinY: wallBottom - cap.ridge_min_ft * ppf,
      }
    : null;

  // Precomputed display strings — single member-expression per SVG text
  // node (dev-instrumentation wraps inline templates in <span>, which
  // does not paint inside SVG <text>).
  const sheetName = String(data.sheet || "").toUpperCase();
  const S = {};
  S.title = `${sheetName} ELEVATION`;
  S.headerLine = `${String(data.customer_name || "").toUpperCase()} · ${String(data.address || "").toUpperCase()} · SHEET ${data.sheet_code} OF 4`;
  S.fasciaLabel = `FASCIA / RAKE · ${fmtFt(ovFt)} OVERHANG`;
  S.coursesNote = W.courses ? `${W.courses} × ${fmtInFrac(W.exposure_in)} taped` : "";
  if (dev) {
    S.dev1 = `AI run ${dev.run_short} read this wall ${dev.ai_width_label} × ${dev.ai_height_label}` +
      (dev.ai_counts?.length ? ` (${dev.ai_counts.join("/")} courses, ${dev.ai_basis})` : ` (${dev.ai_basis})`);
    S.dev2 = dev.width_disputed
      ? `vs key ${W.width_label} × ${dev.tape_heights_label}: ${dev.delta_width_label} width, ${dev.delta_height_label} height.`
      : `vs key heights ${dev.tape_heights_label}: ${dev.delta_height_label} vs first segment · width untaped — AI governs width.`;
    S.devSummary = `AI wall read: ${dev.ai_width_label} × ${dev.ai_height_label} — flagged deviation above; tape governs heights`;
  }
  if (chase) {
    S.chase1 = `${String(chase.note).toUpperCase()} — ${chase.tag}`;
    S.chase2 = chase.dims_tag === "TAPED"
      ? `${chase.width_label} W × ${chase.depth_label} D × ${chase.height_label} H — TAPED (${chase.taped_stamp || ""})`
      : `profile ${chase.profile} · footprint ${chase.footprint}`;
    S.chase3 = chase.dims_tag === "TAPED" ? `POSITION: ${chase.position || ""}` : "";
    S.chase4 = chase.ai_band ? chase.ai_band.note : "";
    S.chaseGlyphTitle = chase.dims_tag === "TAPED"
      ? `CHIMNEY CHASE — ${chase.width_label} × ${chase.height_label} TAPED`
      : "CHIMNEY CHASE";
    S.chaseGlyphSub = `POSITION ${chase.position_tag || "—"} · ${String(chase.position_note || "").split(" — ")[0].toUpperCase()}`;
    S.chaseData = chase.dims_tag === "TAPED"
      ? `Chase ${chase.width_label} × ${chase.depth_label} × ${chase.height_label} — TAPED · position ${chase.position_tag || "—"}${chase.suppressed ? ` · DRAWING ${String(chase.suppressed_note || "suppressed — collision").toUpperCase()}` : ""}`
      : "";
  }
  // COLLAPSE RULE (ruled 2026-07-20): more than 3 flagged (non-suppressed)
  // pairs stack into ONE summary block; suppression callouts ALWAYS render
  // in full; each affected schedule row keeps its own flag; the full pair
  // list stays in the sheet data. The collapse never hides a flag, only
  // stacks it.
  const suppressedCols = collisions.filter((c) => c.suppressed);
  const flaggedCols = collisions.filter((c) => !c.suppressed);
  const colCollapsed = flaggedCols.length > 3;
  const colLines = (colCollapsed ? suppressedCols : collisions).map((c) => ({
    head: `COLLISION GUARD — ${c.elements.join(" × ")} OVERLAP ${c.overlap_label}${c.suppressed ? ` — ${String(c.suppressed).toUpperCase()} DRAWING SUPPRESSED (OPENING GOVERNS)` : " — POSITIONS UNVERIFIED"}`,
    b1: `${c.elements[0]}: ${c.bases[0]}`,
    b2: `${c.elements[1]}: ${c.bases[1]}`,
  }));
  const colSummaryH = colCollapsed ? 40 : 0;
  if (colCollapsed) {
    const affectedTags = [...new Set(flaggedCols.flatMap((c) => c.elements))];
    S.colSummary1 = `COLLISION GUARD — ${flaggedCols.length} OPENING-PAIR OVERLAPS — POSITIONS UNVERIFIED — SEE SCHEDULE`;
    S.colSummary2 = `AFFECTED: ${affectedTags.join(" ")} · full pair detail retained in sheet data — nothing suppressed`;
  }
  if (prof) {
    S.prof1 = `CHASE PROFILE — ${prof.depth_label} DEEP × ${prof.height_label} — TAPED`;
    S.prof2 = String(prof.anchor).toUpperCase();
  }
  if (cap) {
    S.cap1 = `CHASE CAP ${cap.cap_label} TAPED — VISIBLE OVER RIDGE (clears worst-case AI ridge by ~${cap.clearance_worst_label})`;
    S.cap2 = `RIDGE BAND ${cap.ridge_min_label}–${cap.ridge_max_label} (${cap.ridge_basis}) · ${cap.position}`;
  }
  S.widthTail = ` — ${W.width_tag} (${W.width_source})`;
  if (stepped) {
    S.heightsBold = segList.map((s) => s.height_label).join(" / ");
    S.heightsTail = ` — ${segList[0].height_tag}`;
    S.heightsSub = `${segList.map((s) => s.height_formula).join(" · ")} · step location NOT TAPED`;
  } else {
    S.heightTail = ` — ${W.height_tag} (${W.height_formula})`;
  }
  S.areaBold = W.area_sqft != null ? `${W.area_sqft} ft²` : "—";
  S.areaTail = W.area_sqft != null
    ? ` — DERIVED (${fmtNum(W.width_ft)} × ${fmtNum(W.height_ft)}) · Gable triangle `
    : ` not derivable (step untaped) · Gable `;
  S.gable = gableFt > 0 ? fmtFt(gableFt) : "none";
  S.gableTag = gableFt > 0 ? ` [${W.gable_tag}]` : "";
  S.storiesTail = ` · Stories ${W.stories}`;
  S.sidingBold = `${W.siding_pct}%`;
  S.profileBold = String(W.profile_callout).toUpperCase();
  S.profileTail = W.profile_key_item ? ` (${W.profile_key_item} per key)` : "";
  S.openCount = String(data.openings.length);
  const oc = data.opening_counts;
  S.openTail = data.openings.length
    ? ` (${oc.windows} windows · ${oc.doors} entry door${oc.doors === 1 ? "" : "s"} · ${oc.vents} vent${oc.vents === 1 ? "" : "s"}) — positions AI-READ ✓`
    : " — none read on this wall";
  S.photosLine = `AI source photos: ${(W.source_photos || []).join(", ")} · AI confidence ${W.ai_confidence}${dev ? " (superseded by tape)" : ""}`;
  S.sheetLine = `SHEET ${data.sheet_code} · ${sheetName}`;
  S.wallDataHead = `WALL DATA — ${sheetName}`;
  S.schedHead = `OPENING SCHEDULE — ${sheetName}`;
  S.basisWalls = `GEOMETRY BASIS: ${data.geometry_basis.walls}`;
  S.scaleLine = `Scale ≈ ${scaleLabel} = 1'-0" (auto-fit)`;
  S.viewLine = `${data.view.convention} · ${data.view.datum}`;
  S.dateLine = `Pro-Quote · ${data.generated_date}`;
  S.gableCallout = gableFt > 0 ? `GABLE TRIANGLE ${fmtFt(gableFt)} RISE — INDICATIVE OUTLINE` : "";
  if (stepped) {
    S.seg0Formula = segList[0].height_formula;
    S.seg1Formula = segList[1].height_formula;
    S.seg0Label = segList[0].height_label;
    S.seg1Label = segList[1].height_label;
    S.seg0Corner = `@ ${String(segList[0].adjacent || "").toUpperCase()} CORNER`;
    S.seg1Corner = `@ ${String(segList[1].adjacent || "").toUpperCase()} CORNER`;
  }
  for (const o of data.openings) {
    o._style = `${o.type}${o.style ? ` · ${abbrevStyle(o.style)}` : ""}`;
    o._size = `${o.width_in}×${o.height_in} in`;
  }

  return (
    <svg viewBox="0 0 1056 816" width="1056" height="816" style={{ background: "#fff", boxShadow: "0 2px 12px rgba(0,0,0,.18)" }}
      fontFamily="Helvetica, Arial, sans-serif" data-testid="elevation-sheet-svg">
        <rect width="1056" height="816" fill="#fff" />
        <rect x="24" y="24" width="1008" height="768" fill="none" stroke={C.ink} strokeWidth="2" />
        <rect x="30" y="30" width="996" height="756" fill="none" stroke={C.ink} strokeWidth="0.75" />

        {/* Header */}
        <text x="60" y="72" fontSize="26" fontWeight="bold" letterSpacing="3" fill={C.ink} data-testid="elevation-sheet-title">{S.title}</text>
        <text x="60" y="92" fontSize="11" fill={C.muted} letterSpacing="1">{S.headerLine}</text>
        <text x="996" y="72" fontSize="11" textAnchor="end" fill={C.amber} fontWeight="bold" letterSpacing="1">NOT A SURVEY — SOURCE-TAGGED VERIFICATION SHEET</text>
        <text x="996" y="90" fontSize="10" textAnchor="end" fill={C.muted}>LINEWORK = COMPONENT · CHIPS = SOURCE</text>
        <line x1="60" y1="104" x2="996" y2="104" stroke={C.ink} strokeWidth="1" />

        {/* Deviation box (status channel) */}
        {dev && (
          <g data-testid="elevation-deviation-box">
            <rect x="90" y="150" width="420" height="46" fill="#fef7ec" stroke={C.amber} strokeWidth="1.2" />
            <text x="100" y="166" fontSize="9.5" fontWeight="bold" fill={C.amber}>DEVIATION — AI PHOTO RUN DISAGREES WITH TAPE (TAPE GOVERNS)</text>
            <text x="100" y="180" fontSize="9" fill="#7a4a12">{S.dev1}</text>
            <text x="100" y="192" fontSize="9" fill="#7a4a12">{S.dev2}</text>
          </g>
        )}
        {/* Chase annotation — AI-read, footprint untaped: annotation box +
            INDICATIVE on-wall locator glyph (largest opening-free span) */}
        {chase && (
          <g data-testid="elevation-chase-note">
            <rect x="530" y="150" width="466" height={chaseBoxH} fill="#fffbeb" stroke={C.amber} strokeWidth="1.2" strokeDasharray="5 3" />
            <text x="540" y="166" fontSize="9.5" fontWeight="bold" fill={C.amber}>{S.chase1}</text>
            <text x="540" y="180" fontSize="9" fill="#7a4a12">{S.chase2}</text>
            <text x="540" y="192" fontSize="6" fill="#7a4a12">{S.chase3}</text>
            {chase.ai_band && (
              <text x="540" y="204" fontSize="6" fill="#7a4a12" data-testid="elevation-chase-ai-band">{S.chase4}</text>
            )}
          </g>
        )}
        {colLines.length > 0 && (
          <g data-testid="elevation-collision-guard">
            {colLines.map((c, i) => (
              <g key={i}>
                <rect x="530" y={collisionBoxY + i * 48} width="466" height="44" fill="#fef2f2" stroke={C.trim} strokeWidth="1.4" />
                <text x="540" y={collisionBoxY + i * 48 + 14} fontSize="8" fontWeight="bold" fill={C.trim}>{c.head}</text>
                <text x="540" y={collisionBoxY + i * 48 + 26} fontSize="7" fill="#7f1d1d">{c.b1}</text>
                <text x="540" y={collisionBoxY + i * 48 + 37} fontSize="7" fill="#7f1d1d">{c.b2}</text>
              </g>
            ))}
          </g>
        )}
        {colCollapsed && (
          <g data-testid="elevation-collision-collapse">
            <rect x="530" y={collisionBoxY + colLines.length * 48} width="466" height="34" fill="#fef2f2" stroke={C.trim} strokeWidth="1.4" />
            <text x="540" y={collisionBoxY + colLines.length * 48 + 14} fontSize="8" fontWeight="bold" fill={C.trim}>{S.colSummary1}</text>
            <text x="540" y={collisionBoxY + colLines.length * 48 + 26} fontSize="7" fill="#7f1d1d">{S.colSummary2}</text>
          </g>
        )}
        {prof && (
          <g data-testid="elevation-chase-profile">
            <rect x={profX} y={profTop} width={profW} height={wallBottom - profTop}
              fill="#fbfcfe" stroke={C.siding} strokeWidth="1.75" />
            <g stroke="#e2e8f0" strokeWidth="0.6" data-testid="elevation-chase-profile-hatch">
              {hatchYs.filter((y) => y > profTop + 2).map((y, i) => (
                <line key={i} x1={profX + 1.5} y1={y} x2={profX + profW - 1.5} y2={y} />
              ))}
            </g>
            <line x1={profX - 3} y1={profTop} x2={profX + profW + 3} y2={profTop} stroke={C.siding} strokeWidth="2" />
            <line x1={profX + 3} y1={profTop + 10} x2={profX + profW - 3} y2={profTop + 10} stroke="#8a93a2" strokeWidth="0.7" />
            {data.sheet === "left" ? (
              <g>
                <line x1={profX + profW / 2} y1={profTop - 4} x2="96" y2="224" stroke={C.amber} strokeWidth="0.9" strokeDasharray="3 2" />
                <text x="64" y="234" fontSize="7.5" fontWeight="bold" fill={C.amber}>{S.prof1}</text>
                <text x="64" y="244" fontSize="6.5" fill={C.amber}>{S.prof2}</text>
              </g>
            ) : (
              <g>
                <line x1={profX + profW / 2} y1={profTop - 4} x2="960" y2="224" stroke={C.amber} strokeWidth="0.9" strokeDasharray="3 2" />
                <text x="992" y="234" fontSize="7.5" fontWeight="bold" fill={C.amber} textAnchor="end">{S.prof1}</text>
                <text x="992" y="244" fontSize="6.5" fill={C.amber} textAnchor="end">{S.prof2}</text>
              </g>
            )}
          </g>
        )}
        {capG && (
          <g data-testid="elevation-chase-cap">
            <line x1={wallX - 20} y1={capG.ridgeMaxY} x2={wallRight + 20} y2={capG.ridgeMaxY} stroke="#8a93a2" strokeWidth="0.9" strokeDasharray="8 4" />
            <line x1={wallX - 20} y1={capG.ridgeMinY} x2={wallRight + 20} y2={capG.ridgeMinY} stroke="#8a93a2" strokeWidth="0.9" strokeDasharray="8 4" />
            <rect x={capG.cx - capG.w / 2} y={capG.capY} width={capG.w} height={capG.ridgeMinY - capG.capY}
              fill="#fbfcfe" stroke={C.siding} strokeWidth="1.5" strokeDasharray="5 3" />
            <g stroke="#e2e8f0" strokeWidth="0.6" data-testid="elevation-chase-cap-hatch">
              {hatchYs.filter((y) => y > capG.capY + 2 && y < capG.ridgeMinY - 1).map((y, i) => (
                <line key={i} x1={capG.cx - capG.w / 2 + 1.5} y1={y} x2={capG.cx + capG.w / 2 - 1.5} y2={y} />
              ))}
            </g>
            <line x1={capG.cx - capG.w / 2 - 3} y1={capG.capY} x2={capG.cx + capG.w / 2 + 3} y2={capG.capY} stroke={C.siding} strokeWidth="2" />
            <text x={capG.cx} y={capG.capY - 14} fontSize="7.5" textAnchor="middle" fill={C.amber} fontWeight="bold">{S.cap1}</text>
            <text x={capG.cx} y={capG.capY - 5} fontSize="6.5" textAnchor="middle" fill={C.amber}>{S.cap2}</text>
          </g>
        )}
        {anyCollision && (
          <g data-testid="elevation-collision-banner">
            <rect x="530" y={collisionBoxY + colLines.length * 48 + colSummaryH} width="300" height="24" fill="#fef2f2" stroke={C.trim} strokeWidth="1.2" strokeDasharray="4 2" />
            <text x="540" y={collisionBoxY + colLines.length * 48 + colSummaryH + 16} fontSize="9" fontWeight="bold" fill={C.trim}>OPENING POSITIONS UNVERIFIED — OVERLAP DETECTED</text>
          </g>
        )}

        {/* Gable-end walls: dashed indicative triangle + rake; eave walls: fascia band + soffit */}
        {gableFt > 0 ? (
          <g data-testid="elevation-gable">
            <clipPath id="gable-clip">
              <path d={`M ${wallX} ${segTopY[0]} L ${(wallX + wallRight) / 2} ${apexY} L ${wallRight} ${segTopY[stepped ? 1 : 0]} Z`} />
            </clipPath>
            <g clipPath="url(#gable-clip)" stroke="#e2e8f0" strokeWidth="0.6" data-testid="elevation-gable-hatch">
              {hatchYs.filter((y) => y > apexY + 2 && y < Math.max(...segTopY)).map((y, i) => (
                <line key={i} x1={wallX} y1={y} x2={wallRight} y2={y} />
              ))}
            </g>
            <path d={`M ${wallX} ${segTopY[0]} L ${(wallX + wallRight) / 2} ${apexY} L ${wallRight} ${segTopY[stepped ? 1 : 0]}`}
              fill="none" stroke={C.fascia} strokeWidth="2" strokeDasharray="7 4" />
            <text x={(wallX + wallRight) / 2} y={apexY - 8} fontSize="9" textAnchor="middle" fill="#0284c7" fontWeight="bold" letterSpacing="1">{S.gableCallout}</text>
            <Chip x={(wallX + wallRight) / 2 + 4} y={apexY + 6}
              w={W.gable_tag === "AI-READ ✓" ? 62 : 66} label={W.gable_tag} kind={tagKind(W.gable_tag)} />
            <text x={wallX - 14} y={segTopY[0] - 8} fontSize="8.5" fill="#0284c7" fontWeight="bold">RAKE (GABLE END) ↗</text>
          </g>
        ) : (
          <g>
            <rect x={wallX - ovFt * ppf} y={wallTop - 22} width={wallW + 2 * ovFt * ppf} height="22" fill="none" stroke={C.fascia} strokeWidth="3" />
            <text x={fasciaLabelX} y={wallTop - 29.4} fontSize="9" textAnchor="middle" fill="#0284c7" letterSpacing="1" fontWeight="bold">{S.fasciaLabel}</text>
            <line x1={wallX - ovFt * ppf + 1.2} y1={wallTop - 2.6} x2={wallRight + ovFt * ppf - 1.2} y2={wallTop - 2.6} stroke={C.soffit} strokeWidth="2.5" strokeDasharray="1 4" />
            <text x={wallX - 14} y={wallTop - 29.4} fontSize="8.5" fill={C.soffit} fontWeight="bold">SOFFIT (EAVES ONLY) ↴</text>
          </g>
        )}

        {/* Wall + course hatch (true per-segment course counts) */}
        {stepped ? (
          <path d={outline} fill="#fbfcfe" stroke={C.siding} strokeWidth="1.75" data-testid="elevation-wall-rect" />
        ) : (
          <rect x={wallX} y={wallTop} width={wallW} height={wallBottom - wallTop} fill="#fbfcfe" stroke={C.siding} strokeWidth="1.75" data-testid="elevation-wall-rect" />
        )}
        <g stroke="#e2e8f0" strokeWidth="0.6">
          {courseLines.map((l, i) => <line key={i} x1={l.x1} y1={l.y} x2={l.x2} y2={l.y} />)}
        </g>
        {stepped && (
          <g data-testid="elevation-step-note">
            <line x1={stepX} y1={segTopY[1] - 6} x2={stepX} y2={segTopY[0]} stroke={C.amber} strokeWidth="1" strokeDasharray="3 2" />
            <text x={stepX} y={segTopY[1] - 12} fontSize="8" textAnchor="middle" fill={C.amber} fontWeight="bold">STEP — LOCATION NOT TAPED (INDICATIVE)</text>
          </g>
        )}

        {/* Openings (component: opening trim; sill-less = dashed, V-pos estimated) */}
        {ops.filter((o) => o.drawable).map((o) => (
          <g key={o.tag} data-testid={`elevation-opening-${o.tag}`}>
            <rect x={o.x} y={o.y} width={o.w} height={o.h}
              fill={o.type === "Window" ? "#eef3f9" : o.type === "Vent" ? "#f5f2e8" : "#e7e2d8"}
              stroke={C.trim} strokeWidth="2.25"
              strokeDasharray={o.collision || o.noSill ? "5 3" : undefined} />
            {o.type === "Window" && (
              <g stroke="#8a93a2">
                <line x1={o.cx} y1={o.y} x2={o.cx} y2={o.y + o.h} strokeWidth="1.2" />
                <line x1={o.x} y1={o.y + o.h / 2} x2={o.x + o.w} y2={o.y + o.h / 2} strokeWidth="1" />
              </g>
            )}
            {o.type === "Vent" && (
              <g stroke="#8a93a2" strokeWidth="0.9">
                <line x1={o.x + 2} y1={o.y + o.h * 0.3} x2={o.x + o.w - 2} y2={o.y + o.h * 0.3} />
                <line x1={o.x + 2} y1={o.y + o.h * 0.55} x2={o.x + o.w - 2} y2={o.y + o.h * 0.55} />
                <line x1={o.x + 2} y1={o.y + o.h * 0.8} x2={o.x + o.w - 2} y2={o.y + o.h * 0.8} />
              </g>
            )}
            {o.type === "Entry door" && (
              <g>
                <rect x={o.x + o.w * 0.17} y={o.y + o.h * 0.1} width={o.w * 0.66} height={o.h * 0.38} fill="none" stroke="#8a93a2" strokeWidth="1" />
                <rect x={o.x + o.w * 0.17} y={o.y + o.h * 0.56} width={o.w * 0.66} height={o.h * 0.36} fill="none" stroke="#8a93a2" strokeWidth="1" />
                <circle cx={o.x + o.w - 8} cy={o.y + o.h * 0.52} r="2.2" fill={C.ink} />
              </g>
            )}
            {o.collision && (
              <text x={o.cx} y={o.y - 4} fontSize="7" textAnchor="middle" fill={C.trim} fontWeight="bold">POSITION UNVERIFIED</text>
            )}
            {o.noSill && (
              <text x={o.cx} y={o.y + o.h + 10} fontSize="7" textAnchor="middle" fill={C.amber} fontWeight="bold">V-POS ESTIMATED — NO DOOR ANCHOR</text>
            )}
            {/* schedule tag bubble */}
            <line x1={o.cx} y1={bubbleY + 10} x2={o.cx} y2={o.y - 2} stroke={C.muted} strokeWidth="0.9" />
            <circle cx={o.cx} cy={bubbleY} r="12" fill="#fff" stroke={C.ink} strokeWidth="1.5" />
            <text x={o.cx} y={bubbleY + 4} fontSize="11" fontWeight="bold" textAnchor="middle" fill={C.ink}>{o.tag}</text>
          </g>
        ))}

        {/* Starter + outside corners + grade */}
        <line x1={wallX} y1={wallBottom - 3.5} x2={wallRight} y2={wallBottom - 3.5} stroke={C.starter} strokeWidth="2.5" strokeDasharray="8 3 2 3" />
        <line x1={wallX + 1.5} y1={segTopY[0]} x2={wallX + 1.5} y2={wallBottom} stroke={C.osc} strokeWidth="3.5" />
        <line x1={wallRight - 1.5} y1={segTopY[stepped ? 1 : 0]} x2={wallRight - 1.5} y2={wallBottom} stroke={C.osc} strokeWidth="3.5" />
        <line x1="60" y1={wallBottom} x2="960" y2={wallBottom} stroke={C.ink} strokeWidth="2" />
        <path d={`M 66 ${wallBottom} l 8 10 M 82 ${wallBottom} l 8 10 M 98 ${wallBottom} l 8 10 M 918 ${wallBottom} l 8 10 M 934 ${wallBottom} l 8 10 M 950 ${wallBottom} l 8 10`} stroke={C.ink} strokeWidth="1" />
        <text x="62" y={wallBottom + 16} fontSize="9" fill={C.muted}>GRADE</text>

        {/* Chase glyph — LAST wall-plane paint. OCCLUSION RULE (ruled
            2026-07-19): the chase projects 31" proud of the wall — it
            occludes ALL wall-plane linework inside its footprint (wall top
            line, fascia/soffit, course hatch, starter, grade). Wall lines
            break at its edges; the chase's own outline + lap fill govern
            inside. Same mechanism family as the z-order fix. */}
        {chaseG && (
          <g data-testid="elevation-chase-glyph">
            <line x1="530" y1="208" x2={chaseG.cx + chaseG.w / 2} y2={chaseG.top - 30} stroke={C.amber} strokeWidth="0.9" strokeDasharray="3 2" />
            <rect x={chaseG.cx - chaseG.w / 2} y={chaseG.top} width={chaseG.w} height={wallBottom - chaseG.top}
              fill="#fbfcfe" stroke={C.siding} strokeWidth="1.75" />
            <g stroke="#e2e8f0" strokeWidth="0.6" data-testid="elevation-chase-glyph-hatch">
              {hatchYs.filter((y) => y > chaseG.top + 2 && y < wallBottom - 1).map((y, i) => (
                <line key={i} x1={chaseG.cx - chaseG.w / 2 + 1.5} y1={y} x2={chaseG.cx + chaseG.w / 2 - 1.5} y2={y} />
              ))}
            </g>
            {/* chase-to-wall junctions (vinyl conventions: ISC treatment, wall height) */}
            <line x1={chaseG.cx - chaseG.w / 2 - 4} y1={wallTop} x2={chaseG.cx - chaseG.w / 2 - 4} y2={wallBottom} stroke={C.isc} strokeWidth="2.25" strokeDasharray="6 3" />
            <line x1={chaseG.cx + chaseG.w / 2 + 4} y1={wallTop} x2={chaseG.cx + chaseG.w / 2 + 4} y2={wallBottom} stroke={C.isc} strokeWidth="2.25" strokeDasharray="6 3" />
            {/* chase outer vertical edges = OUTSIDE CORNERS (contractor-spec): SOLID OSC component color, grade to cap */}
            <line x1={chaseG.cx - chaseG.w / 2} y1={chaseG.top} x2={chaseG.cx - chaseG.w / 2} y2={wallBottom} stroke={C.osc} strokeWidth="3.5" />
            <line x1={chaseG.cx + chaseG.w / 2} y1={chaseG.top} x2={chaseG.cx + chaseG.w / 2} y2={wallBottom} stroke={C.osc} strokeWidth="3.5" />
            <line x1={chaseG.cx - chaseG.w / 2 - 3} y1={chaseG.top} x2={chaseG.cx + chaseG.w / 2 + 3} y2={chaseG.top} stroke={C.siding} strokeWidth="2" />
            <text x={chaseG.cx} y={chaseG.top - 18} fontSize="7.5" textAnchor="middle" fill={C.amber} fontWeight="bold">{S.chaseGlyphTitle}</text>
            <text x={chaseG.cx} y={chaseG.top - 9} fontSize="6.5" textAnchor="middle" fill={C.amber}>{S.chaseGlyphSub}</text>
          </g>
        )}

        {/* Opening-center chain (only when openings exist on this wall) */}
        {ops.some((o) => o.drawable) && (
          <g>
            <g stroke={C.ink} strokeWidth="1">
              {chain.map((x, i) => <line key={i} x1={x} y1={i === 0 || i === chain.length - 1 ? 522 : 494} x2={x} y2={566} />)}
              <line x1={wallX} y1="560" x2={wallRight} y2="560" />
              {chain.map((x, i) => <path key={`t${i}`} d={`M ${x - 4.2} 564 l 8.4 -8`} strokeWidth="1.4" />)}
            </g>
            <g fontSize="10.5" textAnchor="middle" fill={C.ink}>
              {segs.map((s, i) => <text key={i} x={s.x} y="554">{s.label}</text>)}
            </g>
            <Chip x={920} y={551} w={98} label="CTRS · AI-READ ✓" kind="ai-ok" />
          </g>
        )}

        {/* Overall width */}
        <g stroke={C.ink} strokeWidth="1">
          <line x1={wallX} y1="568" x2={wallX} y2="606" /><line x1={wallRight} y1="568" x2={wallRight} y2="606" />
          <line x1={wallX} y1="600" x2={wallRight} y2="600" />
          <path d={`M ${wallX - 4.2} 604 l 8.4 -8 M ${wallRight - 4.2} 604 l 8.4 -8`} strokeWidth="1.4" />
        </g>
        <rect x="448" y="588" width="104" height="20" fill="#fff" />
        <text x="500" y="602" fontSize="13" fontWeight="bold" textAnchor="middle" fill={C.ink} data-testid="elevation-width-value">{W.width_label}</text>
        <Chip x={556} y={590} w={W.width_tag === "TAPED" ? 52 : 74} label={W.width_tag} kind={tagKind(W.width_tag)} />

        {/* Siding height basis lines — §9 naming; stepped: ONE PER SEGMENT */}
        {stepped ? (
          <g>
            {/* seg[1] (right half) — right-side basis line */}
            <g stroke={C.ink} strokeWidth="1" data-testid="elevation-seg-basis-1">
              <line x1={wallRight + dimOffR + 2} y1={segTopY[1]} x2="952" y2={segTopY[1]} /><line x1={wallRight + dimOffR + 2} y1={wallBottom} x2="952" y2={wallBottom} />
              <line x1="946" y1={segTopY[1]} x2="946" y2={wallBottom} />
              <path d={`M 941.8 ${segTopY[1] + 4} l 8.4 -8 M 941.8 ${wallBottom + 4} l 8.4 -8`} strokeWidth="1.4" />
            </g>
            <text x="954" y={segTopY[1] + 24} fontSize="7.5" fontWeight="bold" fill={C.muted}>SEG 2 HEIGHT</text>
            <text x="954" y={segTopY[1] + 33} fontSize="6.5" fontWeight="bold" fill={C.amber}>{S.seg1Corner}</text>
            <text x="954" y={segTopY[1] + 48} fontSize="12" fontWeight="bold" fill={C.ink} data-testid="elevation-height-value">{S.seg1Label}</text>
            <Chip x={950} y={segTopY[1] + 54} w={74} label="TAPED-DERIVED" kind="taped-derived" />
            <text x="1022" y={segTopY[1] + 82} fontSize="7" fill={C.muted} textAnchor="end">{S.seg1Formula}</text>
            {/* seg[0] (left half) — left-side basis line */}
            <g stroke={C.ink} strokeWidth="1" data-testid="elevation-seg-basis-0">
              <line x1={wallX - dimOffL - 2} y1={segTopY[0]} x2={wallX - dimOffL - 52} y2={segTopY[0]} /><line x1={wallX - dimOffL - 2} y1={wallBottom} x2={wallX - dimOffL - 52} y2={wallBottom} />
              <line x1={wallX - dimOffL - 46} y1={segTopY[0]} x2={wallX - dimOffL - 46} y2={wallBottom} />
              <path d={`M ${wallX - dimOffL - 50.2} ${segTopY[0] + 4} l 8.4 -8 M ${wallX - dimOffL - 50.2} ${wallBottom + 4} l 8.4 -8`} strokeWidth="1.4" />
            </g>
            <text x={wallX - dimOffL - 56} y={segTopY[0] + 24} fontSize="7.5" fontWeight="bold" fill={C.muted} textAnchor="end">SEG 1 HEIGHT</text>
            <text x={wallX - dimOffL - 56} y={segTopY[0] + 33} fontSize="6.5" fontWeight="bold" fill={C.amber} textAnchor="end">{S.seg0Corner}</text>
            <text x={wallX - dimOffL - 56} y={segTopY[0] + 48} fontSize="12" fontWeight="bold" fill={C.ink} textAnchor="end">{S.seg0Label}</text>
            <Chip x={wallX - dimOffL - 130} y={segTopY[0] + 54} w={74} label="TAPED-DERIVED" kind="taped-derived" />
            <text x={wallX - dimOffL - 56} y={segTopY[0] + 82} fontSize="7" fill={C.muted} textAnchor="end">{S.seg0Formula}</text>
          </g>
        ) : (
          <g>
            <g stroke={C.ink} strokeWidth="1">
              <line x1={wallRight + 2} y1={wallTop} x2="952" y2={wallTop} /><line x1={wallRight + 2} y1={wallBottom} x2="952" y2={wallBottom} />
              <line x1="946" y1={wallTop} x2="946" y2={wallBottom} />
              <path d={`M 941.8 ${wallTop + 4} l 8.4 -8 M 941.8 ${wallBottom + 4} l 8.4 -8`} strokeWidth="1.4" />
            </g>
            <text x="954" y={wallTop + 38} fontSize="7.5" fontWeight="bold" fill={C.muted}>SIDING HEIGHT</text>
            <text x="954" y={wallTop + 47} fontSize="6.5" fill={C.muted}>(starter → soffit)</text>
            <text x="954" y={wallTop + 64} fontSize="13" fontWeight="bold" fill={C.ink} data-testid="elevation-height-value">{W.height_label}</text>
            <Chip x={950} y={wallTop + 70} w={74} label={W.height_tag === "TAPED-DERIVED" ? "TAPED-DERIVED" : W.height_tag} kind={tagKind(W.height_tag)} />
            {W.courses && (
              <text x="950" y={wallTop + 100} fontSize="8" fill={C.muted}>{S.coursesNote}</text>
            )}
          </g>
        )}

        {/* Bottom strip */}
        <line x1="60" y1="628" x2="996" y2="628" stroke={C.ink} strokeWidth="1" />

        {/* Wall data (stepped: formulas get their own sub-line — column is 344px) */}
        <g fontSize="9" fill={C.ink} data-testid="elevation-wall-data">
          <text x="60" y="646" fontWeight="bold" letterSpacing="1.5" fontSize="10.5">{S.wallDataHead}</text>
          <text x="60" y="664"><tspan>Width </tspan><tspan fontWeight="bold">{W.width_label}</tspan><tspan>{S.widthTail}</tspan></text>
          {stepped ? (
            <g>
              <text x="60" y="680"><tspan>Siding heights (starter → soffit) </tspan><tspan fontWeight="bold">{S.heightsBold}</tspan><tspan>{S.heightsTail}</tspan></text>
              <text x="60" y="691" fontSize="7.5" fill={C.muted}>{S.heightsSub}</text>
            </g>
          ) : (
            <text x="60" y="680"><tspan>Siding height (starter → soffit) </tspan><tspan fontWeight="bold">{W.height_label}</tspan><tspan>{S.heightTail}</tspan></text>
          )}
          <text x="60" y={stepped ? 704 : 696}><tspan>Wall area </tspan><tspan fontWeight="bold">{S.areaBold}</tspan><tspan>{S.areaTail}</tspan><tspan fontWeight="bold">{S.gable}</tspan><tspan>{S.gableTag}</tspan><tspan>{S.storiesTail}</tspan></text>
          <text x="60" y={stepped ? 718 : 712}><tspan>Siding </tspan><tspan fontWeight="bold">{S.sidingBold}</tspan><tspan> · Profile callout </tspan><tspan fontWeight="bold">{S.profileBold}</tspan><tspan>{S.profileTail}</tspan></text>
          <text x="60" y={stepped ? 732 : 728}><tspan>Openings </tspan><tspan fontWeight="bold">{S.openCount}</tspan><tspan>{S.openTail}</tspan></text>
          {dev && <text x="60" y={stepped ? 746 : S.chaseData ? 742 : 744}>{S.devSummary}</text>}
          {S.chaseData && (
            <text x="60" y="751" fontSize="6.8" data-testid="elevation-wall-data-chase">{S.chaseData}</text>
          )}
          <text x="60" y="760" fill={C.muted}>{S.photosLine}</text>
        </g>

        {/* Opening schedule */}
        <g fontSize="9.5" fill={C.ink} data-testid="elevation-schedule">
          <text x="404" y="646" fontWeight="bold" letterSpacing="1.5" fontSize="10.5">{S.schedHead}</text>
          {data.openings.length > 0 && (
            <g>
              <g fontWeight="bold" fill={C.muted}>
                <text x="420" y="664">TAG</text><text x="452" y="664">TYPE / STYLE</text><text x="566" y="664">SIZE (W×H)</text><text x="630" y="664">CTR @</text><text x="676" y="664">SILL</text>
              </g>
              <line x1="404" y1="669" x2="712" y2="669" stroke="#8a93a2" strokeWidth="0.8" />
            </g>
          )}
          {data.openings.map((o, i) => (
            <g key={o.tag}>
              <rect x="404" y={677 + i * 16} width="9" height="9" fill="#fff" stroke={C.trim} strokeWidth="2" />
              <text x="420" y={684 + i * 16}>{o.tag}</text>
              <text x="452" y={684 + i * 16}>{o._style}</text>
              <text x="566" y={684 + i * 16}>{o._size}</text>
              <text x="630" y={684 + i * 16}>{o.center_label}</text>
              <text x="676" y={684 + i * 16}>{o.sill_label}</text>
              {o.collision && (
                <text x="714" y={684 + i * 16} fontSize="8" fontWeight="bold" fill={C.trim} data-testid={`elevation-schedule-collision-${o.tag}`}>⚠</text>
              )}
            </g>
          ))}
          {data.openings.length > 0 && (
            <text x="404" y={677 + data.openings.length * 16 + 12} fill={C.muted} fontSize="8.5">Swatch = drawn element's component class (opening trim).</text>
          )}
          <text x="404" y={677 + data.openings.length * 16 + 24} fill={C.muted} fontSize="8.5">{data.schedule_note}</text>
          {anyCollision && (
            <text x="404" y={677 + data.openings.length * 16 + 36} fill={C.trim} fontSize="8.5" data-testid="elevation-schedule-collision-legend">⚠ = position unverified — overlap flagged by the collision guard</text>
          )}
        </g>

        {/* Title block + merged legend */}
        <g data-testid="elevation-title-block">
          <rect x="732" y="638" width="264" height="132" fill="none" stroke={C.ink} strokeWidth="1.5" />
          <line x1="732" y1="658" x2="996" y2="658" stroke={C.ink} strokeWidth="0.8" />
          <line x1="732" y1="688" x2="996" y2="688" stroke={C.ink} strokeWidth="0.8" />
          <line x1="732" y1="704" x2="996" y2="704" stroke={C.ink} strokeWidth="0.8" />
          <g fontSize="8.5" fill={C.ink}>
            <text x="738" y="651" fontWeight="bold" fontSize="9">{String(data.customer_name || "").toUpperCase()}</text>
            <text x="990" y="651" textAnchor="end">{S.sheetLine}</text>
            <text x="738" y="670" fontWeight="bold" fontSize={S.basisWalls.length > 68 ? 6.3 : 7.5}>{S.basisWalls}</text>
            <text x="738" y="681" fontSize="7.5">{data.geometry_basis.openings}</text>
            <text x="738" y="699" fontSize="7.5">{S.scaleLine}</text>
            <text x="990" y="699" textAnchor="end" fontSize="7.5">{S.dateLine}</text>
          </g>
          <text x="738" y="715" fontSize="7" fontWeight="bold" fill={C.muted} letterSpacing="1">KEY — LINEWORK = COMPONENT · CHIPS = SOURCE</text>
          <g fontSize="6.5" fontWeight="bold" fill={C.ink}>
            <line x1="738" y1="724" x2="752" y2="724" stroke={C.siding} strokeWidth="1.75" /><text x="755" y="727">SIDING</text>
            <line x1="784" y1="724" x2="798" y2="724" stroke={C.trim} strokeWidth="2.25" /><text x="801" y="727">TRIM</text>
            <line x1="822" y1="724" x2="836" y2="724" stroke={C.osc} strokeWidth="3.5" /><text x="839" y="727">OSC</text>
            <line x1="857" y1="724" x2="871" y2="724" stroke={C.isc} strokeWidth="2.25" strokeDasharray="6 3" /><text x="874" y="727">ISC</text>
            <line x1="891" y1="724" x2="905" y2="724" stroke={C.fascia} strokeWidth="3" /><text x="908" y="727">FASCIA/RAKE</text>
            <line x1="738" y1="738" x2="752" y2="738" stroke={C.soffit} strokeWidth="2.5" strokeDasharray="1 4" /><text x="755" y="741">SOFFIT</text>
            <line x1="786" y1="738" x2="800" y2="738" stroke={C.starter} strokeWidth="2.5" strokeDasharray="8 3 2 3" /><text x="803" y="741">STARTER</text>
            <line x1="838" y1="738" x2="852" y2="738" stroke={C.band} strokeWidth="2.75" strokeDasharray="10 4" /><text x="855" y="741">BAND BD (C-SPEC)</text>
          </g>
          <g fontSize="6" fontWeight="bold">
            <rect x="736" y="748" width="32" height="12" rx="6" fill={C.green} /><text x="752" y="756.5" textAnchor="middle" fill="#fff">TAPED</text>
            <rect x="771" y="748" width="32" height="12" rx="6" fill={C.green} stroke="#fff" strokeWidth="0.8" strokeDasharray="2.5 1.5" /><text x="787" y="756.5" textAnchor="middle" fill="#fff">T-DER</text>
            <rect x="806" y="748" width="26" height="12" rx="6" fill="#fff" stroke={C.green} /><text x="819" y="756.5" textAnchor="middle" fill={C.green}>AI ✓</text>
            <rect x="835" y="748" width="26" height="12" rx="6" fill={C.amber} /><text x="848" y="756.5" textAnchor="middle" fill="#fff">AI ⚠</text>
            <rect x="864" y="748" width="24" height="12" rx="6" fill="#fff" stroke={C.amber} strokeDasharray="3 2" /><text x="876" y="756.5" textAnchor="middle" fill={C.amber}>EST</text>
            <rect x="891" y="748" width="30" height="12" rx="6" fill="#1d4ed8" /><text x="906" y="756.5" textAnchor="middle" fill="#fff">PRINT</text>
            <rect x="924" y="748" width="26" height="12" rx="6" fill="#7c3aed" /><text x="937" y="756.5" textAnchor="middle" fill="#fff">USER</text>
            <rect x="953" y="748" width="38" height="12" rx="6" fill="#111827" /><text x="972" y="756.5" textAnchor="middle" fill="#fff">C-SPEC</text>
          </g>
        </g>
      </svg>
  );
}

function fmtFt(ft) {
  const sign = ft < 0 ? "-" : "";
  const totalE = Math.round(Math.abs(ft) * 96);
  const feet = Math.floor(totalE / 96);
  const rem = totalE - feet * 96;
  const inches = Math.floor(rem / 8);
  const e = rem - inches * 8;
  const FR = ["", "⅛", "¼", "⅜", "½", "⅝", "¾", "⅞"];
  return `${sign}${feet}'-${inches}${FR[e]}"`;
}
function fmtInFrac(inches) {
  const whole = Math.floor(inches);
  const e = Math.round((inches - whole) * 8);
  const FR = ["", "⅛", "¼", "⅜", "½", "⅝", "¾", "⅞"];
  return e === 8 ? `${whole + 1}"` : `${whole}${FR[e]}"`;
}
function fmtNum(n) {
  return Number(n).toFixed(3).replace(/\.?0+$/, "");
}
function abbrevStyle(s) {
  return String(s).replace("Double Hung", "DH");
}
