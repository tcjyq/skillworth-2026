"use client";

import { MagnifyingGlass, SlidersHorizontal } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import type { ChinaSkillWorthRecord, ChinaSkillWorthResponse, RolesResponse } from "@/lib/api/types";
import { roleLabel } from "./terminology";
import styles from "./visual-v2.module.css";

const RECENCY = [
  { value: "180d", label: "近 180 天" },
  { value: "all_active", label: "全部在招样本" },
] as const;

function robustnessLabel(record: ChinaSkillWorthRecord) {
  if (record.robustness_level === "robust") return "很稳";
  if (record.robustness_level === "moderate") return "中等";
  return "需谨慎";
}

function rankRange(record: ChinaSkillWorthRecord) {
  return record.sensitivity_rank_min != null && record.sensitivity_rank_max != null
    ? `${record.sensitivity_rank_min}–${record.sensitivity_rank_max} 名`
    : "暂无稳定区间";
}

function rankingLayerReason(record: ChinaSkillWorthRecord) {
  return record.skillworth_rank != null
    ? "当前证据满足主排名层条件，可以用于比较；这不等于正式推荐。"
    : "当前证据不足以进入主排名层，因此只保留真实观察结果。";
}

function confidenceLabel(level: ChinaSkillWorthRecord["confidence_level"]) {
  if (level === "High") return "高";
  if (level === "Medium") return "中等";
  return "低";
}

