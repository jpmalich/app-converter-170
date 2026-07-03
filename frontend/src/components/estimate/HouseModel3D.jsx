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
import { AlertTriangle, Check } from "lucide-react";

const ROOF_PITCHES = [4, 6, 8, 10, 12];
const ROOF_TYPES = [
  { id: "gable", label: "Gable" },
  { id: "hip", label: "Hip" },
  { id: "gable-shed-dormer", label: "Gable + shed dormer" },
];
const DEFAULT_PITCH = 6;
const DEFAULT_EAVE_HEIGHT = 10;
const AMBER = "#F59E0B";
const ROOF_TYPE_CONFIDENCE_THRESHOLD = 0.8;

function pitchRise(widthFt, pitchOver12) {
  // rise across HALF the roof span, e.g. 6/12 on a 40 ft span = 20 × 6/12 = 10 ft.
  return (widthFt / 2) * (pitchOver12 / 12);
}

// Iter 79j.23 — Derive roof pitch from any gable-end wall Claude found.
// Formula: rise = (width / 2) × (pitch / 12)  ⇒  pitch = rise × 24 / width.
// When the house has multiple gables we average the raw values before
// snapping to the nearest supported pitch (4/6/8/10/12). Returns null
// when no gable data is available — caller falls back to DEFAULT_PITCH.
function deriveRoofPitchFromWalls(walls) {
  const gables = (walls || []).filter(
    (w) => Number(w?.gable_triangle_height_ft || 0) > 0 && Number(w?.width_ft || 0) > 0,
  );
  if (!gables.length) return null;
  const raws = gables.map((w) => (Number(w.gable_triangle_height_ft) * 24) / Number(w.width_ft));
  const avg = raws.reduce((a, b) => a + b, 0) / raws.length;
  let best = ROOF_PITCHES[0];
  let bestDelta = Math.abs(avg - best);
  for (const p of ROOF_PITCHES) {
    const d = Math.abs(avg - p);
    if (d < bestDelta) {
      best = p;
      bestDelta = d;
    }
  }
  return { pitch: best, raw: Math.round(avg * 10) / 10, sampleCount: gables.length };
}

