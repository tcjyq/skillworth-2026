"use client";

/* Three.js BufferAttributes are intentionally mutated in the render synchronization effect. */
/* eslint-disable react-hooks/immutability */

import { useEffect, useMemo, useRef } from "react";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { gsap } from "gsap";
import * as THREE from "three";
import type { SceneNode } from "../types";
import type { QualityProfileName } from "./visual-system";
import { QUALITY_PROFILES, skillColor } from "./visual-system";

const NODE_VERTEX_SHADER = `
  varying vec3 vInstanceColor;
  varying vec3 vNormal;
  varying vec3 vViewDirection;
  varying float vViewDepth;
  void main() {
    vInstanceColor = instanceColor;
    vec4 modelViewPosition = modelViewMatrix * instanceMatrix * vec4(position, 1.0);
    vNormal = normalize(mat3(modelViewMatrix * instanceMatrix) * normal);
    vViewDirection = normalize(-modelViewPosition.xyz);
    vViewDepth = -modelViewPosition.z;
    gl_Position = projectionMatrix * modelViewPosition;
  }
`;

const NODE_FRAGMENT_SHADER = `
  varying vec3 vInstanceColor;
  varying vec3 vNormal;
  varying vec3 vViewDirection;
  varying float vViewDepth;
  void main() {
    vec3 keyDirection = normalize(vec3(-0.42, 0.62, 0.65));
    float diffuse = 0.26 + 0.54 * max(dot(vNormal, keyDirection), 0.0);
    float facing = max(dot(vNormal, vViewDirection), 0.0);
    float fresnel = pow(1.0 - facing, 3.4);
    float highlight = pow(max(dot(normalize(keyDirection + vViewDirection), vNormal), 0.0), 18.0);
    vec3 body = mix(vInstanceColor * 0.46, vInstanceColor * 0.96, diffuse);
    vec3 color = body + vInstanceColor * fresnel * 0.42 + vec3(0.72, 0.80, 0.72) * highlight * 0.18;
    color = max(color, max(vInstanceColor * 0.58, vec3(0.042, 0.056, 0.047)));
    float depthFade = smoothstep(38.0, 18.0, vViewDepth);
    color = mix(vec3(0.035, 0.051, 0.043), color, 0.62 + 0.38 * depthFade);
    gl_FragColor = vec4(color, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const HALO_VERTEX_SHADER = `
  attribute vec3 color;
  attribute float haloSize;
  varying vec3 vColor;
  void main() {
    vColor = color;
    vec4 modelViewPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = clamp(haloSize * 190.0 / max(-modelViewPosition.z, 1.0), 1.5, 46.0);
    gl_Position = projectionMatrix * modelViewPosition;
  }
