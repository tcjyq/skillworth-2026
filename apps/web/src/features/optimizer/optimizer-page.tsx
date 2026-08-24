"use client";

import { useState } from "react";
import { Clock, Path } from "@phosphor-icons/react";
import { Metric } from "@/components/data/metric";
import { SkillPicker } from "@/components/forms/skill-picker";
import { PageFrame } from "@/components/layout/page-frame";
import { EmptyState, ErrorState, LoadingState, LowConfidenceBanner } from "@/components/states/data-states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi } from "@/hooks/use-api";
import { optimizePortfolio } from "@/lib/api/client";
import type { OptimizerResult, RolesResponse, SkillDemandResult } from "@/lib/api/types";
import { percent, roleName } from "@/lib/format";

export function OptimizerPage() {
  const skills = useApi<SkillDemandResult>("/skills");
  const roles = useApi<RolesResponse>("/roles");
  const [currentSkills, setCurrentSkills] = useState<string[]>([]);
  const [role, setRole] = useState("");
  const [hours, setHours] = useState(100);
  const [result, setResult] = useState<OptimizerResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const submit = async () => { setLoading(true); setError(null); try { setResult(await optimizePortfolio({ current_skills: currentSkills, target_role: role, hour_budget: hours, match_threshold: .7 })); } catch (value) { setError(value as Error); } finally { setLoading(false); } };
  if (!skills.data || !roles.data) return <PageFrame title="学习优化器" eyebrow="Learning Optimizer" description="按学习时间预算动态分配技能投资。">{skills.error || roles.error ? <ErrorState message={skills.error?.message ?? roles.error?.message} /> : <LoadingState />}</PageFrame>;
  return <PageFrame title="学习优化器" eyebrow="Learning Optimizer" description="每选择一项技能后重新计算剩余技能的边际收益，不是一次性 ROI 排序。"><div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]"><section className="terminal-panel p-4"><p className="label-caps">ALLOCATION INPUT</p><h2 className="mt-1 terminal-heading">配置学习投资</h2><div className="mt-5 space-y-4"><label className="grid gap-1.5"><span className="text-[11px] text-[var(--text-secondary)]">当前技能</span><SkillPicker skills={skills.data.records} value={currentSkills} onChange={setCurrentSkills} /></label><label className="grid gap-1.5"><span className="text-[11px] text-[var(--text-secondary)]">目标岗位</span><select value={role} onChange={(e) => setRole(e.target.value)} className="h-9 border border-[var(--border)] bg-transparent px-2 text-[12px] outline-none focus:border-[var(--accent)]"><option value="">请选择岗位</option>{roles.data.records.map((item) => <option key={item.role_id} value={item.role_id}>{roleName(item.role_id)}</option>)}</select></label><label className="grid gap-1.5"><span className="text-[11px] text-[var(--text-secondary)]">学习时间预算</span><div className="flex gap-2">{[100, 200, 300].map((value) => <button type="button" key={value} onClick={() => setHours(value)} className={`h-8 flex-1 border text-[11px] ${hours === value ? "border-[var(--accent)] bg-[#19160f] text-[var(--accent)]" : "border-[var(--border)] text-[var(--text-secondary)]"}`}>{value}h</button>)}</div><Input type="number" min={1} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="h-9 rounded-[3px]" /></label><p className="text-[10px] leading-[16px] text-[var(--text-muted)]">Learning Hours 是估算，不是课程时长、掌握承诺或就业承诺。</p><Button type="button" disabled={!role || hours <= 0 || loading} onClick={submit} className="h-9 w-full rounded-[3px] bg-[var(--accent)] text-[#090909] hover:bg-[#e4b75f]">{loading ? "正在优化…" : "生成学习分配"}</Button></div></section><OptimizerResultView result={result} error={error} /></div></PageFrame>;
}

function OptimizerResultView({ result, error }: { result: OptimizerResult | null; error: Error | null }) {
  if (error) return <ErrorState message={error.message} />;
  if (!result) return <EmptyState title="等待学习预算" description="选择目标岗位和时间预算后，后端将运行迭代式贪心边际增益优化。" />;
  if (result.status !== "ok" || !result.steps.length) return <EmptyState title="当前预算内没有可选技能" description={result.warnings.join("；") || "目标岗位缺少可用技能证据。"} />;
  return <section className="space-y-4"><div className="terminal-panel"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3"><div className="flex items-center gap-2"><Path size={16} className="text-[var(--accent)]" /><h2 className="terminal-heading">技能投资时间线</h2></div><span className="mono text-[10px] text-[var(--text-muted)]">ITERATIVE GREEDY</span></div><div className="grid grid-cols-2 md:grid-cols-4"><Metric label="时间预算" value={`${result.hour_budget.toFixed(0)}h`} /><Metric label="已分配" value={`${result.cumulative_hours.toFixed(0)}h`} /><Metric label="初始匹配度" value={percent(result.initial_fit)} /><Metric label="最终匹配度" value={percent(result.final_fit)} tone="positive" /></div></div>{result.warnings.length > 0 && <LowConfidenceBanner reasons={result.warnings.slice(0, 3)} />}<div className="terminal-panel overflow-hidden"><div className="relative p-4 sm:p-6"><div className="absolute bottom-6 left-[34px] top-6 w-px bg-[var(--border)] sm:left-[50px]" />{result.steps.map((step) => <article key={step.step} className="relative grid grid-cols-[38px_1fr] gap-3 pb-8 last:pb-0 sm:grid-cols-[52px_1fr]"><div className="mono z-10 flex h-7 w-7 items-center justify-center border border-[var(--accent)] bg-[#11100d] text-[10px] text-[var(--accent)]">{String(step.step).padStart(2, "0")}</div><div className="border border-[var(--border-subtle)] bg-[#0b0c0c]"><div className="flex flex-col gap-2 border-b border-[var(--border-subtle)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="text-[15px] font-semibold">{step.canonical_name}</h3><p className="mt-1 text-[10px] text-[var(--text-muted)]">{step.reason}</p></div><div className="flex items-center gap-2 text-[var(--accent)]"><Clock size={14} /><span className="mono text-[12px]">{step.estimated_hours.toFixed(0)}h</span></div></div><div className="grid grid-cols-2 sm:grid-cols-4"><Small label="边际增益" value={`+${percent(step.marginal_fit_gain)}`} /><Small label="累计匹配度" value={percent(step.cumulative_fit)} /><Small label="阈值覆盖" value={percent(step.threshold_coverage)} /><Small label="累计时间" value={`${step.cumulative_hours.toFixed(0)}h`} /></div></div></article>)}</div></div></section>;
}

function Small({ label, value }: { label: string; value: string }) { return <div className="border-r border-t border-[var(--border-subtle)] px-4 py-2.5 last:border-r-0 sm:border-t-0"><p className="label-caps">{label}</p><p className="mono mt-1 text-[11px]">{value}</p></div>; }
