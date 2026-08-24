"use client";

import { useState } from "react";
import type { EChartsOption } from "echarts";
import { EChartsChart } from "@/components/charts/echarts-chart";
import { Metric } from "@/components/data/metric";
import { PageFrame } from "@/components/layout/page-frame";
import { EmptyState, ErrorState, LoadingState, LowConfidenceBanner } from "@/components/states/data-states";
import { useApi } from "@/hooks/use-api";
import type { RoleDetail, RolesResponse } from "@/lib/api/types";
import { integer, money, roleName } from "@/lib/format";

export function RoleIntelligence() {
  const roles = useApi<RolesResponse>("/roles");
  const [selected, setSelected] = useState("");
  const effectiveSelected = selected || [...(roles.data?.records ?? [])].sort((a, b) => b.canonical_job_count - a.canonical_job_count)[0]?.role_id || "";
  const detail = useApi<RoleDetail>(effectiveSelected ? `/roles/${encodeURIComponent(effectiveSelected)}` : null);
  if (!roles.data && roles.isLoading) return <PageFrame title="岗位洞察" eyebrow="Role Intelligence" description="查看目标岗位的薪资和技能结构。"><LoadingState /></PageFrame>;
  if (roles.error) return <PageFrame title="岗位洞察" eyebrow="Role Intelligence" description="查看目标岗位的薪资和技能结构。"><ErrorState message={roles.error.message} retry={() => void roles.mutate()} /></PageFrame>;
  return <PageFrame title="岗位洞察" eyebrow="Role Intelligence" description="从岗位样本中识别核心技能结构，为学习目标提供市场上下文。"><div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]"><aside className="terminal-panel overflow-hidden">{roles.data?.records.map((role) => <button key={role.role_id} onClick={() => setSelected(role.role_id)} aria-current={effectiveSelected === role.role_id ? "true" : undefined} className={`flex w-full items-center justify-between border-b border-[var(--border-subtle)] px-3 py-3 text-left text-[12px] transition-colors ${effectiveSelected === role.role_id ? "bg-[#19160f] text-[var(--accent)]" : "hover:bg-[var(--surface-hover)]"}`}><span>{roleName(role.role_id)}</span><span className="mono text-[10px] text-[var(--text-secondary)]">{role.canonical_job_count}</span></button>)}</aside><RoleCanvas detail={detail.data} loading={detail.isLoading} error={detail.error} retry={() => void detail.mutate()} /></div></PageFrame>;
}

function RoleCanvas({ detail, loading, error, retry }: { detail?: RoleDetail; loading: boolean; error: Error | undefined; retry: () => void }) {
  if (loading && !detail) return <LoadingState label="正在读取岗位数据" />;
  if (error) return <ErrorState message={error.message} retry={retry} />;
  if (!detail) return <EmptyState title="请选择目标岗位" />;
  const top = detail.skill_demand.records.filter((item) => item.job_count > 0).sort((a, b) => b.job_count - a.job_count).slice(0, 12);
  const option: EChartsOption = { grid: { left: 100, right: 28, top: 18, bottom: 28 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" } }, xAxis: { type: "value", axisLabel: { formatter: "{value}%" } }, yAxis: { type: "category", inverse: true, data: top.map((item) => item.canonical_name) }, series: [{ type: "bar", data: top.map((item) => (item.job_coverage ?? 0) * 100), barWidth: 8, itemStyle: { color: "#D8A54A" } }] };
  const low = detail.role.canonical_job_count < 30;
  return <section className="space-y-4"><div className="terminal-panel"><div className="border-b border-[var(--border-subtle)] px-4 py-4"><p className="label-caps">目标岗位</p><h2 className="mt-1 text-[23px] font-semibold">{roleName(detail.role.role_id)}</h2></div><div className="grid grid-cols-2 md:grid-cols-4"><Metric label="标准岗位数" value={integer(detail.role.canonical_job_count)} /><Metric label="公司数" value={integer(detail.role.company_count)} /><Metric label="城市数" value={integer(detail.role.city_count)} /><Metric label="月薪中位数" value={money(detail.role.salary_mid_median)} /></div></div>{low && <LowConfidenceBanner reasons={[`当前岗位样本 ${detail.role.canonical_job_count} 条`, "低样本不输出强趋势结论"]} />}<div className="terminal-panel"><div className="border-b border-[var(--border-subtle)] px-4 py-3"><h3 className="terminal-heading">核心技能需求</h3></div>{top.length ? <EChartsChart option={option} className="h-[380px] w-full" ariaLabel={`${roleName(detail.role.role_id)} 核心技能岗位覆盖率`} /> : <EmptyState title="该岗位暂无技能关系" />}</div><UnavailableDimensions /></section>;
}

function UnavailableDimensions() { return <section className="border-y border-[var(--border-subtle)] py-3"><div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="terminal-heading">待补充分析维度</h3><p className="mt-1 text-[11px] text-[var(--text-muted)]">当前 API 暂未提供，界面未使用代理值。</p></div><div className="flex gap-2 text-[10px] text-[var(--text-secondary)]"><span className="border border-[var(--border-subtle)] px-2 py-1">经验分布</span><span className="border border-[var(--border-subtle)] px-2 py-1">城市分布</span><span className="border border-[var(--border-subtle)] px-2 py-1">来源结构</span></div></div></section>; }
