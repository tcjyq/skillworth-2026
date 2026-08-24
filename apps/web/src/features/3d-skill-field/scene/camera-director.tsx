"use client";

import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import type { SceneMode } from "../state/scene-machine";

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
    const distance = mode.startsWith("RELATION") ? 22 : 25;
    void instance.setLookAt(1.4, 0.8, distance, focus[0], focus[1], focus[2], !reducedMotion);
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
    smoothTime={0.38}
    draggingSmoothTime={0.12}
    dollySpeed={0.45}
    truckSpeed={0}
    dollyToCursor={false}
  />;
}