export function ExploreMode() {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [viewMode, setViewMode] = useState<"skill" | "role">("skill");
  const [layer, setLayer] = useState<"all" | "ranked" | "observed">("all");
  const [recency, setRecency] = useState<(typeof RECENCY)[number]["value"]>("180d");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const roles = useApi<RolesResponse>("/roles");
  const path = `/market/china-skillworth?eligibility=all&robustness=all&recency_window=${recency}${role ? `&role=${role}` : ""}`;
  const result = useApi<ChinaSkillWorthResponse>(path);
  const records = useMemo(() => result.data?.records ?? [], [result.data?.records]);
  const normalized = query.trim().toLocaleLowerCase("zh-CN");
  const searched = useMemo(() => records.filter((record) => !normalized || `${record.skill} ${record.skill_category} ${record.skill_type}`.toLocaleLowerCase("zh-CN").includes(normalized)), [normalized, records]);
  const filtered = useMemo(() => searched.filter((record) => layer === "all" || (layer === "ranked" ? record.skillworth_rank != null : record.skillworth_rank == null && record.job_count > 0)), [layer, searched]);
  const allRanked = records.filter((record) => record.skillworth_rank != null);
  const allObserved = records.filter((record) => record.skillworth_rank == null && record.job_count > 0);
  const ranked = filtered.filter((record) => record.skillworth_rank != null);
  const observed = filtered.filter((record) => record.skillworth_rank == null && record.job_count > 0);
  const selected = records.find((record) => record.skill_id === selectedId) ?? ranked[0] ?? observed[0] ?? null;
  const lowEvidence = Boolean(role && result.data && (result.data.job_count < 10 || allRanked.length === 0));
  const evidenceLevel = result.data && result.data.job_count <= 3 ? "极低样本" : "低样本";
  const success = !result.error ? result.data : undefined;

  function changeViewMode(nextMode: "skill" | "role") {
    setViewMode(nextMode);
    setQuery("");
    if (nextMode === "skill") setRole("");
    if (nextMode === "role" && !role) setRole("backend_engineer");
    setSelectedId(null);
  }

  return <section id="explore" className={styles.exploreMode} aria-labelledby="explore-title">
    <div className={styles.exploreIntro}>
      <p>开始自己的查找</p>
      <h2 id="explore-title">{success ? `探索 ${success.skill_count} 项技能` : "探索技能"}</h2>
      <p>按技能或岗位查找，首先看岗位覆盖、公司覆盖、学习时间和排名稳定性。</p>
    </div>

    <div className={styles.exploreModeSwitch} role="group" aria-label="探索方式"><button type="button" aria-pressed={viewMode === "skill"} onClick={() => changeViewMode("skill")}>按技能</button><button type="button" aria-pressed={viewMode === "role"} onClick={() => changeViewMode("role")}>按岗位</button></div>
    <div className={styles.exploreToolbar}>
      <label className={styles.searchField}><MagnifyingGlass size={20} aria-hidden="true" /><span className="sr-only">搜索技能</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索 Python、Java、React、Redis…" /></label>
      <label className={viewMode === "role" ? styles.activeExploreControl : ""}><span>岗位方向</span><select aria-label="岗位方向" value={role} onChange={(event) => { setRole(event.target.value); setSelectedId(null); }}><option value="">全部岗位</option>{roles.data?.records.map((item) => <option key={item.role_id} value={item.role_id}>{roleLabel(item.role_id)} · {item.canonical_job_count} 岗位</option>)}</select></label>
      <label><span>技能层</span><select aria-label="技能层" value={layer} onChange={(event) => { setLayer(event.target.value as typeof layer); setSelectedId(null); }}><option value="all">全部技能层</option><option value="ranked">主排名层</option><option value="observed">已观察技能</option></select></label>
      <label><span>观察窗口</span><select aria-label="观察窗口" value={recency} onChange={(event) => { setRecency(event.target.value as (typeof RECENCY)[number]["value"]); setSelectedId(null); }}>{RECENCY.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
    </div>

    {result.error && <div className={styles.exploreState}><p>当前数据暂时无法读取</p><button type="button" onClick={() => void result.mutate()}>重试</button></div>}
    {!result.data && !result.error && <div className={styles.exploreState}>正在读取完整技能集合…</div>}
    {success && success.records.length === 0 && <div className={styles.exploreState}>当前筛选条件下没有可展示的技能</div>}
    {success && success.records.length > 0 && <>
      <div className={styles.resultSummary} aria-live="polite">
        <span><b>{records.length}</b> 项可搜索技能</span>
        <span><b>{allRanked.length}</b> 项进入主排名层</span>
        <span><b>{allObserved.length}</b> 项仅观察</span>
        <span><b>{success.job_count}</b> 个岗位样本</span>
        {normalized && <span><b>{searched.length}</b> 项匹配搜索</span>}
      </div>

      {lowEvidence && <div className={`${styles.lowEvidence} ${evidenceLevel === "极低样本" ? styles.severeEvidence : ""}`}>
        <strong>当前岗位样本较少。以下排序仅反映当前开放样本，不构成稳定推荐。</strong>
        <dl><div><dt>样本</dt><dd>{success.job_count} 个岗位</dd></div><div><dt>证据状态</dt><dd>{evidenceLevel}</dd></div><div><dt>解释</dt><dd>可以查看当前样本中的技能排序与观察结果，但不宜将精确名次视为稳定结论。</dd></div></dl>
      </div>}

      {filtered.length === 0 ? <div className={styles.exploreState}>当前筛选中没有找到“{query}”。清除岗位筛选后可继续搜索全局技能集合。</div> : <div className={styles.exploreWorkspace}>
        <div className={styles.skillLists}>
          <SkillLayer title="主排名层" explanation="当前规则可计算排名，不等于正式推荐" records={ranked} selectedId={selected?.skill_id ?? null} onSelect={setSelectedId} ranked />
          <SkillLayer title="已观察技能" explanation="样本中真实出现，但没有进入当前主排名层" records={observed} selectedId={selected?.skill_id ?? null} onSelect={setSelectedId} />
        </div>
        <SkillDetail record={selected} role={role} />
      </div>}
    </>}
  </section>;
}

function SkillLayer({ title, explanation, records, selectedId, onSelect, ranked = false }: { title: string; explanation: string; records: ChinaSkillWorthRecord[]; selectedId: string | null; onSelect: (id: string) => void; ranked?: boolean }) {
  return <section className={styles.skillLayer} aria-label={title}>
    <header><div><h3>{title}</h3><p>{explanation}</p></div><b>{records.length}</b></header>
    {records.length === 0 ? <p className={styles.layerEmpty}>这一层当前没有技能。</p> : <div className={styles.skillRows}>{records.map((record) => <button key={record.skill_id} type="button" className={record.skill_id === selectedId ? styles.skillRowActive : ""} onClick={() => onSelect(record.skill_id)}>
      <span>{record.skill}</span><small>{record.job_count} 岗位</small>{ranked ? <b>#{record.skillworth_rank}</b> : <i aria-label="仅观察"><SlidersHorizontal size={17} /></i>}
    </button>)}</div>}
  </section>;
}

function SkillDetail({ record, role }: { record: ChinaSkillWorthRecord | null; role: string }) {
  if (!record) return <aside className={styles.skillDetail}><p>选择一个技能查看证据。</p></aside>;
  return <aside className={styles.skillDetail} aria-live="polite">
    <div className={styles.detailHeading}><div><p>{role ? roleLabel(role, true) : "全局样本"}</p><h3>{record.skill}</h3></div>{record.skillworth_rank != null ? <b>学习性价比第 {record.skillworth_rank} 名</b> : <b className={styles.observedBadge}>仅观察</b>}</div>
    <dl className={styles.plainMetrics}>
      <div><dt>岗位覆盖</dt><dd>{record.job_count} 个岗位</dd></div>
      <div><dt>公司覆盖</dt><dd>{record.company_count} 家公司</dd></div>
      <div><dt>约学习时间</dt><dd>约 {record.learning_hours_expected} 小时</dd></div>
      <div><dt>排名稳定性</dt><dd>{robustnessLabel(record)} · {rankRange(record)}</dd></div>
    </dl>
    <p className={styles.eligibilityReason}>{rankingLayerReason(record)}</p>
    <details><summary>查看进阶指标</summary><dl className={styles.advancedMetrics}><div><dt>市场支持度（Market Signal）</dt><dd>{record.market_signal.toFixed(2)}</dd></div><div><dt>学习性价比（SkillWorth）</dt><dd>{record.skillworth_score.toFixed(2)}</dd></div><div><dt>岗位方向覆盖（Role Breadth）</dt><dd>{record.role_breadth.toFixed(4)}</dd></div><div><dt>技能共同出现程度（Synergy）</dt><dd>{record.synergy_score.toFixed(4)}</dd></div><div><dt>证据可信度（Confidence）</dt><dd>{record.confidence.toFixed(1)} · {confidenceLabel(record.confidence_level)}</dd></div></dl></details>
  </aside>;
}
