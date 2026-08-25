"use client";

import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import type { SceneMode } from "../state/scene-machine";

const CAMERA_PRESETS = {
  GLOBAL_VALUE: { position: [14.3, 3.1, 22.9] },
  GLOBAL_DEMAND: { position: [-13.5, 2.4, 23.4] },
  ROLE_VALUE: { position: [5.6, 1.5, 25.5] },
  RELATION_GLOBAL: { position: [2.9, 3.4, 21.5] },
  RELATION_ROLE: { position: [-3.2, 2.6, 21.8] },
} satisfies Record<SceneMode, { position: [number, number, number] }>;

export function cameraPresetFor(mode: SceneMode) {
  return CAMERA_PRESETS[mode];
}

export function CameraDirector({
  mode,
  focus,
  reducedMotion,
  transitionToken,
}: {
  mode: SceneMode;
  focus: [number, number, number];
  reducedMotion: boolean;
  transitionToken: number;
}) {
  const controls = useRef<React.ElementRef<typeof CameraControls>>(null);
  useEffect(() => {
    const instance = controls.current;
    if (!instance) return;
    instance.stop();
    instance.normalizeRotations();
    const preset = cameraPresetFor(mode);
    void instance.setLookAt(...preset.position, focus[0], focus[1], focus[2], !reducedMotion);
  }, [focus, mode, reducedMotion, transitionToken]);
  return <CameraControls
    ref={controls}
    makeDefault
    minAzimuthAngle={-Math.PI / 4}
    maxAzimuthAngle={Math.PI / 4}
    minPolarAngle={Math.PI / 2 - Math.PI / 9}
    maxPolarAngle={Math.PI / 2 + Math.PI / 9}
    minDistance={15}
    maxDistance={34}
    smoothTime={0.46}
    draggingSmoothTime={0.12}
    dollySpeed={0.45}
    truckSpeed={0}
    dollyToCursor={false}
  />;
}
