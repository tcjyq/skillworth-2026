export type MarketFilters = {
  role_id?: string;
  city_code?: string;
  experience_band?: string;
  education_band?: string;
  source_id?: string[];
  published_from?: string;
  published_to?: string;
};

export type AnalyticsMetadata = {
  metric_name: string;
  methodology_version: string;
  data_version: string;
  filters: MarketFilters;
  sample_size: number;
  source_count: number;
  published_from: string | null;
  published_to: string | null;
};

export type SkillDemand = {
  skill_id: string;
  canonical_name: string;
  category: string;
  job_count: number;
  job_coverage: number | null;
  source_count: number;
  sample_size: number;
};

export type PlatformDemand = {
  skill_id: string;
  canonical_name: string;
  category: string;
  pooled_coverage: number | null;
  platform_balanced_coverage: number | null;
  platform_breakdown: Array<{ source_id: string; job_count: number; job_coverage: number | null; sample_size: number }>;
  source_count: number;
  sample_size: number;
};

export type SalaryDistribution = {
  skill_id: string;
  canonical_name: string;
  category: string;
  median: number | null;
  p25: number | null;
  p75: number | null;
  sample_size: number;
  salary_coverage: number | null;
  status: "available" | "unavailable";
};

export type TrendRecord = {
  skill_id: string;
  canonical_name: string;
  category: string;
  monthly: Array<{ month: string; job_count: number; sample_size: number; skill_job_coverage: number; rolling_mean: number | null }>;
  change_3m: number | null;
  change_6m: number | null;
  trend_slope: number | null;
  volatility: number | null;
  observed_month_count: number;
  qualified_month_count: number;
  sample_size: number;
  classification: string | null;
  conclusion_strength: "qualified" | "insufficient" | "inconclusive";
  limitations: string[];
};

export type SalaryAssociation = {
  skill_id: string;
  canonical_name: string;
  category: string;
  coefficient: number | null;
  percentage_approximation: number | null;
  confidence_interval_low: number | null;
  confidence_interval_high: number | null;
  percentage_confidence_interval_low: number | null;
  percentage_confidence_interval_high: number | null;
  p_value: number | null;
  sample_size: number;
  skill_job_count: number;
  non_skill_job_count: number;
  status: string;
  diagnostics: Record<string, unknown>;
};

export type MarketSummary = {
  metadata: AnalyticsMetadata;
  top_skills: SkillDemand[];
  platform_balanced_top_skills: PlatformDemand[];
  salary_by_skill: SalaryDistribution[];
};

export type SkillDemandResult = { metadata: AnalyticsMetadata; records: SkillDemand[] };
export type TrendResult = { metadata: AnalyticsMetadata; config_version: string; records: TrendRecord[] };
export type SkillDetail = { demand: SkillDemand; salary_distribution: SalaryDistribution | null; adjusted_salary_association: SalaryAssociation | null; trend: TrendRecord | null };
export type RelatedSkill = { skill_id: string; canonical_name: string; category: string; cooccurrence_count: number; jaccard: number; pmi: number; weight: number };
export type RelatedSkills = { skill_id: string; records: RelatedSkill[]; methodology_version: string; config_version: string };

export type SkillWorthEligibility = "main" | "secondary" | "excluded";
export type RankingRobustness = "robust" | "moderate" | "sensitive";

export type ChinaSkillWorthRecord = {
  skill_id: string;
  skill: string;
  skill_type: string;
  skill_category: string;
  skillworth_eligibility: SkillWorthEligibility;
  eligibility_reason: string;
  job_count: number;
  job_coverage: number;
  sample_size: number;
  company_count: number;
  company_coverage: number;
  company_sample_size: number;
  role_count: number;
  role_breadth: number;
  synergy_score: number;
  market_signal: number;
  learning_hours_min: number;
  learning_hours_expected: number;
  learning_hours_max: number;
  skillworth_score: number;
  skillworth_rank: number | null;
  sensitivity_rank_min: number | null;
  sensitivity_rank_max: number | null;
  ranking_robustness: number;
  robustness_level: RankingRobustness;
  confidence: number;
  confidence_level: "High" | "Medium" | "Low";
  high_skillworth_candidate: boolean;
  market_theme: string | null;
  snapshot_id: string;
  recency_window: string;
  role_id: string | null;
  window_status: string;
  salary_signal_status: "available" | "unavailable";
  trend_signal_status: "available" | "unavailable";
};

