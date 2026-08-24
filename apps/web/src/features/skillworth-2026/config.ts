export const RECENCY_OPTIONS = [
  { value: "90d", label: "90 天" },
  { value: "180d", label: "180 天" },
  { value: "365d", label: "365 天" },
  { value: "all_active", label: "全部在招" },
] as const;

export type RecencyWindow = (typeof RECENCY_OPTIONS)[number]["value"];

export const ROLE_OPTIONS = [
  { value: "all", label: "全部岗位" },
  { value: "ai_engineer", label: "AI 工程" },
  { value: "data_scientist", label: "数据科学" },
  { value: "data_analyst", label: "数据分析" },
  { value: "data_engineer", label: "数据工程" },
  { value: "backend_engineer", label: "后端" },
  { value: "frontend_engineer", label: "前端" },
  { value: "devops_engineer", label: "云与 DevOps" },
  { value: "security_engineer", label: "安全" },
] as const;

export const SKILL_TYPE_COLORS: Record<string, string> = {
  programming_language: "#c8dc62",
  database: "#8eb9a2",
  framework_library: "#d7aa72",
  cloud_platform: "#8ba6c7",
  devops_tool: "#a79ab7",
  data_tool: "#72aaa5",
  ai_ml_technology: "#d19a8a",
  frontend_technology: "#be9b73",
  backend_technology: "#9bac7d",
};

export const fallbackSkillColor = "#89908b";

export const SOURCE_ROLE_LABELS: Record<string, string> = {
  china_supplementary: "Single Supplementary Source",
  supplementary_market: "Supplementary Market Source",
  engineering_validation: "Engineering Validation Source",
  core_market_candidate: "Core Market Candidate",
  core_market: "Core Market Source",
};
