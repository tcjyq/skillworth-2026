"use client";

import { useCallback, useEffect, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import type { SceneMode, TransitionPhase } from "../state/scene-machine";
import type { SceneModel } from "../types";
import { CAMERA_LIMITS, CameraDirector, cameraMinDistance, idleRotationEnabled } from "./camera-director";
import { Labels } from "./labels";
import { PerformanceProbe } from "./performance-probe";
import { RelationLines } from "./relation-lines";
import { RoleShiftLines } from "./role-shift-lines";
import { SkillNodes } from "./skill-nodes";
import { Atmosphere } from "./atmosphere";
import { ValueCore } from "./value-core";
import { RenderedPositionProvider } from "./rendered-positions";
import { atmosphereParticleCount, nextQualityProfile, QUALITY_PROFILES, resolveAtmosphereVariant, type QualityProfileName } from "./visual-system";
import * as THREE from "three";
import styles from "../skill-field.module.css";

function WebGLContextGuard({ onContextLost }: { onContextLost: () => void }) {
  const { gl } = useThree();
  useEffect(() => {
    const handleContextLoss = (event: Event) => { event.preventDefault(); onContextLost(); };
    gl.domElement.addEventListener("webglcontextlost", handleContextLoss);
    const host = gl.domElement.closest<HTMLElement>('[data-testid="skill-field-canvas"]');
    if (host) host.dataset.contextGuardReady = "true";
    return () => {
      gl.domElement.removeEventListener("webglcontextlost", handleContextLoss);
      if (host) delete host.dataset.contextGuardReady;
    };
  }, [gl, onContextLost]);
  return null;
}

export default function SkillFieldCanvas({
  model,
  mode,
  activeSkillId,
  homeResetToken,
  selectedRelationId,
  reducedMotion,
  transitionToken,
  transitionPhase,
  relationReady,
  onSelect,
  onClearSelection,
  onCameraFlyStart,
  onConstellationMorphStart,
  onFocusInterrupted,
  onCameraDeparture,
  onMorphComplete,
  onReturnComplete,
  onContextLost,
}: {
  model: SceneModel;
  mode: SceneMode;
  activeSkillId: string | null;
  homeResetToken: number;
  selectedRelationId: string | null;
  reducedMotion: boolean;
  transitionToken: number;
  transitionPhase: TransitionPhase;
  relationReady: boolean;
  onSelect: (skillId: string) => void;
  onClearSelection: () => void;
  onCameraFlyStart: (token: number) => void;
  onConstellationMorphStart: (token: number) => void;
  onFocusInterrupted: (token: number) => void;
  onCameraDeparture: () => void;
  onMorphComplete: (token: number, returning: boolean) => void;
  onReturnComplete: (token: number) => void;
  onContextLost: () => void;
}) {
  const [hoveredSkillId, setHoveredSkillId] = useState<string | null>(null);
  const mobile = typeof window !== "undefined" && window.innerWidth < 768;
  const requestedQuality = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("quality")?.toUpperCase() : null;
  const [quality, setQuality] = useState<QualityProfileName>(() => mobile ? "LOW" : requestedQuality === "HIGH" || requestedQuality === "BALANCED" || requestedQuality === "LOW" ? requestedQuality : "HIGH");
  const atmosphereVariant = typeof window === "undefined" ? "B" : resolveAtmosphereVariant(new URLSearchParams(window.location.search).get("atmosphere"));
  const backgroundParticleCount = atmosphereParticleCount(quality, atmosphereVariant);
  const profile = QUALITY_PROFILES[quality];
  const downgradeQuality = useCallback(() => {
    if (requestedQuality) return;
    setQuality(nextQualityProfile);
  }, [requestedQuality]);
  const valueMode = mode === "GLOBAL_VALUE" || mode === "GLOBAL_DEMAND";
  return <div
    className={styles.canvas}
    data-testid="skill-field-canvas"
    data-skill-star-count={model.nodes.length}
    data-background-star-count={backgroundParticleCount}
    data-atmosphere-variant={atmosphereVariant}
    data-background-motion="static"
    data-skill-motion-cadence={String(profile.ambientCadenceFps)}
    data-skill-motion-enabled={String(!reducedMotion && profile.ambientCadenceFps > 0)}
    data-star-material="A"
    data-reduced-motion={String(reducedMotion)}
    data-camera-min-azimuth={String(CAMERA_LIMITS.minAzimuthAngle)}
    data-camera-max-azimuth={String(CAMERA_LIMITS.maxAzimuthAngle)}
    data-camera-min-polar={CAMERA_LIMITS.minPolarAngle.toFixed(4)}
    data-camera-max-polar={CAMERA_LIMITS.maxPolarAngle.toFixed(4)}
    data-camera-min-distance={String(cameraMinDistance(mobile))}
    data-camera-max-distance={String(CAMERA_LIMITS.maxDistance)}
    data-idle-rotation={String(idleRotationEnabled(quality, mobile, reducedMotion))}
    data-transition-phase={transitionPhase}
    data-transition-token={transitionToken}
    data-active-skill={activeSkillId ?? ""}
    data-unique-skill-count={new Set(model.nodes.map((node) => node.record.skill_id)).size}
    aria-label="交互式 3D 技能星域"
  >
    <Canvas
      frameloop="demand"
      dpr={[...profile.dpr]}
      camera={{ fov: 44, near: 0.1, far: 100, position: [1.4, 0.8, 25] }}
      gl={{ antialias: true, alpha: false, powerPreference: "high-performance", outputColorSpace: THREE.SRGBColorSpace, toneMapping: THREE.NeutralToneMapping, toneMappingExposure: 1.03 }}
      onPointerMissed={onClearSelection}
    >
      <color attach="background" args={["#090d0b"]} />
      <fog attach="fog" args={["#090d0b", 24, 52]} />
      <WebGLContextGuard onContextLost={onContextLost} />
      <PerformanceProbe qualityProfile={quality} environmentalParticleCount={backgroundParticleCount} relationParticleCount={0} visibleLabelCount={profile.visibleLabelCount} aaMode={profile.aaMode} bloomMode={profile.bloomMode} postProcessingPassCount={0} onSustainedLowFps={downgradeQuality} />
      <Atmosphere particleCount={backgroundParticleCount} />
      <ValueCore visible={valueMode} />
      <RenderedPositionProvider nodes={model.nodes}>
        <RoleShiftLines shifts={model.roleShifts} reducedMotion={reducedMotion} transitionToken={transitionToken} />
        <RelationLines lines={model.lines} selectedRelationId={selectedRelationId} hoveredSkillId={hoveredSkillId} reducedMotion={reducedMotion} transitionPhase={transitionPhase} transitionToken={transitionToken} />
        <SkillNodes
          nodes={model.nodes}
          reducedMotion={reducedMotion}
          selectedSkillId={selectedRelationId ?? activeSkillId}
          emphasisSkillIds={model.roleShifts.map((shift) => shift.skillId)}
          quality={quality}
          transitionPhase={transitionPhase}
          transitionToken={transitionToken}
          mobile={mobile}
          homeResetToken={homeResetToken}
          onHover={setHoveredSkillId}
          onSelect={onSelect}
          onMorphComplete={onMorphComplete}
        />
        <Labels nodes={model.nodes} lines={model.lines} relationMode={mode === "RELATION_GLOBAL" || mode === "RELATION_ROLE"} selectedRelationId={selectedRelationId} hoveredSkillId={hoveredSkillId} visibleLabelCount={profile.visibleLabelCount} protectValueCore={valueMode} transitionPhase={transitionPhase} activeSkillId={activeSkillId} onSelect={onSelect} />
        <CameraDirector
          mode={mode}
          focus={model.focus}
          activeSkillId={activeSkillId}
          homeResetToken={homeResetToken}
          reducedMotion={reducedMotion}
          transitionToken={transitionToken}
          transitionPhase={transitionPhase}
          relationReady={relationReady}
          quality={quality}
          mobile={mobile}
          onCameraFlyStart={onCameraFlyStart}
          onConstellationMorphStart={onConstellationMorphStart}
          onFocusInterrupted={onFocusInterrupted}
          onCameraDeparture={onCameraDeparture}
          onReturnComplete={onReturnComplete}
        />
      </RenderedPositionProvider>
    </Canvas>
  </div>;
}
