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
  const nodes = records.map((record) => {
    const position = layout[record.skill_id];
    const defaultLabel = (position.rank !== null && position.rank <= 4) || STORY_SKILLS.has(record.skill_id);
    return {
      record,
      position: position.position,
      size: Math.max(position.size, 0.18),
      visualState: position.observedOnly ? "observed-only" : "default",
      labelPriority: defaultLabel ? 50 - (position.rank ?? 40) : 0,
      relation: null,
    } satisfies SceneNode;
  });
  const cpp = records.find((record) => record.skill_id === "programming_cpp");
  const demandLayout = buildRankedLayout(globalRecords, "demand_rank");
  const cppShift = cpp?.demand_rank && cpp.skillworth_rank && (mode === "GLOBAL_VALUE" || mode === "GLOBAL_DEMAND") ? [{
    skillId: cpp.skill_id,
    label: cpp.skill,
    start: mode === "GLOBAL_DEMAND" ? globalLayout[cpp.skill_id].position : demandLayout[cpp.skill_id].position,
    end: layout[cpp.skill_id].position,
    globalRank: mode === "GLOBAL_DEMAND" ? cpp.skillworth_rank : cpp.demand_rank,
    roleRank: mode === "GLOBAL_DEMAND" ? cpp.demand_rank : cpp.skillworth_rank,
  }] : [];
  const roleShifts = mode === "ROLE_VALUE"
    ? selectRoleRankShifts(globalRecords, records).map(({ skill, globalRank, roleRank }) => ({
        skillId: skill.skill_id,
        label: skill.skill,
        start: globalLayout[skill.skill_id].position,
        end: layout[skill.skill_id].position,
        globalRank,
        roleRank,
      }))
    : cppShift;
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
      visualState: isCore || isSelectedRelation ? "selected" : constellationNode ? "highlighted" : "muted",
      labelPriority: isCore ? 100 : constellationNode?.ring === "primary" ? 80 : constellationNode?.ring === "secondary" ? 35 : 0,
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
