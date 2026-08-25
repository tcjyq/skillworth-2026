"use client";

import { useEffect, useRef } from "react";
import { useGSAP } from "@gsap/react";
import { gsap } from "gsap";
import type { ChinaSkillWorthRecord, SkillRelationRecord } from "@/lib/api/types";
import { roleEvidence } from "../layout";
import type { SceneState } from "../state/scene-machine";
import styles from "../skill-field.module.css";
import { formatRelationEvidence } from "../scene/visual-system";

gsap.registerPlugin(useGSAP);

function robustnessCopy(record: ChinaSkillWorthRecord) {
  if (record.sensitivity_rank_min === record.sensitivity_rank_max) return `稳定在第 ${record.sensitivity_rank_min} 名`;
  return `大多在 ${record.sensitivity_rank_min}–${record.sensitivity_rank_max} 名`;
}

export function DetailPanel({
  state,
  record,
  relation,
  onSelectRelation,
}: {
  state: SceneState;
  record: ChinaSkillWorthRecord | null;
  relation: SkillRelationRecord | null;
  onSelectRelation: (skillId: string) => void;
}) {
  const panelRef = useRef<HTMLElement>(null);
  useGSAP(() => {
    if (state.reducedMotion || !panelRef.current) return;
    const evidenceBlocks = panelRef.current.querySelectorAll("[data-evidence-block]");
    if (!evidenceBlocks.length) return;
    gsap.fromTo(evidenceBlocks,
      { y: 18, opacity: 0.35 },
      { y: 0, opacity: 1, duration: 0.5, stagger: 0.045, ease: "power3.out", overwrite: true });
  }, { scope: panelRef, dependencies: [record?.skill_id, relation?.related_skill_id, state.reducedMotion] });
  useEffect(() => { panelRef.current?.scrollTo({ top: 0, behavior: state.reducedMotion ? "auto" : "smooth" }); }, [record?.skill_id, state.reducedMotion]);
  if (!record) return <aside ref={panelRef} className={styles.detailPanel} aria-label="技能详情">
    <div className={styles.detailEmpty}><p>选择一个技能</p><span>点击节点或使用搜索，查看岗位证据和技能关系。</span></div>
  </aside>;
  const gate = state.activeRole ? roleEvidence(state.activeRole.sampleSize) : null;
  return <aside ref={panelRef} className={styles.detailPanel} aria-label="技能详情">
    <header data-evidence-block>
      <p>{state.activeRole ? state.activeRole.label : "当前公开样本"}</p>
      <h2>{record.skill}</h2>
      <span>{record.skillworth_eligibility === "main" && record.skillworth_rank ? `学习性价比第 ${record.skillworth_rank}` : "已观察，但当前不进入主排名"}</span>
    </header>
    {gate?.warning && <p className={gate.status === "insufficient" ? styles.insufficient : styles.smallSample} data-evidence-block>{gate.warning}</p>}
    <div className={styles.detailMetrics} data-evidence-block>
      <div><strong>{record.job_count}</strong><span>个岗位出现</span></div>
      <div><strong>{record.company_count}</strong><span>家公司</span></div>
      <div><strong>约 {Math.round(record.learning_hours_expected)}</strong><span>小时学习投入</span></div>
    </div>
    <section data-evidence-block>
      <h3>为什么值得关注？</h3>
      <ul>
        <li>招聘支持覆盖当前样本的 {(record.job_coverage * 100).toFixed(1)}%</li>
        <li>公司覆盖率 {(record.company_coverage * 100).toFixed(1)}%</li>
        <li>{record.role_count} 个职业方向达到支持门槛</li>
        <li>排名稳健性：{robustnessCopy(record)}</li>
      </ul>
    </section>
    {relation && <section className={styles.relationDetail} data-evidence-block>
      <h3>{record.skill} + {relation.related_skill}</h3>
      <p>经常一起出现</p>
      <strong>{formatRelationEvidence(relation.cooccurrence_count, relation.recency_window)}</strong>
      <span>在提到 {record.skill} 的岗位中，{(relation.core_conditional_coverage * 100).toFixed(1)}% 同时提到 {relation.related_skill}。</span>
      <button type="button" onClick={() => onSelectRelation(relation.related_skill_id)}>以 {relation.related_skill} 继续探索</button>
    </section>}
    <details data-evidence-block>
      <summary>查看分析依据</summary>
      <dl className={styles.advancedEvidence}>
        <div><dt>Market Signal</dt><dd>{record.market_signal.toFixed(1)}</dd></div>
        <div><dt>SkillWorth</dt><dd>{record.skillworth_score.toFixed(1)}</dd></div>
        <div><dt>Confidence</dt><dd>{record.confidence.toFixed(1)} · {record.confidence_level}</dd></div>
        <div><dt>Robustness</dt><dd>{record.ranking_robustness.toFixed(1)} · {record.robustness_level}</dd></div>
        {relation && <><div><dt>Jaccard</dt><dd>{relation.jaccard.toFixed(3)}</dd></div><div><dt>PMI</dt><dd>{relation.pmi.toFixed(3)}</dd></div></>}
      </dl>
      <a href="/methodology">查看完整方法说明</a>
    </details>
  </aside>;
}
