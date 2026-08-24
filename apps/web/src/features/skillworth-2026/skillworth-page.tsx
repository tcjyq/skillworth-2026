"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, Info } from "@phosphor-icons/react";
import { CinematicHero } from "./cinematic-hero";
import { FrontierFindings, RobustCoreHeading, RoleReversalStory, StoryPrelude, SynergyStory } from "./finding-stories";
import { FrontierChart } from "./frontier-chart";
import { deriveFinalFindings } from "./findings";
import { MarketThemes } from "./market-themes";
import { RobustPicks } from "./robust-picks";
import { SkillDetailSheet } from "./skill-detail-sheet";
import { RECENCY_OPTIONS, ROLE_OPTIONS, SOURCE_ROLE_LABELS, type RecencyWindow } from "./config";
import { selectFrontierRecords } from "./selection";
import { useApi } from "@/hooks/use-api";
import type { ChinaSkillWorthRecord, ChinaSkillWorthResponse, RelatedSkills, RolesResponse } from "@/lib/api/types";

export function SkillWorthPage() {
  const [recencyWindow, setRecencyWindow] = useState<RecencyWindow>("180d");
  const [role, setRole] = useState("all");
  const [showAllRobust, setShowAllRobust] = useState(false);
  const [showModerate, setShowModerate] = useState(false);
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [selected, setSelected] = useState<ChinaSkillWorthRecord | null>(null);
  const [focusedSkillId, setFocusedSkillId] = useState<string | null>(null);

  const params = new URLSearchParams({
    eligibility: "main",
    robustness: showModerate ? "all" : "robust",
    recency_window: recencyWindow,
  });
  if (role !== "all") params.set("role", role);
  const result = useApi<ChinaSkillWorthResponse>(`/market/china-skillworth?${params.toString()}`);
  const roles = useApi<RolesResponse>("/roles");
  const frozenGlobal = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=180d");
  const frozenDevops = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=180d&role=devops_engineer");
  const frozenData = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=180d&role=data_engineer");
  const frozenAllActive = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=all_active");
  const pythonRelated = useApi<RelatedSkills>("/skills/programming_python/related");
  const numpyRelated = useApi<RelatedSkills>("/skills/data_analysis_numpy/related");
  const grafanaRelated = useApi<RelatedSkills>("/skills/devops_grafana/related");

  const supportedRoleIds = useMemo(() => new Set(roles.data?.records.map((item) => item.role_id) ?? []), [roles.data]);
  const roleOptions = ROLE_OPTIONS.filter((item) => item.value === "all" || supportedRoleIds.has(item.value));
  const allRecords = useMemo(() => result.data?.records ?? [], [result.data?.records]);
  const robustCandidates = useMemo(
    () => allRecords.filter((item) => item.high_skillworth_candidate && item.robustness_level === "robust").sort(byRank),
    [allRecords],
  );
  const displayRecords = useMemo(
    () => selectFrontierRecords(allRecords, { showAllRobust, showModerate }),
    [allRecords, showAllRobust, showModerate],
  );
  const rankingScale = useMemo(() => Math.max(...allRecords.map((item) => item.skillworth_rank ?? 0), 1), [allRecords]);
  const marketThemes = useMemo(() => result.data?.market_themes.slice(0, 6) ?? [], [result.data?.market_themes]);
  const sourceRole = result.data ? SOURCE_ROLE_LABELS[result.data.source_role] ?? result.data.source_role.replaceAll("_", " ") : "—";
  const windowLabel = RECENCY_OPTIONS.find((item) => item.value === recencyWindow)?.label ?? recencyWindow;
  const findings = useMemo(() => deriveFinalFindings({
    global: frozenGlobal.data,
    devops: frozenDevops.data,
    data: frozenData.data,
    allActive: frozenAllActive.data,
    pythonRelated: pythonRelated.data,
    numpyRelated: numpyRelated.data,
    grafanaRelated: grafanaRelated.data,
  }), [frozenAllActive.data, frozenData.data, frozenDevops.data, frozenGlobal.data, grafanaRelated.data, numpyRelated.data, pythonRelated.data]);

  const changeRole = (value: string) => {
    setRole(value);
    setSelected(null);
    setSelectedTheme(null);
  };
  const changeWindow = (value: string) => {
    setRecencyWindow(value as RecencyWindow);
    setSelected(null);
    setSelectedTheme(null);
  };
  const selectFrozenRole = (value: "devops_engineer" | "data_engineer") => {
    setRecencyWindow("180d");
    changeRole(value);
  };

  return (
    <div className="min-h-screen bg-[var(--sw-canvas)] text-[var(--sw-text)]">
      <main id="main-content">
        <div className="cinematic-market-space">
          <CinematicHero robustPickCount={result.data ? robustCandidates.length : null} jobCount={result.data?.job_count ?? null} companyCount={result.data?.company_count ?? null} skillCount={result.data?.skill_count ?? null} windowLabel={windowLabel} sourceRole={sourceRole} />

        <section id="data-scope" className="mx-auto max-w-[1560px] scroll-mt-20 px-5 py-10 sm:px-8 lg:px-12 lg:py-12" aria-labelledby="scope-title">
          <SectionHeading id="scope-title" title="EVIDENCE / SCOPE" description="Analysis Freeze V1：当前证据能支持什么，以及哪些信号仍不可用。" />
          <div className="grid border-y border-[var(--sw-line)] md:grid-cols-2 lg:grid-cols-4">
            <ScopeItem label="SNAPSHOT" value={result.data?.snapshot ?? "—"} mono />
            <ScopeItem label="RECENCY WINDOW" value={windowLabel} />
            <ScopeItem label="OBSERVATIONS" value={result.data ? `${result.data.job_count} 岗位 · ${result.data.company_count} 公司 · ${result.data.skill_count} 技能` : "—"} />
            <ScopeItem label="SOURCE ROLE" value={sourceRole} />
            <ScopeItem label="SALARY SIGNAL" value="Unavailable · Insufficient evidence" />
            <ScopeItem label="TREND SIGNAL" value="Unavailable · Requires independent snapshots" />
            <ScopeItem label="MARKET SCOPE" value="China Open Tech Sample" />
            <ScopeItem label="CONFIDENCE STATUS" value="按技能展示证据强度" />
          </div>
          <div className="mt-6 flex max-w-[920px] gap-3 text-xs leading-6 text-[var(--sw-muted)]"><Info className="mt-1 shrink-0" size={14} /><p>{result.data?.disclaimer ?? "该样本来源于当前可观察的中国公开技术岗位，不代表完整中国招聘市场。"} All Active 可能包含早于 2026 年发布、但在快照时仍可观察的岗位。</p></div>
        </section>

        <StoryPrelude />

        <section className="relative mx-auto max-w-[1560px] px-5 py-10 sm:px-8 lg:px-12 lg:pb-14 lg:pt-12" aria-labelledby="frontier-title">
          <div className="grid min-w-0 gap-6 border-b border-[var(--sw-line)] pb-5 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
            <div className="min-w-0">
              <h2 id="frontier-title" className="text-2xl font-semibold tracking-[-.025em] sm:text-[2rem]">SKILLWORTH FRONTIER <span className="ml-2 text-base font-normal text-[var(--sw-muted)]">技值前沿</span></h2>
              <p className="mt-2 max-w-[650px] text-pretty text-xs leading-5 text-[var(--sw-muted)]">向上代表市场信号增强，向左代表预期学习投入降低；气泡面积按岗位数平方根缩放。</p>
            </div>
            <div className="flex min-w-0 flex-col gap-3 xl:items-end">
              <FilterGroup label="岗位方向" value={role} options={roleOptions} onChange={changeRole} />
              <FilterGroup label="时间窗口" value={recencyWindow} options={RECENCY_OPTIONS} onChange={changeWindow} />
            </div>
          </div>

          <FrontierFindings findings={findings} />

          <div className="relative border-b border-[var(--sw-line)]">
            {result.isValidating && result.data && <div className="absolute inset-x-0 top-0 z-10 h-px overflow-hidden bg-[var(--sw-line)]"><span className="block h-full w-1/3 animate-pulse bg-[var(--sw-accent)]" /></div>}
            {result.isLoading && !result.data && <FrontierSkeleton />}
            {result.error && <div className="flex h-[420px] flex-col items-center justify-center text-center"><p className="text-sm text-[var(--sw-warning)]">真实市场数据暂时无法读取。</p><button onClick={() => void result.mutate()} className="sw-focus mt-4 border border-[var(--sw-line-strong)] px-4 py-2 text-xs hover:border-[var(--sw-accent)]">重新请求</button></div>}
            {result.data && !displayRecords.length && <div className="flex h-[420px] items-center justify-center text-sm text-[var(--sw-muted)]">当前筛选没有满足稳健候选条件的技能。</div>}
            {displayRecords.length > 0 && <FrontierChart records={displayRecords} selectedId={selected?.skill_id} focusedId={focusedSkillId} highlightedTheme={selectedTheme} onFocus={setFocusedSkillId} onSelect={setSelected} />}
          </div>

          <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-[720px] text-[11px] leading-5 text-[var(--sw-muted)]">默认显示前 12 项 Robust 高技值候选。虚线为当前候选的效率前沿；精确排名不是绝对结论。</p>
            <div className="flex shrink-0 gap-2">
              <button aria-pressed={showModerate} onClick={() => setShowModerate((value) => !value)} className={`filter-toggle sw-focus ${showModerate ? "filter-toggle-active" : ""}`}>Moderate {showModerate ? "已显示" : "隐藏"}</button>
              <button aria-pressed={showAllRobust} onClick={() => setShowAllRobust((value) => !value)} className={`filter-toggle sw-focus ${showAllRobust ? "filter-toggle-active" : ""}`}>{showAllRobust ? "显示前 12" : `全部 Robust · ${robustCandidates.length}`}</button>
            </div>
          </div>
          {selectedTheme && <p role="status" className="border-t border-[var(--sw-line)] py-3 text-[11px] text-[var(--sw-text-secondary)]">正在突出与 <strong className="font-medium text-[var(--sw-accent)]">{selectedTheme}</strong> 相关的具体候选；其他技能保留为对照。</p>}
        </section>
        </div>

        <RoleReversalStory findings={findings} onSelectRole={selectFrozenRole} />

        <SynergyStory findings={findings} />

        <section className="market-board-band cinematic-reveal" aria-labelledby="picks-title">
          <div className="mx-auto max-w-[1560px] px-5 py-16 sm:px-8 lg:px-12 lg:py-22">
          <RobustCoreHeading findings={findings} />
          {robustCandidates.length ? <RobustPicks records={robustCandidates} focusedId={focusedSkillId} onFocus={setFocusedSkillId} onSelect={setSelected} /> : <p className="border-y border-[var(--sw-line)] py-10 text-sm text-[var(--sw-muted)]">当前筛选下暂无稳健候选。</p>}
          </div>
        </section>

        <section className="themes-atmosphere cinematic-reveal mx-auto max-w-[1560px] px-5 py-18 sm:px-8 lg:px-12 lg:py-26" aria-labelledby="themes-title">
          <SectionHeading id="themes-title" title="MARKET THEMES" description="主题描述岗位文本中的领域广度，不是可直接学习的技能，不显示 SkillWorth，也不会进入主榜。点击后仅突出关联候选。" />
          {marketThemes.length ? <MarketThemes themes={marketThemes} selected={selectedTheme} onSelect={setSelectedTheme} /> : <p className="border-y border-[var(--sw-line)] py-10 text-sm text-[var(--sw-muted)]">当前窗口暂无可用主题聚合。</p>}
        </section>

        <section className="border-y border-[var(--sw-line)]" aria-labelledby="method-title">
          <div className="mx-auto max-w-[1560px] px-5 py-14 sm:px-8 lg:px-12 lg:py-18">
            <SectionHeading id="method-title" title="HOW IT WORKS" description="所有信号由同一数据管道计算；学习时长是版本化估算，不是学习结果承诺。" />
            <ol className="grid gap-px border border-[var(--sw-line)] bg-[var(--sw-line)] md:grid-cols-4 lg:grid-cols-7">
              {["公开岗位", "技能标准化", "需求 / 公司 / 岗位广度 / 协同", "市场信号", "学习投入", "SkillWorth", "排名稳健性"].map((step, index) => <li key={step} className="relative bg-[var(--sw-canvas)] px-4 py-5 text-xs text-[var(--sw-text-secondary)]"><span className="mb-4 block font-mono text-[9px] text-[var(--sw-muted)]">{String(index + 1).padStart(2, "0")}</span>{step}{index < 6 && <ArrowRight aria-hidden="true" className="absolute -right-2 top-1/2 z-10 hidden -translate-y-1/2 text-[var(--sw-muted)] md:block" size={14} />}</li>)}
            </ol>
            <Link href="/methodology" className="sw-focus mt-6 inline-flex items-center gap-2 text-xs text-[var(--sw-accent)] hover:text-[#e0ed9b]">阅读完整方法说明 <ArrowRight size={14} /></Link>
          </div>
        </section>

      </main>

      <footer className="border-t border-[var(--sw-line)]"><div className="mx-auto flex max-w-[1560px] flex-col gap-3 px-5 py-7 text-[10px] uppercase tracking-[.1em] text-[var(--sw-muted)] sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12"><span>SKILLWORTH 2026 · Research Product</span><Link href="/lab" className="sw-focus normal-case tracking-normal hover:text-[var(--sw-text-secondary)]">研究工具与历史视图</Link></div></footer>
      <SkillDetailSheet record={selected} recencyWindow={recencyWindow} rankingScale={rankingScale} onClose={() => setSelected(null)} />
    </div>
  );
}

