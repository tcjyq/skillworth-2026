"use client";

import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { SceneNode } from "../types";
import styles from "../skill-field.module.css";
import { resolveLabelPlacements, type LabelPlacement } from "./label-layout";

export function Labels({ nodes, hoveredSkillId, visibleLabelCount, protectValueCore, onSelect }: { nodes: SceneNode[]; hoveredSkillId: string | null; visibleLabelCount: number; protectValueCore: boolean; onSelect: (skillId: string) => void }) {
  const candidates = useMemo(() => nodes
    .filter((node) => node.labelPriority > 0 || node.record.skill_id === hoveredSkillId)
    .map((node) => ({
      node,
      priority: node.visualState === "selected"
        ? 1_000
        : node.record.skill_id === hoveredSkillId
          ? Math.max(node.labelPriority, 200)
          : node.labelPriority,
    })), [hoveredSkillId, nodes]);
  const [placements, setPlacements] = useState(new Map<string, LabelPlacement>());
  const signature = useRef("");
  const projected = useRef(new THREE.Vector3());

  useFrame(({ camera, size }) => {
    const layoutCandidates = candidates.map(({ node, priority }) => {
      projected.current.set(...node.position).project(camera);
      return {
        id: node.record.skill_id,
        anchor: [
          (projected.current.x * 0.5 + 0.5) * size.width,
          (-projected.current.y * 0.5 + 0.5) * size.height,
        ] as const,
        width: Math.max(70, node.record.skill.length * 11 + 18),
        height: 30,
        priority,
      };
    });
    const next = resolveLabelPlacements(layoutCandidates, {
      width: size.width,
      height: size.height,
      maxVisible: visibleLabelCount,
      protectedRects: protectValueCore ? [{
        left: size.width * 0.5 - 250,
        top: size.height * 0.48,
        right: size.width * 0.5 + 48,
        bottom: size.height * 0.72,
      }] : [],
    });
    const nextSignature = [...next].map(([id, item]) => `${id}:${item.visible ? 1 : 0}:${item.offset.join(",")}`).join("|");
    if (nextSignature !== signature.current) {
      signature.current = nextSignature;
      setPlacements(next);
    }
  });

  return <>{candidates.flatMap(({ node }, index) => {
    const placement = placements.get(node.record.skill_id);
    if (!placement?.visible) return [];
    return (
    <Html key={node.record.skill_id} position={node.position} center distanceFactor={12} zIndexRange={[20, 0]}>
      <div style={{ transform: `translate(${placement.offset[0]}px, ${placement.offset[1]}px)` }}>
        <button
          type="button"
          className={styles.nodeLabel}
          data-mobile-extra={index >= 4 ? "true" : undefined}
          data-selected={node.visualState === "selected" ? "true" : undefined}
          onClick={() => onSelect(node.record.skill_id)}
        >
          <span>{node.record.skill}</span>
        </button>
      </div>
    </Html>
  );})}</>;
}
