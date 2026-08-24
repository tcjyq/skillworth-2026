import type { ChinaSkillWorthRecord, SkillRelationRecord } from "@/lib/api/types";

export type NodeVisualState = "default" | "highlighted" | "selected" | "muted" | "observed-only";

export type SceneNode = {
  record: ChinaSkillWorthRecord;
  position: [number, number, number];
  size: number;
  visualState: NodeVisualState;
  labelPriority: number;
  relation: SkillRelationRecord | null;
};

export type SceneLine = {
  id: string;
  start: [number, number, number];
  end: [number, number, number];
  primary: boolean;
  relation: SkillRelationRecord;
};

export type SceneRoleShift = {
  skillId: string;
  label: string;
  start: [number, number, number];
  end: [number, number, number];
  globalRank: number;
  roleRank: number;
};

export type SceneModel = {
  nodes: SceneNode[];
  lines: SceneLine[];
  roleShifts: SceneRoleShift[];
  focus: [number, number, number];
};
