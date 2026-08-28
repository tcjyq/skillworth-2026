"use client";

import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { SceneLine, SceneNode } from "../types";
import styles from "../skill-field.module.css";
import { rankBrowsableLabelCandidates, resolveLabelPlacements, type LabelPlacement } from "./label-layout";
import type { TransitionPhase } from "../state/scene-machine";
import { useRenderedSkillPositions } from "./rendered-positions";

const LABEL_REFRESH_MS = 125;
const SAFE_VIEWPORT_INSET = 0.08;

type LabelState = { placements: Map<string, LabelPlacement>; visibleIds: string[] };

function labelWidth(label: string) { return Math.max(74, label.length * 7.5 + 22); }

function cameraSignature(camera: THREE.Camera) {
  return [...camera.matrixWorld.elements, ...camera.projectionMatrix.elements].map((value) => value.toFixed(3)).join(",");
}

function RenderedHtmlAnchor({ skillId, children }: { skillId: string; children: React.ReactNode }) {
  const group = useRef<THREE.Group>(null);
  const { currentRenderedSkillPosition } = useRenderedSkillPositions();
  useFrame(() => {
    const position = currentRenderedSkillPosition(skillId);
    if (position && group.current) group.current.position.copy(position);
  });
  return <group ref={group}><Html center distanceFactor={12} zIndexRange={[20, 0]}>{children}</Html></group>;
}

