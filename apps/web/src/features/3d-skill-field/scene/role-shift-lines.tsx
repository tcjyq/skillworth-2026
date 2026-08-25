"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Html } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { gsap } from "gsap";
import * as THREE from "three";
import type { SceneRoleShift } from "../types";
import styles from "../skill-field.module.css";

export function RoleShiftLines({ shifts, reducedMotion, transitionToken }: { shifts: SceneRoleShift[]; reducedMotion: boolean; transitionToken: number }) {
  const materialRef = useRef<THREE.LineBasicMaterial>(null);
  const [settledToken, setSettledToken] = useState<number | null>(null);
  const { invalidate } = useThree();
  const hasRoleShifts = shifts.some((shift) => shift.kind === "role");
  const presentation = hasRoleShifts && !reducedMotion && settledToken !== transitionToken ? "explain" : "settled";
  const geometry = useMemo(() => {
    const positions = shifts.flatMap((shift, shiftIndex) => {
      const start = new THREE.Vector3(...shift.start);
      const end = new THREE.Vector3(...shift.end);
      const control = start.clone().lerp(end, 0.5);
      control.y += (shiftIndex % 2 ? -1 : 1) * Math.min(start.distanceTo(end) * 0.08, 0.8);
      const points = new THREE.QuadraticBezierCurve3(start, control, end).getPoints(18);
      return points.slice(0, -1).flatMap((point, index) => [...point.toArray(), ...points[index + 1].toArray()]);
    });
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
    const tween = gsap.to(material, { opacity: 0, delay: 0.3, duration: 1.45, ease: "power2.out", onUpdate: invalidate });
    return () => { tween.kill(); };
  }, [invalidate, reducedMotion, shifts, transitionToken]);
  useEffect(() => {
    if (!hasRoleShifts || reducedMotion) return;
    const timer = window.setTimeout(() => setSettledToken(transitionToken), 1_500);
    return () => window.clearTimeout(timer);
  }, [hasRoleShifts, reducedMotion, transitionToken]);
  if (!shifts.length) return null;
  return <>
    {!reducedMotion && <lineSegments geometry={geometry} raycast={() => undefined}><lineBasicMaterial ref={materialRef} color="#c8dc62" transparent depthWrite={false} blending={THREE.AdditiveBlending} toneMapped /></lineSegments>}
    {!reducedMotion && shifts.filter((shift) => shift.kind !== "cpp-demand").map((shift, index) => <Html key={`${shift.skillId}-ghost`} position={shift.start} center distanceFactor={13} zIndexRange={[17, 0]}><span className={styles.rankGhost} data-mobile-extra={index >= 3 ? "true" : undefined}>{shift.startLabel}</span></Html>)}
    {shifts.map((shift, index) => <Html key={shift.skillId} position={shift.end} center distanceFactor={13} zIndexRange={[18, 0]}>
      <span className={styles.roleShiftLabel} data-kind={shift.kind} data-presentation={shift.kind === "role" ? presentation : "settled"} data-mobile-extra={index >= 3 ? "true" : undefined} data-reduced-motion={reducedMotion ? "true" : undefined}>
        {shift.label}<small>{shift.endLabel}</small>{shift.summary && <b>{shift.summary}</b>}
      </span>
    </Html>)}
  </>;
}
