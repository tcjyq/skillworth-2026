"use client";

import { useCallback, useEffect, useRef } from "react";
import { CameraControls, CameraControlsImpl } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { gsap } from "gsap";
import * as THREE from "three";
import type { SceneMode, TransitionPhase } from "../state/scene-machine";
import type { QualityProfileName } from "./visual-system";
import { useRenderedSkillPositions } from "./rendered-positions";

export const CAMERA_LIMITS = {
  minAzimuthAngle: -Infinity,
  maxAzimuthAngle: Infinity,
  minPolarAngle: Math.PI / 2 - Math.PI * 70 / 180,
  maxPolarAngle: Math.PI / 2 + Math.PI * 70 / 180,
  minDistance: 12,
  maxDistance: 34,
} as const;

export function cameraMinDistance(mobile: boolean) {
  return mobile ? 13 : CAMERA_LIMITS.minDistance;
}

export function idleRotationEnabled(quality: QualityProfileName, mobile: boolean, reducedMotion: boolean) {
  return quality === "HIGH" && !mobile && !reducedMotion;
}

type CameraPreset = { position: [number, number, number]; target?: [number, number, number] };
type CameraPose = { position: [number, number, number]; target: [number, number, number] };

export const CAMERA_FOCUS_DISTANCE = 16.2;

