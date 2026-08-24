import type { ChinaSkillWorthResponse } from "@/lib/api/types";

const recencyLabels: Record<string, string> = {
  "90d": "近 90 天",
  "180d": "近 180 天",
  "365d": "近 365 天",
  all_active: "全部在招样本",
};

const sourceRoleLabels: Record<string, string> = {
  china_supplementary: "Freehire 中国公开技术岗位补充样本",
  engineering_validation: "SkillWorth 公开合成演示样本",
};

export function recencyLabel(recencyWindow: string) {
  return recencyLabels[recencyWindow] ?? recencyWindow;
}

export function sourceRoleLabel(sourceRole: string) {
  return sourceRoleLabels[sourceRole] ?? sourceRole;
}

export function accessDateLabel(accessDate: string | null) {
  return accessDate ? `数据截止 ${accessDate}` : "数据日期暂不可用";
}

export function marketScopeLine(metadata: ChinaSkillWorthResponse) {
  return `样本：${metadata.job_count} 个岗位 · ${recencyLabel(metadata.recency_window)} · ${accessDateLabel(metadata.access_date)}`;
}

export function availabilityLabel(status: "available" | "unavailable") {
  return status === "available" ? "可用" : "暂不可用";
}
