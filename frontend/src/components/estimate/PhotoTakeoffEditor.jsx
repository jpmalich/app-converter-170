import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { X, ZoomIn, ZoomOut, AlertTriangle, Ruler, Trash2, Check, Ban, Move, Download, Sparkles } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import MarksPanel from "@/components/estimate/phototakeoff/MarksPanel";
import QuantitiesPanel from "@/components/estimate/phototakeoff/QuantitiesPanel";
import ScalePanel from "@/components/estimate/phototakeoff/ScalePanel";
// SEND-143 — PHASE 2 LINEAR RUNS: J-channel from the drawn opening box,
// the gable rake from the lines drawn with the triangle, and a named
// refusal row for every trim whose mark does not exist yet.
// SEND-144 — the finished AI read hands off STARTING ZONES; the candidate
// edges of a body zone show what a trim run would follow, with no LF.
import CandidateEdges from "@/components/estimate/phototakeoff/CandidateEdges";
import TrimPanel from "@/components/estimate/phototakeoff/TrimPanel";
import {
  CATEGORIES, DORMER, EAVE, GABLE, OPENING, SIDING, TAP_ORDER, WALL_BASE, kindLabel, markColor,
} from "@/components/estimate/phototakeoff/marks";
// SEND-139 — the gable and dormer tools MOVE HERE from the annotator.
// The annotator's own math module is REUSED, not re-implemented: same
// base/rise/pitch, same averaged dormer edges, same masking. Its gable
// area has always been the true triangle (½ × base × rise), which is
// exactly what SEND-137 ruled — no 0.70 exists in this path.
import {
  GABLE_PITCH_PRESETS, gableDims, dormerDims, pitchOutOfRange,
} from "@/lib/gableMath";

/* PHOTO TAKEOFF EDITOR — PHASE 1 (Howard ruled 2026-08-26, SEND-131A).
   The contractor marks THE PHOTO. Full-screen, one photo at a time,
   shaped after PdfOverlayEditor: same snap/zoom conventions, same
   colours (siding blue from the overlay editor, the annotator's own
   material colours), window-level vertex drag that tracks the pointer
   1:1 at any zoom, and pinch-zoom on a phone.

   Discipline, carried verbatim from the blueprint lane:
     · every mark lands PROVISIONAL and carries NO quantity until a
       human confirms it — unconfirmed marks are listed and named;
     · scale is LOCAL TO THIS PHOTO (two-tap anchor or typed tape;
       THE TAPE WINS). No scale → no quantity, and the refusal is named;
     · openings are REPORTED, never deducted (phase 1);
     · Apply writes ft²/counts only — no money, ever.  */

// SEND-142 — the shared mark vocabulary (colours, categories, tap order,
// labels) moved to ./phototakeoff/marks so the three rail panels and this
// editor read ONE declaration each.

const polyAreaPx = (pts) => {
  if (!pts || pts.length < 3) return 0;
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const q = pts[(i + 1) % pts.length];
    a += pts[i].x * q.y - q.x * pts[i].y;
  }
  return Math.abs(a) / 2;
};
const inPerPx = (scale) => {
  if (!scale || !scale.span_px) return null;
  if (scale.tape_inches) return { ipp: scale.tape_inches / scale.span_px, basis: "tape" };
  const inches = scale.anchor?.inches;
  if (!inches) return null;
  return { ipp: inches / scale.span_px, basis: "anchor" };
};
const ftin = (ft, inch) => {
  const f = parseFloat(ft || 0) || 0;
  const i = parseFloat(inch || 0) || 0;
  const total = f * 12 + i;
  return total > 0 ? total : null;
};

