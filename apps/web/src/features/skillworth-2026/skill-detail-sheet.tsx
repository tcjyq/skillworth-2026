"use client";

import { useEffect, useMemo, useState } from "react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useApi } from "@/hooks/use-api";
import { apiRequest } from "@/lib/api/client";
import type { ChinaSkillWorthRecord, ChinaSkillWorthResponse, RelatedSkills } from "@/lib/api/types";
import { RECENCY_OPTIONS, ROLE_OPTIONS, type RecencyWindow } from "./config";
import { percentValue, rankRange, scoreValue, titleCase } from "./format";

type RoleEvidence = { role: string; label: string; jobCount: number };
const roleEvidenceCache = new Map<string, RoleEvidence[]>();

export function SkillDetailSheet({ record, recencyWindow, rankingScale, onClose }: { record: ChinaSkillWorthRecord | null; recencyWindow: RecencyWindow; rankingScale: number; onClose: () => void }) {
  const [mobile, setMobile] = useState(false);
  const [roleResult, setRoleResult] = useState<{ key: string; values: RoleEvidence[] }>({ key: "", values: [] });
  const related = useApi<RelatedSkills>(record ? `/skills/${encodeURIComponent(record.skill_id)}/related` : null);

  const roleCacheKey = record ? `${record.skill_id}:${recencyWindow}` : "";
  const roles = useMemo(() => roleEvidenceCache.get(roleCacheKey) ?? (roleResult.key === roleCacheKey ? roleResult.values : []), [roleCacheKey, roleResult]);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 639px)");
    const update = () => setMobile(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    let active = true;
    if (!record) return;
    const cacheKey = `${record.skill_id}:${recencyWindow}`;
    if (roleEvidenceCache.has(cacheKey)) return;
    const controller = new AbortController();
    void Promise.all(ROLE_OPTIONS.slice(1).map(async (role) => {
      const params = new URLSearchParams({ eligibility: "all", robustness: "all", role: role.value, recency_window: recencyWindow });
      const result = await apiRequest<ChinaSkillWorthResponse>(`/market/china-skillworth?${params}`, { signal: controller.signal });
      const found = result.records.find((item) => item.skill_id === record.skill_id);
      return { role: role.value, label: role.label, jobCount: found?.job_count ?? 0 };
    })).then((values) => {
      const next = values.filter((item) => item.jobCount > 0).sort((a, b) => b.jobCount - a.jobCount);
      roleEvidenceCache.set(cacheKey, next);
      if (active) setRoleResult({ key: cacheKey, values: next });
    }).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (active) setRoleResult({ key: cacheKey, values: [] });
    });
    return () => { active = false; controller.abort(); };
  }, [record, recencyWindow]);

  const maxRoleJobs = useMemo(() => Math.max(...roles.map((item) => item.jobCount), 1), [roles]);

  return (
    <Sheet open={Boolean(record)} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side={mobile ? "bottom" : "right"} className="skill-inspector w-full min-w-0 max-w-[100vw] max-h-[92dvh] gap-0 overflow-y-auto overflow-x-hidden border-[rgba(206,219,204,.18)] bg-[rgba(14,19,16,.94)] p-0 sm:!w-[430px] sm:!max-w-[430px]">
        {record && <>
          <div className="sheet-handle sm:hidden" aria-hidden="true" />
          <SheetHeader className="border-b border-[var(--sw-line)] px-6 pb-7 pt-8 text-left sm:px-7 sm:pt-9">
            <p className="font-mono text-[10px] uppercase tracking-[.14em] text-[var(--sw-accent)]">#{String(record.skillworth_rank ?? "—").padStart(2, "0")} · {titleCase(record.skill_type)}</p>
            <SheetTitle className="mt-3 text-[clamp(2rem,8vw,2.65rem)] font-semibold leading-none tracking-[-.038em] text-[var(--sw-text)]">{record.skill}</SheetTitle>
            <SheetDescription className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-[var(--sw-text-secondary)]">
              <span>{titleCase(record.robustness_level)} ranking</span><span aria-hidden="true">·</span><span>{record.learning_hours_min}–{record.learning_hours_max}h 学习估算</span>
            </SheetDescription>
          </SheetHeader>

          <div className="divide-y divide-[var(--sw-line)]">
            <section className="drawer-core-metrics grid grid-cols-[1.22fr_1fr_.88fr] px-6 py-6 sm:px-7" aria-label="核心指标">
              <DrawerMetric label="SKILLWORTH" value={scoreValue(record.skillworth_score)} priority="primary" />
              <DrawerMetric label="市场信号" value={scoreValue(record.market_signal)} priority="secondary" />
              <DrawerMetric label="学习投入" value={`${record.learning_hours_expected}h`} priority="tertiary" />
            </section>

            <section className="px-6 py-6 sm:px-7">
              <h3 className="drawer-label">市场证据</h3>
              <div className="mt-5 space-y-4">
                <EvidenceRail label="岗位覆盖" value={record.job_coverage} display={`${record.job_count} · ${percentValue(record.job_coverage)}`} />
                <EvidenceRail label="公司覆盖" value={record.company_coverage} display={`${record.company_count} · ${percentValue(record.company_coverage)}`} />
                <EvidenceRail label="岗位方向广度" value={record.role_breadth} display={`${record.role_count} 个方向`} />
                <EvidenceRail label="技能协同信号" value={record.synergy_score} display={scoreValue(record.synergy_score)} />
                <EvidenceRail label="排名稳健性" value={record.ranking_robustness / 100} display={scoreValue(record.ranking_robustness)} />
              </div>
            </section>

            <section className="px-6 py-6 sm:px-7">
              <div className="flex items-end justify-between"><h3 className="drawer-label">敏感性排名范围</h3><span className="font-mono text-sm text-[var(--sw-text)]">{rankRange(record.sensitivity_rank_min, record.sensitivity_rank_max)}</span></div>
              <RankRangeRail min={record.sensitivity_rank_min} max={record.sensitivity_rank_max} scale={rankingScale} />
              <p className="mt-3 text-xs leading-5 text-[var(--sw-muted)]">敏感性区间表示权重变化时的排名范围，不等同于统计置信度。</p>
            </section>

            <section className="px-6 py-6 sm:px-7">
              <h3 className="drawer-label">技能共现 · ALL-ACTIVE GRAPH</h3>
              <div className="mt-4 divide-y divide-[var(--sw-line)] border-y border-[var(--sw-line)]">
                {related.data?.records.slice(0, 5).map((item) => <div key={item.skill_id} className="grid grid-cols-[1fr_auto] items-center gap-4 py-3"><span className="text-xs text-[var(--sw-text-secondary)]">{item.canonical_name}</span><span className="text-right font-mono text-[9px] leading-4 text-[var(--sw-muted)]">{item.cooccurrence_count} co-jobs<br />J {item.jaccard.toFixed(3)} · PMI {item.pmi.toFixed(3)}</span></div>)}
                {!related.isLoading && !related.data?.records.length && <span className="text-xs text-[var(--sw-muted)]">当前支持度下暂无稳定关联。</span>}
              </div>
              <p className="mt-3 text-[10px] leading-5 text-[var(--sw-muted)]">共同出现次数表示规模；Jaccard / PMI 表示相对亲和度。共现不是因果，也不是必须一起学习。</p>
            </section>

            <section className="px-6 py-6 sm:px-7">
              <h3 className="drawer-label">岗位方向分布</h3>
              <div className="mt-4 space-y-3">
                {roles.slice(0, 6).map((item) => <div key={item.role} className="grid grid-cols-[96px_1fr_32px] items-center gap-3 text-xs"><span className="truncate text-[var(--sw-text-secondary)]">{item.label}</span><span className="h-px bg-[var(--sw-line-strong)]"><span className="block h-px bg-[var(--sw-cyan)]" style={{ width: `${(item.jobCount / maxRoleJobs) * 100}%` }} /></span><span className="text-right font-mono text-[var(--sw-text)]">{item.jobCount}</span></div>)}
                {!roles.length && <span className="text-xs text-[var(--sw-muted)]">暂无可用岗位方向分布。</span>}
              </div>
            </section>

            <section className="px-6 py-6 sm:px-7">
              <h3 className="drawer-label">证据边界</h3>
              <dl className="mt-4 grid grid-cols-2 gap-x-7 gap-y-5">
                <Evidence label="快照" value={record.snapshot_id} mono />
                <Evidence label="时间窗口" value={RECENCY_OPTIONS.find((item) => item.value === recencyWindow)?.label ?? recencyWindow} />
                <Evidence label="样本量" value={`${record.sample_size} 个岗位`} />
                <Evidence label="数据置信度" value={`${record.confidence.toFixed(0)} · ${record.confidence_level}`} />
                <Evidence label="薪资信号" value="Insufficient evidence" subdued />
                <Evidence label="趋势信号" value="Requires multiple independent snapshots" subdued />
              </dl>
            </section>
          </div>
        </>}
      </SheetContent>
    </Sheet>
  );
}

