"use client";

import { useLayoutEffect, useMemo, useRef } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";

const CORE_VERTEX_SHADER = `
  uniform float uPixelRatio;
  void main() {
    vec4 modelViewPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = 24.0 * uPixelRatio;
    gl_Position = projectionMatrix * modelViewPosition;
  }
`;

const CORE_FRAGMENT_SHADER = `
  void main() {
    float radial = length(gl_PointCoord - vec2(0.5)) * 2.0;
    if (radial > 1.0) discard;
    float core = 1.0 - smoothstep(0.04, 0.2, radial);
    float halo = exp(-pow(radial * 2.8, 1.65));
    float alpha = max(core, halo * 0.44);
    if (alpha < 0.012) discard;
    vec3 energy = mix(vec3(0.59, 0.75, 0.24), vec3(1.0, 0.98, 0.78), core);
    gl_FragColor = vec4(energy, alpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export function ValueCore({ visible }: { visible: boolean }) {
  const ringsRef = useRef<THREE.InstancedMesh>(null);
  const { gl } = useThree();
  const corePosition = useMemo(() => new THREE.BufferAttribute(new Float32Array([0, 0, 0]), 3), []);
  const uniforms = useMemo(() => ({ uPixelRatio: { value: gl.getPixelRatio() } }), [gl]);
  useLayoutEffect(() => {
    const rings = ringsRef.current;
    if (!rings) return;
    const matrix = new THREE.Matrix4();
    const quaternion = new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2.45, 0, 0));
    [1.05, 1.55, 2.12].forEach((scale, index) => {
      matrix.compose(new THREE.Vector3(), quaternion, new THREE.Vector3(scale, scale, scale));
      rings.setMatrixAt(index, matrix);
    });
    rings.instanceMatrix.needsUpdate = true;
  }, []);
  if (!visible) return null;
  return <group raycast={() => undefined}>
    <points frustumCulled={false} raycast={() => undefined}>
      <bufferGeometry><primitive object={corePosition} attach="attributes-position" /></bufferGeometry>
      <shaderMaterial
        vertexShader={CORE_VERTEX_SHADER}
        fragmentShader={CORE_FRAGMENT_SHADER}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        toneMapped
      />
    </points>
    <instancedMesh ref={ringsRef} args={[undefined, undefined, 3]}>
      <torusGeometry args={[1, 0.0045, 3, 96]} />
      <meshBasicMaterial color="#b8d454" transparent opacity={0.075} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} />
    </instancedMesh>
  </group>;
}
