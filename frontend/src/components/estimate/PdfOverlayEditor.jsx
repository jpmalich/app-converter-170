// MATERIAL ZONE LAYER — MUV SESSION 2 editor (Howard ruled 2026-08-13
// pro-quotes replies 5/6/7).
//
// The contractor opens a REAL rasterised elevation PDF page, draws /
// drags polygons over walls, and each zone REPLACES the app's derived
// square footage for its (material_class, face_id). The three laws:
//   A. REPLACE not add — the app's number stays visible, marked superseded.
//   B. A human value is a function of its polygons — delete the last one
//      and the app's number comes back.
//   C. Scale is READ FROM THE SHEET per view (OCR the printed dimension,
//      or trace a calibration line) — never a baked constant. No scale
//      for a view → the area is REFUSED, not defaulted.
//
// The polygon math + persistence is authoritative on the backend
// (/api/estimates/:id/pdf-overlay); this editor mirrors the ft² live so
// the readout tracks the drawing.
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  X, Trash2, Ruler, Sparkles, Loader2, AlertTriangle, PencilRuler,
  ZoomIn, ZoomOut, MousePointer2,
} from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

const MATERIAL_CLASSES = [
  { value: "siding", label: "Siding", color: "#2563EB" },
  { value: "soffit", label: "Soffit", color: "#0891B2" },
  { value: "accent", label: "Accent", color: "#DB2777" },
  { value: "trim", label: "Trim", color: "#D97706" },
];
const FIXED_FACES = ["front", "back", "left", "right"];

function classColor(mc) {
  return (MATERIAL_CLASSES.find((m) => m.value === mc) || MATERIAL_CLASSES[0]).color;
}

// Live ft² — mirrors backend polygon_sqft_from_scale exactly (two modes:
// printed_scale = fraction+DPI, trace = human calibration line). Returns
// null (REFUSED) when the scale can't be resolved.
function polygonSqft(vertices, scaleRef, wpx, hpx) {
  if (!vertices || vertices.length < 3 || !scaleRef || !wpx || !hpx) return null;
  const mode = scaleRef.mode || (scaleRef.in_per_ft ? "printed_scale" : "trace");
  let ftPerPx = null;
  if (mode === "printed_scale") {
    const { in_per_ft, dpi } = scaleRef;
    if (!in_per_ft || !dpi || in_per_ft <= 0 || dpi <= 0) return null;
    ftPerPx = 1 / (in_per_ft * dpi);
  } else {
    const { p1, p2, real_ft } = scaleRef;
    if (!p1 || !p2 || !real_ft || real_ft <= 0) return null;
    const calibPx = Math.hypot((p2[0] - p1[0]) * wpx, (p2[1] - p1[1]) * hpx);
    if (calibPx <= 0) return null;
    ftPerPx = real_ft / calibPx;
  }
  if (!ftPerPx || ftPerPx <= 0) return null;
  let a = 0;
  const n = vertices.length;
  for (let i = 0; i < n; i++) {
    const x1 = vertices[i][0] * wpx, y1 = vertices[i][1] * hpx;
    const x2 = vertices[(i + 1) % n][0] * wpx, y2 = vertices[(i + 1) % n][1] * hpx;
    a += x1 * y2 - x2 * y1;
  }
  return Math.round((Math.abs(a / 2) * ftPerPx * ftPerPx) * 100) / 100;
}

// Derive the elevation face from the page's identified title. NEVER
// defaults (Howard ruled 2026-08-13). Returns a face ONLY when the title
// names EXACTLY ONE face — a page titled "FRONT & REAR ELEVATIONS" names
// two, so it is AMBIGUOUS and returns "" to force the user to pick (that
// two-face page is exactly why the rear zone got mislabelled "front").
function faceFromTitle(title) {
  const t = (title || "").toLowerCase();
  const hits = [];
  if (/\bfront\b/.test(t)) hits.push("front");
  if (/\b(rear|back)\b/.test(t)) hits.push("back");
  if (/\bleft\b/.test(t)) hits.push("left");
  if (/\bright\b/.test(t)) hits.push("right");
  return hits.length === 1 ? hits[0] : ""; // 0 or >1 → user must pick
}

