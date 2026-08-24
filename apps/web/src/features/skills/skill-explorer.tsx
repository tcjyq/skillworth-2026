"use client";

import { useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { EChartsChart } from "@/components/charts/echarts-chart";
import { Metric } from "@/components/data/metric";
import { PageFrame } from "@/components/layout/page-frame";
import { EmptyState, ErrorState, LoadingState, LowConfidenceBanner } from "@/components/states/data-states";
import { Input } from "@/components/ui/input";
import { useApi } from "@/hooks/use-api";
import type { RelatedSkills, SkillDemandResult, SkillDetail } from "@/lib/api/types";
import { categoryName, integer, limitationName, money, percent, signedPercent, statusName } from "@/lib/format";

export function SkillExplorer() {
  const skills = useApi<SkillDemandResult>("/skills");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const sorted = useMemo(() => [...(skills.data?.records ?? [])].sort((a, b) => b.job_count - a.job_count || a.canonical_name.localeCompare(b.canonical_name)), [skills.data]);
  const effectiveSelected = selected || sorted[0]?.skill_id || "";
  const detail = useApi<SkillDetail>(effectiveSelected ? `/skills/${encodeURIComponent(effectiveSelected)}` : null);
  const related = useApi<RelatedSkills>(effectiveSelected ? `/skills/${encodeURIComponent(effectiveSelected)}/related` : null);
  const visible = sorted.filter((item) => item.canonical_name.toLowerCase().includes(query.toLowerCase()) || categoryName(item.category).includes(query));
  if (!skills.data && skills.isLoading) return <PageFrame title="技能探索" eyebrow="Skill Explorer" description="像查看金融资产一样查看技能的市场信号。"><LoadingState /></PageFrame>;
  if (skills.error) return <PageFrame title="技能探索" eyebrow="Skill Explorer" description="像查看金融资产一样查看技能的市场信号。"><ErrorState message={skills.error.message} retry={() => void skills.mutate()} /></PageFrame>;
  return <PageFrame title="技能探索" eyebrow="Skill Explorer" description="需求、趋势和薪资只描述招聘市场中的统计信号，不代表学习承诺或就业结果。">
    <div className="grid min-h-[650px] gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="terminal-panel overflow-hidden"><div className="border-b border-[var(--border-subtle)] p-3"><Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索技能或类别" className="h-8 rounded-[3px] text-[12px]" /></div><div className="scrollbar-thin max-h-[640px] overflow-y-auto">{visible.map((skill) => <button key={skill.skill_id} onClick={() => setSelected(skill.skill_id)} aria-current={effectiveSelected === skill.skill_id ? "true" : undefined} className={`grid w-full grid-cols-[1fr_auto] items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2.5 text-left transition-colors ${effectiveSelected === skill.skill_id ? "bg-[#19160f] text-[var(--accent)]" : "hover:bg-[var(--surface-hover)]"}`}><span><span className="block truncate text-[12px]">{skill.canonical_name}</span><span className="block text-[9px] text-[var(--text-muted)]">{categoryName(skill.category)}</span></span><span className="mono text-[10px] text-[var(--text-secondary)]">{percent(skill.job_coverage)}</span></button>)}</div></aside>
      <SkillAsset detail={detail.data} related={related.data} loading={detail.isLoading} error={detail.error} retry={() => void detail.mutate()} />
    </div>
  </PageFrame>;
}

function SkillAsset({ detail, related, loading, error, retry }: { detail?: SkillDetail; related?: RelatedSkills; loading: boolean; error: Error | undefined; retry: () => void }) {
  if (loading && !detail) return <LoadingState label="正在读取技能资产详情" />;
  if (error) return <ErrorState message={error.message} retry={retry} />;
  if (!detail) return <EmptyState title="请选择一个技能" description="从左侧技能列表打开资产详情。" />;
  const trend = detail.trend;
  const salary = detail.salary_distribution;
  const association = detail.adjusted_salary_association;
  const low = detail.demand.sample_size < 30 || trend?.conclusion_strength !== "qualified";
  const trendOption: EChartsOption = { grid: { left: 46, right: 18, top: 20, bottom: 32 }, tooltip: { trigger: "axis" }, xAxis: { type: "category", data: trend?.monthly.map((p) => p.month) ?? [] }, yAxis: { type: "value", axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } }, series: [{ type: "line", data: trend?.monthly.map((p) => p.skill_job_coverage) ?? [], showSymbol: true, areaStyle: { color: "rgba(216,165,74,.08)" }, lineStyle: { color: "#D8A54A" }, itemStyle: { color: "#D8A54A" } }] };
  return <section className="space-y-4"><div className="terminal-panel"><div className="flex items-start justify-between border-b border-[var(--border-subtle)] px-4 py-4"><div><p className="label-caps">{categoryName(detail.demand.category)}</p><h2 className="mt-1 text-[24px] font-semibold tracking-[-.03em]">{detail.demand.canonical_name}</h2><p className="mono mt-1 text-[10px] text-[var(--text-muted)]">{detail.demand.skill_id}</p></div><span className={`mono border px-2 py-1 text-[10px] ${low ? "border-[var(--warning)]/50 text-[var(--warning)]" : "border-[var(--positive)]/50 text-[var(--positive)]"}`}>{low ? "低置信度" : "证据充分"}</span></div><div className="grid grid-cols-2 md:grid-cols-5"><Metric label="岗位覆盖率" value={percent(detail.demand.job_coverage)} note={`${integer(detail.demand.job_count)} 个岗位`} /><Metric label="6M 变化" value={signedPercent(trend?.change_6m)} note={trend?.classification ?? "证据不足"} /><Metric label="薪资中位数" value={salary?.status === "unavailable" ? "不可用" : money(salary?.median)} note={salary?.status === "unavailable" ? "数据源无薪资" : salary ? `样本 ${salary.sample_size}` : "暂无数据"} /><Metric label="调整后薪资关联" value={association?.status === "unavailable" ? "不可用" : signedPercent(association?.percentage_approximation)} note={statusName(association?.status)} /><Metric label="来源数量" value={integer(detail.demand.source_count)} note={`总样本 ${detail.demand.sample_size}`} /></div></div>
    {low && <LowConfidenceBanner reasons={[`需求样本 ${detail.demand.sample_size}`, ...(trend?.limitations?.map(limitationName) ?? ["暂无可靠趋势"])]} />}
    <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]"><div className="terminal-panel"><div className="border-b border-[var(--border-subtle)] px-4 py-3"><h3 className="terminal-heading">历史需求覆盖率</h3></div>{trend?.monthly.length ? <EChartsChart option={trendOption} className="h-[300px] w-full" ariaLabel={`${detail.demand.canonical_name} 历史岗位覆盖率`} /> : <EmptyState title="暂无历史趋势" description="当前仓库没有足够的月度观察点。" />}</div><div className="terminal-panel"><div className="border-b border-[var(--border-subtle)] px-4 py-3"><h3 className="terminal-heading">相关技能</h3></div>{related?.records.length ? related.records.slice(0, 10).map((item) => <div key={item.skill_id} className="grid grid-cols-[1fr_auto] border-b border-[var(--border-subtle)] px-4 py-2.5 last:border-0"><span className="text-[12px]">{item.canonical_name}</span><span className="mono text-[10px] text-[var(--text-secondary)]">J {item.jaccard.toFixed(2)}</span></div>) : <p className="p-4 text-[11px] text-[var(--text-muted)]">当前没有满足支持度规则的关联边。</p>}</div></div>
    <div className="terminal-panel grid sm:grid-cols-3"><Metric label="薪资 P25" value={salary?.status === "unavailable" ? "不可用" : money(salary?.p25)} /><Metric label="薪资 P75" value={salary?.status === "unavailable" ? "不可用" : money(salary?.p75)} /><Metric label="薪资覆盖率" value={salary?.status === "unavailable" ? "不可用" : percent(salary?.salary_coverage)} note={salary?.status === "unavailable" ? "数据源不支持" : "仅描述样本关联"} /></div>
  </section>;
}
