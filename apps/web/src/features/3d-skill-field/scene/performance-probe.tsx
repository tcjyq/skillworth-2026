"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export function PerformanceProbe({ qualityProfile, environmentalParticleCount, relationParticleCount, visibleLabelCount, aaMode, bloomMode, postProcessingPassCount, onSustainedLowFps }: {
  qualityProfile: string;
  environmentalParticleCount: number;
  relationParticleCount: number;
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
  const frameDurations = useRef<number[]>([]);

  useFrame(({ gl, camera, controls }, delta) => {
    const now = performance.now();
    renderedFrames.current += 1;
    frameTimes.current = [...frameTimes.current.filter((time) => now - time <= 1000), now];
    if (delta > 0 && delta < 0.1) frameDurations.current = [...frameDurations.current.slice(-29), delta];
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
    host.dataset.cameraPosition = camera.position.toArray().map((value) => value.toFixed(3)).join(",");
    const cameraControls = controls as { getTarget?: (out: THREE.Vector3) => THREE.Vector3 } | null;
    if (cameraControls?.getTarget) host.dataset.cameraTarget = cameraControls.getTarget(new THREE.Vector3()).toArray().map((value) => value.toFixed(3)).join(",");
    host.dataset.cameraAzimuthDegrees = (Math.atan2(camera.position.x, camera.position.z) * 180 / Math.PI).toFixed(2);
    host.dataset.cameraPolarDegrees = (Math.acos(THREE.MathUtils.clamp(camera.position.y / Math.max(camera.position.length(), 0.0001), -1, 1)) * 180 / Math.PI).toFixed(2);
    const rollingSeconds = frameDurations.current.reduce((total, item) => total + item, 0);
    host.dataset.actualFps = frameDurations.current.length >= 12 && rollingSeconds > 0
      ? (frameDurations.current.length / rollingSeconds).toFixed(1)
      : "0";
    host.dataset.environmentalParticleCount = String(environmentalParticleCount);
    host.dataset.relationParticleCount = String(relationParticleCount);
    host.dataset.visibleLabelCount = String(visibleLabelCount);
    host.dataset.aaMode = aaMode;
    host.dataset.bloomMode = bloomMode;
    host.dataset.postProcessingPassCount = String(postProcessingPassCount);
    const sampleSpan = frameTimes.current.length > 1 ? now - frameTimes.current[0] : 0;
    const samplingActive = host.dataset.cameraActive === "true";
    if (samplingActive && !downgradeTriggered.current && sampleSpan > 800 && frameTimes.current.length < 45) {
      lowFpsStartedAt.current ??= now;
      if (now - lowFpsStartedAt.current > 1000) {
        downgradeTriggered.current = true;
        onSustainedLowFps();
      }
    } else if (!samplingActive || frameTimes.current.length >= 45) {
      lowFpsStartedAt.current = null;
    }
  });

  return null;
}
