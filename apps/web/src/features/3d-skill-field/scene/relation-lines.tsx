"use client";

import { useEffect, useMemo } from "react";
import * as THREE from "three";
import type { SceneLine } from "../types";

export function RelationLines({ lines, selectedRelationId }: { lines: SceneLine[]; selectedRelationId: string | null }) {
  const geometry = useMemo(() => {
    const positions: number[] = [];
    const colors: number[] = [];
    const maximum = Math.max(...lines.map((line) => line.relation.cooccurrence_count), 1);
    lines.forEach((line) => {
      positions.push(...line.start, ...line.end);
      const selected = line.relation.related_skill_id === selectedRelationId;
      const intensity = selected
        ? 1
        : selectedRelationId
          ? line.primary ? 0.09 : 0.035
          : line.primary ? 0.32 + 0.58 * Math.sqrt(line.relation.cooccurrence_count / maximum) : 0.16;
      const color = new THREE.Color("#c8dc62").multiplyScalar(intensity);
      colors.push(color.r, color.g, color.b, color.r, color.g, color.b);
    });
    const output = new THREE.BufferGeometry();
    output.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    output.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    return output;
  }, [lines, selectedRelationId]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  if (!lines.length) return null;
  return <lineSegments geometry={geometry}>
    <lineBasicMaterial vertexColors transparent opacity={0.9} depthWrite={false} />
  </lineSegments>;
}
