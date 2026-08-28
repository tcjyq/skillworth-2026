"use client";

import { createContext, useContext, useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { SceneNode } from "../types";

type RenderedSkillPosition = { position: THREE.Vector3; size: number };

type RenderedPositionSource = {
  currentRenderedSkillPosition: (skillId: string, target?: THREE.Vector3) => THREE.Vector3 | null;
  currentRenderedSkillSize: (skillId: string) => number | null;
  setRenderedSkillPosition: (skillId: string, position: THREE.Vector3, size: number) => void;
};

const RenderedPositionContext = createContext<RenderedPositionSource | null>(null);

export function RenderedPositionProvider({ nodes, children }: { nodes: SceneNode[]; children: React.ReactNode }) {
  const positions = useRef(new Map<string, RenderedSkillPosition>());
  useEffect(() => {
    const ids = new Set(nodes.map((node) => node.record.skill_id));
    positions.current.forEach((_, skillId) => {
      if (!ids.has(skillId)) positions.current.delete(skillId);
    });
    nodes.forEach((node) => {
      if (!positions.current.has(node.record.skill_id)) {
        positions.current.set(node.record.skill_id, { position: new THREE.Vector3(...node.position), size: node.size });
      }
    });
  }, [nodes]);
  const source = useMemo<RenderedPositionSource>(() => ({
    currentRenderedSkillPosition: (skillId, target = new THREE.Vector3()) => {
      const entry = positions.current.get(skillId);
      return entry ? target.copy(entry.position) : null;
    },
    currentRenderedSkillSize: (skillId) => positions.current.get(skillId)?.size ?? null,
    setRenderedSkillPosition: (skillId, position, size) => {
      const existing = positions.current.get(skillId);
      if (existing) {
        existing.position.copy(position);
        existing.size = size;
      } else {
        positions.current.set(skillId, { position: position.clone(), size });
      }
    },
  }), []);
  return <RenderedPositionContext.Provider value={source}>{children}</RenderedPositionContext.Provider>;
}

export function useRenderedSkillPositions() {
  const source = useContext(RenderedPositionContext);
  if (!source) throw new Error("Rendered skill positions must be read inside RenderedPositionProvider");
  return source;
}
