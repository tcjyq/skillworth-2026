import type { ChinaSkillWorthRecord, SkillRelationRecord } from "@/lib/api/types";
import { buildConstellationLayout, buildRankedLayout, selectRoleRankShifts } from "../layout";
import type { SceneMode } from "../state/scene-machine";
import type { SceneModel, SceneNode } from "../types";
import { skillColor } from "../scene/visual-system";

const STORY_SKILLS = new Set(["programming_python", "database_sql", "devops_git", "devops_docker", "programming_cpp"]);

export function buildSceneModel({
  mode,
  records,
  globalRecords,
  activeSkillId,
  selectedRelationId,
  relations,
  relationPrimaryLimit = 5,
}: {
  mode: SceneMode;
  records: ChinaSkillWorthRecord[];
  globalRecords: ChinaSkillWorthRecord[];
  activeSkillId: string | null;
  selectedRelationId: string | null;
  relations: SkillRelationRecord[];
  relationPrimaryLimit?: number;
}): SceneModel {
  const relationMode = mode === "RELATION_GLOBAL" || mode === "RELATION_ROLE";
  if (relationMode && activeSkillId) {
    return relationScene(globalRecords, records, activeSkillId, selectedRelationId, relations, relationPrimaryLimit);
  }
  const rankField = mode === "GLOBAL_DEMAND" ? "demand_rank" : "skillworth_rank";
  const layout = buildRankedLayout(records, rankField);
  const globalLayout = buildRankedLayout(globalRecords, "skillworth_rank");
  const cpp = records.find((record) => record.skill_id === "programming_cpp");
  const demandLayout = buildRankedLayout(globalRecords, "demand_rank");
  const cppShift = cpp?.demand_rank && cpp.skillworth_rank && (mode === "GLOBAL_VALUE" || mode === "GLOBAL_DEMAND") ? [{
    kind: mode === "GLOBAL_DEMAND" ? "cpp-demand" as const : "cpp-value" as const,
    skillId: cpp.skill_id,
    label: cpp.skill,
    start: mode === "GLOBAL_DEMAND" ? globalLayout[cpp.skill_id].position : demandLayout[cpp.skill_id].position,
    end: layout[cpp.skill_id].position,
    globalRank: mode === "GLOBAL_DEMAND" ? cpp.skillworth_rank : cpp.demand_rank,
    roleRank: mode === "GLOBAL_DEMAND" ? cpp.demand_rank : cpp.skillworth_rank,
    startLabel: mode === "GLOBAL_DEMAND" ? `学习性价比 #${cpp.skillworth_rank}` : `需求 #${cpp.demand_rank}`,
    endLabel: mode === "GLOBAL_DEMAND" ? `招聘需求 #${cpp.demand_rank}` : `学习性价比 #${cpp.skillworth_rank}`,
    summary: mode === "GLOBAL_VALUE" ? `#${cpp.demand_rank} → #${cpp.skillworth_rank}` : null,
  }] : [];
  const roleShifts = mode === "ROLE_VALUE"
    ? selectRoleRankShifts(globalRecords, records).map(({ skill, globalRank, roleRank }) => ({
        kind: "role" as const,
        skillId: skill.skill_id,
        label: skill.skill,
        start: globalLayout[skill.skill_id].position,
        end: layout[skill.skill_id].position,
        globalRank,
        roleRank,
        startLabel: `全局 #${globalRank}`,
        endLabel: `#${globalRank} → #${roleRank}`,
        summary: null,
      }))
    : cppShift;
  const roleShiftIds = new Set(roleShifts.map((shift) => shift.skillId));
  const nodes = records.map((record) => {
    const position = layout[record.skill_id];
    const topRanked = position.rank !== null && position.rank <= 5;
    const isCpp = record.skill_id === "programming_cpp";
    const visualState = position.observedOnly
      ? "observed-only"
      : mode === "GLOBAL_DEMAND"
        ? isCpp ? "selected" : "muted"
        : mode === "ROLE_VALUE"
          ? roleShiftIds.has(record.skill_id) ? "selected" : topRanked ? "highlighted" : "muted"
          : "default";
    const labelPriority = roleShiftIds.has(record.skill_id)
      ? 0
      : mode === "GLOBAL_DEMAND"
        ? topRanked ? 400 - (position.rank ?? 40) : 0
        : mode === "ROLE_VALUE"
          ? topRanked ? 500 - (position.rank ?? 40) : 0
          : topRanked || STORY_SKILLS.has(record.skill_id) ? 400 - (position.rank ?? 40) : 0;
    return {
      record,
      position: position.position,
      size: Math.max(position.size, 0.18),
      visualState,
      labelPriority,
      relation: null,
    } satisfies SceneNode;
  });
  return { nodes, lines: [], roleShifts, focus: [0, 0, 0] };
}

function relationScene(
  globalRecords: ChinaSkillWorthRecord[],
  scopedRecords: ChinaSkillWorthRecord[],
  activeSkillId: string,
  selectedRelationId: string | null,
  relations: SkillRelationRecord[],
  primaryLimit: number,
): SceneModel {
  const constellation = buildConstellationLayout(activeSkillId, relations, primaryLimit);
  const positions = new Map(constellation.nodes.map((node) => [node.skillId, node]));
  const scoped = new Map(scopedRecords.map((record) => [record.skill_id, record]));
  const globalLayout = buildRankedLayout(globalRecords, "skillworth_rank");
  const relationBySkill = new Map(relations.map((relation) => [relation.related_skill_id, relation]));
  const nodes = globalRecords.map((globalRecord) => {
    const record = scoped.get(globalRecord.skill_id) ?? globalRecord;
    const constellationNode = positions.get(record.skill_id);
    const isCore = record.skill_id === activeSkillId;
    const relation = relationBySkill.get(record.skill_id) ?? null;
    const isSelectedRelation = record.skill_id === selectedRelationId;
    const backgroundPosition = globalLayout[record.skill_id].position.map((value) => value * 1.25) as [number, number, number];
    return {
      record,
      position: constellationNode?.position ?? backgroundPosition,
      size: isCore ? 1.18 : Math.max(globalLayout[record.skill_id].size, 0.15),
      visualState: isCore || isSelectedRelation ? "selected" : constellationNode ? selectedRelationId ? "muted" : "highlighted" : "muted",
      labelPriority: isCore ? 1_000 : isSelectedRelation ? 900 : constellationNode?.ring === "primary" ? 600 : constellationNode?.ring === "secondary" ? 200 : 0,
      relation,
    } satisfies SceneNode;
  });
  const core = positions.get(activeSkillId)?.position ?? [0, 0, 0];
  const coreRecord = globalRecords.find((record) => record.skill_id === activeSkillId);
  const lines = constellation.nodes.flatMap((node) => {
    if (!node.relation) return [];
    return [{
      id: `${activeSkillId}:${node.skillId}`,
      start: core as [number, number, number],
      end: node.position,
      primary: node.ring === "primary",
      relation: node.relation,
      coreColor: skillColor(activeSkillId, coreRecord?.skill_category ?? "other").color,
      targetColor: skillColor(node.skillId, node.relation.related_skill_category).color,
    }];
  });
  return { nodes, lines, roleShifts: [], focus: [0, 0, 0] };
}
