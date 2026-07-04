// Iter 78u — In-app 3D preview of a single elevation. Uses the same
// `buildElevationScene()` factory the headless PNG renderer uses, so
// what the contractor sees on screen matches what gets embedded in
// the customer quote PDF.
//
// Renders once on mount + whenever the elevation prop changes. No
// orbit controls — orthographic straight-on view by design (HOVER
// parity). If we later want a small rotate toggle it can plug in here.
import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { buildElevationScene } from "@/lib/elevation3D";

export default function Elevation3DPreview({ elevation, pxHeight = 220 }) {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    const built = buildElevationScene(elevation);
    if (!built) return undefined;
    const { scene, bounds } = built;
    const rect = container.getBoundingClientRect();
    const pxWidth = Math.max(200, Math.floor(rect.width));
    const worldW = bounds.maxX - bounds.minX;
    const worldH = bounds.maxY - bounds.minY;
    const targetAspect = pxWidth / pxHeight;
    const worldAspect = worldW / worldH;
    let fW;
    let fH;
    if (worldAspect > targetAspect) {
      fW = worldW;
      fH = worldW / targetAspect;
    } else {
      fH = worldH;
      fW = worldH * targetAspect;
    }
    const cx = (bounds.minX + bounds.maxX) / 2;
    const cy = (bounds.minY + bounds.maxY) / 2;
    const camera = new THREE.OrthographicCamera(
      cx - fW / 2, cx + fW / 2,
      cy + fH / 2, cy - fH / 2,
      -100, 100
    );
    camera.position.set(cx, cy, 50);
    camera.lookAt(cx, cy, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(pxWidth, pxHeight, false);
    rendererRef.current = renderer;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);
    renderer.render(scene, camera);
    return () => {
      renderer.dispose();
      scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose?.();
        if (obj.material) {
          if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose?.());
          else obj.material.dispose?.();
        }
      });
      if (renderer.domElement && renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    };
  }, [elevation, pxHeight]);

  return (
    <div
      className="border border-[var(--border)] bg-[var(--surface)]"
      data-testid={`elevation-3d-${(elevation?.label || "").toLowerCase()}`}
    >
      <div className="flex items-center justify-between px-3 py-1.5 bg-[var(--surface-muted)] border-b border-[var(--border)]">
        <div className="text-[11px] uppercase tracking-wider font-bold text-[var(--ink)]">
          {elevation?.label || "Elevation"}
          <span className="ml-2 font-mono-num text-[var(--muted)]">
            {Number(elevation?.facade_width_ft || 0).toFixed(0)}&apos;W &times; {Number(elevation?.facade_height_ft || 0).toFixed(0)}&apos;H
          </span>
        </div>
        <span className="text-[9px] uppercase tracking-wider font-bold text-[var(--ai)] bg-[#FAF5FF] border border-[#E9D5FF] px-1.5 py-0.5">3D</span>
      </div>
      <div ref={containerRef} style={{ width: "100%", height: pxHeight }} />
    </div>
  );
}
