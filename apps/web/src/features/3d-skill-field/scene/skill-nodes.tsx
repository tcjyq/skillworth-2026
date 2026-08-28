"use client";

/* Three.js BufferAttributes are intentionally mutated in the render synchronization effect. */
/* eslint-disable react-hooks/immutability */

import { useEffect, useMemo, useRef } from "react";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { gsap } from "gsap";
import * as THREE from "three";
import type { SceneNode } from "../types";
import type { TransitionPhase } from "../state/scene-machine";
import type { QualityProfileName } from "./visual-system";
import { QUALITY_PROFILES, skillColor, skillStarMotion, starPointerShouldSelect, SKILL_STAR_MATERIAL } from "./visual-system";
import { useRenderedSkillPositions } from "./rendered-positions";

const STAR_VERTEX_SHADER = `
  attribute float starSize;
  attribute float phase;
  attribute float speed;
  attribute float amplitude;
  attribute float attention;
  uniform float uTime;
  uniform float uMotionEnabled;
  uniform float uPixelRatio;
  uniform float uPointScale;
  uniform float uScreenFloorScale;
  varying vec3 vColor;
  varying float vAttention;
  varying float vBreath;
  varying float vTwinkle;
  void main() {
    vColor = color;
    vAttention = attention;
    vec4 modelViewPosition = modelViewMatrix * vec4(position, 1.0);
    float breath = sin(uTime * speed + phase) * amplitude * uMotionEnabled;
    float twinkleWave = sin(uTime * speed * 2.37 + phase * 1.73);
    float twinkle = smoothstep(0.78, 0.99, twinkleWave) * (0.03 + attention * 0.05) * uMotionEnabled;
    vBreath = breath;
    vTwinkle = twinkle;
    float visualScale = 1.0 + breath * 0.2 + attention * 0.24;
    float depthSizedPoint = starSize * uPointScale * uPixelRatio * visualScale / max(-modelViewPosition.z, 1.0);
    float screenMinimum = mix(7.6, 12.7, attention) * uScreenFloorScale * uPixelRatio;
    float screenMaximum = mix(11.3, 15.2, attention) * uScreenFloorScale * uPixelRatio;
    gl_PointSize = clamp(
      depthSizedPoint,
      screenMinimum,
      screenMaximum
    );
    gl_Position = projectionMatrix * modelViewPosition;
  }
`;

