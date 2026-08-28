"use client";

import { useEffect, useMemo, useRef } from "react";
import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { gsap } from "gsap";
import { stableHash } from "../layout";
import type { SceneLine } from "../types";
import styles from "../skill-field.module.css";
import { formatRelationEvidence } from "./visual-system";
import type { TransitionPhase } from "../state/scene-machine";
import { useRenderedSkillPositions } from "./rendered-positions";

type Endpoints = { start: THREE.Vector3; end: THREE.Vector3 };

export function relationLineEndpoints(source: THREE.Vector3, target: THREE.Vector3, sourceSize: number, targetSize: number): Endpoints {
  const direction = target.clone().sub(source);
  const distance = direction.length();
  if (distance < 0.0001) return { start: source.clone(), end: target.clone() };
  direction.multiplyScalar(1 / distance);
  const sourceGap = Math.min(distance * 0.22, Math.max(0.12, sourceSize * 0.58 + 0.08));
  const targetGap = Math.min(distance * 0.22, Math.max(0.1, targetSize * 0.58 + 0.06));
  return { start: source.clone().addScaledVector(direction, sourceGap), end: target.clone().addScaledVector(direction, -targetGap) };
}

function relationCurve(line: SceneLine, start: THREE.Vector3, end: THREE.Vector3) {
  const midpoint = start.clone().lerp(end, 0.5);
  const perpendicular = new THREE.Vector3(-end.y, end.x, 0).normalize();
  const sign = stableHash(line.id) % 2 ? 1 : -1;
  midpoint.addScaledVector(perpendicular, sign * Math.min(start.distanceTo(end) * 0.1, 0.72));
  midpoint.z += (((stableHash(line.id) >>> 8) % 101) / 100 - 0.5) * 0.48;
  return new THREE.QuadraticBezierCurve3(start, midpoint, end);
}

function RelationEvidenceAnchor({ line }: { line: SceneLine }) {
  const group = useRef<THREE.Group>(null);
  const { currentRenderedSkillPosition, currentRenderedSkillSize } = useRenderedSkillPositions();
  useFrame(() => {
    const source = currentRenderedSkillPosition(line.relation.core_skill_id);
    const target = currentRenderedSkillPosition(line.relation.related_skill_id);
    if (!source || !target || !group.current) return;
    const endpoints = relationLineEndpoints(source, target, currentRenderedSkillSize(line.relation.core_skill_id) ?? 0.2, currentRenderedSkillSize(line.relation.related_skill_id) ?? 0.2);
    group.current.position.copy(relationCurve(line, endpoints.start, endpoints.end).getPoint(0.56));
  });
  return <group ref={group}><Html center distanceFactor={12} zIndexRange={[22, 0]}><span className={styles.relationEvidenceLabel}>{formatRelationEvidence(line.relation.cooccurrence_count, line.relation.recency_window)}</span></Html></group>;
}