export default function PdfOverlayEditor({ est, onChanged }) {
  const [open, setOpen] = useState(false);
  const [pages, setPages] = useState([]);       // [{name,url,idx,label,face,faceKnown}]
  const [polygons, setPolygons] = useState([]); // backend polygons
  const [renderDpi, setRenderDpi] = useState(null); // recorded page render DPI (null ⇒ scan)
  const [perWall, setPerWall] = useState([]);       // app's internal per-wall areas (display only)
  const [facesND, setFacesND] = useState([]);       // per-face NOT DERIVABLE reasons (backend truth)
  const [runId, setRunId] = useState(null);         // latest run id (for the diagnostic panel)
  const [loadErr, setLoadErr] = useState("");

  // Probe the latest blueprint run for rasterised elevation pages + the
  // existing polygon set. Runs on mount so the launcher shows a count.
  const probe = useCallback(async () => {
    if (!est?.id) return;
    try {
      const [{ data: runResp }, { data: ovl }] = await Promise.all([
        api.get(`/measure/ai-blueprint/latest-for-estimate/${est.id}`, { timeout: 12000 }),
        api.get(`/estimates/${est.id}/pdf-overlay`).catch(() => ({ data: { polygons: [] } })),
      ]);
      const run = runResp?.run;
      const names = (run?.page_paths || "").split(",").map((s) => s.trim()).filter(Boolean);
      const res = run?.result || {};
      const sheets = res.raw_ai?.sheets_identified
        || res.measurements?._blueprint_sheets
        || res.sheets_identified || [];
      setRenderDpi(run?.render_dpi != null ? Number(run.render_dpi) : null);
      setPerWall(res.measurements?._per_elevation_breakdown
        || res.raw_ai?._per_elevation_breakdown || []);
      setFacesND(res.measurements?._faces_not_derivable
        || res.raw_ai?._faces_not_derivable || []);
      setRunId(run?.run_id || res.measurements?._run_id || null);
      const sheetFor = (i1) => sheets.find((x) => Number(x.page) === i1) || null;
      setPages(names.map((name, i) => {
        const s = sheetFor(i + 1);
        const title = s ? (s.sheet_title || s.useful_for || "") : "";
        const isElev = (s?.useful_for || "") === "elevation";
        const face = isElev ? faceFromTitle(title) : "";
        return {
          name, url: `${BACKEND}/api/uploads/${name}`, idx: i + 1,
          label: title ? `${i + 1}· ${title}` : `Page ${i + 1}`,
          elevation: isElev, face, faceKnown: !!face,
        };
      }));
      setPolygons(ovl?.polygons || []);
      setLoadErr(names.length ? "" : "no-pages");
    } catch {
      setLoadErr("no-run");
    }
  }, [est?.id]);

  useEffect(() => { probe(); }, [probe]);

  const polyCount = polygons.length;

  return (
    <div className="card p-4" data-testid="pdf-overlay-launcher">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-2)] flex items-center gap-2">
          <PencilRuler className="w-3 h-3" /> Material Zones — draw on the real elevation page
        </div>
        <button
          type="button"
          onClick={() => { setOpen(true); probe(); }}
          disabled={!!loadErr}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-[var(--ai)] bg-[var(--ai)] text-white text-[10px] font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-40 transition-opacity"
          data-testid="pdf-overlay-open-btn"
          title={loadErr === "no-run"
            ? "Read a blueprint PDF first — the editor draws on its rasterised pages"
            : "Open the elevation page and draw material zones"}
        >
          <PencilRuler className="w-3 h-3" />
          {polyCount > 0 ? `Material Zones · ${polyCount}` : "Draw Material Zones"}
        </button>
      </div>
      {loadErr === "no-run" && (
        <p className="text-[11px] text-[var(--muted)] mt-2" data-testid="pdf-overlay-no-run">
          No blueprint read yet — run <span className="font-bold">Read Blueprints</span> so the
          real elevation pages are available to draw on.
        </p>
      )}
      {loadErr === "no-pages" && (
        <p className="text-[11px] text-[var(--muted)] mt-2" data-testid="pdf-overlay-no-pages">
          The last blueprint read didn&apos;t persist page images — re-run the read to draw zones.
        </p>
      )}

      {open && (
        <OverlayModal
          est={est}
          pages={pages}
          polygons={polygons}
          renderDpi={renderDpi}
          perWall={perWall}
          facesND={facesND}
          runId={runId}
          onClose={() => setOpen(false)}
          onMutated={async () => { await probe(); onChanged?.(); }}
        />
      )}
    </div>
  );
}

