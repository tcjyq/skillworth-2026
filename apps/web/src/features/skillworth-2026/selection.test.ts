import { describe, expect, it } from "vitest";
import type { ChinaSkillWorthRecord } from "@/lib/api/types";
import { isSkillInTheme, selectFrontierRecords } from "./selection";

const record = (overrides: Partial<ChinaSkillWorthRecord>): ChinaSkillWorthRecord => ({
  skill_id: "skill",
  skill: "Skill",
  skill_type: "engineering_tool",
  skill_category: "other",
  skillworth_eligibility: "main",
  eligibility_reason: "specific",
  job_count: 20,
  job_coverage: 0.1,
  sample_size: 200,
  company_count: 10,
  company_coverage: 0.1,
  company_sample_size: 100,
  role_count: 2,
  role_breadth: 0.2,
  synergy_score: 0.4,
  market_signal: 20,
  learning_hours_min: 20,
  learning_hours_expected: 50,
  learning_hours_max: 100,
  skillworth_score: 16,
  skillworth_rank: 1,
  sensitivity_rank_min: 1,
  sensitivity_rank_max: 2,
  ranking_robustness: 80,
  robustness_level: "robust",
  confidence: 50,
  confidence_level: "Medium",
  high_skillworth_candidate: true,
  market_theme: null,
  snapshot_id: "snapshot",
  recency_window: "180d",
  role_id: null,
  window_status: "available",
  salary_signal_status: "unavailable",
  trend_signal_status: "unavailable",
  ...overrides,
});

describe("selectFrontierRecords", () => {
  it("defaults to the first twelve robust high-SkillWorth candidates", () => {
    const records = Array.from({ length: 15 }, (_, index) => record({ skill_id: `r${index}`, skillworth_rank: index + 1 }));
    records.push(record({ skill_id: "moderate", skillworth_rank: 3, robustness_level: "moderate" }));
    records.push(record({ skill_id: "not-candidate", skillworth_rank: 2, high_skillworth_candidate: false }));

    expect(selectFrontierRecords(records, { showAllRobust: false, showModerate: false }).map((item) => item.skill_id)).toEqual(
      Array.from({ length: 12 }, (_, index) => `r${index}`),
    );
  });

  it("adds moderate candidates only after the secondary toggle is enabled", () => {
    const records = [
      record({ skill_id: "robust", skillworth_rank: 1 }),
      record({ skill_id: "moderate", skillworth_rank: 2, robustness_level: "moderate" }),
      record({ skill_id: "sensitive", skillworth_rank: 3, robustness_level: "sensitive" }),
    ];

    expect(selectFrontierRecords(records, { showAllRobust: true, showModerate: true }).map((item) => item.skill_id)).toEqual(["robust", "moderate"]);
  });
});

describe("isSkillInTheme", () => {
  it("matches a skill assigned to multiple semicolon-separated market themes", () => {
    expect(isSkillInTheme(record({ market_theme: "AI; Machine Learning" }), "Machine Learning")).toBe(true);
    expect(isSkillInTheme(record({ market_theme: "AI; Machine Learning" }), "Optimization")).toBe(false);
  });
});
