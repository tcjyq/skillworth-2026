"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

export function PerformanceProbe() {
  const renderedFrames = useRef(0);
  const frameTimes = useRef<number[]>([]);

  useFrame(({ gl }) => {
    const now = performance.now();
    renderedFrames.current += 1;
    frameTimes.current = [...frameTimes.current.filter((time) => now - time <= 1000), now];
    const host = gl.domElement.closest<HTMLElement>('[data-testid="skill-field-canvas"]');
    if (!host) return;
    host.dataset.renderedFrames = String(renderedFrames.current);
    host.dataset.activeFps = String(frameTimes.current.length);
    host.dataset.drawCalls = String(gl.info.render.calls);
    host.dataset.geometries = String(gl.info.memory.geometries);
    host.dataset.textures = String(gl.info.memory.textures);
    host.dataset.rendererDpr = gl.getPixelRatio().toFixed(2);
    host.dataset.lastRenderedAt = now.toFixed(1);
  });

  return null;
}