export function Labels({ nodes, lines, relationMode, selectedRelationId, hoveredSkillId, visibleLabelCount, protectValueCore, transitionPhase, activeSkillId, onSelect }: {
  nodes: SceneNode[];
  lines: SceneLine[];
  relationMode: boolean;
  selectedRelationId: string | null;
  hoveredSkillId: string | null;
  visibleLabelCount: number;
  protectValueCore: boolean;
  transitionPhase: TransitionPhase;
  activeSkillId: string | null;
  onSelect: (skillId: string) => void;
}) {
  const positionMorphing = transitionPhase === "CONSTELLATION_MORPH" || transitionPhase === "RETURN_MORPH";
  const { currentRenderedSkillPosition } = useRenderedSkillPositions();
  const primaryRelationIds = useMemo(() => new Set(lines.filter((line) => line.primary).map((line) => line.relation.related_skill_id)), [lines]);
  const relationNodeIds = useMemo(() => new Set([activeSkillId, ...lines.map((line) => line.relation.related_skill_id)].filter((id): id is string => Boolean(id))), [activeSkillId, lines]);
  const visibleNodes = useMemo(() => relationMode ? nodes.filter((node) => relationNodeIds.has(node.record.skill_id)) : nodes, [nodes, relationMode, relationNodeIds]);
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.record.skill_id, node])), [nodes]);
  const [labelState, setLabelState] = useState<LabelState>({ placements: new Map(), visibleIds: [] });
  const [tooltipSkillId, setTooltipSkillId] = useState<string | null>(null);
  const previousIds = useRef(new Set<string>());
  const lastCamera = useRef("");
  const lastComputedAt = useRef(0);
  const wasMoving = useRef(false);
  const layoutSignature = useRef("");
  const tooltipTimer = useRef<number | null>(null);
  const frustum = useRef(new THREE.Frustum());
  const projection = useRef(new THREE.Matrix4());
  const worldPoint = useRef(new THREE.Vector3());
  const projectedPoint = useRef(new THREE.Vector3());

  useEffect(() => { lastComputedAt.current = 0; }, [activeSkillId, hoveredSkillId, positionMorphing, relationMode, selectedRelationId, visibleLabelCount, visibleNodes]);
  useEffect(() => {
    if (tooltipTimer.current !== null) window.clearTimeout(tooltipTimer.current);
    if (hoveredSkillId) {
      const frame = window.requestAnimationFrame(() => setTooltipSkillId(hoveredSkillId));
      return () => window.cancelAnimationFrame(frame);
    }
    tooltipTimer.current = window.setTimeout(() => setTooltipSkillId(null), 90);
    return () => { if (tooltipTimer.current !== null) window.clearTimeout(tooltipTimer.current); };
  }, [hoveredSkillId]);

  useFrame(({ camera, gl, size }) => {
    const now = performance.now();
    const nextCamera = cameraSignature(camera);
    const moving = nextCamera !== lastCamera.current;
    const readyForActiveRefresh = moving && now - lastComputedAt.current >= LABEL_REFRESH_MS;
    const readyForPositionRefresh = positionMorphing && now - lastComputedAt.current >= LABEL_REFRESH_MS;
    const needsSettledRefresh = !moving && wasMoving.current;
    if (lastComputedAt.current !== 0 && !readyForActiveRefresh && !readyForPositionRefresh && !needsSettledRefresh) return;

    lastCamera.current = nextCamera;
    wasMoving.current = moving;
    lastComputedAt.current = now;
    projection.current.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    frustum.current.setFromProjectionMatrix(projection.current);
    const insetX = size.width * SAFE_VIEWPORT_INSET;
    const insetY = size.height * SAFE_VIEWPORT_INSET;
    const lockedIds = new Set([activeSkillId, selectedRelationId, hoveredSkillId].filter((id): id is string => Boolean(id)));
    const candidates = visibleNodes.flatMap((node) => {
      const rendered = currentRenderedSkillPosition(node.record.skill_id, worldPoint.current);
      if (!rendered || !frustum.current.containsPoint(rendered)) return [];
      projectedPoint.current.copy(rendered).project(camera);
      if (projectedPoint.current.z < -1 || projectedPoint.current.z > 1) return [];
      const x = (projectedPoint.current.x * 0.5 + 0.5) * size.width;
      const y = (-projectedPoint.current.y * 0.5 + 0.5) * size.height;
      if (x < insetX || x > size.width - insetX || y < insetY || y > size.height - insetY) return [];
      const edge = Math.min((x - insetX) / Math.max(size.width - insetX * 2, 1), (size.width - insetX - x) / Math.max(size.width - insetX * 2, 1), (y - insetY) / Math.max(size.height - insetY * 2, 1), (size.height - insetY - y) / Math.max(size.height - insetY * 2, 1));
      const depth = 1 - (projectedPoint.current.z + 1) / 2;
      const isPrimary = primaryRelationIds.has(node.record.skill_id);
      const locked = lockedIds.has(node.record.skill_id) || node.visualState === "selected" || (relationMode && isPrimary);
      return [{ id: node.record.skill_id, anchor: [x, y] as const, width: labelWidth(node.record.skill), height: 30, score: (relationMode ? isPrimary ? 900 : 350 : 60) + edge * 22 + depth * 10 + Math.min(node.size, 0.5) * 10 + Math.min(node.labelPriority, 4), locked }];
    });
    const ranked = rankBrowsableLabelCandidates(candidates, previousIds.current, size.width, size.height);
    const lockedCount = ranked.filter((candidate) => candidate.locked).length;
    const relationBudget = relationMode ? Math.max(visibleLabelCount, primaryRelationIds.size + 1) : visibleLabelCount;
    const placements = resolveLabelPlacements(ranked, { width: size.width, height: size.height, maxVisible: relationBudget + lockedCount, protectedRects: protectValueCore ? [{ left: size.width * 0.5 - 250, top: size.height * 0.48, right: size.width * 0.5 + 48, bottom: size.height * 0.72 }] : [] });
    const visibleIds = ranked.flatMap((candidate) => placements.get(candidate.id)?.visible ? [candidate.id] : []);
    previousIds.current = new Set(visibleIds);
    const nextSignature = visibleIds.map((id) => `${id}:${placements.get(id)!.offset.join(",")}`).join("|");
    const host = gl.domElement.closest<HTMLElement>('[data-testid="skill-field-canvas"]');
    if (host) {
      host.dataset.dynamicLabelCount = String(visibleIds.length);
      host.dataset.dynamicLabelIds = visibleIds.join(",");
      host.dataset.labelRefreshCadenceHz = String(1000 / LABEL_REFRESH_MS);
      host.dataset.labelMode = relationMode ? "relation" : "browse";
    }
    if (nextSignature !== layoutSignature.current) {
      layoutSignature.current = nextSignature;
      setLabelState({ placements, visibleIds });
    }
  });

  const tooltipNode = tooltipSkillId ? nodeById.get(tooltipSkillId) : null;
  const tooltipDuplicatesLabel = tooltipSkillId !== null && labelState.visibleIds.includes(tooltipSkillId);
  return <>
    {labelState.visibleIds.flatMap((skillId) => {
      const node = nodeById.get(skillId);
      const placement = labelState.placements.get(skillId);
      if (!node || !placement?.visible) return [];
      return <RenderedHtmlAnchor key={skillId} skillId={skillId}><div style={{ transform: `translate(${placement.offset[0]}px, ${placement.offset[1]}px)` }}><button type="button" className={styles.nodeLabel} data-selected={node.visualState === "selected" ? "true" : undefined} data-hovered={skillId === hoveredSkillId ? "true" : undefined} data-testid="skill-field-label" onClick={() => onSelect(skillId)}><span>{node.record.skill}</span></button></div></RenderedHtmlAnchor>;
    })}
    {tooltipNode && !tooltipDuplicatesLabel && <RenderedHtmlAnchor skillId={tooltipNode.record.skill_id}><span className={styles.nodeTooltip} data-testid="skill-hover-tooltip" style={{ transform: "translate(-50%, -28px)" }}>{tooltipNode.record.skill}</span></RenderedHtmlAnchor>}
  </>;
}