export function RelationLines({ lines, selectedRelationId, hoveredSkillId, reducedMotion, transitionPhase, transitionToken }: {
  lines: SceneLine[];
  selectedRelationId: string | null;
  hoveredSkillId: string | null;
  reducedMotion: boolean;
  transitionPhase: TransitionPhase;
  transitionToken: number;
}) {
  const materialRef = useRef<THREE.LineBasicMaterial>(null);
  const { currentRenderedSkillPosition, currentRenderedSkillSize } = useRenderedSkillPositions();
  const geometry = useMemo(() => {
    const segmentCounts = lines.map((line) => (line.primary ? 18 : 10));
    const segmentTotal = segmentCounts.reduce((sum, count) => sum + count, 0);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(segmentTotal * 6, 3));
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(segmentTotal * 6, 3));
    return geometry;
  }, [lines]);
  const selectedLine = lines.find((item) => item.relation.related_skill_id === selectedRelationId) ?? null;
  useEffect(() => () => geometry.dispose(), [geometry]);
  useFrame(({ gl }) => {
    const positionAttribute = geometry.getAttribute("position") as THREE.BufferAttribute;
    const colorAttribute = geometry.getAttribute("color") as THREE.BufferAttribute;
    const maximum = Math.max(...lines.map((line) => line.relation.cooccurrence_count), 1);
    let segmentOffset = 0;
    const probe: Record<string, unknown> = {};
    lines.forEach((line) => {
      const source = currentRenderedSkillPosition(line.relation.core_skill_id);
      const target = currentRenderedSkillPosition(line.relation.related_skill_id);
      const segmentCount = line.primary ? 18 : 10;
      if (!source || !target) return;
      const endpoints = relationLineEndpoints(source, target, currentRenderedSkillSize(line.relation.core_skill_id) ?? 0.2, currentRenderedSkillSize(line.relation.related_skill_id) ?? 0.2);
      const points = relationCurve(line, endpoints.start, endpoints.end).getPoints(segmentCount);
      const selected = line.relation.related_skill_id === selectedRelationId;
      const hovered = line.relation.related_skill_id === hoveredSkillId;
      const hasFocusedLine = Boolean(selectedRelationId || hoveredSkillId);
      const evidence = Math.sqrt(line.relation.cooccurrence_count / maximum);
      const intensity = selected || hovered ? 1.16 : hasFocusedLine ? line.primary ? 0.14 : 0.025 : line.primary ? 0.33 + evidence * 0.47 : 0.08;
      const sourceColor = new THREE.Color(line.coreColor).multiplyScalar(intensity);
      const targetColor = new THREE.Color(line.targetColor).multiplyScalar(intensity);
      for (let index = 0; index < segmentCount; index += 1) {
        const a = points[index];
        const b = points[index + 1];
        const attributeIndex = (segmentOffset + index) * 2;
        positionAttribute.setXYZ(attributeIndex, a.x, a.y, a.z);
        positionAttribute.setXYZ(attributeIndex + 1, b.x, b.y, b.z);
        const colorA = sourceColor.clone().lerp(targetColor, index / segmentCount);
        const colorB = sourceColor.clone().lerp(targetColor, (index + 1) / segmentCount);
        colorAttribute.setXYZ(attributeIndex, colorA.r, colorA.g, colorA.b);
        colorAttribute.setXYZ(attributeIndex + 1, colorB.r, colorB.g, colorB.b);
      }
      segmentOffset += segmentCount;
      probe[line.relation.related_skill_id] = { source: source.toArray().map((value) => Number(value.toFixed(3))), target: target.toArray().map((value) => Number(value.toFixed(3))), endpointStart: endpoints.start.toArray().map((value) => Number(value.toFixed(3))), endpointEnd: endpoints.end.toArray().map((value) => Number(value.toFixed(3))) };
    });
    positionAttribute.needsUpdate = true;
    colorAttribute.needsUpdate = true;
    const host = gl.domElement.closest<HTMLElement>('[data-testid="skill-field-canvas"]');
    if (host) {
      host.dataset.relationPositionProbe = JSON.stringify(probe);
      host.dataset.relationFocusedLine = selectedRelationId ?? hoveredSkillId ?? "";
    }
  });
  useEffect(() => {
    const material = materialRef.current;
    if (!material) return;
    if (reducedMotion) {
      material.opacity = transitionPhase === "RETURN_LINES" ? 0 : 0.92;
      return;
    }
    const tween = gsap.fromTo(material, { opacity: transitionPhase === "RETURN_LINES" ? material.opacity : 0 }, { opacity: transitionPhase === "RETURN_LINES" ? 0 : 0.92, delay: transitionPhase === "CONSTELLATION_MORPH" ? 0.3 : 0, duration: transitionPhase === "RETURN_LINES" ? 0.14 : 0.16, ease: "power2.out", overwrite: true });
    return () => { tween.kill(); };
  }, [reducedMotion, transitionPhase, transitionToken]);
  if (!lines.length) return null;
  return <>
    <lineSegments geometry={geometry} raycast={() => undefined}><lineBasicMaterial ref={materialRef} vertexColors transparent opacity={0.92} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped /></lineSegments>
    {selectedLine && <RelationEvidenceAnchor line={selectedLine} />}
  </>;
}