function DrawerMetric({ label, value, priority }: { label: string; value: string; priority: "primary" | "secondary" | "tertiary" }) {
  return <div className={`drawer-core-metric drawer-core-metric-${priority} min-w-0 border-r border-[var(--sw-line)] px-3 first:pl-0 last:border-0 last:pr-0`}><p className="drawer-label truncate">{label}</p><p className="mt-2 font-mono tabular-nums">{value}</p></div>;
}

function EvidenceRail({ label, value, display }: { label: string; value: number; display: string }) {
  const width = Math.max(0, Math.min(100, value * 100));
  return <div><div className="mb-2 flex items-center justify-between gap-4 text-[10px]"><span className="text-[var(--sw-text-secondary)]">{label}</span><span className="font-mono text-[var(--sw-text)]">{display}</span></div><div className="h-px bg-[var(--sw-line-strong)]"><span className="block h-px bg-[var(--sw-accent)] shadow-[0_0_9px_rgba(200,220,98,.35)]" style={{ width: `${width}%` }} /></div></div>;
}

function RankRangeRail({ min, max, scale }: { min: number | null; max: number | null; scale: number }) {
  if (min == null || max == null) return <div className="mt-5 h-px bg-[var(--sw-line-strong)]" />;
  const left = Math.max(0, ((min - 1) / Math.max(scale - 1, 1)) * 100);
  const width = Math.max(2, ((max - min + 1) / Math.max(scale, 1)) * 100);
  return <div className="relative mt-6 h-px bg-[var(--sw-line-strong)]" aria-label={`敏感性排名范围 ${min} 到 ${max}`}><span className="absolute -top-[3px] h-[7px] min-w-[8px] bg-[var(--sw-accent)] shadow-[0_0_12px_rgba(200,220,98,.42)]" style={{ left: `${left}%`, width: `${width}%` }} /></div>;
}

function Evidence({ label, value, mono = false, subdued = false }: { label: string; value: string; mono?: boolean; subdued?: boolean }) {
  return <div><dt className="text-[9px] uppercase tracking-[.1em] text-[var(--sw-muted)]">{label}</dt><dd className={`mt-1.5 break-words text-xs leading-5 ${subdued ? "text-[var(--sw-violet)]" : "text-[var(--sw-text-secondary)]"} ${mono ? "font-mono text-[10px]" : ""}`}>{value}</dd></div>;
}