function byRank(left: ChinaSkillWorthRecord, right: ChinaSkillWorthRecord) { return (left.skillworth_rank ?? Number.MAX_SAFE_INTEGER) - (right.skillworth_rank ?? Number.MAX_SAFE_INTEGER); }

function FilterGroup({ label, value, options, onChange }: { label: string; value: string; options: readonly { value: string; label: string }[]; onChange: (value: string) => void }) { return <div className="editorial-filter flex max-w-full items-center gap-3 overflow-x-auto scrollbar-none"><span className="shrink-0 font-mono text-[9px] uppercase tracking-[.1em] text-[var(--sw-muted)]">{label}</span><div className="flex shrink-0 gap-4">{options.map((option) => <button key={option.value} aria-pressed={value === option.value} onClick={() => onChange(option.value)} className={`sw-focus relative min-h-8 whitespace-nowrap px-0.5 py-1.5 text-[10px] uppercase tracking-[.04em] ${value === option.value ? "text-[var(--sw-accent)] after:absolute after:inset-x-0 after:bottom-0 after:h-px after:bg-[var(--sw-accent)]" : "text-[var(--sw-text-secondary)] hover:text-[var(--sw-text)]"}`}>{option.label}</button>)}</div></div>; }

function SectionHeading({ id, title, description }: { id: string; title: string; description: string }) { return <div className="mb-7 grid gap-2 md:grid-cols-[260px_1fr] md:items-start"><h2 id={id} className="text-xl font-semibold tracking-[-.025em] sm:text-2xl">{title}</h2><p className="max-w-[720px] text-pretty text-xs leading-5 text-[var(--sw-muted)]">{description}</p></div>; }

function ScopeItem({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) { return <div className="border-b border-[var(--sw-line)] px-4 py-5 md:border-r"><p className="font-mono text-[9px] tracking-[.1em] text-[var(--sw-muted)]">{label}</p><p className={`mt-3 break-words text-xs leading-5 text-[var(--sw-text-secondary)] ${mono ? "font-mono text-[10px]" : ""}`}>{value}</p></div>; }

function FrontierSkeleton() { return <div className="h-[380px] px-8 py-10 sm:h-[520px] lg:h-[620px]"><div className="sw-skeleton h-px w-full" /><div className="relative h-full border-b border-l border-[var(--sw-line)]"><span className="sw-skeleton absolute left-[14%] top-[58%] h-9 w-9 rounded-full" /><span className="sw-skeleton absolute left-[38%] top-[38%] h-12 w-12 rounded-full" /><span className="sw-skeleton absolute left-[63%] top-[22%] h-16 w-16 rounded-full" /><span className="sw-skeleton absolute left-[78%] top-[52%] h-10 w-10 rounded-full" /></div></div>; }