`;

const HALO_FRAGMENT_SHADER = `
  varying vec3 vColor;
  void main() {
    float distanceToCenter = distance(gl_PointCoord, vec2(0.5));
    float outer = smoothstep(0.5, 0.12, distanceToCenter);
    float innerControl = mix(0.48, 1.0, smoothstep(0.0, 0.22, distanceToCenter));
    float alpha = outer * innerControl;
    if (alpha < 0.01) discard;
    gl_FragColor = vec4(vColor, alpha * 0.34);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

function nodeColor(node: SceneNode) {
  if (node.visualState === "observed-only") return new THREE.Color("#6e7b71");
  const color = new THREE.Color(skillColor(node.record.skill_id, node.record.skill_category).color);
  if (node.visualState === "muted") return color.multiplyScalar(0.4);
  if (node.visualState === "highlighted") return color.multiplyScalar(1.04);
  if (node.visualState === "selected") return color.multiplyScalar(1.12);
  return color.multiplyScalar(0.78);
}

export function SkillNodes({
  nodes,
  reducedMotion,
  selectedSkillId,
  emphasisSkillIds,
  quality,
  onHover,
  onSelect,
}: {
  nodes: SceneNode[];
  reducedMotion: boolean;
  selectedSkillId: string | null;
  emphasisSkillIds: string[];
  quality: QualityProfileName;
  onHover: (skillId: string | null) => void;
  onSelect: (skillId: string) => void;
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const hitRef = useRef<THREE.InstancedMesh>(null);
  const previous = useRef(new Map<string, { position: THREE.Vector3; size: number }>());
  const { invalidate } = useThree();
  const nodeIndex = useMemo(() => nodes.map((node) => node.record.skill_id), [nodes]);
  const instanceColors = useMemo(() => new THREE.InstancedBufferAttribute(new Float32Array(Math.max(nodes.length, 1) * 3), 3), [nodes.length]);
  const haloPositions = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1) * 3), 3), [nodes.length]);
  const haloColors = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1) * 3), 3), [nodes.length]);
  const haloSizes = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1)), 1), [nodes.length]);

  useEffect(() => {
    const mesh = meshRef.current;
    const hit = hitRef.current;
    if (!mesh || !hit) return;
    const starts = nodes.map((node) => previous.current.get(node.record.skill_id) ?? {
      position: new THREE.Vector3(...node.position),
      size: reducedMotion ? node.size : node.size * 0.82,
    });
    const ends = nodes.map((node) => ({ position: new THREE.Vector3(...node.position), size: node.size }));
    const matrix = new THREE.Matrix4();
    const hitMatrix = new THREE.Matrix4();
    const quaternion = new THREE.Quaternion();
    const scaleVector = new THREE.Vector3();
    const emphasis = new Set(emphasisSkillIds);
    const progress = { value: reducedMotion ? 1 : 0 };
    const render = () => {
      nodes.forEach((node, index) => {
        const position = starts[index].position.clone().lerp(ends[index].position, progress.value);
        const scale = THREE.MathUtils.lerp(starts[index].size, ends[index].size, progress.value);
        scaleVector.setScalar(scale);
        matrix.compose(position, quaternion, scaleVector);
        hitMatrix.compose(position, quaternion, scaleVector.clone().multiplyScalar(2.15));
        mesh.setMatrixAt(index, matrix);
        hit.setMatrixAt(index, hitMatrix);
        const color = nodeColor(node);
        if (emphasis.size && !emphasis.has(node.record.skill_id) && progress.value < 0.72) color.multiplyScalar(0.82);
        if (emphasis.has(node.record.skill_id) && progress.value < 0.86) color.multiplyScalar(1.22);
        mesh.setColorAt(index, color);
        haloPositions.setXYZ(index, position.x, position.y, position.z);
        haloColors.setXYZ(index, color.r, color.g, color.b);
        const selected = node.record.skill_id === selectedSkillId;
        const stateIntensity = selected ? 2.35 : node.visualState === "highlighted" ? 1.25 : node.visualState === "muted" ? 0.12 : 0.42;
        haloSizes.setX(index, Math.max(scale, 0.22) * stateIntensity * QUALITY_PROFILES[quality].haloIntensity);
      });
      mesh.instanceMatrix.needsUpdate = true;
      hit.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      haloPositions.needsUpdate = true;
      haloColors.needsUpdate = true;
      haloSizes.needsUpdate = true;
      invalidate();
    };
    render();
    const tween = reducedMotion ? null : gsap.to(progress, {
      value: 1,
      duration: 1.45,
      ease: "power3.inOut",
      overwrite: true,
      onUpdate: render,
    });
    previous.current = new Map(ends.map((entry, index) => [nodes[index].record.skill_id, entry]));
    return () => { tween?.kill(); };
  }, [emphasisSkillIds, haloColors, haloPositions, haloSizes, instanceColors, invalidate, nodes, quality, reducedMotion, selectedSkillId]);

  const pointerNode = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    const skillId = event.instanceId === undefined ? null : nodeIndex[event.instanceId] ?? null;
    onHover(skillId);
    document.body.style.cursor = skillId ? "pointer" : "default";
  };
  const selectNode = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (event.instanceId !== undefined) onSelect(nodeIndex[event.instanceId]);
  };
  return <>
    <instancedMesh ref={meshRef} args={[undefined, undefined, nodes.length]} frustumCulled={false}>
      <sphereGeometry args={[1, 12, 8]} />
      <shaderMaterial vertexShader={NODE_VERTEX_SHADER} fragmentShader={NODE_FRAGMENT_SHADER} vertexColors toneMapped />
      <primitive object={instanceColors} attach="instanceColor" />
    </instancedMesh>
    <points frustumCulled={false} raycast={() => undefined}>
      <bufferGeometry>
        <primitive object={haloPositions} attach="attributes-position" />
        <primitive object={haloColors} attach="attributes-color" />
        <primitive object={haloSizes} attach="attributes-haloSize" />
      </bufferGeometry>
      <shaderMaterial vertexShader={HALO_VERTEX_SHADER} fragmentShader={HALO_FRAGMENT_SHADER} transparent depthWrite={false} blending={THREE.AdditiveBlending} toneMapped />
    </points>
    <instancedMesh ref={hitRef} args={[undefined, undefined, nodes.length]} frustumCulled={false} onPointerMove={pointerNode} onPointerOut={() => { onHover(null); document.body.style.cursor = "default"; }} onClick={selectNode}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} />
    </instancedMesh>
  </>;
}
