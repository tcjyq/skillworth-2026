"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { PageFrame } from "@/components/layout/page-frame";
import { ErrorState, LoadingState, LowConfidenceBanner } from "@/components/states/data-states";
import { useApi } from "@/hooks/use-api";
import { marketQuery } from "@/lib/api/client";
import type { MarketFilters, MarketSummary, RolesResponse, SourcesResponse, TrendResult } from "@/lib/api/types";
import { integer } from "@/lib/format";
import { MarketFiltersBar } from "./market-filters";
import { MarketMap } from "./market-map";
import { MarketRail } from "./market-rail";

export function MarketPulse() {
  const [filters, setFilters] = useState<MarketFilters>({});
  const [category, setCategory] = useState("");
  const deferredFilters = useDeferredValue(filters);
  const query = marketQuery(deferredFilters);
  const summary = useApi<MarketSummary>(`/market/summary${query}`);
  const trends = useApi<TrendResult>(`/market/trends${query}`);
  const roles = useApi<RolesResponse>("/roles");
  const sources = useApi<SourcesResponse>("/sources");
  const categories = useMemo(() => [...new Set(summary.data?.top_skills.map((item) => item.category) ?? [])], [summary.data]);
  const skills = useMemo(() => (summary.data?.top_skills ?? []).filter((item) => !category || item.category === category), [summary.data, category]);
  if (!summary.data && (summary.isLoading || trends.isLoading)) return <PageFrame title="技术技能市场" eyebrow="Market Pulse" description="从招聘需求、变化趋势和岗位规模观察技能市场。"><LoadingState /></PageFrame>;
  if (summary.error || trends.error) return <PageFrame title="技术技能市场" eyebrow="Market Pulse" description="从招聘需求、变化趋势和岗位规模观察技能市场。"><ErrorState message={summary.error?.message ?? trends.error?.message} retry={() => { void summary.mutate(); void trends.mutate(); }} /></PageFrame>;
  const metadata = summary.data!.metadata;
  const low = metadata.sample_size < 30 || metadata.source_count < 2;
  return <PageFrame title="技术技能市场" eyebrow="Market Pulse" description="把技术技能视为市场资产：需求是市场热度，变化是动量，岗位数是可观察规模。">
    <MarketFiltersBar filters={filters} category={category} roles={roles.data?.records ?? []} categories={categories} onFilters={setFilters} onCategory={setCategory} />
    {low && <div className="mb-4"><LowConfidenceBanner reasons={[`当前样本 ${metadata.sample_size} 条`, `数据来源 ${metadata.source_count} 个`, "低样本不会输出强趋势结论"]} /></div>}
    <div className="grid gap-4 lg:grid-cols-[minmax(0,8.5fr)_minmax(280px,3.5fr)]"><section className="terminal-panel overflow-hidden"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3"><div><h2 className="terminal-heading">技术技能市场地图</h2><p className="mt-0.5 text-[10px] text-[var(--text-muted)]">X 需求覆盖率 · Y 6M 变化 · 气泡 岗位数</p></div><span className="mono text-[10px] text-[var(--text-muted)]">LIVE DATA</span></div><MarketMap skills={skills} trends={(trends.data?.records ?? []).filter((item) => !category || item.category === category)} /></section><MarketRail trends={trends.data?.records ?? []} sources={sources.data?.records ?? []} /></div>
    <div className="mt-4 grid border border-[var(--border-subtle)] bg-[var(--surface)] sm:grid-cols-4"><Status label="当前样本" value={integer(metadata.sample_size)} /><Status label="来源数量" value={integer(metadata.source_count)} /><Status label="数据起始" value={metadata.published_from ?? "未知"} /><Status label="数据截止" value={metadata.published_to ?? "未知"} /></div>
  </PageFrame>;
}

function Status({ label, value }: { label: string; value: string }) { return <div className="border-b border-[var(--border-subtle)] px-4 py-3 last:border-0 sm:border-b-0 sm:border-r sm:last:border-r-0"><p className="label-caps">{label}</p><p className="mono mt-1 text-[13px]">{value}</p></div>; }