// Build a house-JSON shape from the AI preview + user overrides.
function buildHouseJson(preview, overrides) {
  if (!preview) return null;
  const walls = preview.raw_ai?.walls || [];
  const openings = preview.raw_ai?.openings || [];
  const avgAiEave = preview.measurements?._ai_avg_wall_height_ft;
  // Iter 79j.23 — try to derive pitch from Claude's gable heights before
  // falling back to the 6/12 default.
  const aiPitch = deriveRoofPitchFromWalls(walls);
  const pitch = overrides.pitch ?? aiPitch?.pitch ?? DEFAULT_PITCH;
  const pitchSource = overrides.pitch != null
    ? "user"
    : aiPitch
    ? "ai"
    : "default";
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

  // Iter 79j.24 — Per-facade eave heights. Claude reports `height_ft` on
  // every walls[] entry; we prefer that over the whole-house average.
  // Sources cascade: user override > wall-specific AI > whole-house AI
  // average > 10ft default. Sources drive the badge color in the UI.
  const eaveOverrides = overrides.eaveHeights || {};
  const resolveEave = (id, wallData) => {
    if (eaveOverrides[id] != null) return { h: Number(eaveOverrides[id]), source: "user" };
    const wallH = Number(wallData?.height_ft || 0);
    if (wallH > 0) return { h: wallH, source: "ai" };
    const avgH = Number(avgAiEave || 0);
    if (avgH > 0) return { h: avgH, source: "ai-avg" };
    return { h: DEFAULT_EAVE_HEIGHT, source: "default" };
  };
  const eaves = {
    front: resolveEave("front", front),
    back: resolveEave("back", back),
    left: resolveEave("left", left),
    right: resolveEave("right", right),
  };
  const avgEave = (eaves.front.h + eaves.back.h + eaves.left.h + eaves.right.h) / 4;

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

  // Iter 79j.26 — Roof type cascade: user > AI (≥0.8 confidence) >
  // default 'gable'. Below-threshold AI values still surface in the
  // tooltip so contractors can double-check.
  const aiRoofType = preview.measurements?._ai_roof_type || null;
  const aiRoofTypeConfidence = Number(preview.measurements?._ai_roof_type_confidence ?? 0);
  const aiRoofTypeReasoning = preview.measurements?._ai_roof_type_reasoning || "";
  const aiRoofTypeConfident = aiRoofType && aiRoofTypeConfidence >= ROOF_TYPE_CONFIDENCE_THRESHOLD;
  const roofType = overrides.roofType
    ?? (aiRoofTypeConfident ? aiRoofType : "gable");
  const roofTypeSource = overrides.roofType
    ? "user"
    : aiRoofTypeConfident
    ? "ai"
    : aiRoofType
    ? "ai-low-conf"
    : "default";

  // Dormer geometry (only used when roofType === 'gable-shed-dormer').
  // The AI may return { face, width_ft, knee_wall_height_ft, offset_x_ft };
  // fall back to a sane default centered on the front slope.
  const aiDormer = preview.measurements?._ai_dormer || null;
  const dormerOverride = overrides.dormer || {};
  const dormerFace = dormerOverride.face ?? aiDormer?.face ?? "front";
  const dormerWidth = Number(dormerOverride.width ?? aiDormer?.width_ft ?? Math.min(footprintW * 0.6, 16));
  const dormerKnee = Number(dormerOverride.kneeWallHeight ?? aiDormer?.knee_wall_height_ft ?? 4);
  const dormerOffsetX = Number(dormerOverride.offsetX ?? aiDormer?.offset_x_ft ?? 0);

  const mkFacade = (id, label, widthOverride, wallData, eave) => ({
    id,
    label,
    width: widthOverride,
    eaveHeight: eave.h,
    eaveHeightSource: eave.source,
    gableEnd: id === "left" || id === "right",
    confidence: wallData?.confidence ?? null,
    estimated: !wallData,
    openings: autoSpace(openingsByWall[id] || [], widthOverride),
  });
  return {
    footprint: { width: footprintW, depth: footprintD, estimated: !front || !left },
    avgEaveHeight: avgEave,
    roof: {
      type: roofType,
      typeSource: roofTypeSource,        // "user" | "ai" | "ai-low-conf" | "default"
      typeAiRaw: aiRoofType,
      typeAiConfidence: aiRoofTypeConfidence,
      typeAiReasoning: aiRoofTypeReasoning,
      pitch,
      ridgeAxis: "x",
      overhang: 1.25,
      pitchSource,
      pitchAiRaw: aiPitch?.raw ?? null,
      pitchAiSamples: aiPitch?.sampleCount ?? 0,
      pitchEstimated: pitchSource === "default",
      dormer: roofType === "gable-shed-dormer"
        ? { face: dormerFace, width: dormerWidth, kneeWallHeight: dormerKnee, offsetX: dormerOffsetX }
        : null,
    },
    facades: [
      mkFacade("front", "Front elevation", widthFront, front, eaves.front),
      mkFacade("right", "Right gable end", widthRight, right, eaves.right),
      mkFacade("back", "Rear elevation", widthBack, back, eaves.back),
      mkFacade("left", "Left gable end", widthLeft, left, eaves.left),
    ],
  };
}