const STAR_FRAGMENT_SHADER = `
  uniform float uCoreRadius;
  uniform float uHaloFalloff;
  uniform float uHaloStrength;
  uniform float uWhiteCore;
  varying vec3 vColor;
  varying float vAttention;
  varying float vBreath;
  varying float vTwinkle;
  void main() {
    float radial = length(gl_PointCoord - vec2(0.5)) * 2.0;
    if (radial > 1.0) discard;
    float core = 1.0 - smoothstep(uCoreRadius * 0.52, uCoreRadius, radial);
    float halo = exp(-pow(radial * uHaloFalloff, 1.72));
    float flare = pow(max(1.0 - radial, 0.0), 7.0) * vAttention;
    float vitality = 1.0 + vBreath * 0.7 + vTwinkle;
    float alpha = max(core * (1.0 + vTwinkle * 0.3), halo * uHaloStrength * vitality) * (0.8 + vAttention * 0.2);
    if (alpha < 0.012) discard;
    vec3 haloColor = vColor * (0.72 + halo * 0.86 + vAttention * 0.32);
    vec3 color = mix(haloColor, vec3(1.0), core * uWhiteCore);
    color += vColor * flare * 0.44 + vec3(vTwinkle * 0.08 + max(vBreath, 0.0) * 0.03);
    gl_FragColor = vec4(color, alpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

function nodeColor(node: SceneNode, focusSkillId: string | null, focusActive: boolean) {
  if (node.visualState === "observed-only") return new THREE.Color("#77837a");
  const color = new THREE.Color(skillColor(node.record.skill_id, node.record.skill_category).color);
  if (node.visualState === "muted") return color.multiplyScalar(0.46);
  return color.multiplyScalar(focusActive && node.record.skill_id !== focusSkillId ? 0.68 : 0.94);
}

function nodeAttention(node: SceneNode, selectedSkillId: string | null, hoveredSkillId: string | null, emphasis: Set<string>) {
  if (node.record.skill_id === selectedSkillId) return 1;
  if (node.record.skill_id === hoveredSkillId) return 0.68;
  if (emphasis.has(node.record.skill_id) || node.visualState === "highlighted") return 0.42;
  if (node.visualState === "muted") return 0.02;
  return node.visualState === "observed-only" ? 0.06 : 0.14;
}

export function SkillNodes({
  nodes,
  reducedMotion,
  selectedSkillId,
  emphasisSkillIds,
  quality,
  transitionPhase,
  transitionToken,
  mobile,
  homeResetToken,
  onHover,
  onSelect,
  onMorphComplete,
}: {
  nodes: SceneNode[];
  reducedMotion: boolean;
  selectedSkillId: string | null;
  emphasisSkillIds: string[];
  quality: QualityProfileName;
  transitionPhase: TransitionPhase;
  transitionToken: number;
  mobile: boolean;
  homeResetToken: number;
  onHover: (skillId: string | null) => void;
  onSelect: (skillId: string) => void;
  onMorphComplete: (token: number, returning: boolean) => void;
}) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const hitRef = useRef<THREE.InstancedMesh>(null);
  const hoveredSkillId = useRef<string | null>(null);
  const { gl, invalidate } = useThree();
  const { currentRenderedSkillPosition, currentRenderedSkillSize, setRenderedSkillPosition } = useRenderedSkillPositions();
  const nodeIndex = useMemo(() => nodes.map((node) => node.record.skill_id), [nodes]);
  const positions = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1) * 3), 3), [nodes.length]);
  const colors = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1) * 3), 3), [nodes.length]);
  const sizes = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1)), 1), [nodes.length]);
  const phases = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1)), 1), [nodes.length]);
  const speeds = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1)), 1), [nodes.length]);
  const amplitudes = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1)), 1), [nodes.length]);
  const attentions = useMemo(() => new THREE.BufferAttribute(new Float32Array(Math.max(nodes.length, 1)), 1), [nodes.length]);
  const materialPreset = SKILL_STAR_MATERIAL;
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uMotionEnabled: { value: 0 },
    uPixelRatio: { value: 1 },
    uPointScale: { value: materialPreset.pointScale },
    uScreenFloorScale: { value: quality === "LOW" ? 0.88 : 1 },
    uCoreRadius: { value: materialPreset.coreRadius },
    uHaloFalloff: { value: materialPreset.haloFalloff },
    uHaloStrength: { value: materialPreset.haloStrength },
    uWhiteCore: { value: materialPreset.whiteCore },
  }), [materialPreset, quality]);

  useEffect(() => {
    const material = materialRef.current;
    if (!material) return;
    material.uniforms.uPixelRatio.value = gl.getPixelRatio();
    material.uniforms.uMotionEnabled.value = reducedMotion || QUALITY_PROFILES[quality].ambientCadenceFps === 0 ? 0 : 1;
    material.uniforms.uTime.value = performance.now() / 1000;
    const cadence = QUALITY_PROFILES[quality].ambientCadenceFps;
    if (!cadence || reducedMotion) {
      invalidate();
      return;
    }
    const timer = window.setInterval(() => {
      material.uniforms.uTime.value = performance.now() / 1000;
      invalidate();
    }, 1000 / cadence);
    return () => window.clearInterval(timer);
  }, [gl, invalidate, quality, reducedMotion]);

  useEffect(() => {
    const hit = hitRef.current;
    if (!hit) return;
    const starts = nodes.map((node) => {
      const position = currentRenderedSkillPosition(node.record.skill_id);
      const size = currentRenderedSkillSize(node.record.skill_id);
      return position && size !== null ? { position, size } : {
        position: new THREE.Vector3(...node.position),
        size: reducedMotion ? node.size : node.size * 0.86,
      };
    });
    const ends = nodes.map((node) => ({ position: new THREE.Vector3(...node.position), size: node.size }));
    const hitMatrix = new THREE.Matrix4();
    const quaternion = new THREE.Quaternion();
    const hitScale = new THREE.Vector3();
    const emphasis = new Set(emphasisSkillIds);
    const progress = { value: reducedMotion ? 1 : 0 };
    const focusActive = transitionPhase === "HIGHLIGHT" || transitionPhase === "CAMERA_FLY";
    const morphing = transitionPhase === "CONSTELLATION_MORPH" || transitionPhase === "RETURN_MORPH";
    const host = gl.domElement.closest<HTMLElement>('[data-testid="skill-field-canvas"]');
    if (host && morphing) {
      host.dataset.nodeMorphObservedIntermediate = "false";
      delete host.dataset.nodeMorphIntermediateProbe;
    }
    const render = () => {
      nodes.forEach((node, index) => {
        const position = starts[index].position.clone().lerp(ends[index].position, progress.value);
        const size = THREE.MathUtils.lerp(starts[index].size, ends[index].size, progress.value);
        setRenderedSkillPosition(node.record.skill_id, position, size);
        const color = nodeColor(node, selectedSkillId, focusActive);
        const motion = skillStarMotion(node.record.skill_id);
        positions.setXYZ(index, position.x, position.y, position.z);
        colors.setXYZ(index, color.r, color.g, color.b);
        sizes.setX(index, size);
        phases.setX(index, motion.phase);
        speeds.setX(index, motion.speed);
        amplitudes.setX(index, motion.amplitude);
        const attention = nodeAttention(node, selectedSkillId, hoveredSkillId.current, emphasis);
        const recognitionPulse = focusActive && node.record.skill_id === selectedSkillId
          ? 1 + Math.sin(Math.min(progress.value / 0.32, 1) * Math.PI) * 0.18
          : 1;
        attentions.setX(index, attention * recognitionPulse);
        const interactionRadius = Math.max(size * 2.45, quality === "LOW" ? 0.72 : 0.58);
        hitScale.setScalar(interactionRadius);
        hitMatrix.compose(position, quaternion, hitScale);
        hit.setMatrixAt(index, hitMatrix);
      });
      for (const attribute of [positions, colors, sizes, phases, speeds, amplitudes, attentions]) attribute.needsUpdate = true;
      hit.instanceMatrix.needsUpdate = true;
      if (host) {
        const probes = [...(nodes.length <= 8 ? nodes.map((node) => node.record.skill_id) : []), selectedSkillId, "programming_python", "database_sql", "devops_kubernetes"]
          .filter((skillId): skillId is string => Boolean(skillId));
        const nodeProbe = Object.fromEntries(probes.flatMap((skillId) => {
          const rendered = currentRenderedSkillPosition(skillId);
          return rendered ? [[skillId, rendered.toArray().map((value) => Number(value.toFixed(3)))]] : [];
        }));
        host.dataset.nodeProbe = JSON.stringify(nodeProbe);
        host.dataset.nodeMorphProgress = progress.value.toFixed(3);
        if (morphing && progress.value > 0.08 && progress.value < 0.92) {
          host.dataset.nodeMorphObservedIntermediate = "true";
          host.dataset.nodeMorphIntermediateProbe = JSON.stringify(nodeProbe);
        }
      }
      invalidate();
    };
    render();
    const duration = morphing
      ? reducedMotion ? 0 : mobile ? 0.3 : transitionPhase === "RETURN_MORPH" ? 0.42 : 0.46
      : 1.45;
    const tween = reducedMotion ? null : gsap.to(progress, {
      value: 1,
      duration,
      ease: "power3.inOut",
      overwrite: true,
      onUpdate: render,
      onComplete: () => {
        if (morphing) onMorphComplete(transitionToken, transitionPhase === "RETURN_MORPH");
      },
    });
    if (reducedMotion && morphing) onMorphComplete(transitionToken, transitionPhase === "RETURN_MORPH");
    return () => { tween?.kill(); };
  }, [amplitudes, attentions, colors, currentRenderedSkillPosition, currentRenderedSkillSize, emphasisSkillIds, gl, invalidate, mobile, nodes, onMorphComplete, phases, positions, quality, reducedMotion, selectedSkillId, setRenderedSkillPosition, sizes, speeds, transitionPhase, transitionToken]);

  useEffect(() => {
    hoveredSkillId.current = null;
    onHover(null);
    document.body.style.cursor = "default";
  }, [homeResetToken, onHover]);

  const updateHover = (skillId: string | null) => {
    if (hoveredSkillId.current === skillId) return;
    hoveredSkillId.current = skillId;
    const emphasis = new Set(emphasisSkillIds);
    nodes.forEach((node, index) => attentions.setX(index, nodeAttention(node, selectedSkillId, skillId, emphasis)));
    attentions.needsUpdate = true;
    onHover(skillId);
    document.body.style.cursor = skillId ? "pointer" : "default";
    invalidate();
  };
  const pointerNode = (event: ThreeEvent<PointerEvent>) => {
    updateHover(event.instanceId === undefined ? null : nodeIndex[event.instanceId] ?? null);
  };
  const selectNode = (event: ThreeEvent<MouseEvent>) => {
    if (!starPointerShouldSelect(event.delta)) return;
    event.stopPropagation();
    if (event.instanceId !== undefined) onSelect(nodeIndex[event.instanceId]);
  };

  return <>
    <points frustumCulled={false} raycast={() => undefined}>
      <bufferGeometry>
        <primitive object={positions} attach="attributes-position" />
        <primitive object={colors} attach="attributes-color" />
        <primitive object={sizes} attach="attributes-starSize" />
        <primitive object={phases} attach="attributes-phase" />
        <primitive object={speeds} attach="attributes-speed" />
        <primitive object={amplitudes} attach="attributes-amplitude" />
        <primitive object={attentions} attach="attributes-attention" />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        vertexShader={STAR_VERTEX_SHADER}
        fragmentShader={STAR_FRAGMENT_SHADER}
        uniforms={uniforms}
        vertexColors
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        toneMapped
      />
    </points>
    <instancedMesh
      ref={hitRef}
      args={[undefined, undefined, nodes.length]}
      frustumCulled={false}
      onPointerMove={pointerNode}
      onPointerOut={() => updateHover(null)}
      onClick={selectNode}
    >
      <sphereGeometry args={[1, 6, 4]} />
      <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} />
    </instancedMesh>
  </>;
}
