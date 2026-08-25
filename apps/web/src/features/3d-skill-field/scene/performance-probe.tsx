"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

export function PerformanceProbe({ qualityProfile, particleCount, visibleLabelCount, aaMode, bloomMode, postProcessingPassCount, onSustainedLowFps }: {
  qualityProfile: string;
  particleCount: number;
  visibleLabelCount: number;
  aaMode: string;
  bloomMode: string;
  postProcessingPassCount: number;
  onSustainedLowFps: () => void;
}) {
  const renderedFrames = useRef(0);
  const frameTimes = useRef<number[]>([]);
  const lowFpsStartedAt = useRef<number | null>(null);
  const downgradeTriggered = useRef(false);

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
    host.dataset.qualityProfile = qualityProfile;
    host.dataset.particleCount = String(particleCount);
    host.dataset.visibleLabelCount = String(visibleLabelCount);
    host.dataset.aaMode = aaMode;
    host.dataset.bloomMode = bloomMode;
    host.dataset.postProcessingPassCount = String(postProcessingPassCount);
    const sampleSpan = frameTimes.current.length > 1 ? now - frameTimes.current[0] : 0;
    if (!downgradeTriggered.current && sampleSpan > 800 && frameTimes.current.length < 45) {
      lowFpsStartedAt.current ??= now;
      if (now - lowFpsStartedAt.current > 1000) {
        downgradeTriggered.current = true;
        onSustainedLowFps();
      }
    } else if (frameTimes.current.length >= 45) {
      lowFpsStartedAt.current = null;
    }
  });

  return null;
}
