// Iter 79j.22 — 3D House Model view for the AI Measure preview.
//
// Builds a parametric 3D house from the current AI-measure `preview`:
//   footprint W×D  ← approximated from front/back/left/right wall widths
//   eaveHeight     ← measurements._ai_avg_wall_height_ft (may be defaulted)
//   roof pitch     ← DEFAULTED (Claude doesn't extract pitch reliably)
//   openings       ← raw_ai.openings, auto-spaced across each wall
//
// SSOT rule (per Howard 2026-02-28):
//   The side panel's "Squares / J-channel / corner post / starter"
//   values are read DIRECTLY from `preview.lines` — never re-implemented
//   here. The whole-house totals section reflects the exact same numbers
//   the estimator ships. Per-facade sqft/openings come from
//   `preview.measurements._per_elevation_breakdown` (already computed
//   server-side).
//
// Editable overrides:
//   • roof pitch (dropdown)  • eave height (number)  • per-wall width
//   Overrides update the 3D drawing LIVE (visuals only) but do NOT
//   silently recompute line quantities. A prominent hint tells the
//   contractor to hit Re-run if they want the estimator to reflect the
//   override. This preserves single-source-of-truth.

import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";
import { AlertTriangle } from "lucide-react";

const ROOF_PITCHES = [4, 6, 8, 10, 12];
const DEFAULT_PITCH = 6;
const DEFAULT_EAVE_HEIGHT = 10;
const AMBER = "#F59E0B";

function pitchRise(widthFt, pitchOver12) {
  // rise across HALF the roof span, e.g. 6/12 on a 40 ft span = 20 × 6/12 = 10 ft.
  return (widthFt / 2) * (pitchOver12 / 12);
}

// Build a house-JSON shape from the AI preview + user overrides.
function buildHouseJson(preview, overrides) {
  if (!preview) return null;
  const walls = preview.raw_ai?.walls || [];
  const openings = preview.raw_ai?.openings || [];
  const eave = overrides.eaveHeight
    ?? preview.measurements?._ai_avg_wall_height_ft
    ?? DEFAULT_EAVE_HEIGHT;
  const pitch = overrides.pitch ?? DEFAULT_PITCH;
  // Match primary walls by label. If a label is missing, keep the wall
  // but flag "estimated" in the UI.
  const findWall = (lab) => walls.find((w) => (w.label || "").toLowerCase() === lab);
  const front = findWall("front");
  const back = findWall("back");
  const left = findWall("left");
  const right = findWall("right");
  const widthFront = overrides.widths?.front ?? front?.width_ft ?? 32;
  const widthBack = overrides.widths?.back ?? back?.width_ft ?? widthFront;
  const widthLeft = overrides.widths?.left ?? left?.width_ft ?? 24;
  const widthRight = overrides.widths?.right ?? right?.width_ft ?? widthLeft;
  const footprintW = Math.max(widthFront, widthBack);
  const footprintD = Math.max(widthLeft, widthRight);

  const openingsByWall = openings.reduce((acc, o) => {
    const k = (o.wall || "other").toLowerCase();
    (acc[k] = acc[k] || []).push(o);
    return acc;
  }, {});
  const autoSpace = (list, wallWidth) => {
    if (!list?.length) return [];
    const n = list.length;
    return list.map((o, i) => {
      const w = (o.width_in || 36) / 12;
      const h = (o.height_in || 48) / 12;
      const slot = wallWidth / n;
      const cx = slot * (i + 0.5);
      const y = (o.type || "").toLowerCase().includes("door") ? 0 : 3.2;
      return {
        type: (o.type || "window").toLowerCase().includes("door") ? "door" : "window",
        style: o.style,
        x: Math.max(0.5, cx - w / 2),
        y,
        w,
        h,
        confidence: o.style_confidence ?? o.confidence ?? null,
      };
    });
  };

  const mkFacade = (id, label, widthOverride, wallData) => ({
    id,
    label,
    width: widthOverride,
    gableEnd: id === "left" || id === "right",
    confidence: wallData?.confidence ?? null,
    estimated: !wallData,
    openings: autoSpace(openingsByWall[id] || [], widthOverride),
  });
  return {
    footprint: { width: footprintW, depth: footprintD, estimated: !front || !left },
    eaveHeight: eave,
    eaveHeightEstimated: overrides.eaveHeight == null && preview.measurements?._ai_avg_wall_height_ft == null,
    roof: { type: "gable", pitch, ridgeAxis: "x", overhang: 1.25, pitchEstimated: overrides.pitch == null },
    facades: [
      mkFacade("front", "Front elevation", widthFront, front),
      mkFacade("right", "Right gable end", widthRight, right),
      mkFacade("back", "Rear elevation", widthBack, back),
      mkFacade("left", "Left gable end", widthLeft, left),
    ],
  };
}

