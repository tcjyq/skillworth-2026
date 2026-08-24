import type { ChinaSkillWorthRecord } from "@/lib/api/types";

export type FrontierSelection = {
  showAllRobust: boolean;
  showModerate: boolean;
};

const byRank = (left: ChinaSkillWorthRecord, right: ChinaSkillWorthRecord) =>
  (left.skillworth_rank ?? Number.MAX_SAFE_INTEGER) - (right.skillworth_rank ?? Number.MAX_SAFE_INTEGER);

export function selectFrontierRecords(records: ChinaSkillWorthRecord[], selection: FrontierSelection) {
  const candidates = records.filter((record) => record.high_skillworth_candidate);
  const robust = candidates.filter((record) => record.robustness_level === "robust").sort(byRank);
  const visibleRobust = selection.showAllRobust ? robust : robust.slice(0, 12);
  if (!selection.showModerate) return visibleRobust;
  const moderate = candidates.filter((record) => record.robustness_level === "moderate").sort(byRank).slice(0, 12);
  return [...visibleRobust, ...moderate].sort(byRank);
}

export function isSkillInTheme(record: ChinaSkillWorthRecord, theme: string | null) {
  if (!theme) return true;
  return (record.market_theme ?? "").split(";").map((value) => value.trim()).includes(theme);
}
