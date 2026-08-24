"use client";

import { useMemo, useState } from "react";
import { ArrowRight, Lightning } from "@phosphor-icons/react";
import { ConfidencePanel } from "@/components/data/confidence-panel";
import { Metric } from "@/components/data/metric";
import { PageFrame } from "@/components/layout/page-frame";
import { EmptyState, ErrorState, LoadingState, LowConfidenceBanner } from "@/components/states/data-states";
import { useApi } from "@/hooks/use-api";
import { analyzePortfolio } from "@/lib/api/client";
import type { OpportunityResult, RolesResponse, SkillDemandResult } from "@/lib/api/types";
import { integer, percent, roleName } from "@/lib/format";
import { PortfolioForm, type PortfolioFields } from "./portfolio-form";

const initial: PortfolioFields = { current_skills: [], target_role: "", city: "", experience: "", match_threshold: .7 };

export function PortfolioPage() {
  const skills = useApi<SkillDemandResult>("/skills");
  const roles = useApi<RolesResponse>("/roles");
  const [fields, setFields] = useState(initial);
  const [result, setResult] = useState<OpportunityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const submit = async () => { setLoading(true); setError(null); try { setResult(await analyzePortfolio({ current_skills: fields.current_skills, target_role: fields.target_role, city: fields.city || undefined, experience: fields.experience || undefined, match_threshold: fields.match_threshold })); } catch (value) { setError(value as Error); } finally { setLoading(false); } };
  if (!skills.data || !roles.data) return <PageFrame title="我的技能组合" eyebrow="My Skill Portfolio" description="找出对你当前技能组合最有杠杆的下一项技能。">{skills.error || roles.error ? <ErrorState message={skills.error?.message ?? roles.error?.message} /> : <LoadingState />}</PageFrame>;
  return <PageFrame title="我的技能组合" eyebrow="My Skill Portfolio" description="衡量的是招聘岗位技能覆盖，不是录取概率、就业概率或 Offer Probability。"><div className="grid items-start gap-4 xl:grid-cols-[360px_minmax(0,1fr)]"><PortfolioForm value={fields} onChange={setFields} skills={skills.data.records} roles={roles.data.records} loading={loading} onSubmit={submit} /><PortfolioResult result={result} error={error} role={fields.target_role} /></div></PageFrame>;
}

function PortfolioResult({ result, error, role }: { result: OpportunityResult | null; error: Error | null; role: string }) {
  const candidates = useMemo(() => [...(result?.candidates ?? [])].sort((a, b) => b.average_fit_gain - a.average_fit_gain), [result]);
  if (error) return <ErrorState message={error.message} />;
  if (!result) return <EmptyState title="等待你的技能组合" description="选择目标岗位和已有技能后，系统会从后端重新计算每项候选技能的边际覆盖增益。" />;
  if (result.status !== "ok" || !candidates.length) return <EmptyState title={result.status === "no_target_jobs" ? "目标岗位暂无样本" : "当前岗位没有可用技能证据"} description="请调整岗位、城市或经验筛选。" />;
  const best = candidates[0];
  return <section className="space-y-4"><div className="terminal-panel overflow-hidden border-l-2 border-l-[var(--accent)]"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-5 py-4"><div className="flex items-center gap-2 text-[var(--accent)]"><Lightning size={17} weight="fill" /><span className="label-caps !text-[var(--accent)]">HIGHEST-LEVERAGE NEXT SKILL</span></div><span className="mono text-[10px] text-[var(--text-muted)]">{roleName(role)}</span></div><div className="px-5 py-6"><p className="text-[32px] font-semibold tracking-[-.04em]">{best.canonical_name}</p><p className="mt-2 max-w-2xl text-[12px] text-[var(--text-secondary)]">在当前目标岗位样本中，加入这项技能后，技能匹配度的边际增益最高。</p></div><div className="grid grid-cols-2 border-t border-[var(--border-subtle)] md:grid-cols-4"><Metric label="平均匹配度增益" value={percent(best.average_fit_gain)} /><Metric label="阈值覆盖增益" value={percent(best.threshold_coverage_gain)} /><Metric label="跨越阈值岗位" value={integer(best.jobs_crossing_threshold)} /><Metric label="数据置信度" value={`${best.confidence.confidence_score.toFixed(0)}/100`} tone={best.confidence.confidence_level === "Low" ? "warning" : undefined} /></div></div>{result.confidence.confidence_level !== "High" && <LowConfidenceBanner reasons={result.confidence.warnings.map((item) => item.message).slice(0, 3)} />}<div className="grid gap-4 lg:grid-cols-[1fr_310px]"><section className="terminal-panel"><div className="border-b border-[var(--border-subtle)] px-4 py-3"><h3 className="terminal-heading">候选技能机会序列</h3></div>{candidates.slice(0, 12).map((item, index) => <div key={item.skill_id} className="grid grid-cols-[28px_1fr_auto_auto] items-center gap-3 border-b border-[var(--border-subtle)] px-4 py-3 last:border-0"><span className="mono text-[10px] text-[var(--text-muted)]">{String(index + 1).padStart(2, "0")}</span><span className="text-[12px]">{item.canonical_name}</span><span className="mono text-[11px] text-[var(--positive)]">+{percent(item.average_fit_gain)}</span><ArrowRight size={12} className="text-[var(--text-muted)]" /></div>)}</section><ConfidencePanel confidence={result.confidence} /></div></section>;
}