export type ChinaMarketTheme = {
  market_theme: string;
  job_count: number;
  job_coverage: number;
  company_count: number;
  company_coverage: number;
  role_count: number;
  role_breadth: number;
  snapshot_id: string;
  recency_window: string;
};

export type ChinaSkillWorthResponse = {
  market_scope: string;
  source_role: string;
  snapshot: string;
  recency_window: string;
  job_count: number;
  company_count: number;
  skill_count: number;
  source_count: number;
  disclaimer: string;
  salary_signal_status: "available" | "unavailable";
  trend_signal_status: "available" | "unavailable";
  market_themes: ChinaMarketTheme[];
  records: ChinaSkillWorthRecord[];
};

export type Role = { role_id: string; canonical_job_count: number; company_count: number; city_count: number; salary_mid_median: number | null };
export type RolesResponse = { records: Role[] };
export type RoleDetail = { role: Role; skill_demand: SkillDemandResult };
export type Source = { source_id: string; source_job_count: number; canonical_job_count: number; first_observed_at: string | null; last_observed_at: string | null };
export type SourcesResponse = { records: Source[] };
export type DataQuality = { raw_row_count: number; silver_row_count: number; missing_rate: number; missing_rate_by_field: Record<string, number>; salary_parse_rate: number; role_parse_rate: number; city_parse_rate: number; invalid_record_rate: number; skill_extraction_f1?: number | null; dedup_rate?: number | null };

export type Confidence = {
  confidence_score: number;
  confidence_level: "High" | "Medium" | "Low";
  confidence_components: Record<string, { component_score: number | null; raw_value: number | null; weight: number; effective_weight: number; applicable: boolean; available: boolean; explanation: string }>;
  warnings: Array<{ code: string; component: string; message: string }>;
  methodology_version: string;
  config_version: string;
};

export type OpportunityRequest = { current_skills: string[]; target_role: string; city?: string; experience?: string; match_threshold: number };
export type OpportunityCandidate = { skill_id: string; canonical_name: string; category: string; new_average_fit: number; new_threshold_coverage: number; average_fit_gain: number; threshold_coverage_gain: number; jobs_crossing_threshold: number; sample_size: number; confidence: Confidence };
export type OpportunityResult = { status: string; request: OpportunityRequest; current_average_fit: number | null; current_threshold_coverage: number | null; target_job_count: number; sample_size: number; jobs_without_extracted_skills: number; candidates: OpportunityCandidate[]; confidence: Confidence; methodology_version: string };

export type OptimizerRequest = { current_skills: string[]; target_role: string; hour_budget: number; city?: string; experience?: string; match_threshold?: number; learning_hours_overrides?: Record<string, number> };
export type OptimizerStep = { step: number; skill_id: string; canonical_name: string; category: string; estimated_hours: number; cumulative_hours: number; marginal_fit_gain: number; cumulative_fit: number; threshold_coverage: number; reason: string; learning_hours: { learning_hours_min: number; learning_hours_expected: number; learning_hours_max: number; effective_expected_hours: number; is_user_override: boolean; is_estimate: boolean; disclaimer: string } };
export type OptimizerResult = { status: string; strategy: string; beam_search_used: boolean; hour_budget: number; cumulative_hours: number; remaining_hours: number; initial_fit: number | null; final_fit: number | null; final_threshold_coverage: number | null; steps: OptimizerStep[]; warnings: string[]; methodology_version: string; config_version: string };

export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message); }
}
