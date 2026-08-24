"use client";

import { useEffect, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import type { SceneMode } from "../state/scene-machine";
import type { SceneModel } from "../types";
import { CameraDirector } from "./camera-director";
import { Labels } from "./labels";
import { PerformanceProbe } from "./performance-probe";
import { RelationLines } from "./relation-lines";
import { RoleShiftLines } from "./role-shift-lines";
import { SkillNodes } from "./skill-nodes";
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
  return <div className={styles.canvas} data-testid="skill-field-canvas" aria-label="交互式 3D 技能星域">
    <Canvas
      frameloop="demand"
      dpr={mobile ? [1, 1.15] : [1, 1.55]}
      camera={{ fov: 44, near: 0.1, far: 100, position: [1.4, 0.8, 25] }}
      gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
      onPointerMissed={onClearSelection}
    >
      <color attach="background" args={["#090d0b"]} />
      <fog attach="fog" args={["#090d0b", 28, 56]} />
      <WebGLContextGuard onContextLost={onContextLost} />
      <PerformanceProbe />
      <RoleShiftLines shifts={model.roleShifts} reducedMotion={reducedMotion} transitionToken={transitionToken} />
      <RelationLines lines={model.lines} selectedRelationId={selectedRelationId} />
      <SkillNodes
        nodes={model.nodes}
        reducedMotion={reducedMotion}
        selectedSkillId={activeSkillId ?? selectedRelationId}
        onHover={setHoveredSkillId}
        onSelect={onSelect}
      />
      <Labels nodes={model.nodes} hoveredSkillId={hoveredSkillId} onSelect={onSelect} />
      <CameraDirector mode={mode} focus={model.focus} reducedMotion={reducedMotion} transitionToken={transitionToken} />
    </Canvas>
  </div>;
}
