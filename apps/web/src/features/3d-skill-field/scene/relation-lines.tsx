"use client";

import { useEffect, useMemo } from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { stableHash } from "../layout";
import type { SceneLine } from "../types";
import styles from "../skill-field.module.css";
import { formatRelationEvidence, relationFlowParticleCount, type QualityProfileName } from "./visual-system";

function relationCurve(line: SceneLine) {
  const start = new THREE.Vector3(...line.start);
  const end = new THREE.Vector3(...line.end);
  const midpoint = start.clone().lerp(end, 0.5);
  const perpendicular = new THREE.Vector3(-end.y, end.x, 0).normalize();
  const sign = stableHash(line.id) % 2 ? 1 : -1;
  midpoint.addScaledVector(perpendicular, sign * Math.min(start.distanceTo(end) * 0.1, 0.72));
  midpoint.z += (((stableHash(line.id) >>> 8) % 101) / 100 - 0.5) * 0.48;
  return new THREE.QuadraticBezierCurve3(start, midpoint, end);
}

export function RelationLines({ lines, selectedRelationId, reducedMotion, quality }: {
  lines: SceneLine[];
  selectedRelationId: string | null;
  reducedMotion: boolean;
  quality: QualityProfileName;
}) {
  const geometry = useMemo(() => {
    const positions: number[] = [];
    const colors: number[] = [];
    const maximum = Math.max(...lines.map((line) => line.relation.cooccurrence_count), 1);
    lines.forEach((line) => {
      const points = relationCurve(line).getPoints(line.primary ? 18 : 10);
      const selected = line.relation.related_skill_id === selectedRelationId;
      const evidence = Math.sqrt(line.relation.cooccurrence_count / maximum);
      const intensity = selected ? 1.16 : selectedRelationId ? line.primary ? 0.17 : 0.025 : line.primary ? 0.33 + evidence * 0.47 : 0.08;
      const source = new THREE.Color(line.coreColor).multiplyScalar(intensity);
      const target = new THREE.Color(line.targetColor).multiplyScalar(intensity);
      for (let index = 0; index < points.length - 1; index += 1) {
        const a = points[index];
        const b = points[index + 1];
        const colorA = source.clone().lerp(target, index / (points.length - 1));
        const colorB = source.clone().lerp(target, (index + 1) / (points.length - 1));
        positions.push(a.x, a.y, a.z, b.x, b.y, b.z);
        colors.push(colorA.r, colorA.g, colorA.b, colorB.r, colorB.g, colorB.b);
      }
    });
    const output = new THREE.BufferGeometry();
    output.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    output.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    return output;
  }, [lines, selectedRelationId]);
  const flow = useMemo(() => {
    const line = lines.find((item) => item.relation.related_skill_id === selectedRelationId);
    const count = relationFlowParticleCount(quality, reducedMotion, Boolean(line));
    if (!line || count === 0) return null;
    const curve = relationCurve(line);
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const mirrored = index % 2 === 0 ? index / count : 1 - index / count;
      const point = curve.getPoint(0.12 + mirrored * 0.76);
      positions.set(point.toArray(), index * 3);
    }
    return new THREE.BufferAttribute(positions, 3);
  }, [lines, quality, reducedMotion, selectedRelationId]);
  const selectedLine = lines.find((item) => item.relation.related_skill_id === selectedRelationId) ?? null;
  const evidencePosition = selectedLine ? relationCurve(selectedLine).getPoint(0.56).toArray() as [number, number, number] : null;
  useEffect(() => () => geometry.dispose(), [geometry]);
  if (!lines.length) return null;
  return <>
    <lineSegments geometry={geometry} raycast={() => undefined}>
      <lineBasicMaterial vertexColors transparent opacity={0.92} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped />
    </lineSegments>
    {flow && <points raycast={() => undefined}>
      <bufferGeometry><primitive object={flow} attach="attributes-position" /></bufferGeometry>
      <pointsMaterial color="#f1f0e9" size={0.085} sizeAttenuation transparent opacity={0.88} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped />
    </points>}
    {selectedLine && evidencePosition && <Html position={evidencePosition} center distanceFactor={12} zIndexRange={[22, 0]}>
      <span className={styles.relationEvidenceLabel}>{formatRelationEvidence(selectedLine.relation.cooccurrence_count, selectedLine.relation.recency_window)}</span>
    </Html>}
  </>;
}
