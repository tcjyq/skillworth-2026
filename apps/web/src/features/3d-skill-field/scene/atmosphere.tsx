"use client";

import { useMemo } from "react";
import * as THREE from "three";
import { stableHash } from "../layout";
import { DECORATIVE_PARTICLE_POLICY } from "./visual-system";

export function Atmosphere({ particleCount }: { particleCount: number }) {
  const positions = useMemo(() => {
    const values = new Float32Array(particleCount * 3);
    for (let index = 0; index < particleCount; index += 1) {
      const hash = stableHash(`ambient-particle-${index}`);
      const angle = index * Math.PI * (3 - Math.sqrt(5));
      const radius = 11 + (hash % 1000) / 1000 * 18;
      values[index * 3] = Math.cos(angle) * radius;
      values[index * 3 + 1] = (((hash >>> 10) % 2000) / 1000 - 1) * 13;
      values[index * 3 + 2] = -4 - ((hash >>> 20) % 1000) / 1000 * 25;
    }
    return new THREE.BufferAttribute(values, 3);
  }, [particleCount]);
  return <points frustumCulled={false} raycast={DECORATIVE_PARTICLE_POLICY.pickable ? undefined : () => undefined}>
    <bufferGeometry><primitive object={positions} attach="attributes-position" /></bufferGeometry>
    <pointsMaterial color="#839084" size={0.035} transparent opacity={0.32} depthWrite={false} toneMapped />
  </points>;
}