export function cameraFocusDestination(
  position: readonly [number, number, number],
  target: readonly [number, number, number],
  focus: readonly [number, number, number],
  distance = CAMERA_FOCUS_DISTANCE,
): CameraPose {
  const direction = new THREE.Vector3(...position).sub(new THREE.Vector3(...target));
  if (direction.lengthSq() < 0.0001) direction.set(0, 0, 1);
  direction.normalize();
  const destination = new THREE.Vector3(...focus).addScaledVector(direction, distance);
  return { position: destination.toArray(), target: [...focus] };
}

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
  transitionPhase,
  activeSkillId,
  homeResetToken,
  relationReady,
  quality,
  mobile,
  onCameraFlyStart,
  onConstellationMorphStart,
  onFocusInterrupted,
  onReturnComplete,
}: {
  mode: SceneMode;
  focus: [number, number, number];
  reducedMotion: boolean;
  transitionToken: number;
  transitionPhase: TransitionPhase;
  activeSkillId: string | null;
  homeResetToken: number;
  relationReady: boolean;
  quality: QualityProfileName;
  mobile: boolean;
  onCameraFlyStart: (token: number) => void;
  onConstellationMorphStart: (token: number) => void;
  onFocusInterrupted: (token: number) => void;
  onReturnComplete: (token: number) => void;
}) {
  const { ACTION } = CameraControlsImpl;
  const controls = useRef<React.ElementRef<typeof CameraControls>>(null);
  const lastInteractionAt = useRef(0);
  const autoTween = useRef<gsap.core.Tween | null>(null);
  const focusProgress = useRef(0);
  const morphStarted = useRef(false);
  const phase = useRef(transitionPhase);
  const callbacks = useRef({ onCameraFlyStart, onConstellationMorphStart, onFocusInterrupted, onReturnComplete });
  const relationReadyRef = useRef(relationReady);
  const seenHomeResetToken = useRef(homeResetToken);
  const { gl, invalidate } = useThree();
  const { currentRenderedSkillPosition } = useRenderedSkillPositions();
  useEffect(() => {
    phase.current = transitionPhase;
    callbacks.current = { onCameraFlyStart, onConstellationMorphStart, onFocusInterrupted, onReturnComplete };
    relationReadyRef.current = relationReady;
  }, [onCameraFlyStart, onConstellationMorphStart, onFocusInterrupted, onReturnComplete, relationReady, transitionPhase]);
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
  const interruptAutomation = useCallback(() => {
    const tween = autoTween.current;
    if (!tween) return;
    tween.kill();
    autoTween.current = null;
    controls.current?.stop();
    markInteraction();
    setCameraActive(false);
    if (phase.current === "HIGHLIGHT" || phase.current === "CAMERA_FLY") {
      callbacks.current.onFocusInterrupted(transitionToken);
    } else if (phase.current === "RETURN_CAMERA") {
      callbacks.current.onReturnComplete(transitionToken);
    }
  }, [markInteraction, setCameraActive, transitionToken]);
  const beginUserInteraction = useCallback(() => {
    interruptAutomation();
    beginInteraction();
  }, [beginInteraction, interruptAutomation]);
  useEffect(() => {
    const canvas = gl.domElement;
    const interruptWheel = () => interruptAutomation();
    canvas.addEventListener("wheel", interruptWheel, { capture: true, passive: true });
    return () => canvas.removeEventListener("wheel", interruptWheel, { capture: true });
  }, [gl, interruptAutomation]);
  useEffect(() => {
    const instance = controls.current;
    const rendered = activeSkillId ? currentRenderedSkillPosition(activeSkillId) : null;
    const skillPosition = rendered?.toArray() as [number, number, number] | undefined;
    if (!instance || !skillPosition || reducedMotion || phase.current !== "HIGHLIGHT") return;
    const sourcePosition = instance.getPosition(new THREE.Vector3()).toArray();
    const sourceTarget = instance.getTarget(new THREE.Vector3()).toArray();
    const destination = cameraFocusDestination(sourcePosition, sourceTarget, skillPosition);
    const progress = { value: 0 };
    focusProgress.current = 0;
    morphStarted.current = false;
    instance.stop();
    markInteraction();
    setCameraActive(true);
    const startMorphIfReady = () => {
      if (morphStarted.current || !relationReadyRef.current) return;
      morphStarted.current = true;
      callbacks.current.onConstellationMorphStart(transitionToken);
    };
    autoTween.current = gsap.to(progress, {
      value: 1,
      delay: mobile ? 0.08 : 0.14,
      duration: mobile ? 0.52 : 0.72,
      ease: "power3.inOut",
      onStart: () => callbacks.current.onCameraFlyStart(transitionToken),
      onUpdate: () => {
        focusProgress.current = progress.value;
        if (progress.value >= 0.62) startMorphIfReady();
        void instance.lerpLookAt(
          ...sourcePosition,
          ...sourceTarget,
          ...destination.position,
          ...destination.target,
          progress.value,
          false,
        );
        const host = gl.domElement.closest<HTMLElement>('[data-testid="skill-field-canvas"]');
        if (host) host.dataset.cameraTransitionProgress = progress.value.toFixed(3);
        invalidate();
      },
      onComplete: () => {
        autoTween.current = null;
        startMorphIfReady();
        setCameraActive(false);
      },
    });
    return () => {
      autoTween.current?.kill();
      autoTween.current = null;
    };
  }, [activeSkillId, currentRenderedSkillPosition, gl, invalidate, markInteraction, mobile, reducedMotion, setCameraActive, transitionToken]);
  useEffect(() => {
    if (reducedMotion && phase.current === "CONSTELLATION_MORPH" && activeSkillId && relationReady) callbacks.current.onConstellationMorphStart(transitionToken);
    if (!reducedMotion && relationReady && focusProgress.current >= 0.62 && !morphStarted.current) {
      morphStarted.current = true;
      callbacks.current.onConstellationMorphStart(transitionToken);
    }
  }, [activeSkillId, reducedMotion, relationReady, transitionToken]);
  useEffect(() => {
    if (seenHomeResetToken.current === homeResetToken) return;
    seenHomeResetToken.current = homeResetToken;
    const instance = controls.current;
    if (!instance) return;
    autoTween.current?.kill();
    autoTween.current = null;
    instance.stop();
    const preset = cameraPresetFor("GLOBAL_VALUE");
    void instance.setLookAt(...preset.position, ...(preset.target ?? [0, -0.65, 0]), false);
    focusProgress.current = 0;
    morphStarted.current = false;
    lastInteractionAt.current = performance.now();
    setCameraActive(false);
    invalidate();
  }, [homeResetToken, invalidate, setCameraActive]);
  useEffect(() => {
    if (transitionPhase !== "RETURN_CAMERA") return;
    const instance = controls.current;
    if (!instance) return;
    const preset = cameraPresetFor(mode);
    const target = preset.target ?? focus;
    if (reducedMotion) {
      void instance.setLookAt(...preset.position, ...target, false);
      callbacks.current.onReturnComplete(transitionToken);
      return;
    }
    const sourcePosition = instance.getPosition(new THREE.Vector3()).toArray();
    const sourceTarget = instance.getTarget(new THREE.Vector3()).toArray();
    const progress = { value: 0 };
    instance.stop();
    setCameraActive(true);
    autoTween.current = gsap.to(progress, {
      value: 1,
      duration: mobile ? 0.38 : 0.56,
      ease: "power3.inOut",
      onUpdate: () => {
        void instance.lerpLookAt(...sourcePosition, ...sourceTarget, ...preset.position, ...target, progress.value, false);
        invalidate();
      },
      onComplete: () => {
        autoTween.current = null;
        setCameraActive(false);
        callbacks.current.onReturnComplete(transitionToken);
      },
    });
    return () => {
      autoTween.current?.kill();
      autoTween.current = null;
    };
  }, [focus, invalidate, mobile, mode, reducedMotion, setCameraActive, transitionPhase, transitionToken]);
  useEffect(() => {
    if (!idleRotationEnabled(quality, mobile, reducedMotion) || !["IDLE", "SETTLED"].includes(transitionPhase)) return;
    markInteraction();
    const timer = window.setInterval(() => {
      const instance = controls.current;
      if (!instance || performance.now() - lastInteractionAt.current < 4500) return;
      void instance.rotate(0.0009, 0, false);
      invalidate();
    }, 1000 / 4);
    return () => window.clearInterval(timer);
  }, [invalidate, markInteraction, mobile, quality, reducedMotion, transitionPhase]);
  return <CameraControls
    ref={controls}
    makeDefault
    minAzimuthAngle={CAMERA_LIMITS.minAzimuthAngle}
    maxAzimuthAngle={CAMERA_LIMITS.maxAzimuthAngle}
    minPolarAngle={CAMERA_LIMITS.minPolarAngle}
    maxPolarAngle={CAMERA_LIMITS.maxPolarAngle}
    minDistance={cameraMinDistance(mobile)}
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
    onControlStart={beginUserInteraction}
    onControl={interruptAutomation}
    onControlEnd={endInteraction}
    onRest={() => setCameraActive(false)}
  />;
}
