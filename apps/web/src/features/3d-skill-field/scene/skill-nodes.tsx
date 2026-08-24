"use client";

import { useEffect, useMemo, useRef } from "react";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { gsap } from "gsap";
import * as THREE from "three";
import type { SceneNode } from "../types";

const COLORS = {
  default: new THREE.Color("#839084"),
  highlighted: new THREE.Color("#d9e3a4"),
  selected: new THREE.Color("#c8dc62"),
  muted: new THREE.Color("#243128"),
  "observed-only": new THREE.Color("#4c5650"),
};

const NODE_VERTEX_SHADER = `
  varying vec3 vInstanceColor;
  void main() {
    vInstanceColor = instanceColor;
    vec4 modelViewPosition = modelViewMatrix * instanceMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * modelViewPosition;
  }
`;

const NODE_FRAGMENT_SHADER = `
  varying vec3 vInstanceColor;
  void main() {
    gl_FragColor = vec4(vInstanceColor, 1.0);
    #include <colorspace_fragment>
  }
`;

export function SkillNodes({
  nodes,
  reducedMotion,
  selectedSkillId,
  onHover,
  onSelect,
}: {
  nodes: SceneNode[];
  reducedMotion: boolean;
  selectedSkillId: string | null;
  onHover: (skillId: string | null) => void;
  onSelect: (skillId: string) => void;
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const hitRef = useRef<THREE.InstancedMesh>(null);
  const previous = useRef(new Map<string, { position: THREE.Vector3; size: number }>());
  const { invalidate } = useThree();
  const nodeIndex = useMemo(() => nodes.map((node) => node.record.skill_id), [nodes]);
  const instanceColors = useMemo(
    () => new THREE.InstancedBufferAttribute(new Float32Array(Math.max(nodes.length, 1) * 3), 3),
    [nodes.length],
  );

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
    const progress = { value: reducedMotion ? 1 : 0 };
    const render = () => {
      nodes.forEach((node, index) => {
        const position = starts[index].position.clone().lerp(ends[index].position, progress.value);
        const scale = THREE.MathUtils.lerp(starts[index].size, ends[index].size, progress.value);
        matrix.compose(position, quaternion, new THREE.Vector3(scale, scale, scale));
        hitMatrix.compose(position, quaternion, new THREE.Vector3(scale * 2.15, scale * 2.15, scale * 2.15));
        mesh.setMatrixAt(index, matrix);
        hit.setMatrixAt(index, hitMatrix);
        mesh.setColorAt(index, COLORS[node.visualState]);
      });
      mesh.instanceMatrix.needsUpdate = true;
      hit.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      invalidate();
    };
    render();
    const tween = reducedMotion ? null : gsap.to(progress, {
      value: 1,
      duration: 0.82,
      ease: "power3.inOut",
      overwrite: true,
      onUpdate: render,
    });
    previous.current = new Map(ends.map((entry, index) => [nodes[index].record.skill_id, entry]));
    return () => { tween?.kill(); };
  }, [invalidate, nodes, reducedMotion]);

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
  const selected = nodes.find((node) => node.record.skill_id === selectedSkillId);

  return <>
    <instancedMesh ref={meshRef} args={[undefined, undefined, nodes.length]} frustumCulled={false}>
      <primitive object={instanceColors} attach="instanceColor" />
      <icosahedronGeometry args={[1, 2]} />
      <shaderMaterial vertexShader={NODE_VERTEX_SHADER} fragmentShader={NODE_FRAGMENT_SHADER} toneMapped={false} />
    </instancedMesh>
    <instancedMesh
      ref={hitRef}
      args={[undefined, undefined, nodes.length]}
      frustumCulled={false}
      onPointerMove={pointerNode}
      onPointerOut={() => { onHover(null); document.body.style.cursor = "default"; }}
      onClick={selectNode}
    >
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} />
    </instancedMesh>
    {selected && <mesh position={selected.position} scale={selected.size * 1.55}>
      <sphereGeometry args={[1, 18, 18]} />
      <meshBasicMaterial color="#c8dc62" wireframe transparent opacity={0.24} depthWrite={false} />
    </mesh>}
  </>;
}
