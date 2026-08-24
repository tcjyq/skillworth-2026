"use client";

import { CaretDown } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import type { ChinaSkillWorthResponse, RolesResponse } from "@/lib/api/types";
import { roleLabel } from "./terminology";
import { recencyLabel, sourceRoleLabel } from "./market-metadata";
import { VisualLoading } from "./visual-loading";
import styles from "./visual-v2.module.css";

const PRIMARY_ROLES = [
  { role: "backend_engineer", label: "后端" },
  { role: "ml_engineer", label: "AI / 机器学习" },
  { role: "data_analyst", label: "数据分析" },
  { role: "data_engineer", label: "数据工程" },
  { role: "devops_engineer", label: "运维 / DevOps" },
  { role: "frontend_engineer", label: "前端" },
  { role: "product_manager", label: "产品" },
] as const;

function evidenceLabel(sampleSize: number) {
  if (sampleSize <= 3) return "极低样本";
  if (sampleSize < 10) return "低样本";
  if (sampleSize < 30) return "有限样本";
  return "样本可用";
}

export function RoleFirst() {
  const [role, setRole] = useState<string>("backend_engineer");
  const [showMore, setShowMore] = useState(false);
  const roles = useApi<RolesResponse>("/roles");
  const global = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d");
  const result = useApi<ChinaSkillWorthResponse>(`/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d&role=${role}`);
  const globalBySkill = useMemo(() => new Map(global.data?.records.map((record) => [record.skill_id, record])), [global.data?.records]);
  const ranked = result.data?.records.filter((record) => record.skillworth_rank != null).slice(0, 4) ?? [];
  const observed = result.data?.records.filter((record) => record.skillworth_rank == null && record.job_count > 0).slice(0, 6) ?? [];
  const sampleSize = result.data?.job_count ?? 0;
  const lowEvidence = Boolean(result.data && sampleSize < 10);
  const hasError = Boolean(result.error || global.error);
  const isLoading = !hasError && (!result.data || !global.data);
  const success = !hasError && result.data && global.data ? result.data : undefined;

  function selectRole(nextRole: string) {
    setRole(nextRole);
  }

  return <section id="roles" className={styles.roleFirst} aria-labelledby="roles-title">
    <div className={styles.roleIntro}>
      <p>先选目标，再看排名</p>
      <h2 id="roles-title">你想做什么方向？</h2>
      <p>同一项技能，在不同岗位中的优先级可能完全不同。</p>
    </div>

    <div className={styles.roleChoices} aria-label="常用岗位方向">
      {PRIMARY_ROLES.map((item) => <button key={item.role} type="button" aria-pressed={role === item.role} onClick={() => selectRole(item.role)}>{item.label}</button>)}
      <button type="button" aria-expanded={showMore} onClick={() => setShowMore((current) => !current)}>更多方向 <CaretDown size={16} weight="bold" /></button>
    </div>

    {showMore && <label className={styles.moreRoleSelect}><span>全部岗位方向</span><select value={role} onChange={(event) => selectRole(event.target.value)}>{roles.data?.records.map((item) => <option key={item.role_id} value={item.role_id}>{roleLabel(item.role_id)} · {item.canonical_job_count} 岗位</option>)}</select></label>}

    <article className={styles.roleResult} aria-live="polite">
      {isLoading && <VisualLoading label="正在读取该方向的当前样本…" variant="panel" />}
      {hasError && <div className={styles.roleLoading}><p>当前数据暂时无法读取</p><button type="button" onClick={() => { void result.mutate(); void global.mutate(); }}>重试</button></div>}
      {success && success.records.length === 0 && <p className={styles.roleLoading}>当前岗位方向下没有可展示的技能</p>}
      {success && success.records.length > 0 && <>
        <header className={styles.roleResultHeader}>
          <div><p>当前方向</p><h3>{roleLabel(role, true)}</h3></div>
          <dl><div><dt>样本</dt><dd>{sampleSize} 个岗位</dd></div><div><dt>证据状态</dt><dd>{evidenceLabel(sampleSize)}</dd></div></dl>
        </header>

        {lowEvidence && <div className={styles.roleEvidence}><strong>当前岗位样本较少。</strong><p>可以查看当前样本中的技能排序与观察结果，但不宜将精确名次视为稳定结论。</p></div>}

        <div className={styles.roleSkills}>
          <div className={styles.roleSkillsHeading}><h4>主要技能</h4><span>全局学习性价比排名 → 当前方向排名</span></div>
          {ranked.length > 0 ? ranked.map((record) => {
            const globalRank = globalBySkill.get(record.skill_id)?.skillworth_rank;
            return <div className={styles.roleSkillRow} key={record.skill_id}><strong>{record.skill}</strong><span>{record.job_count} 个岗位提到</span><b>{globalRank != null ? `#${globalRank}` : "仅观察"} <i>→</i> #{record.skillworth_rank}</b></div>;
          }) : <div className={styles.noRoleRanking}><strong>当前没有可计算的岗位排名</strong><p>{observed.length} 项已观察技能：{observed.map((record) => record.skill).join("、")}。保留真实观察，不制造排名。</p></div>}
        </div>
        <p className={styles.roleSource}>样本：{sourceRoleLabel(success.source_role)} · {recencyLabel(success.recency_window)}</p>
      </>}
    </article>
  </section>;
}