function OverlayModal({ est, pages, polygons: initialPolys, renderDpi, perWall, facesND, runId, onClose, onMutated }) {
  const [polygons, setPolygons] = useState(initialPolys || []);
  const [activePage, setActivePage] = useState(
    (pages.find((p) => p.elevation) || pages[0])?.idx || 1);
  const [material, setMaterial] = useState("siding");
  const [face, setFace] = useState("");           // NEVER defaults — derived from the page
  const [faceAuto, setFaceAuto] = useState(false); // true when face came from the page title
  const [dormerLabel, setDormerLabel] = useState("");
  // SEND-48 per-surface binding: a gable is its own bindable surface.
  const [gableSurface, setGableSurface] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [scaleByPage, setScaleByPage] = useState({}); // {pageIdx: scaleRef}
  const [draft, setDraft] = useState(null);           // {points:[[x,y]], cx, cy}
  const [scaleDraft, setScaleDraft] = useState(null); // {p1,p2,active,dragging}
  const [scaleInput, setScaleInput] = useState(null); // {p1,p2,ft}
  const [selectedId, setSelectedId] = useState(null);
  const [dragVertex, setDragVertex] = useState(null); // {polyId, index}
  const [imgNat, setImgNat] = useState({ w: 0, h: 0 });
  const [zoom, setZoom] = useState(1);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [estLines, setEstLines] = useState(est?.lines || []);
  const imgRef = useRef(null);
  const scrollRef = useRef(null);      // the scrolling canvas viewport
  const wheelAnchor = useRef(null);    // {fx,fy,ox,oy} to keep the cursor point fixed across a wheel-zoom

  const page = pages.find((p) => p.idx === activePage);
  const pageScale = scaleByPage[activePage] || null;
  const faceId = face === "dormer"
    ? `dormer:${(dormerLabel || "").trim() || "1"}`
    : (face && gableSurface ? `gable:${face}` : face);

  // FACE FROM PAGE (Howard ruled 2026-08-13): derive the face from the
  // page's identified elevation; where unknown, leave it EMPTY so the
  // user must pick. Never default to "front".
  useEffect(() => {
    if (page && page.faceKnown) { setFace(page.face); setFaceAuto(true); }
    else { setFace(""); setFaceAuto(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage]);

  // Seed per-page scale from any polygon already drawn on that page
  // (the calibration travels with the polygon → per-view by construction).
  useEffect(() => {
    const seeded = {};
    for (const p of polygons) {
      if (p.scale_ref && p.page && !seeded[p.page]) seeded[p.page] = p.scale_ref;
    }
    setScaleByPage((cur) => ({ ...seeded, ...cur }));
  }, [polygons]);

  // Pull the raw estimate lines (unmerged) for the superseded side-by-side.
  const refreshLines = useCallback(async () => {
    try {
      const { data } = await api.get(`/estimates/${est.id}`);
      setEstLines(data?.lines || []);
    } catch { /* keep last */ }
  }, [est.id]);
  useEffect(() => { refreshLines(); }, [refreshLines]);

  useEffect(() => {
    const h = (e) => {
      if (e.key === "Escape") { setDraft(null); setScaleDraft(null); setScaleInput(null); }
      if (e.key === "Enter" && draft?.points?.length >= 3) finalizeDraft(draft.points);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, pageScale, faceId, material, activePage, imgNat]);

  const pagePolys = polygons.filter((p) => p.page === activePage);

  const normFromEvent = (e) => {
    const r = imgRef.current.getBoundingClientRect();
    return [
      Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
      Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
    ];
  };

  const onMouseDown = (e) => {
    if (!imgRef.current) return;
    const [x, y] = normFromEvent(e);
    if (scaleDraft?.active) {
      // TWO-CLICK trace (matches the polygon tool): first click sets the
      // start, second click sets the end and only THEN measures. Never
      // evaluate length until two DISTINCT points exist.
      if (!scaleDraft.p1) {
        setScaleDraft({ active: true, p1: [x, y], p2: [x, y] });
        return;
      }
      const p1 = scaleDraft.p1;
      const p2 = [x, y];
      const distPx = Math.hypot((p2[0] - p1[0]) * imgNat.w, (p2[1] - p1[1]) * imgNat.h);
      if (distPx < 8) {
        toast.error("Second point too close — click the other end of the dimension");
        return; // keep p1; let the user click the far end
      }
      setScaleDraft(null);
      setScaleInput({ p1, p2, ft: "" });
      return;
    }
    if (dragVertex) return; // vertex handle owns the drag
    // polygon draw: click adds a vertex; click near first vertex closes.
    const pts = draft?.points || [];
    if (pts.length >= 3) {
      const d = Math.hypot(pts[0][0] - x, pts[0][1] - y);
      if (d < 0.02) { finalizeDraft(pts); return; }
    }
    setDraft({ points: [...pts, [x, y]], cx: x, cy: y });
  };

  const onMouseMove = (e) => {
    if (!imgRef.current) return;
    const [x, y] = normFromEvent(e);
    if (scaleDraft?.active && scaleDraft.p1) { setScaleDraft({ ...scaleDraft, p2: [x, y] }); return; }
    if (dragVertex) {
      setPolygons((cur) => cur.map((p) => p.id === dragVertex.polyId
        ? { ...p, vertices_pct: p.vertices_pct.map((v, i) => i === dragVertex.index ? [x, y] : v) }
        : p));
      return;
    }
    if (draft) setDraft({ ...draft, cx: x, cy: y });
  };

  const onMouseUp = async () => {
    if (dragVertex) {
      const poly = polygons.find((p) => p.id === dragVertex.polyId);
      setDragVertex(null);
      if (poly) await persistPolygon(poly);
    }
  };

  const finalizeDraft = async (points) => {
    if (!points || points.length < 3) return;
    if (!faceId) {
      // FACE FROM PAGE (Howard ruled): refuse rather than default.
      // Clear the draft so the next attempt (after picking a face)
      // starts clean and can close by proximity to its own first vertex.
      setDraft(null);
      toast.error("Pick a face for this view first — the page didn't identify one, so it won't be guessed");
      return;
    }
    setDraft(null);
    if (!pageScale) {
      toast.warning("Scale not read on this view — the zone saves but cannot be priced yet");
    }
    await persistPolygon({
      page: activePage, face_id: faceId, material_class: material,
      vertices_pct: points,
    });
  };

  const persistPolygon = async (poly) => {
    try {
      const body = {
        id: poly.id,
        page: poly.page,
        face_id: poly.face_id,
        material_class: poly.material_class,
        vertices_pct: poly.vertices_pct,
        // A proposal carries its own evidence-grounded trace scale from
        // the height chain — keep it when the page has no traced scale.
        scale_ref: scaleByPage[poly.page] || poly.scale_ref || null,
        page_w_px: imgNat.w || poly.page_w_px || null,
        page_h_px: imgNat.h || poly.page_h_px || null,
        // SEND-48: ANY human touch (draw, bump, confirm) makes it HUMAN.
        provenance: "human",
      };
      const { data } = await api.put(`/estimates/${est.id}/pdf-overlay`, body);
      const saved = data?.polygon;
      setPolygons((cur) => {
        const rest = cur.filter((p) => p.id !== saved.id);
        return [...rest, saved];
      });
      setSelectedId(saved.id);
      if (data?.scale_read === false) {
        toast.warning("Zone saved — scale not read on this view, area refused");
      } else {
        toast.success(`Zone saved · ${saved.sqft} ft²`);
      }
      await refreshLines();
      onMutated?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save zone");
    }
  };

  // SEND-48: AI proposes provisional zones from the Height Build (one
  // band rectangle per DERIVED face). They feed NO quantity until the
  // contractor confirms or bumps them (which makes them HUMAN).
  const proposeZones = async () => {
    setProposing(true);
    try {
      const { data } = await api.post(`/estimates/${est.id}/pdf-overlay/propose`);
      const fresh = await api.get(`/estimates/${est.id}/pdf-overlay`);
      setPolygons(fresh.data?.polygons || []);
      const n = (data?.proposed || []).length;
      if (n) toast.success(`${n} zone${n === 1 ? "" : "s"} proposed — provisional until you confirm`);
      else toast.warning("No face established a height — nothing to propose");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Propose failed");
    } finally {
      setProposing(false);
    }
  };

  const deletePolygon = async (pid) => {
    try {
      const { data } = await api.delete(`/estimates/${est.id}/pdf-overlay/${pid}`);
      setPolygons((cur) => cur.filter((p) => p.id !== pid));
      if (selectedId === pid) setSelectedId(null);
      toast.success(data?.retired_override
        ? "Zone deleted — the app's own number is back"
        : "Zone deleted");
      await refreshLines();
      onMutated?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to delete zone");
    }
  };

  const confirmScale = () => {
    const ft = Number(scaleInput.ft);
    if (!ft || ft <= 0) { toast.error("Enter a positive length in feet"); return; }
    setScaleByPage((cur) => ({
      ...cur,
      [activePage]: {
        mode: "trace", p1: scaleInput.p1, p2: scaleInput.p2, real_ft: ft,
        source: `TRACE · you calibrated ${ft} ft`, from_quote: "",
      },
    }));
    setScaleInput(null);
    toast.success(`Scale traced for this view · ${ft} ft`);
  };

  // READ (AI): the PRIMARY Law-C path — read the printed scale FRACTION
  // (e.g. 3/16"=1'-0") as text and combine with the page's RECORDED
  // render DPI. No vision pixel coords (those were ~3.6x short → ~13x
  // area). Refuses when the fraction can't be read or the page has no
  // known DPI (a scan) — the user then TRACES.
  const readPrintedScale = async () => {
    if (!page?.name) return;
    if (!renderDpi) {
      toast.error("This page has no recorded render DPI (a scan) — trace the scale by hand instead");
      return;
    }
    setOcrBusy(true);
    try {
      const { data } = await api.post("/measure/read-page-scale", {
        upload_name: page.name, render_dpi: renderDpi,
      });
      if (!data?.found || !data.in_per_ft) {
        toast.error(data?.notes
          ? `Printed scale not read · ${data.notes} — trace it instead`
          : "Couldn't read the printed scale — trace it instead");
        return;
      }
      setScaleByPage((cur) => ({
        ...cur,
        [activePage]: {
          mode: "printed_scale", in_per_ft: data.in_per_ft, dpi: renderDpi,
          source: `READ · ${data.scale_text}`, from_quote: data.scale_text || "",
        },
      }));
      toast.success(`Printed scale read · ${data.scale_text}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Read-scale failed");
    } finally {
      setOcrBusy(false);
    }
  };

  // Superseded side-by-side for the material lines touched on this
  // estimate. The takeoff line is an AGGREGATE (no per-face), so we key
  // the row off the section + carry the zone count (Howard's "say when
  // merged"), not a single face.
  const impacts = useMemo(() => {
    const slug = (s) => (s || "line").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    return estLines
      .filter((l) => l.overlay_superseded || l.overlay_scale_unreadable)
      .map((l) => ({
        section: l.section || "Line", slug: slug(l.section), unit: l.unit,
        app: l.superseded_qty != null ? l.superseded_qty : l.qty,
        human: l.qty, sqft: l.overlay_sqft,
        merged: !!l.overlay_merged, count: l.overlay_polygon_count,
        refused: !!l.overlay_scale_unreadable,
        perSurface: !!l.overlay_per_surface,
        surfaces: l.overlay_replaced_surfaces || [],
      }));
  }, [estLines]);

  const bumpZoom = (f) => setZoom((z) => Math.max(0.5, Math.min(6, z * f)));

  // SCROLL-WHEEL ZOOM (Howard 2026-08-14 UX): scrolling over the drawing
  // zooms in/out — the normal expectation for a tracing tool — anchored
  // to the cursor so the point under the pointer stays put. Native
  // non-passive listener so we can preventDefault the page scroll.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const ox = e.clientX - rect.left;   // cursor offset inside the viewport
      const oy = e.clientY - rect.top;
      // fraction of the CONTENT currently under the cursor
      const fx = el.scrollWidth ? (el.scrollLeft + ox) / el.scrollWidth : 0.5;
      const fy = el.scrollHeight ? (el.scrollTop + oy) / el.scrollHeight : 0.5;
      wheelAnchor.current = { fx, fy, ox, oy };
      const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
      setZoom((z) => Math.max(0.5, Math.min(6, z * factor)));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  // After a wheel-zoom re-layout, re-place the scroll so the same content
  // fraction sits back under the cursor.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    const a = wheelAnchor.current;
    if (!el || !a) return;
    el.scrollLeft = a.fx * el.scrollWidth - a.ox;
    el.scrollTop = a.fy * el.scrollHeight - a.oy;
    wheelAnchor.current = null;
  }, [zoom]);

  return (
    <div className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-3"
      data-testid="pdf-overlay-modal" onClick={onClose}>
      <div className="bg-[var(--surface)] w-full h-[92vh] max-w-6xl flex flex-col border border-[var(--border)]"
        onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="bg-[var(--ai)] text-white px-4 py-2.5 flex items-center justify-between">
          <div>
            <div className="font-heading text-base">Material Zone Editor</div>
            <div className="text-[11px] opacity-90">Draw on the real elevation page · your zone replaces the app&apos;s number</div>
          </div>
          <button type="button" onClick={onClose} className="text-white/90 hover:text-white" data-testid="pdf-overlay-close">
            <X size={18} />
          </button>
        </div>

        {/* Known-limit banner (Howard ruled — name it on the surface) */}
        <div className="px-3 py-1.5 bg-[#FEF3C7] border-b border-[#F59E0B] text-[10px] text-[var(--warning-text)] font-bold flex items-center gap-1.5"
          data-testid="pdf-overlay-known-limit">
          <AlertTriangle className="w-3 h-3 flex-shrink-0" />
          Known limit: “front”/“back” aggregate every wall segment into ONE number and there is no separate entry-gable face yet.
          When two zones feed one face the line is flagged “merged”.
        </div>

        <div className="flex-1 flex min-h-0">
          {/* Page strip */}
          <div className="w-28 border-r border-[var(--border)] overflow-y-auto bg-[var(--surface-muted)] p-2 space-y-2">
            {pages.map((p) => (
              <button key={p.idx} type="button" onClick={() => { setActivePage(p.idx); setDraft(null); setZoom(1); }}
                className={`block w-full border-2 text-left ${p.idx === activePage ? "border-[var(--ai)]" : "border-[var(--border)]"}`}
                data-testid={`pdf-overlay-page-${p.idx}`}>
                <img src={p.url} alt={p.label} className="w-full h-auto block" />
                <span className="block text-[9px] font-bold uppercase tracking-wider text-[var(--muted)] px-1 py-0.5 truncate">
                  {p.label}
                </span>
              </button>
            ))}
          </div>

          {/* Canvas */}
          <div className="flex-1 relative min-w-0">
            <div ref={scrollRef} className="absolute inset-0 overflow-auto bg-[#27272A]">
            {page ? (
              <div className="p-4">
                <div className="relative" style={{ width: `${zoom * 100}%`, lineHeight: 0 }}>
                  <img ref={imgRef} src={page.url} alt={page.label} draggable={false}
                    className="select-none" style={{ display: "block", width: "100%", height: "auto", cursor: "crosshair" }}
                    onLoad={(e) => setImgNat({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                    onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp} onMouseLeave={onMouseUp}
                    data-testid="pdf-overlay-canvas-img" />

                  {/* existing polygons */}
                  <svg className="absolute top-0 left-0 pointer-events-none" style={{ width: "100%", height: "100%" }}
                    viewBox="0 0 100 100" preserveAspectRatio="none">
                    {pagePolys.map((p) => {
                      const col = classColor(p.material_class);
                      const sel = p.id === selectedId;
                      const proposed = p.provenance === "proposed";
                      return (
                        <polygon key={p.id}
                          points={p.vertices_pct.map((v) => `${v[0] * 100},${v[1] * 100}`).join(" ")}
                          fill={`${col}${proposed ? "11" : sel ? "44" : "22"}`} stroke={col} strokeWidth={sel ? "0.6" : "0.4"}
                          strokeDasharray={proposed ? "2 1.2" : p.sqft == null ? "1 0.6" : "0"} />
                      );
                    })}
                    {draft?.points?.length > 0 && (
                      <polyline points={[...draft.points, [draft.cx, draft.cy]].map((v) => `${v[0] * 100},${v[1] * 100}`).join(" ")}
                        fill="none" stroke={classColor(material)} strokeWidth="0.4" strokeDasharray="1 0.5" />
                    )}
                    {scaleDraft?.p1 && scaleDraft?.p2 && (
                      <line x1={scaleDraft.p1[0] * 100} y1={scaleDraft.p1[1] * 100} x2={scaleDraft.p2[0] * 100} y2={scaleDraft.p2[1] * 100}
                        stroke="#10B981" strokeWidth="0.5" strokeDasharray="2 1" />
                    )}
                  </svg>
                  {/* vertex handles on the selected polygon (drag to reshape) */}
                  {pagePolys.filter((p) => p.id === selectedId).map((p) => p.vertices_pct.map((v, i) => (
                    <div key={`${p.id}-${i}`}
                      onMouseDown={(e) => { e.stopPropagation(); setDragVertex({ polyId: p.id, index: i }); }}
                      className="absolute w-2.5 h-2.5 -ml-1 -mt-1 rounded-full bg-white border-2 cursor-move"
                      style={{ left: `${v[0] * 100}%`, top: `${v[1] * 100}%`, borderColor: classColor(p.material_class) }}
                      data-testid={`pdf-overlay-vertex-${p.id}-${i}`} />
                  )))}
                  {/* per-polygon sqft badge */}
                  {pagePolys.map((p) => (
                    <div key={`lbl-${p.id}`} className="absolute text-white font-bold" style={{
                      left: `${p.vertices_pct[0][0] * 100}%`, top: `${p.vertices_pct[0][1] * 100}%`,
                      background: classColor(p.material_class), fontSize: "9px", padding: "1px 3px", lineHeight: 1,
                    }}>
                      {p.material_class}·{p.sqft == null ? "no scale" : `${p.sqft} ft²`}
                    </div>
                  ))}
                </div>
              </div>
            ) : <div className="text-white p-4 text-sm">No elevation page</div>}
            </div>
            {/* Floating zoom controls — anchored to the pane so they never
                scroll away when you pan down to a dimension line. Scroll
                the wheel over the drawing to zoom (cursor-anchored). */}
            <div className="absolute top-2 right-2 z-30 flex flex-col gap-1 w-fit">
              <button type="button" onClick={() => bumpZoom(1.25)} className="w-8 h-8 bg-white/95 border border-[#27272A] flex items-center justify-center shadow-md" title="Zoom in (or scroll up)" data-testid="pdf-overlay-zoom-in"><ZoomIn className="w-4 h-4" /></button>
              <button type="button" onClick={() => setZoom(1)} className="px-1 h-8 bg-white/95 border border-[#27272A] text-[9px] font-bold shadow-md" title="Reset zoom" data-testid="pdf-overlay-zoom-reset">{Math.round(zoom * 100)}%</button>
              <button type="button" onClick={() => bumpZoom(1 / 1.25)} className="w-8 h-8 bg-white/95 border border-[#27272A] flex items-center justify-center shadow-md" title="Zoom out (or scroll down)" data-testid="pdf-overlay-zoom-out"><ZoomOut className="w-4 h-4" /></button>
            </div>
          </div>

          {/* Right panel */}
          <div className="w-72 border-l border-[var(--border)] flex flex-col overflow-y-auto">
            {/* Scale for this view */}
            <div className="p-3 border-b border-[var(--border)]">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">Scale for this view</div>
              {pageScale ? (
                <div className="text-[11px] text-[var(--success)] font-bold" data-testid="pdf-overlay-scale-ok">
                  ✓ {pageScale.source || (pageScale.mode === "printed_scale" ? "READ" : "TRACE")}
                </div>
              ) : (
                <div className="text-[11px] text-[var(--warning-text)] font-bold flex items-center gap-1" data-testid="pdf-overlay-scale-missing">
                  <AlertTriangle className="w-3 h-3" /> Not read — areas refused on this view
                </div>
              )}
              <div className="flex gap-1 mt-2">
                <button type="button" onClick={() => setScaleDraft({ active: true })}
                  className={`flex-1 text-[10px] uppercase font-bold px-2 py-1.5 border flex items-center justify-center gap-1 ${scaleDraft?.active ? "bg-[var(--success)] text-white" : "border-[var(--border)] hover:bg-[var(--surface-muted)]"}`}
                  data-testid="pdf-overlay-set-scale">
                  <Ruler size={12} /> {scaleDraft?.active ? (scaleDraft?.p1 ? "Click the far end…" : "Click one end…") : "Trace scale"}
                </button>
                <button type="button" onClick={readPrintedScale} disabled={ocrBusy}
                  className="flex-1 text-[10px] uppercase font-bold px-2 py-1.5 border border-[var(--ai)] text-[var(--ai)] hover:bg-[var(--ai-soft)] flex items-center justify-center gap-1 disabled:opacity-50"
                  data-testid="pdf-overlay-read-scale">
                  {ocrBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />} Read (AI)
                </button>
              </div>
              {scaleInput && (
                <div className="mt-2 p-2 border border-[var(--success)] bg-[#ECFDF5]">
                  <div className="text-[10px] font-bold text-[#065F46] mb-1">What length did you trace? (feet)</div>
                  <div className="flex gap-1">
                    <input type="number" step="0.01" min="0.1" value={scaleInput.ft} autoFocus
                      onChange={(e) => setScaleInput({ ...scaleInput, ft: e.target.value })}
                      className="flex-1 border border-[var(--border)] px-2 py-1 text-xs" data-testid="pdf-overlay-scale-ft" />
                    <button type="button" onClick={confirmScale} className="bg-[var(--success)] text-white text-[10px] font-bold px-2" data-testid="pdf-overlay-scale-confirm">OK</button>
                  </div>
                </div>
              )}
            </div>

            {/* Material + face pickers */}
            <div className="p-3 border-b border-[var(--border)]">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">New zone · material</div>
              <div className="grid grid-cols-2 gap-1 mb-2">
                {MATERIAL_CLASSES.map((m) => (
                  <button key={m.value} type="button" onClick={() => setMaterial(m.value)}
                    className={`text-[10px] uppercase font-bold px-2 py-1.5 border ${material === m.value ? "ring-2 ring-[var(--brand)]" : "border-transparent"}`}
                    style={{ background: `${m.color}22`, color: m.color }}
                    data-testid={`pdf-overlay-material-${m.value}`}>{m.label}</button>
                ))}
              </div>
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">
                Face {faceAuto
                  ? <span className="text-[var(--success)]">· from page “{page?.label}”</span>
                  : <span className="text-[var(--warning-text)]">· page didn’t identify one — pick it</span>}
              </div>
              <div className="grid grid-cols-3 gap-1" data-testid="pdf-overlay-face-picker">
                {[...FIXED_FACES, "dormer"].map((f) => (
                  <button key={f} type="button" onClick={() => { setFace(f); setFaceAuto(false); }}
                    className={`text-[10px] uppercase font-bold px-1.5 py-1.5 border ${face === f ? "bg-[var(--bar-bg)] text-white border-[var(--border-strong)]" : "border-[var(--border)] hover:bg-[var(--surface-muted)]"}`}
                    data-testid={`pdf-overlay-face-${f}`}>{f}</button>
                ))}
              </div>
              {face === "dormer" && (
                <input type="text" value={dormerLabel} onChange={(e) => setDormerLabel(e.target.value)}
                  placeholder="dormer label (e.g. A)" className="mt-1 w-full border border-[var(--border)] px-2 py-1 text-[11px]"
                  data-testid="pdf-overlay-dormer-label" />
              )}
              {face && face !== "dormer" && (
                <button type="button" onClick={() => setGableSurface((g) => !g)}
                  className={`mt-1 w-full text-[10px] uppercase font-bold px-2 py-1.5 border ${gableSurface ? "bg-[var(--bar-bg)] text-white border-[var(--border-strong)]" : "border-[var(--border)] hover:bg-[var(--surface-muted)]"}`}
                  data-testid="pdf-overlay-gable-toggle">
                  {gableSurface ? `binding: gable of ${face}` : "bind the gable (triangle) instead"}
                </button>
              )}
              <button type="button" onClick={proposeZones} disabled={proposing}
                className="mt-2 w-full text-[10px] uppercase font-bold px-2 py-1.5 border border-[var(--ai)] text-[var(--ai)] hover:bg-[var(--ai-soft)] flex items-center justify-center gap-1 disabled:opacity-50"
                data-testid="pdf-overlay-propose-zones">
                {proposing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                Propose zones (AI · provisional)
              </button>
              <p className="text-[10px] text-[var(--muted)] mt-2 flex items-center gap-1">
                <MousePointer2 className="w-3 h-3" /> Click each corner on the page, click the first point (or press Enter) to close.
              </p>
            </div>

            {/* Zones on this page */}
            <div className="p-3 border-b border-[var(--border)]">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">Zones on this page ({pagePolys.length})</div>
              {pagePolys.length === 0 && <div className="text-[11px] text-[var(--muted)] italic">None yet.</div>}
              {pagePolys.map((p) => (
                <div key={p.id} className={`flex items-center justify-between border p-1.5 mb-1 cursor-pointer ${p.id === selectedId ? "border-[var(--ai)]" : "border-[var(--border)]"}`}
                  onClick={() => setSelectedId(p.id)} data-testid={`pdf-overlay-zone-${p.id}`}>
                  <span className="text-[11px] font-bold" style={{ color: classColor(p.material_class) }}>
                    {p.material_class} · {p.face_id} · {p.sqft == null ? (p.provenance === "proposed" ? "proposed" : "no scale") : `${p.sqft} ft²`}
                    {p.provenance === "proposed" && (
                      <span className="ml-1 text-[9px] uppercase font-bold text-[var(--warning-text)]">provisional</span>
                    )}
                  </span>
                  <span className="flex items-center gap-1">
                    {p.provenance === "proposed" && (
                      <button type="button" onClick={(e) => { e.stopPropagation(); persistPolygon(p); }}
                        className="text-[9px] uppercase font-bold px-1.5 py-0.5 border border-[var(--success)] text-[var(--success)] hover:bg-[#ECFDF5]"
                        data-testid={`pdf-overlay-confirm-${p.id}`}>confirm</button>
                    )}
                    <button type="button" onClick={(e) => { e.stopPropagation(); deletePolygon(p.id); }}
                      className="text-[var(--muted)] hover:text-[var(--danger)]" data-testid={`pdf-overlay-delete-${p.id}`}>
                      <Trash2 size={13} />
                    </button>
                  </span>
                </div>
              ))}
            </div>

            {/* Superseded side-by-side */}
            <div className="p-3">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">App vs. your number</div>
              {impacts.length === 0 && <div className="text-[11px] text-[var(--muted)] italic">Draw a zone to correct a face.</div>}
              {impacts.map((im, i) => (
                <div key={i} className="border border-[var(--border)] p-1.5 mb-1 text-[11px]" data-testid={`pdf-overlay-impact-${im.slug}`}>
                  <div className="font-bold">
                    {im.section}
                    {im.count ? <span className="ml-1 text-[9px] uppercase font-bold text-[var(--muted)]">· {im.count} zone{im.count === 1 ? "" : "s"}</span> : null}
                  </div>
                  {im.refused ? (
                    <div className="text-[var(--warning-text)] font-bold">scale not read — cannot convert (kept app {im.app} {im.unit})</div>
                  ) : (
                    <div>
                      <span className="line-through text-[var(--muted)]">app {im.app}</span>
                      {" → "}
                      <span className="font-bold text-[var(--ai)]">you {im.human} {im.unit}</span>
                      {im.sqft != null && <span className="ml-1 text-[9px] text-[var(--muted)]">({im.sqft} ft²)</span>}
                      {im.merged && <span className="ml-1 text-[9px] uppercase font-bold text-[var(--warning-text)]">merged</span>}
                      {im.perSurface && im.surfaces.map((s) => (
                        <div key={s.face_id} className="mt-0.5 text-[10px]" data-testid={`pdf-overlay-surface-${s.face_id.replace(/[^a-z]+/g, "-")}`}>
                          <span className="uppercase font-bold">{s.face_id}</span>
                          {" — "}
                          {s.refusal
                            ? <span className="text-[var(--warning-text)]">was refused: {s.refusal}</span>
                            : <span>replaced app {s.superseded_sqft} ft²</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* App's internal per-wall breakdown (DISPLAY ONLY — the
                aggregate line is what binds; this shows the pieces so a
                correction can be judged against the app's own faces). */}
            {perWall && perWall.length > 0 && (
              <div className="p-3 border-t border-[var(--border)]" data-testid="pdf-overlay-perwall">
                <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] mb-1">
                  App&apos;s per-wall siding (read-only, not bound)
                </div>
                {perWall.map((w, i) => {
                  const bodyND = w.wall_body_sqft === null || w.wall_body_sqft === undefined;
                  const gableND = w.gable_sqft === null || w.gable_sqft === undefined;
                  const body = Number(w.wall_body_sqft || 0);
                  const gable = Number(w.gable_sqft || 0);
                  const dormer = Number(w.dormer_sqft || 0);
                  const tot = body + gable + dormer;
                  const notDerivable = bodyND || gableND;
                  // RULING EE surface fix (send-27): the refusal reason is
                  // BACKEND TRUTH — never a hardcoded string. A footprint-
                  // closure refusal carries refused_reason on the row; other
                  // NOT DERIVABLE faces name their reason in _faces_not_derivable.
                  // "does not close" and "width not read" are DIFFERENT
                  // sentences; the surface must say which one actually fired.
                  const ndReasons = (facesND || [])
                    .filter((f) => String(f.elevation || f.label || "").toLowerCase()
                      === String(w.label || "").toLowerCase())
                    .map((f) => f.reason)
                    .filter(Boolean);
                  const reason = w.refused_reason
                    || ndReasons.find((r) => r.startsWith("footprint does not close"))
                    || ndReasons[0]
                    || "not derivable — reason not recorded";
                  return (
                    <div key={i} className="flex justify-between text-[11px] border-b border-[var(--border)] py-0.5" data-testid={`pdf-overlay-perwall-${w.label}`}>
                      <span className="font-bold uppercase">{w.label}</span>
                      {notDerivable ? (
                        <span className="text-amber-600 font-semibold text-[10px] text-right max-w-[70%]" data-testid={`pdf-overlay-perwall-nd-${w.label}`}>
                          NOT DERIVABLE — {reason}
                          {!bodyND ? <span className="ml-1 text-[9px] text-[var(--muted)]">(wall {body.toFixed(0)})</span> : null}
                        </span>
                      ) : (
                        <span className="text-[var(--muted)]">
                          {tot.toFixed(0)} ft²
                          {(gable || dormer) ? <span className="ml-1 text-[9px]">(wall {body.toFixed(0)}{gable ? ` · gable ${gable.toFixed(0)}` : ""}{dormer ? ` · dormer ${dormer.toFixed(0)}` : ""})</span> : null}
                        </span>
                      )}
                    </div>
                  );
                })}
                <div className="text-[9px] text-[var(--muted)] mt-1 italic">These are the app&apos;s internal faces; MUV still binds one aggregate line until per-face binding lands.</div>
              </div>
            )}
            <BlueprintDiagnosticsPanel runId={runId} />

          </div>
        </div>
      </div>
    </div>
  );
}


// SEND-27 Item 3 — the plain diagnostic panel. Howard verifies GG / FF
// inputs / EE reasons IN THE BROWSER, no database view. Read-only.
function BlueprintDiagnosticsPanel({ runId }) {
  const [diag, setDiag] = useState(null);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!open || !runId || diag) return;
    let live = true;
    api.get(`/measure/ai-blueprint/diagnostics/${runId}`, { timeout: 12000 })
      .then(({ data }) => { if (live) setDiag(data?.diagnostics || null); })
      .catch((e) => { if (live) setErr(e?.response?.data?.detail || "diagnostics unavailable"); });
    return () => { live = false; };
  }, [open, runId, diag]);
  if (!runId) return null;
  const gg = diag?.gg || {};
  const ff = diag?.ff_inputs || {};
  const ee = diag?.ee || [];
  const renderHits = (v) => (v === "ABSENT" || !v)
    ? <span className="text-red-600 font-bold">ABSENT</span>
    : (Array.isArray(v) ? v : [v]).map((h, i) => (
        <div key={i} className="pl-2 font-mono-num text-[10px]">
          {JSON.stringify(h.raw)} · p{h.page} · {h.loc ? `x${h.loc.x_pct} y${h.loc.y_pct} w${h.loc.w_pct} h${h.loc.h_pct}` : "no box"}
        </div>));
  return (
    <div className="p-3 border-t border-[var(--border)]" data-testid="pdf-overlay-diagnostics">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] hover:text-[var(--fg)]"
        data-testid="pdf-overlay-diagnostics-toggle"
      >
        {open ? "▾" : "▸"} Blueprint read diagnostics (GG · FF inputs · EE) — read-only
      </button>
      {open && (
        <div className="mt-2 text-[11px] space-y-3" data-testid="pdf-overlay-diagnostics-body">
          {err && <div className="text-red-600">{err}</div>}
          {!diag && !err && <div className="text-[var(--muted)]">loading…</div>}
          {diag && (
            <>
              <div data-testid="diag-gg">
                <div className="font-bold uppercase text-[10px] tracking-wider">GG — OCR persistence</div>
                <div className="font-mono-num text-[10px]">
                  stored: {String(gg.where)} · total runs: {gg.total_runs} · truncated: {String(gg.truncated)} · int-key coercions: {String(gg.int_key_coercions)}
                </div>
                <div className="font-mono-num text-[10px]">runs/page: {JSON.stringify(gg.pages || {})}</div>
              </div>
              <div data-testid="diag-ff">
                <div className="font-bold uppercase text-[10px] tracking-wider">FF inputs (probes)</div>
                <div>garage label: {renderHits(ff.garage_label)}</div>
                <div>left elevation title: {renderHits(ff.left_elevation_title)}</div>
                <div>right elevation title: {renderHits(ff.right_elevation_title)}</div>
                <div>depth near garage: {renderHits(ff.depth_near_garage)}</div>
              </div>
              <div data-testid="diag-ee">
                <div className="font-bold uppercase text-[10px] tracking-wider">EE — per-face refusal</div>
                {ee.length === 0 && <div className="text-[var(--muted)]">no refused faces</div>}
                {ee.map((e, i) => (
                  <div key={i} className="pl-2 mb-1" data-testid={`diag-ee-${e.face}`}>
                    <span className="font-bold uppercase">{e.face}</span>: {e.refusal_reason}
                    <div className="text-[9px] text-[var(--muted)]">produced by: {e.produced_by}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
