// Accept-page interactive 3D (ruled 2026-07-15): homeowner surface.
// The house renders in its RATIFIED state — appendages forced solid,
// no per-feature verification chips, no internal state labels, no
// edit controls. Payload arrives pre-sanitized from /public/accept.
import React, { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";
import { buildHouseJson, buildScene } from "@/components/estimate/HouseModel3D";

export default function AcceptHouse3D({ house3d }) {
  const mountRef = useRef(null);
  const house = useMemo(() => {
    try {
      const apDims = {};
      Object.entries(house3d?.dims || {}).forEach(([wall, fields]) => {
        apDims[`appendage:${wall}`] = Object.fromEntries(
          Object.entries(fields).map(([f, v]) => [f, { value: v, status: "user_measured" }])
        );
      });
      const h = buildHouseJson(
        { measurements: house3d.measurements, raw_ai: house3d.raw_ai, lines: [] },
        { pitch: null, eaveHeights: {}, widths: {} },
        null,
        apDims,
      );
      if (h) h.appendages = (h.appendages || []).map((a) => ({ ...a, confirmed: true }));
      return h;
    } catch {
      return null;
    }
  }, [house3d]);

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
    try { buildScene(scene, house); } catch { /* homeowner surface never breaks acceptance */ }
    let raf;
    const animate = () => { controls.update(); renderer.render(scene, camera); raf = requestAnimationFrame(animate); };
    animate();
    const ro = new ResizeObserver(() => {
      const nw = el.clientWidth, nh = el.clientHeight;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    });
    ro.observe(el);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
    };
  }, [house]);

  if (!house) return null;
  return (
    <div
      ref={mountRef}
      style={{ width: "100%", height: 320, touchAction: "none", cursor: "grab" }}
      data-testid="accept-3d-canvas"
    />
  );
}
