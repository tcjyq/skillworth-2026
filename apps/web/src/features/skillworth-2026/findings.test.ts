import { describe, expect, it } from "vitest";
import type { ChinaSkillWorthRecord, ChinaSkillWorthResponse, RelatedSkills } from "@/lib/api/types";
import { deriveFinalFindings } from "./findings";

function record(skill: string, overrides: Partial<ChinaSkillWorthRecord>): ChinaSkillWorthRecord {
  return {
    skill_id: skill.toLowerCase().replaceAll(" ", "_"),
    skill,
    skill_type: "engineering_tool",
    skill_category: "other",
    skillworth_eligibility: "main",
    eligibility_reason: "specific",
    job_count: 20,
    job_coverage: 0.02,
    sample_size: 998,
    company_count: 10,
    company_coverage: 0.03,
    company_sample_size: 313,
    role_count: 2,
    role_breadth: 0.2,
    synergy_score: 0.4,
    market_signal: 20,
    learning_hours_min: 20,
    learning_hours_expected: 50,
    learning_hours_max: 100,
    skillworth_score: 12,
    skillworth_rank: 10,
    sensitivity_rank_min: 8,
    sensitivity_rank_max: 14,
    ranking_robustness: 70,
    robustness_level: "moderate",
    confidence: 50,
    confidence_level: "Medium",
    high_skillworth_candidate: true,
    market_theme: null,
    snapshot_id: "freehire_china_tech_2026_08",
    recency_window: "180d",
    role_id: null,
    window_status: "available",
    salary_signal_status: "unavailable",
    trend_signal_status: "unavailable",
    ...overrides,
  };
}

function response(records: ChinaSkillWorthRecord[], jobCount: number, roleId: string | null = null): ChinaSkillWorthResponse {
  return {
    market_scope: "china_open_tech_sample",
    source_role: "china_supplementary",
    snapshot: "freehire_china_tech_2026_08",
    access_date: "2026-08-10",
    recency_window: roleId ? "180d" : records[0]?.recency_window ?? "180d",
    job_count: jobCount,
    company_count: 313,
    skill_count: 134,
    source_count: 1,
    disclaimer: "sample only",
    salary_signal_status: "unavailable",
    trend_signal_status: "unavailable",
    market_themes: [],
    records: records.map((item) => ({ ...item, role_id: roleId })),
  };
}

function related(skillId: string, canonicalName: string, cooccurrence: number, jaccard: number, pmi: number): RelatedSkills {
  return {
    skill_id: skillId,
    methodology_version: "phase7_advanced_analytics_v1",
    config_version: "1.0.0",
    records: [{ skill_id: canonicalName.toLowerCase(), canonical_name: canonicalName, category: "other", cooccurrence_count: cooccurrence, jaccard, pmi, weight: jaccard }],
  };
}

describe("deriveFinalFindings", () => {
  it("derives the frozen V1 findings from API evidence without hardcoding ranks", () => {
    const global = response([
      record("Python", { job_count: 321, market_signal: 48.05, learning_hours_expected: 160, skillworth_score: 24.03, skillworth_rank: 1, sensitivity_rank_min: 1, sensitivity_rank_max: 2 }),
      record("SQL", { job_count: 169, market_signal: 36.32, learning_hours_expected: 100, skillworth_score: 22.35, skillworth_rank: 2, sensitivity_rank_min: 1, sensitivity_rank_max: 2 }),
      record("Git", { job_count: 40, market_signal: 21.68, learning_hours_expected: 55, skillworth_score: 16.13, skillworth_rank: 3, sensitivity_rank_min: 3, sensitivity_rank_max: 4 }),
      record("Docker", { job_count: 53, skillworth_rank: 4, sensitivity_rank_min: 3, sensitivity_rank_max: 4 }),
      record("C++", { job_count: 92, learning_hours_expected: 260, skillworth_rank: 35 }),
      record("Kubernetes", { job_count: 70, skillworth_rank: 18 }),
      record("Apache Spark", { job_count: 63, skillworth_rank: 19 }),
      record("Apache Kafka", { job_count: 27, skillworth_rank: 23 }),
      record("Terraform", { job_count: 25, skillworth_rank: 33 }),
      record("Tableau", { job_count: 44, skillworth_rank: 7, sensitivity_rank_min: 7, sensitivity_rank_max: 25 }),
      record("RAG", { job_count: 50, skillworth_rank: 8, sensitivity_rank_min: 6, sensitivity_rank_max: 29 }),
      record("Azure", { job_count: 60, skillworth_rank: 12, sensitivity_rank_min: 8, sensitivity_rank_max: 27 }),
    ], 998);
    const devops = response([
      record("Kubernetes", { skillworth_rank: 1 }),
      record("Terraform", { skillworth_rank: 3 }),
    ], 21, "devops_engineer");
    const data = response([
      record("Apache Spark", { skillworth_rank: 3 }),
      record("Apache Kafka", { skillworth_rank: 5 }),
    ], 38, "data_engineer");
    const allActive = response([record("Python", { recency_window: "all_active" })], 1140);

    const findings = deriveFinalFindings({
      global,
      devops,
      data,
      allActive,
      pythonRelated: related("programming_python", "SQL", 141, 0.343066, 0.856537),
      numpyRelated: related("data_analysis_numpy", "Pandas", 12, 0.666667, 4.125527),
      grafanaRelated: related("devops_grafana", "Prometheus", 11, 0.578947, 4.038516),
    });

    expect(findings?.frontier.map((item) => item.skill)).toEqual(["Python", "SQL", "Git"]);
    expect(findings?.cpp).toMatchObject({ demandRank: 3, skillworthRank: 35, learningHours: 260 });
    expect(findings?.roles).toEqual([
      { role: "DevOps", sampleSize: 21, skills: [{ skill: "Kubernetes", globalRank: 18, roleRank: 1 }, { skill: "Terraform", globalRank: 33, roleRank: 3 }] },
      { role: "Data Engineer", sampleSize: 38, skills: [{ skill: "Spark", globalRank: 19, roleRank: 3 }, { skill: "Kafka", globalRank: 23, roleRank: 5 }] },
    ]);
    expect(findings?.synergy).toMatchObject({ sampleSize: 1140, scale: { cooccurrence: 141 }, affinity: [{ jaccard: 0.666667 }, { jaccard: 0.578947 }] });
    expect(findings?.robustCore.map((item) => [item.skill, item.min, item.max])).toEqual([
      ["Python", 1, 2], ["SQL", 1, 2], ["Git", 3, 4], ["Docker", 3, 4], ["Tableau", 7, 25], ["RAG", 6, 29], ["Azure", 8, 27],
    ]);
  });
});
