"use client";

import { useCallback, useEffect, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import type { SceneMode } from "../state/scene-machine";
import type { SceneModel } from "../types";
import { CameraDirector } from "./camera-director";
import { Labels } from "./labels";
import { PerformanceProbe } from "./performance-probe";
import { RelationLines } from "./relation-lines";
import { RoleShiftLines } from "./role-shift-lines";
import { SkillNodes } from "./skill-nodes";
import { Atmosphere } from "./atmosphere";
import { ValueCore } from "./value-core";
import { QUALITY_PROFILES, type QualityProfileName } from "./visual-system";
import * as THREE from "three";
import styles from "../skill-field.module.css";

function WebGLContextGuard({ onContextLost }: { onContextLost: () => void }) {
  const { gl } = useThree();
  useEffect(() => {
    const handleContextLoss = (event: Event) => { event.preventDefault(); onContextLost(); };
    gl.domElement.addEventListener("webglcontextlost", handleContextLoss);
    return () => gl.domElement.removeEventListener("webglcontextlost", handleContextLoss);
  }, [gl, onContextLost]);
  return null;
}

export default function SkillFieldCanvas({
  model,
  mode,
  activeSkillId,
  selectedRelationId,
  reducedMotion,
  transitionToken,
  onSelect,
  onClearSelection,
  onContextLost,
}: {
  model: SceneModel;
  mode: SceneMode;
  activeSkillId: string | null;
  selectedRelationId: string | null;
  reducedMotion: boolean;
  transitionToken: number;
  onSelect: (skillId: string) => void;
  onClearSelection: () => void;
  onContextLost: () => void;
}) {
  const [hoveredSkillId, setHoveredSkillId] = useState<string | null>(null);
  const mobile = typeof window !== "undefined" && window.innerWidth < 768;
  const requestedQuality = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("quality")?.toUpperCase() : null;
  const [quality, setQuality] = useState<QualityProfileName>(() => mobile ? "LOW" : requestedQuality === "HIGH" || requestedQuality === "LOW" ? requestedQuality : "BALANCED");
  const profile = QUALITY_PROFILES[quality];
  const downgradeQuality = useCallback(() => {
    if (requestedQuality) return;
    setQuality((current) => current === "HIGH" ? "BALANCED" : "LOW");
  }, [requestedQuality]);
  const valueMode = mode === "GLOBAL_VALUE" || mode === "GLOBAL_DEMAND";
  return <div className={styles.canvas} data-testid="skill-field-canvas" aria-label="交互式 3D 技能星域">
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
      <PerformanceProbe qualityProfile={quality} particleCount={profile.particleCount} visibleLabelCount={profile.visibleLabelCount} aaMode={profile.aaMode} bloomMode={profile.bloomMode} postProcessingPassCount={0} onSustainedLowFps={downgradeQuality} />
      <Atmosphere particleCount={profile.particleCount} />
      <ValueCore visible={valueMode} />
      <RoleShiftLines shifts={model.roleShifts} reducedMotion={reducedMotion} transitionToken={transitionToken} />
      <RelationLines lines={model.lines} selectedRelationId={selectedRelationId} reducedMotion={reducedMotion} quality={quality} />
      <SkillNodes
        nodes={model.nodes}
        reducedMotion={reducedMotion}
        selectedSkillId={selectedRelationId ?? activeSkillId}
        emphasisSkillIds={model.roleShifts.map((shift) => shift.skillId)}
        quality={quality}
        onHover={setHoveredSkillId}
        onSelect={onSelect}
      />
      <Labels nodes={model.nodes} hoveredSkillId={hoveredSkillId} visibleLabelCount={profile.visibleLabelCount} onSelect={onSelect} />
      <CameraDirector mode={mode} focus={model.focus} reducedMotion={reducedMotion} transitionToken={transitionToken} />
    </Canvas>
  </div>;
}
