"use client";

import { useEffect, useMemo, useRef } from "react";
import { Html } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { gsap } from "gsap";
import * as THREE from "three";
import type { SceneRoleShift } from "../types";
import styles from "../skill-field.module.css";

export function RoleShiftLines({ shifts, reducedMotion, transitionToken }: { shifts: SceneRoleShift[]; reducedMotion: boolean; transitionToken: number }) {
  const materialRef = useRef<THREE.LineBasicMaterial>(null);
  const { invalidate } = useThree();
  const geometry = useMemo(() => {
    const positions = shifts.flatMap((shift) => [...shift.start, ...shift.end]);
    const output = new THREE.BufferGeometry();
    output.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    return output;
  }, [shifts]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => {
    const material = materialRef.current;
    if (!material || !shifts.length) return;
    material.opacity = 0.48;
    invalidate();
    if (reducedMotion) return;
    const tween = gsap.to(material, { opacity: 0, delay: 0.18, duration: 1.25, ease: "power2.out", onUpdate: invalidate });
    return () => { tween.kill(); };
  }, [invalidate, reducedMotion, shifts, transitionToken]);
  if (!shifts.length) return null;
  return <>
    <lineSegments geometry={geometry}><lineBasicMaterial ref={materialRef} color="#c8dc62" transparent depthWrite={false} /></lineSegments>
    {shifts.map((shift, index) => <Html key={shift.skillId} position={shift.end} center distanceFactor={13} zIndexRange={[18, 0]}>
      <span className={styles.roleShiftLabel} data-mobile-extra={index >= 3 ? "true" : undefined} data-reduced-motion={reducedMotion ? "true" : undefined}>
        {shift.label}<small>#{shift.globalRank} → #{shift.roleRank}</small>
      </span>
    </Html>)}
  </>;
}
