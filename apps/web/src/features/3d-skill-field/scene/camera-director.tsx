"use client";

import { useCallback, useEffect, useRef } from "react";
import { CameraControls, CameraControlsImpl } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import type { SceneMode } from "../state/scene-machine";
import type { QualityProfileName } from "./visual-system";

export const CAMERA_LIMITS = {
  minAzimuthAngle: -Infinity,
  maxAzimuthAngle: Infinity,
  minPolarAngle: Math.PI / 2 - Math.PI * 70 / 180,
  maxPolarAngle: Math.PI / 2 + Math.PI * 70 / 180,
  minDistance: 15,
  maxDistance: 34,
} as const;

export function idleRotationEnabled(quality: QualityProfileName, mobile: boolean, reducedMotion: boolean) {
  return quality === "HIGH" && !mobile && !reducedMotion;
}

type CameraPreset = { position: [number, number, number]; target?: [number, number, number] };

const CAMERA_PRESETS: Record<SceneMode, CameraPreset> = {
  GLOBAL_VALUE: { position: [10, 3.4, 16.3], target: [0, -0.65, 0] },
  GLOBAL_DEMAND: { position: [-13.5, 2.4, 23.4] },
  ROLE_VALUE: { position: [5.6, 1.5, 25.5] },
  RELATION_GLOBAL: { position: [2.9, 3.4, 21.5] },
  RELATION_ROLE: { position: [-3.2, 2.6, 21.8] },
};

export function cameraPresetFor(mode: SceneMode) {
  return CAMERA_PRESETS[mode];
}

export function CameraDirector({
  mode,
  focus,
  reducedMotion,
  transitionToken,
  quality,
  mobile,
}: {
  mode: SceneMode;
  focus: [number, number, number];
  reducedMotion: boolean;
  transitionToken: number;
  quality: QualityProfileName;
  mobile: boolean;
}) {
  const { ACTION } = CameraControlsImpl;
  const controls = useRef<React.ElementRef<typeof CameraControls>>(null);
  const lastInteractionAt = useRef(0);
  const { gl, invalidate } = useThree();
  const markInteraction = useCallback(() => { lastInteractionAt.current = performance.now(); }, []);
  const setCameraActive = useCallback((active: boolean) => {
    const host = gl.domElement.closest<HTMLElement>('[data-testid="skill-field-canvas"]');
    if (host) host.dataset.cameraActive = String(active);
  }, [gl]);
  const beginInteraction = useCallback(() => {
    markInteraction();
    setCameraActive(true);
  }, [markInteraction, setCameraActive]);
  const endInteraction = useCallback(() => {
    markInteraction();
    setCameraActive(false);
  }, [markInteraction, setCameraActive]);
  useEffect(() => {
    const instance = controls.current;
    if (!instance) return;
    instance.stop();
    instance.normalizeRotations();
    const preset = cameraPresetFor(mode);
    markInteraction();
    setCameraActive(!reducedMotion);
    const target = preset.target ?? focus;
    void instance.setLookAt(...preset.position, target[0], target[1], target[2], !reducedMotion);
  }, [focus, markInteraction, mode, reducedMotion, setCameraActive, transitionToken]);
  useEffect(() => {
    if (!idleRotationEnabled(quality, mobile, reducedMotion)) return;
    markInteraction();
    const timer = window.setInterval(() => {
      const instance = controls.current;
      if (!instance || performance.now() - lastInteractionAt.current < 4500) return;
      void instance.rotate(0.0009, 0, false);
      invalidate();
    }, 1000 / 4);
    return () => window.clearInterval(timer);
  }, [invalidate, markInteraction, mobile, quality, reducedMotion]);
  return <CameraControls
    ref={controls}
    makeDefault
    minAzimuthAngle={CAMERA_LIMITS.minAzimuthAngle}
    maxAzimuthAngle={CAMERA_LIMITS.maxAzimuthAngle}
    minPolarAngle={CAMERA_LIMITS.minPolarAngle}
    maxPolarAngle={CAMERA_LIMITS.maxPolarAngle}
    minDistance={CAMERA_LIMITS.minDistance}
    maxDistance={CAMERA_LIMITS.maxDistance}
    smoothTime={0.46}
    draggingSmoothTime={0.12}
    dollySpeed={0.45}
    truckSpeed={0}
    dollyToCursor={false}
    mouseButtons={{
      left: ACTION.ROTATE,
      middle: ACTION.DOLLY,
      right: ACTION.ROTATE,
      wheel: ACTION.DOLLY,
    }}
    touches={{
      one: ACTION.TOUCH_ROTATE,
      two: ACTION.TOUCH_DOLLY_TRUCK,
      three: ACTION.TOUCH_ROTATE,
    }}
    onControlStart={beginInteraction}
    onControlEnd={endInteraction}
    onRest={() => setCameraActive(false)}
  />;
}
