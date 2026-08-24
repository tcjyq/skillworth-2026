"use client";

import { useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { ArrowsOut, Crosshair, MagnifyingGlassMinus, MagnifyingGlassPlus } from "@phosphor-icons/react";
import { EChartsChart } from "@/components/charts/echarts-chart";
import { PageFrame } from "@/components/layout/page-frame";
import { EmptyState, ErrorState, LoadingState, LowConfidenceBanner } from "@/components/states/data-states";
import { useApi } from "@/hooks/use-api";
import type { RelatedSkills, SkillDemandResult } from "@/lib/api/types";
import { categoryName, integer } from "@/lib/format";

export function SkillGraph() {
  const skills = useApi<SkillDemandResult>("/skills");
  const [focus, setFocus] = useState("");
  const effectiveFocus = focus || [...(skills.data?.records ?? [])].sort((a, b) => b.job_count - a.job_count)[0]?.skill_id || "";
  const related = useApi<RelatedSkills>(effectiveFocus ? `/skills/${encodeURIComponent(effectiveFocus)}/related` : null);
  const focusSkill = skills.data?.records.find((item) => item.skill_id === effectiveFocus);
  if (!skills.data && skills.isLoading) return <PageFrame title="技能图谱" eyebrow="Skill Graph" description="探索技能共同出现的结构。"><LoadingState /></PageFrame>;
  if (skills.error) return <PageFrame title="技能图谱" eyebrow="Skill Graph" description="探索技能共同出现的结构。"><ErrorState message={skills.error.message} retry={() => void skills.mutate()} /></PageFrame>;
  return <PageFrame title="技能图谱" eyebrow="Skill Graph" description="节点和连接来自真实职位技能共现；支持缩放、平移、悬停、聚焦和侧边检查。" actions={<label className="flex items-center gap-2"><span className="label-caps">聚焦技能</span><select value={focus} onChange={(e) => setFocus(e.target.value)} className="h-8 min-w-[190px] border border-[var(--border)] bg-transparent px-2 text-[11px] outline-none focus:border-[var(--accent)]">{[...(skills.data?.records ?? [])].sort((a,b) => b.job_count-a.job_count).map((item) => <option key={item.skill_id} value={item.skill_id}>{item.canonical_name}</option>)}</select></label>}>
    {focusSkill && focusSkill.source_count < 2 && <div className="mb-4"><LowConfidenceBanner reasons={[`当前技能来源 ${focusSkill.source_count} 个`, `岗位关系样本 ${focusSkill.sample_size}`]} /></div>}
    <div className="grid min-h-[650px] border border-[var(--border-subtle)] bg-[var(--surface)] lg:grid-cols-[minmax(0,1fr)_340px]"><GraphCanvas focus={focusSkill} related={related.data} loading={related.isLoading} error={related.error} retry={() => void related.mutate()} onFocus={setFocus} /><GraphInspector focus={focusSkill} related={related.data} /></div>
  </PageFrame>;
}

function GraphCanvas({ focus, related, loading, error, retry, onFocus }: { focus?: SkillDemandResult["records"][number]; related?: RelatedSkills; loading: boolean; error: Error | undefined; retry: () => void; onFocus: (id: string) => void }) {
  const option: EChartsOption = useMemo(() => {
    if (!focus) return {};
    const nodes = [{ id: focus.skill_id, name: focus.canonical_name, value: focus.job_count, symbolSize: 58, category: 0, itemStyle: { color: "#D8A54A" }, label: { show: true } }, ...(related?.records ?? []).map((item) => ({ id: item.skill_id, name: item.canonical_name, value: item.cooccurrence_count, symbolSize: Math.max(18, Math.min(42, 16 + item.weight * 18)), category: 1, itemStyle: { color: "#71857A" }, label: { show: true } }))];
    const links = (related?.records ?? []).map((item) => ({ source: focus.skill_id, target: item.skill_id, value: item.weight, lineStyle: { width: Math.max(1, item.weight * 3), opacity: .65 } }));
    return { animationDurationUpdate: 220, tooltip: { formatter: (p: unknown) => { const item = p as { dataType: string; data: { name?: string; value?: number } }; return item.dataType === "node" ? `<b>${item.data.name}</b><br/>支持度 ${item.data.value ?? "—"}` : "技能共现关系"; } }, toolbox: { right: 16, top: 12, feature: { restore: {} }, iconStyle: { borderColor: "#888E8B" }, emphasis: { iconStyle: { borderColor: "#D8A54A" } } }, series: [{ type: "graph", layout: "force", roam: true, draggable: true, data: nodes, links, force: { repulsion: 260, edgeLength: [100, 180], gravity: .08 }, emphasis: { focus: "adjacency", lineStyle: { width: 3, opacity: 1 } }, label: { position: "right", color: "#BFC3C0", fontSize: 10 }, lineStyle: { color: "#39413D", curveness: .08 } }] };
  }, [focus, related]);
  if (loading && !related) return <div className="p-4"><LoadingState label="正在构建共现关系" /></div>;
  if (error) return <div className="p-4"><ErrorState message={error.message} retry={retry} /></div>;
  if (!focus) return <div className="p-4"><EmptyState title="请选择聚焦技能" /></div>;
  if (!related?.records.length) return <div className="relative min-h-[650px]"><div className="absolute left-4 top-4 flex gap-1 text-[var(--text-muted)]"><MagnifyingGlassPlus size={16} /><MagnifyingGlassMinus size={16} /><ArrowsOut size={16} /></div><div className="absolute inset-x-8 top-1/2 -translate-y-1/2"><EmptyState bare title="暂无满足支持度的共现连接" description="图谱不会为当前技能伪造关系边。请切换聚焦技能。" /></div></div>;
  return <EChartsChart option={option} className="h-[650px] w-full" ariaLabel={`${focus.canonical_name} 技能共现网络，可缩放和平移`} onClick={(params) => { if (params.dataType === "node" && typeof (params.data as { id?: unknown })?.id === "string") onFocus((params.data as { id: string }).id); }} />;
}

function GraphInspector({ focus, related }: { focus?: SkillDemandResult["records"][number]; related?: RelatedSkills }) {
  return <aside className="border-t border-[var(--border-subtle)] lg:border-l lg:border-t-0"><div className="border-b border-[var(--border-subtle)] px-4 py-4"><div className="flex items-center gap-2 text-[var(--accent)]"><Crosshair size={15} /><span className="label-caps !text-[var(--accent)]">FOCUS INSPECTOR</span></div><h2 className="mt-2 text-[20px] font-semibold">{focus?.canonical_name ?? "未选择"}</h2><p className="mt-1 text-[11px] text-[var(--text-secondary)]">{focus ? categoryName(focus.category) : "—"}</p></div>{focus && <div className="grid grid-cols-2 border-b border-[var(--border-subtle)]"><Item label="岗位数" value={integer(focus.job_count)} /><Item label="来源数" value={integer(focus.source_count)} /></div>}<div className="px-4 py-3"><h3 className="terminal-heading">最强连接</h3></div>{related?.records.slice(0, 8).map((item) => <div key={item.skill_id} className="border-t border-[var(--border-subtle)] px-4 py-2.5"><div className="flex justify-between"><span className="text-[12px]">{item.canonical_name}</span><span className="mono text-[10px] text-[var(--accent)]">{item.weight.toFixed(2)}</span></div><p className="mono mt-1 text-[9px] text-[var(--text-muted)]">JACCARD {item.jaccard.toFixed(2)} · PMI {item.pmi.toFixed(2)}</p></div>)}</aside>;
}

function Item({ label, value }: { label: string; value: string }) { return <div className="border-r border-[var(--border-subtle)] p-4 last:border-0"><p className="label-caps">{label}</p><p className="mono mt-2 text-[16px]">{value}</p></div>; }
