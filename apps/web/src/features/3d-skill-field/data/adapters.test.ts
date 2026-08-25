import { describe, expect, it } from "vitest";
import type { ChinaSkillWorthRecord, SkillRelationRecord } from "@/lib/api/types";
import { buildSceneModel } from "./adapters";

function record(skill_id: string, skill: string, skillworth_rank: number | null, demand_rank: number | null, job_coverage = 0.1): ChinaSkillWorthRecord {
  return {
    skill_id, skill, skillworth_rank, demand_rank, job_coverage,
    skill_type: "technology", skill_category: skill_id.includes("sql") ? "database" : "devops",
    skillworth_eligibility: skillworth_rank ? "main" : "secondary", eligibility_reason: "test",
    job_count: 10, sample_size: 100, company_count: 8, company_coverage: 0.08, company_sample_size: 80,
    role_count: 2, role_breadth: 0.2, synergy_score: 0.2, market_signal: 20,
    learning_hours_min: 20, learning_hours_expected: 40, learning_hours_max: 60, skillworth_score: 10,
    sensitivity_rank_min: skillworth_rank, sensitivity_rank_max: skillworth_rank, ranking_robustness: 1,
    robustness_level: "robust", confidence: 80, confidence_level: "High", high_skillworth_candidate: false,
    market_theme: null, snapshot_id: "demo", recency_window: "180d", role_id: null, window_status: "active",
    salary_signal_status: "unavailable", trend_signal_status: "unavailable",
  };
}

const globalRecords = [
  record("programming_python", "Python", 1, 2, 0.36),
  record("database_sql", "SQL", 2, 1, 0.2),
  record("devops_git", "Git", 3, 7),
  record("devops_docker", "Docker", 4, 6),
  record("devops_kubernetes", "Kubernetes", 18, 12),
  record("programming_cpp", "C++", 35, 3, 0.09),
  record("devops_terraform", "Terraform", 33, 25),
];

describe("signature ranking moments", () => {
  it("keeps C++ #3 in demand mode while muting other nodes", () => {
    const model = buildSceneModel({ mode: "GLOBAL_DEMAND", records: globalRecords, globalRecords, activeSkillId: null, selectedRelationId: null, relations: [] });
    const cpp = model.nodes.find((node) => node.record.skill_id === "programming_cpp");
    expect(cpp?.record.demand_rank).toBe(3);
    expect(cpp?.record.skillworth_rank).toBe(35);
    expect(cpp?.visualState).toBe("selected");
    expect(cpp?.labelPriority).toBe(0);
    expect(model.nodes.filter((node) => node.record.skill_id !== "programming_cpp").every((node) => node.visualState === "muted")).toBe(true);
    expect(model.roleShifts[0]).toMatchObject({ kind: "cpp-demand", startLabel: "学习性价比 #35", endLabel: "招聘需求 #3" });
  });

  it("returns C++ to its real #35 endpoint with the demand #3 ghost", () => {
    const model = buildSceneModel({ mode: "GLOBAL_VALUE", records: globalRecords, globalRecords, activeSkillId: null, selectedRelationId: null, relations: [] });
    expect(model.nodes.find((node) => node.record.skill_id === "programming_cpp")?.record.skillworth_rank).toBe(35);
    expect(model.roleShifts[0]).toMatchObject({ kind: "cpp-value", startLabel: "需求 #3", endLabel: "学习性价比 #35", summary: "#3 → #35" });
  });
});

describe("role emphasis", () => {
  it("keeps role Top 5 readable, mutes other skills, and highlights at most three real changes", () => {
    const roleRecords = globalRecords.map((item) => ({
      ...item,
      role_id: "devops_engineer",
      skillworth_rank: item.skill_id === "devops_kubernetes" ? 1
        : item.skill_id === "devops_docker" ? 2
          : item.skill_id === "devops_terraform" ? 3
            : item.skill_id === "devops_git" ? 4
            : item.skill_id === "programming_python" ? 10
              : (item.skillworth_rank ?? 20) + 20,
    }));
    const model = buildSceneModel({ mode: "ROLE_VALUE", records: roleRecords, globalRecords, activeSkillId: null, selectedRelationId: null, relations: [] });
    expect(model.roleShifts).toHaveLength(3);
    expect(model.roleShifts).toEqual(expect.arrayContaining([
      expect.objectContaining({ skillId: "devops_kubernetes", globalRank: 18, roleRank: 1 }),
      expect.objectContaining({ skillId: "devops_terraform", globalRank: 33, roleRank: 3 }),
    ]));
    expect(model.nodes.find((node) => node.record.skill_id === "devops_kubernetes")?.visualState).toBe("selected");
    expect(model.nodes.find((node) => node.record.skill_id === "devops_kubernetes")?.labelPriority).toBe(0);
    expect(model.nodes.find((node) => node.record.skill_id === "devops_terraform")?.labelPriority).toBe(0);
    expect(model.nodes.find((node) => node.record.skill_id === "devops_git")?.labelPriority).toBeGreaterThan(0);
    expect(model.nodes.find((node) => node.record.skill_id === "database_sql")?.visualState).toBe("muted");
  });
});

describe("selected relation focus", () => {
  it("keeps only the core and selected relation at full emphasis", () => {
    const related = ["database_sql", "devops_git", "devops_docker", "devops_kubernetes", "devops_terraform"];
    const relations: SkillRelationRecord[] = related.map((related_skill_id, index) => ({
      core_skill_id: "programming_python", related_skill_id,
      related_skill: globalRecords.find((item) => item.skill_id === related_skill_id)!.skill,
      related_skill_category: "devops", role_id: null, recency_window: "180d", sample_size: 998,
      core_job_count: 300, related_job_count: 160, cooccurrence_count: 128 - index * 10,
      core_conditional_coverage: 0.4, jaccard: 0.4 - index * 0.04, pmi: 0.2, evidence_status: "supported",
    }));
    const model = buildSceneModel({ mode: "RELATION_GLOBAL", records: globalRecords, globalRecords, activeSkillId: "programming_python", selectedRelationId: "database_sql", relations });
    expect(model.nodes.find((node) => node.record.skill_id === "programming_python")?.visualState).toBe("selected");
    expect(model.nodes.find((node) => node.record.skill_id === "database_sql")?.visualState).toBe("selected");
    expect(model.nodes.find((node) => node.record.skill_id === "devops_git")?.visualState).toBe("muted");
  });
});