// Iter 79j.26 — Gable roof planes (2 sloped rectangles).
function buildGableRoofPlanes(scene, house, roofMat, roofRise, avgGableEave) {
  const { footprint, roof } = house;
  const roofPlaneLen = Math.sqrt(Math.pow(footprint.depth / 2, 2) + Math.pow(roofRise, 2));
  const roofPlaneGeom = new THREE.PlaneGeometry(footprint.width + roof.overhang * 2, roofPlaneLen + roof.overhang);
  ["north", "south"].forEach((side) => {
    const plane = new THREE.Mesh(roofPlaneGeom, roofMat);
    const angle = Math.atan2(roofRise, footprint.depth / 2);
    const dir = side === "north" ? 1 : -1;
    plane.rotation.x = dir * (Math.PI / 2 - angle);
    plane.position.set(
      0,
      avgGableEave + roofRise / 2,
      side === "north" ? -footprint.depth / 4 : footprint.depth / 4,
    );
    scene.add(plane);
  });
}

// Iter 79j.26 — Hip roof: 4 planes (2 trapezoids on the long sides,
// 2 triangles on the short ends) meeting at a shortened ridge that
// runs along whichever axis (X or Z) is longer. Equal pitch all
// around → ridge length = |longAxis − shortAxis|.
function buildHipRoof(scene, house, roofMat, ridgeY, avgGableEave) {
  const { footprint } = house;
  const W = footprint.width;    // X axis
  const D = footprint.depth;    // Z axis
  const halfW = W / 2;
  const halfD = D / 2;
  const ridgeAlongX = W >= D;   // ridge runs along the longer axis
  const shortHalf = Math.min(halfW, halfD);
  const ridgeHalfLen = Math.abs(halfW - halfD);

  // Ridge endpoints in world space
  const ridgeEnds = ridgeAlongX
    ? [[-ridgeHalfLen, ridgeY, 0], [+ridgeHalfLen, ridgeY, 0]]
    : [[0, ridgeY, -ridgeHalfLen], [0, ridgeY, +ridgeHalfLen]];

  // Eave corners (all at avgGableEave for hip — hip roofs sit on
  // rectangular walls at uniform eave)
  const corners = {
    fl: [-halfW, avgGableEave, +halfD],
    fr: [+halfW, avgGableEave, +halfD],
    bl: [-halfW, avgGableEave, -halfD],
    br: [+halfW, avgGableEave, -halfD],
  };

  // Helper to add a polygon face from a vertex list. Assumes convex.
  const addFace = (verts) => {
    const positions = [];
    // Fan triangulation from vert[0]
    for (let i = 1; i < verts.length - 1; i += 1) {
      positions.push(...verts[0], ...verts[i], ...verts[i + 1]);
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geom.computeVertexNormals();
    scene.add(new THREE.Mesh(geom, roofMat));
  };

  // 4 faces: 2 trapezoids + 2 triangles.
  if (ridgeAlongX) {
    // Front trapezoid: FL → FR → ridgeEnd_R (top-right) → ridgeEnd_L (top-left)
    addFace([corners.fl, corners.fr, ridgeEnds[1], ridgeEnds[0]]);
    // Back trapezoid: BR → BL → ridgeEnd_L → ridgeEnd_R
    addFace([corners.br, corners.bl, ridgeEnds[0], ridgeEnds[1]]);
    // Right triangle: FR → BR → ridgeEnd_R
    addFace([corners.fr, corners.br, ridgeEnds[1]]);
    // Left triangle: BL → FL → ridgeEnd_L
    addFace([corners.bl, corners.fl, ridgeEnds[0]]);
  } else {
    // Ridge runs along Z. Left+right are trapezoids; front+back are triangles.
    addFace([corners.fr, corners.br, ridgeEnds[0], ridgeEnds[1]]);   // Right trapezoid
    addFace([corners.bl, corners.fl, ridgeEnds[1], ridgeEnds[0]]);   // Left trapezoid
    addFace([corners.fl, corners.fr, ridgeEnds[1]]);                 // Front triangle
    addFace([corners.br, corners.bl, ridgeEnds[0]]);                 // Back triangle
  }
  // shortHalf reserved for future overhang math
  void shortHalf;
}

// Iter 79j.26 — Shed dormer on one slope of a gable roof. Adds:
//   • vertical face wall (rectangle) with any openings pinned to it
//   • two triangular cheek walls filling the gap between the face
//     top and the main roof surface
//   • low-slope shed roof from the face top back to the main ridge
function buildShedDormer(scene, house, roofMat, wallMat, frameMat, paneMat, roofRise, avgGableEave) {
  const { footprint, roof } = house;
  const d = roof.dormer;
  if (!d) return;
  const halfD = footprint.depth / 2;
  // Position dormer face at 25% of the roof depth back from the eave
  // (halfway between eave and ridge on the chosen slope).
  const zFrac = 0.5;   // fraction of halfD from ridge to eave
  const faceSign = d.face === "rear" ? -1 : 1;
  const zFace = faceSign * halfD * zFrac;
  // Main roof Y at this Z (linear from ridge at Z=0 to eave at Z=±halfD)
  const mainRoofYAtFace = avgGableEave + roofRise * (1 - Math.abs(zFace) / halfD);
  const faceBottomY = mainRoofYAtFace;
  const faceTopY = faceBottomY + Number(d.kneeWallHeight);
  const halfWD = Number(d.width) / 2;
  const cx = Number(d.offsetX) || 0;

  // 1) Face wall (vertical rectangle in XY at Z=zFace)
  const faceShape = new THREE.Shape();
  faceShape.moveTo(cx - halfWD, faceBottomY);
  faceShape.lineTo(cx + halfWD, faceBottomY);
  faceShape.lineTo(cx + halfWD, faceTopY);
  faceShape.lineTo(cx - halfWD, faceTopY);
  faceShape.lineTo(cx - halfWD, faceBottomY);
  const faceGeom = new THREE.ShapeGeometry(faceShape);
  const faceMesh = new THREE.Mesh(faceGeom, wallMat.clone());
  // Face wall normal points outward on the dormer's own axis (+Z for front, -Z for rear)
  faceMesh.position.set(0, 0, zFace + faceSign * 0.05);
  if (d.face === "rear") faceMesh.rotation.y = Math.PI;
  scene.add(faceMesh);

  // Add a stock 3'×5' window at the center of the dormer face
  const win = { w: 3, h: 5, cx, cy: (faceBottomY + faceTopY) / 2 };
  const frame = new THREE.Mesh(new THREE.BoxGeometry(win.w + 0.4, win.h + 0.4, 0.15), frameMat);
  frame.position.set(cx, win.cy, zFace + faceSign * 0.14);
  scene.add(frame);
  const pane = new THREE.Mesh(new THREE.BoxGeometry(win.w, win.h, 0.2), paneMat);
  pane.position.set(cx, win.cy, zFace + faceSign * 0.16);
  scene.add(pane);

  // 2) Cheek walls — two triangles filling the wedge on each side.
  // Each cheek is a triangle in the XZ (well, YZ at fixed X) plane
  // with vertices: (X=side_of_dormer, faceTopY, zFace),
  //                (X=side, faceBottomY, zFace),
  //                (X=side, ridgeY, 0)  ← where the shed meets ridge
  const ridgeY = avgGableEave + roofRise;
  const addTri = (v1, v2, v3) => {
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.Float32BufferAttribute([...v1, ...v2, ...v3], 3));
    geom.computeVertexNormals();
    scene.add(new THREE.Mesh(geom, wallMat.clone()));
  };
  const cheekXs = [cx - halfWD, cx + halfWD];
  cheekXs.forEach((x) => {
    // For rear-facing dormer, the shed slopes DOWN toward the ridge; z of
    // "back" edge is 0 (ridge), z of face edge is zFace.
    addTri(
      [x, faceTopY, zFace],
      [x, faceBottomY, zFace],
      [x, ridgeY, 0],
    );
  });

  // 3) Shed roof plane — quad from (X=-halfWD..+halfWD, Y=faceTopY, Z=zFace)
  // to (X=-halfWD..+halfWD, Y=ridgeY, Z=0)
  const shedGeomPositions = [
    cx - halfWD, faceTopY, zFace,
    cx + halfWD, faceTopY, zFace,
    cx + halfWD, ridgeY,   0,
    cx - halfWD, faceTopY, zFace,
    cx + halfWD, ridgeY,   0,
    cx - halfWD, ridgeY,   0,
  ];
  const shedGeom = new THREE.BufferGeometry();
  shedGeom.setAttribute("position", new THREE.Float32BufferAttribute(shedGeomPositions, 3));
  shedGeom.computeVertexNormals();
  scene.add(new THREE.Mesh(shedGeom, roofMat));
}

