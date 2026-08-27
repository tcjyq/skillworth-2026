"use client";

import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { stableHash } from "../layout";
import { DECORATIVE_PARTICLE_POLICY } from "./visual-system";

const DUST_VERTEX_SHADER = `
  attribute float starSize;
  attribute float brightness;
  uniform float uPixelRatio;
  varying float vBrightness;
  void main() {
    vBrightness = brightness;
    vec4 modelViewPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = clamp(starSize * 42.0 * uPixelRatio / max(-modelViewPosition.z, 1.0), 0.7 * uPixelRatio, 1.85 * uPixelRatio);
    gl_Position = projectionMatrix * modelViewPosition;
  }
`;

const DUST_FRAGMENT_SHADER = `
  varying float vBrightness;
  void main() {
    float radial = length(gl_PointCoord - vec2(0.5)) * 2.0;
    float alpha = (1.0 - smoothstep(0.12, 1.0, radial)) * vBrightness;
    if (alpha < 0.018) discard;
    gl_FragColor = vec4(vec3(0.62, 0.69, 0.65), alpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export function Atmosphere({ particleCount }: { particleCount: number }) {
  const { gl } = useThree();
  const attributes = useMemo(() => {
    const positions = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);
    const brightness = new Float32Array(particleCount);
    for (let index = 0; index < particleCount; index += 1) {
      const hash = stableHash(`ambient-star-${index}`);
      const layerRoll = (hash >>> 2) % 10;
      const layer = layerRoll < 2 ? 0 : layerRoll < 7 ? 1 : 2;
      const layerMin = [9.5, 18, 29][layer];
      const layerSpan = [12.5, 15, 15][layer];
      const radius = layerMin + ((hash >>> 4) % 1000) / 1000 * layerSpan;
      const u = (((hash >>> 10) & 0x7ff) + 0.5) / 2048;
      const v = (((hash >>> 21) & 0x7ff) + 0.5) / 2048;
      const theta = Math.acos(1 - 2 * u);
      const phi = 2 * Math.PI * v + index * Math.PI * (3 - Math.sqrt(5));
      positions[index * 3] = Math.sin(theta) * Math.cos(phi) * radius;
      positions[index * 3 + 1] = Math.cos(theta) * radius * 0.78;
      positions[index * 3 + 2] = Math.sin(theta) * Math.sin(phi) * radius;
      sizes[index] = layer === 0
        ? 0.86 + ((hash >>> 7) % 1000) / 1000 * 0.52
        : layer === 1
          ? 0.62 + ((hash >>> 7) % 1000) / 1000 * 0.5
          : 0.46 + ((hash >>> 7) % 1000) / 1000 * 0.34;
      brightness[index] = layer === 0
        ? 0.085 + ((hash >>> 17) % 1000) / 1000 * 0.075
        : layer === 1
          ? 0.065 + ((hash >>> 17) % 1000) / 1000 * 0.075
          : 0.04 + ((hash >>> 17) % 1000) / 1000 * 0.055;
    }
    return {
      positions: new THREE.BufferAttribute(positions, 3),
      sizes: new THREE.BufferAttribute(sizes, 1),
      brightness: new THREE.BufferAttribute(brightness, 1),
    };
  }, [particleCount]);
  const uniforms = useMemo(() => ({ uPixelRatio: { value: gl.getPixelRatio() } }), [gl]);
  return <points frustumCulled={false} raycast={DECORATIVE_PARTICLE_POLICY.pickable ? undefined : () => undefined}>
    <bufferGeometry>
      <primitive object={attributes.positions} attach="attributes-position" />
      <primitive object={attributes.sizes} attach="attributes-starSize" />
      <primitive object={attributes.brightness} attach="attributes-brightness" />
    </bufferGeometry>
    <shaderMaterial
      vertexShader={DUST_VERTEX_SHADER}
      fragmentShader={DUST_FRAGMENT_SHADER}
      uniforms={uniforms}
      transparent
      depthWrite={false}
      blending={THREE.AdditiveBlending}
      toneMapped
    />
  </points>;
}
