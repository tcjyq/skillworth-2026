import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FinalFindings } from "@/features/skillworth-2026/findings";
import type { ChinaSkillWorthRecord, ChinaSkillWorthResponse } from "@/lib/api/types";
import { ExploreMode } from "./explore-mode";
import { RoleFirst } from "./role-first";
import { CppMoment } from "./story-visuals";

const api = vi.hoisted(() => ({
  responses: new Map<string, Record<string, unknown>>(),
  retry: vi.fn(),
}));

vi.mock("@/hooks/use-api", () => ({
  useApi: (path: string) => api.responses.get(path) ?? { isLoading: true, mutate: api.retry },
}));

const globalPath = "/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d";
const rolePath = `${globalPath}&role=backend_engineer`;
const explorePath = "/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d";

function response(overrides: Partial<ChinaSkillWorthResponse> = {}): ChinaSkillWorthResponse {
  return {
    market_scope: "demo_dataset",
    source_role: "engineering_validation",
    snapshot: "demo-2026-08-08",
    access_date: "2026-08-08",
    recency_window: "180d",
    job_count: 8,
    company_count: 7,
    skill_count: 3,
    source_count: 1,
    disclaimer: "仅用于工程验证的合成数据。",
    salary_signal_status: "unavailable",
    trend_signal_status: "unavailable",
    market_themes: [],
    records: [],
    ...overrides,
  };
}

function record(): ChinaSkillWorthRecord {
  return {
    skill_id: "programming_python",
    skill: "Python",
    skill_type: "programming_language",
    skill_category: "programming",
    skillworth_eligibility: "main",
    eligibility_reason: "fixture",
    job_count: 2,
    job_coverage: 0.25,
    sample_size: 8,
    company_count: 2,
    company_coverage: 0.28,
    company_sample_size: 7,
    role_count: 2,
    role_breadth: 0.5,
    synergy_score: 0,
    market_signal: 40,
    learning_hours_min: 20,
    learning_hours_expected: 40,
    learning_hours_max: 60,
    skillworth_score: 30,
    skillworth_rank: 1,
    sensitivity_rank_min: 1,
    sensitivity_rank_max: 2,
    ranking_robustness: 80,
    robustness_level: "robust",
    confidence: 40,
    confidence_level: "Low",
    high_skillworth_candidate: true,
    market_theme: null,
    snapshot_id: "demo-2026-08-08",
    recency_window: "180d",
    role_id: null,
    window_status: "available",
    salary_signal_status: "unavailable",
    trend_signal_status: "unavailable",
  };
}

beforeEach(() => {
  api.responses.clear();
  api.retry.mockReset();
  api.responses.set("/roles", { data: { records: [] }, mutate: api.retry });
});

afterEach(cleanup);

describe("Visual V2 data integrity", () => {
  it("does not show fake success counts while Explore is loading", () => {
    render(<ExploreMode />);

    expect(screen.getByRole("heading", { name: "探索技能" })).toBeInTheDocument();
    expect(screen.getByText("正在读取完整技能集合…")).toBeInTheDocument();
    expect(screen.queryByText("134", { exact: true })).not.toBeInTheDocument();
  });

  it("distinguishes Explore error from empty and exposes retry", () => {
    api.responses.set(explorePath, { error: new Error("unavailable"), data: response({ skill_count: 134, records: [record()] }), mutate: api.retry });
    const { rerender } = render(<ExploreMode />);

    expect(screen.getByText("当前数据暂时无法读取")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
    expect(screen.queryByText(/项可搜索技能/)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "探索 134 项技能" })).not.toBeInTheDocument();

    api.responses.set(explorePath, { data: response({ job_count: 0, company_count: 0, skill_count: 0 }), mutate: api.retry });
    rerender(<ExploreMode />);
    expect(screen.getByText("当前筛选条件下没有可展示的技能")).toBeInTheDocument();
    expect(screen.queryByText("当前数据暂时无法读取")).not.toBeInTheDocument();
  });

  it("uses response skill_count instead of a component literal", () => {
    api.responses.set(explorePath, { data: response({ skill_count: 7, records: [record()] }), mutate: api.retry });

    render(<ExploreMode />);

    expect(screen.getByRole("heading", { name: "探索 7 项技能" })).toBeInTheDocument();
    expect(screen.queryByText("探索 134 项技能")).not.toBeInTheDocument();
  });

  it("uses the current role slice sample size", () => {
    api.responses.set(globalPath, { data: response(), mutate: api.retry });
    api.responses.set(rolePath, { data: response({ job_count: 23, records: [{ ...record(), role_id: "backend_engineer" }] }), mutate: api.retry });

    render(<RoleFirst />);

    expect(screen.getByText("23 个岗位")).toBeInTheDocument();
    expect(screen.queryByText("0 个岗位")).not.toBeInTheDocument();
  });

  it("uses response metadata for the story source line", () => {
    const findings = {
      frontier: [],
      cpp: { demandRank: 3, skillworthRank: 35, learningHours: 260, jobCount: 92, companyCount: 48 },
      roles: [],
      synergy: { sampleSize: 0, scale: { pair: "Python–SQL", cooccurrence: 0, jaccard: 0, pmi: 0 }, affinity: [] },
      robustCore: [],
    } satisfies FinalFindings;

    render(<CppMoment findings={findings} metadata={response({ job_count: 17, access_date: "2026-09-03" })} />);

    expect(screen.getByText("样本：17 个岗位 · 近 180 天 · 数据截止 2026-09-03")).toBeInTheDocument();
    expect(screen.queryByText(/998 个岗位/)).not.toBeInTheDocument();
  });
});
