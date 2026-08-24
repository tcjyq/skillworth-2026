export const ROLE_LABELS: Record<string, string> = {
  ai_engineer: "AI 工程师",
  analytics_engineer: "分析工程师（Analytics Engineer）",
  backend_engineer: "后端工程师",
  bi_analyst: "商业智能分析师（BI Analyst）",
  business_analyst: "业务分析师（Business Analyst）",
  cloud_engineer: "云工程师（Cloud Engineer）",
  data_analyst: "数据分析师",
  data_engineer: "数据工程师（Data Engineer）",
  data_scientist: "数据科学家",
  devops_engineer: "运维 / DevOps 工程师",
  frontend_engineer: "前端工程师",
  fullstack_engineer: "全栈工程师",
  ml_engineer: "机器学习工程师（Machine Learning Engineer）",
  mlops_engineer: "机器学习运维工程师（MLOps）",
  other: "其他技术岗位",
  product_manager: "产品经理",
  security_engineer: "安全工程师（Security Engineer）",
  software_engineer: "软件工程师",
  technical_product_manager: "技术产品经理（Technical Product Manager）",
};

const ROLE_SHORT_LABELS: Record<string, string> = {
  analytics_engineer: "分析工程师",
  bi_analyst: "商业智能分析师",
  business_analyst: "业务分析师",
  cloud_engineer: "云工程师",
  data_engineer: "数据工程师",
  ml_engineer: "机器学习工程师",
  security_engineer: "安全工程师",
  technical_product_manager: "技术产品经理",
};

export const TERM_HELP = {
  marketSignal: "市场信号（Market Signal）",
  synergy: "技能协同（Skill Synergy）",
  roleBreadth: "岗位广度（Role Breadth）",
  robustness: "排名稳健性（Ranking Robustness）",
  learningEffort: "学习投入（Learning Effort）",
} as const;

export function roleLabel(roleId: string | null, short = false) {
  if (!roleId) return "全部岗位";
  return short ? ROLE_SHORT_LABELS[roleId] ?? ROLE_LABELS[roleId] ?? roleId : ROLE_LABELS[roleId] ?? roleId;
}