// Rebuild the Three.js scene from the house JSON. Returns walls by id
// (so the click handler can highlight the tapped facade).
function buildScene(scene, house) {
  const wallMeshes = {};
  const wallMat = new THREE.MeshLambertMaterial({ color: 0xd9dce2, side: THREE.DoubleSide });
  const frameMat = new THREE.MeshLambertMaterial({ color: 0x333842 });
  const paneMat = new THREE.MeshLambertMaterial({ color: 0x88a9c7, transparent: true, opacity: 0.75 });
  const roofMat = new THREE.MeshLambertMaterial({ color: 0x4a5058, side: THREE.DoubleSide });
  const { footprint, roof } = house;
  const halfW = footprint.width / 2;
  const halfD = footprint.depth / 2;

  house.facades.forEach((f) => {
    // Iter 79j.24 — each wall uses its own eave height so split-level
    // homes render with the correct step in the eave line.
    // Iter 79j.26 — hip roofs have NO gable triangles on any wall; the
    // gable-shed-dormer type keeps the gable-end triangles as normal
    // (dormer geometry is added separately as its own mesh cluster).
    const H = f.eaveHeight;
    const hasGablePeak = f.gableEnd && (roof.type === "gable" || roof.type === "gable-shed-dormer");
    const rise = hasGablePeak ? pitchRise(footprint.depth, roof.pitch) : 0;
    const shape = new THREE.Shape();
    shape.moveTo(-f.width / 2, 0);
    shape.lineTo(f.width / 2, 0);
    shape.lineTo(f.width / 2, H);
    if (hasGablePeak) {
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

  // Iter 79j.26 — Roof geometry routes on roof.type. All 3 types share
  // the same ridge-height math (avgGableEave + rise) so the sanity
  // check below applies uniformly.
  const gableEndFacades = house.facades.filter((f) => f.gableEnd);
  const avgGableEave = gableEndFacades.length
    ? gableEndFacades.reduce((s, f) => s + f.eaveHeight, 0) / gableEndFacades.length
    : house.avgEaveHeight;
  const roofRise = pitchRise(footprint.depth, roof.pitch);
  const ridgeY = avgGableEave + roofRise;

  if (roof.type === "hip") {
    buildHipRoof(scene, house, roofMat, ridgeY, avgGableEave);
  } else {
    buildGableRoofPlanes(scene, house, roofMat, roofRise, avgGableEave);
    if (roof.type === "gable-shed-dormer" && roof.dormer) {
      buildShedDormer(scene, house, roofMat, wallMat, frameMat, paneMat, roofRise, avgGableEave);
    }
  }

  // Iter 79j.25 + .26 — Geometry sanity checks.
  const maxEave = Math.max(...house.facades.map((f) => f.eaveHeight));
  if (ridgeY <= maxEave) {
    console.error(
      "[HouseModel3D] sanity FAILED — ridge not above eave",
      { roofType: roof.type, ridgeY, maxEave, avgGableEave, roofRise, pitch: roof.pitch },
    );
  }
  if (roof.type === "hip") {
    // For hip: ridge length ≥ 0 (i.e. |width - depth| ≥ 0) and all
    // four planes slope downward from the ridge. `PlaneGeometry` +
    // BufferGeometry constructions we build ensure downward slope by
    // construction, so this reduces to a non-negative ridge length.
    const ridgeLen = Math.abs(footprint.width - footprint.depth);
    if (ridgeLen < 0) {
      console.error("[HouseModel3D] hip sanity FAILED — negative ridge length", { ridgeLen });
    }
  }
  if (roof.type === "gable-shed-dormer" && roof.dormer) {
    // Dormer face top must sit below the main ridge.
    // Face bottom sits on the main roof surface at Z=zd.
    const zd = footprint.depth * 0.25;
    const mainRoofY = avgGableEave + roofRise * (1 - zd / (footprint.depth / 2));
    const dormerFaceTop = mainRoofY + Number(roof.dormer.kneeWallHeight || 0);
    if (dormerFaceTop >= ridgeY) {
      console.error(
        "[HouseModel3D] dormer sanity FAILED — dormer face top ≥ main ridge",
        { dormerFaceTop, ridgeY, kneeWallHeight: roof.dormer.kneeWallHeight },
      );
    }
  }

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
  const [overrides, setOverrides] = useState({ pitch: null, eaveHeights: {}, widths: {} });
  const house = useMemo(() => buildHouseJson(preview, overrides), [preview, overrides]);

  // Mount scene once
  useEffect(() => {
    if (!mountRef.current || !house) return;
    const el = mountRef.current;
    const w = el.clientWidth, h = el.clientHeight;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf7f8fb);
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 500);
    camera.position.set(house.footprint.width * 1.2, house.avgEaveHeight * 1.5, house.footprint.depth * 1.2);
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
    controls.target.set(0, house.avgEaveHeight * 0.55, 0);
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
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="ai-measure-3d-view">
      <div className="md:col-span-2 h-[560px] md:h-[640px] border border-[#E4E4E7] bg-[#F7F8FB] relative" ref={mountRef}>
        <div className="absolute top-2 left-2 text-[10px] uppercase tracking-wider font-bold text-[#7C3AED] bg-white/80 px-2 py-1 border border-[#7C3AED]" data-testid="ai-measure-3d-hint">
          Tap a wall to see its takeoff · drag to orbit · scroll to zoom
        </div>
      </div>
      <div className="h-[560px] md:h-[640px] flex flex-col gap-2 min-h-0">
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
              value={facade.eaveHeight}
              onChange={(e) => setOverrides((o) => ({ ...o, eaveHeights: { ...o.eaveHeights, [facade.id]: parseFloat(e.target.value) || facade.eaveHeight } }))}
              className="w-20 px-2 py-1 border border-[#E4E4E7] font-mono-num text-right"
              data-testid={`ai-measure-3d-eave-${facade.id}`}
            />
            {facade.eaveHeightSource === "default" && <Amber />}
            {facade.eaveHeightSource === "ai" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#DCFCE7] text-[#166534] border border-[#16A34A]"
                title="Read straight from Claude's per-wall height_ft for this elevation"
                data-testid={`ai-measure-3d-eave-derived-${facade.id}`}
              >
                <Check className="w-2.5 h-2.5" /> AI per-wall
              </span>
            )}
            {facade.eaveHeightSource === "ai-avg" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#FEF3C7] text-[#92400E] border border-[#F59E0B]"
                title="Claude didn't return a per-wall height for this elevation — using the whole-house average. Verify in the field."
                data-testid={`ai-measure-3d-eave-avg-${facade.id}`}
              >
                <AlertTriangle className="w-2.5 h-2.5" style={{ color: AMBER }} /> AI avg
              </span>
            )}
            {facade.eaveHeightSource === "user" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#EDE9FE] text-[#5B21B6] border border-[#7C3AED]"
                title="You overrode this wall's eave — hit Re-run to feed this back to the estimator"
                data-testid={`ai-measure-3d-eave-user-${facade.id}`}
              >
                edited
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-[#71717A] w-24">Roof pitch</span>
            <select
              value={house.roof.pitch}
              onChange={(e) => setOverrides((o) => ({ ...o, pitch: parseInt(e.target.value, 10) }))}
              className="w-20 px-2 py-1 border border-[#E4E4E7] text-right"
              data-testid="ai-measure-3d-pitch"
            >
              {ROOF_PITCHES.map((p) => (
                <option key={p} value={p}>{`${p}/12`}</option>
              ))}
            </select>
            {house.roof.pitchSource === "default" && <Amber />}
            {house.roof.pitchSource === "ai" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#DCFCE7] text-[#166534] border border-[#16A34A]"
                title={`Derived from Claude's gable height (raw ${house.roof.pitchAiRaw}/12 across ${house.roof.pitchAiSamples} gable-end wall${house.roof.pitchAiSamples > 1 ? "s" : ""}, snapped to ${house.roof.pitch}/12)`}
                data-testid="ai-measure-3d-pitch-derived"
              >
                <Check className="w-2.5 h-2.5" /> AI-derived
              </span>
            )}
            {house.roof.pitchSource === "user" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#EDE9FE] text-[#5B21B6] border border-[#7C3AED]"
                title="You overrode the pitch — hit Re-run to feed this back to the estimator"
                data-testid="ai-measure-3d-pitch-user"
              >
                edited
              </span>
            )}
          </div>
          {/* Iter 79j.26 — Roof type dropdown */}
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-[#71717A] w-24">Roof type</span>
            <select
              value={house.roof.type}
              onChange={(e) => setOverrides((o) => ({ ...o, roofType: e.target.value }))}
              className="px-2 py-1 border border-[#E4E4E7] text-left flex-1 min-w-0"
              data-testid="ai-measure-3d-roof-type"
            >
              {ROOF_TYPES.map((rt) => (
                <option key={rt.id} value={rt.id}>{rt.label}</option>
              ))}
            </select>
            {house.roof.typeSource === "default" && <Amber />}
            {house.roof.typeSource === "ai-low-conf" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#FEF3C7] text-[#92400E] border border-[#F59E0B]"
                title={`Claude guessed "${house.roof.typeAiRaw}" with only ${Math.round((house.roof.typeAiConfidence || 0) * 100)}% confidence — defaulting to gable. Verify from the photos.`}
                data-testid="ai-measure-3d-roof-type-lowconf"
              >
                <AlertTriangle className="w-2.5 h-2.5" style={{ color: AMBER }} /> estimated
              </span>
            )}
            {house.roof.typeSource === "ai" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#DCFCE7] text-[#166534] border border-[#16A34A]"
                title={`Classified by Claude with ${Math.round((house.roof.typeAiConfidence || 0) * 100)}% confidence. ${house.roof.typeAiReasoning || ""}`}
                data-testid="ai-measure-3d-roof-type-ai"
              >
                <Check className="w-2.5 h-2.5" /> AI-classified
              </span>
            )}
            {house.roof.typeSource === "user" && (
              <span
                className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 bg-[#EDE9FE] text-[#5B21B6] border border-[#7C3AED]"
                title="You changed the roof type — hit Re-run to feed this back to the estimator"
                data-testid="ai-measure-3d-roof-type-user"
              >
                edited
              </span>
            )}
          </div>
          {(facade.estimated || facade.eaveHeightSource === "default" || facade.eaveHeightSource === "ai-avg" || house.roof.pitchSource === "default" || house.roof.typeSource === "default" || house.roof.typeSource === "ai-low-conf") && (
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
        <div className="p-3 bg-white border border-[#E4E4E7] space-y-1 flex-1 min-h-0 overflow-y-auto">
          <div className="text-[10px] uppercase tracking-wider text-[#A1A1AA] font-bold sticky top-0 bg-white pb-1" data-testid="ai-measure-3d-materials-heading">
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
