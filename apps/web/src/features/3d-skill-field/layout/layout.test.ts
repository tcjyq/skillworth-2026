import { describe, expect, it } from "vitest";
import {
  buildConstellationLayout,
  buildRankedLayout,
  nodeSize,
  roleEvidence,
  selectRoleRankShifts,
  selectConstellationRelations,
} from "./index";

const skills = [
  { skill_id: "python", skillworth_rank: 1, demand_rank: 2, job_coverage: 0.36 },
  { skill_id: "sql", skillworth_rank: 2, demand_rank: 1, job_coverage: 0.16 },
  { skill_id: "cpp", skillworth_rank: 35, demand_rank: 3, job_coverage: 0.09 },
  { skill_id: "observed", skillworth_rank: null, demand_rank: null, job_coverage: 0.04 },
];

describe("ranked radial layouts", () => {
  it("preserves SkillWorth rank radius order", () => {
    const layout = buildRankedLayout(skills, "skillworth_rank");
    expect(layout.python.radius).toBeLessThan(layout.sql.radius);
    expect(layout.sql.radius).toBeLessThan(layout.cpp.radius);
  });

  it("preserves demand rank radius order", () => {
    const layout = buildRankedLayout(skills, "demand_rank");
    expect(layout.sql.radius).toBeLessThan(layout.python.radius);
    expect(layout.python.radius).toBeLessThan(layout.cpp.radius);
  });

  it("uses the supplied role slice ranks without global fallback", () => {
    const roleSkills = skills.map((skill) => ({
      ...skill,
      skillworth_rank: skill.skill_id === "cpp" ? 1 : skill.skillworth_rank === 1 ? 3 : skill.skillworth_rank,
    }));
    const layout = buildRankedLayout(roleSkills, "skillworth_rank");
    expect(layout.cpp.radius).toBeLessThan(layout.python.radius);
  });

  it("keeps observed-only skills outside the ranking field without a fake rank", () => {
    const layout = buildRankedLayout(skills, "skillworth_rank");
    expect(layout.observed.rank).toBeNull();
    expect(layout.observed.observedOnly).toBe(true);
    expect(layout.observed.radius).toBeGreaterThan(layout.cpp.radius);
  });

  it("is deterministic for identical inputs", () => {
    expect(buildRankedLayout(skills, "skillworth_rank")).toEqual(
      buildRankedLayout(skills, "skillworth_rank"),
    );
  });

  it("never changes rank radius while spreading angular positions", () => {
    const layout = buildRankedLayout(skills, "skillworth_rank");
    expect(Math.hypot(...layout.python.position)).toBeCloseTo(layout.python.radius, 8);
    expect(Math.hypot(...layout.sql.position)).toBeCloseTo(layout.sql.radius, 8);
  });

  it("uses a square-root node-size transform", () => {
    expect(nodeSize(0.36) / nodeSize(0.09)).toBeCloseTo(2, 2);
  });
});

const relations = Array.from({ length: 24 }, (_, index) => ({
  core_skill_id: "python",
  related_skill_id: `skill-${index}`,
  related_skill: `Skill ${index}`,
  related_skill_category: "test",
  role_id: null,
  recency_window: "180d" as const,
  sample_size: 100,
  core_job_count: 40,
  related_job_count: 30,
  cooccurrence_count: index % 2 ? 12 : 10,
  core_conditional_coverage: 0.25,
  jaccard: 1 - Math.floor(index / 2) * 0.03,
  pmi: 0.4,
  evidence_status: "supported" as const,
}));

describe("relation constellation", () => {
  it("caps the primary ring at 7 and secondary ring at 12", () => {
    const selected = selectConstellationRelations(relations);
    expect(selected.primary).toHaveLength(7);
    expect(selected.secondary).toHaveLength(12);
  });

  it("sorts by Jaccard descending then cooccurrence descending", () => {
    const selected = selectConstellationRelations(relations);
    expect(selected.primary[0].related_skill_id).toBe("skill-1");
    expect(selected.primary[1].related_skill_id).toBe("skill-0");
  });

  it("keeps unsupported relations out of visible rings", () => {
    const selected = selectConstellationRelations([
      ...relations,
      { ...relations[0], related_skill_id: "weak", evidence_status: "small_sample_supported" as const, cooccurrence_count: 1 },
    ]);
    expect([...selected.primary, ...selected.secondary].some((item) => item.related_skill_id === "weak")).toBe(false);
  });

  it("builds deterministic, rank-preserving relation distances", () => {
    const first = buildConstellationLayout("python", relations);
    const second = buildConstellationLayout("python", relations);
    expect(first).toEqual(second);
    expect(first.nodes[1].distance).toBeLessThanOrEqual(first.nodes[2].distance);
  });
});

describe("role sample gates", () => {
  it("blocks deterministic role ranking at n <= 3", () => {
    expect(roleEvidence(3)).toEqual({ status: "insufficient", canRank: false, warning: "当前岗位样本不足，暂不足以形成稳定排序。" });
  });

  it("marks n=4..9 as a permanent small-sample warning", () => {
    expect(roleEvidence(7)).toEqual({ status: "small", canRank: true, warning: "小样本，仅供方向参考" });
  });
});

describe("role rank-shift presentation", () => {
  it("selects at most five largest real rank changes without hard-coded skills", () => {
    const roleSkills = skills.map((skill) => ({
      ...skill,
      skillworth_rank: skill.skill_id === "cpp" ? 1 : skill.skill_id === "python" ? 20 : skill.skillworth_rank,
    }));
    const shifts = selectRoleRankShifts(skills, roleSkills);
    expect(shifts).toHaveLength(2);
    expect(shifts[0]).toMatchObject({ skill: { skill_id: "cpp" }, globalRank: 35, roleRank: 1, rankShift: 34 });
    expect(shifts[1]).toMatchObject({ skill: { skill_id: "python" }, globalRank: 1, roleRank: 20, rankShift: 19 });
  });
});
