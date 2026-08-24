"use client";

import { Html } from "@react-three/drei";
import type { SceneNode } from "../types";
import styles from "../skill-field.module.css";

export function Labels({ nodes, hoveredSkillId, onSelect }: { nodes: SceneNode[]; hoveredSkillId: string | null; onSelect: (skillId: string) => void }) {
  const visible = nodes
    .filter((node) => node.labelPriority > 0 || node.record.skill_id === hoveredSkillId)
    .toSorted((left, right) => right.labelPriority - left.labelPriority)
    .slice(0, hoveredSkillId ? 10 : 8);
  return <>{visible.map((node, index) => (
    <Html key={node.record.skill_id} position={node.position} center distanceFactor={12} zIndexRange={[20, 0]}>
      <button
        type="button"
        className={styles.nodeLabel}
        data-mobile-extra={index >= 4 ? "true" : undefined}
        data-selected={node.visualState === "selected" ? "true" : undefined}
        onClick={() => onSelect(node.record.skill_id)}
      >
        <span>{node.record.skill}</span>
        {node.relation && <small>{node.relation.cooccurrence_count} 个岗位一起出现</small>}
      </button>
    </Html>
  ))}</>;
}