// Rebuild the Three.js scene from the house JSON. Returns walls by id
// (so the click handler can highlight the tapped facade).
function buildScene(scene, house) {
  const wallMeshes = {};
  const wallMat = new THREE.MeshLambertMaterial({ color: 0xd9dce2, side: THREE.DoubleSide });
  const frameMat = new THREE.MeshLambertMaterial({ color: 0x333842 });
  const paneMat = new THREE.MeshLambertMaterial({ color: 0x88a9c7, transparent: true, opacity: 0.75 });
  const roofMat = new THREE.MeshLambertMaterial({ color: 0x4a5058, side: THREE.DoubleSide });
  const { footprint, eaveHeight: H, roof } = house;
  const halfW = footprint.width / 2;
  const halfD = footprint.depth / 2;

  house.facades.forEach((f) => {
    const rise = f.gableEnd ? pitchRise(footprint.depth, roof.pitch) : 0;
    // Build shape (rectangle + optional gable triangle)
    const shape = new THREE.Shape();
    shape.moveTo(-f.width / 2, 0);
    shape.lineTo(f.width / 2, 0);
    shape.lineTo(f.width / 2, H);
    if (f.gableEnd) {
      shape.lineTo(0, H + rise);
    }
    shape.lineTo(-f.width / 2, H);
    shape.lineTo(-f.width / 2, 0);
    const geom = new THREE.ShapeGeometry(shape);
    const mesh = new THREE.Mesh(geom, wallMat.clone());
    // Position each wall around the footprint.
    switch (f.id) {
      case "front": mesh.position.set(0, 0, halfD); break;
      case "back":  mesh.position.set(0, 0, -halfD); mesh.rotation.y = Math.PI; break;
      case "right": mesh.position.set(halfW, 0, 0); mesh.rotation.y = Math.PI / 2; break;
      case "left":  mesh.position.set(-halfW, 0, 0); mesh.rotation.y = -Math.PI / 2; break;
      default: break;
    }
    mesh.userData.facadeId = f.id;
    wallMeshes[f.id] = mesh;
    scene.add(mesh);
    // Openings on this facade (in local wall coords x from left, y from bottom).
    f.openings.forEach((o) => {
      const cx = -f.width / 2 + o.x + o.w / 2;
      const cy = o.y + o.h / 2;
      const frame = new THREE.Mesh(new THREE.BoxGeometry(o.w + 0.4, o.h + 0.4, 0.15), frameMat);
      frame.position.set(cx, cy, 0.09);
      mesh.add(frame);
      const pane = new THREE.Mesh(new THREE.BoxGeometry(o.w, o.h, 0.2), paneMat);
      pane.position.set(cx, cy, 0.11);
      mesh.add(pane);
    });
  });

  // Roof — two sloped planes.
  const roofRise = pitchRise(footprint.depth, roof.pitch);
  const roofPlaneLen = Math.sqrt(Math.pow(footprint.depth / 2, 2) + Math.pow(roofRise, 2));
  const roofOverhang = roof.overhang;
  const roofPlaneGeom = new THREE.PlaneGeometry(footprint.width + roofOverhang * 2, roofPlaneLen + roofOverhang);
  ["north", "south"].forEach((side) => {
    const plane = new THREE.Mesh(roofPlaneGeom, roofMat);
    const angle = Math.atan2(roofRise, footprint.depth / 2);
    plane.rotation.x = side === "north" ? -(Math.PI / 2 - angle) : (Math.PI / 2 - angle);
    plane.position.set(
      0,
      H + roofRise / 2,
      side === "north" ? -footprint.depth / 4 : footprint.depth / 4
    );
    scene.add(plane);
  });

  // Ground shadow disc for visual grounding.
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(Math.max(footprint.width, footprint.depth) * 1.2, 40),
    new THREE.MeshLambertMaterial({ color: 0xeceff4 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.01;
  scene.add(ground);

  return wallMeshes;
}

export default function HouseModel3D({ preview }) {
  const mountRef = useRef(null);
  const sceneRef = useRef({});
  const [selectedFacade, setSelectedFacade] = useState("front");
  const [overrides, setOverrides] = useState({ pitch: null, eaveHeight: null, widths: {} });
  const house = useMemo(() => buildHouseJson(preview, overrides), [preview, overrides]);

  // Mount scene once
  useEffect(() => {
    if (!mountRef.current || !house) return;
    const el = mountRef.current;
    const w = el.clientWidth, h = el.clientHeight;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf7f8fb);
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 500);
    camera.position.set(house.footprint.width * 1.2, house.eaveHeight * 1.5, house.footprint.depth * 1.2);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(w, h);
    el.appendChild(renderer.domElement);
    scene.add(new THREE.AmbientLight(0xbcd0e8, 0.55));
    const sun = new THREE.DirectionalLight(0xfff2e0, 0.85);
    sun.position.set(60, 90, 45);
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x6fa0d8, 0.3);
    fill.position.set(-50, 40, -60);
    scene.add(fill);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, house.eaveHeight * 0.55, 0);
    controls.enableDamping = true;

    let raf;
    const animate = () => { controls.update(); renderer.render(scene, camera); raf = requestAnimationFrame(animate); };
    animate();

    const onResize = () => {
      const nw = el.clientWidth, nh = el.clientHeight;
      camera.aspect = nw / nh; camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(el);

    // Click → facade select
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const onClick = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects(Object.values(sceneRef.current.wallMeshes || {}));
      if (hits.length) {
        const id = hits[0].object.userData.facadeId;
        if (id) setSelectedFacade(id);
      }
    };
    renderer.domElement.addEventListener("click", onClick);

    sceneRef.current = { scene, camera, renderer, controls, wallMeshes: {} };
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      renderer.domElement.removeEventListener("click", onClick);
      controls.dispose();
      renderer.dispose();
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
    };
  }, []);

  // Rebuild geometry when house changes
  useEffect(() => {
    const s = sceneRef.current;
    if (!s.scene || !house) return;
    // Wipe non-light objects
    [...s.scene.children].forEach((child) => {
      if (child.isMesh) s.scene.remove(child);
    });
    s.wallMeshes = buildScene(s.scene, house);
  }, [house]);

  // Highlight selected facade
  useEffect(() => {
    const wm = sceneRef.current.wallMeshes || {};
    Object.entries(wm).forEach(([id, m]) => {
      m.material.emissive = new THREE.Color(id === selectedFacade ? 0x2b6bd5 : 0x000000);
      m.material.emissiveIntensity = id === selectedFacade ? 0.35 : 0;
    });
  }, [selectedFacade, house]);

  if (!house) {
    return <div className="p-6 text-sm text-[#71717A]">Run AI Measure first — the 3D model builds from the preview.</div>;
  }

  const facade = house.facades.find((f) => f.id === selectedFacade) || house.facades[0];
  const peb = (preview.measurements?._per_elevation_breakdown || []).find(
    (r) => (r.label || "").toLowerCase() === selectedFacade
  ) || {};
  const totalSqft = (peb.wall_body_sqft || 0) + (peb.gable_sqft || 0) + (peb.dormer_sqft || 0);
  // Whole-house material lines from the estimator (SSOT). Filter to
  // siding-adjacent categories so the "Materials" section shows the
  // squares / j-channel / starter / corner post the estimate will use.
  const sidingLines = (preview.lines || []).filter((l) => {
    const s = (l.section || "").toLowerCase();
    return ["siding", "trim", "corners", "j-channel", "starter"].some((k) => s.includes(k));
  }).slice(0, 10);
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 h-full" data-testid="ai-measure-3d-view">
      <div className="md:col-span-2 min-h-[520px] border border-[#E4E4E7] bg-[#F7F8FB] relative" ref={mountRef}>
        <div className="absolute top-2 left-2 text-[10px] uppercase tracking-wider font-bold text-[#7C3AED] bg-white/80 px-2 py-1 border border-[#7C3AED]" data-testid="ai-measure-3d-hint">
          Tap a wall to see its takeoff · drag to orbit · scroll to zoom
        </div>
      </div>
      <div className="min-h-[520px] flex flex-col gap-2">
        <div className="flex gap-1">
          {house.facades.map((f) => (
            <button
              key={f.id}
              onClick={() => setSelectedFacade(f.id)}
              className={`flex-1 px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider border ${selectedFacade === f.id ? "bg-[#7C3AED] text-white border-[#7C3AED]" : "bg-white text-[#52525B] border-[#E4E4E7]"}`}
              data-testid={`ai-measure-3d-tab-${f.id}`}
            >
              {f.id}
            </button>
          ))}
        </div>
        <div className="p-3 bg-white border border-[#E4E4E7] space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-[#A1A1AA] font-bold">Geometry — this wall</div>
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-[#71717A] w-24">Width (ft)</span>
            <input
              type="number" step="0.5" min="1"
              value={facade.width}
              onChange={(e) => setOverrides((o) => ({ ...o, widths: { ...o.widths, [facade.id]: parseFloat(e.target.value) || facade.width } }))}
              className="w-20 px-2 py-1 border border-[#E4E4E7] font-mono-num text-right"
              data-testid={`ai-measure-3d-width-${facade.id}`}
            />
            {facade.estimated && <Amber />}
          </div>
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-[#71717A] w-24">Eave height</span>
            <input
              type="number" step="0.5" min="6"
              value={house.eaveHeight}
              onChange={(e) => setOverrides((o) => ({ ...o, eaveHeight: parseFloat(e.target.value) || house.eaveHeight }))}
              className="w-20 px-2 py-1 border border-[#E4E4E7] font-mono-num text-right"
              data-testid="ai-measure-3d-eave"
            />
            {house.eaveHeightEstimated && <Amber />}
          </div>
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-[#71717A] w-24">Roof pitch</span>
            <select
              value={house.roof.pitch}
              onChange={(e) => setOverrides((o) => ({ ...o, pitch: parseInt(e.target.value, 10) }))}
              className="w-20 px-2 py-1 border border-[#E4E4E7] text-right"
              data-testid="ai-measure-3d-pitch"
            >
              {ROOF_PITCHES.map((p) => <option key={p} value={p}>{p}/12</option>)}
            </select>
            {house.roof.pitchEstimated && <Amber />}
          </div>
          {(facade.estimated || house.eaveHeightEstimated || house.roof.pitchEstimated) && (
            <div className="text-[9px] italic text-[#92400E] leading-tight pt-1 border-t border-[#F59E0B]">
              Edits update the 3D drawing only. To make the estimator match, hit <strong>Re-run</strong> in the footer.
            </div>
          )}
        </div>
        <div className="p-3 bg-white border border-[#E4E4E7] space-y-1">
          <div className="text-[10px] uppercase tracking-wider text-[#A1A1AA] font-bold flex items-center justify-between">
            <span>This wall — AI takeoff</span>
            {facade.confidence != null && (
              <span className="text-[9px] font-bold" style={{ color: facade.confidence >= 80 ? "#16A34A" : AMBER }}>
                {facade.confidence}% conf
              </span>
            )}
          </div>
          <Row k="Wall body" v={`${(peb.wall_body_sqft || 0).toFixed(0)} sf`} />
          {(peb.gable_sqft || 0) > 0 && <Row k="Gable area" v={`${peb.gable_sqft.toFixed(0)} sf`} />}
          {(peb.dormer_sqft || 0) > 0 && <Row k="Dormer face" v={`${peb.dormer_sqft.toFixed(0)} sf`} />}
          {(peb.stone_sqft || 0) > 0 && <Row k="Stone / masked" v={`${peb.stone_sqft.toFixed(0)} sf`} />}
          <Row k="Total (this wall)" v={`${totalSqft.toFixed(0)} sf`} bold />
          <Row k="Openings" v={facade.openings.length} />
        </div>
        <div className="p-3 bg-white border border-[#E4E4E7] space-y-1 flex-1 overflow-y-auto">
          <div className="text-[10px] uppercase tracking-wider text-[#A1A1AA] font-bold">
            Whole-house materials <span className="text-[9px] italic text-[#71717A] font-normal">· from estimator</span>
          </div>
          {sidingLines.length === 0 ? (
            <div className="text-[11px] italic text-[#71717A]">No siding lines in this preview.</div>
          ) : (
            sidingLines.map((ln, i) => (
              <Row key={i} k={ln.name} v={`${ln.qty} ${ln.unit || ""}`} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

const Row = ({ k, v, bold }) => (
  <div className={`flex justify-between items-baseline text-[11px] ${bold ? "font-bold text-[#09090B]" : "text-[#52525B]"}`}>
    <span className="text-[#71717A]">{k}</span>
    <span className="font-mono-num tabular-nums">{v}</span>
  </div>
);

const Amber = () => (
  <span className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#FEF3C7] text-[#92400E] border border-[#F59E0B]" title="Approximated / low-confidence — verify before you quote" data-testid="ai-measure-3d-amber">
    <AlertTriangle className="w-2.5 h-2.5" style={{ color: AMBER }} /> estimated
  </span>
);