export default function PhotoTakeoffEditor({ est, photoUrl, photoKey, onClose }) {
  const [marks, setMarks] = useState([]);
  const [scale, setScale] = useState(null);
  const [qty, setQty] = useState(null);
  const [stage, setStage] = useState(null);          // {stage, ai_read, stage_note, proposals_refusal}
  const [products, setProducts] = useState([]);
  const [productsNote, setProductsNote] = useState(null);
  const [tool, setTool] = useState("siding_zone");   // siding_zone | non_siding_zone | opening | gable | dormer | scale
  const [category, setCategory] = useState("brick");
  const [draft, setDraft] = useState(null);          // {points:[{x,y}] norm, cx, cy}
  const [scaleDraft, setScaleDraft] = useState(null);// {p1,p2} norm
  const [scaleAsk, setScaleAsk] = useState(null);    // {p1,p2}
  const [spanFt, setSpanFt] = useState("");
  const [spanIn, setSpanIn] = useState("");
  const [tapeFt, setTapeFt] = useState("");
  const [tapeIn, setTapeIn] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [dragVertex, setDragVertex] = useState(null); // {markId, index}
  const [imgNat, setImgNat] = useState({ w: 0, h: 0 });
  const [zoom, setZoom] = useState(1);
  const [busy, setBusy] = useState(false);

  const imgRef = useRef(null);
  const scrollRef = useRef(null);
  const wheelAnchor = useRef(null);
  const marksRef = useRef([]);
  const pinch = useRef(null);
  useEffect(() => { marksRef.current = marks; }, [marks]);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/estimates/${est.id}/photo-takeoff`, { params: { photo_key: photoKey } });
      setMarks(data.marks || []);
      const per = (data.per_photo || {})[photoKey] || {};
      setScale(per.scale || null);
      setQty(per.quantities || null);
      setStage({ stage: per.stage || 1, ai_read: per.ai_read || null,
        stage_note: per.stage_note, proposals_refusal: per.proposals_refusal });
      setProducts(data.products || []);
      setProductsNote(data.products_note || null);
    } catch { toast.error("Could not read this photo's takeoff"); }
  }, [est.id, photoKey]);
  useEffect(() => { load(); }, [load]);

  const sc = useMemo(() => inPerPx(scale), [scale]);
  const sqftOf = (m) => {
    if (!sc) return null;
    const pts = m.points || [];
    if (pts.length < 3) return null;
    return Math.round(polyAreaPx(pts) * ((sc.ipp * sc.ipp) / 144) * 100) / 100;
  };

  // ── geometry plumbing (PdfOverlayEditor's convention: normalise against
  // the RENDERED rect exactly once, so zoom cancels and a vertex drag
  // tracks the pointer 1:1 at any zoom) ──────────────────────────────
  const normFromEvent = (e) => {
    const r = imgRef.current.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
      y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
    };
  };
  const toNat = (p) => ({ x: p.x * imgNat.w, y: p.y * imgNat.h });
  const toNorm = (p) => ({ x: imgNat.w ? p.x / imgNat.w : 0, y: imgNat.h ? p.y / imgNat.h : 0 });

  useEffect(() => {
    if (!dragVertex) return;
    const up = () => {
      const m = marksRef.current.find((x) => x.id === dragVertex.markId);
      setDragVertex(null);
      if (m) patchMark(m.id, { points: m.points });
    };
    const move = (e) => {
      if (!imgRef.current) return;
      if (e.pointerType === "mouse" && e.buttons === 0) { up(); return; }
      const nat = toNat(normFromEvent(e));
      setMarks((cur) => cur.map((m) => m.id === dragVertex.markId
        ? { ...m, points: m.points.map((p, i) => (i === dragVertex.index ? nat : p)) }
        : m));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dragVertex]);

  // ── server calls ───────────────────────────────────────────────────
  const addMark = async (points, shape, extra = {}) => {
    try {
      const body = {
        photo_key: photoKey, kind: tool, shape,
        points: points.map(toNat),
        category: tool === "non_siding_zone" ? category : null,
        ...extra,
      };
      const { data } = await api.post(`/estimates/${est.id}/photo-takeoff/marks`, body);
      await load();
      // SEND-147 — the tap moved the box, so say so and say what it did not move.
      if (data?.rebase?.moved) toast.success(`${tool === "eave" ? "Eave" : "Start"} line set — ${data.rebase.moved} provisional zone(s) moved to it`);
      (data?.rebase?.notes || []).forEach((n) => toast.info(n));
      if (!sc && tool !== "wall_base" && tool !== "eave") toast.warning("No scale on this photo yet — the mark saves, but it carries no quantity until you set the scale");
    } catch (e) { toast.error(e?.response?.data?.detail || "The mark was refused"); }
  };
  const patchMark = async (id, body) => {
    try {
      const { data } = await api.patch(`/estimates/${est.id}/photo-takeoff/marks/${id}`, body);
      if (data?.mark?.refused_reason === "geometry changed after confirmation — re-confirm the new figure") {
        toast.warning("Geometry changed — that mark went back to PROVISIONAL; confirm the new figure");
      }
      await load();
      if (data?.rebase?.moved) toast.success(`Start line moved — ${data.rebase.moved} provisional zone(s) followed it`);
      (data?.rebase?.notes || []).forEach((n) => toast.info(n));
    } catch (e) { toast.error(e?.response?.data?.detail || "The change was refused"); }
  };
  const delMark = async (id) => {
    try {
      const { data } = await api.delete(`/estimates/${est.id}/photo-takeoff/marks/${id}`);
      if (selectedId === id) setSelectedId(null);
      await load();
      if (data?.rebase?.moved) toast.info(`Start line deleted — ${data.rebase.moved} provisional zone(s) went back to the read's own answer`);
    } catch { toast.error("Could not delete that mark"); }
  };
  const commitScale = async (p1, p2, inches) => {
    try {
      const { data } = await api.put(`/estimates/${est.id}/photo-takeoff/scale`, {
        photo_key: photoKey, anchor: { p1: toNat(p1), p2: toNat(p2), inches },
      });
      setScaleAsk(null); setSpanFt(""); setSpanIn("");
      await load();
      if (data.refusal) toast.warning(data.refusal);
    } catch (e) { toast.error(e?.response?.data?.detail || "The scale was refused"); }
  };
  const commitTape = async () => {
    const inches = ftin(tapeFt, tapeIn);
    if (!inches) { toast.error("Type the taped figure for that same span"); return; }
    try {
      await api.put(`/estimates/${est.id}/photo-takeoff/scale`, { photo_key: photoKey, tape_inches: inches });
      setTapeFt(""); setTapeIn("");
      await load();
      toast.success("Tape set — THE TAPE GOVERNS this photo's scale");
    } catch (e) { toast.error(e?.response?.data?.detail || "The tape was refused"); }
  };
  const clearScale = async () => {
    await api.put(`/estimates/${est.id}/photo-takeoff/scale`, { photo_key: photoKey, clear: true });
    await load();
  };
  const importAnnotations = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/estimates/${est.id}/photo-takeoff/import-annotations`, null, { params: { photo_key: photoKey } });
      await load();
      toast.success(data.imported ? `${data.imported} mark(s) pulled in — all PROVISIONAL` : "Nothing new to pull in");
      if (data.scale_note) toast.info(data.scale_note);
    } catch (e) { toast.error(e?.response?.data?.detail || "Import failed"); }
    setBusy(false);
  };
  const pullProposals = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/estimates/${est.id}/photo-takeoff/propose`, null, { params: { photo_key: photoKey } });
      await load();
      toast.success(data.proposed
        ? `${data.proposed} AI proposal(s) on this photo — all PROVISIONAL until you rule on them`
        : "Nothing new — this read's proposals are already here");
      if (data.openings_without_a_box_note) toast.warning(data.openings_without_a_box_note);
      Object.values(data.kinds_absent || {}).forEach((n) => toast.info(n));
    } catch (e) { toast.error(e?.response?.data?.detail || "The read had nothing to propose here"); }
    setBusy(false);
  };
  const pullZones = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/estimates/${est.id}/photo-takeoff/propose-zones`, null, { params: { photo_key: photoKey } });
      await load();
      if (data.refusal) toast.warning(data.refusal);
      else if (data.moved) toast.success(
        `${data.face?.toUpperCase()} — ${data.moved} zone(s) MOVED to the wall_base line you tapped${data.proposed ? `, ${data.proposed} newly placed` : ""}`);
      else toast.success(data.proposed
        ? `${data.face?.toUpperCase()} — ${data.proposed} starting zone(s) placed, all PROVISIONAL: move them onto the wall you see, then confirm`
        : `${data.face?.toUpperCase()} — this read's starting zones are already here; nothing was overwritten`);
      (data.notes || []).forEach((n) => toast.info(n));
      if (data.openings?.note) toast.warning(data.openings.note);
    } catch (e) { toast.error(e?.response?.data?.detail || "There were no findings to hand off here"); }
    setBusy(false);
  };
  const apply = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/estimates/${est.id}/photo-takeoff/apply`);
      const b = data.photo_takeoff;
      toast.success(`Quantities written — siding ${b.photo_siding_sqft ?? "—"} ft² · non-siding ${b.photo_non_siding_sqft ?? "—"} ft² · openings ${b.photo_opening_count ?? "—"}. No money written.`);
    } catch (e) {
      toast.error(e?.response?.status === 423
        ? "Protected estimate — this derived write is refused (423)"
        : (e?.response?.data?.detail || "Apply failed"));
    }
    setBusy(false);
  };

  // ── drawing ────────────────────────────────────────────────────────
  const onPointerDown = (e) => {
    if (!imgRef.current || pinch.current) return;
    if (e.pointerType === "touch" && e.isPrimary === false) return;
    const p = normFromEvent(e);
    if (tool === "scale") {
      if (!scaleDraft?.p1) { setScaleDraft({ p1: p, p2: p }); return; }
      const d = Math.hypot((p.x - scaleDraft.p1.x) * imgNat.w, (p.y - scaleDraft.p1.y) * imgNat.h);
      if (d < 8) { toast.error("Second tap too close — tap the other end of the known span"); return; }
      setScaleAsk({ p1: scaleDraft.p1, p2: p });
      setScaleDraft(null);
      return;
    }
    if (dragVertex) return;
    const pts = draft?.points || [];
    // SEND-147 — THE WALL BASE IS A TWO-TAP LINE: left end, then right end.
    // Same gesture as the scale, and it is stored as an ANCHOR — no LF.
    if (tool === "wall_base" || tool === "eave") {
      if (!pts.length) { setDraft({ points: [p], cx: p.x, cy: p.y }); return; }
      const d = Math.hypot((p.x - pts[0].x) * imgNat.w, (p.y - pts[0].y) * imgNat.h);
      if (d < 8) { toast.error(`Second tap too close — tap the OTHER end of the ${tool === "eave" ? "eave" : "start"} line`); return; }
      setDraft(null);
      addMark([pts[0], p], "line");
      return;
    }
    if (tool === "opening") {
      // an opening is a TWO-TAP BOX — tap one corner, tap the opposite one
      if (!pts.length) { setDraft({ points: [p], cx: p.x, cy: p.y }); return; }
      const a = pts[0];
      setDraft(null);
      addMark([a, { x: p.x, y: a.y }, p, { x: a.x, y: p.y }], "rect");
      return;
    }
    // SEND-139 — GABLE: three taps, LEFT EAVE → PEAK → RIGHT EAVE.
    // DORMER: four taps round the vertical face. The annotator's gesture,
    // unchanged; the count is fixed, so nothing is padded to fit.
    if (tool === "gable" || tool === "dormer") {
      const need = tool === "gable" ? 3 : 4;
      const next = [...pts, p];
      if (next.length < need) { setDraft({ points: next, cx: p.x, cy: p.y }); return; }
      setDraft(null);
      addMark(next, "poly");
      return;
    }
    if (pts.length >= 3) {
      const d = Math.hypot(pts[0].x - p.x, pts[0].y - p.y);
      if (d < 0.02) { setDraft(null); addMark(pts, "poly"); return; }
    }
    setDraft({ points: [...pts, p], cx: p.x, cy: p.y });
  };
  const onPointerMove = (e) => {
    if (!imgRef.current || dragVertex) return;
    const p = normFromEvent(e);
    if (tool === "scale" && scaleDraft?.p1) { setScaleDraft({ ...scaleDraft, p2: p }); return; }
    if (draft) setDraft({ ...draft, cx: p.x, cy: p.y });
  };
  useEffect(() => {
    const h = (e) => {
      if (e.key === "Escape") { setDraft(null); setScaleDraft(null); setScaleAsk(null); }
      if (e.key === "Enter" && draft?.points?.length >= 3
          && tool !== "opening" && tool !== "gable" && tool !== "dormer") {
        const pts = draft.points; setDraft(null); addMark(pts, "poly");
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, tool, category, sc]);

  // ── zoom: wheel (cursor-anchored) + PINCH on a phone ───────────────
  const bumpZoom = (f) => setZoom((z) => Math.max(0.5, Math.min(6, z * f)));
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const ox = e.clientX - rect.left;
      const oy = e.clientY - rect.top;
      wheelAnchor.current = {
        fx: el.scrollWidth ? (el.scrollLeft + ox) / el.scrollWidth : 0.5,
        fy: el.scrollHeight ? (el.scrollTop + oy) / el.scrollHeight : 0.5,
        ox, oy,
      };
      bumpZoom(e.deltaY < 0 ? 1.1 : 1 / 1.1);
    };
    const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
    const onTouchStart = (e) => {
      if (e.touches.length !== 2) return;
      pinch.current = { d0: dist(e.touches), z0: zoom };
      setDraft(null); setScaleDraft(null);
    };
    const onTouchMove = (e) => {
      if (!pinch.current || e.touches.length !== 2) return;
      e.preventDefault();
      const ratio = dist(e.touches) / (pinch.current.d0 || 1);
      setZoom(Math.max(0.5, Math.min(6, pinch.current.z0 * ratio)));
    };
    const onTouchEnd = (e) => { if (e.touches.length < 2) setTimeout(() => { pinch.current = null; }, 120); };
    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: false });
    el.addEventListener("touchend", onTouchEnd, { passive: true });
    return () => {
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
      el.removeEventListener("touchend", onTouchEnd);
    };
  }, [zoom]);
  useLayoutEffect(() => {
    const el = scrollRef.current;
    const a = wheelAnchor.current;
    if (!el || !a) return;
    el.scrollLeft = a.fx * el.scrollWidth - a.ox;
    el.scrollTop = a.fy * el.scrollHeight - a.oy;
    wheelAnchor.current = null;
  }, [zoom]);

  // SEND-139 — the annotator's own gable/dormer math, on this photo's
  // scale. gableDims returns base, rise, pitch and grossAreaFt = ½ ×
  // base × rise; dormerDims averages the opposing edges. Nothing here is
  // a second implementation of either.
  const gDims = (m) => (m.kind === "gable" ? gableDims(m.points, sc?.ipp || null)
    : m.kind === "dormer" ? dormerDims(m.points, sc?.ipp || null) : null);

  // PITCH → PEAK, ported verbatim: rise = base/2 × pitch/12. The peak
  // MOVES, which is a geometry change — a confirmed gable returns to
  // provisional, exactly as any other adjustment does.
  const applyGablePitch = (m, pitch) => {
    const [L, P, R] = m.points;
    const basePx = Math.hypot(R.x - L.x, R.y - L.y);
    if (basePx <= 0) { toast.error("this gable has no width — re-tap the eave points"); return; }
    const risePx = (basePx / 2) * (pitch / 12);
    const mid = { x: (L.x + R.x) / 2, y: (L.y + R.y) / 2 };
    const peakX = m.symmetric ? mid.x : P.x;
    patchMark(m.id, { points: [L, { x: peakX, y: mid.y - risePx }, R], pitch_set: pitch });
  };
  const toggleSymmetric = (m) => {
    const sym = !m.symmetric;
    const pts = m.points.map((q) => ({ ...q }));
    if (sym) pts[1] = { x: (pts[0].x + pts[2].x) / 2, y: pts[1].y };
    patchMark(m.id, { symmetric: sym, points: pts });
  };

  // SEND-141 (Howard ruled 2026-08-27) — A REFUSED ROW SHOWS NO NUMBER.
  // The figure a refused mark used to print was the FLAT POLYGON'S PIXEL
  // AREA — 0 — and next to REFUSED it read as a measured zero. It is not
  // a takeoff, so it is not promoted anywhere: the cell is an EM DASH.
  // Never 0, never 0.0, never 0 ft². The receipt stays, the reason stays,
  // and a measured gable still prints ½ × width × rise.
  // The FACE refusal blanks the cell; a CHEEK refusal never does — that
  // face was drawn and measured (SEND-140).
  const figureRefused = (id) => {
    const row = [...(qty?.gable_rows || []), ...(qty?.dormer_rows || [])]
      .find((r) => r.id === id);
    return !!(row && row.refusal);
  };
  // The same rule for any ft² figure on a panel: a number only when there
  // IS one. 0.0 ft² beside a refusal is the same measured-zero lie.
  const ft2 = (v) => (v > 0 ? `${v.toFixed(1)} ft²` : "—");

  // The ONE place that decides what a mark's quantity cell may say.
  const qtyCell = (m, a) => {
    // SEND-147 — A WALL BASE IS AN ANCHOR, NOT A QUANTITY: no ft², and above
    // all NO LF. It prints what it is.
    if (m.kind === "wall_base" || m.kind === "eave") return "anchor · no LF";
    if (m.shape === "point") return "count only — no drawn extent";
    if (a == null) return "no scale";
    if (m.status === "refused" || figureRefused(m.id) || !(a > 0)) return "—";
    return `${a} ft²`;
  };

  // SEND-140 — the receipt comes from the SERVER's own refusal, keyed by
  // mark id. Nothing about the reason is re-decided here.
  const receiptFor = (id) => ([...(qty?.gable_receipts || []),
    ...(qty?.dormer_receipts || [])].find((r) => r.id === id) || {}).receipt || null;

  const nMark = (m) => (m.points || []).map(toNorm);
  const TOOLS = [
    { key: "siding_zone", label: "Siding zone", color: SIDING },
    { key: "non_siding_zone", label: "Non-siding", color: CATEGORIES.find((c) => c.key === category)?.color },
    { key: "opening", label: "Opening", color: OPENING },
    { key: "gable", label: "Gable", color: GABLE },
    { key: "dormer", label: "Dormer", color: DORMER },
    // SEND-147 — the two-tap START LINE. An anchor, not a trim run: it
    // carries no LF and it is never priced.
    { key: "wall_base", label: "Wall base", color: WALL_BASE },
    // SEND-149 — the two-tap EAVE / frieze line. Sets the body TOP. Also an
    // anchor: no LF, never priced, and it is not a soffit or a fascia.
    { key: "eave", label: "Eave", color: EAVE },
    { key: "scale", label: "Scale", color: "#10B981" },
  ];

  return (
    <div className="fixed inset-0 z-[70] bg-black/70 flex items-center justify-center p-2" data-testid="photo-takeoff-modal">
      <div className="bg-[var(--surface)] w-full h-[95vh] max-w-7xl flex flex-col border border-[var(--border)]">
        <div className="bg-[var(--ai)] text-white px-4 py-2.5 flex items-center justify-between">
          <div className="min-w-0">
            <div className="font-heading text-base">Photo Takeoff — phase 1</div>
            <div className="text-[11px] opacity-90 truncate">{photoKey} · siding · non-siding · openings · gables · dormers — confirmed marks carry quantity, never money</div>
          </div>
          <button type="button" onClick={onClose} className="text-white/90 hover:text-white" data-testid="photo-takeoff-close"><X size={18} /></button>
        </div>

        <div className="px-3 py-1.5 bg-[#FEF3C7] border-b border-[#F59E0B] text-[10px] font-bold text-[var(--warning-text)] flex items-center gap-1.5" data-testid="photo-takeoff-known-limit">
          <AlertTriangle className="w-3 h-3 flex-shrink-0" />
          Phase 1: areas, openings, gables, dormers and the two anchor lines — WALL BASE (body bottom) and EAVE (body top), both anchors: no LF, never priced. Trim runs (corners, J-channel, starter, soffit, fascia) are NOT built. Openings are reported — nothing is deducted from siding.
        </div>

        {/* ONE EDITOR, TWO STAGES. The stage is decided by THIS photo's own
            read — a read on another photo unlocks nothing here. */}
        <div
          className={`px-3 py-2 border-b flex flex-col md:flex-row md:items-center gap-1.5 md:gap-3 ${stage?.stage === 2 ? "bg-[#ECFDF5] border-[#10B981]" : "bg-[#EFF6FF] border-[#3B82F6]"}`}
          data-testid="photo-takeoff-stage-banner"
        >
          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 text-white ${stage?.stage === 2 ? "bg-[var(--success)]" : "bg-[var(--ai)]"}`}>
            {stage?.stage === 2 ? "Stage 2 — after AI" : "Stage 1 — before AI"}
          </span>
          <span className="text-[10px] text-[var(--ink-2)] leading-snug flex-1" data-testid="photo-takeoff-stage-note">
            {stage?.stage_note || "Reading this photo's state…"}
          </span>
          <button
            type="button" onClick={pullProposals} disabled={busy || stage?.stage !== 2}
            title={stage?.proposals_refusal || "Pull this photo's AI proposals"}
            className="inline-flex items-center gap-1 px-2 py-1 border text-[10px] font-bold uppercase tracking-wider disabled:opacity-40 disabled:cursor-not-allowed border-[var(--success)] text-[var(--success)]"
            data-testid="photo-takeoff-propose-btn"
          >
            <Sparkles className="w-3 h-3" /> AI proposals
          </button>
          <button
            type="button" onClick={pullZones} disabled={busy || stage?.stage !== 2}
            title={stage?.proposals_refusal || "Pull this face's starting zones from the finished read"}
            className="inline-flex items-center gap-1 px-2 py-1 border text-[10px] font-bold uppercase tracking-wider disabled:opacity-40 disabled:cursor-not-allowed border-[var(--ai)] text-[var(--ai)]"
            data-testid="photo-takeoff-zones-btn"
          >
            <Sparkles className="w-3 h-3" /> starting zones
          </button>
        </div>
        {stage?.proposals_refusal && (
          <div className="px-3 py-1 bg-white border-b border-[var(--border)] text-[10px] text-[var(--warning-text)]" data-testid="photo-takeoff-proposals-refusal">
            AI proposals are off on this photo: {stage.proposals_refusal}
          </div>
        )}

        <div className="flex-1 flex min-h-0 flex-col md:flex-row">
          {/* canvas */}
          <div className="flex-1 relative min-w-0 min-h-0">
            <div ref={scrollRef} className="absolute inset-0 overflow-auto bg-[#27272A] touch-pan-x touch-pan-y">
              <div className="p-3">
                <div className="relative" style={{ width: `${zoom * 100}%`, lineHeight: 0 }}>
                  <img
                    ref={imgRef} src={photoUrl} alt={photoKey} draggable={false}
                    className="select-none" style={{ display: "block", width: "100%", height: "auto", cursor: "crosshair", touchAction: "none" }}
                    onLoad={(e) => setImgNat({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                    onPointerDown={onPointerDown} onPointerMove={onPointerMove}
                    data-testid="photo-takeoff-canvas-img"
                  />
                  <svg className="absolute top-0 left-0 pointer-events-none" style={{ width: "100%", height: "100%" }} viewBox="0 0 100 100" preserveAspectRatio="none">
                    {marks.map((m) => {
                      const pts = nMark(m);
                      const col = markColor(m);
                      const sel = m.id === selectedId;
                      if (pts.length === 2) {
                        // SEND-147 — the WALL BASE start line. Two ends, one
                        // stored y, no LF anywhere near it.
                        return (
                          <line key={m.id} x1={pts[0].x * 100} y1={pts[0].y * 100}
                            x2={pts[1].x * 100} y2={pts[1].y * 100}
                            stroke={col} strokeWidth={sel ? "1" : "0.7"}
                            strokeDasharray={m.status === "confirmed" ? "0" : m.status === "refused" ? "0.8 0.8" : "2 1.2"} />
                        );
                      }
                      if (pts.length < 3) {
                        return pts.length === 1 ? (
                          <circle key={m.id} cx={pts[0].x * 100} cy={pts[0].y * 100} r={sel ? 1.4 : 1}
                            fill={m.status === "confirmed" ? col : "none"} stroke={col} strokeWidth="0.5" />
                        ) : null;
                      }
                      return (
                        <polygon
                          key={m.id}
                          points={pts.map((p) => `${p.x * 100},${p.y * 100}`).join(" ")}
                          fill={`${col}${m.status === "confirmed" ? "44" : m.status === "refused" ? "08" : "18"}`}
                          stroke={col} strokeWidth={sel ? "0.7" : "0.4"}
                          strokeDasharray={m.status === "confirmed" ? "0" : m.status === "refused" ? "0.8 0.8" : "2 1.2"}
                        />
                      );
                    })}
                    {draft?.points?.length > 0 && (
                      <polyline
                        points={[...draft.points, { x: draft.cx, y: draft.cy }].map((p) => `${p.x * 100},${p.y * 100}`).join(" ")}
                        fill="none" stroke={tool === "opening" ? OPENING : tool === "siding_zone" ? SIDING : CATEGORIES.find((c) => c.key === category)?.color}
                        strokeWidth="0.4" strokeDasharray="1 0.5"
                      />
                    )}
                    {scaleDraft?.p1 && (
                      <line x1={scaleDraft.p1.x * 100} y1={scaleDraft.p1.y * 100} x2={scaleDraft.p2.x * 100} y2={scaleDraft.p2.y * 100}
                        stroke="#10B981" strokeWidth="0.5" strokeDasharray="2 1" />
                    )}
                    {scale?.anchor && imgNat.w > 0 && (
                      <line
                        x1={(scale.anchor.p1.x / imgNat.w) * 100} y1={(scale.anchor.p1.y / imgNat.h) * 100}
                        x2={(scale.anchor.p2.x / imgNat.w) * 100} y2={(scale.anchor.p2.y / imgNat.h) * 100}
                        stroke="#10B981" strokeWidth="0.5" />
                    )}
                    <CandidateEdges marks={marks} nMark={nMark} />
                  </svg>
                  {/* vertex handles on the selected mark — drag tracks 1:1 at any zoom */}
                  {marks.filter((m) => m.id === selectedId).map((m) => nMark(m).map((p, i) => (
                    <div
                      key={`${m.id}-${i}`}
                      onPointerDown={(e) => { e.stopPropagation(); setDragVertex({ markId: m.id, index: i }); }}
                      className="absolute w-3.5 h-3.5 -ml-[7px] -mt-[7px] rounded-full bg-white border-2 cursor-move"
                      style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%`, borderColor: markColor(m), touchAction: "none" }}
                      data-testid={`photo-takeoff-vertex-${m.id}-${i}`}
                    />
                  )))}
                  {marks.filter((m) => (m.points || []).length === 2).map((m) => {
                    const p = nMark(m)[0];
                    return (
                      <div key={`lbl2-${m.id}`} className="absolute text-white font-bold pointer-events-none"
                        style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%`, background: markColor(m), fontSize: "9px", padding: "1px 3px", lineHeight: 1 }}
                        data-testid={`photo-takeoff-line-label-${m.id}`}>
                        {kindLabel(m)}·y {Math.round(m.wall_base?.y ?? m.eave?.y ?? 0)}px{m.status !== "confirmed" ? `·${m.status === "refused" ? "refused" : "provisional"}` : ""}
                      </div>
                    );
                  })}
                  {marks.filter((m) => (m.points || []).length >= 3).map((m) => {
                    const p = nMark(m)[0];
                    const a = sqftOf(m);
                    return (
                      <div key={`lbl-${m.id}`} className="absolute text-white font-bold pointer-events-none"
                        style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%`, background: markColor(m), fontSize: "9px", padding: "1px 3px", lineHeight: 1 }}>
                        {kindLabel(m)}·{qtyCell(m, a)}{m.status !== "confirmed" ? `·${m.status === "refused" ? "refused" : "provisional"}` : ""}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <div className="absolute top-2 right-2 z-30 flex flex-col gap-1 w-fit">
              <button type="button" onClick={() => bumpZoom(1.25)} className="w-8 h-8 bg-white/95 border border-[#27272A] flex items-center justify-center shadow-md" data-testid="photo-takeoff-zoom-in"><ZoomIn className="w-4 h-4" /></button>
              <button type="button" onClick={() => setZoom(1)} className="px-1 h-8 bg-white/95 border border-[#27272A] text-[9px] font-bold shadow-md" data-testid="photo-takeoff-zoom-reset">{Math.round(zoom * 100)}%</button>
              <button type="button" onClick={() => bumpZoom(1 / 1.25)} className="w-8 h-8 bg-white/95 border border-[#27272A] flex items-center justify-center shadow-md" data-testid="photo-takeoff-zoom-out"><ZoomOut className="w-4 h-4" /></button>
            </div>
            {/* tools */}
            <div className="absolute bottom-2 left-2 z-30 flex flex-wrap gap-1 bg-white/95 border border-[#27272A] p-1.5">
              {TOOLS.map((t) => (
                <button key={t.key} type="button"
                  onClick={() => { setTool(t.key); setDraft(null); setScaleDraft(null); }}
                  className={`px-2 py-1 text-[10px] font-bold uppercase tracking-wider border ${tool === t.key ? "text-white" : "text-[var(--ink-2)] border-[var(--border)]"}`}
                  style={tool === t.key ? { background: t.color, borderColor: t.color } : {}}
                  data-testid={`photo-takeoff-tool-${t.key}`}>{t.label}</button>
              ))}
              {tool === "non_siding_zone" && CATEGORIES.map((c) => (
                <button key={c.key} type="button" onClick={() => setCategory(c.key)}
                  className={`px-2 py-1 text-[10px] font-bold uppercase border ${category === c.key ? "text-white" : ""}`}
                  style={category === c.key ? { background: c.color, borderColor: c.color } : { color: c.color, borderColor: c.color }}
                  data-testid={`photo-takeoff-category-${c.key}`}>{c.name}</button>
              ))}
              <span className="text-[9px] text-[var(--muted)] px-1 self-center">
                {tool === "scale" ? "tap both ends of a known span"
                  : tool === "opening" ? "tap two opposite corners"
                    : TAP_ORDER[tool]
                      ? TAP_ORDER[tool][(draft?.points?.length || 0)] || TAP_ORDER[tool][0]
                      : "tap each corner · tap the first again to close"}
                {tool === "wall_base" ? " — an ANCHOR for the AI body bottom, never an LF run"
                  : tool === "eave" ? " — an ANCHOR for the AI body top, never an LF run (not a soffit, not a fascia)" : ""}
              </span>
            </div>
          </div>

          {/* right rail */}
          <div className="w-full md:w-80 border-t md:border-t-0 md:border-l border-[var(--border)] flex flex-col overflow-y-auto">
            <ScalePanel sc={sc} scale={scale} qty={qty} setTool={setTool}
              setScaleDraft={setScaleDraft} clearScale={clearScale}
              tapeFt={tapeFt} setTapeFt={setTapeFt} tapeIn={tapeIn}
              setTapeIn={setTapeIn} commitTape={commitTape} />

            <QuantitiesPanel qty={qty} />

            {qty?.trim_rows?.length ? <TrimPanel qty={qty} /> : null}

            <MarksPanel marks={marks} selectedId={selectedId}
              setSelectedId={setSelectedId} busy={busy} products={products}
              productsNote={productsNote} sqftOf={sqftOf} qtyCell={qtyCell}
              receiptFor={receiptFor} gDims={gDims} ft2={ft2}
              patchMark={patchMark} delMark={delMark}
              importAnnotations={importAnnotations}
              toggleSymmetric={toggleSymmetric}
              applyGablePitch={applyGablePitch} />

            <div className="p-3 border-t border-[var(--border)]">
              <button type="button" onClick={apply} disabled={busy}
                className="w-full px-3 py-2 bg-[var(--ai)] text-white text-[11px] font-bold uppercase tracking-wider disabled:opacity-50"
                data-testid="photo-takeoff-apply-btn">
                Write quantities to the estimate
              </button>
              <div className="text-[9px] text-[var(--muted)] mt-1 leading-snug">
                ft², counts — the photo lane only. No price, no priced line, no money. Protected estimates refuse (423).
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* the two-tap span asks for its real length */}
      {scaleAsk && (
        <div className="absolute inset-0 z-[80] bg-black/50 flex items-center justify-center p-4" data-testid="photo-takeoff-scale-ask">
          <div className="bg-white border border-[var(--border)] max-w-sm w-full p-4">
            <div className="font-heading text-sm mb-1">How long is that span, really?</div>
            <div className="text-[11px] text-[var(--muted)] mb-3">
              This is the scale for THIS photo only. Nothing is carried from a blueprint or another photo.
            </div>
            <div className="flex items-center gap-1">
              <input value={spanFt} onChange={(e) => setSpanFt(e.target.value)} placeholder="ft" inputMode="decimal"
                className="w-16 border border-[var(--border)] px-2 py-1.5 text-sm" data-testid="photo-takeoff-span-ft" autoFocus />
              <input value={spanIn} onChange={(e) => setSpanIn(e.target.value)} placeholder="in" inputMode="decimal"
                className="w-16 border border-[var(--border)] px-2 py-1.5 text-sm" data-testid="photo-takeoff-span-in" />
              <button type="button"
                onClick={() => {
                  const inches = ftin(spanFt, spanIn);
                  if (!inches) { toast.error("Type the real length of that span — it is never guessed"); return; }
                  commitScale(scaleAsk.p1, scaleAsk.p2, inches);
                }}
                className="px-3 py-1.5 bg-[var(--ai)] text-white text-[11px] font-bold uppercase" data-testid="photo-takeoff-span-commit">set scale</button>
              <button type="button" onClick={() => setScaleAsk(null)} className="px-2 py-1.5 border border-[var(--border)] text-[11px] uppercase" data-testid="photo-takeoff-span-cancel">cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
