export type RankField = "skillworth_rank" | "demand_rank";

export type LayoutSkill = {
  skill_id: string;
  skillworth_rank: number | null;
  demand_rank: number | null;
  job_coverage: number;
};

export type RelationDatum = {
  core_skill_id: string;
  related_skill_id: string;
  related_skill: string;
  related_skill_category: string;
  role_id: string | null;
  recency_window: "90d" | "180d" | "365d" | "all_active";
  sample_size: number;
  core_job_count: number;
  related_job_count: number;
  cooccurrence_count: number;
  core_conditional_coverage: number;
  jaccard: number;
  pmi: number;
  evidence_status: "supported" | "small_sample_supported";
};

export type PositionedSkill = {
  skillId: string;
  position: [number, number, number];
  radius: number;
  size: number;
  rank: number | null;
  observedOnly: boolean;
};

export const LAYOUT_CONFIG = {
  ranked: { coreSafeRadius: 2.75, innerRadius: 3.7, outerRadius: 13.3, observedRadius: 15.2, gamma: 0.72 },
  relation: { primaryMin: 3.4, primaryMax: 6.2, secondaryMin: 7.6, secondaryMax: 10.8 },
  node: { coverageCap: 0.5, scale: 1.45, maxVisualSize: 0.9 },
} as const;

export function stableHash(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function directionFor(skillId: string): [number, number, number] {
  const hash = stableHash(skillId);
  const u = ((hash & 0xffff) + 0.5) / 65536;
  const v = (((hash >>> 16) & 0xffff) + 0.5) / 65536;
  const theta = Math.acos(1 - 2 * u);
  const phi = Math.PI * 2 * v + Math.PI * (3 - Math.sqrt(5)) * (hash % 233);
  return [
    Math.sin(theta) * Math.cos(phi),
    Math.cos(theta) * 0.72,
    Math.sin(theta) * Math.sin(phi),
  ];
}

export function nodeSize(jobCoverage: number) {
  return Math.min(
    Math.sqrt(Math.min(Math.max(jobCoverage, 0), LAYOUT_CONFIG.node.coverageCap)) * LAYOUT_CONFIG.node.scale,
    LAYOUT_CONFIG.node.maxVisualSize,
  );
}

export function buildRankedLayout<T extends LayoutSkill>(skills: T[], rankField: RankField) {
  const ranked = skills.filter((skill) => skill[rankField] !== null);
  const rankCount = Math.max(...ranked.map((skill) => skill[rankField] ?? 0), 1);
  return Object.fromEntries(
    skills.map((skill) => {
      const rank = skill[rankField];
      const observedOnly = rank === null;
      const normalizedRank = rank === null ? 1 : (rank - 1) / Math.max(rankCount - 1, 1);
      const radius = observedOnly
        ? LAYOUT_CONFIG.ranked.observedRadius + (stableHash(skill.skill_id) % 97) / 220
        : LAYOUT_CONFIG.ranked.innerRadius
          + normalizedRank ** LAYOUT_CONFIG.ranked.gamma
            * (LAYOUT_CONFIG.ranked.outerRadius - LAYOUT_CONFIG.ranked.innerRadius);
      const direction = directionFor(skill.skill_id);
      const position: [number, number, number] = direction.map((value) => value * radius) as [number, number, number];
      const actualRadius = Math.hypot(...position);
      const normalizedPosition: [number, number, number] = position.map(
        (value) => value * radius / actualRadius,
      ) as [number, number, number];
      return [skill.skill_id, {
        skillId: skill.skill_id,
        position: normalizedPosition,
        radius,
        size: nodeSize(skill.job_coverage),
        rank,
        observedOnly,
      } satisfies PositionedSkill];
    }),
  ) as Record<string, PositionedSkill>;
}

export function selectConstellationRelations(relations: RelationDatum[], primaryLimit = 5) {
  const sorted = relations
    .filter((relation) => relation.cooccurrence_count >= 3)
    .toSorted((left, right) => right.jaccard - left.jaccard
      || right.cooccurrence_count - left.cooccurrence_count
      || left.related_skill_id.localeCompare(right.related_skill_id));
  return { primary: sorted.slice(0, primaryLimit), secondary: sorted.slice(primaryLimit, primaryLimit + 12) };
}

export function buildConstellationLayout(coreSkillId: string, relations: RelationDatum[], primaryLimit = 5) {
  const { primary, secondary } = selectConstellationRelations(relations, primaryLimit);
  const buildRing = (items: RelationDatum[], min: number, max: number, ring: "primary" | "secondary") =>
    items.map((relation, index) => {
      const progress = items.length <= 1 ? 0 : index / (items.length - 1);
      const distance = min + progress * (max - min);
      const angularOffset = (stableHash(coreSkillId) % 360) * Math.PI / 180;
      const angle = angularOffset + index * Math.PI * 2 / Math.max(items.length, 1) + (ring === "secondary" ? Math.PI / Math.max(items.length, 1) : 0);
      const z = (((stableHash(relation.related_skill_id) >>> 7) % 2001) / 1000 - 1) * (ring === "primary" ? 1.15 : 1.7);
      const planarRadius = Math.sqrt(Math.max(distance ** 2 - z ** 2, 0));
      return {
        skillId: relation.related_skill_id,
        position: [Math.cos(angle) * planarRadius, Math.sin(angle) * planarRadius * 0.72, z] as [number, number, number],
        distance,
        ring,
        relation,
      };
    });
  return {
    nodes: [
      { skillId: coreSkillId, position: [0, 0, 0] as [number, number, number], distance: 0, ring: "center" as const, relation: null },
      ...buildRing(primary, LAYOUT_CONFIG.relation.primaryMin, LAYOUT_CONFIG.relation.primaryMax, "primary"),
      ...buildRing(secondary, LAYOUT_CONFIG.relation.secondaryMin, LAYOUT_CONFIG.relation.secondaryMax, "secondary"),
    ],
    primary,
    secondary,
  };
}

export function roleEvidence(sampleSize: number) {
  if (sampleSize <= 3) {
    return { status: "insufficient" as const, canRank: false, warning: "当前岗位样本不足，暂不足以形成稳定排序。" };
  }
  if (sampleSize < 10) {
    return { status: "small" as const, canRank: true, warning: "小样本，仅供方向参考" };
  }
  return { status: "normal" as const, canRank: true, warning: null };
}

export function selectRoleRankShifts<T extends LayoutSkill>(globalSkills: T[], roleSkills: T[], limit = 3) {
  const globalById = new Map(globalSkills.map((skill) => [skill.skill_id, skill]));
  return roleSkills
    .flatMap((roleSkill) => {
      const globalSkill = globalById.get(roleSkill.skill_id);
      if (!globalSkill?.skillworth_rank || !roleSkill.skillworth_rank) return [];
      return [{
        skill: roleSkill,
        globalRank: globalSkill.skillworth_rank,
        roleRank: roleSkill.skillworth_rank,
        rankShift: Math.abs(globalSkill.skillworth_rank - roleSkill.skillworth_rank),
      }];
    })
    .filter((item) => item.roleRank <= 5 && item.roleRank < item.globalRank)
    .toSorted((left, right) => right.rankShift - left.rankShift
      || left.roleRank - right.roleRank
      || left.skill.skill_id.localeCompare(right.skill.skill_id))
    .slice(0, limit);
}
