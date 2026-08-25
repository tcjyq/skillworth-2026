"use client";

import { useLayoutEffect, useRef } from "react";
import * as THREE from "three";

export function ValueCore({ visible }: { visible: boolean }) {
  const ringsRef = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    const rings = ringsRef.current;
    if (!rings) return;
    const matrix = new THREE.Matrix4();
    const quaternion = new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2.45, 0, 0));
    [1.15, 1.75, 2.45].forEach((scale, index) => {
      matrix.compose(new THREE.Vector3(), quaternion, new THREE.Vector3(scale, scale, scale));
      rings.setMatrixAt(index, matrix);
    });
    rings.instanceMatrix.needsUpdate = true;
  }, []);
  if (!visible) return null;
  return <group raycast={() => undefined}>
    <mesh>
      <icosahedronGeometry args={[0.23, 3]} />
      <meshBasicMaterial color={new THREE.Color("#c8dc62").multiplyScalar(1.75)} toneMapped />
    </mesh>
    <instancedMesh ref={ringsRef} args={[undefined, undefined, 3]}>
      <torusGeometry args={[1, 0.006, 3, 96]} />
      <meshBasicMaterial color="#c8dc62" transparent opacity={0.11} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} />
    </instancedMesh>
  </group>;
}
