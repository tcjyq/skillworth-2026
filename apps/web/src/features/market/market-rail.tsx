import type { Source, TrendRecord } from "@/lib/api/types";
import { integer, signedPercent } from "@/lib/format";

export function MarketRail({ trends, sources }: { trends: TrendRecord[]; sources: Source[] }) {
  const qualified = trends.filter((item) => item.conclusion_strength === "qualified" && item.change_6m != null);
  const rising = [...qualified].filter((item) => (item.change_6m ?? 0) > 0).sort((a, b) => (b.change_6m ?? 0) - (a.change_6m ?? 0)).slice(0, 5);
  const declining = [...qualified].filter((item) => (item.change_6m ?? 0) < 0).sort((a, b) => (a.change_6m ?? 0) - (b.change_6m ?? 0)).slice(0, 5);
  return <aside className="space-y-3">
    <section className="terminal-panel p-4"><p className="label-caps">市场状态</p><div className="mt-4 flex items-end justify-between"><span className="text-[22px] font-semibold">{qualified.length ? "可评估" : "证据不足"}</span><span className="mono text-[11px] text-[var(--text-secondary)]">{qualified.length} SKILLS</span></div><p className="mt-2 text-[11px] leading-[17px] text-[var(--text-secondary)]">仅在月度样本满足方法规则时给出上升或下降判断。</p></section>
    <MoverList title="上升技能" items={rising} positive />
    <MoverList title="下降技能" items={declining} />
    <section className="terminal-panel"><div className="border-b border-[var(--border-subtle)] px-4 py-3"><h2 className="terminal-heading">数据源账本</h2></div>{sources.length ? sources.map((source) => <div key={source.source_id} className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-2.5 last:border-0"><div><p className="text-[12px]">{source.source_id}</p><p className="mono text-[10px] text-[var(--text-muted)]">{integer(source.source_job_count)} 条来源记录</p></div><span className="mono text-[10px] text-[var(--text-secondary)]">已导入</span></div>) : <p className="p-4 text-[11px] text-[var(--text-muted)]">暂无来源记录</p>}</section>
  </aside>;
}

function MoverList({ title, items, positive = false }: { title: string; items: TrendRecord[]; positive?: boolean }) {
  return <section className="terminal-panel"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3"><h2 className="terminal-heading">{title}</h2><span className="label-caps">6M</span></div>{items.length ? items.map((item, index) => <div key={item.skill_id} className="grid grid-cols-[20px_1fr_auto] items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-2.5 last:border-0"><span className="mono text-[10px] text-[var(--text-muted)]">{String(index + 1).padStart(2, "0")}</span><span className="truncate text-[12px]">{item.canonical_name}</span><span className={`mono text-[11px] ${positive ? "text-[var(--positive)]" : "text-[var(--negative)]"}`}>{signedPercent(item.change_6m)}</span></div>) : <p className="px-4 py-5 text-[11px] text-[var(--text-muted)]">当前没有满足样本规则的技能</p>}</section>;
}
